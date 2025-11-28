"""Custom exception classes for the application.

Provides a hierarchy of exceptions for consistent error handling
across the application with appropriate HTTP status codes.
"""

from decimal import Decimal


class AppException(Exception):
    """Base application exception.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found exception.
    
    Raised when a requested resource does not exist.
    """
    
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource} with id {identifier} not found",
            status_code=404,
        )
        self.resource = resource
        self.identifier = identifier


class ConflictError(AppException):
    """Resource conflict exception.
    
    Raised when there's a conflict such as duplicate entries
    or version mismatch during optimistic locking.
    """
    
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=409)


class ValidationError(AppException):
    """Input validation failed exception.
    
    Raised when input data fails validation rules.
    """
    
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=422)


class InsufficientFundsError(AppException):
    """Insufficient wallet balance exception.
    
    Raised when a transaction cannot be completed due to
    insufficient funds in the source wallet.
    """
    
    def __init__(
        self,
        wallet_id: str,
        required: Decimal,
        available: Decimal,
    ) -> None:
        super().__init__(
            message=(
                f"Insufficient funds in wallet {wallet_id}: "
                f"required {required}, available {available}"
            ),
            status_code=400,
        )
        self.wallet_id = wallet_id
        self.required = required
        self.available = available


class ConcurrencyError(AppException):
    """Concurrent modification detected exception.
    
    Raised when optimistic locking detects that a resource was modified
    by another transaction between read and update operations.
    The caller should implement retry logic to handle this error.
    """
    
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            message=(
                f"{resource} {identifier} was modified by another transaction. "
                "Please retry."
            ),
            status_code=409,
        )
        self.resource = resource
        self.identifier = identifier
