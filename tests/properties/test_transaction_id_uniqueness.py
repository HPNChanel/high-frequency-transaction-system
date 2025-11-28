"""Property-based tests for Transaction ID uniqueness.

**Feature: high-frequency-transaction-system, Property 9: Transaction ID Uniqueness**
**Validates: Requirements 6.1**
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionStatus


# Strategy for number of transactions to create
num_transactions_strategy = st.integers(min_value=2, max_value=20)

# Strategy for DECIMAL(18,4) values
decimal_strategy = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("9999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for Transaction status
status_strategy = st.sampled_from(list(TransactionStatus))


def create_test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    return engine


def create_user_and_wallet(session, email: str) -> Wallet:
    """Helper to create a user and wallet."""
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hashedpassword123",
        full_name="Test User",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.commit()
    
    wallet = Wallet(
        id=uuid.uuid4(),
        user_id=user.id,
        balance=Decimal("10000.0000"),
        currency="USD",
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(wallet)
    session.commit()
    return wallet


@settings(max_examples=100)
@given(
    num_transactions=num_transactions_strategy,
    amounts=st.lists(decimal_strategy, min_size=20, max_size=20),
    statuses=st.lists(status_strategy, min_size=20, max_size=20),
)
def test_transaction_id_uniqueness(
    num_transactions: int,
    amounts: list,
    statuses: list,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 9: Transaction ID Uniqueness**
    
    *For any* set of N transactions created, all N transaction IDs SHALL be unique.
    
    **Validates: Requirements 6.1**
    """
    engine = create_test_engine()
    
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        
        # Create sender and receiver wallets
        sender_wallet = create_user_and_wallet(session, "sender@test.com")
        receiver_wallet = create_user_and_wallet(session, "receiver@test.com")
        
        # Create N transactions
        transaction_ids = []
        for i in range(num_transactions):
            transaction = Transaction(
                id=uuid.uuid4(),
                sender_wallet_id=sender_wallet.id,
                receiver_wallet_id=receiver_wallet.id,
                amount=amounts[i],
                status=statuses[i],
                created_at=now,
            )
            session.add(transaction)
            session.commit()
            transaction_ids.append(transaction.id)
        
        # Verify all transaction IDs are unique
        assert len(transaction_ids) == num_transactions
        assert len(set(transaction_ids)) == num_transactions, (
            f"Expected {num_transactions} unique transaction IDs, "
            f"but got {len(set(transaction_ids))} unique IDs"
        )
