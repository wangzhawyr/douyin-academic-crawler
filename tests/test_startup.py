from __future__ import annotations

import importlib
import json
import logging
import tempfile
import unittest
from pathlib import Path

from douyin_academic_crawler.config import CrawlerConfig
from douyin_academic_crawler.runtime import (
    ensure_output_directories,
    run_mock_acceptance_task,
)


class StartupTest(unittest.TestCase):
    """Startup and local mock acceptance tests."""

    def test_main_entry_points_are_importable(self) -> None:
        """main.py and package __main__ can be imported."""

        self.assertIsNotNone(importlib.import_module("main"))
        self.assertIsNotNone(importlib.import_module("douyin_academic_crawler.__main__"))

    def test_mock_mode_defaults_to_enabled(self) -> None:
        """Default configuration starts in mock acceptance mode."""

        self.assertTrue(CrawlerConfig().mock_mode)

    def test_output_directories_are_created(self) -> None:
        """Startup creates comments, audit, and logs directories."""

        with tempfile.TemporaryDirectory() as tmp:
            directories = ensure_output_directories(Path(tmp) / "exports")

            self.assertTrue(directories.comments.is_dir())
            self.assertTrue(directories.audit.is_dir())
            self.assertTrue(directories.logs.is_dir())

    def test_mock_task_generates_csv_audit_and_runtime_log(self) -> None:
        """A mock acceptance task writes local CSV, audit JSONL, and runtime log."""

        with tempfile.TemporaryDirectory() as tmp:
            try:
                output_dir = Path(tmp) / "exports"
                result = run_mock_acceptance_task(
                    CrawlerConfig(output_dir=output_dir, mock_mode=True),
                    video_id="video-fixture-001",
                    max_depth=4,
                )

                csv_files = list((output_dir / "comments").glob("comments_video-fixture-001_depth4_task-*.csv"))
                audit_path = output_dir / "audit" / "audit.jsonl"
                runtime_log = output_dir / "logs" / "runtime.log"

                self.assertEqual(result.status.value, "success")
                self.assertEqual(result.total_saved_count, 4)
                self.assertEqual(len(csv_files), 1)
                self.assertTrue(audit_path.exists())
                self.assertTrue(runtime_log.exists())

                with audit_path.open("r", encoding="utf-8") as file:
                    audit_record = json.loads(file.readline())
                self.assertEqual(audit_record["status"], "success")
                self.assertEqual(audit_record["total_saved_count"], 4)
                self.assertIn("compliance_note", audit_record)
            finally:
                logging.shutdown()
                logging.getLogger().handlers.clear()


if __name__ == "__main__":
    unittest.main()
