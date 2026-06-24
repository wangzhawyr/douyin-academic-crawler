from __future__ import annotations

import csv
import re
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Optional, Tuple

from douyin_academic_crawler.api import CommentPage
from douyin_academic_crawler.collector import CommentTreeCollector
from douyin_academic_crawler.models import RawComment
from douyin_academic_crawler.rate_limit import SleepInterval
from douyin_academic_crawler.storage import COMMENT_FIELDNAMES, CSVCommentStore, CSVFailureLogger


class FixtureCommentAPI:
    """Mock comment API backed by in-memory fixture pages."""

    def __init__(
        self,
        *,
        duplicate_second_level: bool = False,
        failing_replies: set[str] | None = None,
    ) -> None:
        """Build a fixture tree with optional duplicate IDs and failing reply pages."""

        second_level = [self._comment("c1-1", "alice")]
        if duplicate_second_level:
            second_level.append(self._comment("c1-1", "alice duplicate"))

        self.top_pages: Dict[Optional[str], CommentPage] = {
            None: CommentPage([self._comment("c1", "root user")])
        }
        self.reply_pages: Dict[Tuple[str, Optional[str]], CommentPage] = {
            ("c1", None): CommentPage(second_level),
            ("c1-1", None): CommentPage([self._comment("c1-1-1", "third user")]),
            ("c1-1-1", None): CommentPage([self._comment("c1-1-1-1", "fourth user")]),
        }
        self.failing_replies = failing_replies or set()

    def fetch_top_level_comments(self, video_id: str, cursor: Optional[str] = None) -> CommentPage:
        """Return a fixture top-level comment page."""

        return self.top_pages.get(cursor, CommentPage(comments=[]))

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Return a fixture reply page or raise a configured mock failure."""

        if comment_id in self.failing_replies:
            raise RuntimeError(f"fixture reply failure for {comment_id}")
        return self.reply_pages.get((comment_id, cursor), CommentPage(comments=[]))

    @staticmethod
    def _comment(comment_id: str, user_name: str) -> RawComment:
        """Create a fully populated fixture comment."""

        return RawComment(
            comment_id=comment_id,
            user_name=user_name,
            user_id=f"user-id-{comment_id}",
            user_uid=f"uid-{comment_id}",
            sec_uid=f"sec-{comment_id}",
            comment_time="2026-06-24T12:00:00+08:00",
            ip_location="北京",
            like_count=7,
            text=f"fixture text {comment_id}",
            reply_to_comment_id=None,
            reply_to_user_name=None,
        )


class CommentTreeEndToEndTest(unittest.TestCase):
    """End-to-end verification for fixture-based four-level comment export."""

    def test_fixture_comment_tree_csv_export_end_to_end(self) -> None:
        """Collect fixture comments and verify CSV fields, depth, paths, resume, and failures."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            normal_rows = self._collect_rows(root / "normal.csv", root / "normal_errors.csv", 4)

            self.assertEqual(list(normal_rows[0].keys()), COMMENT_FIELDNAMES)
            self.assertEqual(max(int(row["depth"]) for row in normal_rows), 4)
            self.assertEqual(
                [row["comment_path"] for row in normal_rows],
                ["1", "1.1", "1.1.1", "1.1.1.1"],
            )
            self.assertTrue(all(re.fullmatch(r"\d+(?:\.\d+){0,3}", row["comment_path"]) for row in normal_rows))
            self.assertEqual({row["video_id"] for row in normal_rows}, {"video-fixture-001"})
            self.assertEqual(normal_rows[1]["parent_comment_id"], "c1")
            self.assertEqual(normal_rows[2]["root_comment_id"], "c1")
            self.assertEqual(normal_rows[3]["reply_to_comment_id"], "c1-1-1")
            self.assertNotIn("user-id-c1", normal_rows[0]["comment_user_id_hash"])
            self.assertNotIn("uid-c1", normal_rows[0]["comment_user_uid_hash"])

            limited_rows = self._collect_rows(root / "limited.csv", root / "limited_errors.csv", 2)
            self.assertEqual([row["comment_id"] for row in limited_rows], ["c1", "c1-1"])
            self.assertLessEqual(max(int(row["depth"]) for row in limited_rows), 2)

            duplicate_rows = self._collect_rows(
                root / "duplicate.csv",
                root / "duplicate_errors.csv",
                4,
                duplicate_second_level=True,
            )
            self.assertEqual(
                [row["comment_id"] for row in duplicate_rows],
                ["c1", "c1-1", "c1-1-1", "c1-1-1-1"],
            )

            failing_rows = self._collect_rows(
                root / "failing.csv",
                root / "failing_errors.csv",
                4,
                failing_replies={"c1-1"},
            )
            self.assertEqual([row["comment_id"] for row in failing_rows], ["c1", "c1-1"])
            self.assertTrue((root / "failing_errors.csv").exists())

    def _collect_rows(
        self,
        output_path: Path,
        error_path: Path,
        max_depth: int,
        *,
        duplicate_second_level: bool = False,
        failing_replies: set[str] | None = None,
    ) -> list[dict[str, str]]:
        """Run the collector against fixture data and return exported CSV rows."""

        collector = CommentTreeCollector(
            FixtureCommentAPI(
                duplicate_second_level=duplicate_second_level,
                failing_replies=failing_replies,
            ),
            CSVCommentStore(output_path),
            CSVFailureLogger(error_path),
            max_depth=max_depth,
            sleep_interval=SleepInterval(0, 0),
            hash_salt="fixture-test",
        )
        collector.collect_comment_tree("video-fixture-001", "https://example.invalid/video-fixture-001")
        with output_path.open("r", newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))


if __name__ == "__main__":
    unittest.main()
