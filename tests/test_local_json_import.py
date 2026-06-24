from __future__ import annotations

import csv
import json
import logging
import tempfile
import unittest
from pathlib import Path

from douyin_academic_crawler.audit import AuditLogger
from douyin_academic_crawler.config import CrawlerConfig
from douyin_academic_crawler.local_json_client import (
    LocalJSONCommentClient,
    LocalJSONFileNotFoundError,
)
from douyin_academic_crawler.runtime import run_mock_acceptance_task
from douyin_academic_crawler.service import CommentCollectionService
from douyin_academic_crawler.task import CrawlTask, CrawlTaskType
from douyin_academic_crawler.task_runner import CrawlTaskRunner


class LocalJSONImportTest(unittest.TestCase):
    """Tests for offline local JSON comment import mode."""

    fixture_path = Path("examples/local_comment_tree_sample.json")

    def test_local_json_client_reads_four_level_tree_without_network(self) -> None:
        """LocalJSONCommentClient reads local file and exposes standard pages."""

        client = LocalJSONCommentClient(self.fixture_path)

        top_page = client.fetch_top_level_comments("video-local-json-001")
        level2 = client.fetch_replies("video-local-json-001", "local-c1")
        level3 = client.fetch_comment_replies("video-local-json-001", "local-c1-1")
        level4 = client.fetch_replies("video-local-json-001", "local-c1-1-1")

        self.assertEqual(top_page.comments[0].comment_id, "local-c1")
        self.assertEqual(level2.comments[0].comment_id, "local-c1-1")
        self.assertEqual(level3.comments[0].comment_id, "local-c1-1-1")
        self.assertEqual(level4.comments[0].comment_id, "local-c1-1-1-1")
        self.assertFalse(top_page.has_more)
        self.assertIsNone(top_page.cursor)

    def test_local_json_runtime_exports_csv_and_audit(self) -> None:
        """local_json mode writes CSV and audit JSONL through the normal pipeline."""

        with tempfile.TemporaryDirectory() as tmp:
            try:
                output_dir = Path(tmp) / "exports"
                config = CrawlerConfig(
                    output_dir=output_dir,
                    input_mode="local_json",
                    input_json_file=str(self.fixture_path),
                    mock_mode=True,
                    allow_real_requests=False,
                )

                result = run_mock_acceptance_task(config, video_id="video-local-json-001", max_depth=4)

                csv_files = list((output_dir / "comments").glob("comments_video-local-json-001_depth4_task-*.csv"))
                self.assertEqual(result.status.value, "success")
                self.assertEqual(result.total_saved_count, 4)
                self.assertEqual(len(csv_files), 1)
                with csv_files[0].open("r", newline="", encoding="utf-8-sig") as file:
                    rows = list(csv.DictReader(file))
                self.assertEqual([row["depth"] for row in rows], ["1", "2", "3", "4"])
                self.assertEqual(
                    [row["comment_id"] for row in rows],
                    ["local-c1", "local-c1-1", "local-c1-1-1", "local-c1-1-1-1"],
                )

                audit_path = output_dir / "audit" / "audit.jsonl"
                with audit_path.open("r", encoding="utf-8") as file:
                    audit = json.loads(file.readline())
                self.assertEqual(audit["input_mode"], "local_json")
                self.assertEqual(audit["input_json_file"], str(self.fixture_path))
                self.assertIn("本地 JSON 文件", audit["data_source_note"])
            finally:
                self._reset_logging()

    def test_local_json_depth_two_exports_two_rows(self) -> None:
        """max_depth=2 limits local JSON traversal to two levels."""

        with tempfile.TemporaryDirectory() as tmp:
            try:
                output_dir = Path(tmp) / "exports"
                config = CrawlerConfig(
                    output_dir=output_dir,
                    input_mode="local_json",
                    input_json_file=str(self.fixture_path),
                )

                result = run_mock_acceptance_task(config, video_id="video-local-json-001", max_depth=2)

                csv_file = next((output_dir / "comments").glob("comments_video-local-json-001_depth2_task-*.csv"))
                with csv_file.open("r", newline="", encoding="utf-8-sig") as file:
                    rows = list(csv.DictReader(file))
                self.assertEqual(result.total_saved_count, 2)
                self.assertEqual([row["depth"] for row in rows], ["1", "2"])
            finally:
                self._reset_logging()

    def test_local_json_max_pages_still_uses_hard_limit(self) -> None:
        """local_json tasks are still subject to max_pages hard limits."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = CrawlerConfig(
                input_mode="local_json",
                input_json_file=str(self.fixture_path),
                max_pages_hard_limit=5,
            )
            runner = CrawlTaskRunner(
                CommentCollectionService(
                    lambda output_path, error_path, max_depth: LocalJSONCommentClient(self.fixture_path),
                    output_dir=output_dir,
                ),
                AuditLogger(output_dir / "audit.jsonl", config=config),
                config=config,
            )
            task = CrawlTask(
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-local-json-001",
                max_depth=4,
                max_pages=6,
                output_dir=output_dir,
            )

            result = runner.run(task)

            self.assertEqual(result.status.value, "failed")
            self.assertIn("max_pages", result.error_message)

    def test_missing_local_json_file_has_clear_error(self) -> None:
        """Missing local JSON input files raise a clear error."""

        with self.assertRaisesRegex(LocalJSONFileNotFoundError, "Local JSON input file not found"):
            LocalJSONCommentClient("examples/does-not-exist.json")

    @staticmethod
    def _reset_logging() -> None:
        """Release and remove runtime log handlers created during tests."""

        logging.shutdown()
        logging.getLogger().handlers.clear()


if __name__ == "__main__":
    unittest.main()
