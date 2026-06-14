from uuid import UUID
from pydantic import BaseModel, Field
from app.models.transaction import TransactionOperateur


class ComptePayoutCreate(BaseModel):
    operateur: TransactionOperateur
    telephone: str = Field(..., min_length=8, max_length=20)


class ComptePayoutRead(BaseModel):
    id: UUID
    chauffeur_id: UUID
    operateur: TransactionOperateur
    telephone: str
    actif: bool

    model_config = {"from_attributes": True}
