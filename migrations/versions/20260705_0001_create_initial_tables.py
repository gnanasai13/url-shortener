"""create initial tables

Revision ID: 20260705_0001
Revises: None
Create Date: 2026-07-05 00:01:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260705_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table("short_urls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("short_code", sa.String(length=32), nullable=False),
        sa.Column("custom_alias", sa.String(length=64), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("clicks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_short_urls_custom_alias"), "short_urls", ["custom_alias"], unique=True)
    op.create_index(op.f("ix_short_urls_id"), "short_urls", ["id"], unique=False)
    op.create_index("ix_short_urls_owner_created_at", "short_urls", ["owner_id", "created_at"], unique=False)
    op.create_index("ix_short_urls_owner_is_active", "short_urls", ["owner_id", "is_active"], unique=False)
    op.create_index(op.f("ix_short_urls_owner_id"), "short_urls", ["owner_id"], unique=False)
    op.create_index(op.f("ix_short_urls_short_code"), "short_urls", ["short_code"], unique=True)

    op.create_table("click_analytics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url_id", sa.Integer(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("browser", sa.String(length=120), nullable=True),
        sa.Column("device", sa.String(length=120), nullable=True),
        sa.Column("os", sa.String(length=120), nullable=True),
        sa.Column("referrer", sa.String(length=2048), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["url_id"], ["short_urls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_click_analytics_id"), "click_analytics", ["id"], unique=False)
    op.create_index(op.f("ix_click_analytics_url_id"), "click_analytics", ["url_id"], unique=False)
    op.create_index("ix_click_analytics_url_country", "click_analytics", ["url_id", "country"], unique=False)
    op.create_index("ix_click_analytics_url_timestamp", "click_analytics", ["url_id", "timestamp"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_click_analytics_url_timestamp", table_name="click_analytics")
    op.drop_index("ix_click_analytics_url_country", table_name="click_analytics")
    op.drop_index(op.f("ix_click_analytics_url_id"), table_name="click_analytics")
    op.drop_index(op.f("ix_click_analytics_id"), table_name="click_analytics")
    op.drop_table("click_analytics")
    op.drop_index(op.f("ix_short_urls_short_code"), table_name="short_urls")
    op.drop_index(op.f("ix_short_urls_owner_id"), table_name="short_urls")
    op.drop_index("ix_short_urls_owner_is_active", table_name="short_urls")
    op.drop_index("ix_short_urls_owner_created_at", table_name="short_urls")
    op.drop_index(op.f("ix_short_urls_id"), table_name="short_urls")
    op.drop_index(op.f("ix_short_urls_custom_alias"), table_name="short_urls")
    op.drop_table("short_urls")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
