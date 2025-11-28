# Requirements Document

## Introduction

This document specifies the requirements for a High-Frequency Transaction System (Core Banking Lite) - a portfolio project demonstrating professional-grade fintech architecture. The system provides user management, wallet operations, and transaction ledger functionality using Python 3.12+, FastAPI (async), PostgreSQL, SQLAlchemy (async), and Docker infrastructure.

## Glossary

- **System**: The High-Frequency Transaction System application
- **User**: An authenticated entity that owns a wallet and can perform transactions
- **Wallet**: A financial account associated with a user, storing balance in a specific currency
- **Transaction**: A transfer of funds between two wallets recorded in the ledger
- **Ledger**: The immutable record of all transactions in the system
- **Optimistic Locking**: A concurrency control mechanism using version numbers to detect conflicts
- **DECIMAL(18,4)**: A fixed-point numeric type with 18 total digits and 4 decimal places for financial precision

## Requirements

### Requirement 1: Project Structure

**User Story:** As a developer, I want a clean, scalable folder structure following Service-Repository Pattern, so that the codebase maintains separation of concerns and is easy to navigate.

#### Acceptance Criteria

1. WHEN the project is initialized THEN the System SHALL provide an `app/api` directory for routers and controllers
2. WHEN the project is initialized THEN the System SHALL provide an `app/core` directory for configuration, security, and exception handling
3. WHEN the project is initialized THEN the System SHALL provide an `app/db` directory for database connection and base models
4. WHEN the project is initialized THEN the System SHALL provide an `app/models` directory for SQLAlchemy ORM models
5. WHEN the project is initialized THEN the System SHALL provide an `app/schemas` directory for Pydantic data transfer objects
6. WHEN the project is initialized THEN the System SHALL provide an `app/services` directory for business logic

### Requirement 2: Docker Environment

**User Story:** As a developer, I want a Docker Compose environment with PostgreSQL, Redis, and PgAdmin, so that I can run the complete infrastructure locally with minimal setup.

#### Acceptance Criteria

1. WHEN Docker Compose is executed THEN the System SHALL start a PostgreSQL container using the latest version
2. WHEN Docker Compose is executed THEN the System SHALL start a Redis container for future caching and task queue support
3. WHEN Docker Compose is executed THEN the System SHALL optionally start a PgAdmin container for database administration
4. WHEN containers are started THEN the System SHALL load database credentials from environment variables defined in a `.env` file
5. WHEN PostgreSQL container starts THEN the System SHALL expose the database on a configurable port

### Requirement 3: Configuration Management

**User Story:** As a developer, I want centralized configuration using pydantic-settings, so that environment variables are validated and typed at application startup.

#### Acceptance Criteria

1. WHEN the application starts THEN the System SHALL load configuration from environment variables using pydantic-settings
2. WHEN configuration is loaded THEN the System SHALL validate all required database connection parameters
3. WHEN configuration is loaded THEN the System SHALL provide typed access to all environment variables
4. WHEN a required environment variable is missing THEN the System SHALL raise a validation error with a descriptive message

### Requirement 4: User Management

**User Story:** As a system administrator, I want to manage user accounts with standard fields, so that users can be authenticated and associated with wallets.

#### Acceptance Criteria

1. WHEN a User record is created THEN the System SHALL store id, email, hashed_password, full_name, and is_active fields
2. WHEN a User email is stored THEN the System SHALL enforce uniqueness at the database level
3. WHEN a User is created THEN the System SHALL set is_active to true by default
4. WHEN a User record is serialized THEN the System SHALL produce a JSON representation containing all non-sensitive fields
5. WHEN a User record is deserialized THEN the System SHALL reconstruct the User object with validated field types

### Requirement 5: Wallet Management

**User Story:** As a user, I want a wallet associated with my account that stores my balance with financial precision, so that I can send and receive funds accurately.

#### Acceptance Criteria

1. WHEN a Wallet is created THEN the System SHALL establish a one-to-one relationship with a User
2. WHEN a Wallet balance is stored THEN the System SHALL use DECIMAL(18,4) data type for financial precision
3. WHEN a Wallet is created THEN the System SHALL set the balance to 0.0000 by default
4. WHEN a Wallet is created THEN the System SHALL set the currency to a configurable default (USD or VND)
5. WHEN a Wallet is created THEN the System SHALL initialize a version field to 1 for optimistic locking
6. WHEN a Wallet record is serialized THEN the System SHALL produce a JSON representation with balance as a decimal string
7. WHEN a Wallet record is deserialized THEN the System SHALL reconstruct the Wallet object preserving decimal precision

### Requirement 6: Transaction Ledger

**User Story:** As a user, I want all fund transfers recorded in an immutable ledger, so that I have a complete audit trail of my financial activity.

#### Acceptance Criteria

1. WHEN a Transaction is created THEN the System SHALL generate a unique identifier (UUID or BigInteger)
2. WHEN a Transaction is created THEN the System SHALL record sender_wallet_id as a foreign key to Wallets
3. WHEN a Transaction is created THEN the System SHALL record receiver_wallet_id as a foreign key to Wallets
4. WHEN a Transaction amount is stored THEN the System SHALL use DECIMAL(18,4) data type
5. WHEN a Transaction is created THEN the System SHALL set status to one of: PENDING, COMPLETED, or FAILED
6. WHEN a Transaction is created THEN the System SHALL record created_at timestamp automatically
7. WHEN transactions are queried by wallet THEN the System SHALL use database indexes on sender_wallet_id and receiver_wallet_id for performance
8. WHEN a Transaction record is serialized THEN the System SHALL produce a JSON representation with amount as a decimal string and status as a string enum value
9. WHEN a Transaction record is deserialized THEN the System SHALL reconstruct the Transaction object with validated enum status and decimal amount

### Requirement 7: Database Connection

**User Story:** As a developer, I want an async database connection using SQLAlchemy, so that the application can handle high-frequency operations efficiently.

#### Acceptance Criteria

1. WHEN the application starts THEN the System SHALL establish an async database connection using SQLAlchemy async engine
2. WHEN database sessions are requested THEN the System SHALL provide async session management with proper cleanup
3. WHEN the database URL is constructed THEN the System SHALL use the asyncpg driver for PostgreSQL
4. WHEN database models are defined THEN the System SHALL use a declarative base class for inheritance

### Requirement 8: Fund Transfer Operations

**User Story:** As a user, I want to transfer funds between wallets with ACID guarantees, so that my transactions are reliable and my balance is always accurate.

#### Acceptance Criteria

1. WHEN a fund transfer is initiated THEN the System SHALL execute all operations within a single atomic database transaction
2. WHEN a fund transfer is requested with a non-existent sender wallet THEN the System SHALL raise a NotFoundError
3. WHEN a fund transfer is requested with a non-existent receiver wallet THEN the System SHALL raise a NotFoundError
4. WHEN a fund transfer is requested where sender and receiver are identical THEN the System SHALL raise a ValidationError
5. WHEN a fund transfer is requested with an amount less than or equal to zero THEN the System SHALL raise a ValidationError
6. WHEN a fund transfer is requested with an amount greater than sender balance THEN the System SHALL raise an InsufficientFundsError
7. WHEN a valid fund transfer is executed THEN the System SHALL deduct the amount from the sender wallet balance
8. WHEN a valid fund transfer is executed THEN the System SHALL add the amount to the receiver wallet balance
9. WHEN a valid fund transfer is executed THEN the System SHALL create a Transaction record with status COMPLETED
10. WHEN any validation or execution step fails THEN the System SHALL rollback all changes and leave wallet balances unchanged

### Requirement 9: Transfer API Endpoint

**User Story:** As a client application, I want a REST API endpoint to initiate fund transfers, so that I can integrate transaction functionality into my application.

#### Acceptance Criteria

1. WHEN a POST request is made to the transfer endpoint THEN the System SHALL accept sender_wallet_id, receiver_wallet_id, and amount as input
2. WHEN a transfer request is successfully processed THEN the System SHALL return HTTP 200 with the created Transaction object
3. WHEN a transfer request fails due to validation errors THEN the System SHALL return HTTP 400 with error details
4. WHEN a transfer request fails due to non-existent wallet THEN the System SHALL return HTTP 404 with error details
5. WHEN a transfer request fails due to any error THEN the System SHALL return a JSON response with error type, message, and status code
