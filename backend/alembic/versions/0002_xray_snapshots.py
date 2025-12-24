"""add xray config snapshots

Revision ID: 0002_xray_snapshots
Revises: 0001_initial
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_xray_snapshots"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xray_config_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("applied", sa.Boolean(), nullable=True),
        sa.Column("apply_status", sa.String(length=50), nullable=True),
        sa.Column("apply_error", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_xray_config_snapshots_id"), "xray_config_snapshots", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_xray_config_snapshots_id"), table_name="xray_config_snapshots")
    op.drop_table("xray_config_snapshots")
