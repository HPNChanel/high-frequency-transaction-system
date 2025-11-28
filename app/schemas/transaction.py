"""Transaction Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.transaction import TransactionStatus


class TransactionBase(BaseModel):
    """Base schema with common Transaction fields."""
    
    sender_wallet_id: uuid.UUID
    receiver_wallet_id: uuid.UUID
    amount: Decimal = Field(gt=Decimal("0"))


class TransactionCreate(TransactionBase):
    """Schema for creating a new Transaction."""
    
    pass


class TransactionRead(TransactionBase):
    """Schema for reading Transaction data.
    
    Amount is serialized as a decimal string for precision.
    Status is serialized as a string enum value.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    status: TransactionStatus
    created_at: datetime
    
    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        """Serialize amount as decimal string to preserve precision."""
        return str(amount)
    
    @field_serializer("status")
    def serialize_status(self, status: TransactionStatus) -> str:
        """Serialize status as string enum value."""
        return status.value
