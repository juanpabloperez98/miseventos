"""create seed records table

Revision ID: c3dcc26de3e9
Revises: ec35a4d3bc95
Create Date: 2026-10-09 00:28:57.328945

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3dcc26de3e9"
down_revision: Union[str, Sequence[str], None] = "ec35a4d3bc95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seed_records",
        sa.Column("seed_key", sa.String(length=150), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum(
                "SPEAKER",
                "EVENT",
                "SESSION",
                name="seed_entity_type",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("seed_key", name=op.f("pk_seed_records")),
    )


def downgrade() -> None:
    op.drop_table("seed_records")
