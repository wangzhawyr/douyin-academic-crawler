from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path


class MockRunCLITest(unittest.TestCase):
    """End-to-end CLI test for the non-GUI mock acceptance command."""

    def test_mock_run_cli_completes_with_outputs(self) -> None:
        """mock-run exits within timeout and writes CSV, audit, and runtime log."""

        repo_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [
                sys.executable,
                "main.py",
                "--mock-run",
                "--config",
                "examples/sample_config.json",
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("loading config", result.stdout)
        self.assertIn("mock_mode=True", result.stdout)
        self.assertIn("creating task", result.stdout)
        self.assertIn("running task", result.stdout)
        self.assertIn("writing csv", result.stdout)
        self.assertIn("writing audit log", result.stdout)
        self.assertIn("done", result.stdout)
        csv_files = list((repo_root / "exports" / "comments").glob("comments_video-fixture-001_depth4_task-*.csv"))
        self.assertTrue(csv_files)
        latest_csv = max(csv_files, key=lambda path: path.stat().st_mtime)
        with latest_csv.open("r", newline="", encoding="utf-8-sig") as file:
            rows = list(csv.DictReader(file))
        self.assertGreaterEqual(len(rows), 4)
        self.assertTrue({"c1", "c1-1", "c1-1-1", "c1-1-1-1"}.issubset({row["comment_id"] for row in rows}))

        audit_path = repo_root / "exports" / "audit" / "audit.jsonl"
        self.assertTrue(audit_path.exists())
        with audit_path.open("r", encoding="utf-8") as file:
            audit_records = [json.loads(line) for line in file if line.strip()]
        self.assertEqual(audit_records[-1]["total_saved_count"], 4)
        self.assertTrue((repo_root / "exports" / "logs" / "runtime.log").exists())


if __name__ == "__main__":
    unittest.main()
