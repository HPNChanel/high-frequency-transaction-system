"""Property-based tests for task logging.

**Feature: async-task-processing, Property 2: Task Logging Contains Input Parameters**
**Validates: Requirements 2.3, 3.3**
"""

import uuid
from decimal import Decimal
from io import StringIO
import sys
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
def test_email_task_logging_contains_input_parameters(
    email: str,
    amount: str,
    status: str,
) -> None:
    """
    **Feature: async-task-processing, Property 2: Task Logging Contains Input Parameters**
    
    *For any* email task invocation with input parameters, the logged message
    SHALL contain all input parameter values (email, amount, status).
    
    **Validates: Requirements 2.3**
    """
    # Capture stdout to verify logging
    captured_output = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    try:
        # Mock time.sleep to avoid slow test execution
        with patch('app.worker.time.sleep'):
            # Execute the task directly (not via Celery queue)
            # This calls the task function synchronously for testing
            result = send_transaction_email(email, amount, status)
        
        # Get the logged output
        log_output = captured_output.getvalue()
        
        # Verify all input parameters are present in the log
        assert email in log_output, f"Email '{email}' not found in log output"
        assert amount in log_output, f"Amount '{amount}' not found in log output"
        assert status in log_output, f"Status '{status}' not found in log output"
        
        # Verify the message is also in the return value
        assert email in result["message"]
        assert amount in result["message"]
        assert status in result["message"]
        
    finally:
        # Restore stdout
        sys.stdout = old_stdout


@settings(max_examples=100, deadline=None)
@given(
    transaction_id=transaction_id_strategy,
    data=transaction_data_strategy,
)
def test_audit_task_logging_contains_input_parameters(
    transaction_id: str,
    data: dict,
) -> None:
    """
    **Feature: async-task-processing, Property 2: Task Logging Contains Input Parameters**
    
    *For any* audit task invocation with input parameters, the logged message
    SHALL contain all input parameter values (transaction_id and data).
    
    **Validates: Requirements 3.3**
    """
    # Capture stdout to verify logging
    captured_output = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    try:
        # Mock time.sleep to avoid slow test execution
        with patch('app.worker.time.sleep'):
            # Execute the task directly (not via Celery queue)
            result = audit_log_transaction(transaction_id, data)
        
        # Get the logged output
        log_output = captured_output.getvalue()
        
        # Verify transaction_id is present in the log
        assert transaction_id in log_output, f"Transaction ID '{transaction_id}' not found in log output"
        
        # Verify key data elements are present in the log
        # The data dict is converted to string in the log, so check for key values
        assert data["sender_wallet_id"] in log_output, "Sender wallet ID not found in log output"
        assert data["receiver_wallet_id"] in log_output, "Receiver wallet ID not found in log output"
        assert data["amount"] in log_output, "Amount not found in log output"
        
        # Verify the message contains transaction_id
        assert transaction_id in result["message"]
        
    finally:
        # Restore stdout
        sys.stdout = old_stdout
