import httpx
from uuid import uuid4
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()


class MoovMoneyError(Exception):
    pass


class MoovMoneyClient:
    def __init__(self):
        self.base_url = settings.MOOV_MONEY_API_URL.rstrip("/")
        self.merchant_id = settings.MOOV_MONEY_MERCHANT_ID
        self.secret = settings.MOOV_MONEY_SECRET

    def _auth_headers(self) -> dict:
        import base64
        credentials = base64.b64encode(
            f"{self.merchant_id}:{self.secret}".encode()
        ).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }

    async def collect(self, amount: int, phone: str, external_id: str) -> str:
        reference_id = str(uuid4())
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/payment/collect",
                headers=self._auth_headers(),
                json={
                    "amount": amount,
                    "currency": "XOF",
                    "subscriber": {"country": "BJ", "currency": "XOF", "msisdn": phone.lstrip("+")},
                    "transaction": {"id": external_id, "description": "Paiement GoTaxi"},
                },
            )
        if resp.status_code not in (200, 201, 202):
            raise MoovMoneyError(f"Collect failed: {resp.text}")
        logger.info("moov_money_collect", reference_id=reference_id, amount=amount)
        return reference_id

    async def get_status(self, reference_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/payment/status/{reference_id}",
                headers=self._auth_headers(),
            )
        if resp.status_code != 200:
            raise MoovMoneyError(f"Status failed: {resp.text}")
        return resp.json()


moov_money = MoovMoneyClient()