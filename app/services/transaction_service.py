"""Transaction service for handling fund transfer operations.

CONCURRENCY CONTROL COMPARISON
===============================

This service implements TWO different concurrency control strategies for fund transfers.
Choose the appropriate method based on your use case:

METHOD 1: PESSIMISTIC LOCKING (transfer_funds_pessimistic)
-----------------------------------------------------------
The "Safe" Way - Locks rows immediately, blocks other transactions

✅ WHEN TO USE:
- High contention scenarios (popular merchant accounts receiving many payments)
- Critical operations where blocking is acceptable
- When consistency is more important than throughput
- Banking systems with frequent transfers between popular accounts
- Payroll processing (batch transfers that must succeed)
- ATM withdrawals (must be reliable, low volume)

✅ ADVANTAGES:
- Zero conflict errors - transactions always succeed if valid
- Simpler error handling - no retry logic required
- Predictable behavior under load
- First transaction wins, others wait in queue

❌ DISADVANTAGES:
- Lower throughput under high contention
- Risk of deadlocks if locks acquired in different orders
- Blocked transactions consume database connections
- Higher latency when waiting for locks

EXAMPLE:
    async with session.begin():
        service = TransactionService()
        # This will block if another transaction holds the lock
        transaction = await service.transfer_funds_pessimistic(
            session, sender_id, receiver_id, Decimal("100.00")
        )


METHOD 2: OPTIMISTIC LOCKING (transfer_funds_optimistic)
---------------------------------------------------------
The "Fast" Way - No locks, uses version numbers to detect conflicts

✅ WHEN TO USE:
- Low contention scenarios (peer-to-peer transfers between random users)
- Read-heavy workloads with occasional updates
- When throughput is more important than latency
- Systems where retry logic is acceptable
- Micro-transactions in gaming (high volume, retry acceptable)
- Social media interactions (likes, follows)

✅ ADVANTAGES:
- Higher throughput under low contention
- No blocking - transactions never wait
- No deadlock risk
- Better database connection utilization
- Lower latency when no conflicts occur

❌ DISADVANTAGES:
- Conflicts result in ConcurrencyError requiring retry
- More complex error handling
- Wasted work when conflicts occur
- Performance degrades under high contention

EXAMPLE:
    async with session.begin():
        service = TransactionService()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # This will raise ConcurrencyError if version mismatch
                transaction = await service.transfer_funds_optimistic(
                    session, sender_id, receiver_id, Decimal("100.00")
                )
                break
            except ConcurrencyError:
                if attempt == max_retries - 1:
                    raise
                # Retry with exponential backoff
                await asyncio.sleep(0.1 * (2 ** attempt))


DECISION MATRIX
---------------
| Scenario                                    | Recommended Strategy | Reason                          |
|---------------------------------------------|----------------------|---------------------------------|
| Popular merchant receiving 1000s payments   | Pessimistic          | High contention, blocking OK    |
| Peer-to-peer transfers (random users)       | Optimistic           | Low contention, max throughput  |
| Payroll processing (batch transfers)        | Pessimistic          | Predictable, must succeed       |
| Micro-transactions in gaming                | Optimistic           | High volume, retry acceptable   |
| ATM withdrawals                             | Pessimistic          | Must be reliable, low volume    |
| E-commerce checkout                         | Pessimistic          | User expects immediate success  |
| Background balance adjustments              | Optimistic           | Can retry, no user waiting      |

"""

import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConcurrencyError,
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
    
    Two concurrency control strategies are available:
    1. Pessimistic Locking (transfer_funds_pessimistic) - The "Safe" Way
    2. Optimistic Locking (transfer_funds_optimistic) - The "Fast" Way
    
    See module docstring for detailed comparison and decision matrix.
    """
    
    async def transfer_funds(
        self,
        session: AsyncSession,
        sender_wallet_id: uuid.UUID,
        receiver_wallet_id: uuid.UUID,
        amount: Decimal,
    ) -> Transaction:
        """Transfer funds between two wallets using pessimistic locking.
        
        This is the default method that delegates to transfer_funds_pessimistic
        for backward compatibility with existing code.
        
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
        """
        return await self.transfer_funds_pessimistic(
            session, sender_wallet_id, receiver_wallet_id, amount
        )
    
    async def transfer_funds_pessimistic(
        self,
        session: AsyncSession,
        sender_wallet_id: uuid.UUID,
        receiver_wallet_id: uuid.UUID,
        amount: Decimal,
    ) -> Transaction:
        """Transfer funds using PESSIMISTIC LOCKING (The "Safe" Way).
        
        This method acquires exclusive row locks on both wallets immediately,
        preventing any other transaction from reading or modifying them until
        this transaction commits or rolls back.
        
        CONCURRENCY BEHAVIOR:
        - Uses SELECT ... FOR UPDATE to lock wallet rows
        - Other transactions attempting to access these wallets will BLOCK
        - Guarantees no concurrent modifications - zero conflict errors
        - First transaction to acquire locks wins, others wait in queue
        
        WHEN TO USE:
        - High contention scenarios (popular merchant accounts)
        - When consistency is more important than throughput
        - When blocking is acceptable
        - When retry logic should be avoided
        
        TRADE-OFFS:
        ✅ No conflicts - transactions always succeed if valid
        ✅ Simpler error handling
        ❌ Lower throughput under contention
        ❌ Blocked transactions consume connections
        
        The transfer process follows these steps:
        1. Validate amount is positive
        2. Lock and verify sender wallet exists
        3. Lock and verify receiver wallet exists
        4. Validate sender and receiver are different
        5. Validate sender has sufficient funds
        6. Deduct amount from sender balance
        7. Add amount to receiver balance
        8. Create transaction record with COMPLETED status
        
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
                transaction = await service.transfer_funds_pessimistic(
                    session=session,
                    sender_wallet_id=sender_id,
                    receiver_wallet_id=receiver_id,
                    amount=Decimal("100.0000")
                )
        """
        # Validation Step 1: Validate amount
        if amount <= Decimal("0"):
            raise ValidationError("Transfer amount must be greater than zero")
        
        # Validation Step 2: Check sender exists and LOCK ROW
        # with_for_update() acquires an exclusive lock on this row
        # Other transactions trying to read/update this wallet will WAIT here
        sender_result = await session.execute(
            select(Wallet).where(Wallet.id == sender_wallet_id).with_for_update()
        )
        sender_wallet = sender_result.scalar_one_or_none()
        if not sender_wallet:
            raise NotFoundError("Wallet", str(sender_wallet_id))
        
        # Validation Step 3: Check receiver exists and LOCK ROW
        # Now we hold locks on BOTH wallets - no one else can modify them
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
        # Safe to modify - we hold the lock, no one else can change this
        sender_wallet.balance -= amount
        
        # Execution Step 2: Add to receiver
        # Safe to modify - we hold the lock, no one else can change this
        receiver_wallet.balance += amount
        
        # Execution Step 3: Create transaction record
        transaction = Transaction(
            sender_wallet_id=sender_wallet_id,
            receiver_wallet_id=receiver_wallet_id,
            amount=amount,
            status=TransactionStatus.COMPLETED,
        )
        session.add(transaction)
        
        # Locks are released when transaction commits or rolls back
        # Other waiting transactions can now proceed
        
        return transaction
    
    async def transfer_funds_optimistic(
        self,
        session: AsyncSession,
        sender_wallet_id: uuid.UUID,
        receiver_wallet_id: uuid.UUID,
        amount: Decimal,
    ) -> Transaction:
        """Transfer funds using OPTIMISTIC LOCKING (The "Fast" Way).
        
        This method reads wallets WITHOUT locking, performs validations,
        then uses version numbers to detect if another transaction modified
        the wallets in the meantime.
        
        CONCURRENCY BEHAVIOR:
        - Reads wallets without locks - other transactions can proceed
        - Uses version column to detect concurrent modifications
        - UPDATE with WHERE version = old_version
        - If rowcount == 0, someone else modified the wallet - raise error
        - Caller must implement retry logic
        
        WHEN TO USE:
        - Low contention scenarios (peer-to-peer transfers)
        - When throughput is more important than latency
        - When retry logic is acceptable
        - Read-heavy workloads
        
        TRADE-OFFS:
        ✅ Higher throughput under low contention
        ✅ No blocking - better connection utilization
        ✅ No deadlock risk
        ❌ Conflicts result in errors requiring retry
        ❌ Wasted work when conflicts occur
        
        The transfer process follows these steps:
        1. Validate amount is positive
        2. Read sender wallet WITHOUT locking, remember version
        3. Read receiver wallet WITHOUT locking, remember version
        4. Validate sender and receiver are different
        5. Validate sender has sufficient funds
        6. Update sender with version check, increment version
        7. If rowcount == 0, raise ConcurrencyError
        8. Update receiver with version check, increment version
        9. If rowcount == 0, raise ConcurrencyError
        10. Create transaction record with COMPLETED status
        
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
            ConcurrencyError: If wallet was modified by another transaction
            
        Example:
            async with session.begin():
                service = TransactionService()
                try:
                    transaction = await service.transfer_funds_optimistic(
                        session=session,
                        sender_wallet_id=sender_id,
                        receiver_wallet_id=receiver_id,
                        amount=Decimal("100.0000")
                    )
                except ConcurrencyError:
                    # Implement retry logic here
                    pass
        """
        # Validation Step 1: Validate amount
        if amount <= Decimal("0"):
            raise ValidationError("Transfer amount must be greater than zero")
        
        # Validation Step 2: Read sender WITHOUT locking
        # Other transactions can read/modify this wallet concurrently
        sender_result = await session.execute(
            select(Wallet).where(Wallet.id == sender_wallet_id)
        )
        sender_wallet = sender_result.scalar_one_or_none()
        if not sender_wallet:
            raise NotFoundError("Wallet", str(sender_wallet_id))
        
        # Remember the version we read - this is our "snapshot"
        sender_version = sender_wallet.version
        sender_balance = sender_wallet.balance
        
        # Validation Step 3: Read receiver WITHOUT locking
        receiver_result = await session.execute(
            select(Wallet).where(Wallet.id == receiver_wallet_id)
        )
        receiver_wallet = receiver_result.scalar_one_or_none()
        if not receiver_wallet:
            raise NotFoundError("Wallet", str(receiver_wallet_id))
        
        # Remember the version we read
        receiver_version = receiver_wallet.version
        receiver_balance = receiver_wallet.balance
        
        # Validation Step 4: Check self-transfer
        if sender_wallet_id == receiver_wallet_id:
            raise ValidationError("Cannot transfer funds to the same wallet")
        
        # Validation Step 5: Check sufficient funds
        if sender_balance < amount:
            raise InsufficientFundsError(
                str(sender_wallet_id),
                amount,
                sender_balance,
            )
        
        # Execution Step 1: Update sender with version check
        # This UPDATE will only succeed if version hasn't changed
        # If another transaction modified this wallet, version will be different
        sender_update_result = await session.execute(
            update(Wallet)
            .where(Wallet.id == sender_wallet_id, Wallet.version == sender_version)
            .values(
                balance=sender_balance - amount,
                version=sender_version + 1,  # Increment version atomically
            )
        )
        
        # Check if update succeeded
        if sender_update_result.rowcount == 0:
            # Version mismatch - someone else modified this wallet
            raise ConcurrencyError("Wallet", str(sender_wallet_id))
        
        # Execution Step 2: Update receiver with version check
        receiver_update_result = await session.execute(
            update(Wallet)
            .where(Wallet.id == receiver_wallet_id, Wallet.version == receiver_version)
            .values(
                balance=receiver_balance + amount,
                version=receiver_version + 1,  # Increment version atomically
            )
        )
        
        # Check if update succeeded
        if receiver_update_result.rowcount == 0:
            # Version mismatch - someone else modified this wallet
            # Sender update will be rolled back automatically
            raise ConcurrencyError("Wallet", str(receiver_wallet_id))
        
        # Execution Step 3: Create transaction record
        transaction = Transaction(
            sender_wallet_id=sender_wallet_id,
            receiver_wallet_id=receiver_wallet_id,
            amount=amount,
            status=TransactionStatus.COMPLETED,
        )
        session.add(transaction)
        
        # If we reach here, both updates succeeded - versions matched
        # Transaction commits successfully
        
        return transaction
