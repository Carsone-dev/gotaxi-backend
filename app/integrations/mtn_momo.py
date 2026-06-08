import httpx
from uuid import uuid4
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()

_COLLECTION_BASE = "/collection/v1_0"


class MTNMoMoError(Exception):
    pass


class MTNMoMoClient:
    def __init__(self):
        self.base_url = settings.MTN_MOMO_API_URL.rstrip("/")
        self.subscription_key = settings.MTN_MOMO_SUBSCRIPTION_KEY
        self.target_env = settings.MTN_MOMO_TARGET_ENV
        self._token: str | None = None

    def _base_headers(self) -> dict:
        return {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "X-Target-Environment": self.target_env,
        }

    async def _get_access_token(self) -> str:
        import base64
        credentials = base64.b64encode(
            f"{settings.MTN_MOMO_API_USER}:{settings.MTN_MOMO_API_KEY}".encode()
        ).decode()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}{_COLLECTION_BASE}/token/",
                headers={
                    **self._base_headers(),
                    "Authorization": f"Basic {credentials}",
                },
            )
            if resp.status_code != 200:
                raise MTNMoMoError(f"Token fetch failed: {resp.text}")
            return resp.json()["access_token"]

    async def _auth_headers(self) -> dict:
        token = await self._get_access_token()
        return {
            **self._base_headers(),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def request_to_pay(self, amount: int, phone: str, external_id: str) -> str:
        reference_id = str(uuid4())
        headers = await self._auth_headers()
        headers["X-Reference-Id"] = reference_id

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}{_COLLECTION_BASE}/requesttopay",
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
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}{_COLLECTION_BASE}/requesttopay/{reference_id}",
                headers=headers,
            )
        if resp.status_code != 200:
            raise MTNMoMoError(f"Status check failed: {resp.text}")
        return resp.json()

    async def transfer(self, amount: int, phone: str, external_id: str) -> str:
        """Disbursement vers le téléphone du chauffeur."""
        reference_id = str(uuid4())
        headers = await self._auth_headers()
        headers["X-Reference-Id"] = reference_id

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/disbursement/v1_0/transfer",
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