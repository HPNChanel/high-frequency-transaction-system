"""Wallet SQLAlchemy ORM model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Wallet(Base):
    """Wallet model for storing user balance with financial precision.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to User (unique, one-to-one)
        balance: Current balance with DECIMAL(18,4) precision
        currency: ISO currency code (default: USD)
        version: Optimistic locking version number
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
        user: Relationship to User model
    """
    
    __tablename__ = "wallets"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000")
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD"
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # One-to-one relationship with User
    user: Mapped["User"] = relationship("User", back_populates="wallet")
