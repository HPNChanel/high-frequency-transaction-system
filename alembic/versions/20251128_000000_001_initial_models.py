"""Initial models - User, Wallet, Transaction

Revision ID: 001
Revises: 
Create Date: 2025-11-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema for User, Wallet, and Transaction models."""
    
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    
    # Create wallets table
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("balance", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_wallets_user_id"),
        sa.UniqueConstraint("user_id", name="uq_wallets_user_id"),
    )
    
    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["sender_wallet_id"],
            ["wallets.id"],
            name="fk_transactions_sender_wallet_id",
        ),
        sa.ForeignKeyConstraint(
            ["receiver_wallet_id"],
            ["wallets.id"],
            name="fk_transactions_receiver_wallet_id",
        ),
    )
    op.create_index(
        "ix_transactions_sender_wallet_id",
        "transactions",
        ["sender_wallet_id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_receiver_wallet_id",
        "transactions",
        ["receiver_wallet_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_index("ix_transactions_receiver_wallet_id", table_name="transactions")
    op.drop_index("ix_transactions_sender_wallet_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("wallets")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
