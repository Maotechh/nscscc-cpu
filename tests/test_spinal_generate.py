from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import spinal_generate


VALID_RTL = b"module core_top(input wire aclk);\nendmodule\n"


class SpinalGenerateFixture:
    def __init__(self, root: Path) -> None:
        self.repo = root / "repo"
        self.reference = self.repo / "reference"
        self.spinal = self.repo / "spinal"
        self.rtl = self.repo / "rtl"
        self.tools = root / "locked-tools"
        self.out = self.repo / "build" / "generated"
        self.reference.mkdir(parents=True)
        self.rtl.mkdir(parents=True)
        (self.rtl / "existing.v").write_text("module existing; endmodule\n", encoding="ascii")
        for relative in (
            ".scalafmt.conf",
            "build.sbt",
            "project/build.properties",
            "project/plugins.sbt",
        ):
            path = self.spinal / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(relative + "\n", encoding="utf-8")
        generator = self.spinal / "src/main/scala/miku/compat/GenerateCoreTopCompat.scala"
        generator.parent.mkdir(parents=True)
        generator.write_text(
            "package miku.compat\nobject GenerateCoreTopCompat { def main(args: Array[String]) = () }\n",
            encoding="utf-8",
        )
        test_source = self.spinal / "src/test/scala/miku/CompatSpec.scala"
        test_source.parent.mkdir(parents=True)
        test_source.write_text("package miku\n", encoding="utf-8")
        self.java = root / ("java.exe" if os.name == "nt" else "java")
        self.java.write_bytes(b"locked-java")
        if os.name != "nt":
            self.java.chmod(0o755)
        self.sbt = self.tools / "sbt-1.10.11/bin/sbt-launch.jar"
        self.sbt.parent.mkdir(parents=True)
        self.sbt.write_bytes(b"locked-sbt")
        self.dependency_lock = self.reference / spinal_generate.SCALA_DEPENDENCY_LOCK
        self.dependency_lock.write_text("{}\n", encoding="utf-8")
        self.manifest = self.reference / "manifest.lock"
        self.manifest.write_text(
            "jdk=17.0.19+10\n"
            "java_binary_sha256=" + spinal_generate.sha256_file(self.java) + "\n"
            "sbt=1.10.11\n"
            "sbt_launch_jar_sha256=" + spinal_generate.sha256_file(self.sbt) + "\n"
            "scala=2.13.16\n"
            "spinalhdl=1.14.2\n"
            "scala_cache_dir=cache\n"
            "scala_dependency_lock_sha256="
            + spinal_generate.sha256_file(self.dependency_lock)
            + "\n",
            encoding="utf-8",
        )
        self.args = argparse.Namespace(
            manifest=self.manifest,
            spinal_dir=self.spinal,
            tool_root=self.tools,
            main_class="miku.compat.GenerateCoreTopCompat",
            expected_module="core_top",
            expected_file="core_top.v",
            out_dir=self.out,
            java_home=None,
            runs=2,
            timeout=10,
        )


class RequestValidationTests(unittest.TestCase):
    def test_rejects_non_repository_main_and_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            for value in (
                "scala.Predef",
                "miku.compat.Generate;show update",
                "miku.compat.Generate\nreload",
                " miku.compat.GenerateCoreTopCompat",
            ):
                with self.subTest(value=value):
                    fixture.args.main_class = value
                    with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "miku"):
                        spinal_generate.validate_request(fixture.args)

    def test_rejects_path_expected_file_and_single_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            fixture.args.expected_file = "../core_top.v"
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "basename"):
                spinal_generate.validate_request(fixture.args)
            fixture.args.expected_file = "core_top.v"
            fixture.args.runs = 1
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "at least 2"):
                spinal_generate.validate_request(fixture.args)

    def test_rejects_repository_rtl_output_and_manifest_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            fixture.args.out_dir = fixture.rtl / "generated"
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "RTL directory"):
                spinal_generate.validate_request(fixture.args)
            if hasattr(os, "symlink"):
                alias = fixture.reference / "manifest-alias.lock"
                try:
                    alias.symlink_to(fixture.manifest)
                except OSError:
                    return
                fixture.args.manifest = alias
                with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "symlink"):
                    spinal_generate.validate_request(fixture.args)

    def test_rejects_output_symlink_and_symlink_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SpinalGenerateFixture(root)
            target = root / "output-target"
            target.mkdir()
            fixture.out.parent.mkdir(parents=True)

            def make_directory_link(link: Path) -> None:
                try:
                    link.symlink_to(target, target_is_directory=True)
                    return
                except OSError as symlink_error:
                    if os.name != "nt":
                        self.fail(f"could not create test symlink: {symlink_error}")
                result = subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                if result.returncode != 0:
                    self.fail(f"could not create test junction: {result.stdout}")

            def remove_directory_link(link: Path) -> None:
                if link.is_symlink():
                    link.unlink()
                else:
                    os.rmdir(link)

            make_directory_link(fixture.out)
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "symlink"):
                spinal_generate.validate_request(fixture.args)

            remove_directory_link(fixture.out)
            ancestor = fixture.repo / "output-link"
            make_directory_link(ancestor)
            fixture.args.out_dir = ancestor / "generated"
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "symlink"):
                spinal_generate.validate_request(fixture.args)
            remove_directory_link(ancestor)

    def test_main_class_must_exist_once_in_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            evidence = spinal_generate.find_main_source(
                fixture.spinal, fixture.args.main_class
            )
            self.assertEqual(
                "src/main/scala/miku/compat/GenerateCoreTopCompat.scala",
                evidence["path"],
            )
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "exactly one"):
                spinal_generate.find_main_source(
                    fixture.spinal, "miku.compat.DoesNotExist"
                )


class OutputPolicyTests(unittest.TestCase):
    def test_warning_and_captured_failure_markers_are_fail_closed(self) -> None:
        self.assertEqual([], spinal_generate.warning_lines("[info] generated\n"))
        self.assertEqual(
            ["%Warning-WIDTH: bad"],
            spinal_generate.warning_lines("%Warning-WIDTH: bad\n"),
        )
        for output in (
            "SKIP: caught exception\n",
            "[error] generation failed\n",
            "Exception in thread main\n",
            "spinal.core.SpinalExit\n",
        ):
            with self.subTest(output=output):
                self.assertTrue(spinal_generate.failure_marker_lines(output))

    def test_only_exact_trusted_java_options_marker_is_accepted(self) -> None:
        options = '-Duser.home="/tmp/home" -Djava.io.tmpdir="/tmp/tmp"'
        marker = f"[error] Picked up JAVA_TOOL_OPTIONS: {options}\n"
        self.assertEqual(
            [],
            spinal_generate.failure_marker_lines(
                marker, trusted_java_tool_options=options
            ),
        )
        self.assertTrue(
            spinal_generate.failure_marker_lines(
                marker, trusted_java_tool_options=options + " -Ddrift=true"
            )
        )

    def test_expected_module_must_be_unique_and_balanced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            generated = Path(temporary)
            rtl = generated / "core_top.v"
            rtl.write_bytes(VALID_RTL)
            evidence = spinal_generate.inspect_generated_rtl(
                generated, "core_top.v", "core_top"
            )
            self.assertEqual(["core_top"], evidence["module_declarations"])
            rtl.write_text(
                "module core_top; endmodule\nmodule core_top; endmodule\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "not unique"):
                spinal_generate.inspect_generated_rtl(generated, "core_top.v", "core_top")

    def test_extra_generated_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            generated = Path(temporary)
            (generated / "core_top.v").write_bytes(VALID_RTL)
            (generated / ".unexpected").write_text("drift\n", encoding="ascii")
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "differ"):
                spinal_generate.inspect_generated_rtl(generated, "core_top.v", "core_top")

    def test_source_snapshot_excludes_target_and_rejects_runner_options(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            target = fixture.spinal / "target/ignored.bin"
            target.parent.mkdir()
            target.write_bytes(b"ignored")
            paths = spinal_generate.source_files(fixture.spinal)
            self.assertNotIn(target, paths)
            (fixture.spinal / ".sbtopts").write_text("-J-Xmx1g\n", encoding="ascii")
            with self.assertRaisesRegex(spinal_generate.SpinalGenerateError, "forbidden"):
                spinal_generate.source_files(fixture.spinal)


class GenerationTests(unittest.TestCase):
    def _run(
        self,
        fixture: SpinalGenerateFixture,
        payloads: list[bytes],
        *,
        outputs: list[str] | None = None,
        extras: bool = False,
        heads: list[str] | None = None,
        dependencies: list[dict[str, object]] | None = None,
        mutate_snapshot: bool = False,
    ) -> tuple[int, dict[str, object]]:
        payload_iter = iter(payloads)
        output_iter = iter(outputs or [""] * fixture.args.runs)

        def fake_environment(values, tool_root, java, runtime):
            del values, tool_root, java
            runtime.mkdir()
            return {"JAVA_TOOL_OPTIONS": "-Dlocked=true"}, []

        def fake_command(argv, *, cwd, timeout, environment=None):
            del cwd, timeout, environment
            match = re.search(r'--out-dir "([^"]+)"$', argv[-1])
            self.assertIsNotNone(match)
            generated = Path(match.group(1))
            (generated / fixture.args.expected_file).write_bytes(next(payload_iter))
            if extras:
                (generated / "unexpected.txt").write_text("extra\n", encoding="ascii")
            return {
                "argv": argv,
                "returncode": 0,
                "stdout": next(output_iter),
                "timed_out": False,
                "elapsed_seconds": 0.001,
            }

        dependency_values = dependencies or [
            {
                "lock_path": str(fixture.dependency_lock),
                "lock_sha256": spinal_generate.sha256_file(fixture.dependency_lock),
                "cache_root": str(fixture.tools / "cache"),
                "artifact_count": 1,
                "artifacts_sha256": "2" * 64,
            }
        ] * 2
        head_values = heads or ["1" * 40, "1" * 40]
        copy_snapshot = spinal_generate.copy_scala_snapshot

        def fake_copy_snapshot(spinal_dir, manifest, dependency_lock, destination):
            isolated = copy_snapshot(spinal_dir, manifest, dependency_lock, destination)
            if mutate_snapshot:
                source = (
                    isolated[0]
                    / "src/main/scala/miku/compat/GenerateCoreTopCompat.scala"
                )
                source.write_text(
                    source.read_text(encoding="utf-8") + "// isolated drift\n",
                    encoding="utf-8",
                )
            return isolated

        with mock.patch.object(
            spinal_generate,
            "load_scala_gate",
            return_value=(object(), {"path": "scala_gate.py", "sha256": "3" * 64}),
        ), mock.patch.object(
            spinal_generate,
            "verify_scala_dependencies",
            side_effect=dependency_values,
        ), mock.patch.object(
            spinal_generate,
            "locked_tools",
            return_value=(
                fixture.java,
                fixture.sbt,
                {
                    "java": str(fixture.java),
                    "java_sha256": spinal_generate.sha256_file(fixture.java),
                    "jdk": "17.0.19+10",
                    "sbt": "1.10.11",
                    "sbt_launcher": str(fixture.sbt),
                    "sbt_launcher_sha256": spinal_generate.sha256_file(fixture.sbt),
                },
            ),
        ), mock.patch.object(
            spinal_generate, "generation_environment", side_effect=fake_environment
        ), mock.patch.object(
            spinal_generate, "run_command", side_effect=fake_command
        ), mock.patch.object(
            spinal_generate, "git_output", side_effect=head_values
        ), mock.patch.object(
            spinal_generate, "copy_scala_snapshot", side_effect=fake_copy_snapshot
        ):
            with redirect_stdout(io.StringIO()):
                code = spinal_generate.generate(fixture.args)
        summary = json.loads((fixture.out / "summary.json").read_text(encoding="utf-8"))
        return code, summary

    def test_identical_runs_publish_exact_rtl_with_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            code, summary = self._run(fixture, [VALID_RTL, VALID_RTL])
            published = fixture.out / "rtl/core_top.v"
            self.assertEqual(VALID_RTL, published.read_bytes())
        self.assertEqual(0, code)
        self.assertEqual("pass", summary["status"])
        self.assertTrue(summary["reproducible"])
        self.assertTrue(summary["stable_inputs"])
        self.assertEqual(2, summary["counts"]["executed"])
        self.assertEqual(0, summary["counts"]["skipped"])
        self.assertEqual("1" * 40, summary["repo_head_sha"])
        self.assertIn("evaluator_sha256", summary)
        self.assertIn("toolchain", summary)

    def test_byte_drift_fails_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            code, summary = self._run(
                fixture,
                [VALID_RTL, b"module core_top(input wire reset);\nendmodule\n"],
            )
            self.assertFalse((fixture.out / "rtl/core_top.v").exists())
        self.assertEqual(1, code)
        self.assertFalse(summary["reproducible"])

    def test_warning_skip_wrong_module_and_extra_file_never_publish(self) -> None:
        cases = (
            ("warning", [VALID_RTL, VALID_RTL], ["[warn] bad\n", ""], False),
            ("skip", [VALID_RTL, VALID_RTL], ["SKIP: swallowed exception\n", ""], False),
            (
                "wrong-module",
                [b"module not_core_top; endmodule\n"] * 2,
                ["", ""],
                False,
            ),
            ("extra-file", [VALID_RTL, VALID_RTL], ["", ""], True),
        )
        for name, payloads, outputs, extras in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                fixture = SpinalGenerateFixture(Path(temporary))
                code, summary = self._run(
                    fixture, payloads, outputs=outputs, extras=extras
                )
                self.assertEqual(1, code)
                self.assertEqual("fail", summary["status"])
                self.assertFalse((fixture.out / "rtl/core_top.v").exists())

    def test_head_or_dependency_drift_fails_identical_rtl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            dependency = {
                "lock_path": str(fixture.dependency_lock),
                "lock_sha256": spinal_generate.sha256_file(fixture.dependency_lock),
                "cache_root": str(fixture.tools / "cache"),
                "artifact_count": 1,
                "artifacts_sha256": "2" * 64,
            }
            drifted = {**dependency, "artifacts_sha256": "4" * 64}
            code, summary = self._run(
                fixture,
                [VALID_RTL, VALID_RTL],
                heads=["1" * 40, "5" * 40],
                dependencies=[dependency, drifted],
            )
            self.assertFalse((fixture.out / "rtl/core_top.v").exists())
        self.assertEqual(1, code)
        self.assertTrue(summary["reproducible"])
        self.assertFalse(summary["stable_inputs"])

    def test_isolated_snapshot_drift_fails_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SpinalGenerateFixture(Path(temporary))
            code, summary = self._run(
                fixture,
                [VALID_RTL, VALID_RTL],
                mutate_snapshot=True,
            )
            self.assertFalse((fixture.out / "rtl/core_top.v").exists())
        self.assertEqual(1, code)
        self.assertTrue(summary["reproducible"])
        self.assertFalse(summary["isolated_snapshots_match_source"])
        self.assertFalse(summary["stable_inputs"])
        self.assertTrue(
            all(not run["snapshot_matches_source"] for run in summary["runs"])
        )


class ProcessTests(unittest.TestCase):
    def test_run_command_executes_a_real_process(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = spinal_generate.run_command(
                [sys.executable, "-c", "print('real-process-ok')"],
                cwd=Path(temporary),
                timeout=10,
            )
        self.assertEqual(0, result["returncode"])
        self.assertEqual("real-process-ok", str(result["stdout"]).strip())

    def test_cli_requires_isolated_python(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(spinal_generate.__file__))],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("requires isolated Python", result.stderr)


if __name__ == "__main__":
    unittest.main()
