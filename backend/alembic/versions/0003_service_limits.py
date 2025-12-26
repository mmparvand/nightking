"""add service limits

Revision ID: 0003_service_limits
Revises: 0002_xray_snapshots
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_service_limits"
down_revision: Union[str, None] = "0002_xray_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("services", sa.Column("traffic_limit_bytes", sa.Integer(), nullable=True))
    op.add_column("services", sa.Column("traffic_used_bytes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("services", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("services", sa.Column("ip_limit", sa.Integer(), nullable=True))
    op.add_column("services", sa.Column("concurrent_limit", sa.Integer(), nullable=True))
    op.add_column("services", sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()))
    op.alter_column("services", "traffic_used_bytes", server_default=None)
    op.alter_column("services", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("services", "is_active")
    op.drop_column("services", "concurrent_limit")
    op.drop_column("services", "ip_limit")
    op.drop_column("services", "expires_at")
    op.drop_column("services", "traffic_used_bytes")
    op.drop_column("services", "traffic_limit_bytes")
