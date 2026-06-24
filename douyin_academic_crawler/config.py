"""Configuration loading for the Douyin academic crawler."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class CrawlerConfig:
    """Runtime settings for request pacing, cookies, and exports."""

    mock_mode: bool = True
    input_mode: str = "mock"
    input_json_file: Optional[str] = None
    allow_real_requests: bool = False
    real_request_warning_ack: bool = False
    max_pages_default: int = 1
    max_pages_hard_limit: int = 5
    max_depth_hard_limit: int = 4
    enable_text_cleaning: bool = True
    remove_emoji: bool = False
    remove_urls: bool = True
    remove_mentions: bool = False
    export_xlsx: bool = True
    cookie_file: Path = Path("cookie.txt")
    output_dir: Path = Path("exports")
    sleep_min_seconds: float = 1.0
    sleep_max_seconds: float = 2.0
    request_timeout: float = 10.0
    max_retry: int = 2
    user_agent: str = "DouyinAcademicCrawler/0.1 research-only"

    @classmethod
    def from_file(cls, path: Path | str) -> "CrawlerConfig":
        """Load crawler settings from a JSON config file."""

        config_path = Path(path)
        with config_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, Mapping):
            raise ValueError("config file must contain a JSON object")
        return cls.from_mapping(payload)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CrawlerConfig":
        """Create settings from a mapping while applying safe defaults."""

        return cls(
            mock_mode=bool(payload.get("mock_mode", cls.mock_mode)),
            input_mode=str(payload.get("input_mode", cls.input_mode)),
            input_json_file=(
                None
                if payload.get("input_json_file", cls.input_json_file) is None
                else str(payload.get("input_json_file"))
            ),
            allow_real_requests=bool(payload.get("allow_real_requests", cls.allow_real_requests)),
            real_request_warning_ack=bool(
                payload.get("real_request_warning_ack", cls.real_request_warning_ack)
            ),
            max_pages_default=int(payload.get("max_pages_default", cls.max_pages_default)),
            max_pages_hard_limit=int(
                payload.get("max_pages_hard_limit", cls.max_pages_hard_limit)
            ),
            max_depth_hard_limit=int(
                payload.get("max_depth_hard_limit", cls.max_depth_hard_limit)
            ),
            enable_text_cleaning=bool(
                payload.get("enable_text_cleaning", cls.enable_text_cleaning)
            ),
            remove_emoji=bool(payload.get("remove_emoji", cls.remove_emoji)),
            remove_urls=bool(payload.get("remove_urls", cls.remove_urls)),
            remove_mentions=bool(payload.get("remove_mentions", cls.remove_mentions)),
            export_xlsx=bool(payload.get("export_xlsx", cls.export_xlsx)),
            cookie_file=Path(str(payload.get("cookie_file", cls.cookie_file))),
            output_dir=Path(str(payload.get("output_dir", cls.output_dir))),
            sleep_min_seconds=float(payload.get("sleep_min_seconds", cls.sleep_min_seconds)),
            sleep_max_seconds=float(payload.get("sleep_max_seconds", cls.sleep_max_seconds)),
            request_timeout=float(payload.get("request_timeout", cls.request_timeout)),
            max_retry=int(payload.get("max_retry", cls.max_retry)),
            user_agent=str(payload.get("user_agent", cls.user_agent)),
        )


def load_config(path: Path | str | None = None) -> CrawlerConfig:
    """Load configuration from JSON when provided, otherwise return defaults."""

    if path is None:
        return CrawlerConfig()
    return CrawlerConfig.from_file(path)
