from __future__ import annotations

import json
import unittest
from pathlib import Path


class DocsAndScriptsTest(unittest.TestCase):
    """Delivery documentation and script existence tests."""

    def test_delivery_docs_scripts_and_manifest_exist(self) -> None:
        """Required delivery files exist."""

        required = [
            "docs/FIELD_DICTIONARY.md",
            "docs/USER_GUIDE.md",
            "docs/DEVELOPER_GUIDE.md",
            "scripts/run_acceptance.ps1",
            "scripts/show_latest_outputs.ps1",
            "scripts/clean_outputs.ps1",
            "release_manifest.json",
        ]
        for path in required:
            self.assertTrue(Path(path).exists(), path)

    def test_field_dictionary_contains_core_fields(self) -> None:
        """Field dictionary documents key analysis fields."""

        text = Path("docs/FIELD_DICTIONARY.md").read_text(encoding="utf-8")
        for field in ["depth", "comment_path", "cleaned_comment_text", "has_url"]:
            self.assertIn(field, text)

    def test_release_manifest_is_valid_json(self) -> None:
        """Release manifest contains expected top-level metadata."""

        manifest = json.loads(Path("release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["project_name"], "douyin-academic-crawler")
        self.assertIn("mock", manifest["supported_input_modes"])
        self.assertIn("local_json", manifest["supported_input_modes"])


if __name__ == "__main__":
    unittest.main()
