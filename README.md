# High-Frequency Transaction System

A professional-grade fintech application demonstrating core banking functionality with high-frequency transaction processing capabilities. Built with FastAPI, PostgreSQL, and modern Python best practices.

## Overview

This project showcases a production-ready transaction system with:

- **User Management**: Secure authentication and user accounts
- **Digital Wallets**: High-precision balance tracking with optimistic locking
- **Transaction Processing**: Reliable fund transfers between wallets
- **Financial Precision**: DECIMAL(18,4) for accurate monetary calculations
- **Async Architecture**: Built on FastAPI and SQLAlchemy async for high performance
- **Property-Based Testing**: Comprehensive test coverage using Hypothesis

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL with asyncpg driver
- **ORM**: SQLAlchemy 2.0+ (async)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Authentication**: JWT with python-jose, bcrypt
- **Testing**: pytest, pytest-asyncio, Hypothesis
- **Code Quality**: Black, Ruff, mypy
- **Containerization**: Docker & Docker Compose

## Project Structure

```
.
├── app/
│   ├── api/              # API endpoints and routing
│   ├── core/             # Core configuration and utilities
│   ├── db/               # Database setup and session management
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic schemas for validation
│   ├── services/         # Business logic layer
│   └── main.py           # Application entry point
├── alembic/              # Database migrations
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── properties/       # Property-based tests (Hypothesis)
├── docker-compose.yml    # Docker services configuration
├── Dockerfile            # Application container
└── pyproject.toml        # Project metadata and dependencies
```

## Features

### Core Models

**User**
- UUID-based identification
- Email-based authentication with bcrypt password hashing
- Account status management
- Timestamps for audit trails

**Wallet**
- One-to-one relationship with User
- High-precision balance (DECIMAL 18,4)
- Multi-currency support (ISO codes)
- Optimistic locking with version control

**Transaction**
- Atomic fund transfers between wallets
- Status tracking (PENDING, COMPLETED, FAILED)
- Indexed for query performance
- Immutable transaction history

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd high-frequency-transaction-system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Running with Docker

Start all services (PostgreSQL, Redis, and optionally PgAdmin):

```bash
# Start core services
docker-compose up -d

# Include PgAdmin for database management
docker-compose --profile admin up -d
```

Services will be available at:
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- PgAdmin: `http://localhost:5050` (if using admin profile)

### Database Setup

Run migrations to create the database schema:

```bash
alembic upgrade head
```

### Running the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

The project includes comprehensive test coverage with three testing strategies:

### Run All Tests
```bash
pytest
```

### Run Specific Test Types
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Property-based tests (Hypothesis)
pytest tests/properties/
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

## Development

### Code Formatting
```bash
# Format code with Black
black .

# Lint with Ruff
ruff check .
```

### Type Checking
```bash
mypy app/
```

### Creating Database Migrations
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Configuration

Key environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |
| `POSTGRES_USER` | Database user | postgres |
| `POSTGRES_PASSWORD` | Database password | - |
| `POSTGRES_DB` | Database name | hfts_db |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `SECRET_KEY` | JWT secret key | - |
| `DEBUG` | Debug mode | false |

## Architecture Highlights

### Financial Precision
- Uses `DECIMAL(18,4)` for all monetary values
- Prevents floating-point arithmetic errors
- Supports up to 14 digits before decimal, 4 after

### Concurrency Control
- Optimistic locking on wallet balance updates
- Version field prevents lost updates
- Transaction isolation for data consistency

### Async Performance
- Fully async database operations with asyncpg
- Non-blocking I/O for high throughput
- Connection pooling for efficient resource usage

### Testing Strategy
- **Unit Tests**: Individual component validation
- **Integration Tests**: End-to-end API testing
- **Property-Based Tests**: Hypothesis for edge case discovery

## API Documentation

Once the application is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Contact

Developer - developer@example.com

Project Link: [https://github.com/yourusername/high-frequency-transaction-system](https://github.com/yourusername/high-frequency-transaction-system)
