"""add nodes and service_nodes

Revision ID: 0005_nodes
Revises: 0004_reseller_business
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_nodes"
down_revision: Union[str, None] = "0004_reseller_business"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=False),
        sa.Column("ip_address", sa.String(length=100), nullable=False),
        sa.Column("api_base_url", sa.String(length=255), nullable=False),
        sa.Column("auth_token_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_nodes_id"), "nodes", ["id"], unique=False)

    op.create_table(
        "service_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_id", "node_id", name="uq_service_node"),
    )
    op.create_index(op.f("ix_service_nodes_id"), "service_nodes", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_service_nodes_id"), table_name="service_nodes")
    op.drop_table("service_nodes")
    op.drop_index(op.f("ix_nodes_id"), table_name="nodes")
    op.drop_table("nodes")
