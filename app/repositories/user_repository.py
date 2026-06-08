from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole, UserStatus
from app.models.chauffeur import Chauffeur
from app.models.wallet import Wallet
from app.core.security import hash_password


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_telephone(self, telephone: str) -> User | None:
        result = await self._db.execute(
            select(User).where(User.telephone == telephone)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._db.get(User, user_id)

    async def telephone_exists(self, telephone: str) -> bool:
        result = await self._db.execute(
            select(User.id).where(User.telephone == telephone)
        )
        return result.scalar_one_or_none() is not None

    async def create(
        self,
        telephone: str,
        nom: str,
        prenom: str,
        password: str,
        email: str | None = None,
    ) -> User:
        user = User(
            telephone=telephone,
            nom=nom,
            prenom=prenom,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.CLIENT,
            statut=UserStatus.ACTIF,
        )
        self._db.add(user)
        await self._db.flush()
        self._db.add(Wallet(user_id=user.id))
        await self._db.flush()
        return user

    async def create_chauffeur_user(
        self,
        telephone: str,
        nom: str,
        prenom: str,
        password: str,
        email: str | None = None,
    ) -> User:
        user = User(
            telephone=telephone,
            nom=nom,
            prenom=prenom,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.CHAUFFEUR,
            statut=UserStatus.ACTIF,
        )
        self._db.add(user)
        await self._db.flush()
        chauffeur = Chauffeur(user_id=user.id)
        self._db.add(chauffeur)
        await self._db.flush()
        self._db.add(Wallet(user_id=user.id))
        await self._db.flush()
        return user

    async def init_chauffeur_profile(self, user_id: UUID) -> Chauffeur:
        chauffeur = Chauffeur(user_id=user_id)
        self._db.add(chauffeur)
        await self._db.flush()
        return chauffeur