import base64
import httpx
from uuid import uuid4
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()

_COLLECTION_V1 = "/collection/v1_0"
_DISBURSE_V1   = "/disbursement/v1_0"


class MTNMoMoError(Exception):
    pass


class MTNMoMoClient:
    def __init__(self):
        self.base_url = settings.MTN_MOMO_API_URL.rstrip("/")
        self.target_env = settings.MTN_MOMO_TARGET_ENV

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _base_headers(self, subscription_key: str) -> dict:
        return {
            "Ocp-Apim-Subscription-Key": subscription_key,
            "X-Target-Environment": self.target_env,
        }

    async def _get_token(self, product: str, api_user: str, api_key: str, subscription_key: str) -> str:
        """Récupère un Bearer token pour le produit MTN MoMo demandé.

        product: "collection" ou "disbursement"
        Token endpoint : POST /{product}/token/  (sans version dans l'URL)
        """
        credentials = base64.b64encode(f"{api_user}:{api_key}".encode()).decode()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/{product}/token/",
                headers={
                    **self._base_headers(subscription_key),
                    "Authorization": f"Basic {credentials}",
                },
            )
        if resp.status_code != 200:
            raise MTNMoMoError(f"Token fetch failed: {resp.text}")
        return resp.json()["access_token"]

    async def _collection_headers(self) -> dict:
        token = await self._get_token(
            "collection",
            settings.MTN_MOMO_API_USER,
            settings.MTN_MOMO_API_KEY,
            settings.MTN_MOMO_SUBSCRIPTION_KEY,
        )
        return {
            **self._base_headers(settings.MTN_MOMO_SUBSCRIPTION_KEY),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _disbursement_headers(self) -> dict:
        # Utilise les credentials disbursement si définis, sinon fallback sur collection
        api_user = getattr(settings, "MTN_MOMO_DISBURSE_API_USER", None) or settings.MTN_MOMO_API_USER
        api_key  = getattr(settings, "MTN_MOMO_DISBURSE_API_KEY",  None) or settings.MTN_MOMO_API_KEY
        sub_key  = getattr(settings, "MTN_MOMO_DISBURSE_SUB_KEY",  None) or settings.MTN_MOMO_SUBSCRIPTION_KEY
        token = await self._get_token("disbursement", api_user, api_key, sub_key)
        return {
            **self._base_headers(sub_key),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── Collections ───────────────────────────────────────────────────────────

    async def request_to_pay(self, amount: int, phone: str, external_id: str) -> str:
        reference_id = str(uuid4())
        headers = await self._collection_headers()
        headers["X-Reference-Id"] = reference_id

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}{_COLLECTION_V1}/requesttopay",
                headers=headers,
                json={
                    "amount": str(amount),
                    "currency": "XOF",
                    "externalId": external_id,
                    "payer": {
                        "partyIdType": "MSISDN",
                        "partyId": phone.lstrip("+"),
                    },
                    "payerMessage": "Paiement GoTaxi",
                    "payeeNote": "GoTaxi",
                },
            )
        if resp.status_code not in (200, 202):
            raise MTNMoMoError(f"RequestToPay failed: {resp.text}")
        logger.info("mtn_momo_request_to_pay", reference_id=reference_id, amount=amount)
        return reference_id

    async def get_transaction_status(self, reference_id: str) -> dict:
        headers = await self._collection_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}{_COLLECTION_V1}/requesttopay/{reference_id}",
                headers=headers,
            )
        if resp.status_code != 200:
            raise MTNMoMoError(f"Status check failed: {resp.text}")
        return resp.json()

    # ── Disbursements ─────────────────────────────────────────────────────────

    async def transfer(self, amount: int, phone: str, external_id: str) -> str:
        """Disbursement vers le téléphone du chauffeur/utilisateur."""
        reference_id = str(uuid4())
        headers = await self._disbursement_headers()
        headers["X-Reference-Id"] = reference_id

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}{_DISBURSE_V1}/transfer",
                headers=headers,
                json={
                    "amount": str(amount),
                    "currency": "XOF",
                    "externalId": external_id,
                    "payee": {
                        "partyIdType": "MSISDN",
                        "partyId": phone.lstrip("+"),
                    },
                    "payerMessage": "Reversement GoTaxi",
                    "payeeNote": "Reversement chauffeur",
                },
            )
        if resp.status_code not in (200, 202):
            raise MTNMoMoError(f"Transfer failed: {resp.text}")
        logger.info("mtn_momo_transfer", reference_id=reference_id, amount=amount)
        return reference_id


mtn_momo = MTNMoMoClient()