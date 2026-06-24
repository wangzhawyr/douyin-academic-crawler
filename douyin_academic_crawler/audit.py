"""Research audit logging for crawl tasks."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import CrawlerConfig
from .task import CrawlTask


DEFAULT_COMPLIANCE_NOTE = (
    "本任务仅用于学术研究，仅保存研究者有权访问范围内平台正常返回的数据；"
    "不包含自动登录、破解、绕过验证码、规避频控或获取不可访问数据的逻辑。"
)


class AuditLogger:
    """Append task audit records to a JSONL file."""

    def __init__(
        self,
        audit_path: Path | str = Path("exports") / "audit.jsonl",
        *,
        config: CrawlerConfig | None = None,
        compliance_note: str = DEFAULT_COMPLIANCE_NOTE,
    ) -> None:
        """Create an audit logger for the given JSONL path."""

        self.audit_path = Path(audit_path)
        self.config = config or CrawlerConfig()
        self.compliance_note = compliance_note
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def log_task(
        self,
        task: CrawlTask,
        *,
        total_saved_count: int,
    ) -> None:
        """Append one task audit record."""

        record: dict[str, Any] = {
            "task_id": task.task_id,
            "task_type": str(task.task_type),
            "video_id": task.video_id,
            "video_url": task.video_url,
            "max_depth": task.max_depth,
            "max_pages": task.max_pages,
            "output_file": str(task.output_file or ""),
            "output_xlsx": str(task.output_xlsx or ""),
            "quality_report_file": str(task.quality_report_file or ""),
            "started_at": task.started_at,
            "finished_at": task.finished_at,
            "status": str(task.status.value if hasattr(task.status, "value") else task.status),
            "total_saved_count": total_saved_count,
            "error_message": task.error_message,
            "compliance_note": self.compliance_note,
            "mock_mode": self.config.mock_mode,
            "allow_real_requests": self.config.allow_real_requests,
            "input_mode": self.config.input_mode,
            "input_json_file": self.config.input_json_file,
            "data_source_note": self._data_source_note(),
            "cleaning_enabled": self.config.enable_text_cleaning,
            "max_pages_hard_limit": self.config.max_pages_hard_limit,
            "max_depth_hard_limit": self.config.max_depth_hard_limit,
            "config_snapshot": self._config_snapshot(),
        }
        with self.audit_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _config_snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of safety-relevant config."""

        snapshot = asdict(self.config)
        return {key: str(value) if isinstance(value, Path) else value for key, value in snapshot.items()}

    def _data_source_note(self) -> str:
        """Return an audit note describing the task input source."""

        if self.config.input_mode == "local_json":
            return "本任务使用本地 JSON 文件作为输入，不发起真实平台请求。"
        if self.config.input_mode == "mock":
            return "本任务使用内置 mock fixture 作为输入，不发起真实平台请求。"
        return "真实请求模式未启用。"
