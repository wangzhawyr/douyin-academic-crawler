from __future__ import annotations

import json
import unittest
from pathlib import Path


class OfficialAPITemplatesTest(unittest.TestCase):
    """Tests for official API checklist, templates, and secret ignore rules."""

    def test_official_api_templates_exist(self) -> None:
        """Official API checklist and templates exist."""

        for path in [
            "docs/OFFICIAL_API_CHECKLIST.md",
            "examples/official_api_config.template.json",
            "examples/official_token.template.json",
        ]:
            self.assertTrue(Path(path).exists(), path)

    def test_templates_do_not_contain_real_tokens(self) -> None:
        """Templates contain placeholders, not real token values."""

        config = json.loads(Path("examples/official_api_config.template.json").read_text(encoding="utf-8"))
        token = json.loads(Path("examples/official_token.template.json").read_text(encoding="utf-8"))

        self.assertEqual(token["access_token"], "YOUR_ACCESS_TOKEN")
        self.assertEqual(token["refresh_token"], "YOUR_REFRESH_TOKEN")
        self.assertIn("OFFICIAL_OPEN_PLATFORM_BASE_URL_FROM_DOCUMENTATION", config["official_api_base_url"])
        self.assertNotIn("Bearer ", json.dumps(token))
        self.assertNotIn("eyJ", json.dumps(token))

    def test_gitignore_contains_token_and_secret_rules(self) -> None:
        """Sensitive token and secret files are ignored."""

        text = Path(".gitignore").read_text(encoding="utf-8")
        for rule in [
            "cookie.txt",
            "token.json",
            "official_token.json",
            "*token*.json",
            "*secret*.json",
        ]:
            self.assertIn(rule, text)


if __name__ == "__main__":
    unittest.main()
