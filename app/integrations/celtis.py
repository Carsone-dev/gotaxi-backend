"""Intégration Celtis (Celtiis Bénin — BiBi Money).

Sandbox : https://api-sandbox.celtiis.bj
Doc : fournie par Celtiis (voir portail développeur)

Flux Collection (recharge wallet) :
  1. POST /oauth2/token          → Bearer token
  2. POST /v1/payment/collect    → initie le débit USSD (202 Accepted)
  3. GET  /v1/payment/{txId}     → vérifie le statut (PENDING / SUCCESS / FAILED)

Flux Disbursement (retrait wallet) :
  1. POST /oauth2/token          → Bearer token
  2. POST /v1/payment/disburse   → virement vers le téléphone (202 Accepted)
  3. GET  /v1/payment/{txId}     → vérifie le statut
"""
import httpx
from uuid import uuid4
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()


class CeltisError(Exception):
    pass


class CeltisClient:
    def __init__(self):
        self.base_url = settings.CELTIS_API_URL.rstrip("/")
        self.client_id = settings.CELTIS_CLIENT_ID
        self.client_secret = settings.CELTIS_CLIENT_SECRET
        self.merchant_id = settings.CELTIS_MERCHANT_ID

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def _get_token(self) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise CeltisError(f"Token fetch failed: {resp.text}")
        return resp.json()["access_token"]

    async def _headers(self) -> dict:
        token = await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Merchant-Id": self.merchant_id,
        }

    # ── Collection ────────────────────────────────────────────────────────────

    async def collect(self, amount: int, phone: str, external_id: str) -> str:
        """Initie un débit USSD Celtis. Retourne le txId Celtis."""
        tx_id = str(uuid4())
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/v1/payment/collect",
                headers=headers,
                json={
                    "transactionId": tx_id,
                    "externalRef": external_id,
                    "amount": amount,
                    "currency": "XOF",
                    "msisdn": phone.lstrip("+"),
                    "description": "Recharge GoTaxi",
                },
            )
        if resp.status_code not in (200, 201, 202):
            raise CeltisError(f"Collect failed [{resp.status_code}]: {resp.text}")
        logger.info("celtis_collect", tx_id=tx_id, amount=amount, phone=phone)
        return tx_id

    async def get_status(self, tx_id: str) -> dict:
        """Retourne le statut d'une transaction Celtis."""
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/v1/payment/{tx_id}",
                headers=headers,
            )
        if resp.status_code != 200:
            raise CeltisError(f"Status check failed: {resp.text}")
        return resp.json()

    # ── Disbursement ──────────────────────────────────────────────────────────

    async def disburse(self, amount: int, phone: str, external_id: str) -> str:
        """Initie un virement vers un abonné Celtis."""
        tx_id = str(uuid4())
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/v1/payment/disburse",
                headers=headers,
                json={
                    "transactionId": tx_id,
                    "externalRef": external_id,
                    "amount": amount,
                    "currency": "XOF",
                    "msisdn": phone.lstrip("+"),
                    "description": "Reversement GoTaxi",
                },
            )
        if resp.status_code not in (200, 201, 202):
            raise CeltisError(f"Disburse failed [{resp.status_code}]: {resp.text}")
        logger.info("celtis_disburse", tx_id=tx_id, amount=amount, phone=phone)
        return tx_id


celtis = CeltisClient()
