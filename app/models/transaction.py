"""Transaction SQLAlchemy ORM model."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TransactionStatus(str, enum.Enum):
    """Transaction status enum.
    
    Values:
        PENDING: Transaction is awaiting processing
        COMPLETED: Transaction has been successfully processed
        FAILED: Transaction processing failed
    """
    
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Transaction(Base):
    """Transaction model for recording fund transfers between wallets.
    
    Attributes:
        id: Unique identifier (UUID)
        sender_wallet_id: Foreign key to sender's Wallet
        receiver_wallet_id: Foreign key to receiver's Wallet
        amount: Transfer amount with DECIMAL(18,4) precision
        status: Transaction status (PENDING, COMPLETED, FAILED)
        created_at: Transaction timestamp
    """
    
    __tablename__ = "transactions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    sender_wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.id"),
        nullable=False
    )
    receiver_wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.id"),
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        String(20),
        nullable=False,
        default=TransactionStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    sender_wallet: Mapped["Wallet"] = relationship(
        "Wallet",
        foreign_keys=[sender_wallet_id],
        backref="sent_transactions"
    )
    receiver_wallet: Mapped["Wallet"] = relationship(
        "Wallet",
        foreign_keys=[receiver_wallet_id],
        backref="received_transactions"
    )
    
    # Composite indexes for query performance
    __table_args__ = (
        Index("ix_transactions_sender_wallet_id", "sender_wallet_id"),
        Index("ix_transactions_receiver_wallet_id", "receiver_wallet_id"),
    )
