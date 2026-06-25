"""Tkinter GUI helpers for comment collection."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .config import CrawlerConfig
from .task import CrawlTask, CrawlTaskType
from .task_runner import CrawlTaskRunner


COMMENT_DEPTH_OPTIONS = {
    "1 级评论": 1,
    "2 级评论": 2,
    "3 级评论": 3,
    "4 级评论": 4,
}


def create_comment_depth_selector(
    parent: tk.Misc,
    *,
    default_depth: int = 4,
    on_change: Callable[[int], None] | None = None,
) -> ttk.Combobox:
    """Create a read-only dropdown for selecting the maximum comment depth."""

    if default_depth not in COMMENT_DEPTH_OPTIONS.values():
        raise ValueError("default_depth must be one of 1, 2, 3, or 4")

    labels = list(COMMENT_DEPTH_OPTIONS.keys())
    selected_label = label_for_depth(default_depth)
    variable = tk.StringVar(parent, value=selected_label)
    combo = ttk.Combobox(parent, textvariable=variable, values=labels, state="readonly")

    def handle_change(_: tk.Event[ttk.Combobox]) -> None:
        """Notify callers when the user changes the maximum comment depth."""

        if on_change is not None:
            on_change(COMMENT_DEPTH_OPTIONS[variable.get()])

    combo.bind("<<ComboboxSelected>>", handle_change)
    return combo


def label_for_depth(depth: int) -> str:
    """Return the dropdown label for a numeric comment depth."""

    for label, option_depth in COMMENT_DEPTH_OPTIONS.items():
        if option_depth == depth:
            return label
    raise ValueError("depth must be one of 1, 2, 3, or 4")


class CommentCollectionFrame(ttk.Frame):
    """Comment collection panel that delegates all execution to a task runner."""

    def __init__(
        self,
        parent: tk.Misc,
        task_runner: CrawlTaskRunner,
        *,
        config: CrawlerConfig | None = None,
        default_video_id: str = "",
        default_depth: int = 4,
    ) -> None:
        """Build the comment collection controls."""

        super().__init__(parent)
        self.task_runner = task_runner
        self.config = config or task_runner.config
        self.video_id_var = tk.StringVar(self, value=default_video_id)
        self.depth_var = tk.StringVar(self, value=label_for_depth(default_depth))
        self.max_pages_var = tk.StringVar(self, value=str(self.config.max_pages_default))

        ttk.Label(self, text="视频 ID").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.video_id_entry = ttk.Entry(self, textvariable=self.video_id_var)
        self.video_id_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(self, text="最大评论层级").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.depth_combo = ttk.Combobox(
            self,
            textvariable=self.depth_var,
            values=list(COMMENT_DEPTH_OPTIONS.keys()),
            state="readonly",
        )
        self.depth_combo.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(self, text="最大页数").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.max_pages_entry = ttk.Entry(self, textvariable=self.max_pages_var)
        self.max_pages_entry.grid(row=2, column=1, sticky="ew", padx=4, pady=4)

        self.mode_label = ttk.Label(self, text=self._mode_text(), justify="left")
        self.mode_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=4)

        self.start_button = ttk.Button(self, text="开始采集", command=self.start_collection)
        self.start_button.grid(row=4, column=0, columnspan=2, sticky="ew", padx=4, pady=4)

        self.log_text = tk.Text(self, height=8, width=60)
        self.log_text.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(5, weight=1)

    def get_max_depth(self) -> int:
        """Return the numeric depth selected in the dropdown."""

        return COMMENT_DEPTH_OPTIONS[self.depth_var.get()]

    def get_max_pages(self) -> int:
        """Return the validated max_pages value from the entry."""

        try:
            max_pages = int(self.max_pages_var.get())
        except ValueError as exc:
            raise ValueError("最大页数必须是整数") from exc
        if max_pages < 1 or max_pages > self.config.max_pages_hard_limit:
            raise ValueError(f"最大页数必须在 1 到 {self.config.max_pages_hard_limit} 之间")
        return max_pages

    def append_log(self, message: str) -> None:
        """Append one log line to the GUI log area."""

        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def start_collection(self) -> None:
        """Create a task and execute it through the task runner."""

        try:
            max_pages = self.get_max_pages()
        except ValueError as exc:
            self.append_log(f"错误：{exc}")
            return

        previous_runner_log = self.task_runner.log_callback
        previous_service_log = self.task_runner.service.log_callback

        def gui_runner_log(message: str) -> None:
            if previous_runner_log is not None:
                previous_runner_log(message)
            self.append_log(message)

        def gui_service_log(message: str) -> None:
            if previous_service_log is not None:
                previous_service_log(message)
            self.append_log(message)

        self.task_runner.log_callback = gui_runner_log
        self.task_runner.service.log_callback = gui_service_log

        task = CrawlTask(
            task_type=CrawlTaskType.COMMENT_TREE.value,
            video_id=self.video_id_var.get().strip(),
            max_depth=self.get_max_depth(),
            max_pages=max_pages,
            output_dir=self.task_runner.service.output_dir,
        )
        self.append_log(f"task_id：{task.task_id}")
        self.task_runner.run(task)

    def _mode_text(self) -> str:
        """Return the visible safety mode text."""

        if self.config.input_mode == "local_json":
            mode = "本地 JSON 导入模式"
        elif self.config.input_mode == "official_api":
            mode = "官方授权 API 骨架模式"
        elif self.config.input_mode == "mock":
            mode = "Mock 验收模式"
        else:
            mode = "真实请求禁用"
        real_requests = "已启用" if self.config.allow_real_requests else "已禁用"
        return (
            f"当前模式：{mode}\n"
            f"真实请求：{real_requests}\n"
            f"最大页数限制：{self.config.max_pages_hard_limit}\n"
            f"最大评论层级限制：{self.config.max_depth_hard_limit}\n"
            f"文本清洗：{self._enabled_text(self.config.enable_text_cleaning)}\n"
            f"去 URL：{self._enabled_text(self.config.remove_urls)}\n"
            f"Excel 导出：{self._enabled_text(self.config.export_xlsx)}\n"
            f"质量报告路径：{self.task_runner.service.reports_dir}"
        )

    @staticmethod
    def _enabled_text(value: bool) -> str:
        """Return localized enabled/disabled text."""

        return "开启" if value else "关闭"
