"""Property-based tests for Transaction schema round-trip.

**Feature: high-frequency-transaction-system, Property 3: Transaction Schema Round-Trip**
**Validates: Requirements 6.8, 6.9**
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings, strategies as st

# Import all models to ensure proper mapper initialization
from app.models.user import User  # noqa: F401
from app.models.wallet import Wallet  # noqa: F401
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import TransactionRead


# Strategy for DECIMAL(18,4) values - valid financial amounts (positive)
decimal_18_4_strategy = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("99999999999999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for Transaction status
status_strategy = st.sampled_from(list(TransactionStatus))

# Strategy for datetime values
datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 12, 31),
    timezones=st.just(timezone.utc)
)


@settings(max_examples=100)
@given(
    amount=decimal_18_4_strategy,
    status=status_strategy,
    created_at=datetime_strategy,
)
def test_transaction_schema_round_trip(
    amount: Decimal,
    status: TransactionStatus,
    created_at: datetime,
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 3: Transaction Schema Round-Trip**
    
    *For any* valid Transaction object, serializing to JSON and deserializing back
    SHALL produce an equivalent Transaction object with exact decimal amount
    precision and valid enum status preserved.
    
    **Validates: Requirements 6.8, 6.9**
    """
    # Create a Transaction ORM model instance
    transaction_id = uuid.uuid4()
    sender_wallet_id = uuid.uuid4()
    receiver_wallet_id = uuid.uuid4()
    
    transaction = Transaction(
        id=transaction_id,
        sender_wallet_id=sender_wallet_id,
        receiver_wallet_id=receiver_wallet_id,
        amount=amount,
        status=status,
        created_at=created_at,
    )
    
    # Serialize to Pydantic schema (simulates JSON serialization)
    transaction_read = TransactionRead.model_validate(transaction)
    
    # Serialize to JSON and back
    json_data = transaction_read.model_dump_json()
    transaction_read_restored = TransactionRead.model_validate_json(json_data)
    
    # Verify all fields are preserved
    assert transaction_read_restored.id == transaction_id
    assert transaction_read_restored.sender_wallet_id == sender_wallet_id
    assert transaction_read_restored.receiver_wallet_id == receiver_wallet_id
    assert transaction_read_restored.created_at == created_at
    
    # Verify decimal precision is preserved exactly
    assert Decimal(str(transaction_read_restored.amount)) == amount
    
    # Verify status enum is preserved
    assert transaction_read_restored.status == status
    assert transaction_read_restored.status.value == status.value
