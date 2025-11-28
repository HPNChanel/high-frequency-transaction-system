"""Property-based tests for task return values.

**Feature: async-task-processing, Property 3: Task Success Return Value**
**Validates: Requirements 2.4, 3.4**
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

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
def test_email_task_returns_success_indicator(
    email: str,
    amount: str,
    status: str,
) -> None:
    """
    **Feature: async-task-processing, Property 3: Task Success Return Value**
    
    *For any* successful email task execution, the task SHALL return a dictionary
    containing a success indicator set to True.
    
    **Validates: Requirements 2.4**
    """
    # Mock time.sleep to avoid slow test execution
    with patch('app.worker.time.sleep'):
        # Execute the task directly (not via Celery queue)
        result = send_transaction_email(email, amount, status)
    
    # Verify result is a dictionary
    assert isinstance(result, dict), "Task must return a dictionary"
    
    # Verify success indicator is present and True
    assert "success" in result, "Result must contain 'success' key"
    assert result["success"] is True, "Success indicator must be True"
    
    # Verify other expected keys are present
    assert "message" in result, "Result must contain 'message' key"
    assert "task_id" in result, "Result must contain 'task_id' key"
    
    # Verify message is a non-empty string
    assert isinstance(result["message"], str), "Message must be a string"
    assert len(result["message"]) > 0, "Message must not be empty"


@settings(max_examples=100, deadline=None)
@given(
    transaction_id=transaction_id_strategy,
    data=transaction_data_strategy,
)
def test_audit_task_returns_success_indicator(
    transaction_id: str,
    data: dict,
) -> None:
    """
    **Feature: async-task-processing, Property 3: Task Success Return Value**
    
    *For any* successful audit task execution, the task SHALL return a dictionary
    containing a success indicator set to True.
    
    **Validates: Requirements 3.4**
    """
    # Mock time.sleep to avoid slow test execution
    with patch('app.worker.time.sleep'):
        # Execute the task directly (not via Celery queue)
        result = audit_log_transaction(transaction_id, data)
    
    # Verify result is a dictionary
    assert isinstance(result, dict), "Task must return a dictionary"
    
    # Verify success indicator is present and True
    assert "success" in result, "Result must contain 'success' key"
    assert result["success"] is True, "Success indicator must be True"
    
    # Verify other expected keys are present
    assert "message" in result, "Result must contain 'message' key"
    assert "task_id" in result, "Result must contain 'task_id' key"
    assert "transaction_id" in result, "Result must contain 'transaction_id' key"
    
    # Verify message is a non-empty string
    assert isinstance(result["message"], str), "Message must be a string"
    assert len(result["message"]) > 0, "Message must not be empty"
    
    # Verify transaction_id matches input
    assert result["transaction_id"] == transaction_id, "Returned transaction_id must match input"
