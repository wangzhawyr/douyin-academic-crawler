from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Optional

from douyin_academic_crawler.audit import AuditLogger, DEFAULT_COMPLIANCE_NOTE
from douyin_academic_crawler.service import CommentCollectionService
from douyin_academic_crawler.task import CrawlTask, CrawlTaskStatus, CrawlTaskType
from douyin_academic_crawler.task_runner import CrawlTaskRunner


class SuccessCollector:
    """Collector double that records calls and returns a saved count."""

    def __init__(self, saved_count: int = 4) -> None:
        """Create a successful collector double."""

        self.saved_count = saved_count
        self.video_id: Optional[str] = None
        self.max_depth: Optional[int] = None

    def collect_comment_tree(
        self,
        video_id: str,
        video_url: str = "",
        *,
        max_depth: int | None = None,
    ) -> int:
        """Record the call and return the configured count."""

        self.video_id = video_id
        self.max_depth = max_depth
        return self.saved_count


class FailingCollector:
    """Collector double that raises during collection."""

    def collect_comment_tree(
        self,
        video_id: str,
        video_url: str = "",
        *,
        max_depth: int | None = None,
    ) -> int:
        """Raise a deterministic failure."""

        raise RuntimeError("collector exploded")


class TaskRunnerTest(unittest.TestCase):
    """Tests for controlled task execution and audit logging."""

    def test_comment_tree_task_depth_four_succeeds_and_writes_audit(self) -> None:
        """A valid comment_tree task reaches success and writes JSONL audit."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            collector = SuccessCollector(saved_count=4)
            service = self._service(output_dir, collector)
            runner = CrawlTaskRunner(
                service,
                AuditLogger(output_dir / "audit.jsonl"),
                clock=lambda: datetime(2026, 6, 24, 10, 0, 0),
            )
            task = CrawlTask(
                task_id="task-success",
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-fixture-001",
                video_url="https://example.invalid/video-fixture-001",
                max_depth=4,
                output_dir=output_dir,
                researcher_note="fixture research run",
            )

            result = runner.run(task)

            self.assertEqual(result.status, CrawlTaskStatus.SUCCESS)
            self.assertEqual(result.total_saved_count, 4)
            self.assertEqual(collector.video_id, "video-fixture-001")
            self.assertEqual(collector.max_depth, 4)
            self.assertEqual(
                Path(task.output_file).name,
                "comments_video-fixture-001_depth4_task-success_20260624.csv",
            )
            audit_record = self._read_audit(output_dir / "audit.jsonl")
            self.assertEqual(audit_record["task_id"], "task-success")
            self.assertEqual(audit_record["status"], "success")
            self.assertEqual(audit_record["total_saved_count"], 4)
            self.assertEqual(audit_record["compliance_note"], DEFAULT_COMPLIANCE_NOTE)

    def test_max_depth_five_is_rejected(self) -> None:
        """max_depth outside 1-4 fails before collector execution."""

        result, task = self._run_invalid_task(max_depth=5, max_pages=None)

        self.assertEqual(result.status, CrawlTaskStatus.FAILED)
        self.assertEqual(task.status, CrawlTaskStatus.FAILED)
        self.assertIn("max_depth", task.error_message)

    def test_negative_max_pages_is_rejected(self) -> None:
        """max_pages must be positive or None."""

        result, task = self._run_invalid_task(max_depth=4, max_pages=-1)

        self.assertEqual(result.status, CrawlTaskStatus.FAILED)
        self.assertIn("max_pages", task.error_message)

    def test_collector_exception_marks_task_failed(self) -> None:
        """Collector failures are captured in task.error_message."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            runner = CrawlTaskRunner(
                self._service(output_dir, FailingCollector()),
                AuditLogger(output_dir / "audit.jsonl"),
            )
            task = CrawlTask(
                task_id="task-failure",
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-fixture-001",
                max_depth=4,
                output_dir=output_dir,
            )

            result = runner.run(task)

            self.assertEqual(result.status, CrawlTaskStatus.FAILED)
            self.assertIn("collector exploded", task.error_message)
            audit_record = self._read_audit(output_dir / "audit.jsonl")
            self.assertEqual(audit_record["status"], "failed")
            self.assertIn("collector exploded", audit_record["error_message"])

    def test_gui_or_service_does_not_bypass_task_runner_contract(self) -> None:
        """The runner is the component that transitions task state and audits."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            task = CrawlTask(
                task_id="task-contract",
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-fixture-001",
                max_depth=4,
                output_dir=output_dir,
            )
            service = self._service(output_dir, SuccessCollector())
            self.assertEqual(task.status, CrawlTaskStatus.PENDING)

            runner = CrawlTaskRunner(service, AuditLogger(output_dir / "audit.jsonl"))
            runner.run(task)

            self.assertEqual(task.status, CrawlTaskStatus.SUCCESS)
            self.assertTrue((output_dir / "audit.jsonl").exists())

    def _run_invalid_task(self, *, max_depth: int, max_pages: int | None) -> tuple[object, CrawlTask]:
        """Run an invalid task and return its result and mutated task."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            runner = CrawlTaskRunner(
                self._service(output_dir, SuccessCollector()),
                AuditLogger(output_dir / "audit.jsonl"),
            )
            task = CrawlTask(
                task_id="task-invalid",
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-fixture-001",
                max_depth=max_depth,
                max_pages=max_pages,
                output_dir=output_dir,
            )
            return runner.run(task), task

    @staticmethod
    def _service(output_dir: Path, collector: object) -> CommentCollectionService:
        """Create a service wired to a fixed collector double."""

        return CommentCollectionService(
            lambda output_path, error_path, max_depth: collector,
            output_dir=output_dir,
            clock=lambda: datetime(2026, 6, 24, 10, 0, 0),
        )

    @staticmethod
    def _read_audit(path: Path) -> dict[str, object]:
        """Read the first audit JSONL record."""

        with path.open("r", encoding="utf-8") as file:
            return json.loads(file.readline())


if __name__ == "__main__":
    unittest.main()
