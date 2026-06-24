from __future__ import annotations

import tempfile
import tkinter as tk
import unittest
from datetime import datetime
from pathlib import Path
from typing import Optional

from douyin_academic_crawler.audit import AuditLogger
from douyin_academic_crawler.gui import CommentCollectionFrame, label_for_depth
from douyin_academic_crawler.service import CommentCollectionService
from douyin_academic_crawler.task_runner import CrawlTaskRunner


class RecorderCollector:
    """Collector double that records calls without writing CSV files."""

    def __init__(self) -> None:
        """Create an empty call recorder."""

        self.video_id: Optional[str] = None
        self.max_depth: Optional[int] = None

    def collect_comment_tree(
        self,
        video_id: str,
        video_url: str = "",
        *,
        max_depth: int | None = None,
    ) -> int:
        """Record the collector invocation and pretend two comments were saved."""

        self.video_id = video_id
        self.max_depth = max_depth
        return 2


class GUISmokeTest(unittest.TestCase):
    """Smoke tests for GUI depth selection and task-runner delegation."""

    def test_default_depth_and_selected_depth_are_passed_through_task_runner(self) -> None:
        """Selecting 2 levels in the GUI sends max_depth=2 through the task runner."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            collector = RecorderCollector()
            factory_calls: list[tuple[Path, Path, int]] = []

            def collector_factory(output_path: Path, error_path: Path, max_depth: int) -> RecorderCollector:
                factory_calls.append((output_path, error_path, max_depth))
                return collector

            service = CommentCollectionService(
                collector_factory,
                output_dir=output_dir,
                clock=lambda: datetime(2026, 6, 24, 9, 30, 0),
            )
            runner = CrawlTaskRunner(
                service,
                AuditLogger(output_dir / "audit.jsonl"),
                clock=lambda: datetime(2026, 6, 24, 9, 30, 0),
            )

            root = tk.Tk()
            root.withdraw()
            try:
                frame = CommentCollectionFrame(
                    root,
                    runner,
                    default_video_id="video-fixture-001",
                )
                self.assertEqual(frame.get_max_depth(), 4)

                frame.depth_var.set(label_for_depth(2))
                frame.start_collection()

                self.assertEqual(factory_calls[0][2], 2)
                self.assertEqual(collector.video_id, "video-fixture-001")
                self.assertEqual(collector.max_depth, 2)
                self.assertRegex(
                    factory_calls[0][0].name,
                    r"comments_video-fixture-001_depth2_task-[a-f0-9]{12}_20260624\.csv",
                )
                logs = frame.log_text.get("1.0", "end")
                self.assertIn("task_id：task-", logs)
                self.assertIn("任务状态：pending -> running", logs)
                self.assertIn("任务状态：running -> success", logs)
                self.assertIn("当前最大采集层级：2", logs)
                self.assertIn("正在采集一级评论", logs)
                self.assertIn("正在采集二级评论", logs)
                self.assertEqual(list(output_dir.glob("comments_*.csv")), [])
            finally:
                root.destroy()


if __name__ == "__main__":
    unittest.main()
