from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import scala_gate


class ScalaGateLockTests(unittest.TestCase):
    def test_lock_value_may_contain_equals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.lock"
            path.write_text("url=https://example.invalid/?a=b\n", encoding="utf-8")
            self.assertEqual("https://example.invalid/?a=b", scala_gate.parse_lock(path)["url"])

    def test_duplicate_lock_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.lock"
            path.write_text("sbt=1.10.11\nsbt=unlocked\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                scala_gate.parse_lock(path)

    def test_dependency_cache_rejects_tamper_and_extra_semantic_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jar = root / "coursier" / "v1" / "repo" / "library.jar"
            pom = root / "sbt-boot" / "sbt.properties"
            for path, text in ((jar, "jar\n"), (pom, "properties\n")):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            lock_path = root / "lock.json"
            scala_gate.write_json(
                lock_path, scala_gate.dependency_cache_manifest(root)
            )
            scala_gate.verify_dependency_cache(root, lock_path)
            extra = root / "coursier" / "v1" / "repo" / "extra.jar"
            extra.write_text("extra\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs"):
                scala_gate.verify_dependency_cache(root, lock_path)


class ScalaGateTestCountTests(unittest.TestCase):
    PASS_OUTPUT = """
Suites: completed 1, aborted 0
Tests: succeeded 2, failed 0, canceled 0, ignored 0, pending 0
Total number of tests run: 2
"""

    def test_complete_scalatest_outcome_is_accepted(self) -> None:
        outcome = scala_gate.scala_test_outcome(self.PASS_OUTPUT)
        self.assertTrue(scala_gate.scala_test_outcome_passed(outcome))

    def test_missing_skipped_or_failed_outcome_is_rejected(self) -> None:
        samples = (
            "[success] Total time: 1 s",
            self.PASS_OUTPUT.replace("ignored 0", "ignored 1"),
            self.PASS_OUTPUT.replace("failed 0", "failed 1"),
            self.PASS_OUTPUT.replace("aborted 0", "aborted 1"),
        )
        for output in samples:
            with self.subTest(output=output):
                self.assertFalse(
                    scala_gate.scala_test_outcome_passed(
                        scala_gate.scala_test_outcome(output)
                    )
                )


class ScalaGateWarningTests(unittest.TestCase):
    def test_spinal_and_verilator_warnings_are_detected(self) -> None:
        output = "[Warning] pruned\n%Warning-WIDTH: bad width\n[info] ordinary\n"
        self.assertEqual(
            ["[Warning] pruned", "%Warning-WIDTH: bad width"],
            scala_gate.forbidden_warning_lines(output),
        )

    def test_info_output_is_not_a_warning(self) -> None:
        self.assertEqual([], scala_gate.forbidden_warning_lines("[info] All tests passed."))

    def test_ansi_sbt_and_generic_warnings_are_detected(self) -> None:
        output = "\x1b[33m[warn] plugin warning\x1b[0m\nWARNING: generic\n%Warning-WIDTH no-colon\n"
        self.assertEqual(3, len(scala_gate.forbidden_warning_lines(output)))

    def test_verilator_policy_requires_effective_reenable_after_spinal_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "verilatorScript.sh"
            script.write_text(
                "verilator -Wall -Wno-WIDTH -Wwarn-WIDTH "
                "-Wno-UNOPTFLAT -Wwarn-UNOPTFLAT "
                "-Wno-CMPCONST -Wwarn-CMPCONST "
                "-Wno-UNSIGNED -Wwarn-UNSIGNED\n",
                encoding="utf-8",
            )
            self.assertTrue(scala_gate.verilator_script_policy(script)["passed"])
            script.write_text(script.read_text(encoding="utf-8") + "-Wno-WIDTH\n", encoding="utf-8")
            self.assertFalse(scala_gate.verilator_script_policy(script)["passed"])


class ScalaGateEnvironmentTests(unittest.TestCase):
    def test_environment_does_not_inherit_semantic_overrides(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"HOME": "/tmp/home", "LD_PRELOAD": "evil.so", "JAVA_TOOL_OPTIONS": "-Xbad"},
            clear=True,
        ):
            environment = scala_gate.clean_environment(
                [Path("/locked/bin")], {"JAVA_HOME": "/locked/java"}
            )
        self.assertEqual(str(Path("/tmp/home")), environment["HOME"])
        self.assertNotIn("LD_PRELOAD", environment)
        self.assertNotIn("JAVA_TOOL_OPTIONS", environment)

    def test_explicit_isolated_home_replaces_user_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(
            "os.environ", {"HOME": "/untrusted/home"}, clear=True
        ):
            isolated = Path(temporary) / "home"
            environment = scala_gate.clean_environment([], {}, home=isolated)
        self.assertEqual(str(isolated), environment["HOME"])


class ScalaGateWorkspaceTests(unittest.TestCase):
    def test_snapshot_copies_sources_but_never_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spinal = root / "source" / "spinal"
            manifest = root / "source" / "reference" / "manifest.lock"
            for relative, text in (
                ("build.sbt", "build\n"),
                (".scalafmt.conf", "format\n"),
                ("project/build.properties", "sbt.version=1.10.11\n"),
                ("project/plugins.sbt", "plugin\n"),
                ("src/main/scala/Main.scala", "object Main\n"),
                ("src/test/resources/blackbox.v", "module blackbox; endmodule\n"),
                ("target/stale.class", "stale\n"),
            ):
                path = spinal / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            manifest.parent.mkdir(parents=True)
            manifest.write_text("sbt=1.10.11\n", encoding="utf-8")
            isolated, isolated_manifest = scala_gate.copy_source_snapshot(
                spinal, manifest, root / "out" / "run"
            )
            self.assertEqual(
                scala_gate.source_fingerprint(spinal),
                scala_gate.source_fingerprint(isolated),
            )
            self.assertFalse((isolated / "target").exists())
            self.assertEqual(manifest.read_bytes(), isolated_manifest.read_bytes())

    def test_gate_lock_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary)
            lock = scala_gate.acquire_gate_lock(out_dir, "one")
            with self.assertRaisesRegex(ValueError, "already exists"):
                scala_gate.acquire_gate_lock(out_dir, "two")
            lock.unlink()


if __name__ == "__main__":
    unittest.main()
