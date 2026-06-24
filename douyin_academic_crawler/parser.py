"""Parsing helpers that normalize accessible comment payloads."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .api import CommentPage
from .models import CommentNode, RawComment


class CommentParser:
    """Convert raw JSON payloads into standard comment structures."""

    def parse_comment(self, payload: Mapping[str, Any]) -> CommentNode:
        """Normalize one platform comment payload into a CommentNode."""

        user = _as_mapping(payload.get("user"))
        return CommentNode(
            comment_id=str(payload.get("comment_id") or payload.get("cid") or payload.get("id") or ""),
            user_name=str(user.get("nickname") or payload.get("user_name") or ""),
            user_id=_optional_str(user.get("user_id") or user.get("uid") or payload.get("user_id")),
            user_uid=_optional_str(user.get("uid") or payload.get("user_uid")),
            sec_uid=_optional_str(user.get("sec_uid") or payload.get("sec_uid")),
            comment_time=_optional_str(payload.get("comment_time") or payload.get("create_time")),
            ip_location=_optional_str(payload.get("ip_location") or payload.get("ip_label")),
            like_count=_safe_int(payload.get("like_count") or payload.get("digg_count")),
            text=str(payload.get("text") or payload.get("comment_text") or ""),
            reply_to_comment_id=_optional_str(payload.get("reply_to_comment_id")),
            reply_to_user_name=_optional_str(payload.get("reply_to_user_name")),
        )

    def parse_comment_page(self, payload: Mapping[str, Any]) -> CommentPage:
        """Parse one comment page JSON object into a CommentPage."""

        raw_comments = self._extract_comment_list(payload)
        return CommentPage(
            comments=[self.parse_comment(comment) for comment in raw_comments],
            cursor=_optional_str(payload.get("cursor") or payload.get("next_cursor")),
            has_more=bool(payload.get("has_more", False)),
            page_number=_safe_int(payload.get("page") or payload.get("page_number"), default=1),
        )

    @staticmethod
    def _extract_comment_list(payload: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
        """Return the first recognized comment list from a JSON page."""

        candidates = [
            payload.get("comments"),
            payload.get("reply_comments"),
            _as_mapping(payload.get("data")).get("comments"),
            _as_mapping(payload.get("data")).get("reply_comments"),
        ]
        for candidate in candidates:
            if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                return [item for item in candidate if isinstance(item, Mapping)]
        return []


def parse_comment_payload(payload: Mapping[str, Any]) -> RawComment:
    """Backward-compatible function wrapper around CommentParser."""

    return CommentParser().parse_comment(payload)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping for nested JSON objects and an empty mapping otherwise."""

    return value if isinstance(value, Mapping) else {}


def _optional_str(value: Any) -> Optional[str]:
    """Convert non-empty values to strings while preserving blanks as None."""

    if value is None or value == "":
        return None
    return str(value)


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int without raising on malformed or missing fields."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default
