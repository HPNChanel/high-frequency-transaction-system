"""Unit tests for API integration with Celery tasks.

Tests that the transfer API endpoint correctly queues background tasks
on successful transfers and does NOT queue tasks on failed transfers.

**Validates: Requirements 4.3, 4.4, 4.7**
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.transactions import transfer_funds
from app.core.exceptions import InsufficientFundsError, NotFoundError, ValidationError
from app.schemas.transaction import TransferRequest


class TestAPITaskIntegration:
    """Tests for API endpoint task queuing behavior."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        session = AsyncMock()
        session.begin = MagicMock(return_value=AsyncMock())
        session.begin.return_value.__aenter__ = AsyncMock()
        session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def mock_transaction(self) -> MagicMock:
        """Create a mock transaction object."""
        transaction = MagicMock()
        transaction.id = uuid.uuid4()
        transaction.sender_wallet_id = uuid.uuid4()
        transaction.receiver_wallet_id = uuid.uuid4()
        transaction.amount = Decimal("100.0000")
        transaction.status = MagicMock()
        transaction.status.value = "COMPLETED"
        transaction.created_at = MagicMock()
        transaction.created_at.isoformat = MagicMock(return_value="2025-11-28T10:00:00")
        return transaction

    @pytest.fixture
    def transfer_request(self) -> TransferRequest:
        """Create a transfer request."""
        return TransferRequest(
            sender_wallet_id=uuid.uuid4(),
            receiver_wallet_id=uuid.uuid4(),
            amount=Decimal("100.0000"),
        )


    @pytest.mark.asyncio
    async def test_successful_transfer_queues_email_task(
        self,
        mock_session: AsyncMock,
        mock_transaction: MagicMock,
        transfer_request: TransferRequest,
    ) -> None:
        """Test that successful transfer queues email notification task.
        
        **Validates: Requirement 4.3**
        """
        with patch(
            "app.api.v1.transactions.TransactionService"
        ) as mock_service_class, patch(
            "app.api.v1.transactions.send_transaction_email"
        ) as mock_email_task, patch(
            "app.api.v1.transactions.audit_log_transaction"
        ) as mock_audit_task:
            # Setup mock service
            mock_service = mock_service_class.return_value
            mock_service.transfer_funds = AsyncMock(return_value=mock_transaction)
            
            # Execute transfer
            await transfer_funds(transfer_request, mock_session)
            
            # Verify email task was queued using .delay()
            mock_email_task.delay.assert_called_once()
            
            # Verify correct parameters
            call_kwargs = mock_email_task.delay.call_args
            assert call_kwargs.kwargs["email"] == "user@example.com"
            assert call_kwargs.kwargs["amount"] == str(mock_transaction.amount)
            assert call_kwargs.kwargs["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_successful_transfer_queues_audit_task(
        self,
        mock_session: AsyncMock,
        mock_transaction: MagicMock,
        transfer_request: TransferRequest,
    ) -> None:
        """Test that successful transfer queues audit log task.
        
        **Validates: Requirement 4.4**
        """
        with patch(
            "app.api.v1.transactions.TransactionService"
        ) as mock_service_class, patch(
            "app.api.v1.transactions.send_transaction_email"
        ) as mock_email_task, patch(
            "app.api.v1.transactions.audit_log_transaction"
        ) as mock_audit_task:
            # Setup mock service
            mock_service = mock_service_class.return_value
            mock_service.transfer_funds = AsyncMock(return_value=mock_transaction)
            
            # Execute transfer
            await transfer_funds(transfer_request, mock_session)
            
            # Verify audit task was queued using .delay()
            mock_audit_task.delay.assert_called_once()
            
            # Verify correct parameters
            call_kwargs = mock_audit_task.delay.call_args
            assert call_kwargs.kwargs["transaction_id"] == str(mock_transaction.id)
            assert "sender_wallet_id" in call_kwargs.kwargs["data"]
            assert "receiver_wallet_id" in call_kwargs.kwargs["data"]
            assert "amount" in call_kwargs.kwargs["data"]
            assert "status" in call_kwargs.kwargs["data"]
            assert "created_at" in call_kwargs.kwargs["data"]


    @pytest.mark.asyncio
    async def test_failed_transfer_not_found_does_not_queue_tasks(
        self,
        mock_session: AsyncMock,
        transfer_request: TransferRequest,
    ) -> None:
        """Test that failed transfer (wallet not found) does NOT queue any tasks.
        
        **Validates: Requirement 4.7**
        """
        with patch(
            "app.api.v1.transactions.TransactionService"
        ) as mock_service_class, patch(
            "app.api.v1.transactions.send_transaction_email"
        ) as mock_email_task, patch(
            "app.api.v1.transactions.audit_log_transaction"
        ) as mock_audit_task:
            # Setup mock service to raise NotFoundError
            mock_service = mock_service_class.return_value
            mock_service.transfer_funds = AsyncMock(
                side_effect=NotFoundError("Wallet", str(transfer_request.sender_wallet_id))
            )
            
            # Execute transfer - should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await transfer_funds(transfer_request, mock_session)
            
            assert exc_info.value.status_code == 404
            
            # Verify NO tasks were queued
            mock_email_task.delay.assert_not_called()
            mock_audit_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_transfer_insufficient_funds_does_not_queue_tasks(
        self,
        mock_session: AsyncMock,
        transfer_request: TransferRequest,
    ) -> None:
        """Test that failed transfer (insufficient funds) does NOT queue any tasks.
        
        **Validates: Requirement 4.7**
        """
        with patch(
            "app.api.v1.transactions.TransactionService"
        ) as mock_service_class, patch(
            "app.api.v1.transactions.send_transaction_email"
        ) as mock_email_task, patch(
            "app.api.v1.transactions.audit_log_transaction"
        ) as mock_audit_task:
            # Setup mock service to raise InsufficientFundsError
            mock_service = mock_service_class.return_value
            mock_service.transfer_funds = AsyncMock(
                side_effect=InsufficientFundsError(
                    str(transfer_request.sender_wallet_id),
                    Decimal("100.0000"),
                    Decimal("50.0000"),
                )
            )
            
            # Execute transfer - should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await transfer_funds(transfer_request, mock_session)
            
            assert exc_info.value.status_code == 400
            
            # Verify NO tasks were queued
            mock_email_task.delay.assert_not_called()
            mock_audit_task.delay.assert_not_called()


    @pytest.mark.asyncio
    async def test_failed_transfer_validation_error_does_not_queue_tasks(
        self,
        mock_session: AsyncMock,
        transfer_request: TransferRequest,
    ) -> None:
        """Test that failed transfer (validation error) does NOT queue any tasks.
        
        **Validates: Requirement 4.7**
        """
        with patch(
            "app.api.v1.transactions.TransactionService"
        ) as mock_service_class, patch(
            "app.api.v1.transactions.send_transaction_email"
        ) as mock_email_task, patch(
            "app.api.v1.transactions.audit_log_transaction"
        ) as mock_audit_task:
            # Setup mock service to raise ValidationError
            mock_service = mock_service_class.return_value
            mock_service.transfer_funds = AsyncMock(
                side_effect=ValidationError("Cannot transfer funds to the same wallet")
            )
            
            # Execute transfer - should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await transfer_funds(transfer_request, mock_session)
            
            assert exc_info.value.status_code == 400
            
            # Verify NO tasks were queued
            mock_email_task.delay.assert_not_called()
            mock_audit_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_tasks_use_delay_method_not_direct_call(
        self,
        mock_session: AsyncMock,
        mock_transaction: MagicMock,
        transfer_request: TransferRequest,
    ) -> None:
        """Test that tasks are invoked using .delay() method for async execution.
        
        **Validates: Requirement 4.3, 4.4**
        """
        with patch(
            "app.api.v1.transactions.TransactionService"
        ) as mock_service_class, patch(
            "app.api.v1.transactions.send_transaction_email"
        ) as mock_email_task, patch(
            "app.api.v1.transactions.audit_log_transaction"
        ) as mock_audit_task:
            # Setup mock service
            mock_service = mock_service_class.return_value
            mock_service.transfer_funds = AsyncMock(return_value=mock_transaction)
            
            # Execute transfer
            await transfer_funds(transfer_request, mock_session)
            
            # Verify .delay() was called (not direct function call)
            # If direct call was used, the mock itself would be called, not .delay
            mock_email_task.delay.assert_called_once()
            mock_audit_task.delay.assert_called_once()
            
            # Verify the task functions themselves were NOT called directly
            mock_email_task.assert_not_called()
            mock_audit_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_audit_task_receives_correct_transaction_data(
        self,
        mock_session: AsyncMock,
        mock_transaction: MagicMock,
        transfer_request: TransferRequest,
    ) -> None:
        """Test that audit task receives complete transaction data dictionary.
        
        **Validates: Requirement 4.4**
        """
        with patch(
            "app.api.v1.transactions.TransactionService"
        ) as mock_service_class, patch(
            "app.api.v1.transactions.send_transaction_email"
        ), patch(
            "app.api.v1.transactions.audit_log_transaction"
        ) as mock_audit_task:
            # Setup mock service
            mock_service = mock_service_class.return_value
            mock_service.transfer_funds = AsyncMock(return_value=mock_transaction)
            
            # Execute transfer
            await transfer_funds(transfer_request, mock_session)
            
            # Verify audit task data structure
            call_kwargs = mock_audit_task.delay.call_args
            data = call_kwargs.kwargs["data"]
            
            # Verify all required fields are present and correct
            assert data["sender_wallet_id"] == str(mock_transaction.sender_wallet_id)
            assert data["receiver_wallet_id"] == str(mock_transaction.receiver_wallet_id)
            assert data["amount"] == str(mock_transaction.amount)
            assert data["status"] == mock_transaction.status.value
            assert data["created_at"] == mock_transaction.created_at.isoformat()


    @pytest.mark.asyncio
    async def test_unexpected_error_does_not_queue_tasks(
        self,
        mock_session: AsyncMock,
        transfer_request: TransferRequest,
    ) -> None:
        """Test that unexpected errors do NOT queue any tasks.
        
        **Validates: Requirement 4.7**
        """
        with patch(
            "app.api.v1.transactions.TransactionService"
        ) as mock_service_class, patch(
            "app.api.v1.transactions.send_transaction_email"
        ) as mock_email_task, patch(
            "app.api.v1.transactions.audit_log_transaction"
        ) as mock_audit_task:
            # Setup mock service to raise unexpected error
            mock_service = mock_service_class.return_value
            mock_service.transfer_funds = AsyncMock(
                side_effect=RuntimeError("Database connection lost")
            )
            
            # Execute transfer - should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await transfer_funds(transfer_request, mock_session)
            
            assert exc_info.value.status_code == 500
            
            # Verify NO tasks were queued
            mock_email_task.delay.assert_not_called()
            mock_audit_task.delay.assert_not_called()
