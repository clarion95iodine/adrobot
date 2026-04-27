from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .editor import (
    add_offer,
    current_state_label,
    ensure_draft,
    hydrate_offer_names,
    merge_main_state,
    normalize_fetched_flow,
    push_flow_to_keitaro,
    remove_offer,
    revive_offer,
    toggle_pin,
    visible_state,
)
from .keitaro import KeitaroAPIError, KeitaroClient
from .models import CampaignCache, CampaignFlowState, CampaignRecord
from .schemas import (
    CampaignCreateRequest,
    CampaignCreateResponse,
    CampaignEditorResponse,
    CampaignListItem,
    FlowActionRequest,
    FlowActionResponse,
    FlowStateResponse,
    KTSyncResponse,
    KeitaroConfigResponse,
    OfferSearchResult,
    ResolvedObject,
)

settings = get_settings()
client = KeitaroClient(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    client.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin, "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DbSession = Annotated[Session, Depends(get_db)]


def _http_error(exc: KeitaroAPIError) -> HTTPException:
    detail = {"message": str(exc)}
    if exc.payload is not None:
        detail["keitaro"] = exc.payload
    return HTTPException(status_code=exc.status_code if exc.status_code >= 400 else 500, detail=detail)


def _campaign_cache_item(campaign: CampaignCache, db: Session) -> CampaignListItem:
    flow_count = db.query(func.count(CampaignFlowState.id)).filter(CampaignFlowState.kt_campaign_id == campaign.kt_campaign_id).scalar() or 0
    draft_flow_count = (
        db.query(func.count(CampaignFlowState.id))
        .filter(CampaignFlowState.kt_campaign_id == campaign.kt_campaign_id, CampaignFlowState.draft_state.is_not(None))
        .scalar()
        or 0
    )
    return CampaignListItem(
        id=campaign.id,
        kt_campaign_id=campaign.kt_campaign_id,
        name=campaign.name,
        alias=campaign.alias,
        state=campaign.state,
        domain_id=campaign.domain_id,
        group_id=campaign.group_id,
        traffic_source_id=campaign.traffic_source_id,
        flow_count=flow_count,
        draft_flow_count=draft_flow_count,
        updated_at=campaign.updated_at,
    )


def _get_campaign_or_404(db: Session, kt_campaign_id: int) -> CampaignCache:
    campaign = db.query(CampaignCache).filter(CampaignCache.kt_campaign_id == kt_campaign_id).first()
    if campaign is None:
        raise HTTPException(status_code=404, detail={"message": "Campaign not found. Sync campaigns from KT first."})
    return campaign


def _get_flow_or_404(db: Session, kt_campaign_id: int, kt_stream_id: int) -> CampaignFlowState:
    flow = (
        db.query(CampaignFlowState)
        .filter(CampaignFlowState.kt_campaign_id == kt_campaign_id, CampaignFlowState.kt_stream_id == kt_stream_id)
        .first()
    )
    if flow is None:
        raise HTTPException(status_code=404, detail={"message": "Flow not found. Fetch from KT first."})
    return flow


def _offer_lookup() -> dict[int, str]:
    try:
        offers = client.list_offers()
    except KeitaroAPIError:
        return {}
    lookup: dict[int, str] = {}
    for offer in offers:
        offer_id = offer.get("id")
        if offer_id is None:
            continue
        lookup[int(offer_id)] = str(offer.get("name") or "")
    return lookup


def _flow_response(flow: CampaignFlowState, offer_lookup: dict[int, str] | None = None) -> FlowStateResponse:
    main_state = hydrate_offer_names(flow.main_state, offer_lookup)
    draft_state = hydrate_offer_names(flow.draft_state, offer_lookup)
    return FlowStateResponse(
        id=flow.id,
        kt_stream_id=flow.kt_stream_id,
        kt_campaign_id=flow.kt_campaign_id,
        name=flow.name,
        position=flow.position,
        state=current_state_label(main_state, draft_state),
        has_draft=draft_state is not None,
        main_state=main_state,
        draft_state=draft_state,
        current_state=visible_state(main_state, draft_state),
    )


def _campaign_response(db: Session, campaign: CampaignCache) -> CampaignEditorResponse:
    flows = (
        db.query(CampaignFlowState)
        .filter(CampaignFlowState.kt_campaign_id == campaign.kt_campaign_id)
        .order_by(CampaignFlowState.position.asc(), CampaignFlowState.id.asc())
        .all()
    )
    offer_lookup = _offer_lookup()
    return CampaignEditorResponse(
        campaign=_campaign_cache_item(campaign, db),
        flows=[_flow_response(flow, offer_lookup) for flow in flows],
        state="draft" if any(flow.draft_state is not None for flow in flows) else "main",
    )


def _upsert_campaign_cache(db: Session, raw: dict) -> CampaignCache:
    kt_campaign_id = int(raw["id"])
    campaign = db.query(CampaignCache).filter(CampaignCache.kt_campaign_id == kt_campaign_id).first()
    if campaign is None:
        campaign = CampaignCache(kt_campaign_id=kt_campaign_id, name=str(raw.get("name") or ""), alias=str(raw.get("alias") or ""), state=str(raw.get("state") or "active"))
        db.add(campaign)
    campaign.name = str(raw.get("name") or "")
    campaign.alias = str(raw.get("alias") or "")
    campaign.state = str(raw.get("state") or "active")
    campaign.domain_id = raw.get("domain_id")
    campaign.group_id = raw.get("group_id")
    campaign.traffic_source_id = raw.get("traffic_source_id")
    campaign.raw = raw
    return campaign


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", response_model=KeitaroConfigResponse)
def read_config() -> KeitaroConfigResponse:
    try:
        context = client.resolve_context()
    except KeitaroAPIError as exc:
        raise _http_error(exc) from exc

    return KeitaroConfigResponse(
        base_url=settings.keitaro_base_url,
        google_url=settings.keitaro_google_url,
        has_api_key=bool(settings.keitaro_api_key),
        domain=ResolvedObject(id=context["domain"].id, name=context["domain"].name, raw=context["domain"].raw),
        group=ResolvedObject(id=context["group"].id, name=context["group"].name, raw=context["group"].raw),
        traffic_source=ResolvedObject(
            id=context["traffic_source"].id,
            name=context["traffic_source"].name,
            raw=context["traffic_source"].raw,
        ),
    )


@app.get("/api/campaigns", response_model=list[CampaignCreateResponse])
def list_created_campaigns(db: DbSession):
    items = db.query(CampaignRecord).order_by(CampaignRecord.id.desc()).all()
    return items


@app.post("/api/campaigns", response_model=CampaignCreateResponse)
def create_campaign(payload: CampaignCreateRequest, db: DbSession):
    if not settings.keitaro_api_key:
        raise HTTPException(status_code=400, detail={"message": "KEITARO_API_KEY is not set"})

    country_code = payload.country_code.strip().upper()
    alias = client.make_alias(payload.name)

    try:
        context = client.resolve_context()
        campaign = client.create_campaign(
            name=payload.name.strip(),
            alias=alias,
            domain_id=context["domain"].id,
            group_id=context["group"].id,
            traffic_source_id=context["traffic_source"].id,
        )

        google_stream = client.create_stream(
            campaign_id=campaign["id"],
            name=f"{country_code} → Google",
            action_type="http",
            schema="redirect",
            action_payload=settings.keitaro_google_url,
            filters=[{"name": "country", "mode": "accept", "payload": [country_code]}],
        )

        offer_stream = client.create_stream(
            campaign_id=campaign["id"],
            name="Offer fallback",
            action_type="http",
            schema="landings",
            offers=[{"offer_id": payload.offer_id, "share": 100}],
        )
    except KeitaroAPIError as exc:
        raise _http_error(exc) from exc

    record = CampaignRecord(
        name=payload.name.strip(),
        country_code=country_code,
        offer_id=payload.offer_id,
        alias=alias,
        keitaro_campaign_id=campaign["id"],
        keitaro_google_stream_id=google_stream["id"],
        keitaro_offer_stream_id=offer_stream["id"],
        domain_id=context["domain"].id,
        group_id=context["group"].id,
        traffic_source_id=context["traffic_source"].id,
        status="created",
        keitaro_payload={
            "campaign": campaign,
            "google_stream": google_stream,
            "offer_stream": offer_stream,
        },
        keitaro_response={
            "campaign": campaign,
            "google_stream": google_stream,
            "offer_stream": offer_stream,
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/offers/search", response_model=list[OfferSearchResult])
def search_offers(q: str = ""):
    if not settings.keitaro_api_key:
        raise HTTPException(status_code=400, detail={"message": "KEITARO_API_KEY is not set"})

    try:
        offers = client.search_offers(q, limit=10)
    except KeitaroAPIError as exc:
        raise _http_error(exc) from exc

    return [OfferSearchResult(id=offer["id"], name=str(offer.get("name") or ""), state=offer.get("state")) for offer in offers]


@app.get("/api/editor/campaigns", response_model=list[CampaignListItem])
def editor_campaigns(db: DbSession):
    items = db.query(CampaignCache).order_by(CampaignCache.updated_at.desc().nullslast(), CampaignCache.id.desc()).all()
    return [_campaign_cache_item(item, db) for item in items]


@app.post("/api/editor/campaigns/sync", response_model=KTSyncResponse)
def sync_editor_campaigns(db: DbSession):
    if not settings.keitaro_api_key:
        raise HTTPException(status_code=400, detail={"message": "KEITARO_API_KEY is not set"})

    try:
        campaigns = client.list_campaigns()
    except KeitaroAPIError as exc:
        raise _http_error(exc) from exc

    for raw in campaigns:
        _upsert_campaign_cache(db, raw)
    db.commit()
    items = db.query(CampaignCache).order_by(CampaignCache.updated_at.desc().nullslast(), CampaignCache.id.desc()).all()
    return KTSyncResponse(campaigns=[_campaign_cache_item(item, db) for item in items])


@app.get("/api/editor/campaigns/{kt_campaign_id}", response_model=CampaignEditorResponse)
def get_editor_campaign(kt_campaign_id: int, db: DbSession):
    campaign = _get_campaign_or_404(db, kt_campaign_id)
    return _campaign_response(db, campaign)


@app.post("/api/editor/campaigns/{kt_campaign_id}/fetch", response_model=CampaignEditorResponse)
def fetch_campaign_from_kt(kt_campaign_id: int, db: DbSession):
    if not settings.keitaro_api_key:
        raise HTTPException(status_code=400, detail={"message": "KEITARO_API_KEY is not set"})

    campaign = _get_campaign_or_404(db, kt_campaign_id)
    try:
        streams = client.get_campaign_streams(kt_campaign_id)
    except KeitaroAPIError as exc:
        raise _http_error(exc) from exc

    existing_flows = {
        flow.kt_stream_id: flow
        for flow in db.query(CampaignFlowState).filter(CampaignFlowState.kt_campaign_id == kt_campaign_id).all()
    }

    offer_lookup = _offer_lookup()

    for raw_stream in streams:
        fetched_flow = normalize_fetched_flow(raw_stream, offer_lookup=offer_lookup)
        flow = existing_flows.get(fetched_flow["kt_stream_id"])
        if flow is None:
            flow = CampaignFlowState(
                kt_campaign_id=kt_campaign_id,
                kt_stream_id=fetched_flow["kt_stream_id"],
                name=fetched_flow["name"],
                position=fetched_flow["position"],
                main_state=fetched_flow,
                draft_state=None,
                raw=raw_stream,
            )
            db.add(flow)
        else:
            flow.name = fetched_flow["name"]
            flow.position = fetched_flow["position"]
            flow.main_state = merge_main_state(flow.main_state, fetched_flow)
            flow.raw = raw_stream
    db.commit()
    db.refresh(campaign)
    return _campaign_response(db, campaign)


@app.post("/api/editor/campaigns/{kt_campaign_id}/push", response_model=CampaignEditorResponse)
def push_campaign_to_kt(kt_campaign_id: int, db: DbSession):
    if not settings.keitaro_api_key:
        raise HTTPException(status_code=400, detail={"message": "KEITARO_API_KEY is not set"})

    campaign = _get_campaign_or_404(db, kt_campaign_id)
    flows = (
        db.query(CampaignFlowState)
        .filter(CampaignFlowState.kt_campaign_id == kt_campaign_id, CampaignFlowState.draft_state.is_not(None))
        .order_by(CampaignFlowState.position.asc(), CampaignFlowState.id.asc())
        .all()
    )

    try:
        for flow in flows:
            if flow.draft_state is None:
                continue
            push_flow_to_keitaro(client, flow.kt_stream_id, flow.draft_state)
            flow.main_state = flow.draft_state
            flow.draft_state = None
    except KeitaroAPIError as exc:
        raise _http_error(exc) from exc

    db.commit()
    db.refresh(campaign)
    return _campaign_response(db, campaign)


@app.post("/api/editor/campaigns/{kt_campaign_id}/cancel", response_model=CampaignEditorResponse)
def cancel_campaign_drafts(kt_campaign_id: int, db: DbSession):
    campaign = _get_campaign_or_404(db, kt_campaign_id)
    flows = db.query(CampaignFlowState).filter(CampaignFlowState.kt_campaign_id == kt_campaign_id).all()
    for flow in flows:
        flow.draft_state = None
    db.commit()
    db.refresh(campaign)
    return _campaign_response(db, campaign)


@app.post("/api/editor/campaigns/{kt_campaign_id}/flows/{kt_stream_id}/actions", response_model=FlowActionResponse)
def mutate_flow(
    kt_campaign_id: int,
    kt_stream_id: int,
    payload: FlowActionRequest,
    db: DbSession,
):
    campaign = _get_campaign_or_404(db, kt_campaign_id)
    flow = _get_flow_or_404(db, kt_campaign_id, kt_stream_id)

    action = payload.action
    draft_affecting_actions = {"add_offer", "remove_offer", "revive_offer"}
    pin_action = action == "toggle_pin"
    working = ensure_draft(flow.main_state or {"offers": []}, flow.draft_state)

    try:
        if action == "add_offer":
            if payload.offer_id is None or not payload.name:
                raise HTTPException(status_code=400, detail={"message": "offer_id and name are required"})
            add_offer(working, payload.offer_id, payload.name)
        elif action == "remove_offer":
            if payload.offer_id is None:
                raise HTTPException(status_code=400, detail={"message": "offer_id is required"})
            remove_offer(working, payload.offer_id)
        elif action == "revive_offer":
            if payload.offer_id is None:
                raise HTTPException(status_code=400, detail={"message": "offer_id is required"})
            revive_offer(working, payload.offer_id)
        elif pin_action:
            if payload.offer_id is None:
                raise HTTPException(status_code=400, detail={"message": "offer_id is required"})
            toggle_pin(working, payload.offer_id)
        else:
            raise HTTPException(status_code=400, detail={"message": f"Unsupported action: {action}"})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc

    if action in draft_affecting_actions:
        flow.draft_state = working
    elif pin_action and flow.draft_state is None:
        flow.main_state = working
    else:
        flow.draft_state = working
    db.commit()
    db.refresh(campaign)
    db.refresh(flow)
    return FlowActionResponse(flow=_flow_response(flow, _offer_lookup()), campaign=_campaign_response(db, campaign))
