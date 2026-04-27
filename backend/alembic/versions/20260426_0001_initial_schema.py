"""initial schema

Revision ID: 20260426_0001
Revises: 
Create Date: 2026-04-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260426_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("campaign_records"):
        op.create_table(
            "campaign_records",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("country_code", sa.String(length=8), nullable=False),
            sa.Column("offer_id", sa.Integer(), nullable=False),
            sa.Column("alias", sa.String(length=255), nullable=False),
            sa.Column("keitaro_campaign_id", sa.Integer(), nullable=False),
            sa.Column("keitaro_google_stream_id", sa.Integer(), nullable=False),
            sa.Column("keitaro_offer_stream_id", sa.Integer(), nullable=False),
            sa.Column("domain_id", sa.Integer(), nullable=True),
            sa.Column("group_id", sa.Integer(), nullable=True),
            sa.Column("traffic_source_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), server_default="created", nullable=False),
            sa.Column("keitaro_payload", sa.JSON(), nullable=True),
            sa.Column("keitaro_response", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("alias"),
            sa.UniqueConstraint("keitaro_campaign_id"),
        )
        op.create_index(op.f("ix_campaign_records_id"), "campaign_records", ["id"], unique=False)
        op.create_index(op.f("ix_campaign_records_alias"), "campaign_records", ["alias"], unique=False)
        op.create_index(op.f("ix_campaign_records_country_code"), "campaign_records", ["country_code"], unique=False)
        op.create_index(op.f("ix_campaign_records_keitaro_campaign_id"), "campaign_records", ["keitaro_campaign_id"], unique=False)
        op.create_index(op.f("ix_campaign_records_name"), "campaign_records", ["name"], unique=False)

    if not inspector.has_table("campaign_cache"):
        op.create_table(
            "campaign_cache",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("kt_campaign_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("alias", sa.String(length=255), nullable=False),
            sa.Column("state", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("domain_id", sa.Integer(), nullable=True),
            sa.Column("group_id", sa.Integer(), nullable=True),
            sa.Column("traffic_source_id", sa.Integer(), nullable=True),
            sa.Column("raw", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("kt_campaign_id"),
        )
        op.create_index(op.f("ix_campaign_cache_id"), "campaign_cache", ["id"], unique=False)
        op.create_index(op.f("ix_campaign_cache_alias"), "campaign_cache", ["alias"], unique=False)
        op.create_index(op.f("ix_campaign_cache_kt_campaign_id"), "campaign_cache", ["kt_campaign_id"], unique=False)
        op.create_index(op.f("ix_campaign_cache_name"), "campaign_cache", ["name"], unique=False)

    if not inspector.has_table("campaign_flow_state"):
        op.create_table(
            "campaign_flow_state",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("kt_campaign_id", sa.Integer(), nullable=False),
            sa.Column("kt_stream_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("main_state", sa.JSON(), nullable=True),
            sa.Column("draft_state", sa.JSON(), nullable=True),
            sa.Column("raw", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("kt_stream_id"),
        )
        op.create_index(op.f("ix_campaign_flow_state_id"), "campaign_flow_state", ["id"], unique=False)
        op.create_index(op.f("ix_campaign_flow_state_kt_campaign_id"), "campaign_flow_state", ["kt_campaign_id"], unique=False)
        op.create_index(op.f("ix_campaign_flow_state_kt_stream_id"), "campaign_flow_state", ["kt_stream_id"], unique=False)
        op.create_index(op.f("ix_campaign_flow_state_name"), "campaign_flow_state", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_flow_state_name"), table_name="campaign_flow_state")
    op.drop_index(op.f("ix_campaign_flow_state_kt_stream_id"), table_name="campaign_flow_state")
    op.drop_index(op.f("ix_campaign_flow_state_kt_campaign_id"), table_name="campaign_flow_state")
    op.drop_index(op.f("ix_campaign_flow_state_id"), table_name="campaign_flow_state")
    op.drop_table("campaign_flow_state")

    op.drop_index(op.f("ix_campaign_cache_name"), table_name="campaign_cache")
    op.drop_index(op.f("ix_campaign_cache_kt_campaign_id"), table_name="campaign_cache")
    op.drop_index(op.f("ix_campaign_cache_alias"), table_name="campaign_cache")
    op.drop_index(op.f("ix_campaign_cache_id"), table_name="campaign_cache")
    op.drop_table("campaign_cache")

    op.drop_index(op.f("ix_campaign_records_name"), table_name="campaign_records")
    op.drop_index(op.f("ix_campaign_records_keitaro_campaign_id"), table_name="campaign_records")
    op.drop_index(op.f("ix_campaign_records_country_code"), table_name="campaign_records")
    op.drop_index(op.f("ix_campaign_records_alias"), table_name="campaign_records")
    op.drop_index(op.f("ix_campaign_records_id"), table_name="campaign_records")
    op.drop_table("campaign_records")
