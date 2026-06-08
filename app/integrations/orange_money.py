import httpx
from uuid import uuid4
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()

_TOKEN_URL = "https://api.orange.com/oauth/v3/token"


class OrangeMoneyError(Exception):
    pass


class OrangeMoneyClient:
    def __init__(self):
        self.base_url = settings.ORANGE_MONEY_API_URL.rstrip("/")
        self.client_id = settings.ORANGE_MONEY_CLIENT_ID
        self.client_secret = settings.ORANGE_MONEY_CLIENT_SECRET
        self._token: str | None = None

    async def _get_access_token(self) -> str:
        import base64
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
        if resp.status_code != 200:
            raise OrangeMoneyError(f"Token fetch failed: {resp.text}")
        return resp.json()["access_token"]

    async def initiate_payment(self, amount: int, phone: str, external_id: str) -> dict:
        token = await self._get_access_token()
        order_id = str(uuid4())
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/webpayment",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "merchant_key": self.client_id,
                    "currency": "OUV",
                    "order_id": order_id,
                    "amount": amount,
                    "return_url": "",
                    "cancel_url": "",
                    "notif_url": "",
                    "lang": "fr",
                    "reference": external_id,
                },
            )
        if resp.status_code not in (200, 201):
            raise OrangeMoneyError(f"Payment init failed: {resp.text}")
        logger.info("orange_money_payment", order_id=order_id, amount=amount)
        return resp.json()

    async def get_status(self, order_id: str) -> dict:
        token = await self._get_access_token()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/webpayment/{order_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code != 200:
            raise OrangeMoneyError(f"Status failed: {resp.text}")
        return resp.json()


orange_money = OrangeMoneyClient()