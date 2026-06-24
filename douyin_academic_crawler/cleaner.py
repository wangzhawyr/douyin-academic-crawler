"""Comment text cleaning helpers for research exports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"(?<!\w)@[\w\-\u4e00-\u9fff]+")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+",
    re.UNICODE,
)


@dataclass(frozen=True)
class CommentDataCleaner:
    """Clean comment text while preserving the original text field."""

    remove_emoji: bool = False
    remove_urls: bool = True
    remove_mentions: bool = False

    def clean_row(self, row: Mapping[str, object]) -> dict[str, object]:
        """Return a row with cleaned text and quality flags added."""

        cleaned = dict(row)
        original_text = str(row.get("comment_text") or "")
        normalized = self._normalize_whitespace(original_text)
        has_emoji = bool(EMOJI_RE.search(normalized))
        has_url = bool(URL_RE.search(normalized))
        has_mention = bool(MENTION_RE.search(normalized))

        cleaned_text = normalized
        if self.remove_urls:
            cleaned_text = URL_RE.sub("", cleaned_text)
        if self.remove_mentions:
            cleaned_text = MENTION_RE.sub("", cleaned_text)
        if self.remove_emoji:
            cleaned_text = EMOJI_RE.sub("", cleaned_text)
        cleaned_text = self._normalize_whitespace(cleaned_text)

        cleaned["cleaned_comment_text"] = cleaned_text
        cleaned["text_length"] = len(cleaned_text)
        cleaned["has_emoji"] = has_emoji
        cleaned["has_url"] = has_url
        cleaned["has_mention"] = has_mention
        return cleaned

    def clean_rows(self, rows: list[Mapping[str, object]]) -> list[dict[str, object]]:
        """Clean many rows."""

        return [self.clean_row(row) for row in rows]

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Trim text and collapse newlines/tabs into single spaces."""

        return re.sub(r"\s+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()
