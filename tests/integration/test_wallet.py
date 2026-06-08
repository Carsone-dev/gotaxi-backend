"""Tests d'intégration pour les endpoints wallet/paiement."""
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select, insert as sa_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionStatut, TransactionOperateur
from tests.conftest import TEST_PHONE, TEST_PHONE_2

settings = get_settings()

# ── Helpers DB ────────────────────────────────────────────────────────────────

def _make_engine():
    return create_async_engine(settings.DATABASE_URL, poolclass=NullPool)


async def _get_user_id(telephone: str) -> str | None:
    engine = _make_engine()
    async with engine.begin() as conn:
        result = await conn.execute(select(User.id).where(User.telephone == telephone))
        row = result.scalar_one_or_none()
    await engine.dispose()
    return str(row) if row else None


async def _create_wallet(user_id: str, solde: int = 0) -> str:
    wallet_id = uuid4()
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.execute(
            sa_insert(Wallet).values(
                id=wallet_id,
                user_id=user_id,
                solde=solde,
                devise="XOF",
                actif=True,
            )
        )
    await engine.dispose()
    return str(wallet_id)


async def _get_wallet(user_id: str) -> dict | None:
    engine = _make_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        row = result.mappings().first()
    await engine.dispose()
    if not row:
        return None
    return dict(row)


async def _cleanup_wallet(user_id: str):
    engine = _make_engine()
    async with engine.begin() as conn:
        # Transaction d'abord (FK), puis Wallet
        result = await conn.execute(select(Wallet.id).where(Wallet.user_id == user_id))
        wallet_ids = [r[0] for r in result.fetchall()]
        if wallet_ids:
            await conn.execute(
                delete(Transaction).where(Transaction.wallet_id.in_(wallet_ids))
            )
        await conn.execute(delete(Wallet).where(Wallet.user_id == user_id))
    await engine.dispose()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, auth_tokens: dict) -> dict:
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}


@pytest_asyncio.fixture
async def user_with_wallet(client: AsyncClient, auth_tokens: dict) -> dict:
    """Utilisateur connecté avec un wallet (solde 0)."""
    user_id = await _get_user_id(TEST_PHONE)
    wallet_id = await _create_wallet(user_id)
    yield {
        "user_id": user_id,
        "wallet_id": wallet_id,
        "headers": {"Authorization": f"Bearer {auth_tokens['access_token']}"},
    }
    await _cleanup_wallet(user_id)


@pytest_asyncio.fixture
async def user_with_funded_wallet(client: AsyncClient, auth_tokens: dict) -> dict:
    """Utilisateur connecté avec un wallet rechargé (50 000 XOF)."""
    user_id = await _get_user_id(TEST_PHONE)
    wallet_id = await _create_wallet(user_id, solde=50_000)
    yield {
        "user_id": user_id,
        "wallet_id": wallet_id,
        "headers": {"Authorization": f"Bearer {auth_tokens['access_token']}"},
    }
    await _cleanup_wallet(user_id)


# ── GET /wallet/me ─────────────────────────────────────────────────────────────

class TestGetWallet:
    async def test_sans_wallet_retourne_404(self, client: AsyncClient, auth_tokens: dict):
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        resp = await client.get("/api/v1/wallet/me", headers=headers)
        assert resp.status_code == 404

    async def test_avec_wallet_retourne_solde(self, client: AsyncClient, user_with_wallet: dict):
        resp = await client.get("/api/v1/wallet/me", headers=user_with_wallet["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["solde"] == 0
        assert data["devise"] == "XOF"
        assert data["actif"] is True

    async def test_non_authentifie_retourne_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/wallet/me")
        assert resp.status_code == 401


# ── GET /wallet/me/activity ────────────────────────────────────────────────────

class TestWalletActivity:
    async def test_activite_vide(self, client: AsyncClient, user_with_wallet: dict):
        resp = await client.get("/api/v1/wallet/me/activity", headers=user_with_wallet["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_pagination_params(self, client: AsyncClient, user_with_wallet: dict):
        resp = await client.get(
            "/api/v1/wallet/me/activity?page=1&size=5",
            headers=user_with_wallet["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["size"] == 5

    async def test_sans_wallet_retourne_404(self, client: AsyncClient, auth_tokens: dict):
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        resp = await client.get("/api/v1/wallet/me/activity", headers=headers)
        assert resp.status_code == 404


# ── POST /wallet/me/recharge/initiate ─────────────────────────────────────────

class TestRechargeInitiate:
    async def test_mtn_momo_initie_avec_succes(self, client: AsyncClient, user_with_wallet: dict):
        fake_ref = str(uuid4())
        with patch(
            "app.routers.wallet.mtn_momo.request_to_pay",
            new_callable=AsyncMock,
            return_value=fake_ref,
        ):
            resp = await client.post(
                "/api/v1/wallet/me/recharge/initiate",
                headers=user_with_wallet["headers"],
                json={"montant": 5000, "operateur": "MTN_MOMO", "telephone": "+2290197000001"},
            )
        assert resp.status_code == 200
        assert "MTN MoMo" in resp.json()["message"]

    async def test_orange_money_initie_avec_succes(self, client: AsyncClient, user_with_wallet: dict):
        order_id = str(uuid4())
        with patch(
            "app.routers.wallet.orange_money.initiate_payment",
            new_callable=AsyncMock,
            return_value={"order_id": order_id, "payment_url": "https://pay.orange.bj/xxx"},
        ):
            resp = await client.post(
                "/api/v1/wallet/me/recharge/initiate",
                headers=user_with_wallet["headers"],
                json={"montant": 5000, "operateur": "ORANGE_MONEY", "telephone": "+2290197000001"},
            )
        assert resp.status_code == 200
        assert "Orange Money" in resp.json()["message"]

    async def test_moov_money_initie_avec_succes(self, client: AsyncClient, user_with_wallet: dict):
        fake_ref = str(uuid4())
        with patch(
            "app.routers.wallet.moov_money.collect",
            new_callable=AsyncMock,
            return_value=fake_ref,
        ):
            resp = await client.post(
                "/api/v1/wallet/me/recharge/initiate",
                headers=user_with_wallet["headers"],
                json={"montant": 5000, "operateur": "MOOV_MONEY", "telephone": "+2290197000001"},
            )
        assert resp.status_code == 200
        assert "Moov Money" in resp.json()["message"]

    async def test_operateur_invalide_retourne_422(self, client: AsyncClient, user_with_wallet: dict):
        resp = await client.post(
            "/api/v1/wallet/me/recharge/initiate",
            headers=user_with_wallet["headers"],
            json={"montant": 5000, "operateur": "VISA_CARD", "telephone": "+2290197000001"},
        )
        assert resp.status_code == 422

    async def test_montant_trop_faible_retourne_422(self, client: AsyncClient, user_with_wallet: dict):
        resp = await client.post(
            "/api/v1/wallet/me/recharge/initiate",
            headers=user_with_wallet["headers"],
            json={"montant": 100, "operateur": "MTN_MOMO", "telephone": "+2290197000001"},
        )
        assert resp.status_code == 422

    async def test_erreur_operateur_retourne_502(self, client: AsyncClient, user_with_wallet: dict):
        from app.integrations.mtn_momo import MTNMoMoError
        with patch(
            "app.routers.wallet.mtn_momo.request_to_pay",
            new_callable=AsyncMock,
            side_effect=MTNMoMoError("Réseau indisponible"),
        ):
            resp = await client.post(
                "/api/v1/wallet/me/recharge/initiate",
                headers=user_with_wallet["headers"],
                json={"montant": 5000, "operateur": "MTN_MOMO", "telephone": "+2290197000001"},
            )
        assert resp.status_code == 502
        assert "opérateur" in resp.json()["detail"].lower()

    async def test_sans_wallet_retourne_404(self, client: AsyncClient, auth_tokens: dict):
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        resp = await client.post(
            "/api/v1/wallet/me/recharge/initiate",
            headers=headers,
            json={"montant": 5000, "operateur": "MTN_MOMO", "telephone": "+2290197000001"},
        )
        assert resp.status_code == 404


# ── POST /wallet/me/recharge/confirm ──────────────────────────────────────────

class TestRechargeConfirm:
    async def _initiate_mtn(self, client: AsyncClient, headers: dict, fake_ref: str) -> str:
        """Initie une recharge MTN et retourne l'ID de transaction."""
        with patch(
            "app.routers.wallet.mtn_momo.request_to_pay",
            new_callable=AsyncMock,
            return_value=fake_ref,
        ):
            await client.post(
                "/api/v1/wallet/me/recharge/initiate",
                headers=headers,
                json={"montant": 10_000, "operateur": "MTN_MOMO", "telephone": "+2290197000001"},
            )
        # Récupérer l'ID de la transaction créée
        user_id = await _get_user_id(TEST_PHONE)
        wallet_info = await _get_wallet(user_id)
        engine = _make_engine()
        async with engine.begin() as conn:
            result = await conn.execute(
                select(Transaction.id)
                .where(Transaction.wallet_id == wallet_info["id"])
                .order_by(Transaction.created_at.desc())
                .limit(1)
            )
            tx_id = result.scalar_one()
        await engine.dispose()
        return str(tx_id)

    async def test_mtn_recharge_reussie_credite_wallet(
        self, client: AsyncClient, user_with_wallet: dict
    ):
        fake_ref = str(uuid4())
        tx_id = await self._initiate_mtn(client, user_with_wallet["headers"], fake_ref)

        with patch(
            "app.routers.wallet.mtn_momo.get_transaction_status",
            new_callable=AsyncMock,
            return_value={"status": "SUCCESSFUL"},
        ):
            resp = await client.post(
                f"/api/v1/wallet/me/recharge/confirm?transaction_id={tx_id}",
                headers=user_with_wallet["headers"],
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["solde"] == 10_000

    async def test_mtn_recharge_echec_retourne_402(
        self, client: AsyncClient, user_with_wallet: dict
    ):
        fake_ref = str(uuid4())
        tx_id = await self._initiate_mtn(client, user_with_wallet["headers"], fake_ref)

        with patch(
            "app.routers.wallet.mtn_momo.get_transaction_status",
            new_callable=AsyncMock,
            return_value={"status": "FAILED"},
        ):
            resp = await client.post(
                f"/api/v1/wallet/me/recharge/confirm?transaction_id={tx_id}",
                headers=user_with_wallet["headers"],
            )
        assert resp.status_code == 402

    async def test_mtn_recharge_en_attente_retourne_202(
        self, client: AsyncClient, user_with_wallet: dict
    ):
        fake_ref = str(uuid4())
        tx_id = await self._initiate_mtn(client, user_with_wallet["headers"], fake_ref)

        with patch(
            "app.routers.wallet.mtn_momo.get_transaction_status",
            new_callable=AsyncMock,
            return_value={"status": "PENDING"},
        ):
            resp = await client.post(
                f"/api/v1/wallet/me/recharge/confirm?transaction_id={tx_id}",
                headers=user_with_wallet["headers"],
            )
        assert resp.status_code == 202

    async def test_transaction_introuvable_retourne_404(
        self, client: AsyncClient, user_with_wallet: dict
    ):
        fake_tx_id = str(uuid4())
        resp = await client.post(
            f"/api/v1/wallet/me/recharge/confirm?transaction_id={fake_tx_id}",
            headers=user_with_wallet["headers"],
        )
        assert resp.status_code == 404

    async def test_erreur_operateur_sur_confirm_retourne_502(
        self, client: AsyncClient, user_with_wallet: dict
    ):
        from app.integrations.mtn_momo import MTNMoMoError
        fake_ref = str(uuid4())
        tx_id = await self._initiate_mtn(client, user_with_wallet["headers"], fake_ref)

        with patch(
            "app.routers.wallet.mtn_momo.get_transaction_status",
            new_callable=AsyncMock,
            side_effect=MTNMoMoError("Timeout"),
        ):
            resp = await client.post(
                f"/api/v1/wallet/me/recharge/confirm?transaction_id={tx_id}",
                headers=user_with_wallet["headers"],
            )
        assert resp.status_code == 502

    async def test_orange_money_recharge_reussie(
        self, client: AsyncClient, user_with_wallet: dict
    ):
        order_id = str(uuid4())
        with patch(
            "app.routers.wallet.orange_money.initiate_payment",
            new_callable=AsyncMock,
            return_value={"order_id": order_id},
        ):
            await client.post(
                "/api/v1/wallet/me/recharge/initiate",
                headers=user_with_wallet["headers"],
                json={"montant": 8_000, "operateur": "ORANGE_MONEY", "telephone": "+2290197000001"},
            )

        user_id = await _get_user_id(TEST_PHONE)
        wallet_info = await _get_wallet(user_id)
        engine = _make_engine()
        async with engine.begin() as conn:
            result = await conn.execute(
                select(Transaction.id)
                .where(Transaction.wallet_id == wallet_info["id"])
                .order_by(Transaction.created_at.desc())
                .limit(1)
            )
            tx_id = str(result.scalar_one())
        await engine.dispose()

        with patch(
            "app.routers.wallet.orange_money.get_status",
            new_callable=AsyncMock,
            return_value={"status": "SUCCESS"},
        ):
            resp = await client.post(
                f"/api/v1/wallet/me/recharge/confirm?transaction_id={tx_id}",
                headers=user_with_wallet["headers"],
            )
        assert resp.status_code == 200
        assert resp.json()["solde"] == 8_000

    async def test_moov_money_recharge_reussie(
        self, client: AsyncClient, user_with_wallet: dict
    ):
        fake_ref = str(uuid4())
        with patch(
            "app.routers.wallet.moov_money.collect",
            new_callable=AsyncMock,
            return_value=fake_ref,
        ):
            await client.post(
                "/api/v1/wallet/me/recharge/initiate",
                headers=user_with_wallet["headers"],
                json={"montant": 6_000, "operateur": "MOOV_MONEY", "telephone": "+2290197000001"},
            )

        user_id = await _get_user_id(TEST_PHONE)
        wallet_info = await _get_wallet(user_id)
        engine = _make_engine()
        async with engine.begin() as conn:
            result = await conn.execute(
                select(Transaction.id)
                .where(Transaction.wallet_id == wallet_info["id"])
                .order_by(Transaction.created_at.desc())
                .limit(1)
            )
            tx_id = str(result.scalar_one())
        await engine.dispose()

        with patch(
            "app.routers.wallet.moov_money.get_status",
            new_callable=AsyncMock,
            return_value={"status": "SUCCESSFUL"},
        ):
            resp = await client.post(
                f"/api/v1/wallet/me/recharge/confirm?transaction_id={tx_id}",
                headers=user_with_wallet["headers"],
            )
        assert resp.status_code == 200
        assert resp.json()["solde"] == 6_000


# ── POST /wallet/me/withdraw ──────────────────────────────────────────────────

class TestWithdraw:
    async def test_solde_insuffisant_retourne_402(
        self, client: AsyncClient, user_with_wallet: dict
    ):
        resp = await client.post(
            "/api/v1/wallet/me/withdraw",
            headers=user_with_wallet["headers"],
            json={"montant": 5_000, "telephone": "+2290197000001", "operateur": "MTN_MOMO"},
        )
        assert resp.status_code == 402
        assert "insuffisant" in resp.json()["detail"].lower()

    async def test_mtn_retrait_initie_avec_succes(
        self, client: AsyncClient, user_with_funded_wallet: dict
    ):
        fake_ref = str(uuid4())
        with patch(
            "app.routers.wallet.mtn_momo.transfer",
            new_callable=AsyncMock,
            return_value=fake_ref,
        ):
            resp = await client.post(
                "/api/v1/wallet/me/withdraw",
                headers=user_with_funded_wallet["headers"],
                json={"montant": 10_000, "telephone": "+2290197000001", "operateur": "MTN_MOMO"},
            )
        assert resp.status_code == 200
        assert "MTN MoMo" in resp.json()["message"]

        # Vérifier que le solde a été débité
        wallet = await _get_wallet(user_with_funded_wallet["user_id"])
        assert wallet["solde"] == 40_000

    async def test_mtn_retrait_echec_rembourse_solde(
        self, client: AsyncClient, user_with_funded_wallet: dict
    ):
        from app.integrations.mtn_momo import MTNMoMoError
        with patch(
            "app.routers.wallet.mtn_momo.transfer",
            new_callable=AsyncMock,
            side_effect=MTNMoMoError("Transfer échoué"),
        ):
            resp = await client.post(
                "/api/v1/wallet/me/withdraw",
                headers=user_with_funded_wallet["headers"],
                json={"montant": 10_000, "telephone": "+2290197000001", "operateur": "MTN_MOMO"},
            )
        assert resp.status_code == 502

        # Le solde doit être rétabli
        wallet = await _get_wallet(user_with_funded_wallet["user_id"])
        assert wallet["solde"] == 50_000

    async def test_orange_retrait_traitement_manuel(
        self, client: AsyncClient, user_with_funded_wallet: dict
    ):
        resp = await client.post(
            "/api/v1/wallet/me/withdraw",
            headers=user_with_funded_wallet["headers"],
            json={"montant": 5_000, "telephone": "+2290197000001", "operateur": "ORANGE_MONEY"},
        )
        assert resp.status_code == 200
        assert "Orange Money" in resp.json()["message"]

        wallet = await _get_wallet(user_with_funded_wallet["user_id"])
        assert wallet["solde"] == 45_000

    async def test_moov_retrait_traitement_manuel(
        self, client: AsyncClient, user_with_funded_wallet: dict
    ):
        resp = await client.post(
            "/api/v1/wallet/me/withdraw",
            headers=user_with_funded_wallet["headers"],
            json={"montant": 5_000, "telephone": "+2290197000001", "operateur": "MOOV_MONEY"},
        )
        assert resp.status_code == 200
        assert "Moov Money" in resp.json()["message"]

        wallet = await _get_wallet(user_with_funded_wallet["user_id"])
        assert wallet["solde"] == 45_000

    async def test_montant_minimum_422(self, client: AsyncClient, user_with_funded_wallet: dict):
        resp = await client.post(
            "/api/v1/wallet/me/withdraw",
            headers=user_with_funded_wallet["headers"],
            json={"montant": 100, "telephone": "+2290197000001", "operateur": "MTN_MOMO"},
        )
        assert resp.status_code == 422

    async def test_sans_wallet_retourne_404(self, client: AsyncClient, auth_tokens: dict):
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        resp = await client.post(
            "/api/v1/wallet/me/withdraw",
            headers=headers,
            json={"montant": 5_000, "telephone": "+2290197000001", "operateur": "MTN_MOMO"},
        )
        assert resp.status_code == 404


# ── POST /wallet/me/transfer ──────────────────────────────────────────────────

class TestTransfer:
    @pytest_asyncio.fixture
    async def dest_with_wallet(self, client: AsyncClient, chauffeur_auth_tokens: dict):
        """Crée le wallet du destinataire (TEST_PHONE_2)."""
        user_id = await _get_user_id(TEST_PHONE_2)
        wallet_id = await _create_wallet(user_id, solde=0)
        yield {"user_id": user_id, "wallet_id": wallet_id}
        await _cleanup_wallet(user_id)

    async def test_transfert_reussi_entre_deux_wallets(
        self,
        client: AsyncClient,
        user_with_funded_wallet: dict,
        dest_with_wallet: dict,
        chauffeur_user: dict,
    ):
        resp = await client.post(
            "/api/v1/wallet/me/transfer",
            headers=user_with_funded_wallet["headers"],
            json={"destinataire_telephone": TEST_PHONE_2, "montant": 15_000},
        )
        assert resp.status_code == 200
        assert "15000" in resp.json()["message"] or "15 000" in resp.json()["message"] or "XOF" in resp.json()["message"]

        source_wallet = await _get_wallet(user_with_funded_wallet["user_id"])
        dest_wallet = await _get_wallet(dest_with_wallet["user_id"])
        assert source_wallet["solde"] == 35_000
        assert dest_wallet["solde"] == 15_000

    async def test_destinataire_introuvable_retourne_404(
        self, client: AsyncClient, user_with_funded_wallet: dict
    ):
        resp = await client.post(
            "/api/v1/wallet/me/transfer",
            headers=user_with_funded_wallet["headers"],
            json={"destinataire_telephone": "+2290199999999", "montant": 1_000},
        )
        assert resp.status_code == 404

    async def test_solde_insuffisant_retourne_402(
        self, client: AsyncClient, user_with_wallet: dict, chauffeur_user: dict
    ):
        resp = await client.post(
            "/api/v1/wallet/me/transfer",
            headers=user_with_wallet["headers"],
            json={"destinataire_telephone": TEST_PHONE_2, "montant": 5_000},
        )
        assert resp.status_code == 402

    async def test_montant_minimum_transfert(
        self, client: AsyncClient, user_with_funded_wallet: dict
    ):
        resp = await client.post(
            "/api/v1/wallet/me/transfer",
            headers=user_with_funded_wallet["headers"],
            json={"destinataire_telephone": TEST_PHONE_2, "montant": 50},
        )
        assert resp.status_code == 422

    async def test_sans_wallet_retourne_404(
        self, client: AsyncClient, auth_tokens: dict, chauffeur_user: dict
    ):
        headers = {"Authorization": f"Bearer {auth_tokens['access_token']}"}
        resp = await client.post(
            "/api/v1/wallet/me/transfer",
            headers=headers,
            json={"destinataire_telephone": TEST_PHONE_2, "montant": 1_000},
        )
        assert resp.status_code == 404