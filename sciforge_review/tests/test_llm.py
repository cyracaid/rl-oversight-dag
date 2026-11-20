"""Tests for the yunshu/OpenAI-compatible client (no network)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sciforge_review.llm import LLMConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_reads_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "openai.env"
            path.write_text(
                "OPENAI_BASE_URL=https://example.test/v1\n"
                "OPENAI_API_KEY=test-key\n"
                "OPENAI_MODEL=test-model\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                config = load_config(env_path=path, include_defaults=False)
            self.assertEqual(config.base_url, "https://example.test/v1")
            self.assertEqual(config.model, "test-model")
            self.assertEqual(config.api_key, "test-key")
            self.assertNotIn("test-key", repr(config))

    def test_missing_key_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "openai.env"
            path.write_text("OPENAI_BASE_URL=https://example.test/v1\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(LLMConfigError):
                    load_config(env_path=path, include_defaults=False)

    def test_env_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "openai.env"
            path.write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "from-env"}, clear=True):
                config = load_config(env_path=path, include_defaults=False)
            self.assertEqual(config.api_key, "from-env")


if __name__ == "__main__":
    unittest.main()
