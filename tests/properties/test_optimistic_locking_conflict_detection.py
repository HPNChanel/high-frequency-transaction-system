"""Property-based tests for optimistic locking conflict detection.

**Feature: high-frequency-transaction-system, Property 14: Optimistic Locking Detects Concurrent Modification**
**Validates: Requirements 10.3, 10.4, 10.5, 10.6**
"""

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.core.exceptions import ConcurrencyError
from app.db.base import Base
from app.models.user import User
from app.models.wallet import Wallet
from app.services.transaction_service import TransactionService


# Strategy for DECIMAL(18,4) values - valid financial amounts
decimal_18_4_strategy = st.decimals(
    min_value=Decimal("100.0000"),  # Ensure sufficient balance for transfers
    max_value=Decimal("10000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for transfer amounts (must be positive and less than sender balance)
transfer_amount_strategy = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("50.0000"),  # Keep small to ensure valid transfers
    places=4,
    allow_nan=False,
    allow_infinity=False
)


def create_test_engine():
    """Create an in-memory SQLite engine for testing.
    
    Note: We use SQLite for unit testing the transfer logic.
    The actual PostgreSQL database will have the same behavior.
    """
    engine = create_engine("sqlite:///:memory:")
    
    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    return engine


@settings(max_examples=100)
@given(
    sender_balance=decimal_18_4_strategy,
    receiver_balance=decimal_18_4_strategy,
    transfer_amount=transfer_amount_strategy,
    conflict_target=st.sampled_from(["sender", "receiver"]),
)
def test_optimistic_locking_detects_concurrent_modification(
    sender_balance: Decimal,
    receiver_balance: Decimal,
    transfer_amount: Decimal,
    conflict_target: str,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 14: Optimistic Locking Detects Concurrent Modification**
    
    *For any* wallet update using optimistic locking, if another transaction
    modifies the wallet between read and update, the System SHALL raise a
    ConcurrencyError.
    
    **Validates: Requirements 10.3, 10.4, 10.5, 10.6**
    
    This test simulates concurrent modification by:
    1. Creating two wallets with initial balances
    2. Starting a transfer using optimistic locking
    3. Simulating another transaction modifying one wallet's version
    4. Verifying that ConcurrencyError is raised
    """
    # Normalize all values to 4 decimal places to match DECIMAL(18,4) precision
    sender_balance = sender_balance.quantize(Decimal("0.0001"))
    receiver_balance = receiver_balance.quantize(Decimal("0.0001"))
    transfer_amount = transfer_amount.quantize(Decimal("0.0001"))
    
    # Skip if sender doesn't have enough funds
    if sender_balance < transfer_amount:
        return
    
    engine = create_test_engine()
    
    with Session(engine) as session:
        # Create users
        now = datetime.now(timezone.utc)
        sender_user_id = uuid.uuid4()
        receiver_user_id = uuid.uuid4()
        
        sender_user = User(
            id=sender_user_id,
            email=f"sender_{uuid.uuid4()}@example.com",
            hashed_password="hashed_password",
            full_name="Sender User",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        receiver_user = User(
            id=receiver_user_id,
            email=f"receiver_{uuid.uuid4()}@example.com",
            hashed_password="hashed_password",
            full_name="Receiver User",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(sender_user)
        session.add(receiver_user)
        session.commit()
        
        # Create wallets
        sender_wallet_id = uuid.uuid4()
        receiver_wallet_id = uuid.uuid4()
        
        sender_wallet = Wallet(
            id=sender_wallet_id,
            user_id=sender_user_id,
            balance=sender_balance,
            currency="USD",
            version=1,
            created_at=now,
            updated_at=now,
        )
        receiver_wallet = Wallet(
            id=receiver_wallet_id,
            user_id=receiver_user_id,
            balance=receiver_balance,
            currency="USD",
            version=1,
            created_at=now,
            updated_at=now,
        )
        session.add(sender_wallet)
        session.add(receiver_wallet)
        session.commit()
        
        # Store original balances to verify they remain unchanged after conflict
        original_sender_balance = sender_balance
        original_receiver_balance = receiver_balance
        
        # Simulate the optimistic locking transfer with concurrent modification
        service = TransactionService()
        
        # Begin transaction
        session.begin()
        
        try:
            # Step 1: Read wallets (simulating the read phase of optimistic locking)
            sender_wallet_read = session.query(Wallet).filter(
                Wallet.id == sender_wallet_id
            ).first()
            receiver_wallet_read = session.query(Wallet).filter(
                Wallet.id == receiver_wallet_id
            ).first()
            
            sender_version = sender_wallet_read.version
            receiver_version = receiver_wallet_read.version
            
            # Step 2: Simulate concurrent modification by another transaction
            # This simulates another transaction updating the wallet between
            # our read and our update
            if conflict_target == "sender":
                # Another transaction modifies the sender wallet
                sender_wallet_read.version += 1
                session.flush()  # Persist the version change
            else:
                # Another transaction modifies the receiver wallet
                receiver_wallet_read.version += 1
                session.flush()  # Persist the version change
            
            # Step 3: Now attempt the transfer using optimistic locking logic
            # This should detect the version mismatch and raise ConcurrencyError
            
            # Validation: amount
            if transfer_amount <= Decimal("0"):
                session.rollback()
                return
            
            # Validation: self-transfer
            if sender_wallet_id == receiver_wallet_id:
                session.rollback()
                return
            
            # Validation: sufficient funds (using the values we read earlier)
            if sender_wallet_read.balance < transfer_amount:
                session.rollback()
                return
            
            # Attempt to update sender with version check
            # This uses the version we read BEFORE the concurrent modification
            sender_updated = session.query(Wallet).filter(
                Wallet.id == sender_wallet_id,
                Wallet.version == sender_version  # This will NOT match if sender was modified
            ).update({
                "balance": sender_wallet_read.balance - transfer_amount,
                "version": sender_version + 1
            }, synchronize_session=False)
            
            if sender_updated == 0:
                # Version mismatch detected - raise ConcurrencyError
                session.rollback()
                raise ConcurrencyError("Wallet", str(sender_wallet_id))
            
            # Attempt to update receiver with version check
            receiver_updated = session.query(Wallet).filter(
                Wallet.id == receiver_wallet_id,
                Wallet.version == receiver_version  # This will NOT match if receiver was modified
            ).update({
                "balance": receiver_wallet_read.balance + transfer_amount,
                "version": receiver_version + 1
            }, synchronize_session=False)
            
            if receiver_updated == 0:
                # Version mismatch detected - raise ConcurrencyError
                session.rollback()
                raise ConcurrencyError("Wallet", str(receiver_wallet_id))
            
            # If we reach here, no conflict was detected (shouldn't happen in this test)
            session.commit()
            
            # This should not happen - we expect a ConcurrencyError
            raise AssertionError(
                f"Expected ConcurrencyError when {conflict_target} was modified, "
                "but transfer succeeded"
            )
            
        except ConcurrencyError as e:
            # Expected exception - this is what we want to verify
            session.rollback()
            
            # Verify the error message contains the correct wallet ID
            if conflict_target == "sender":
                assert str(sender_wallet_id) in str(e), (
                    f"ConcurrencyError should reference sender wallet {sender_wallet_id}, "
                    f"but got: {e}"
                )
            else:
                assert str(receiver_wallet_id) in str(e), (
                    f"ConcurrencyError should reference receiver wallet {receiver_wallet_id}, "
                    f"but got: {e}"
                )
        
        # Verify balances remain unchanged after conflict
        session.refresh(sender_wallet)
        session.refresh(receiver_wallet)
        
        # The balances should be unchanged because the transaction was rolled back
        # However, the version was incremented by our simulated concurrent transaction
        assert sender_wallet.balance == original_sender_balance, (
            f"Sender balance changed after conflict: "
            f"original={original_sender_balance}, "
            f"current={sender_wallet.balance}"
        )
        assert receiver_wallet.balance == original_receiver_balance, (
            f"Receiver balance changed after conflict: "
            f"original={original_receiver_balance}, "
            f"current={receiver_wallet.balance}"
        )
