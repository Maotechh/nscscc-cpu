from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import local_env


class LocalEnvironmentTests(unittest.TestCase):
    def test_sha256_file_reports_content_and_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact"
            path.write_bytes(b"echo\n")
            self.assertEqual(
                local_env.sha256_file(path),
                "86b0c5a1e2b73b08fd54c727f4458649ed9fe3ad1b6e8ac9460c070113509a1e",
            )
            self.assertIsNone(local_env.sha256_file(path.with_name("missing")))

    def test_resolve_tool_uses_executable_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fallback-tool"
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            self.assertEqual(
                local_env.resolve_tool("definitely-not-a-real-tool", str(path)),
                path.resolve(),
            )

    def test_artifact_info_does_not_require_executable_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.so"
            path.write_bytes(b"binary evidence")
            info = local_env.artifact_info("library", path)
            self.assertEqual(info["status"], "present")
            self.assertEqual(info["path"], str(path.resolve()))
            self.assertIsNotNone(info["sha256"])


if __name__ == "__main__":
    unittest.main()
