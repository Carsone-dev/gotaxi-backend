"""
Seed des administrateurs du backoffice.

Usage (depuis le répertoire backend/) :
    python scripts/seed_admins.py

Chaque entrée de ADMINS est insérée seulement si le numéro de téléphone
n'existe pas déjà. Modifiez les mots de passe avant le premier déploiement.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus

settings = get_settings()

ADMINS: list[dict] = [
    {
        "telephone": "+2290100000010",
        "email": "superadmin@gotaxi.bj",
        "nom": "Super",
        "prenom": "Admin",
        "password": "Admin@GoTaxi2024!",
        "role": UserRole.SUPER_ADMIN,
    },
    {
        "telephone": "+2290100000011",
        "email": "admin@gotaxi.bj",
        "nom": "Admin",
        "prenom": "Backoffice",
        "password": "Admin@GoTaxi2024!",
        "role": UserRole.ADMIN,
    },
]


async def seed_admins() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    skipped = 0

    async with SessionLocal() as session:
        for data in ADMINS:
            result = await session.execute(
                select(User).where(User.telephone == data["telephone"])
            )
            if result.scalar_one_or_none():
                print(f"[SKIP] {data['role'].value:<12} {data['telephone']} — existe déjà")
                skipped += 1
                continue

            user = User(
                telephone=data["telephone"],
                email=data.get("email"),
                nom=data["nom"],
                prenom=data["prenom"],
                password_hash=hash_password(data["password"]),
                role=data["role"],
                statut=UserStatus.ACTIF,
                telephone_verifie=True,
                email_verifie=bool(data.get("email")),
            )
            session.add(user)
            await session.flush()
            print(f"[OK]   {data['role'].value:<12} {data['telephone']} — créé")
            created += 1

        await session.commit()

    await engine.dispose()
    print(f"\nRésultat : {created} créé(s), {skipped} ignoré(s).")


if __name__ == "__main__":
    asyncio.run(seed_admins())