from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import mul_gate


class MulGateContractTests(unittest.TestCase):
    def test_contract_has_exact_six_ports(self) -> None:
        self.assertEqual(
            {
                "mul_clk": ("input", 1),
                "reset": ("input", 1),
                "mul_signed": ("input", 1),
                "x": ("input", 32),
                "y": ("input", 32),
                "result": ("output", 64),
            },
            mul_gate.MUL_PORTS,
        )
        self.assertEqual("miku.execute.GenerateOpenLa500Mul", mul_gate.GENERATOR_MAIN)

    def test_warning_parser_is_fail_closed(self) -> None:
        self.assertEqual([], mul_gate.warning_lines("all clean\n"))
        self.assertEqual(["%Warning-WIDTH: bad"], mul_gate.warning_lines("%Warning-WIDTH: bad\n"))
        self.assertEqual(["[warn] bad"], mul_gate.warning_lines("[warn] bad\n"))

    def test_output_under_repository_rtl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "rtl").mkdir()
            with self.assertRaises(mul_gate.MulGateError):
                mul_gate.ensure_outside_repo_rtl(repo / "rtl" / "generated", repo)
            mul_gate.ensure_outside_repo_rtl(repo / "build" / "generated", repo)

    def test_duplicate_manifest_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.lock"
            path.write_text("sbt=one\nsbt=two\n", encoding="utf-8")
            with self.assertRaises(mul_gate.MulGateError):
                mul_gate.parse_lock(path)

    def test_unsupported_target_returns_nonzero(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "mul_gate.py",
                "lint",
                "--target",
                "alu",
                "--manifest",
                "missing.lock",
                "--rtl",
                "missing.v",
                "--out-dir",
                "out",
            ],
        ):
            self.assertEqual(2, mul_gate.main())


class MulGenerationTests(unittest.TestCase):
    def _fixture(self, root: Path) -> SimpleNamespace:
        spinal = root / "spinal"
        for relative in (
            ".scalafmt.conf",
            "build.sbt",
            "project/build.properties",
            "project/plugins.sbt",
            "src/main/scala/miku/execute/OpenLa500Mul.scala",
        ):
            path = spinal / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(relative + "\n", encoding="utf-8")
        manifest = root / "reference" / "manifest.lock"
        manifest.parent.mkdir()
        fake_java = root / "java"
        fake_java.write_bytes(b"locked-java")
        manifest.write_text(
            "scala_cache_dir=cache\n"
            "scala_dependency_lock_sha256=" + "1" * 64 + "\n"
            "sbt=1.10.11\n"
            "sbt_launch_jar_sha256=" + "0" * 64 + "\n"
            "java_binary_sha256=" + mul_gate.sha256_file(fake_java) + "\n",
            encoding="utf-8",
        )
        fake_sbt = root / "sbt-launch.jar"
        fake_sbt.write_bytes(b"sbt")
        return SimpleNamespace(
            manifest=manifest,
            spinal_dir=spinal,
            tool_root=root / "tools",
            java_home=None,
            out_dir=root / "out",
            timeout=10,
            fake_java=fake_java,
            fake_sbt=fake_sbt,
        )

    def _run(self, root: Path, payloads: list[bytes]) -> tuple[int, dict[str, object]]:
        args = self._fixture(root)
        calls = iter(payloads)

        def fake_environment(values, tool_root, java, runtime):
            del values, tool_root, java
            runtime.mkdir()
            return {}, []

        def fake_command(argv, *, cwd, timeout, environment=None):
            del cwd, timeout, environment
            generated = Path(argv[-1].rsplit("--out-dir ", 1)[1])
            generated.mkdir(parents=True, exist_ok=True)
            (generated / "mul.v").write_bytes(next(calls))
            return {
                "argv": argv,
                "returncode": 0,
                "stdout": "",
                "timed_out": False,
                "elapsed_seconds": 0.001,
            }

        with mock.patch.object(
            mul_gate, "tool_root_sbt_jar", return_value=args.fake_sbt
        ), mock.patch.object(
            mul_gate, "resolve_executable", return_value=args.fake_java
        ), mock.patch.object(
            mul_gate, "generation_environment", side_effect=fake_environment
        ), mock.patch.object(
            mul_gate, "run_command", side_effect=fake_command
        ), mock.patch.object(
            mul_gate, "git_output", return_value="1" * 40
        ), mock.patch.object(
            mul_gate,
            "verify_scala_dependencies",
            return_value={"artifact_count": 1, "artifacts_sha256": "2" * 64},
        ):
            code = mul_gate.generate(args, runs=2, gate_name="generate")
        summary = json.loads((args.out_dir / "summary.json").read_text(encoding="utf-8"))
        return code, summary

    def test_identical_runs_are_published(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code, summary = self._run(root, [b"module mul; endmodule\n"] * 2)
            published = root / "out" / "rtl" / "mul.v"
            self.assertTrue(published.is_file())
        self.assertEqual(0, code)
        self.assertEqual("pass", summary["status"])
        self.assertTrue(summary["reproducible"])

    def test_byte_drift_fails_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code, summary = self._run(
                root, [b"module mul; endmodule\n", b"module mul; wire drift; endmodule\n"]
            )
            self.assertFalse((root / "out" / "rtl" / "mul.v").exists())
        self.assertEqual(1, code)
        self.assertEqual("fail", summary["status"])
        self.assertFalse(summary["reproducible"])

    def test_dependency_lock_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "reference" / "manifest.lock"
            manifest.parent.mkdir()
            manifest.write_text("", encoding="utf-8")
            (manifest.parent / mul_gate.SCALA_DEPENDENCY_LOCK).write_text("{}\n", encoding="utf-8")
            values = {
                "scala_cache_dir": "cache",
                "scala_dependency_lock_sha256": "0" * 64,
            }
            with self.assertRaisesRegex(mul_gate.MulGateError, "lock hash differs"):
                mul_gate.verify_scala_dependencies(manifest, root / "tools", values)


class MulPortCheckTests(unittest.TestCase):
    def _args(self, root: Path) -> SimpleNamespace:
        rtl = root / "mul.v"
        rtl.write_text("module mul; endmodule\n", encoding="utf-8")
        manifest = root / "manifest.lock"
        manifest.write_text("yosys_binary_sha256=" + "0" * 64 + "\n", encoding="utf-8")
        return SimpleNamespace(out_dir=root / "out", rtl=rtl, manifest=manifest, timeout=10)

    def test_exact_yosys_port_projection_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = self._args(root)

            def fake_run(values, script, out_dir, timeout):
                del values, script, timeout
                document = {
                    "modules": {
                        "mul": {
                            "ports": {
                                name: {"direction": direction, "bits": list(range(width))}
                                for name, (direction, width) in mul_gate.MUL_PORTS.items()
                            }
                        }
                    }
                }
                (out_dir / "mul.json").write_text(json.dumps(document), encoding="utf-8")
                log = out_dir / "yosys.log"
                log.write_text("clean\n", encoding="utf-8")
                return {"returncode": 0, "warnings": [], "stdout": "", "timed_out": False}, log

            with mock.patch.object(
                mul_gate, "run_yosys_script", side_effect=fake_run
            ), mock.patch.object(
                mul_gate,
                "gate_provenance",
                return_value={"repository_head": "1" * 40},
            ):
                self.assertEqual(0, mul_gate.port_check(args))

    def test_extra_clock_port_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = self._args(root)

            def fake_run(values, script, out_dir, timeout):
                del values, script, timeout
                ports = {
                    name: {"direction": direction, "bits": list(range(width))}
                    for name, (direction, width) in mul_gate.MUL_PORTS.items()
                }
                ports["clk"] = {"direction": "input", "bits": [0]}
                (out_dir / "mul.json").write_text(
                    json.dumps({"modules": {"mul": {"ports": ports}}}), encoding="utf-8"
                )
                log = out_dir / "yosys.log"
                log.write_text("clean\n", encoding="utf-8")
                return {"returncode": 0, "warnings": [], "stdout": "", "timed_out": False}, log

            with mock.patch.object(
                mul_gate, "run_yosys_script", side_effect=fake_run
            ), mock.patch.object(
                mul_gate,
                "gate_provenance",
                return_value={"repository_head": "1" * 40},
            ):
                self.assertEqual(1, mul_gate.port_check(args))


class MulGateCliTests(unittest.TestCase):
    def test_formal_harness_masks_only_the_pre_capture_state(self) -> None:
        harness = mul_gate.formal_harness("mul_contract_formal", "result")
        self.assertIn("initial seen = 1'b0;", harness)
        self.assertIn("if (!reset)", harness)
        self.assertIn("if (seen)", harness)
        self.assertNotIn("initial expected", harness)

    def test_formal_result_classifiers_are_fail_closed(self) -> None:
        positive = {"returncode": 0, "timed_out": False, "warnings": []}
        positive_log = mul_gate.FORMAL_PASS_BASE + "\n" + mul_gate.FORMAL_PASS_INDUCTION
        self.assertTrue(mul_gate.formal_positive_passed(positive, positive_log))
        self.assertFalse(mul_gate.formal_positive_passed(positive, mul_gate.FORMAL_PASS_BASE))
        self.assertFalse(
            mul_gate.formal_positive_passed({**positive, "warnings": ["Warning: bad"]}, positive_log)
        )

        negative = {"returncode": 1, "timed_out": False, "warnings": []}
        self.assertTrue(
            mul_gate.formal_negative_detected(negative, mul_gate.FORMAL_EXPECTED_FAILURE)
        )
        self.assertFalse(mul_gate.formal_negative_detected(negative, "generic tool failure"))
        self.assertFalse(
            mul_gate.formal_negative_detected(
                {**negative, "timed_out": True}, mul_gate.FORMAL_EXPECTED_FAILURE
            )
        )

    def test_timeout_kills_command_and_returns_124(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = mul_gate.run_command(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                cwd=Path(temporary),
                timeout=1,
            )
        self.assertEqual(124, result["returncode"])
        self.assertTrue(result["timed_out"])

    def test_single_gate_output_path_must_be_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "summary.json"
            output.write_text("{}\n", encoding="utf-8")
            rtl = root / "mul.v"
            rtl.write_text("module mul; endmodule\n", encoding="utf-8")
            manifest = root / "manifest.lock"
            manifest.write_text("yosys_binary_sha256=" + "0" * 64 + "\n", encoding="utf-8")
            args = SimpleNamespace(out_dir=output, rtl=rtl, manifest=manifest)
            with self.assertRaisesRegex(mul_gate.MulGateError, "must be a directory"):
                mul_gate.prepare_single_gate(args, "lint")

    def test_single_gate_snapshot_detects_source_and_snapshot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rtl = root / "mul.v"
            rtl.write_text("module mul; endmodule\n", encoding="ascii")
            manifest = root / "manifest.lock"
            manifest.write_text("", encoding="ascii")
            args = SimpleNamespace(out_dir=root / "out", rtl=rtl, manifest=manifest)
            _, snapshot, _, identity = mul_gate.prepare_single_gate(args, "formal")
            self.assertTrue(mul_gate.gate_input_evidence(identity)["source_stable"])
            rtl.write_text("module mul; wire drift; endmodule\n", encoding="ascii")
            self.assertFalse(mul_gate.gate_input_evidence(identity)["source_stable"])
            snapshot.write_text("module mul; wire drift; endmodule\n", encoding="ascii")
            self.assertFalse(mul_gate.gate_input_evidence(identity)["snapshot_stable"])

    def test_cli_requires_isolated_python(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(mul_gate.__file__)), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("requires isolated Python", result.stderr)


if __name__ == "__main__":
    unittest.main()
