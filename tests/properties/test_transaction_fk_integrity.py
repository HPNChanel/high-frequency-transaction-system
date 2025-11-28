"""Property-based tests for Transaction foreign key integrity.

**Feature: high-frequency-transaction-system, Property 7: Transaction Foreign Key Integrity**
**Validates: Requirements 6.2, 6.3**
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionStatus


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


def create_user_and_wallet(session, email_suffix: int) -> Wallet:
    """Helper to create a user and wallet."""
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=f"user{email_suffix}@test.com",
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
        balance=Decimal("1000.0000"),
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
    amount=decimal_strategy,
    status=status_strategy,
    test_index=st.integers(min_value=0, max_value=999999),
)
def test_transaction_fk_integrity_invalid_sender(
    amount: Decimal,
    status: TransactionStatus,
    test_index: int,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 7: Transaction Foreign Key Integrity**
    
    *For any* Transaction creation with a sender_wallet_id that does not exist
    in the Wallets table, the creation SHALL raise an IntegrityError.
    
    **Validates: Requirements 6.2, 6.3**
    """
    engine = create_test_engine()
    
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        
        # Create a valid receiver wallet
        receiver_wallet = create_user_and_wallet(session, test_index)
        
        # Attempt to create transaction with non-existent sender_wallet_id
        non_existent_wallet_id = uuid.uuid4()
        transaction = Transaction(
            id=uuid.uuid4(),
            sender_wallet_id=non_existent_wallet_id,
            receiver_wallet_id=receiver_wallet.id,
            amount=amount,
            status=status,
            created_at=now,
        )
        session.add(transaction)
        
        try:
            session.commit()
            raise AssertionError(
                f"Expected IntegrityError for non-existent sender_wallet_id, but commit succeeded"
            )
        except IntegrityError:
            session.rollback()


@settings(max_examples=100)
@given(
    amount=decimal_strategy,
    status=status_strategy,
    test_index=st.integers(min_value=0, max_value=999999),
)
def test_transaction_fk_integrity_invalid_receiver(
    amount: Decimal,
    status: TransactionStatus,
    test_index: int,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 7: Transaction Foreign Key Integrity**
    
    *For any* Transaction creation with a receiver_wallet_id that does not exist
    in the Wallets table, the creation SHALL raise an IntegrityError.
    
    **Validates: Requirements 6.2, 6.3**
    """
    engine = create_test_engine()
    
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        
        # Create a valid sender wallet
        sender_wallet = create_user_and_wallet(session, test_index + 1000000)
        
        # Attempt to create transaction with non-existent receiver_wallet_id
        non_existent_wallet_id = uuid.uuid4()
        transaction = Transaction(
            id=uuid.uuid4(),
            sender_wallet_id=sender_wallet.id,
            receiver_wallet_id=non_existent_wallet_id,
            amount=amount,
            status=status,
            created_at=now,
        )
        session.add(transaction)
        
        try:
            session.commit()
            raise AssertionError(
                f"Expected IntegrityError for non-existent receiver_wallet_id, but commit succeeded"
            )
        except IntegrityError:
            session.rollback()
