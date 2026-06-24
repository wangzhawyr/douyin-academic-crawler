"""Data quality reporting for comment exports."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class DataQualityReport:
    """Generate JSON quality reports for exported comment rows."""

    reports_dir: Path | str

    def generate(
        self,
        *,
        task_id: str,
        video_id: str,
        rows: list[Mapping[str, object]],
        output_csv: Path | str,
        output_xlsx: Path | str | None = None,
    ) -> Path:
        """Write and return a quality report JSON file."""

        reports_path = Path(self.reports_dir)
        reports_path.mkdir(parents=True, exist_ok=True)
        report_path = reports_path / f"{task_id}_quality_report.json"
        comment_ids = [str(row.get("comment_id") or "") for row in rows if row.get("comment_id")]
        times = [str(row.get("comment_time") or "") for row in rows if row.get("comment_time")]
        distribution = Counter(str(row.get("depth") or "") for row in rows)
        report = {
            "task_id": task_id,
            "video_id": video_id,
            "total_rows": len(rows),
            "depth_distribution": dict(sorted(distribution.items())),
            "missing_text_count": sum(1 for row in rows if not str(row.get("comment_text") or "").strip()),
            "duplicate_comment_id_count": len(comment_ids) - len(set(comment_ids)),
            "min_comment_time": min(times) if times else "",
            "max_comment_time": max(times) if times else "",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "output_csv": str(output_csv),
            "output_xlsx": str(output_xlsx or ""),
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report_path
