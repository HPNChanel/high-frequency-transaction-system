"""Property-based tests for User email uniqueness constraint.

**Feature: high-frequency-transaction-system, Property 5: User Email Uniqueness**
**Validates: Requirements 4.2**
"""

import uuid
from datetime import datetime, timezone

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.user import User


# Strategy for valid email addresses
email_strategy = st.emails()

# Strategy for valid full names (non-empty strings)
full_name_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())

# Strategy for valid hashed passwords (non-empty strings)
hashed_password_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())


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
    full_name1=full_name_strategy,
    full_name2=full_name_strategy,
    hashed_password1=hashed_password_strategy,
    hashed_password2=hashed_password_strategy,
)
def test_user_email_uniqueness(
    email: str,
    full_name1: str,
    full_name2: str,
    hashed_password1: str,
    hashed_password2: str,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 5: User Email Uniqueness**
    
    *For any* two User creation attempts with identical email addresses,
    the second attempt SHALL raise an IntegrityError.
    
    **Validates: Requirements 4.2**
    """
    engine = create_test_engine()
    
    with Session(engine) as session:
        # Create first user
        now = datetime.now(timezone.utc)
        user1 = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password1,
            full_name=full_name1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user1)
        session.commit()
        
        # Attempt to create second user with same email
        user2 = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password2,
            full_name=full_name2,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user2)
        
        # Second user with same email should raise IntegrityError
        try:
            session.commit()
            raise AssertionError(
                f"Expected IntegrityError for duplicate email '{email}', but commit succeeded"
            )
        except IntegrityError:
            # This is the expected behavior - uniqueness constraint violated
            session.rollback()
