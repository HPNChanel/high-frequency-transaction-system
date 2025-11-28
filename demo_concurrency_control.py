"""Demonstration script comparing pessimistic and optimistic locking strategies.

This script shows how to use both concurrency control methods and demonstrates
their behavior under different scenarios.
"""

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConcurrencyError, InsufficientFundsError
from app.db.session import async_session_maker
from app.models.user import User
from app.models.wallet import Wallet
from app.services.transaction_service import TransactionService


async def setup_test_wallets(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Create two test users with wallets for demonstration."""
    # Create sender user and wallet
    sender_user = User(
        email=f"sender_{uuid.uuid4()}@example.com",
        hashed_password="hashed_password",
        full_name="Sender User",
    )
    session.add(sender_user)
    await session.flush()
    
    sender_wallet = Wallet(
        user_id=sender_user.id,
        balance=Decimal("1000.0000"),
        currency="USD",
    )
    session.add(sender_wallet)
    
    # Create receiver user and wallet
    receiver_user = User(
        email=f"receiver_{uuid.uuid4()}@example.com",
        hashed_password="hashed_password",
        full_name="Receiver User",
    )
    session.add(receiver_user)
    await session.flush()
    
    receiver_wallet = Wallet(
        user_id=receiver_user.id,
        balance=Decimal("500.0000"),
        currency="USD",
    )
    session.add(receiver_wallet)
    
    await session.commit()
    
    return sender_wallet.id, receiver_wallet.id


async def demo_pessimistic_locking():
    """Demonstrate pessimistic locking - simple, no retry needed."""
    print("\n" + "="*70)
    print("DEMO 1: PESSIMISTIC LOCKING (The 'Safe' Way)")
    print("="*70)
    
    async with async_session_maker() as session:
        # Setup
        sender_id, receiver_id = await setup_test_wallets(session)
        
        print(f"\n✓ Created sender wallet: {sender_id}")
        print(f"✓ Created receiver wallet: {receiver_id}")
        print(f"✓ Initial balances: Sender=1000.00, Receiver=500.00")
        
        # Perform transfer using pessimistic locking
        service = TransactionService()
        
        print("\n→ Executing transfer with PESSIMISTIC LOCKING...")
        print("  (This will lock both wallet rows immediately)")
        
        async with session.begin():
            transaction = await service.transfer_funds_pessimistic(
                session=session,
                sender_wallet_id=sender_id,
                receiver_wallet_id=receiver_id,
                amount=Decimal("100.0000"),
            )
            await session.refresh(transaction)
        
        print(f"\n✓ Transfer completed successfully!")
        print(f"  Transaction ID: {transaction.id}")
        print(f"  Amount: {transaction.amount}")
        print(f"  Status: {transaction.status}")
        
        # Verify balances
        async with session.begin():
            sender_wallet = await session.get(Wallet, sender_id)
            receiver_wallet = await session.get(Wallet, receiver_id)
            
            print(f"\n✓ Final balances:")
            print(f"  Sender: {sender_wallet.balance} (was 1000.00)")
            print(f"  Receiver: {receiver_wallet.balance} (was 500.00)")
            print(f"  Total: {sender_wallet.balance + receiver_wallet.balance} (conserved!)")
        
        print("\n💡 KEY POINTS:")
        print("  • No retry logic needed - transaction always succeeds if valid")
        print("  • Other transactions would BLOCK if they tried to access these wallets")
        print("  • Simple error handling - just catch validation/business errors")


async def demo_optimistic_locking():
    """Demonstrate optimistic locking - requires retry logic."""
    print("\n" + "="*70)
    print("DEMO 2: OPTIMISTIC LOCKING (The 'Fast' Way)")
    print("="*70)
    
    async with async_session_maker() as session:
        # Setup
        sender_id, receiver_id = await setup_test_wallets(session)
        
        print(f"\n✓ Created sender wallet: {sender_id}")
        print(f"✓ Created receiver wallet: {receiver_id}")
        print(f"✓ Initial balances: Sender=1000.00, Receiver=500.00")
        
        # Perform transfer using optimistic locking with retry logic
        service = TransactionService()
        max_retries = 3
        
        print("\n→ Executing transfer with OPTIMISTIC LOCKING...")
        print("  (This will NOT lock rows - uses version numbers instead)")
        
        for attempt in range(max_retries):
            try:
                async with session.begin():
                    transaction = await service.transfer_funds_optimistic(
                        session=session,
                        sender_wallet_id=sender_id,
                        receiver_wallet_id=receiver_id,
                        amount=Decimal("100.0000"),
                    )
                    await session.refresh(transaction)
                
                print(f"\n✓ Transfer completed on attempt {attempt + 1}!")
                print(f"  Transaction ID: {transaction.id}")
                print(f"  Amount: {transaction.amount}")
                print(f"  Status: {transaction.status}")
                break
                
            except ConcurrencyError as e:
                print(f"\n⚠ Attempt {attempt + 1} failed: {e.message}")
                if attempt == max_retries - 1:
                    print("  ✗ Max retries reached, giving up")
                    raise
                else:
                    wait_time = 0.1 * (2 ** attempt)
                    print(f"  → Retrying in {wait_time}s with exponential backoff...")
                    await asyncio.sleep(wait_time)
        
        # Verify balances
        async with session.begin():
            sender_wallet = await session.get(Wallet, sender_id)
            receiver_wallet = await session.get(Wallet, receiver_id)
            
            print(f"\n✓ Final balances:")
            print(f"  Sender: {sender_wallet.balance} (was 1000.00)")
            print(f"  Receiver: {receiver_wallet.balance} (was 500.00)")
            print(f"  Total: {sender_wallet.balance + receiver_wallet.balance} (conserved!)")
            print(f"\n✓ Version numbers incremented:")
            print(f"  Sender version: {sender_wallet.version} (was 1)")
            print(f"  Receiver version: {receiver_wallet.version} (was 1)")
        
        print("\n💡 KEY POINTS:")
        print("  • Retry logic required - ConcurrencyError can occur")
        print("  • Other transactions can proceed without blocking")
        print("  • Version numbers detect concurrent modifications")
        print("  • Better throughput when conflicts are rare")


async def demo_comparison():
    """Show side-by-side comparison of both methods."""
    print("\n" + "="*70)
    print("COMPARISON: WHEN TO USE EACH METHOD")
    print("="*70)
    
    comparison = """
┌─────────────────────────────────────┬──────────────────┬──────────────────┐
│ Scenario                            │ Pessimistic      │ Optimistic       │
├─────────────────────────────────────┼──────────────────┼──────────────────┤
│ Popular merchant (1000s payments)   │ ✅ RECOMMENDED   │ ❌ Too many      │
│                                     │                  │    conflicts     │
├─────────────────────────────────────┼──────────────────┼──────────────────┤
│ Peer-to-peer (random users)         │ ⚠ Works but      │ ✅ RECOMMENDED   │
│                                     │   slower         │                  │
├─────────────────────────────────────┼──────────────────┼──────────────────┤
│ Payroll processing (batch)          │ ✅ RECOMMENDED   │ ⚠ Retry overhead │
│                                     │                  │                  │
├─────────────────────────────────────┼──────────────────┼──────────────────┤
│ Gaming micro-transactions           │ ❌ Too slow      │ ✅ RECOMMENDED   │
│                                     │                  │                  │
├─────────────────────────────────────┼──────────────────┼──────────────────┤
│ ATM withdrawals                     │ ✅ RECOMMENDED   │ ⚠ User expects   │
│                                     │                  │   immediate      │
└─────────────────────────────────────┴──────────────────┴──────────────────┘

KEY DIFFERENCES:

Pessimistic Locking:
  ✅ Zero conflicts - always succeeds if valid
  ✅ Simpler code - no retry logic
  ❌ Lower throughput under contention
  ❌ Transactions block each other

Optimistic Locking:
  ✅ Higher throughput when conflicts rare
  ✅ No blocking - better concurrency
  ❌ Requires retry logic
  ❌ Wasted work on conflicts

RULE OF THUMB:
  • High contention (>10% conflict rate) → Use Pessimistic
  • Low contention (<1% conflict rate) → Use Optimistic
  • User waiting for response → Use Pessimistic
  • Background processing → Use Optimistic
"""
    print(comparison)


async def main():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("CONCURRENCY CONTROL DEMONSTRATION")
    print("High-Frequency Transaction System")
    print("="*70)
    
    try:
        await demo_pessimistic_locking()
        await demo_optimistic_locking()
        await demo_comparison()
        
        print("\n" + "="*70)
        print("✓ All demonstrations completed successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error during demonstration: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
