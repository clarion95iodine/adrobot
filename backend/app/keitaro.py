from __future__ import annotations

from dataclasses import dataclass
import re
import uuid
from typing import Any

import httpx

from .config import Settings


class KeitaroAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str, payload: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass(frozen=True)
class ResolvedKeitaroObject:
    id: int
    name: str | None
    raw: dict[str, Any]


class KeitaroClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.Client(
            base_url=settings.keitaro_base_url,
            timeout=30.0,
            headers={
                "api-key": settings.keitaro_api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "adrobot/1.0",
            },
        )

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> Any:
        response = self._client.request(method, path, params=params, json=json)
        if response.status_code >= 400:
            message = response.text
            try:
                data = response.json()
                if isinstance(data, dict):
                    message = data.get("error") or data.get("message") or response.text
                    raise KeitaroAPIError(response.status_code, message, data)
            except ValueError:
                pass
            raise KeitaroAPIError(response.status_code, message)
        if not response.text.strip():
            return None
        return response.json()

    def list_domains(self) -> list[dict[str, Any]]:
        result = self.request("GET", "/domains")
        return result if isinstance(result, list) else []

    def list_groups(self, group_type: str) -> list[dict[str, Any]]:
        result = self.request("GET", "/groups", params={"type": group_type})
        return result if isinstance(result, list) else []

    def list_traffic_sources(self) -> list[dict[str, Any]]:
        result = self.request("GET", "/traffic_sources")
        return result if isinstance(result, list) else []

    def list_campaigns(self) -> list[dict[str, Any]]:
        result = self.request("GET", "/campaigns")
        return result if isinstance(result, list) else []

    def get_campaign_streams(self, campaign_id: int) -> list[dict[str, Any]]:
        result = self.request("GET", f"/campaigns/{campaign_id}/streams")
        return result if isinstance(result, list) else []

    def update_stream(self, stream_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.request("PUT", f"/streams/{stream_id}", json=payload)
        return result if isinstance(result, dict) else {}

    def list_offers(self) -> list[dict[str, Any]]:
        result = self.request("GET", "/offers")
        return result if isinstance(result, list) else []

    def search_offers(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        query = query.strip().lower()
        if not query:
            return []

        offers = self.list_offers()
        exact_matches: list[dict[str, Any]] = []
        name_matches: list[dict[str, Any]] = []
        partial_id_matches: list[dict[str, Any]] = []

        for offer in offers:
            offer_id = offer.get("id")
            offer_name = str(offer.get("name") or "")
            offer_name_lower = offer_name.lower()
            offer_id_text = str(offer_id or "")

            if query.isdigit() and offer_id_text == query:
                exact_matches.append(offer)
                continue

            if query in offer_name_lower:
                name_matches.append(offer)
                continue

            if query.isdigit() and query in offer_id_text:
                partial_id_matches.append(offer)

        ordered = exact_matches + name_matches + partial_id_matches
        seen_ids: set[int] = set()
        unique: list[dict[str, Any]] = []
        for offer in ordered:
            offer_id = offer.get("id")
            if offer_id in seen_ids:
                continue
            seen_ids.add(offer_id)
            unique.append(offer)
            if len(unique) >= limit:
                break
        return unique

    def resolve_domain(self) -> ResolvedKeitaroObject:
        if self.settings.keitaro_domain_id is not None:
            domain = self._find_by_id(self.list_domains(), self.settings.keitaro_domain_id)
            if domain:
                return ResolvedKeitaroObject(domain["id"], domain.get("name"), domain)
            raise KeitaroAPIError(400, f"Configured KEITARO_DOMAIN_ID={self.settings.keitaro_domain_id} was not found")
        domains = self.list_domains()
        if not domains:
            raise KeitaroAPIError(400, "No Keitaro domains found and KEITARO_DOMAIN_ID is not set")
        domain = domains[0]
        return ResolvedKeitaroObject(domain["id"], domain.get("name"), domain)

    def resolve_group(self) -> ResolvedKeitaroObject:
        if self.settings.keitaro_group_id is not None:
            groups = self.list_groups(self.settings.keitaro_group_type)
            group = self._find_by_id(groups, self.settings.keitaro_group_id)
            if group:
                return ResolvedKeitaroObject(group["id"], group.get("name"), group)
            raise KeitaroAPIError(400, f"Configured KEITARO_GROUP_ID={self.settings.keitaro_group_id} was not found")
        groups = self.list_groups(self.settings.keitaro_group_type)
        if not groups:
            raise KeitaroAPIError(400, f"No Keitaro groups found for type={self.settings.keitaro_group_type!r} and KEITARO_GROUP_ID is not set")
        group = groups[0]
        return ResolvedKeitaroObject(group["id"], group.get("name"), group)

    def resolve_traffic_source(self) -> ResolvedKeitaroObject:
        if self.settings.keitaro_traffic_source_id is not None:
            source = self._find_by_id(self.list_traffic_sources(), self.settings.keitaro_traffic_source_id)
            if source:
                return ResolvedKeitaroObject(source["id"], source.get("name"), source)
            raise KeitaroAPIError(400, f"Configured KEITARO_TRAFFIC_SOURCE_ID={self.settings.keitaro_traffic_source_id} was not found")
        sources = self.list_traffic_sources()
        if not sources:
            raise KeitaroAPIError(400, "No Keitaro traffic sources found and KEITARO_TRAFFIC_SOURCE_ID is not set")
        source = sources[0]
        return ResolvedKeitaroObject(source["id"], source.get("name"), source)

    def resolve_context(self) -> dict[str, ResolvedKeitaroObject]:
        return {
            "domain": self.resolve_domain(),
            "group": self.resolve_group(),
            "traffic_source": self.resolve_traffic_source(),
        }

    def create_campaign(self, *, name: str, alias: str, domain_id: int, group_id: int, traffic_source_id: int) -> dict[str, Any]:
        return self.request(
            "POST",
            "/campaigns",
            json={
                "name": name,
                "alias": alias,
                "domain_id": domain_id,
                "group_id": group_id,
                "traffic_source_id": traffic_source_id,
            },
        )

    def create_stream(
        self,
        *,
        campaign_id: int,
        name: str,
        action_type: str,
        schema: str,
        action_payload: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        offers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "campaign_id": campaign_id,
            "name": name,
            "action_type": action_type,
            "schema": schema,
        }
        if action_payload is not None:
            payload["action_payload"] = action_payload
        if filters is not None:
            payload["filters"] = filters
        if offers is not None:
            payload["offers"] = offers
        return self.request("POST", "/streams", json=payload)

    @staticmethod
    def make_alias(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
        slug = slug[:32] or "campaign"
        suffix = uuid.uuid4().hex[:8]
        return f"{slug}-{suffix}"[:63]

    @staticmethod
    def _find_by_id(items: list[dict[str, Any]], item_id: int) -> dict[str, Any] | None:
        for item in items:
            if item.get("id") == item_id:
                return item
        return None
