from __future__ import annotations

import csv
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Tuple

from douyin_academic_crawler.api import (
    CommentPage,
    DouyinAPIClient,
    DouyinRequestError,
)
from douyin_academic_crawler.collector import CommentTreeCollector
from douyin_academic_crawler.config import CrawlerConfig
from douyin_academic_crawler.cookie import CookieFileNotFoundError, CookieManager
from douyin_academic_crawler.models import RawComment
from douyin_academic_crawler.parser import CommentParser
from douyin_academic_crawler.rate_limit import SleepInterval
from douyin_academic_crawler.storage import CSVCommentStore, CSVFailureLogger


@dataclass(frozen=True)
class MockResponse:
    """Minimal mock HTTP response for API adapter tests."""

    status_code: int
    payload: Mapping[str, Any]
    text: str = ""

    def json(self) -> Mapping[str, Any]:
        """Return the configured JSON payload."""

        return self.payload


class CountingRateLimiter:
    """Rate limiter double that records wait calls without sleeping."""

    def __init__(self) -> None:
        """Create an empty counter."""

        self.calls = 0

    def wait(self) -> None:
        """Record one wait call."""

        self.calls += 1


class MockCommentAPI:
    """Standard comment API mock used by collector regression tests."""

    def __init__(self) -> None:
        """Create a four-level comment tree."""

        self.reply_pages = {
            ("c1", None): CommentPage([self._comment("c1-1")]),
            ("c1-1", None): CommentPage([self._comment("c1-1-1")]),
            ("c1-1-1", None): CommentPage([self._comment("c1-1-1-1")]),
        }

    def fetch_top_level_comments(self, video_id: str, cursor: Optional[str] = None) -> CommentPage:
        """Return one top-level mock comment."""

        return CommentPage([self._comment("c1")])

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return mock replies for the requested comment."""

        return self.reply_pages.get((comment_id, cursor), CommentPage([]))

    @staticmethod
    def _comment(comment_id: str) -> RawComment:
        """Create a mock normalized comment."""

        return RawComment(
            comment_id=comment_id,
            user_name=f"user-{comment_id}",
            user_id=f"id-{comment_id}",
            user_uid=f"uid-{comment_id}",
            text=f"text {comment_id}",
        )


class APIAdapterTest(unittest.TestCase):
    """Tests for config, cookie loading, API adapter, parser, and collector wiring."""

    def test_request_uses_cookie_headers_timeout_retry_and_rate_limit(self) -> None:
        """A transient HTTP failure is retried with configured headers and timeout."""

        with tempfile.TemporaryDirectory() as tmp:
            cookie_file = Path(tmp) / "cookie.txt"
            cookie_file.write_text("sessionid=legal-fixture-cookie", encoding="utf-8")
            rate_limiter = CountingRateLimiter()
            calls: list[dict[str, Any]] = []
            responses = [
                MockResponse(500, {"error": "temporary"}, "temporary failure"),
                MockResponse(200, {"ok": True}, "ok"),
            ]

            def transport(**kwargs: Any) -> MockResponse:
                calls.append(kwargs)
                return responses.pop(0)

            client = DouyinAPIClient(
                CrawlerConfig(
                    cookie_file=cookie_file,
                    sleep_min_seconds=0,
                    sleep_max_seconds=0,
                    request_timeout=3.5,
                    max_retry=1,
                    user_agent="UnitTestAgent",
                ),
                rate_limiter=rate_limiter,  # type: ignore[arg-type]
                transport=transport,
            )

            payload = client.request(
                "GET",
                "https://example.invalid/mock",
                params={"cursor": "abc"},
                headers={"X-Test": "yes"},
            )

            self.assertEqual(payload, {"ok": True})
            self.assertEqual(rate_limiter.calls, 2)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0]["timeout"], 3.5)
            self.assertIn("cursor=abc", calls[0]["url"])
            self.assertEqual(calls[0]["headers"]["Cookie"], "sessionid=legal-fixture-cookie")
            self.assertEqual(calls[0]["headers"]["User-Agent"], "UnitTestAgent")
            self.assertEqual(calls[0]["headers"]["X-Test"], "yes")

    def test_request_raises_clear_error_after_retries(self) -> None:
        """Repeated failures are surfaced as a clear API adapter exception."""

        with tempfile.TemporaryDirectory() as tmp:
            cookie_file = Path(tmp) / "cookie.txt"
            cookie_file.write_text("sessionid=legal-fixture-cookie", encoding="utf-8")
            rate_limiter = CountingRateLimiter()

            def transport(**_: Any) -> MockResponse:
                return MockResponse(503, {"error": "unavailable"}, "unavailable")

            client = DouyinAPIClient(
                CrawlerConfig(cookie_file=cookie_file, max_retry=1),
                rate_limiter=rate_limiter,  # type: ignore[arg-type]
                transport=transport,
            )

            with self.assertRaisesRegex(DouyinRequestError, "Request failed after 2 attempt"):
                client.request("GET", "https://example.invalid/mock")
            self.assertEqual(rate_limiter.calls, 2)

    def test_missing_cookie_file_has_clear_message(self) -> None:
        """CookieManager does not auto-login and reports missing cookie.txt clearly."""

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "cookie.txt"
            with self.assertRaisesRegex(CookieFileNotFoundError, "Automatic login"):
                CookieManager(missing).load_cookie_header()

    def test_parser_parses_mock_json_and_tolerates_missing_fields(self) -> None:
        """CommentParser returns normalized objects for complete and sparse JSON."""

        parser = CommentParser()
        page = parser.parse_comment_page(
            {
                "comments": [
                    {
                        "cid": "c1",
                        "user": {
                            "nickname": "alice",
                            "uid": "uid-1",
                            "sec_uid": "sec-1",
                        },
                        "create_time": "2026-06-24T12:00:00+08:00",
                        "ip_label": "北京",
                        "digg_count": "12",
                        "text": "hello",
                    },
                    {"cid": "c2"},
                ],
                "next_cursor": "next",
                "has_more": True,
            }
        )

        self.assertEqual(page.cursor, "next")
        self.assertTrue(page.has_more)
        self.assertEqual(page.comments[0].comment_id, "c1")
        self.assertEqual(page.comments[0].user_name, "alice")
        self.assertEqual(page.comments[0].like_count, 12)
        self.assertEqual(page.comments[1].comment_id, "c2")
        self.assertEqual(page.comments[1].user_name, "")
        self.assertEqual(page.comments[1].like_count, 0)

    def test_collector_still_collects_four_levels_with_mock_client(self) -> None:
        """Collector remains decoupled from raw JSON and works with standard pages."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            collector = CommentTreeCollector(
                MockCommentAPI(),
                CSVCommentStore(root / "comments.csv"),
                CSVFailureLogger(root / "errors.csv"),
                max_depth=4,
                sleep_interval=SleepInterval(0, 0),
            )

            collector.collect_comment_tree("video-mock", max_depth=4)

            with (root / "comments.csv").open("r", newline="", encoding="utf-8-sig") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual([row["depth"] for row in rows], ["1", "2", "3", "4"])
            self.assertEqual(rows[-1]["comment_path"], "1.1.1.1")


if __name__ == "__main__":
    unittest.main()
