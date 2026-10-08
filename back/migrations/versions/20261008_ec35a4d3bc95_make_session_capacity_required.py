"""make session capacity required

Revision ID: ec35a4d3bc95
Revises: c6a9a057936f
Create Date: 2026-10-08 20:11:29.125521

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "ec35a4d3bc95"
down_revision: Union[str, Sequence[str], None] = "c6a9a057936f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHECK_NAME = "ck_sessions_capacity_positive"

sessions = sa.table(
    "sessions", sa.column("event_id", sa.Integer), sa.column("capacity", sa.Integer)
)
events = sa.table("events", sa.column("id", sa.Integer), sa.column("capacity", sa.Integer))


def upgrade() -> None:
    # Sessions without capacity were only limited by their event, so they inherit its capacity.
    event_capacity = (
        sa.select(events.c.capacity).where(events.c.id == sessions.c.event_id).scalar_subquery()
    )
    op.execute(
        sessions.update().where(sessions.c.capacity.is_(None)).values(capacity=event_capacity)
    )
    op.alter_column("sessions", "capacity", existing_type=sa.INTEGER(), nullable=False)
    op.drop_constraint(op.f(CHECK_NAME), "sessions", type_="check")
    op.create_check_constraint(op.f(CHECK_NAME), "sessions", "capacity > 0")


def downgrade() -> None:
    op.drop_constraint(op.f(CHECK_NAME), "sessions", type_="check")
    op.create_check_constraint(op.f(CHECK_NAME), "sessions", "capacity IS NULL OR capacity > 0")
    op.alter_column("sessions", "capacity", existing_type=sa.INTEGER(), nullable=True)
