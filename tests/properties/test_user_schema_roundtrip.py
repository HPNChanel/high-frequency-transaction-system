"""Property-based tests for User schema round-trip.

**Feature: high-frequency-transaction-system, Property 1: User Schema Round-Trip**
**Validates: Requirements 4.4, 4.5**
"""

import uuid
from datetime import datetime, timezone

from hypothesis import given, settings, strategies as st

from app.models.user import User
from app.schemas.user import UserRead


# Strategy for valid email addresses
email_strategy = st.emails()

# Strategy for valid full names (non-empty strings)
full_name_strategy = st.text(min_size=1, max_size=255).filter(lambda x: x.strip())

# Strategy for valid hashed passwords (non-empty strings)
hashed_password_strategy = st.text(min_size=1, max_size=255).filter(lambda x: x.strip())

# Strategy for boolean values
is_active_strategy = st.booleans()

# Strategy for datetime values
datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 12, 31),
    timezones=st.just(timezone.utc)
)


@settings(max_examples=100)
@given(
    email=email_strategy,
    full_name=full_name_strategy,
    hashed_password=hashed_password_strategy,
    is_active=is_active_strategy,
    created_at=datetime_strategy,
    updated_at=datetime_strategy,
)
def test_user_schema_round_trip(
    email: str,
    full_name: str,
    hashed_password: str,
    is_active: bool,
    created_at: datetime,
    updated_at: datetime,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 1: User Schema Round-Trip**
    
    *For any* valid User object, serializing to JSON (via Pydantic schema) and
    deserializing back SHALL produce an equivalent User object with all
    non-sensitive fields preserved.
    
    **Validates: Requirements 4.4, 4.5**
    """
    # Create a User ORM model instance
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=is_active,
        created_at=created_at,
        updated_at=updated_at,
    )
    
    # Serialize to Pydantic schema (simulates JSON serialization)
    user_read = UserRead.model_validate(user)
    
    # Serialize to JSON and back
    json_data = user_read.model_dump_json()
    user_read_restored = UserRead.model_validate_json(json_data)
    
    # Verify all non-sensitive fields are preserved
    assert user_read_restored.id == user_id
    # Email domain is normalized to lowercase per RFC 5321 by Pydantic's EmailStr
    # So we compare the normalized version from the first serialization
    assert user_read_restored.email == user_read.email
    assert user_read_restored.full_name == full_name
    assert user_read_restored.is_active == is_active
    assert user_read_restored.created_at == created_at
    assert user_read_restored.updated_at == updated_at
    
    # Verify hashed_password is NOT in the serialized output
    json_dict = user_read.model_dump()
    assert "hashed_password" not in json_dict
    assert "password" not in json_dict
