from __future__ import annotations

from dataclasses import dataclass
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return int(value)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "adrobot")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/adrobot.db")

    keitaro_base_url: str = os.getenv(
        "KEITARO_BASE_URL",
        "https://tlgk.host/admin_api/v1",
    ).rstrip("/")
    keitaro_api_key: str = os.getenv("KEITARO_API_KEY", "")

    keitaro_domain_id: int | None = _int_or_none(os.getenv("KEITARO_DOMAIN_ID"))
    keitaro_group_id: int | None = _int_or_none(os.getenv("KEITARO_GROUP_ID"))
    keitaro_traffic_source_id: int | None = _int_or_none(os.getenv("KEITARO_TRAFFIC_SOURCE_ID"))

    keitaro_google_url: str = os.getenv("KEITARO_GOOGLE_URL", "https://www.google.com/")
    keitaro_group_type: str = os.getenv("KEITARO_GROUP_TYPE", "campaigns")
    cors_origin: str = os.getenv("CORS_ORIGIN", "http://localhost:5173")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
