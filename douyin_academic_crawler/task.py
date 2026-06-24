"""Crawl task models and statuses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4


class CrawlTaskStatus(str, Enum):
    """Lifecycle status for a crawl task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlTaskType(str, Enum):
    """Supported task types."""

    COMMENT_TREE = "comment_tree"
    PROFILE_VIDEOS = "profile_videos"
    SEARCH_VIDEOS = "search_videos"


@dataclass
class CrawlTask:
    """Configuration and lifecycle metadata for one crawl task."""

    task_type: str
    video_id: str = ""
    video_url: str = ""
    max_depth: int = 4
    max_pages: int | None = None
    output_dir: Path | str = Path("exports")
    output_file: Path | str | None = None
    output_xlsx: Path | str | None = None
    quality_report_file: Path | str | None = None
    researcher_note: str = ""
    task_id: str = field(default_factory=lambda: f"task-{uuid4().hex[:12]}")
    created_at: str = field(default_factory=lambda: _now_iso())
    started_at: str = ""
    finished_at: str = ""
    status: CrawlTaskStatus = CrawlTaskStatus.PENDING
    error_message: str = ""

    def __post_init__(self) -> None:
        """Normalize path-like fields after initialization."""

        self.output_dir = Path(self.output_dir)
        if self.output_file is not None:
            self.output_file = Path(self.output_file)
        if self.output_xlsx is not None:
            self.output_xlsx = Path(self.output_xlsx)
        if self.quality_report_file is not None:
            self.quality_report_file = Path(self.quality_report_file)


def _now_iso() -> str:
    """Return the current UTC time in ISO-8601 format."""

    return datetime.now(timezone.utc).isoformat()
