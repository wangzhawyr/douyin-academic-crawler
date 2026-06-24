"""Local JSON input client for offline field compatibility testing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional

from .api import CommentAPIClient, CommentPage
from .models import RawComment
from .parser import CommentParser


class LocalJSONFileNotFoundError(FileNotFoundError):
    """Raised when the configured local JSON input file is missing."""


class LocalJSONCommentClient(CommentAPIClient):
    """Comment client backed by a user-supplied local JSON file."""

    def __init__(self, input_json_file: Path | str) -> None:
        """Load comments from a local JSON file without any network access."""

        self.input_json_file = Path(input_json_file)
        if not self.input_json_file.exists():
            raise LocalJSONFileNotFoundError(
                f"Local JSON input file not found: {self.input_json_file}. "
                "Provide --local-json or set input_json_file in config."
            )
        self.parser = CommentParser()
        self._top_level: list[RawComment] = []
        self._replies: dict[str, list[RawComment]] = {}
        self._load_file()

    def fetch_top_level_comments(
        self, video_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return top-level comments from the local file."""

        return CommentPage(comments=self._top_level, cursor=None, has_more=False, page_number=1)

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return local replies for a comment."""

        return CommentPage(
            comments=self._replies.get(comment_id, []),
            cursor=None,
            has_more=False,
            page_number=1,
        )

    def fetch_comment_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return local replies using the adapter naming convention."""

        return self.fetch_replies(video_id, comment_id, cursor)

    def _load_file(self) -> None:
        """Load and flatten the local JSON comment tree."""

        with self.input_json_file.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        comments = payload.get("comments", [])
        if not isinstance(comments, list):
            raise ValueError("local JSON input must contain a comments list")
        self._top_level = [self._parse_tree_node(item) for item in comments if isinstance(item, Mapping)]

    def _parse_tree_node(self, payload: Mapping[str, object]) -> RawComment:
        """Parse one local tree node and recursively index replies."""

        comment = self.parser.parse_comment(payload)
        raw_replies = payload.get("replies", [])
        replies: list[RawComment] = []
        if isinstance(raw_replies, list):
            for reply_payload in raw_replies:
                if isinstance(reply_payload, Mapping):
                    replies.append(self._parse_tree_node(reply_payload))
        self._replies[comment.comment_id] = replies
        return comment
