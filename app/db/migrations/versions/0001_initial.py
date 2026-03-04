"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-03 18:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    trend_type = postgresql.ENUM("photo", "video", name="trendtype", create_type=False)
    asset_kind = postgresql.ENUM("image", "video", "other", name="assetkind", create_type=False)
    generation_status = postgresql.ENUM(
        "queued",
        "running",
        "done",
        "failed",
        name="generationstatus",
        create_type=False,
    )

    postgresql.ENUM("photo", "video", name="trendtype").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("image", "video", "other", name="assetkind").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("queued", "running", "done", "failed", name="generationstatus").create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_key", sa.String(length=128), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("token_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("api_key"),
    )
    op.create_index("ix_users_api_key", "users", ["api_key"], unique=True)

    op.create_table(
        "trends",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("type", trend_type, nullable=False),
        sa.Column("preview_asset_id", sa.Integer(), nullable=True),
        sa.Column("preview_url", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("is_popular", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("price_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_template", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", asset_kind, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_assets_sha256", "assets", ["sha256"], unique=False)

    op.create_table(
        "generations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trend_id", sa.Integer(), sa.ForeignKey("trends.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("resources", sa.JSON(), nullable=False),
        sa.Column("status", generation_status, nullable=False),
        sa.Column("price_tokens", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=150), nullable=False),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_generations_user_id", "generations", ["user_id"], unique=False)
    op.create_index("ix_generations_trend_id", "generations", ["trend_id"], unique=False)
    op.create_index("ix_generations_status", "generations", ["status"], unique=False)

    op.create_table(
        "generation_assets",
        sa.Column("generation_id", sa.String(length=36), sa.ForeignKey("generations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.UniqueConstraint("generation_id", "asset_id", name="uq_generation_asset"),
    )

    op.create_table(
        "token_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_id", sa.String(length=36), sa.ForeignKey("generations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_before", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_token_transactions_user_id", "token_transactions", ["user_id"], unique=False)
    op.create_index("ix_token_transactions_generation_id", "token_transactions", ["generation_id"], unique=False)

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("generation_id", sa.String(length=36), sa.ForeignKey("generations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "key", name="uq_user_idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_index("ix_token_transactions_generation_id", table_name="token_transactions")
    op.drop_index("ix_token_transactions_user_id", table_name="token_transactions")
    op.drop_table("token_transactions")
    op.drop_table("generation_assets")
    op.drop_index("ix_generations_status", table_name="generations")
    op.drop_index("ix_generations_trend_id", table_name="generations")
    op.drop_index("ix_generations_user_id", table_name="generations")
    op.drop_table("generations")
    op.drop_index("ix_assets_sha256", table_name="assets")
    op.drop_table("assets")
    op.drop_table("trends")
    op.drop_index("ix_users_api_key", table_name="users")
    op.drop_table("users")

    sa.Enum(name="generationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="assetkind").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="trendtype").drop(op.get_bind(), checkfirst=True)
