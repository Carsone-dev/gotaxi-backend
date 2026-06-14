"""add villes gares

Revision ID: 9efd9ef701fd
Revises: 004
Create Date: 2026-06-10 17:12:23.241935

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '9efd9ef701fd'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tarifs_trajets',
        sa.Column('ville_depart', sa.String(length=100), nullable=False),
        sa.Column('ville_arrivee', sa.String(length=100), nullable=False),
        sa.Column('prix_recommande', sa.Integer(), nullable=False),
        sa.Column('prix_max', sa.Integer(), nullable=False),
        sa.Column('actif', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tarifs_trajets')),
        sa.UniqueConstraint('ville_depart', 'ville_arrivee', name='uq_tarif_route'),
    )
    op.create_table(
        'villes',
        sa.Column('nom', sa.String(length=100), nullable=False),
        sa.Column('actif', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_villes')),
        sa.UniqueConstraint('nom', name=op.f('uq_villes_nom')),
    )
    op.create_table(
        'gares',
        sa.Column('nom', sa.String(length=200), nullable=False),
        sa.Column('ville_id', sa.Uuid(), nullable=False),
        sa.Column('adresse', sa.String(length=300), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('actif', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ville_id'], ['villes.id'], name=op.f('fk_gares_ville_id_villes'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_gares')),
    )


def downgrade() -> None:
    op.drop_table('gares')
    op.drop_table('villes')
    op.drop_table('tarifs_trajets')
