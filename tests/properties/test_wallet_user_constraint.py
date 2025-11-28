"""Property-based tests for Wallet-User one-to-one constraint.

**Feature: high-frequency-transaction-system, Property 6: Wallet-User One-to-One Constraint**
**Validates: Requirements 5.1**
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


# Strategy for valid email addresses
email_strategy = st.emails()

# Strategy for valid full names (non-empty strings)
full_name_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())

# Strategy for valid hashed passwords (non-empty strings)
hashed_password_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())

# Strategy for valid currency codes
currency_strategy = st.sampled_from(["USD", "VND", "EUR"])

# Strategy for DECIMAL(18,4) values
decimal_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("99999999999999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)


def create_test_engine():
    """Create an in-memory SQLite engine for testing.
    
    Note: We use SQLite for unit testing the uniqueness constraint.
    The actual PostgreSQL database will enforce the same constraint.
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
    email=email_strategy,
    full_name=full_name_strategy,
    hashed_password=hashed_password_strategy,
    balance1=decimal_strategy,
    balance2=decimal_strategy,
    currency1=currency_strategy,
    currency2=currency_strategy,
)
def test_wallet_user_one_to_one_constraint(
    email: str,
    full_name: str,
    hashed_password: str,
    balance1: Decimal,
    balance2: Decimal,
    currency1: str,
    currency2: str,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 6: Wallet-User One-to-One Constraint**
    
    *For any* User that already has a Wallet, attempting to create a second
    Wallet for that User SHALL raise an IntegrityError.
    
    **Validates: Requirements 5.1**
    """
    engine = create_test_engine()
    
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        
        # Create a user
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        
        # Create first wallet for the user
        wallet1 = Wallet(
            id=uuid.uuid4(),
            user_id=user.id,
            balance=balance1,
            currency=currency1,
            version=1,
            created_at=now,
            updated_at=now,
        )
        session.add(wallet1)
        session.commit()
        
        # Attempt to create second wallet for the same user
        wallet2 = Wallet(
            id=uuid.uuid4(),
            user_id=user.id,
            balance=balance2,
            currency=currency2,
            version=1,
            created_at=now,
            updated_at=now,
        )
        session.add(wallet2)
        
        # Second wallet for same user should raise IntegrityError
        try:
            session.commit()
            raise AssertionError(
                f"Expected IntegrityError for duplicate user_id '{user.id}', but commit succeeded"
            )
        except IntegrityError:
            # This is the expected behavior - uniqueness constraint violated
            session.rollback()
