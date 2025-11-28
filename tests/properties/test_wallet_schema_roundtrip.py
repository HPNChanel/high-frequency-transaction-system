"""Property-based tests for Wallet schema round-trip.

**Feature: high-frequency-transaction-system, Property 2: Wallet Schema Round-Trip with Decimal Precision**
**Validates: Requirements 5.6, 5.7**
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings, strategies as st

from app.models.wallet import Wallet
from app.schemas.wallet import WalletRead


# Strategy for DECIMAL(18,4) values - valid financial amounts
decimal_18_4_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("99999999999999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for valid currency codes (ISO 4217)
currency_strategy = st.sampled_from(["USD", "VND", "EUR", "GBP", "JPY"])

# Strategy for version numbers (positive integers)
version_strategy = st.integers(min_value=1, max_value=1000000)

# Strategy for datetime values
datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 12, 31),
    timezones=st.just(timezone.utc)
)


@settings(max_examples=100)
@given(
    balance=decimal_18_4_strategy,
    currency=currency_strategy,
    version=version_strategy,
    created_at=datetime_strategy,
    updated_at=datetime_strategy,
)
def test_wallet_schema_round_trip(
    balance: Decimal,
    currency: str,
    version: int,
    created_at: datetime,
    updated_at: datetime,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 2: Wallet Schema Round-Trip with Decimal Precision**
    
    *For any* valid Wallet object with balance having up to 4 decimal places,
    serializing to JSON and deserializing back SHALL produce an equivalent
    Wallet object with exact decimal precision preserved.
    
    **Validates: Requirements 5.6, 5.7**
    """
    # Create a Wallet ORM model instance
    wallet_id = uuid.uuid4()
    user_id = uuid.uuid4()
    wallet = Wallet(
        id=wallet_id,
        user_id=user_id,
        balance=balance,
        currency=currency,
        version=version,
        created_at=created_at,
        updated_at=updated_at,
    )
    
    # Serialize to Pydantic schema (simulates JSON serialization)
    wallet_read = WalletRead.model_validate(wallet)
    
    # Serialize to JSON and back
    json_data = wallet_read.model_dump_json()
    wallet_read_restored = WalletRead.model_validate_json(json_data)
    
    # Verify all fields are preserved
    assert wallet_read_restored.id == wallet_id
    assert wallet_read_restored.user_id == user_id
    assert wallet_read_restored.currency == currency
    assert wallet_read_restored.version == version
    assert wallet_read_restored.created_at == created_at
    assert wallet_read_restored.updated_at == updated_at
    
    # Verify decimal precision is preserved exactly
    # The balance is serialized as string, so we compare the decimal values
    assert Decimal(str(wallet_read_restored.balance)) == balance
