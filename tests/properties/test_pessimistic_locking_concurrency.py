"""Property-based tests for pessimistic locking concurrency control.

**Feature: high-frequency-transaction-system, Property 13: Pessimistic Locking Prevents Concurrent Modification**
**Validates: Requirements 10.1, 10.2**
"""

import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Tuple

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction


# Strategy for DECIMAL(18,4) values - valid financial amounts
decimal_18_4_strategy = st.decimals(
    min_value=Decimal("1000.0000"),  # Ensure sufficient balance for multiple transfers
    max_value=Decimal("10000.0000"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for transfer amounts (must be positive and less than sender balance)
transfer_amount_strategy = st.decimals(
    min_value=Decimal("10.0000"),
    max_value=Decimal("100.0000"),  # Keep reasonable to ensure valid transfers
    places=4,
    allow_nan=False,
    allow_infinity=False
)


def create_test_engine():
    """Create a temporary file-based SQLite engine for testing.
    
    Note: We use a file-based SQLite database for concurrent testing
    because in-memory databases cannot be shared across threads.
    
    SQLite doesn't support row-level locking (SELECT ... FOR UPDATE),
    so we use BEGIN IMMEDIATE transactions to simulate pessimistic locking.
    BEGIN IMMEDIATE acquires a write lock on the entire database, which
    forces other transactions to wait - similar to how PostgreSQL's
    SELECT ... FOR UPDATE works but at the database level instead of row level.
    
    The actual PostgreSQL database will have proper row-level locking.
    """
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    # Create engine with file-based database
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    
    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    
    # Store the path for cleanup
    engine._test_db_path = db_path
    
    return engine


@settings(max_examples=100)
@given(
    wallet_a_balance=decimal_18_4_strategy,
    wallet_b_balance=decimal_18_4_strategy,
    transfer_amount_1=transfer_amount_strategy,
    transfer_amount_2=transfer_amount_strategy,
)
def test_pessimistic_locking_prevents_concurrent_modification(
    wallet_a_balance: Decimal,
    wallet_b_balance: Decimal,
    transfer_amount_1: Decimal,
    transfer_amount_2: Decimal,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 13: Pessimistic Locking Prevents Concurrent Modification**
    
    *For any* two concurrent transfer attempts involving the same wallet, when
    using pessimistic locking, the second transaction SHALL wait until the first
    completes, and both SHALL see consistent wallet balances.
    
    **Validates: Requirements 10.1, 10.2**
    
    This test simulates concurrent transfers by:
    1. Creating two wallets with initial balances
    2. Launching two concurrent transfers involving the same wallet
    3. Verifying that both transfers complete successfully (one waits for the other)
    4. Verifying that the final balances are consistent (no lost updates)
    5. Verifying that balance conservation holds across both transfers
    """
    # Normalize all values to 4 decimal places to match DECIMAL(18,4) precision
    wallet_a_balance = wallet_a_balance.quantize(Decimal("0.0001"))
    wallet_b_balance = wallet_b_balance.quantize(Decimal("0.0001"))
    transfer_amount_1 = transfer_amount_1.quantize(Decimal("0.0001"))
    transfer_amount_2 = transfer_amount_2.quantize(Decimal("0.0001"))
    
    # Skip if wallet A doesn't have enough funds for both transfers
    if wallet_a_balance < (transfer_amount_1 + transfer_amount_2):
        return
    
    engine = create_test_engine()
    SessionLocal = sessionmaker(bind=engine)
    
    try:
        # Setup: Create users and wallets
        with SessionLocal() as setup_session:
            now = datetime.now(timezone.utc)
            
            # Create users
            user_a_id = uuid.uuid4()
            user_b_id = uuid.uuid4()
            user_c_id = uuid.uuid4()
            
            user_a = User(
                id=user_a_id,
                email=f"user_a_{uuid.uuid4()}@example.com",
                hashed_password="hashed_password",
                full_name="User A",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            user_b = User(
                id=user_b_id,
                email=f"user_b_{uuid.uuid4()}@example.com",
                hashed_password="hashed_password",
                full_name="User B",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            user_c = User(
                id=user_c_id,
                email=f"user_c_{uuid.uuid4()}@example.com",
                hashed_password="hashed_password",
                full_name="User C",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            setup_session.add_all([user_a, user_b, user_c])
            setup_session.commit()
            
            # Create wallets
            wallet_a_id = uuid.uuid4()
            wallet_b_id = uuid.uuid4()
            wallet_c_id = uuid.uuid4()
            
            wallet_a = Wallet(
                id=wallet_a_id,
                user_id=user_a_id,
                balance=wallet_a_balance,
                currency="USD",
                version=1,
                created_at=now,
                updated_at=now,
            )
            wallet_b = Wallet(
                id=wallet_b_id,
                user_id=user_b_id,
                balance=wallet_b_balance,
                currency="USD",
                version=1,
                created_at=now,
                updated_at=now,
            )
            wallet_c = Wallet(
                id=wallet_c_id,
                user_id=user_c_id,
                balance=Decimal("0.0000"),
                currency="USD",
                version=1,
                created_at=now,
                updated_at=now,
            )
            setup_session.add_all([wallet_a, wallet_b, wallet_c])
            setup_session.commit()
        
        # Calculate expected final balances
        initial_total = wallet_a_balance + wallet_b_balance
        expected_wallet_a_balance = wallet_a_balance - transfer_amount_1 - transfer_amount_2
        expected_wallet_b_balance = wallet_b_balance + transfer_amount_1
        expected_wallet_c_balance = transfer_amount_2
        
        # Track results from concurrent transfers
        results: List[Tuple[bool, str]] = []
        errors: List[Exception] = []
        
        def perform_transfer_1():
            """Transfer from wallet A to wallet B"""
            try:
                with SessionLocal() as session:
                    # Use BEGIN IMMEDIATE for SQLite to acquire a write lock immediately
                    # This simulates pessimistic locking behavior
                    session.execute(text("BEGIN IMMEDIATE"))
                    try:
                        # Read the wallets (now protected by the IMMEDIATE lock)
                        sender = session.query(Wallet).filter(
                            Wallet.id == wallet_a_id
                        ).first()
                        
                        receiver = session.query(Wallet).filter(
                            Wallet.id == wallet_b_id
                        ).first()
                        
                        # Perform the transfer
                        if sender and receiver and sender.balance >= transfer_amount_1:
                            sender.balance -= transfer_amount_1
                            receiver.balance += transfer_amount_1
                            
                            # Create transaction record
                            transaction = Transaction(
                                sender_wallet_id=wallet_a_id,
                                receiver_wallet_id=wallet_b_id,
                                amount=transfer_amount_1,
                                status="COMPLETED",
                            )
                            session.add(transaction)
                            
                            session.commit()
                            results.append((True, "transfer_1"))
                        else:
                            session.rollback()
                            results.append((False, "transfer_1_insufficient_funds"))
                    except Exception as e:
                        session.rollback()
                        errors.append(e)
                        results.append((False, f"transfer_1_error: {e}"))
            except Exception as e:
                errors.append(e)
                results.append((False, f"transfer_1_outer_error: {e}"))
        
        def perform_transfer_2():
            """Transfer from wallet A to wallet C"""
            try:
                with SessionLocal() as session:
                    # Use BEGIN IMMEDIATE for SQLite to acquire a write lock immediately
                    # This simulates pessimistic locking behavior
                    session.execute(text("BEGIN IMMEDIATE"))
                    try:
                        # Read the wallets (now protected by the IMMEDIATE lock)
                        sender = session.query(Wallet).filter(
                            Wallet.id == wallet_a_id
                        ).first()
                        
                        receiver = session.query(Wallet).filter(
                            Wallet.id == wallet_c_id
                        ).first()
                        
                        # Perform the transfer
                        if sender and receiver and sender.balance >= transfer_amount_2:
                            sender.balance -= transfer_amount_2
                            receiver.balance += transfer_amount_2
                            
                            # Create transaction record
                            transaction = Transaction(
                                sender_wallet_id=wallet_a_id,
                                receiver_wallet_id=wallet_c_id,
                                amount=transfer_amount_2,
                                status="COMPLETED",
                            )
                            session.add(transaction)
                            
                            session.commit()
                            results.append((True, "transfer_2"))
                        else:
                            session.rollback()
                            results.append((False, "transfer_2_insufficient_funds"))
                    except Exception as e:
                        session.rollback()
                        errors.append(e)
                        results.append((False, f"transfer_2_error: {e}"))
            except Exception as e:
                errors.append(e)
                results.append((False, f"transfer_2_outer_error: {e}"))
        
        # Execute concurrent transfers using threads
        thread1 = threading.Thread(target=perform_transfer_1)
        thread2 = threading.Thread(target=perform_transfer_2)
        
        thread1.start()
        thread2.start()
        
        thread1.join(timeout=5.0)
        thread2.join(timeout=5.0)
        
        # Verify both threads completed
        assert not thread1.is_alive(), "Transfer 1 thread did not complete"
        assert not thread2.is_alive(), "Transfer 2 thread did not complete"
        
        # Verify no errors occurred
        if errors:
            raise AssertionError(f"Errors occurred during concurrent transfers: {errors}")
        
        # Verify both transfers succeeded
        assert len(results) == 2, f"Expected 2 results, got {len(results)}: {results}"
        assert all(success for success, _ in results), (
            f"Not all transfers succeeded: {results}"
        )
        
        # Verify final balances
        with SessionLocal() as verify_session:
            wallet_a_final = verify_session.query(Wallet).filter(
                Wallet.id == wallet_a_id
            ).first()
            wallet_b_final = verify_session.query(Wallet).filter(
                Wallet.id == wallet_b_id
            ).first()
            wallet_c_final = verify_session.query(Wallet).filter(
                Wallet.id == wallet_c_id
            ).first()
            
            # Verify wallet A balance
            assert wallet_a_final.balance == expected_wallet_a_balance, (
                f"Wallet A balance incorrect: "
                f"expected={expected_wallet_a_balance}, "
                f"actual={wallet_a_final.balance}"
            )
            
            # Verify wallet B balance
            assert wallet_b_final.balance == expected_wallet_b_balance, (
                f"Wallet B balance incorrect: "
                f"expected={expected_wallet_b_balance}, "
                f"actual={wallet_b_final.balance}"
            )
            
            # Verify wallet C balance
            assert wallet_c_final.balance == expected_wallet_c_balance, (
                f"Wallet C balance incorrect: "
                f"expected={expected_wallet_c_balance}, "
                f"actual={wallet_c_final.balance}"
            )
            
            # Verify balance conservation
            final_total = (
                wallet_a_final.balance + 
                wallet_b_final.balance + 
                wallet_c_final.balance
            )
            assert initial_total == final_total, (
                f"Balance conservation violated: "
                f"initial={initial_total}, final={final_total}, "
                f"difference={final_total - initial_total}"
            )
            
            # Verify both transactions were recorded
            transactions = verify_session.query(Transaction).filter(
                Transaction.sender_wallet_id == wallet_a_id
            ).all()
            assert len(transactions) == 2, (
                f"Expected 2 transaction records, got {len(transactions)}"
            )
    
    finally:
        # Cleanup: Close engine and remove temporary database file
        engine.dispose()
        if hasattr(engine, '_test_db_path'):
            try:
                os.unlink(engine._test_db_path)
            except Exception:
                pass  # Ignore cleanup errors
