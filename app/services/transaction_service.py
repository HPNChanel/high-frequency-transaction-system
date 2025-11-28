"""Transaction service for handling fund transfer operations."""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InsufficientFundsError,
    NotFoundError,
    ValidationError,
)
from app.models.transaction import Transaction, TransactionStatus
from app.models.wallet import Wallet


class TransactionService:
    """Service for handling fund transfer operations with ACID guarantees.
    
    This service provides business logic for transferring funds between wallets
    with comprehensive validation and atomic transaction management.
    """
    
    async def transfer_funds(
        self,
        session: AsyncSession,
        sender_wallet_id: uuid.UUID,
        receiver_wallet_id: uuid.UUID,
        amount: Decimal,
    ) -> Transaction:
        """Transfer funds between two wallets with ACID guarantees.
        
        This method executes within a database transaction context.
        All operations either complete successfully or roll back entirely.
        
        The transfer process follows these steps:
        1. Validate amount is positive
        2. Lock and verify sender wallet exists
        3. Lock and verify receiver wallet exists
        4. Validate sender and receiver are different
        5. Validate sender has sufficient funds
        6. Deduct amount from sender balance
        7. Add amount to receiver balance
        8. Create transaction record with COMPLETED status
        
        Row-level locking (with_for_update) prevents concurrent modifications
        to wallet balances, ensuring consistency in high-frequency scenarios.
        
        Args:
            session: Active async database session (transaction managed by caller)
            sender_wallet_id: UUID of the sending wallet
            receiver_wallet_id: UUID of the receiving wallet
            amount: Amount to transfer (DECIMAL 18,4)
            
        Returns:
            Transaction: The completed transaction record
            
        Raises:
            ValidationError: If amount <= 0 or sender == receiver
            NotFoundError: If sender or receiver wallet doesn't exist
            InsufficientFundsError: If sender balance < amount
            
        Example:
            async with session.begin():
                service = TransactionService()
                transaction = await service.transfer_funds(
                    session=session,
                    sender_wallet_id=sender_id,
                    receiver_wallet_id=receiver_id,
                    amount=Decimal("100.0000")
                )
        """
        # Validation Step 1: Validate amount
        if amount <= Decimal("0"):
            raise ValidationError("Transfer amount must be greater than zero")
        
        # Validation Step 2: Check sender exists and lock row
        sender_result = await session.execute(
            select(Wallet).where(Wallet.id == sender_wallet_id).with_for_update()
        )
        sender_wallet = sender_result.scalar_one_or_none()
        if not sender_wallet:
            raise NotFoundError("Wallet", str(sender_wallet_id))
        
        # Validation Step 3: Check receiver exists and lock row
        receiver_result = await session.execute(
            select(Wallet).where(Wallet.id == receiver_wallet_id).with_for_update()
        )
        receiver_wallet = receiver_result.scalar_one_or_none()
        if not receiver_wallet:
            raise NotFoundError("Wallet", str(receiver_wallet_id))
        
        # Validation Step 4: Check self-transfer
        if sender_wallet_id == receiver_wallet_id:
            raise ValidationError("Cannot transfer funds to the same wallet")
        
        # Validation Step 5: Check sufficient funds
        if sender_wallet.balance < amount:
            raise InsufficientFundsError(
                str(sender_wallet_id),
                amount,
                sender_wallet.balance,
            )
        
        # Execution Step 1: Deduct from sender
        sender_wallet.balance -= amount
        
        # Execution Step 2: Add to receiver
        receiver_wallet.balance += amount
        
        # Execution Step 3: Create transaction record
        transaction = Transaction(
            sender_wallet_id=sender_wallet_id,
            receiver_wallet_id=receiver_wallet_id,
            amount=amount,
            status=TransactionStatus.COMPLETED,
        )
        session.add(transaction)
        
        # Transaction commits when context manager exits successfully
        # Transaction rolls back automatically if any exception is raised
        
        return transaction
