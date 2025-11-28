"""Transaction API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_session
from app.core.exceptions import InsufficientFundsError, NotFoundError, ValidationError
from app.schemas.transaction import TransactionRead, TransferRequest
from app.services.transaction_service import TransactionService
from app.worker import send_transaction_email, audit_log_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/transfer", response_model=TransactionRead, status_code=200)
async def transfer_funds(
    request: TransferRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Transfer funds between two wallets.

    This endpoint provides ACID-compliant fund transfers with comprehensive validation.

    - **sender_wallet_id**: UUID of the wallet sending funds
    - **receiver_wallet_id**: UUID of the wallet receiving funds
    - **amount**: Amount to transfer (must be positive, max 4 decimal places)

    Returns the completed transaction record.
    """
    service = TransactionService()

    try:
        # Begin atomic transaction - commits on success, rolls back on exception
        async with session.begin():
            transaction = await service.transfer_funds(
                session=session,
                sender_wallet_id=request.sender_wallet_id,
                receiver_wallet_id=request.receiver_wallet_id,
                amount=request.amount,
            )
            # Refresh to get auto-generated fields
            await session.refresh(transaction)

        # ✅ CRITICAL: Transaction committed and session closed at this point
        # Now safe to queue background tasks
        
        # Queue email notification task
        send_transaction_email.delay(
            email="user@example.com",  # In production: fetch from user record
            amount=str(transaction.amount),
            status="SUCCESS"
        )
        
        # Queue audit log task
        audit_log_transaction.delay(
            transaction_id=str(transaction.id),
            data={
                "sender_wallet_id": str(transaction.sender_wallet_id),
                "receiver_wallet_id": str(transaction.receiver_wallet_id),
                "amount": str(transaction.amount),
                "status": transaction.status.value,
                "created_at": transaction.created_at.isoformat()
            }
        )
        
        # Return immediately - tasks execute in background
        return transaction

    except NotFoundError as e:
        # Wallet not found - transaction rolled back, no tasks queued
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        # Invalid input - transaction rolled back, no tasks queued
        raise HTTPException(status_code=400, detail=e.message)
    except InsufficientFundsError as e:
        # Insufficient funds - transaction rolled back, no tasks queued
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        # Unexpected error - transaction rolled back, no tasks queued
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
