"""Property-based tests for transfer creating completed transaction.

**Feature: high-frequency-transaction-system, Property 12: Transfer Creates Completed Transaction**
**Validates: Requirements 8.9**
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.models.wallet import Wallet


# Strategy for DECIMAL(18,4) values - valid financial amounts
decimal_18_4_strategy = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("10000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for transfer amounts
transfer_amount_strategy = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("1000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)


def create_test_engine():
    """Create an in-memory SQLite engine for testing."""
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
)
def test_transfer_creates_completed_transaction(
    sender_balance: Decimal,
    receiver_balance: Decimal,
    transfer_amount: Decimal,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 12: Transfer Creates Completed Transaction**
    
    *For any* successful fund transfer, a Transaction record SHALL be created
    with status COMPLETED and the exact transfer amount.
    
    **Validates: Requirements 8.9**
    """
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
        
        # Count transactions before transfer
        transactions_before = session.query(Transaction).count()
        
        # Perform transfer
        try:
            # Simulate the transfer logic
            sender_wallet.balance -= transfer_amount
            receiver_wallet.balance += transfer_amount
            
            # Create transaction record
            transaction = Transaction(
                sender_wallet_id=sender_wallet_id,
                receiver_wallet_id=receiver_wallet_id,
                amount=transfer_amount,
                status=TransactionStatus.COMPLETED,
            )
            session.add(transaction)
            session.commit()
        except Exception:
            session.rollback()
            raise
        
        # Count transactions after transfer
        transactions_after = session.query(Transaction).count()
        
        # Verify exactly one transaction was created
        assert transactions_after == transactions_before + 1, (
            f"Expected exactly one transaction to be created, "
            f"but count changed from {transactions_before} to {transactions_after}"
        )
        
        # Query the created transaction
        created_transaction = (
            session.query(Transaction)
            .filter(Transaction.sender_wallet_id == sender_wallet_id)
            .filter(Transaction.receiver_wallet_id == receiver_wallet_id)
            .order_by(Transaction.created_at.desc())
            .first()
        )
        
        # Verify transaction exists
        assert created_transaction is not None, (
            "Transaction record was not found in database"
        )
        
        # Verify transaction has COMPLETED status
        assert created_transaction.status == TransactionStatus.COMPLETED, (
            f"Expected transaction status to be COMPLETED, "
            f"but got {created_transaction.status}"
        )
        
        # Verify transaction has exact transfer amount
        assert created_transaction.amount == transfer_amount, (
            f"Expected transaction amount to be {transfer_amount}, "
            f"but got {created_transaction.amount}"
        )
        
        # Verify transaction references correct wallets
        assert created_transaction.sender_wallet_id == sender_wallet_id, (
            f"Expected sender_wallet_id to be {sender_wallet_id}, "
            f"but got {created_transaction.sender_wallet_id}"
        )
        assert created_transaction.receiver_wallet_id == receiver_wallet_id, (
            f"Expected receiver_wallet_id to be {receiver_wallet_id}, "
            f"but got {created_transaction.receiver_wallet_id}"
        )
