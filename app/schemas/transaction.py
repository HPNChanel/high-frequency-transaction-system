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


class TransferRequest(BaseModel):
    """Request schema for fund transfer."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sender_wallet_id": "123e4567-e89b-12d3-a456-426614174000",
                "receiver_wallet_id": "123e4567-e89b-12d3-a456-426614174001",
                "amount": "100.5000"
            }
        }
    )
    
    sender_wallet_id: uuid.UUID = Field(..., description="Source wallet UUID")
    receiver_wallet_id: uuid.UUID = Field(..., description="Destination wallet UUID")
    amount: Decimal = Field(..., gt=0, decimal_places=4, description="Transfer amount")
