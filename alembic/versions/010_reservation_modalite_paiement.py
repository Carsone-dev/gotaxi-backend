"""reservation modalite_paiement

Revision ID: 010
Revises: 9efd9ef701fd
Create Date: 2026-06-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE modalitepaiementreservation AS ENUM ('WALLET', 'ESPECES')")
    op.add_column(
        "reservations",
        sa.Column(
            "modalite_paiement",
            sa.Enum("WALLET", "ESPECES", name="modalitepaiementreservation"),
            nullable=False,
            server_default="WALLET",
        ),
    )


def downgrade() -> None:
    op.drop_column("reservations", "modalite_paiement")
    op.execute("DROP TYPE modalitepaiementreservation")
