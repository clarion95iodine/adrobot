from __future__ import annotations

import copy
from typing import Any

from .keitaro import KeitaroClient


PLACEHOLDER_STATS = {"clicks": None, "conversions": None}
PLACEHOLDER_TRENDS = {"clicks": None, "conversions": None}


def empty_offer_stats() -> dict[str, Any]:
    return copy.deepcopy(PLACEHOLDER_STATS)


def empty_offer_trends() -> dict[str, Any]:
    return copy.deepcopy(PLACEHOLDER_TRENDS)


def normalize_offer(
    raw: dict[str, Any],
    *,
    removed: bool = False,
    pinned: bool = False,
    offer_lookup: dict[int, str] | None = None,
) -> dict[str, Any]:
    offer_id = int(raw.get("offer_id") or raw.get("id") or 0)
    name = str(raw.get("name") or raw.get("offer_name") or "")
    if not name and offer_lookup:
        name = offer_lookup.get(offer_id, "")
    return {
        "offer_id": offer_id,
        "name": name,
        "share": int(raw.get("share") or 0),
        "removed": removed or bool(raw.get("removed", False)),
        "pinned": pinned or bool(raw.get("pinned", False)),
        "stats": copy.deepcopy(raw.get("stats") or empty_offer_stats()),
        "trends": copy.deepcopy(raw.get("trends") or empty_offer_trends()),
    }


def normalize_fetched_flow(raw: dict[str, Any], offer_lookup: dict[int, str] | None = None) -> dict[str, Any]:
    offers = [normalize_offer(offer, removed=False, offer_lookup=offer_lookup) for offer in raw.get("offers", [])]
    flow = {
        "kt_stream_id": int(raw["id"]),
        "name": str(raw.get("name") or ""),
        "position": int(raw.get("position") or 0),
        "action_type": raw.get("action_type"),
        "schema": raw.get("schema"),
        "action_payload": raw.get("action_payload") or "",
        "filters": copy.deepcopy(raw.get("filters") or []),
        "offers": offers,
    }
    return flow


def clone_state(state: dict[str, Any] | None) -> dict[str, Any]:
    if state is None:
        return {"offers": []}
    return copy.deepcopy(state)


def merge_main_state(existing: dict[str, Any] | None, fetched: dict[str, Any]) -> dict[str, Any]:
    existing = existing or {}
    existing_offers = {int(offer.get("offer_id")): offer for offer in existing.get("offers", [])}
    fetched_offers = []
    fetched_ids: set[int] = set()

    for offer in fetched.get("offers", []):
        offer_id = int(offer["offer_id"])
        fetched_ids.add(offer_id)
        prev = existing_offers.get(offer_id)
        merged = normalize_offer(offer, removed=False)
        if prev is not None:
            merged["pinned"] = bool(prev.get("pinned", False))
            merged["stats"] = copy.deepcopy(prev.get("stats") or empty_offer_stats())
            merged["trends"] = copy.deepcopy(prev.get("trends") or empty_offer_trends())
        fetched_offers.append(merged)

    for offer_id, prev in existing_offers.items():
        if offer_id in fetched_ids:
            continue
        removed_offer = copy.deepcopy(prev)
        removed_offer["removed"] = True
        removed_offer["share"] = 0
        removed_offer["pinned"] = bool(prev.get("pinned", False))
        fetched_offers.append(removed_offer)

    merged = {
        **copy.deepcopy(fetched),
        "offers": fetched_offers,
    }
    return merged


def ensure_draft(main_state: dict[str, Any], draft_state: dict[str, Any] | None) -> dict[str, Any]:
    return copy.deepcopy(draft_state or main_state)


def rebalance_shares(flow_state: dict[str, Any]) -> dict[str, Any]:
    offers = flow_state.get("offers", [])
    active = [offer for offer in offers if not offer.get("removed")]
    pinned = [offer for offer in active if offer.get("pinned")]
    unpinned = [offer for offer in active if not offer.get("pinned")]

    pinned_total = sum(int(offer.get("share") or 0) for offer in pinned)
    remaining = max(0, 100 - pinned_total)

    if unpinned:
        base = remaining // len(unpinned)
        extra = remaining % len(unpinned)
        for idx, offer in enumerate(unpinned):
            offer["share"] = base + (1 if idx < extra else 0)
    for offer in pinned:
        offer["share"] = int(offer.get("share") or 0)
    for offer in offers:
        if offer.get("removed"):
            offer["share"] = 0
    return flow_state


def add_offer(flow_state: dict[str, Any], offer_id: int, name: str) -> dict[str, Any]:
    offers = flow_state.setdefault("offers", [])
    if any(int(offer.get("offer_id")) == offer_id for offer in offers):
        raise ValueError("Offer already exists in this flow")
    offers.append(
        {
            "offer_id": offer_id,
            "name": name,
            "share": 0,
            "removed": False,
            "pinned": False,
            "stats": empty_offer_stats(),
            "trends": empty_offer_trends(),
        }
    )
    return rebalance_shares(flow_state)


def remove_offer(flow_state: dict[str, Any], offer_id: int) -> dict[str, Any]:
    offer = _find_offer(flow_state, offer_id)
    if offer is None:
        raise ValueError("Offer not found")
    offer["removed"] = True
    offer["pinned"] = False
    offer["share"] = 0
    return rebalance_shares(flow_state)


def revive_offer(flow_state: dict[str, Any], offer_id: int) -> dict[str, Any]:
    offer = _find_offer(flow_state, offer_id)
    if offer is None:
        raise ValueError("Offer not found")
    offer["removed"] = False
    return rebalance_shares(flow_state)


def toggle_pin(flow_state: dict[str, Any], offer_id: int) -> dict[str, Any]:
    offer = _find_offer(flow_state, offer_id)
    if offer is None:
        raise ValueError("Offer not found")
    if offer.get("removed"):
        raise ValueError("Cannot pin a removed offer")
    was_pinned = bool(offer.get("pinned"))
    offer["pinned"] = not was_pinned
    if was_pinned:
        return flow_state
    return rebalance_shares(flow_state)


def hydrate_offer_names(state: dict[str, Any] | None, offer_lookup: dict[int, str] | None) -> dict[str, Any] | None:
    if state is None:
        return None
    hydrated = copy.deepcopy(state)
    for offer in hydrated.get("offers", []):
        offer_id = int(offer.get("offer_id") or 0)
        if not offer.get("name") and offer_lookup:
            offer["name"] = offer_lookup.get(offer_id, "")
    return hydrated


def visible_state(main_state: dict[str, Any] | None, draft_state: dict[str, Any] | None) -> dict[str, Any]:
    return copy.deepcopy(draft_state or main_state or {"offers": []})


def current_state_label(main_state: dict[str, Any] | None, draft_state: dict[str, Any] | None) -> str:
    return "draft" if draft_state is not None else "main"


def active_offers(flow_state: dict[str, Any]) -> list[dict[str, Any]]:
    return [offer for offer in flow_state.get("offers", []) if not offer.get("removed")]


def push_flow_to_keitaro(client: KeitaroClient, stream_id: int, flow_state: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "offers": [
            {"offer_id": int(offer["offer_id"]), "share": int(offer.get("share") or 0)}
            for offer in active_offers(flow_state)
        ]
    }
    return client.update_stream(stream_id, payload)


def _find_offer(flow_state: dict[str, Any], offer_id: int) -> dict[str, Any] | None:
    for offer in flow_state.get("offers", []):
        if int(offer.get("offer_id")) == offer_id:
            return offer
    return None
