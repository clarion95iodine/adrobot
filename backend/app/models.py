from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .database import Base


class CampaignRecord(Base):
    __tablename__ = "campaign_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    offer_id: Mapped[int] = mapped_column(Integer, nullable=False)

    alias: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    keitaro_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    keitaro_google_stream_id: Mapped[int] = mapped_column(Integer, nullable=False)
    keitaro_offer_stream_id: Mapped[int] = mapped_column(Integer, nullable=False)

    domain_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traffic_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created", server_default="created")
    keitaro_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    keitaro_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CampaignCache(Base):
    __tablename__ = "campaign_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kt_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")

    domain_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traffic_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CampaignFlowState(Base):
    __tablename__ = "campaign_flow_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kt_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kt_stream_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    main_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    draft_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
