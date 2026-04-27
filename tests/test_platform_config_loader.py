import os
import tempfile
import unittest
from pathlib import Path

from backend.app.core.config import _load_env_file


class ConfigLoaderTest(unittest.TestCase):
    def test_load_env_file_sets_missing_variables_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text(
                "TEST_PLATFORM_ALPHA=one\nTEST_PLATFORM_BETA='two'\nTEST_PLATFORM_KEPT=from_file\n",
                encoding="utf-8",
            )
            os.environ.pop("TEST_PLATFORM_ALPHA", None)
            os.environ.pop("TEST_PLATFORM_BETA", None)
            os.environ["TEST_PLATFORM_KEPT"] = "existing"

            _load_env_file(env_path)

            self.assertEqual(os.environ["TEST_PLATFORM_ALPHA"], "one")
            self.assertEqual(os.environ["TEST_PLATFORM_BETA"], "two")
            self.assertEqual(os.environ["TEST_PLATFORM_KEPT"], "existing")


if __name__ == "__main__":
    unittest.main()
