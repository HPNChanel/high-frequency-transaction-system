"""Wallet Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class WalletBase(BaseModel):
    """Base schema with common Wallet fields."""
    
    currency: str = Field(default="USD", max_length=3)


class WalletCreate(WalletBase):
    """Schema for creating a new Wallet."""
    
    user_id: uuid.UUID
    balance: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))


class WalletUpdate(BaseModel):
    """Schema for updating an existing Wallet.
    
    All fields are optional to allow partial updates.
    """
    
    balance: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    currency: Optional[str] = Field(default=None, max_length=3)


class WalletRead(WalletBase):
    """Schema for reading Wallet data.
    
    Balance is serialized as a decimal string for precision.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    user_id: uuid.UUID
    balance: Decimal
    version: int
    created_at: datetime
    updated_at: datetime
    
    @field_serializer("balance")
    def serialize_balance(self, balance: Decimal) -> str:
        """Serialize balance as decimal string to preserve precision."""
        return str(balance)
