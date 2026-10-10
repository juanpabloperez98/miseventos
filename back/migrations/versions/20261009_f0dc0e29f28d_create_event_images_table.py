"""create event images table

Revision ID: f0dc0e29f28d
Revises: c3dcc26de3e9
Create Date: 2026-10-09 23:29:02.029744

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f0dc0e29f28d"
down_revision: Union[str, Sequence[str], None] = "c3dcc26de3e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=255), nullable=False),
        sa.Column("secure_url", sa.String(length=500), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("bytes > 0", name=op.f("ck_event_images_bytes_positive")),
        sa.CheckConstraint("height > 0", name=op.f("ck_event_images_height_positive")),
        sa.CheckConstraint("width > 0", name=op.f("ck_event_images_width_positive")),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name=op.f("fk_event_images_event_id_events"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_images")),
        sa.UniqueConstraint("event_id", name=op.f("uq_event_images_event_id")),
        sa.UniqueConstraint("public_id", name=op.f("uq_event_images_public_id")),
    )


def downgrade() -> None:
    op.drop_table("event_images")
