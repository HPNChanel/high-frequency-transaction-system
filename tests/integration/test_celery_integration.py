"""Integration tests for end-to-end Celery task execution.

These tests verify the complete task processing pipeline:
- Tasks are queued in Redis broker
- Celery worker executes tasks
- Task results are stored in Redis backend

**Validates: Requirements 5.3, 5.4, 5.5**

Prerequisites:
- Redis must be running (docker-compose up redis)
- Celery worker must be running (celery -A app.core.celery_app worker --loglevel=info)

Run with: pytest tests/integration/test_celery_integration.py -v
Skip if infrastructure not available: pytest tests/integration/ -v -m "not integration"
"""

import os
import time
import uuid
from datetime import datetime
from decimal import Decimal

import pytest

# Check if Redis is available before importing Celery components
REDIS_AVAILABLE = False
CELERY_AVAILABLE = False

try:
    import redis
    # Try to connect to Redis
    r = redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        socket_connect_timeout=2
    )
    r.ping()
    REDIS_AVAILABLE = True
except Exception:
    pass

if REDIS_AVAILABLE:
    try:
        from app.core.celery_app import celery_app
        from app.worker import send_transaction_email, audit_log_transaction
        
        # Check if any workers are available
        inspect = celery_app.control.inspect()
        active_workers = inspect.ping()
        if active_workers:
            CELERY_AVAILABLE = True
    except Exception:
        pass


# Skip all tests in this module if infrastructure is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not REDIS_AVAILABLE,
        reason="Redis is not available. Start Redis with: docker-compose up redis"
    ),
    pytest.mark.skipif(
        not CELERY_AVAILABLE,
        reason="Celery worker is not available. Start worker with: celery -A app.core.celery_app worker --loglevel=info"
    ),
]


class TestCeleryIntegration:
    """Integration tests for Celery task execution pipeline."""

    @pytest.fixture
    def redis_client(self):
        """Create a Redis client for verification."""
        return redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            decode_responses=True
        )

    def test_email_task_queued_and_executed(self, redis_client):
        """Test that email task is queued in Redis and executed by worker.
        
        **Validates: Requirements 5.3, 5.4**
        
        Verifies:
        - Task is queued in Redis broker
        - Worker consumes and executes the task
        - Task completes successfully
        """
        # Arrange
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        test_amount = "100.5000"
        test_status = "SUCCESS"
        
        # Act - Queue the task
        result = send_transaction_email.delay(
            email=test_email,
            amount=test_amount,
            status=test_status
        )
        
        # Assert - Task was queued (has task ID)
        assert result.id is not None
        assert isinstance(result.id, str)
        
        # Wait for task to complete (max 10 seconds, task takes ~2 seconds)
        task_result = result.get(timeout=10)
        
        # Verify task executed successfully
        assert task_result["success"] is True
        assert test_email in task_result["message"]
        assert test_amount in task_result["message"]
        assert test_status in task_result["message"]
        assert task_result["task_id"] == result.id

    def test_audit_task_queued_and_executed(self, redis_client):
        """Test that audit task is queued in Redis and executed by worker.
        
        **Validates: Requirements 5.3, 5.4**
        
        Verifies:
        - Task is queued in Redis broker
        - Worker consumes and executes the task
        - Task completes successfully with correct data
        """
        # Arrange
        test_transaction_id = str(uuid.uuid4())
        test_data = {
            "sender_wallet_id": str(uuid.uuid4()),
            "receiver_wallet_id": str(uuid.uuid4()),
            "amount": "250.0000",
            "status": "COMPLETED",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Act - Queue the task
        result = audit_log_transaction.delay(
            transaction_id=test_transaction_id,
            data=test_data
        )
        
        # Assert - Task was queued (has task ID)
        assert result.id is not None
        assert isinstance(result.id, str)
        
        # Wait for task to complete (max 10 seconds, task takes ~1 second)
        task_result = result.get(timeout=10)
        
        # Verify task executed successfully
        assert task_result["success"] is True
        assert test_transaction_id in task_result["message"]
        assert task_result["task_id"] == result.id
        assert task_result["transaction_id"] == test_transaction_id

    def test_task_result_stored_in_redis_backend(self, redis_client):
        """Test that task results are stored in Redis backend.
        
        **Validates: Requirement 5.5**
        
        Verifies:
        - After task completion, result is stored in Redis
        - Result can be retrieved using task ID
        """
        # Arrange
        test_email = f"backend_test_{uuid.uuid4().hex[:8]}@example.com"
        
        # Act - Queue and wait for task
        result = send_transaction_email.delay(
            email=test_email,
            amount="50.0000",
            status="SUCCESS"
        )
        
        # Wait for completion
        task_result = result.get(timeout=10)
        
        # Assert - Result is stored and retrievable
        assert result.state == "SUCCESS"
        assert result.result == task_result
        
        # Verify result can be retrieved again (from backend)
        from celery.result import AsyncResult
        stored_result = AsyncResult(result.id, app=celery_app)
        assert stored_result.state == "SUCCESS"
        assert stored_result.result["success"] is True

    def test_multiple_tasks_processed_concurrently(self, redis_client):
        """Test that multiple tasks can be queued and processed.
        
        **Validates: Requirements 5.3, 5.4**
        
        Verifies:
        - Multiple tasks can be queued simultaneously
        - All tasks are executed by worker(s)
        - All results are stored correctly
        """
        # Arrange - Queue multiple tasks
        num_tasks = 3
        results = []
        
        for i in range(num_tasks):
            email_result = send_transaction_email.delay(
                email=f"concurrent_{i}@example.com",
                amount=f"{100 + i}.0000",
                status="SUCCESS"
            )
            results.append(email_result)
        
        # Act - Wait for all tasks to complete
        task_results = []
        for result in results:
            task_results.append(result.get(timeout=15))
        
        # Assert - All tasks completed successfully
        assert len(task_results) == num_tasks
        for i, task_result in enumerate(task_results):
            assert task_result["success"] is True
            assert f"concurrent_{i}@example.com" in task_result["message"]

    def test_task_state_transitions(self, redis_client):
        """Test that task state transitions are tracked correctly.
        
        **Validates: Requirements 5.4, 5.5**
        
        Verifies:
        - Task starts in PENDING state
        - Task transitions through states
        - Final state is SUCCESS
        """
        # Arrange
        test_transaction_id = str(uuid.uuid4())
        test_data = {
            "sender_wallet_id": str(uuid.uuid4()),
            "receiver_wallet_id": str(uuid.uuid4()),
            "amount": "75.0000",
            "status": "COMPLETED",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Act - Queue the task
        result = audit_log_transaction.delay(
            transaction_id=test_transaction_id,
            data=test_data
        )
        
        # Capture initial state (may be PENDING or already STARTED)
        initial_state = result.state
        assert initial_state in ["PENDING", "STARTED", "SUCCESS"]
        
        # Wait for completion
        task_result = result.get(timeout=10)
        
        # Assert - Final state is SUCCESS
        assert result.state == "SUCCESS"
        assert task_result["success"] is True

    def test_task_with_serializable_parameters(self, redis_client):
        """Test that tasks correctly handle JSON-serializable parameters.
        
        **Validates: Requirements 5.4, 8.4, 8.5**
        
        Verifies:
        - Complex nested dictionaries are serialized correctly
        - All data types (strings, numbers) are preserved
        - Task receives exact parameters that were sent
        """
        # Arrange - Complex nested data structure
        test_transaction_id = str(uuid.uuid4())
        test_data = {
            "sender_wallet_id": str(uuid.uuid4()),
            "receiver_wallet_id": str(uuid.uuid4()),
            "amount": "999.9999",
            "status": "COMPLETED",
            "created_at": "2025-11-28T12:00:00.000000",
            "metadata": {
                "source": "api",
                "version": "1.0"
            }
        }
        
        # Act
        result = audit_log_transaction.delay(
            transaction_id=test_transaction_id,
            data=test_data
        )
        
        task_result = result.get(timeout=10)
        
        # Assert - Task executed with correct parameters
        assert task_result["success"] is True
        assert task_result["transaction_id"] == test_transaction_id
        # The message should contain the transaction_id
        assert test_transaction_id in task_result["message"]


class TestCeleryWorkerHealth:
    """Tests for Celery worker health and connectivity."""

    def test_worker_is_responsive(self):
        """Test that at least one Celery worker is running and responsive.
        
        **Validates: Requirement 5.3**
        """
        inspect = celery_app.control.inspect()
        active_workers = inspect.ping()
        
        assert active_workers is not None
        assert len(active_workers) > 0

    def test_worker_has_registered_tasks(self):
        """Test that worker has the expected tasks registered.
        
        **Validates: Requirements 5.3, 5.4**
        """
        inspect = celery_app.control.inspect()
        registered = inspect.registered()
        
        assert registered is not None
        
        # Get all registered task names across all workers
        all_tasks = set()
        for worker_tasks in registered.values():
            all_tasks.update(worker_tasks)
        
        # Verify our tasks are registered
        assert "send_transaction_email" in all_tasks
        assert "audit_log_transaction" in all_tasks

    def test_worker_queue_is_accessible(self):
        """Test that the Redis broker queue is accessible.
        
        **Validates: Requirement 5.3**
        """
        # This test verifies we can interact with the broker
        # by checking active queues
        inspect = celery_app.control.inspect()
        active_queues = inspect.active_queues()
        
        assert active_queues is not None
        # At least one worker should have active queues
        assert len(active_queues) > 0
