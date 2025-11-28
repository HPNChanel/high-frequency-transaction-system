"""Unit tests for Celery task functions.

Tests email notification task and audit log task for correct parameter handling,
execution time, and return value structure.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4**
"""

import time

import pytest


class TestEmailNotificationTask:
    """Tests for send_transaction_email task (Requirements 2.1-2.4)."""

    def test_email_task_accepts_correct_parameters(self) -> None:
        """Test that email task accepts email, amount, and status as string parameters.
        
        **Validates: Requirement 2.1**
        """
        from app.worker import send_transaction_email
        
        # Call the task synchronously using .run() which bypasses Celery context
        result = send_transaction_email.run(
            email="user@example.com",
            amount="100.5000",
            status="SUCCESS"
        )
        
        # If we get here without error, parameters were accepted
        assert result is not None

    def test_email_task_execution_time_minimum_2_seconds(self) -> None:
        """Test that email task simulates SMTP delay of at least 2 seconds.
        
        **Validates: Requirement 2.2**
        """
        from app.worker import send_transaction_email
        
        start_time = time.time()
        send_transaction_email.run(
            email="test@example.com",
            amount="50.0000",
            status="SUCCESS"
        )
        elapsed_time = time.time() - start_time
        
        assert elapsed_time >= 2.0, (
            f"Expected execution time >= 2 seconds, got {elapsed_time:.2f} seconds"
        )

    def test_email_task_returns_success_indicator(self) -> None:
        """Test that email task returns a success indicator.
        
        **Validates: Requirement 2.4**
        """
        from app.worker import send_transaction_email
        
        result = send_transaction_email.run(
            email="user@example.com",
            amount="200.0000",
            status="SUCCESS"
        )
        
        assert "success" in result
        assert result["success"] is True

    def test_email_task_return_value_structure(self) -> None:
        """Test that email task returns dictionary with expected keys.
        
        **Validates: Requirement 2.4**
        """
        from app.worker import send_transaction_email
        
        result = send_transaction_email.run(
            email="structure@example.com",
            amount="300.0000",
            status="FAILED"
        )
        
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert "task_id" in result


class TestAuditLogTask:
    """Tests for audit_log_transaction task (Requirements 3.1-3.4)."""

    def test_audit_task_accepts_correct_parameters(self) -> None:
        """Test that audit task accepts transaction_id and data dictionary.
        
        **Validates: Requirement 3.1**
        """
        from app.worker import audit_log_transaction
        
        transaction_data = {
            "sender_wallet_id": "uuid-sender-123",
            "receiver_wallet_id": "uuid-receiver-456",
            "amount": "150.0000",
            "status": "COMPLETED",
            "created_at": "2025-11-28T10:00:00"
        }
        
        result = audit_log_transaction.run(
            transaction_id="txn-uuid-789",
            data=transaction_data
        )
        
        # If we get here without error, parameters were accepted
        assert result is not None

    def test_audit_task_execution_time_minimum_1_second(self) -> None:
        """Test that audit task simulates audit system delay of at least 1 second.
        
        **Validates: Requirement 3.2**
        """
        from app.worker import audit_log_transaction
        
        transaction_data = {
            "sender_wallet_id": "uuid-sender",
            "receiver_wallet_id": "uuid-receiver",
            "amount": "75.0000",
            "status": "COMPLETED",
            "created_at": "2025-11-28T11:00:00"
        }
        
        start_time = time.time()
        audit_log_transaction.run(
            transaction_id="txn-uuid-timing",
            data=transaction_data
        )
        elapsed_time = time.time() - start_time
        
        assert elapsed_time >= 1.0, (
            f"Expected execution time >= 1 second, got {elapsed_time:.2f} seconds"
        )

    def test_audit_task_returns_success_indicator(self) -> None:
        """Test that audit task returns a success indicator.
        
        **Validates: Requirement 3.4**
        """
        from app.worker import audit_log_transaction
        
        transaction_data = {
            "sender_wallet_id": "uuid-sender",
            "receiver_wallet_id": "uuid-receiver",
            "amount": "500.0000",
            "status": "COMPLETED",
            "created_at": "2025-11-28T12:00:00"
        }
        
        result = audit_log_transaction.run(
            transaction_id="txn-uuid-success",
            data=transaction_data
        )
        
        assert "success" in result
        assert result["success"] is True

    def test_audit_task_return_value_structure(self) -> None:
        """Test that audit task returns dictionary with expected keys.
        
        **Validates: Requirement 3.4**
        """
        from app.worker import audit_log_transaction
        
        transaction_data = {
            "sender_wallet_id": "uuid-sender",
            "receiver_wallet_id": "uuid-receiver",
            "amount": "1000.0000",
            "status": "PENDING",
            "created_at": "2025-11-28T13:00:00"
        }
        
        result = audit_log_transaction.run(
            transaction_id="txn-uuid-structure",
            data=transaction_data
        )
        
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert "task_id" in result
        assert "transaction_id" in result

    def test_audit_task_returns_transaction_id(self) -> None:
        """Test that audit task returns the transaction_id in result.
        
        **Validates: Requirement 3.4**
        """
        from app.worker import audit_log_transaction
        
        transaction_data = {
            "sender_wallet_id": "uuid-sender",
            "receiver_wallet_id": "uuid-receiver",
            "amount": "250.0000",
            "status": "COMPLETED",
            "created_at": "2025-11-28T14:00:00"
        }
        
        expected_txn_id = "txn-uuid-return-check"
        result = audit_log_transaction.run(
            transaction_id=expected_txn_id,
            data=transaction_data
        )
        
        assert result["transaction_id"] == expected_txn_id
