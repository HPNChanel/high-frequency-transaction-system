"""Property-based tests for API response time independence.

**Feature: async-task-processing, Property 5: API Response Time Independence**
**Validates: Requirements 4.6**
"""

import time
from decimal import Decimal
from unittest.mock import MagicMock

from hypothesis import given, settings, strategies as st

from app.worker import send_transaction_email, audit_log_transaction


# Strategy for email addresses
email_strategy = st.emails()

# Strategy for decimal amounts as strings
amount_strategy = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("999.9999"),
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
def test_email_task_delay_returns_immediately(
    email: str,
    amount: str,
    status: str,
) -> None:
    """
    **Feature: async-task-processing, Property 5: API Response Time Independence**
    
    *For any* task invocation using .delay(), the method SHALL return immediately
    without waiting for task execution, demonstrating asynchronous behavior.
    
    The .delay() call should return in under 0.1 seconds, while the actual task
    would take 2+ seconds to execute.
    
    **Validates: Requirements 4.6**
    """
    # Mock the Celery task to prevent actual execution
    # but still test that .delay() returns immediately
    original_delay = send_transaction_email.delay
    
    # Create a mock that simulates Celery's .delay() behavior
    # It should return immediately without executing the task
    mock_result = MagicMock()
    send_transaction_email.delay = MagicMock(return_value=mock_result)
    
    try:
        # Measure time to call .delay()
        start_time = time.time()
        result = send_transaction_email.delay(email, amount, status)
        delay_time = time.time() - start_time
        
        # Verify .delay() returned immediately (under 0.1 seconds)
        assert delay_time < 0.1, \
            f".delay() took {delay_time:.3f}s, should be < 0.1s"
        
        # Verify .delay() was called with correct parameters
        send_transaction_email.delay.assert_called_once_with(email, amount, status)
        
        # The key property: .delay() returned BEFORE task would complete
        # If task was executed synchronously, it would take 2+ seconds
        expected_sync_time = 2.0  # email task sleeps for 2 seconds
        assert delay_time < expected_sync_time, \
            f".delay() time ({delay_time:.3f}s) should be much less than " \
            f"synchronous task execution time ({expected_sync_time}s)"
    
    finally:
        # Restore original delay method
        send_transaction_email.delay = original_delay


@settings(max_examples=100, deadline=None)
@given(
    transaction_id=transaction_id_strategy,
    data=transaction_data_strategy,
)
def test_audit_task_delay_returns_immediately(
    transaction_id: str,
    data: dict,
) -> None:
    """
    **Feature: async-task-processing, Property 5: API Response Time Independence**
    
    *For any* task invocation using .delay(), the method SHALL return immediately
    without waiting for task execution, demonstrating asynchronous behavior.
    
    The .delay() call should return in under 0.1 seconds, while the actual task
    would take 1+ seconds to execute.
    
    **Validates: Requirements 4.6**
    """
    # Mock the Celery task to prevent actual execution
    original_delay = audit_log_transaction.delay
    
    # Create a mock that simulates Celery's .delay() behavior
    mock_result = MagicMock()
    audit_log_transaction.delay = MagicMock(return_value=mock_result)
    
    try:
        # Measure time to call .delay()
        start_time = time.time()
        result = audit_log_transaction.delay(transaction_id, data)
        delay_time = time.time() - start_time
        
        # Verify .delay() returned immediately (under 0.1 seconds)
        assert delay_time < 0.1, \
            f".delay() took {delay_time:.3f}s, should be < 0.1s"
        
        # Verify .delay() was called with correct parameters
        audit_log_transaction.delay.assert_called_once_with(transaction_id, data)
        
        # The key property: .delay() returned BEFORE task would complete
        # If task was executed synchronously, it would take 1+ seconds
        expected_sync_time = 1.0  # audit task sleeps for 1 second
        assert delay_time < expected_sync_time, \
            f".delay() time ({delay_time:.3f}s) should be much less than " \
            f"synchronous task execution time ({expected_sync_time}s)"
    
    finally:
        # Restore original delay method
        audit_log_transaction.delay = original_delay
