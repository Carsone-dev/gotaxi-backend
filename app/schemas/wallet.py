from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.transaction import TransactionType, TransactionStatut, TransactionOperateur


class WalletPublic(BaseModel):
    user_id: UUID
    nom: str
    prenom: str
    telephone: str
    actif: bool


class WalletRead(BaseModel):
    id: UUID
    solde: int
    devise: str
    actif: bool

    model_config = {"from_attributes": True}


class RechargeInitiateResponse(BaseModel):
    message: str
    payment_url: str | None = None


class RechargeInitiateRequest(BaseModel):
    montant: int = Field(..., ge=500, le=1000000)
    operateur: TransactionOperateur
    telephone: str


class WithdrawRequest(BaseModel):
    montant: int = Field(..., ge=500)
    telephone: str
    operateur: TransactionOperateur


class TransferRequest(BaseModel):
    destinataire_telephone: str
    montant: int = Field(..., ge=100)


class TransactionRead(BaseModel):
    id: UUID
    type: TransactionType
    statut: TransactionStatut
    operateur: TransactionOperateur
    montant: int
    reference_externe: str | None = None
    reservation_id: UUID | None = None
    colis_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}