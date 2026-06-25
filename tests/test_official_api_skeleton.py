from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from douyin_academic_crawler.audit import AuditLogger
from douyin_academic_crawler.config import CrawlerConfig
from douyin_academic_crawler.official_api_client import (
    OfficialDouyinAPIClient,
    OfficialScopeError,
    OfficialTokenMissingError,
)
from douyin_academic_crawler.runtime import build_task_runner
from douyin_academic_crawler.service import CommentCollectionService
from douyin_academic_crawler.task import CrawlTask, CrawlTaskType
from douyin_academic_crawler.task_runner import CrawlTaskRunner


class OfficialAPISkeletonTest(unittest.TestCase):
    """Safety tests for official_api skeleton mode."""

    def test_official_api_default_is_rejected(self) -> None:
        """official_api cannot run with default real-request switches."""

        with self.assertRaisesRegex(RuntimeError, "allow_real_requests"):
            build_task_runner(CrawlerConfig(input_mode="official_api"))

    def test_allow_real_requests_false_is_rejected(self) -> None:
        """official_api requires allow_real_requests=True."""

        config = CrawlerConfig(input_mode="official_api", allow_real_requests=False)
        with self.assertRaisesRegex(RuntimeError, "allow_real_requests"):
            build_task_runner(config)

    def test_warning_ack_false_is_rejected(self) -> None:
        """official_api requires explicit warning acknowledgement."""

        config = CrawlerConfig(
            input_mode="official_api",
            allow_real_requests=True,
            real_request_warning_ack=False,
        )
        with self.assertRaisesRegex(RuntimeError, "real_request_warning_ack"):
            build_task_runner(config)

    def test_missing_token_file_has_clear_error(self) -> None:
        """Official client reports missing token files clearly."""

        config = CrawlerConfig(
            input_mode="official_api",
            allow_real_requests=True,
            real_request_warning_ack=True,
            official_access_token_file="does-not-exist-token.json",
        )
        with self.assertRaisesRegex(OfficialTokenMissingError, "Official access token file not found"):
            OfficialDouyinAPIClient(config)

    def test_missing_scope_is_rejected(self) -> None:
        """Official token must include video.comment scope."""

        with tempfile.TemporaryDirectory() as tmp:
            token = Path(tmp) / "token.json"
            token.write_text(
                json.dumps({"access_token": "token", "scopes": ["video.read"]}),
                encoding="utf-8",
            )
            config = CrawlerConfig(
                input_mode="official_api",
                allow_real_requests=True,
                real_request_warning_ack=True,
                official_access_token_file=str(token),
            )
            with self.assertRaisesRegex(OfficialScopeError, "video.comment"):
                OfficialDouyinAPIClient(config)

    def test_official_api_forces_depth_and_pages_to_one(self) -> None:
        """Task runner enforces official_api max_depth=1 and max_pages=1."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = CrawlerConfig(
                input_mode="official_api",
                allow_real_requests=True,
                real_request_warning_ack=True,
            )
            runner = CrawlTaskRunner(
                CommentCollectionService(
                    lambda output_path, error_path, max_depth: object(),
                    output_dir=output_dir,
                    mock_mode=False,
                    config=config,
                ),
                AuditLogger(output_dir / "audit.jsonl", config=config),
                config=config,
            )
            task = CrawlTask(
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-id",
                max_depth=2,
                max_pages=1,
                output_dir=output_dir,
            )

            result = runner.run(task)

            self.assertEqual(result.status.value, "failed")
            self.assertIn("official_api max_depth", result.error_message)

            task_pages = CrawlTask(
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-id",
                max_depth=1,
                max_pages=2,
                output_dir=output_dir,
            )
            result_pages = runner.run(task_pages)
            self.assertEqual(result_pages.status.value, "failed")
            self.assertIn("official_api max_pages", result_pages.error_message)

    def test_official_audit_fields_are_present(self) -> None:
        """Audit JSONL includes official API policy fields."""

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = CrawlerConfig(
                input_mode="official_api",
                allow_real_requests=True,
                real_request_warning_ack=True,
            )
            audit = AuditLogger(output_dir / "audit.jsonl", config=config)
            task = CrawlTask(
                task_type=CrawlTaskType.COMMENT_TREE.value,
                video_id="video-id",
                max_depth=1,
                max_pages=1,
                output_dir=output_dir,
            )

            audit.log_task(task, total_saved_count=0)

            record = json.loads((output_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["input_mode"], "official_api")
            self.assertTrue(record["official_api_mode"])
            self.assertEqual(record["scopes_required"], ["video.comment"])
            self.assertTrue(record["real_request_warning_ack"])
            self.assertIn("官方开放平台授权 API", record["request_policy_note"])

    def test_no_private_douyin_urls_are_present(self) -> None:
        """Official skeleton must not hardcode private Douyin web/App URLs."""

        source = Path("douyin_academic_crawler/official_api_client.py").read_text(encoding="utf-8")
        forbidden = [
            "aweme/v1",
            "aweme/v2",
            "iesdouyin.com",
            "snssdk.com",
            "amemv.com",
            "webcast",
        ]
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
