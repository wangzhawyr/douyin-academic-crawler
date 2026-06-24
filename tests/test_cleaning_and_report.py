from __future__ import annotations

import csv
import json
import logging
import tempfile
import unittest
import zipfile
from pathlib import Path

from douyin_academic_crawler.cleaner import CommentDataCleaner
from douyin_academic_crawler.config import CrawlerConfig
from douyin_academic_crawler.runtime import run_mock_acceptance_task


class CleaningAndReportTest(unittest.TestCase):
    """Tests for text cleaning, XLSX export, reports, and audit fields."""

    def test_cleaner_preserves_original_and_adds_cleaned_fields(self) -> None:
        """Cleaner preserves comment_text and adds cleaned_comment_text plus flags."""

        row = {"comment_text": "  hello\nhttps://example.com @alice 😀  "}
        cleaned = CommentDataCleaner(remove_urls=True, remove_mentions=False, remove_emoji=False).clean_row(row)

        self.assertEqual(cleaned["comment_text"], row["comment_text"])
        self.assertEqual(cleaned["cleaned_comment_text"], "hello @alice 😀")
        self.assertTrue(cleaned["has_url"])
        self.assertTrue(cleaned["has_mention"])
        self.assertTrue(cleaned["has_emoji"])
        self.assertEqual(cleaned["text_length"], len("hello @alice 😀"))

    def test_cleaning_exports_xlsx_quality_report_and_audit_fields(self) -> None:
        """Runtime post-processing writes enhanced CSV, XLSX, quality report, and audit."""

        with tempfile.TemporaryDirectory() as tmp:
            try:
                root = Path(tmp)
                fixture = root / "local_text_fixture.json"
                fixture.write_text(
                    json.dumps(
                        {
                            "comments": [
                                {
                                    "comment_id": "clean-c1",
                                    "user_name": "root",
                                    "comment_time": "2026-06-25T10:00:00+08:00",
                                    "text": "  root line\nhttps://example.com @researcher 😀  ",
                                    "replies": [
                                        {
                                            "comment_id": "clean-c1-1",
                                            "user_name": "reply",
                                            "comment_time": "2026-06-25T10:01:00+08:00",
                                            "text": "reply text",
                                            "replies": [],
                                        }
                                    ],
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                output_dir = root / "exports"
                config = CrawlerConfig(
                    output_dir=output_dir,
                    input_mode="local_json",
                    input_json_file=str(fixture),
                    enable_text_cleaning=True,
                    remove_urls=True,
                    remove_mentions=False,
                    remove_emoji=False,
                    export_xlsx=True,
                )

                result = run_mock_acceptance_task(config, video_id="video-cleaning-001", max_depth=2)

                self.assertEqual(result.status.value, "success")
                csv_file = next((output_dir / "comments").glob("comments_video-cleaning-001_depth2_task-*.csv"))
                xlsx_file = csv_file.with_suffix(".xlsx")
                report_file = next((output_dir / "reports").glob("*_quality_report.json"))
                audit_file = output_dir / "audit" / "audit.jsonl"

                with csv_file.open("r", newline="", encoding="utf-8-sig") as file:
                    rows = list(csv.DictReader(file))
                self.assertIn("cleaned_comment_text", rows[0])
                self.assertIn("text_length", rows[0])
                self.assertIn("has_url", rows[0])
                self.assertIn("has_mention", rows[0])
                self.assertIn("has_emoji", rows[0])
                self.assertEqual(rows[0]["comment_text"], "  root line\nhttps://example.com @researcher 😀  ")
                self.assertEqual(rows[0]["cleaned_comment_text"], "root line @researcher 😀")
                self.assertEqual(rows[0]["has_url"], "True")
                self.assertEqual(rows[0]["has_mention"], "True")
                self.assertEqual(rows[0]["has_emoji"], "True")

                self.assertTrue(xlsx_file.exists())
                with zipfile.ZipFile(xlsx_file) as archive:
                    self.assertIn("xl/worksheets/sheet1.xml", archive.namelist())
                    self.assertIn("xl/worksheets/sheet2.xml", archive.namelist())

                report = json.loads(report_file.read_text(encoding="utf-8"))
                self.assertEqual(report["total_rows"], 2)
                self.assertEqual(report["depth_distribution"], {"1": 1, "2": 1})
                self.assertEqual(report["missing_text_count"], 0)
                self.assertEqual(report["duplicate_comment_id_count"], 0)
                self.assertEqual(report["output_csv"], str(csv_file))
                self.assertEqual(report["output_xlsx"], str(xlsx_file))

                audit_records = [
                    json.loads(line)
                    for line in audit_file.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                audit = audit_records[-1]
                self.assertEqual(audit["quality_report_file"], str(report_file))
                self.assertEqual(audit["output_xlsx"], str(xlsx_file))
                self.assertTrue(audit["cleaning_enabled"])
            finally:
                logging.shutdown()
                logging.getLogger().handlers.clear()


if __name__ == "__main__":
    unittest.main()
