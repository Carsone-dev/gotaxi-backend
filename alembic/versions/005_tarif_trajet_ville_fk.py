"""tarif_trajet: replace string columns with ville FK

Revision ID: 005
Revises: 9efd9ef701fd
Create Date: 2026-06-10

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "9efd9ef701fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old unique constraint and string columns
    op.drop_constraint("uq_tarif_route", "tarifs_trajets", type_="unique")
    op.drop_column("tarifs_trajets", "ville_depart")
    op.drop_column("tarifs_trajets", "ville_arrivee")

    # Add FK columns
    op.add_column(
        "tarifs_trajets",
        sa.Column("ville_depart_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "tarifs_trajets",
        sa.Column("ville_arrivee_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_tarif_ville_depart",
        "tarifs_trajets", "villes",
        ["ville_depart_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_tarif_ville_arrivee",
        "tarifs_trajets", "villes",
        ["ville_arrivee_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_tarif_route",
        "tarifs_trajets",
        ["ville_depart_id", "ville_arrivee_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_tarif_route", "tarifs_trajets", type_="unique")
    op.drop_constraint("fk_tarif_ville_depart", "tarifs_trajets", type_="foreignkey")
    op.drop_constraint("fk_tarif_ville_arrivee", "tarifs_trajets", type_="foreignkey")
    op.drop_column("tarifs_trajets", "ville_depart_id")
    op.drop_column("tarifs_trajets", "ville_arrivee_id")

    op.add_column("tarifs_trajets", sa.Column("ville_depart", sa.String(100), nullable=False))
    op.add_column("tarifs_trajets", sa.Column("ville_arrivee", sa.String(100), nullable=False))
    op.create_unique_constraint("uq_tarif_route", "tarifs_trajets", ["ville_depart", "ville_arrivee"])
