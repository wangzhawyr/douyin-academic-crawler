"""Task runner for controlled and auditable crawl execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .audit import AuditLogger
from .config import CrawlerConfig
from .service import CommentCollectionResult, CommentCollectionService
from .task import CrawlTask, CrawlTaskStatus, CrawlTaskType


LogCallback = Callable[[str], None]


@dataclass(frozen=True)
class CrawlTaskResult:
    """Summary returned after a task run."""

    task_id: str
    status: CrawlTaskStatus
    output_file: Path | None
    total_saved_count: int
    error_message: str


class CrawlTaskRunner:
    """Validate, execute, status-track, and audit crawl tasks."""

    def __init__(
        self,
        service: CommentCollectionService,
        audit_logger: AuditLogger,
        *,
        config: CrawlerConfig | None = None,
        log_callback: LogCallback | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Create a task runner with injectable service, audit logger, and clock."""

        self.service = service
        self.audit_logger = audit_logger
        self.config = config or CrawlerConfig()
        self.log_callback = log_callback
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def run(self, task: CrawlTask) -> CrawlTaskResult:
        """Run one crawl task and return a summary."""

        total_saved_count = 0
        try:
            self._validate(task)
            self._set_status(task, CrawlTaskStatus.RUNNING)
            task.started_at = self._now_iso()

            if self._task_type_value(task) != CrawlTaskType.COMMENT_TREE.value:
                raise NotImplementedError("Only comment_tree tasks are implemented in this phase.")

            result: CommentCollectionResult = self.service.collect_task(task)
            total_saved_count = result.written_count
            task.output_file = result.output_path
            task.output_xlsx = result.output_xlsx
            task.quality_report_file = result.quality_report_file
            self._set_status(task, CrawlTaskStatus.SUCCESS)
            return self._result(task, total_saved_count)
        except Exception as exc:
            task.error_message = f"{type(exc).__name__}: {exc}"
            self._set_status(task, CrawlTaskStatus.FAILED)
            return self._result(task, total_saved_count)
        finally:
            if task.started_at and not task.finished_at:
                task.finished_at = self._now_iso()
            self.audit_logger.log_task(task, total_saved_count=total_saved_count)

    def cancel(self, task: CrawlTask) -> None:
        """Mark a pending task as cancelled."""

        if task.status == CrawlTaskStatus.PENDING:
            self._set_status(task, CrawlTaskStatus.CANCELLED)
            task.finished_at = self._now_iso()

    def _validate(self, task: CrawlTask) -> None:
        """Validate supported task settings and safety limits before execution."""

        if not task.video_id and not task.video_url:
            raise ValueError("video_id or video_url is required")
        if task.max_depth < 1 or task.max_depth > self.config.max_depth_hard_limit:
            raise ValueError(
                f"max_depth must be between 1 and {self.config.max_depth_hard_limit}"
            )
        if task.max_pages is None:
            task.max_pages = self.config.max_pages_default
        if task.max_pages <= 0:
            raise ValueError("max_pages must be a positive integer")
        if task.max_pages > self.config.max_pages_hard_limit:
            raise ValueError(
                f"max_pages must not exceed hard limit {self.config.max_pages_hard_limit}"
            )
        if self._task_type_value(task) not in {
            CrawlTaskType.COMMENT_TREE.value,
            CrawlTaskType.PROFILE_VIDEOS.value,
            CrawlTaskType.SEARCH_VIDEOS.value,
        }:
            raise ValueError("task_type must be comment_tree, profile_videos, or search_videos")
        if not self.config.allow_real_requests and not self.service.mock_mode:
            raise RuntimeError("当前处于 mock 验收模式，真实请求已被禁用。")

    def _set_status(self, task: CrawlTask, status: CrawlTaskStatus) -> None:
        """Update task status and emit a log line."""

        previous = task.status
        task.status = status
        if previous == status:
            self._log(f"任务状态：{status.value}")
        else:
            self._log(f"任务状态：{previous.value} -> {status.value}")

    def _result(self, task: CrawlTask, total_saved_count: int) -> CrawlTaskResult:
        """Build a result object for the current task state."""

        return CrawlTaskResult(
            task_id=task.task_id,
            status=task.status,
            output_file=Path(task.output_file) if task.output_file else None,
            total_saved_count=total_saved_count,
            error_message=task.error_message,
        )

    def _now_iso(self) -> str:
        """Return the current clock time in ISO-8601 format."""

        return self.clock().isoformat()

    def _log(self, message: str) -> None:
        """Send one log line to the configured callback."""

        if self.log_callback is not None:
            self.log_callback(message)

    @staticmethod
    def _task_type_value(task: CrawlTask) -> str:
        """Return a normalized task type value."""

        return task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type)
