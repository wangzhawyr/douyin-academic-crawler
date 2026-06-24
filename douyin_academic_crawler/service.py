"""Service layer used by task runners and compatibility entry points."""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

from .cleaner import CommentDataCleaner
from .config import CrawlerConfig
from .report import DataQualityReport
from .storage import (
    COMMENT_FIELDNAMES,
    export_rows_to_xlsx,
    read_csv_rows,
    write_csv_rows,
)
from .task import CrawlTask, CrawlTaskType


class CollectableCommentTree(Protocol):
    """Collector protocol used by the service layer."""

    def collect_comment_tree(
        self,
        video_id: str,
        video_url: str = "",
        *,
        max_depth: int | None = None,
        max_pages: int | None = None,
    ) -> int:
        """Collect comments for one video."""


CollectorFactory = Callable[[Path, Path, int], CollectableCommentTree]
LogCallback = Callable[[str], None]


@dataclass(frozen=True)
class CommentCollectionResult:
    """Result returned after a comment collection run."""

    output_path: Path
    error_log_path: Path
    written_count: int
    max_depth: int
    task_id: str
    output_xlsx: Path | None = None
    quality_report_file: Path | None = None


class CommentCollectionService:
    """Coordinate task input, export naming, post-processing, and collector invocation."""

    def __init__(
        self,
        collector_factory: CollectorFactory,
        *,
        output_dir: Path | str = "exports",
        reports_dir: Path | str | None = None,
        config: CrawlerConfig | None = None,
        clock: Callable[[], datetime] | None = None,
        log_callback: LogCallback | None = None,
        mock_mode: bool = True,
    ) -> None:
        """Create a collection service with injectable dependencies."""

        self.collector_factory = collector_factory
        self.output_dir = Path(output_dir)
        self.reports_dir = Path(reports_dir) if reports_dir else self.output_dir.parent / "reports"
        self.config = config or CrawlerConfig()
        self.clock = clock or datetime.now
        self.log_callback = log_callback
        self.mock_mode = mock_mode

    def collect_task(self, task: CrawlTask) -> CommentCollectionResult:
        """Execute a comment-tree task using the collector layer."""

        task_type = task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type)
        if task_type != CrawlTaskType.COMMENT_TREE.value:
            raise NotImplementedError("Only comment_tree tasks are implemented in this phase.")
        if not task.video_id:
            raise ValueError("video_id is required")
        if task.max_depth < 1 or task.max_depth > 4:
            raise ValueError("max_depth must be between 1 and 4")

        output_dir = Path(task.output_dir or self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        date_stamp = self.clock().strftime("%Y%m%d")
        safe_video_id = self._safe_filename_part(task.video_id)
        safe_task_id = self._safe_filename_part(task.task_id)
        output_path = Path(task.output_file) if task.output_file else (
            output_dir / f"comments_{safe_video_id}_depth{task.max_depth}_{safe_task_id}_{date_stamp}.csv"
        )
        error_log_path = output_dir / (
            f"comment_errors_{safe_video_id}_depth{task.max_depth}_{safe_task_id}_{date_stamp}.csv"
        )
        task.output_file = output_path

        self._log(f"task_id：{task.task_id}")
        self._log(f"当前最大采集层级：{task.max_depth}")
        for depth in range(1, task.max_depth + 1):
            self._log(f"正在采集{self._depth_name(depth)}评论")

        collector = self.collector_factory(output_path, error_log_path, task.max_depth)
        written_count = self._collect_with_supported_arguments(collector, task)
        postprocess = self._postprocess_outputs(task, output_path)
        self._log(f"采集完成，写入评论数：{written_count}")
        self._log(f"导出文件：{output_path}")
        if postprocess.output_xlsx:
            self._log(f"Excel 导出：{postprocess.output_xlsx}")
        if postprocess.quality_report_file:
            self._log(f"质量报告：{postprocess.quality_report_file}")

        return CommentCollectionResult(
            output_path=output_path,
            error_log_path=error_log_path,
            written_count=written_count,
            max_depth=task.max_depth,
            task_id=task.task_id,
            output_xlsx=postprocess.output_xlsx,
            quality_report_file=postprocess.quality_report_file,
        )

    def collect_comments(
        self,
        *,
        video_id: str,
        max_depth: int,
        video_url: str = "",
    ) -> CommentCollectionResult:
        """Compatibility wrapper that creates a comment_tree task."""

        task = CrawlTask(
            task_type=CrawlTaskType.COMMENT_TREE.value,
            video_id=video_id,
            video_url=video_url,
            max_depth=max_depth,
            output_dir=self.output_dir,
        )
        return self.collect_task(task)

    def _postprocess_outputs(self, task: CrawlTask, output_path: Path) -> CommentCollectionResult:
        """Clean rows, optionally export XLSX, and generate a quality report."""

        rows = read_csv_rows(output_path)
        if not rows:
            return CommentCollectionResult(output_path, output_path, 0, task.max_depth, task.task_id)

        processed_rows = rows
        if self.config.enable_text_cleaning:
            cleaner = CommentDataCleaner(
                remove_emoji=self.config.remove_emoji,
                remove_urls=self.config.remove_urls,
                remove_mentions=self.config.remove_mentions,
            )
            processed_rows = cleaner.clean_rows(rows)
        else:
            processed_rows = [self._ensure_cleaning_fields(row) for row in rows]
        write_csv_rows(output_path, processed_rows, fieldnames=COMMENT_FIELDNAMES)

        output_xlsx = None
        if self.config.export_xlsx:
            output_xlsx = output_path.with_suffix(".xlsx")
            export_rows_to_xlsx(
                output_xlsx,
                processed_rows,
                fieldnames=COMMENT_FIELDNAMES,
                metadata={
                    "task_id": task.task_id,
                    "video_id": task.video_id,
                    "cleaning_enabled": self.config.enable_text_cleaning,
                },
            )
            task.output_xlsx = output_xlsx

        quality_report_file = DataQualityReport(self.reports_dir).generate(
            task_id=task.task_id,
            video_id=task.video_id,
            rows=processed_rows,
            output_csv=output_path,
            output_xlsx=output_xlsx,
        )
        task.quality_report_file = quality_report_file
        return CommentCollectionResult(
            output_path=output_path,
            error_log_path=output_path,
            written_count=len(processed_rows),
            max_depth=task.max_depth,
            task_id=task.task_id,
            output_xlsx=output_xlsx,
            quality_report_file=quality_report_file,
        )

    def _log(self, message: str) -> None:
        """Send one log line to the configured callback."""

        if self.log_callback is not None:
            self.log_callback(message)

    @staticmethod
    def _depth_name(depth: int) -> str:
        """Return the Chinese level name used in run logs."""

        return {1: "一级", 2: "二级", 3: "三级", 4: "四级"}[depth]

    @staticmethod
    def _safe_filename_part(value: str) -> str:
        """Return a filesystem-safe identifier for export filenames."""

        safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
        return safe or "video"

    @staticmethod
    def _collect_with_supported_arguments(
        collector: CollectableCommentTree,
        task: CrawlTask,
    ) -> int:
        """Call a collector while preserving older test doubles without max_pages."""

        parameters = inspect.signature(collector.collect_comment_tree).parameters
        kwargs: dict[str, int] = {"max_depth": task.max_depth}
        if task.max_pages is not None and "max_pages" in parameters:
            kwargs["max_pages"] = task.max_pages
        return collector.collect_comment_tree(task.video_id, task.video_url, **kwargs)

    @staticmethod
    def _ensure_cleaning_fields(row: dict[str, str]) -> dict[str, object]:
        """Add empty cleaning fields when cleaning is disabled."""

        updated = dict(row)
        updated.setdefault("cleaned_comment_text", row.get("comment_text", ""))
        updated.setdefault("text_length", len(str(row.get("comment_text", ""))))
        updated.setdefault("has_emoji", False)
        updated.setdefault("has_url", False)
        updated.setdefault("has_mention", False)
        return updated
