from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Optional, Tuple

from douyin_academic_crawler.api import CommentPage
from douyin_academic_crawler.collector import CommentTreeCollector
from douyin_academic_crawler.models import RawComment
from douyin_academic_crawler.rate_limit import SleepInterval
from douyin_academic_crawler.storage import CSVCommentStore, CSVFailureLogger


class FakeCommentAPI:
    def __init__(
        self,
        top_pages: Dict[Optional[str], CommentPage],
        reply_pages: Dict[Tuple[str, Optional[str]], CommentPage],
        failing_replies: set[str] | None = None,
    ) -> None:
        self.top_pages = top_pages
        self.reply_pages = reply_pages
        self.failing_replies = failing_replies or set()

    def fetch_top_level_comments(self, video_id: str, cursor: Optional[str] = None) -> CommentPage:
        return self.top_pages.get(cursor, CommentPage(comments=[]))

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        if comment_id in self.failing_replies:
            raise RuntimeError(f"reply page failed for {comment_id}")
        return self.reply_pages.get((comment_id, cursor), CommentPage(comments=[]))


def comment(comment_id: str, user: str = "user") -> RawComment:
    return RawComment(
        comment_id=comment_id,
        user_name=user,
        user_id=f"id-{comment_id}",
        user_uid=f"uid-{comment_id}",
        sec_uid=f"sec-{comment_id}",
        text=f"text {comment_id}",
    )


class CommentCollectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.output_path = root / "comments.csv"
        self.error_path = root / "errors.csv"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make_collector(self, api: FakeCommentAPI, max_depth: int) -> CommentTreeCollector:
        return CommentTreeCollector(
            api,
            CSVCommentStore(self.output_path),
            CSVFailureLogger(self.error_path),
            max_depth=max_depth,
            sleep_interval=SleepInterval(0, 0),
            hash_salt="test",
        )

    def read_rows(self) -> list[dict[str, str]]:
        with self.output_path.open("r", newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))

    def test_collects_only_first_level_comments(self) -> None:
        api = FakeCommentAPI(
            {None: CommentPage([comment("c1"), comment("c2")])},
            {("c1", None): CommentPage([comment("c1-1")])},
        )

        written = self.make_collector(api, max_depth=1).collect_comment_tree("v1")

        rows = self.read_rows()
        self.assertEqual(written, 2)
        self.assertEqual([row["comment_id"] for row in rows], ["c1", "c2"])
        self.assertEqual({row["depth"] for row in rows}, {"1"})

    def test_collects_second_level_comments(self) -> None:
        api = FakeCommentAPI(
            {None: CommentPage([comment("c1")])},
            {("c1", None): CommentPage([comment("c1-1"), comment("c1-2")])},
        )

        self.make_collector(api, max_depth=2).collect_comment_tree("v1")

        rows = self.read_rows()
        self.assertEqual([row["comment_path"] for row in rows], ["1", "1.1", "1.2"])
        self.assertEqual(rows[1]["parent_comment_id"], "c1")
        self.assertEqual(rows[1]["root_comment_id"], "c1")

    def test_collects_third_level_comments(self) -> None:
        api = FakeCommentAPI(
            {None: CommentPage([comment("c1")])},
            {
                ("c1", None): CommentPage([comment("c1-1")]),
                ("c1-1", None): CommentPage([comment("c1-1-1")]),
            },
        )

        self.make_collector(api, max_depth=3).collect_comment_tree("v1")

        rows = self.read_rows()
        self.assertEqual([row["depth"] for row in rows], ["1", "2", "3"])
        self.assertEqual(rows[-1]["comment_path"], "1.1.1")

    def test_collects_fourth_level_comments(self) -> None:
        api = FakeCommentAPI(
            {None: CommentPage([comment("c1")])},
            {
                ("c1", None): CommentPage([comment("c1-1")]),
                ("c1-1", None): CommentPage([comment("c1-1-1")]),
                ("c1-1-1", None): CommentPage([comment("c1-1-1-1")]),
            },
        )

        self.make_collector(api, max_depth=4).collect_comment_tree("v1")

        rows = self.read_rows()
        self.assertEqual([row["depth"] for row in rows], ["1", "2", "3", "4"])
        self.assertEqual(rows[-1]["comment_path"], "1.1.1.1")

    def test_max_depth_two_does_not_collect_deeper_comments(self) -> None:
        api = FakeCommentAPI(
            {None: CommentPage([comment("c1")])},
            {
                ("c1", None): CommentPage([comment("c1-1")]),
                ("c1-1", None): CommentPage([comment("c1-1-1")]),
            },
        )

        self.make_collector(api, max_depth=2).collect_comment_tree("v1")

        rows = self.read_rows()
        self.assertEqual([row["comment_id"] for row in rows], ["c1", "c1-1"])

    def test_duplicate_comment_id_is_skipped(self) -> None:
        api = FakeCommentAPI(
            {None: CommentPage([comment("c1"), comment("c1")])},
            {("c1", None): CommentPage([comment("c1-1"), comment("c1-1")])},
        )

        self.make_collector(api, max_depth=2).collect_comment_tree("v1")

        rows = self.read_rows()
        self.assertEqual([row["comment_id"] for row in rows], ["c1", "c1-1"])

    def test_exception_does_not_lose_already_saved_data(self) -> None:
        api = FakeCommentAPI(
            {None: CommentPage([comment("c1"), comment("c2")])},
            {("c2", None): CommentPage([comment("c2-1")])},
            failing_replies={"c1"},
        )

        written = self.make_collector(api, max_depth=2).collect_comment_tree(
            "v1", "https://example.invalid/video/v1"
        )

        rows = self.read_rows()
        self.assertEqual(written, 3)
        self.assertEqual([row["comment_id"] for row in rows], ["c1", "c2", "c2-1"])
        with self.error_path.open("r", newline="", encoding="utf-8-sig") as file:
            error_rows = list(csv.DictReader(file))
        self.assertEqual(error_rows[0]["comment_id"], "c1")
        self.assertIn("RuntimeError", error_rows[0]["error"])


if __name__ == "__main__":
    unittest.main()
