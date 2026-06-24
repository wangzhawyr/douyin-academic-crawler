from __future__ import annotations

import csv
import json
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from typing import Optional

from douyin_academic_crawler.api import CommentPage
from douyin_academic_crawler.audit import AuditLogger
from douyin_academic_crawler.collector import CommentTreeCollector
from douyin_academic_crawler.config import CrawlerConfig
from douyin_academic_crawler.gui import CommentCollectionFrame
from douyin_academic_crawler.models import RawComment
from douyin_academic_crawler.service import CommentCollectionService
from douyin_academic_crawler.storage import CSVCommentStore, CSVFailureLogger
from douyin_academic_crawler.task import CrawlTask, CrawlTaskType
from douyin_academic_crawler.task_runner import CrawlTaskRunner


class NoopCollector:
    """Collector double for safety tests."""

    def collect_comment_tree(
        self,
        video_id: str,
        video_url: str = "",
        *,
        max_depth: int | None = None,
        max_pages: int | None = None,
    ) -> int:
        """Return one saved row count without touching network."""

        return 1


class CursorlessHasMoreAPI:
    """Mock API that incorrectly reports has_more without a cursor."""

    def __init__(self) -> None:
        """Initialize request counters."""

        self.top_calls = 0
        self.reply_calls = 0

    def fetch_top_level_comments(self, video_id: str, cursor: Optional[str] = None) -> CommentPage:
        """Return one top-level page that must not be fetched forever."""

        self.top_calls += 1
        return CommentPage(
            comments=[
                RawComment(comment_id="c1", user_name="user", text="root"),
                RawComment(comment_id="c2", user_name="user2", text="root2"),
            ],
            cursor=None,
            has_more=True,
        )

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return one reply page that must not be fetched forever."""

        self.reply_calls += 1
        return CommentPage(
            comments=[RawComment(comment_id=f"{comment_id}-r", user_name="reply", text="reply")],
            cursor=None,
            has_more=True,
        )


class MultiPageAndBranchAPI:
    """Mock API with second pages and sibling branches for max_pages semantics."""

    def __init__(self) -> None:
        """Initialize request counters."""

        self.reply_calls: dict[str, int] = {}

    def fetch_top_level_comments(self, video_id: str, cursor: Optional[str] = None) -> CommentPage:
        """Return one top-level page plus an uncollected second page."""

        if cursor == "top-page-2":
            return CommentPage(
                comments=[RawComment(comment_id="c2", user_name="second-page", text="skip")],
                has_more=False,
            )
        return CommentPage(
            comments=[
                RawComment(comment_id="c1", user_name="root", text="root"),
                RawComment(comment_id="sibling", user_name="sibling", text="sibling"),
            ],
            cursor="top-page-2",
            has_more=True,
        )

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return first-page replies for each node and optional second pages."""

        self.reply_calls[comment_id] = self.reply_calls.get(comment_id, 0) + 1
        if cursor:
            return CommentPage(
                comments=[RawComment(comment_id=f"{comment_id}-page2", user_name="page2", text="skip")],
                has_more=False,
            )
        replies = {
            "c1": [RawComment(comment_id="c1-1", user_name="level2", text="level2")],
            "c1-1": [RawComment(comment_id="c1-1-1", user_name="level3", text="level3")],
            "c1-1-1": [RawComment(comment_id="c1-1-1-1", user_name="level4", text="level4")],
            "sibling": [RawComment(comment_id="sibling-1", user_name="sibling reply", text="sibling reply")],
        }
        return CommentPage(comments=replies.get(comment_id, []), cursor="reply-page-2", has_more=True)


class SafetyGuardsTest(unittest.TestCase):
    """Safety switch and pagination guard tests."""

    def test_default_config_disables_real_requests(self) -> None:
        """Real requests are disabled by default."""

        config = CrawlerConfig()
        self.assertTrue(config.mock_mode)
        self.assertFalse(config.allow_real_requests)
        self.assertEqual(config.max_pages_default, 1)
        self.assertEqual(config.max_pages_hard_limit, 5)
        self.assertEqual(config.max_depth_hard_limit, 4)

    def test_non_mock_service_is_rejected_when_real_requests_disabled(self) -> None:
        """A non-mock service cannot run while allow_real_requests is false."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = CrawlerConfig(allow_real_requests=False)
            service = CommentCollectionService(
                lambda output_path, error_path, max_depth: NoopCollector(),
                output_dir=output_dir,
                mock_mode=False,
            )
            runner = CrawlTaskRunner(
                service,
                AuditLogger(output_dir / "audit.jsonl", config=config),
                config=config,
            )
            task = CrawlTask(
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-fixture-001",
                max_depth=4,
                output_dir=output_dir,
            )

            result = runner.run(task)

            self.assertEqual(result.status.value, "failed")
            self.assertIn("真实请求已被禁用", task.error_message)

    def test_max_pages_over_hard_limit_is_rejected(self) -> None:
        """max_pages cannot exceed the configured hard limit."""

        result = self._run_task(max_depth=4, max_pages=6)

        self.assertEqual(result.status.value, "failed")
        self.assertIn("max_pages", result.error_message)

    def test_max_depth_over_hard_limit_is_rejected(self) -> None:
        """max_depth cannot exceed the configured hard limit."""

        result = self._run_task(max_depth=5, max_pages=1)

        self.assertEqual(result.status.value, "failed")
        self.assertIn("max_depth", result.error_message)

    def test_gui_default_max_pages_is_one(self) -> None:
        """GUI max_pages input defaults to config.max_pages_default."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = CrawlerConfig()
            service = CommentCollectionService(
                lambda output_path, error_path, max_depth: NoopCollector(),
                output_dir=output_dir,
            )
            runner = CrawlTaskRunner(
                service,
                AuditLogger(output_dir / "audit.jsonl", config=config),
                config=config,
            )
            root = tk.Tk()
            root.withdraw()
            try:
                frame = CommentCollectionFrame(root, runner, config=config)
                self.assertEqual(frame.max_pages_var.get(), "1")
                self.assertEqual(frame.get_max_pages(), 1)
                self.assertIn("当前模式：Mock 验收模式", frame.mode_label.cget("text"))
                self.assertIn("真实请求：已禁用", frame.mode_label.cget("text"))
            finally:
                root.destroy()

    def test_audit_includes_safety_fields(self) -> None:
        """Audit JSONL records safety config fields."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = CrawlerConfig(output_dir=output_dir)
            runner = CrawlTaskRunner(
                CommentCollectionService(
                    lambda output_path, error_path, max_depth: NoopCollector(),
                    output_dir=output_dir,
                ),
                AuditLogger(output_dir / "audit.jsonl", config=config),
                config=config,
            )
            task = CrawlTask(
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-fixture-001",
                max_depth=4,
                output_dir=output_dir,
            )

            runner.run(task)

            with (output_dir / "audit.jsonl").open("r", encoding="utf-8") as file:
                record = json.loads(file.readline())
            self.assertTrue(record["mock_mode"])
            self.assertFalse(record["allow_real_requests"])
            self.assertEqual(record["max_pages_hard_limit"], 5)
            self.assertEqual(record["max_depth_hard_limit"], 4)
            self.assertIn("config_snapshot", record)

    def test_has_more_without_cursor_does_not_loop_forever(self) -> None:
        """Cursorless pagination stops locally and does not block queued nodes."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            api = CursorlessHasMoreAPI()
            collector = CommentTreeCollector(
                api,
                CSVCommentStore(output_dir / "comments.csv"),
                CSVFailureLogger(output_dir / "errors.csv"),
                max_depth=2,
            )

            written = collector.collect_comment_tree("video-fixture-001", max_depth=2, max_pages=5)

            self.assertEqual(written, 4)
            self.assertEqual(api.top_calls, 1)
            self.assertEqual(api.reply_calls, 2)
            with (output_dir / "comments.csv").open("r", newline="", encoding="utf-8-sig") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual([row["depth"] for row in rows], ["1", "1", "2", "2"])

    def test_max_pages_one_collects_four_depths_from_first_page_per_entry(self) -> None:
        """max_pages=1 limits each pagination stream, not the whole tree."""

        rows = self._collect_rows_with_api(MultiPageAndBranchAPI(), max_depth=4, max_pages=1)

        ids = {row["comment_id"] for row in rows}
        self.assertTrue({"c1", "c1-1", "c1-1-1", "c1-1-1-1"}.issubset(ids))
        self.assertEqual({row["depth"] for row in rows if row["comment_id"].startswith("c1")}, {"1", "2", "3", "4"})

    def test_max_depth_two_with_max_pages_one_collects_two_depths(self) -> None:
        """max_depth=2 still limits traversal depth independently of max_pages."""

        rows = self._collect_rows_with_api(MultiPageAndBranchAPI(), max_depth=2, max_pages=1)

        self.assertIn("1", {row["depth"] for row in rows})
        self.assertIn("2", {row["depth"] for row in rows})
        self.assertNotIn("3", {row["depth"] for row in rows})
        self.assertNotIn("4", {row["depth"] for row in rows})

    def test_max_pages_one_skips_second_page_for_same_entry(self) -> None:
        """Second pages are skipped for the same pagination entry when max_pages=1."""

        rows = self._collect_rows_with_api(MultiPageAndBranchAPI(), max_depth=4, max_pages=1)
        ids = {row["comment_id"] for row in rows}

        self.assertNotIn("c2", ids)
        self.assertFalse(any(comment_id.endswith("-page2") for comment_id in ids))

    def _run_task(self, *, max_depth: int, max_pages: int):
        """Run a task using the default safety config."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = CrawlerConfig()
            runner = CrawlTaskRunner(
                CommentCollectionService(
                    lambda output_path, error_path, max_depth: NoopCollector(),
                    output_dir=output_dir,
                ),
                AuditLogger(output_dir / "audit.jsonl", config=config),
                config=config,
            )
            task = CrawlTask(
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-fixture-001",
                max_depth=max_depth,
                max_pages=max_pages,
                output_dir=output_dir,
            )
            return runner.run(task)

    @staticmethod
    def _collect_rows_with_api(
        api: object,
        *,
        max_depth: int,
        max_pages: int,
    ) -> list[dict[str, str]]:
        """Collect rows with a mock API and return CSV records."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            collector = CommentTreeCollector(
                api,
                CSVCommentStore(output_dir / "comments.csv"),
                CSVFailureLogger(output_dir / "errors.csv"),
                max_depth=max_depth,
            )
            collector.collect_comment_tree("video-fixture-001", max_depth=max_depth, max_pages=max_pages)
            with (output_dir / "comments.csv").open("r", newline="", encoding="utf-8-sig") as file:
                return list(csv.DictReader(file))


if __name__ == "__main__":
    unittest.main()
