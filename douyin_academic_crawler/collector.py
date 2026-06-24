"""BFS comment-tree collection with privacy-safe storage."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import logging
from typing import Deque, List, Optional, Set

from .api import CommentAPIClient, CommentPage
from .models import CommentRecord, RawComment, TraversalNode
from .privacy import hash_identifier
from .rate_limit import RateLimiter, SleepInterval
from .storage import CSVCommentStore, CSVFailureLogger


class CommentTreeCollector:
    """Collect first through fourth level comment trees with BFS traversal."""

    def __init__(
        self,
        api_client: CommentAPIClient,
        store: CSVCommentStore,
        failure_logger: CSVFailureLogger,
        *,
        max_depth: int = 4,
        sleep_interval: SleepInterval | None = None,
        hash_salt: str = "",
    ) -> None:
        """Configure dependencies, max depth, request pacing, and hash salt."""

        if max_depth < 1 or max_depth > 4:
            raise ValueError("max_depth must be between 1 and 4")
        self.api_client = api_client
        self.store = store
        self.failure_logger = failure_logger
        self.max_depth = max_depth
        self.rate_limiter = RateLimiter(sleep_interval)
        self.hash_salt = hash_salt

    def collect_comment_tree(
        self,
        video_id: str,
        video_url: str = "",
        *,
        max_depth: int | None = None,
        max_pages: int | None = None,
    ) -> int:
        """Collect an accessible comment tree and append pages to CSV as they arrive."""

        effective_max_depth = self.max_depth if max_depth is None else max_depth
        if effective_max_depth < 1 or effective_max_depth > 4:
            raise ValueError("max_depth must be between 1 and 4")
        if max_pages is not None and max_pages <= 0:
            raise ValueError("max_pages must be a positive integer or None")
        saved_ids = self.store.load_existing_comment_ids()
        traversed_ids: Set[str] = set()
        queue: Deque[TraversalNode] = deque()
        total_written = 0

        cursor: Optional[str] = None
        page_number = 1
        top_level_index = 0
        top_level_pages_fetched = 0

        while True:
            if max_pages is not None and top_level_pages_fetched >= max_pages:
                break
            try:
                page = self._fetch_top_level_page(video_id, cursor)
                top_level_pages_fetched += 1
            except Exception as exc:
                self._log_failure(video_url, video_id, "", 1, page_number, exc)
                break

            records: List[CommentRecord] = []
            for raw in page.comments:
                top_level_index += 1
                node = TraversalNode(
                    raw=raw,
                    depth=1,
                    root_comment_id=raw.comment_id,
                    parent_comment_id=None,
                    comment_path=str(top_level_index),
                )
                if raw.comment_id not in traversed_ids:
                    queue.append(node)
                    traversed_ids.add(raw.comment_id)
                if raw.comment_id in saved_ids:
                    continue
                records.append(self._to_record(video_id, node, None))
                saved_ids.add(raw.comment_id)

            total_written += self.store.append_records(records)
            if not page.has_more:
                break
            if not page.cursor:
                logging.warning(
                    "Stopping top-level pagination for video_id=%s because has_more=True but cursor is empty.",
                    video_id,
                )
                break
            cursor = page.cursor
            page_number += 1

        while queue:
            parent = queue.popleft()
            if parent.depth >= effective_max_depth:
                continue

            child_cursor: Optional[str] = None
            child_page_number = 1
            child_index = 0
            reply_pages_fetched = 0
            while True:
                if max_pages is not None and reply_pages_fetched >= max_pages:
                    break
                try:
                    page = self._fetch_reply_page(video_id, parent.raw.comment_id, child_cursor)
                    reply_pages_fetched += 1
                except Exception as exc:
                    self._log_failure(
                        video_url,
                        video_id,
                        parent.raw.comment_id,
                        parent.depth + 1,
                        child_page_number,
                        exc,
                    )
                    break

                records = []
                for raw in page.comments:
                    child_index += 1
                    node = TraversalNode(
                        raw=raw,
                        depth=parent.depth + 1,
                        root_comment_id=parent.root_comment_id,
                        parent_comment_id=parent.raw.comment_id,
                        comment_path=f"{parent.comment_path}.{child_index}",
                    )
                    if raw.comment_id not in traversed_ids:
                        queue.append(node)
                        traversed_ids.add(raw.comment_id)
                    if raw.comment_id in saved_ids:
                        continue
                    records.append(self._to_record(video_id, node, parent.raw))
                    saved_ids.add(raw.comment_id)

                total_written += self.store.append_records(records)
                if not page.has_more:
                    break
                if not page.cursor:
                    logging.warning(
                        "Stopping reply pagination for video_id=%s comment_id=%s because has_more=True but cursor is empty.",
                        video_id,
                        parent.raw.comment_id,
                    )
                    break
                child_cursor = page.cursor
                child_page_number += 1

        return total_written

    def _fetch_top_level_page(self, video_id: str, cursor: Optional[str]) -> CommentPage:
        """Wait and fetch one top-level comment page."""

        self.rate_limiter.wait()
        return self.api_client.fetch_top_level_comments(video_id, cursor)

    def _fetch_reply_page(
        self, video_id: str, comment_id: str, cursor: Optional[str]
    ) -> CommentPage:
        """Wait and fetch one reply page for a comment."""

        self.rate_limiter.wait()
        return self.api_client.fetch_replies(video_id, comment_id, cursor)

    def _to_record(
        self,
        video_id: str,
        node: TraversalNode,
        parent_raw: Optional[RawComment],
    ) -> CommentRecord:
        """Convert a traversal node into a privacy-preserving export row."""

        raw = node.raw
        reply_to_comment_id = raw.reply_to_comment_id or node.parent_comment_id or ""
        reply_to_user_name = raw.reply_to_user_name or (parent_raw.user_name if parent_raw else "")
        return CommentRecord(
            video_id=video_id,
            comment_id=raw.comment_id,
            root_comment_id=node.root_comment_id,
            parent_comment_id=node.parent_comment_id or "",
            reply_to_comment_id=reply_to_comment_id,
            reply_to_user_name=reply_to_user_name,
            depth=node.depth,
            comment_path=node.comment_path,
            comment_user_name=raw.user_name,
            comment_user_id_hash=hash_identifier(raw.user_id or raw.sec_uid, self.hash_salt),
            comment_user_uid_hash=hash_identifier(raw.user_uid, self.hash_salt),
            comment_time=raw.comment_time or "",
            comment_ip_location=raw.ip_location or "",
            comment_like_count=raw.like_count,
            comment_text=raw.text,
            crawl_time=self._now_iso(),
        )

    def _log_failure(
        self,
        video_url: str,
        video_id: str,
        comment_id: str,
        depth: int,
        page: int,
        exc: Exception,
    ) -> None:
        """Write a failed page request to the exception log."""

        self.failure_logger.log_failure(
            video_url=video_url,
            video_id=video_id,
            comment_id=comment_id,
            depth=depth,
            page=page,
            error=f"{type(exc).__name__}: {exc}",
            crawl_time=self._now_iso(),
        )

    @staticmethod
    def _now_iso() -> str:
        """Return the current UTC time in ISO-8601 format."""

        return datetime.now(timezone.utc).isoformat()
