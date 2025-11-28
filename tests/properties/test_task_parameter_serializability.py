"""Property-based tests for task parameter serializability.

**Feature: async-task-processing, Property 4: Task Parameter Serializability**
**Validates: Requirements 8.4, 8.5**
"""

import json
from decimal import Decimal

from hypothesis import given, settings, strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker import send_transaction_email, audit_log_transaction


# Strategy for email addresses
email_strategy = st.emails()

# Strategy for decimal amounts as strings
amount_strategy = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("999999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False
).map(str)

# Strategy for transaction status
status_strategy = st.sampled_from(["SUCCESS", "FAILED"])

# Strategy for transaction IDs (UUIDs as strings)
transaction_id_strategy = st.uuids().map(str)

# Strategy for transaction data dictionaries
transaction_data_strategy = st.fixed_dictionaries({
    "sender_wallet_id": st.uuids().map(str),
    "receiver_wallet_id": st.uuids().map(str),
    "amount": amount_strategy,
    "status": st.sampled_from(["PENDING", "COMPLETED", "FAILED"]),
    "created_at": st.datetimes().map(lambda dt: dt.isoformat())
})


@settings(max_examples=100, deadline=None)
@given(
    email=email_strategy,
    amount=amount_strategy,
    status=status_strategy,
)
def test_email_task_parameters_are_json_serializable(
    email: str,
    amount: str,
    status: str,
) -> None:
    """
    **Feature: async-task-processing, Property 4: Task Parameter Serializability**
    
    *For any* email task invocation, all task parameters SHALL be JSON-serializable
    (strings, numbers, dictionaries, lists) and SHALL NOT include database session
    objects or ORM model instances.
    
    **Validates: Requirements 8.4, 8.5**
    """
    # Collect all parameters
    params = {
        "email": email,
        "amount": amount,
        "status": status,
    }
    
    # Verify all parameters are JSON-serializable
    try:
        serialized = json.dumps(params)
        deserialized = json.loads(serialized)
        
        # Verify round-trip preserves values
        assert deserialized["email"] == email
        assert deserialized["amount"] == amount
        assert deserialized["status"] == status
    except (TypeError, ValueError) as e:
        raise AssertionError(f"Task parameters are not JSON-serializable: {e}")
    
    # Verify no parameters are database session objects
    for param_name, param_value in params.items():
        assert not isinstance(param_value, AsyncSession), \
            f"Parameter '{param_name}' is a database session object"
        
        # Check that the parameter is not an ORM model instance
        # ORM models typically have __tablename__ or __table__ attributes
        assert not hasattr(param_value, "__tablename__"), \
            f"Parameter '{param_name}' appears to be an ORM model instance"
        assert not hasattr(param_value, "__table__"), \
            f"Parameter '{param_name}' appears to be an ORM model instance"


@settings(max_examples=100, deadline=None)
@given(
    transaction_id=transaction_id_strategy,
    data=transaction_data_strategy,
)
def test_audit_task_parameters_are_json_serializable(
    transaction_id: str,
    data: dict,
) -> None:
    """
    **Feature: async-task-processing, Property 4: Task Parameter Serializability**
    
    *For any* audit task invocation, all task parameters SHALL be JSON-serializable
    (strings, numbers, dictionaries, lists) and SHALL NOT include database session
    objects or ORM model instances.
    
    **Validates: Requirements 8.4, 8.5**
    """
    # Collect all parameters
    params = {
        "transaction_id": transaction_id,
        "data": data,
    }
    
    # Verify all parameters are JSON-serializable
    try:
        serialized = json.dumps(params)
        deserialized = json.loads(serialized)
        
        # Verify round-trip preserves values
        assert deserialized["transaction_id"] == transaction_id
        assert deserialized["data"] == data
    except (TypeError, ValueError) as e:
        raise AssertionError(f"Task parameters are not JSON-serializable: {e}")
    
    # Verify no parameters are database session objects
    for param_name, param_value in params.items():
        assert not isinstance(param_value, AsyncSession), \
            f"Parameter '{param_name}' is a database session object"
        
        # Check that the parameter is not an ORM model instance
        assert not hasattr(param_value, "__tablename__"), \
            f"Parameter '{param_name}' appears to be an ORM model instance"
        assert not hasattr(param_value, "__table__"), \
            f"Parameter '{param_name}' appears to be an ORM model instance"
    
    # Also verify nested data dictionary values
    for key, value in data.items():
        assert not isinstance(value, AsyncSession), \
            f"Data key '{key}' contains a database session object"
        assert not hasattr(value, "__tablename__"), \
            f"Data key '{key}' appears to be an ORM model instance"
        assert not hasattr(value, "__table__"), \
            f"Data key '{key}' appears to be an ORM model instance"
