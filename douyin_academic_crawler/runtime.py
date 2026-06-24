"""Runtime assembly for local GUI and offline acceptance runs."""

from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .audit import AuditLogger
from .collector import CommentTreeCollector
from .config import CrawlerConfig, load_config
from .gui import CommentCollectionFrame
from .local_json_client import LocalJSONCommentClient
from .mock_client import MockCommentAPIClient
from .rate_limit import SleepInterval
from .service import CommentCollectionService
from .storage import CSVCommentStore, CSVFailureLogger
from .task import CrawlTask, CrawlTaskType
from .task_runner import CrawlTaskResult, CrawlTaskRunner


@dataclass(frozen=True)
class OutputDirectories:
    """Standard local output directories."""

    root: Path
    comments: Path
    audit: Path
    logs: Path
    reports: Path


def ensure_output_directories(output_dir: Path | str) -> OutputDirectories:
    """Create and return the standard local output directory layout."""

    root = Path(output_dir)
    directories = OutputDirectories(
        root=root,
        comments=root / "comments",
        audit=root / "audit",
        logs=root / "logs",
        reports=root / "reports",
    )
    for directory in (
        directories.root,
        directories.comments,
        directories.audit,
        directories.logs,
        directories.reports,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return directories


def configure_runtime_logging(log_dir: Path | str) -> Path:
    """Configure runtime logging and return the log file path."""

    log_path = Path(log_dir) / "runtime.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
        force=True,
    )
    logging.info("program started")
    return log_path


def build_task_runner(
    config: CrawlerConfig,
    *,
    log_callback: Callable[[str], None] | None = None,
) -> CrawlTaskRunner:
    """Build a task runner wired to the configured offline input source."""

    if config.input_mode == "real_request":
        raise NotImplementedError("真实请求尚未启用。")
    if config.input_mode not in {"mock", "local_json"}:
        raise ValueError("input_mode must be mock or local_json")
    if not config.mock_mode and not config.allow_real_requests:
        raise NotImplementedError("当前处于 mock 验收模式，真实请求已被禁用。")

    directories = ensure_output_directories(config.output_dir)
    configure_runtime_logging(directories.logs)

    def collector_factory(output_path: Path, error_path: Path, max_depth: int) -> CommentTreeCollector:
        if config.input_mode == "local_json":
            if not config.input_json_file:
                raise ValueError("input_json_file is required when input_mode=local_json")
            api_client = LocalJSONCommentClient(config.input_json_file)
            hash_salt = "local-json-import"
        else:
            api_client = MockCommentAPIClient()
            hash_salt = "mock-acceptance"
        return CommentTreeCollector(
            api_client,
            CSVCommentStore(output_path),
            CSVFailureLogger(error_path),
            max_depth=max_depth,
            sleep_interval=SleepInterval(0, 0),
            hash_salt=hash_salt,
        )

    def runtime_log(message: str) -> None:
        logging.info(message)
        if log_callback is not None:
            log_callback(message)

    service = CommentCollectionService(
        collector_factory,
        output_dir=directories.comments,
        reports_dir=directories.reports,
        config=config,
        clock=datetime.now,
        log_callback=runtime_log,
        mock_mode=True,
    )
    return CrawlTaskRunner(
        service,
        AuditLogger(directories.audit / "audit.jsonl", config=config),
        config=config,
        log_callback=runtime_log,
        clock=datetime.now,
    )


def build_mock_task_runner(
    config: CrawlerConfig,
    *,
    log_callback: Callable[[str], None] | None = None,
) -> CrawlTaskRunner:
    """Backward-compatible wrapper for local/offline task runner assembly."""

    return build_task_runner(config, log_callback=log_callback)


def run_mock_acceptance_task(
    config: CrawlerConfig | None = None,
    *,
    video_id: str = "video-fixture-001",
    max_depth: int = 4,
    progress: Callable[[str], None] | None = None,
) -> CrawlTaskResult:
    """Run one offline comment task for local acceptance testing."""

    emit = progress or (lambda message: None)
    effective_config = config or CrawlerConfig()
    emit("mock_mode=True" if effective_config.mock_mode else "mock_mode=False")
    emit(f"input_mode={effective_config.input_mode}")
    emit("creating task")
    runner = build_task_runner(effective_config)
    task = CrawlTask(
        task_type=CrawlTaskType.COMMENT_TREE.value,
        video_id=video_id,
        video_url=f"https://example.invalid/{video_id}",
        max_depth=max_depth,
        output_dir=runner.service.output_dir,
        researcher_note="local offline acceptance run",
    )
    logging.info("task created: %s", task.task_id)
    emit(f"task_id={task.task_id}")
    emit("running task")
    result = runner.run(task)
    if result.status.value == "success":
        logging.info("task completed: %s saved=%s", task.task_id, result.total_saved_count)
        emit("writing csv")
        emit("writing audit log")
        emit("mock acceptance completed")
        emit("done")
    else:
        logging.error("task failed: %s error=%s", task.task_id, result.error_message)
        emit(f"error: {result.error_message}")
    return result


def launch_gui(config: CrawlerConfig | None = None) -> None:
    """Launch the local Tkinter GUI in offline acceptance mode."""

    effective_config = config or CrawlerConfig()
    runner = build_task_runner(effective_config)
    root = tk.Tk()
    root.title("Douyin Academic Crawler - Offline Acceptance")
    frame = CommentCollectionFrame(
        root,
        runner,
        config=effective_config,
        default_video_id="video-fixture-001",
    )
    frame.pack(fill="both", expand=True, padx=12, pady=12)
    logging.info("gui started input_mode=%s mock_mode=%s", effective_config.input_mode, effective_config.mock_mode)
    root.mainloop()


def load_runtime_config(config_path: Path | str | None = None) -> CrawlerConfig:
    """Load runtime config for CLI entry points."""

    return load_config(config_path)
