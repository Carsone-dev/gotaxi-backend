"""Intégration FedaPay — agrégateur Mobile Money (MTN, Moov, Orange…).

Doc officielle : https://docs.fedapay.com
Sandbox : https://sandbox-api.fedapay.com/v1
Production : https://api.fedapay.com/v1

Flux Collection (recharge wallet) :
  1. POST /transactions              → crée la transaction, retourne l'id
  2. POST /transactions/{id}/token  → retourne token + payment_url
  3. GET  /transactions/{id}         → vérifie le statut (pending / approved / declined / transferred)

  L'utilisateur ouvre le payment_url (checkout FedaPay), choisit son opérateur
  et confirme le paiement USSD. Le webhook ou le polling met à jour le statut.

Flux Payout (retrait wallet) :
  1. POST /payouts                   → crée le payout
  2. POST /payouts/{id}/send_now     → envoie immédiatement
  3. GET  /payouts/{id}              → vérifie le statut (pending / sent / failed)
"""
import re
import httpx
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()

_SUCCESS_STATUSES_COLLECT = {"approved", "transferred"}
_FAILED_STATUSES_COLLECT  = {"declined", "cancelled", "refunded"}
_SUCCESS_STATUSES_PAYOUT  = {"sent"}
_FAILED_STATUSES_PAYOUT   = {"failed", "cancelled"}


class FedaPayError(Exception):
    pass


class FedaPayClient:
    def __init__(self):
        self.base_url = settings.FEDAPAY_API_URL.rstrip("/")
        self.api_key  = settings.FEDAPAY_API_KEY

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        if not self.api_key:
            raise FedaPayError(
                "FEDAPAY_API_KEY non configurée. "
                "Renseignez la variable dans .env pour utiliser FedaPay."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _raise_for(self, resp: httpx.Response, action: str) -> None:
        if not resp.is_success:
            raise FedaPayError(f"{action} failed [{resp.status_code}]: {resp.text}")

    @staticmethod
    def _normalize_phone_bj(phone: str) -> str:
        """Retire le préfixe pays Bénin (+229 / 229) pour ne garder que les 8 chiffres locaux.
        FedaPay avec country='BJ' attend le numéro local uniquement."""
        digits = re.sub(r"\D", "", phone)
        if digits.startswith("229") and len(digits) >= 11:
            digits = digits[3:]
        return digits

    # ── Collections ───────────────────────────────────────────────────────────

    async def create_transaction(
        self,
        amount: int,
        description: str,
        phone: str | None = None,
        customer_firstname: str = "Client",
        customer_lastname: str = "GoTaxi",
        customer_email: str | None = None,
    ) -> int:
        """Crée une transaction FedaPay et retourne son id numérique.

        phone est optionnel : si absent, le checkout FedaPay demande le numéro au client.
        """
        customer: dict = {
            "firstname": customer_firstname,
            "lastname": customer_lastname,
        }
        if phone:
            customer["phone_number"] = {
                "number": self._normalize_phone_bj(phone),
                "country": "BJ",
            }
        if customer_email:
            customer["email"] = customer_email

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/transactions",
                headers=self._headers(),
                json={
                    "description": description,
                    "amount": amount,
                    "currency": {"iso": "XOF"},
                    "customer": customer,
                },
            )
        self._raise_for(resp, "create_transaction")
        tx = resp.json().get("v1/transaction") or resp.json()
        tx_id = tx.get("id")
        logger.info("fedapay_transaction_created", tx_id=tx_id, amount=amount)
        return tx_id

    async def get_payment_token(self, tx_id: int) -> dict:
        """Retourne {'token': ..., 'payment_url': ...} pour le checkout FedaPay."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/transactions/{tx_id}/token",
                headers=self._headers(),
            )
        self._raise_for(resp, "get_payment_token")
        return resp.json()

    async def get_transaction_status(self, tx_id: int) -> str:
        """Retourne le statut brut FedaPay : pending / approved / declined / transferred."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/transactions/{tx_id}",
                headers=self._headers(),
            )
        self._raise_for(resp, "get_transaction_status")
        tx = resp.json().get("v1/transaction") or resp.json()
        return tx.get("status", "pending")

    def is_collection_success(self, status: str) -> bool:
        return status in _SUCCESS_STATUSES_COLLECT

    def is_collection_failed(self, status: str) -> bool:
        return status in _FAILED_STATUSES_COLLECT

    # ── Payouts ───────────────────────────────────────────────────────────────

    async def create_payout(
        self,
        amount: int,
        phone: str,
        customer_firstname: str = "Bénéficiaire",
        customer_lastname: str = "GoTaxi",
    ) -> int:
        """Crée un payout FedaPay et retourne son id."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/payouts",
                headers=self._headers(),
                json={
                    "amount": amount,
                    "currency": {"iso": "XOF"},
                    "customer": {
                        "firstname": customer_firstname,
                        "lastname": customer_lastname,
                        "phone_number": {
                            "number": self._normalize_phone_bj(phone),
                            "country": "BJ",
                        },
                    },
                },
            )
        self._raise_for(resp, "create_payout")
        payout = resp.json().get("v1/payout") or resp.json()
        payout_id = payout.get("id")
        logger.info("fedapay_payout_created", payout_id=payout_id, amount=amount)
        return payout_id

    async def send_payout(self, payout_id: int) -> None:
        """Envoie immédiatement le payout (POST /payouts/{id}/send_now)."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/payouts/{payout_id}/send_now",
                headers=self._headers(),
            )
        self._raise_for(resp, "send_payout")
        logger.info("fedapay_payout_sent", payout_id=payout_id)

    async def get_payout_status(self, payout_id: int) -> str:
        """Retourne le statut brut : pending / sent / failed."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/payouts/{payout_id}",
                headers=self._headers(),
            )
        self._raise_for(resp, "get_payout_status")
        payout = resp.json().get("v1/payout") or resp.json()
        return payout.get("status", "pending")

    def is_payout_success(self, status: str) -> bool:
        return status in _SUCCESS_STATUSES_PAYOUT

    def is_payout_failed(self, status: str) -> bool:
        return status in _FAILED_STATUSES_PAYOUT


fedapay = FedaPayClient()
