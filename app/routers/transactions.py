from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.schemas.wallet import TransactionRead
from app.schemas.common import PaginatedResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/me", response_model=PaginatedResponse[TransactionRead])
async def my_transactions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        return PaginatedResponse(items=[], total=0, page=page, size=size, pages=0)

    result = await db.execute(
        select(Transaction)
        .where(Transaction.wallet_id == wallet.id)
        .order_by(Transaction.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()
    return PaginatedResponse(items=items, total=len(items), page=page, size=size, pages=1)


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()

    transaction = await db.get(Transaction, transaction_id)
    if not transaction or not wallet or transaction.wallet_id != wallet.id:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    return transaction