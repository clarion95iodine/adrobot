from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country_code: str = Field(min_length=2, max_length=8)
    offer_id: int = Field(gt=0)


class CampaignCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country_code: str
    offer_id: int
    alias: str
    keitaro_campaign_id: int
    keitaro_google_stream_id: int
    keitaro_offer_stream_id: int
    domain_id: int | None
    group_id: int | None
    traffic_source_id: int | None
    status: str
    created_at: datetime
    keitaro_payload: dict | None = None
    keitaro_response: dict | None = None


class ResolvedObject(BaseModel):
    id: int
    name: str | None = None
    raw: dict | None = None


class OfferSearchResult(BaseModel):
    id: int
    name: str
    state: str | None = None


class KeitaroConfigResponse(BaseModel):
    base_url: str
    google_url: str
    has_api_key: bool
    domain: ResolvedObject | None = None
    group: ResolvedObject | None = None
    traffic_source: ResolvedObject | None = None


class CampaignListItem(BaseModel):
    id: int
    kt_campaign_id: int
    name: str
    alias: str
    state: str
    domain_id: int | None = None
    group_id: int | None = None
    traffic_source_id: int | None = None
    flow_count: int = 0
    draft_flow_count: int = 0
    updated_at: datetime | None = None


class OfferState(BaseModel):
    offer_id: int
    name: str
    share: int
    removed: bool = False
    pinned: bool = False
    stats: dict | None = None
    trends: dict | None = None


class FlowStateResponse(BaseModel):
    id: int
    kt_stream_id: int
    kt_campaign_id: int
    name: str
    position: int
    state: str
    has_draft: bool
    main_state: dict | None = None
    draft_state: dict | None = None
    current_state: dict | None = None


class CampaignEditorResponse(BaseModel):
    campaign: CampaignListItem
    flows: list[FlowStateResponse]
    state: str


class KTSyncResponse(BaseModel):
    campaigns: list[CampaignListItem]


class FlowActionRequest(BaseModel):
    action: str = Field(pattern=r"^(add_offer|remove_offer|revive_offer|toggle_pin)$")
    offer_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, max_length=255)


class FlowActionResponse(BaseModel):
    flow: FlowStateResponse
    campaign: CampaignEditorResponse
