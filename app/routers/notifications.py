from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationRead, UnreadCountResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/me", response_model=PaginatedResponse[NotificationRead])
async def my_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = result.scalars().all()
    return PaginatedResponse(items=items, total=len(items), page=page, size=size, pages=1)


@router.get("/me/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        await db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == current_user.id,
                Notification.lue == False,
            )
        )
    ).scalar()
    return UnreadCountResponse(count=count or 0)


@router.post("/me/read-all", response_model=MessageResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.lue == False,
        )
    )
    for notif in result.scalars().all():
        notif.lue = True
    return {"message": "Toutes les notifications marquées comme lues"}


@router.post("/{notif_id}/read", response_model=MessageResponse)
async def mark_read(
    notif_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = await db.get(Notification, notif_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    notif.lue = True
    return {"message": "Notification marquée comme lue"}


@router.delete("/{notif_id}", response_model=MessageResponse)
async def delete_notification(
    notif_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = await db.get(Notification, notif_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    await db.delete(notif)
    return {"message": "Notification supprimée"}