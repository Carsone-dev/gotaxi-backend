from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User, UserStatus
from app.models.avis import Avis
from app.schemas.user import UserRead, UserUpdate, UserPublic
from app.schemas.avis import AvisRead
from app.schemas.common import MessageResponse
from app.dependencies import get_current_user
from app.utils.validators import validate_image

router = APIRouter(prefix="/users", tags=["Utilisateurs"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.delete("/me", response_model=MessageResponse)
async def delete_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.statut = UserStatus.SUPPRIME
    await db.commit()
    return {"message": "Compte supprimé"}


@router.post("/me/fcm-token", response_model=MessageResponse)
async def update_fcm_token(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.fcm_token = token
    await db.commit()
    return {"message": "Token FCM enregistré"}


@router.post("/me/photo", response_model=UserRead)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    try:
        validate_image(file.content_type or "", len(content))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    from app.integrations.s3_storage import upload_file
    current_user.photo_url = upload_file(content, "profiles", file.filename, file.content_type or "image/jpeg")
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/me/avis", response_model=list[AvisRead])
async def my_avis_recus(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Avis)
        .where(Avis.cible_id == current_user.id, Avis.visible == True)
        .order_by(Avis.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_public(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await db.get(User, user_id)
    if not user or user.statut == UserStatus.SUPPRIME:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user