"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resellers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("auth_username", sa.String(length=50), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resellers_id"), "resellers", ["id"], unique=False)
    op.create_unique_constraint("uq_resellers_auth_username", "resellers", ["auth_username"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("reseller_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reseller_id"], ["resellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reseller_id", sa.Integer(), nullable=True),
        sa.Column("protocol", sa.Enum("XRAY_VLESS", name="serviceprotocol"), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reseller_id"], ["resellers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "protocol", name="uq_user_protocol"),
    )
    op.create_index(op.f("ix_services_id"), "services", ["id"], unique=False)

    op.create_table(
        "subscription_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscription_tokens_id"), "subscription_tokens", ["id"], unique=False)
    op.create_unique_constraint("uq_subscription_token", "subscription_tokens", ["token"])
    op.create_unique_constraint("uq_subscription_service", "subscription_tokens", ["service_id"])


def downgrade() -> None:
    op.drop_constraint("uq_subscription_service", "subscription_tokens", type_="unique")
    op.drop_constraint("uq_subscription_token", "subscription_tokens", type_="unique")
    op.drop_index(op.f("ix_subscription_tokens_id"), table_name="subscription_tokens")
    op.drop_table("subscription_tokens")

    op.drop_index(op.f("ix_services_id"), table_name="services")
    op.drop_table("services")

    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    op.drop_constraint("uq_resellers_auth_username", "resellers", type_="unique")
    op.drop_index(op.f("ix_resellers_id"), table_name="resellers")
    op.drop_table("resellers")
