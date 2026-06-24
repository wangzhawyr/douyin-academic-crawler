"""Fixture-backed mock clients for local acceptance runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional

from .api import CommentAPIClient, CommentPage
from .models import RawComment
from .parser import CommentParser


class MockCommentAPIClient(CommentAPIClient):
    """Comment API client backed by a local fixture tree."""

    def __init__(self, fixture_path: Path | str | None = None) -> None:
        """Load mock comments from a JSON fixture file."""

        self.fixture_path = Path(fixture_path) if fixture_path else self._default_fixture_path()
        self.parser = CommentParser()
        self._top_level: list[RawComment] = []
        self._replies: dict[str, list[RawComment]] = {}
        self._load_fixture()

    def fetch_top_level_comments(
        self, video_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return fixture top-level comments without network access."""

        return CommentPage(comments=self._top_level, cursor=None, has_more=False, page_number=1)

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return fixture replies for a comment without network access."""

        return CommentPage(
            comments=self._replies.get(comment_id, []),
            cursor=None,
            has_more=False,
            page_number=1,
        )

    def fetch_comment_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return fixture replies using the adapter naming convention."""

        return self.fetch_replies(video_id, comment_id, cursor)

    def _load_fixture(self) -> None:
        """Load and flatten the fixture comment tree."""

        with self.fixture_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        comments = payload.get("comments", [])
        if not isinstance(comments, list):
            raise ValueError("mock fixture must contain a comments list")
        self._top_level = [self._parse_tree_node(item) for item in comments if isinstance(item, Mapping)]

    def _parse_tree_node(self, payload: Mapping[str, object]) -> RawComment:
        """Parse one fixture node and recursively index its replies."""

        comment = self.parser.parse_comment(payload)
        raw_replies = payload.get("replies", [])
        replies: list[RawComment] = []
        if isinstance(raw_replies, list):
            for reply_payload in raw_replies:
                if isinstance(reply_payload, Mapping):
                    replies.append(self._parse_tree_node(reply_payload))
        self._replies[comment.comment_id] = replies
        return comment

    @staticmethod
    def _default_fixture_path() -> Path:
        """Return the repository default fixture path."""

        return Path(__file__).resolve().parent.parent / "examples" / "mock_comment_tree.json"
