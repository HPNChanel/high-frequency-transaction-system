# Implementation Plan

- [x] 1. Update configuration for Celery settings




  - Add `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` settings to `app/core/config.py`
  - Add computed properties `celery_broker_url` and `celery_result_backend` that construct URLs from Redis settings
  - Ensure settings use environment variables with sensible defaults
  - _Requirements: 1.2, 1.3, 7.1, 7.2_

- [x] 2. Create Celery application instance





  - Create `app/core/celery_app.py` with Celery instance initialization
  - Configure Celery with broker URL, result backend URL from settings
  - Set task serialization to JSON, result serialization to JSON
  - Configure accept_content to include JSON
  - Set timezone to UTC and enable UTC
  - Configure task tracking, time limits, and result expiration
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 3. Define background task functions





- [x] 3.1 Implement email notification task


  - Create `app/worker.py` file
  - Define `send_transaction_email` task with `@celery_app.task` decorator
  - Accept parameters: email (str), amount (str), status (str)
  - Implement 2-second sleep to simulate SMTP delay
  - Log message containing email, amount, and status
  - Return dictionary with success indicator, message, and task_id
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3.2 Implement audit log task

  - Define `audit_log_transaction` task with `@celery_app.task` decorator
  - Accept parameters: transaction_id (str), data (dict)
  - Implement 1-second sleep to simulate audit system write
  - Log message containing transaction_id and data
  - Return dictionary with success indicator, message, task_id, and transaction_id
  - _Requirements: 3.1, 3.2, 3.3, 3.4_


- [x] 3.3 Write property test for task logging

  - **Property 2: Task Logging Contains Input Parameters**
  - **Validates: Requirements 2.3, 3.3**

- [x] 3.4 Write property test for task return values


  - **Property 3: Task Success Return Value**
  - **Validates: Requirements 2.4, 3.4**

- [x] 4. Integrate tasks with transfer API endpoint





  - Update `app/api/v1/transactions.py` to import task functions
  - Modify `transfer_funds` endpoint to queue tasks AFTER transaction commits
  - Ensure tasks are queued outside the `async with session.begin()` block
  - Queue `send_transaction_email.delay()` with transaction amount and "SUCCESS" status
  - Queue `audit_log_transaction.delay()` with transaction ID and serialized transaction data
  - Ensure tasks are NOT queued when transfer fails (only queue on success)
  - Pass only serializable data to tasks (strings, dicts) - no ORM objects
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 4.7, 8.4, 8.5_

- [x] 4.1 Write property test for task parameter serializability


  - **Property 4: Task Parameter Serializability**
  - **Validates: Requirements 8.4, 8.5**

- [x] 4.2 Write property test for API response time independence


  - **Property 5: API Response Time Independence**
  - **Validates: Requirements 4.6**

- [x] 5. Update Docker Compose configuration




  - Add `celery_worker` service to `docker-compose.yml`
  - Set command to `celery -A app.core.celery_app worker --loglevel=info`
  - Configure service to depend on `postgres` and `redis` health checks
  - Share same volumes as `web` service (mount codebase)
  - Load same environment variables via `env_file`
  - Set environment variables for `POSTGRES_HOST=postgres` and `REDIS_HOST=redis`
  - Configure restart policy to `unless-stopped`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 6. Update dependencies





  - Add `celery[redis]>=5.3.0` to `requirements.txt`
  - Add `redis>=5.0.0` to `requirements.txt` (if not already present)
  - Document Celery version and Redis version requirements
  - _Requirements: 1.1_

- [x] 7. Write unit tests for Celery configuration





  - Test Celery instance initialization
  - Test configuration loading from environment variables
  - Test broker URL and backend URL construction
  - Test serialization settings
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 7.1 Write property test for Celery configuration from environment


  - **Property 1: Celery Configuration from Environment**
  - **Validates: Requirements 1.2, 1.3, 7.3, 7.4**

- [x] 8. Write unit tests for task functions





  - Test email task accepts correct parameters
  - Test email task execution time (>= 2 seconds)
  - Test audit task accepts correct parameters
  - Test audit task execution time (>= 1 second)
  - Test task return value structure
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

- [x] 9. Write unit tests for API integration





  - Test API endpoint queues tasks on successful transfer (mock tasks)
  - Test API endpoint does NOT queue tasks on failed transfer
  - Test tasks are called with correct parameters
  - Test .delay() is used (not direct call)
  - _Requirements: 4.3, 4.4, 4.7_

- [x] 10. Write integration tests for end-to-end task execution





  - Start Redis container
  - Start Celery worker
  - Execute API transfer request
  - Verify tasks are queued in Redis
  - Verify tasks are executed by worker
  - Verify task results are stored in Redis backend
  - _Requirements: 5.3, 5.4, 5.5_

- [x] 11. Update documentation





  - Add Celery setup instructions to README
  - Document how to start Celery worker locally
  - Document environment variables for Celery
  - Add examples of monitoring task execution
  - Document task retry configuration
  - _Requirements: All_

- [x] 12. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.
