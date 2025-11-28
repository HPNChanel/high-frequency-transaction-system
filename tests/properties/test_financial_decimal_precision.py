"""Property-based tests for financial decimal precision.

**Feature: high-frequency-transaction-system, Property 8: Financial Decimal Precision**
**Validates: Requirements 5.2, 6.4**
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


# Strategy for DECIMAL(18,4) values - valid financial amounts
# Using 4 decimal places to match DECIMAL(18,4) specification
# Note: SQLite stores NUMERIC as floating-point, so we limit the range
# to values that can be represented exactly in IEEE 754 double precision.
# PostgreSQL will handle the full DECIMAL(18,4) range correctly.
# For testing with SQLite, we limit to 10^9 which can be represented precisely
# in IEEE 754 double precision (53-bit mantissa allows ~15-16 significant digits).
decimal_18_4_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("999999999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for valid email addresses
email_strategy = st.emails()

# Strategy for valid full names (non-empty strings)
full_name_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())

# Strategy for valid hashed passwords (non-empty strings)
hashed_password_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())

# Strategy for valid currency codes
currency_strategy = st.sampled_from(["USD", "VND", "EUR"])


def create_test_engine():
    """Create an in-memory SQLite engine for testing.
    
    Note: We use SQLite for unit testing decimal precision.
    SQLite stores NUMERIC as text, which preserves decimal precision.
    The actual PostgreSQL database will use DECIMAL(18,4) for exact precision.
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
    balance=decimal_18_4_strategy,
    email=email_strategy,
    full_name=full_name_strategy,
    hashed_password=hashed_password_strategy,
    currency=currency_strategy,
)
def test_wallet_balance_decimal_precision(
    balance: Decimal,
    email: str,
    full_name: str,
    hashed_password: str,
    currency: str,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 8: Financial Decimal Precision**
    
    *For any* decimal value with up to 4 decimal places stored in Wallet.balance,
    retrieval SHALL return the exact same decimal value without floating-point errors.
    
    **Validates: Requirements 5.2, 6.4**
    """
    engine = create_test_engine()
    
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        
        # Create a user first (required for wallet foreign key)
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
        
        # Create wallet with specific balance
        wallet_id = uuid.uuid4()
        wallet = Wallet(
            id=wallet_id,
            user_id=user.id,
            balance=balance,
            currency=currency,
            version=1,
            created_at=now,
            updated_at=now,
        )
        session.add(wallet)
        session.commit()
        
        # Clear session cache to force database read
        session.expire_all()
        
        # Retrieve wallet from database
        retrieved_wallet = session.get(Wallet, wallet_id)
        
        # Verify decimal precision is preserved exactly
        assert retrieved_wallet is not None
        assert retrieved_wallet.balance == balance, (
            f"Balance precision lost: stored {balance}, retrieved {retrieved_wallet.balance}"
        )
