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
from tools import div_gate


class DivGateContractTests(unittest.TestCase):
    def test_contract_has_exact_nine_ports(self) -> None:
        self.assertEqual(
            {
                "div_clk": ("input", 1),
                "reset": ("input", 1),
                "div": ("input", 1),
                "div_signed": ("input", 1),
                "x": ("input", 32),
                "y": ("input", 32),
                "s": ("output", 32),
                "r": ("output", 32),
                "complete": ("output", 1),
            },
            div_gate.DIV_PORTS,
        )
        self.assertEqual("miku.execute.GenerateOpenLa500Div", div_gate.GENERATOR_MAIN)

    def test_warning_parser_is_fail_closed(self) -> None:
        self.assertEqual([], div_gate.warning_lines("all clean\n"))
        self.assertEqual(["%Warning-WIDTH: bad"], div_gate.warning_lines("%Warning-WIDTH: bad\n"))
        self.assertEqual(["[warn] bad"], div_gate.warning_lines("[warn] bad\n"))

    def test_verilator_normalization_changes_only_the_module_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "div.v"
            source.write_text(
                "module div (input wire div, output wire complete);\n"
                "assign complete = div;\nendmodule\n",
                encoding="ascii",
            )
            (root / "out" / "input").mkdir(parents=True)
            normalized, evidence = div_gate.normalize_verilator_module(source, root / "out")
            payload = normalized.read_text(encoding="ascii")
        self.assertIn("module div_lint (", payload)
        self.assertIn("input wire div", payload)
        self.assertEqual(1, evidence["replacement_count"])
        self.assertNotEqual(evidence["source_sha256"], evidence["normalized_sha256"])

    def test_verilator_normalization_rejects_ambiguous_module_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "div.v"
            source.write_text("module div(); endmodule\nmodule div(); endmodule\n", encoding="ascii")
            (root / "out" / "input").mkdir(parents=True)
            with self.assertRaisesRegex(div_gate.DivGateError, "not unique"):
                div_gate.normalize_verilator_module(source, root / "out")

    def test_output_under_repository_rtl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "rtl").mkdir()
            with self.assertRaises(div_gate.DivGateError):
                div_gate.ensure_outside_repo_rtl(repo / "rtl" / "generated", repo)
            div_gate.ensure_outside_repo_rtl(repo / "build" / "generated", repo)

    def test_duplicate_manifest_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.lock"
            path.write_text("sbt=one\nsbt=two\n", encoding="utf-8")
            with self.assertRaises(div_gate.DivGateError):
                div_gate.parse_lock(path)

    def test_unsupported_target_returns_nonzero(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "div_gate.py",
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
            self.assertEqual(2, div_gate.main())


class DivGenerationTests(unittest.TestCase):
    def _fixture(self, root: Path) -> SimpleNamespace:
        spinal = root / "spinal"
        for relative in (
            ".scalafmt.conf",
            "build.sbt",
            "project/build.properties",
            "project/plugins.sbt",
            "src/main/scala/miku/execute/OpenLa500Div.scala",
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
            "java_binary_sha256=" + div_gate.sha256_file(fake_java) + "\n",
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
            (generated / "div.v").write_bytes(next(calls))
            return {
                "argv": argv,
                "returncode": 0,
                "stdout": "",
                "timed_out": False,
                "elapsed_seconds": 0.001,
            }

        with mock.patch.object(
            div_gate, "tool_root_sbt_jar", return_value=args.fake_sbt
        ), mock.patch.object(
            div_gate, "resolve_executable", return_value=args.fake_java
        ), mock.patch.object(
            div_gate, "generation_environment", side_effect=fake_environment
        ), mock.patch.object(
            div_gate, "run_command", side_effect=fake_command
        ), mock.patch.object(
            div_gate, "git_output", return_value="1" * 40
        ), mock.patch.object(
            div_gate,
            "verify_scala_dependencies",
            return_value={"artifact_count": 1, "artifacts_sha256": "2" * 64},
        ):
            code = div_gate.generate(args, runs=2, gate_name="generate")
        summary = json.loads((args.out_dir / "summary.json").read_text(encoding="utf-8"))
        return code, summary

    def test_identical_runs_are_published(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code, summary = self._run(root, [b"module div; endmodule\n"] * 2)
            published = root / "out" / "rtl" / "div.v"
            self.assertTrue(published.is_file())
        self.assertEqual(0, code)
        self.assertEqual("pass", summary["status"])
        self.assertTrue(summary["reproducible"])

    def test_byte_drift_fails_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code, summary = self._run(
                root, [b"module div; endmodule\n", b"module div; wire drift; endmodule\n"]
            )
            self.assertFalse((root / "out" / "rtl" / "div.v").exists())
        self.assertEqual(1, code)
        self.assertEqual("fail", summary["status"])
        self.assertFalse(summary["reproducible"])

    def test_dependency_lock_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "reference" / "manifest.lock"
            manifest.parent.mkdir()
            manifest.write_text("", encoding="utf-8")
            (manifest.parent / div_gate.SCALA_DEPENDENCY_LOCK).write_text("{}\n", encoding="utf-8")
            values = {
                "scala_cache_dir": "cache",
                "scala_dependency_lock_sha256": "0" * 64,
            }
            with self.assertRaisesRegex(div_gate.DivGateError, "lock hash differs"):
                div_gate.verify_scala_dependencies(manifest, root / "tools", values)


class DivPortCheckTests(unittest.TestCase):
    def _args(self, root: Path) -> SimpleNamespace:
        rtl = root / "div.v"
        rtl.write_text("module div; endmodule\n", encoding="utf-8")
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
                        "div": {
                            "ports": {
                                name: {"direction": direction, "bits": list(range(width))}
                                for name, (direction, width) in div_gate.DIV_PORTS.items()
                            }
                        }
                    }
                }
                (out_dir / "div.json").write_text(json.dumps(document), encoding="utf-8")
                log = out_dir / "yosys.log"
                log.write_text("clean\n", encoding="utf-8")
                return {"returncode": 0, "warnings": [], "stdout": "", "timed_out": False}, log

            with mock.patch.object(
                div_gate, "run_yosys_script", side_effect=fake_run
            ), mock.patch.object(
                div_gate,
                "gate_provenance",
                return_value={"repository_head": "1" * 40},
            ):
                self.assertEqual(0, div_gate.port_check(args))

    def test_extra_clock_port_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = self._args(root)

            def fake_run(values, script, out_dir, timeout):
                del values, script, timeout
                ports = {
                    name: {"direction": direction, "bits": list(range(width))}
                    for name, (direction, width) in div_gate.DIV_PORTS.items()
                }
                ports["clk"] = {"direction": "input", "bits": [0]}
                (out_dir / "div.json").write_text(
                    json.dumps({"modules": {"div": {"ports": ports}}}), encoding="utf-8"
                )
                log = out_dir / "yosys.log"
                log.write_text("clean\n", encoding="utf-8")
                return {"returncode": 0, "warnings": [], "stdout": "", "timed_out": False}, log

            with mock.patch.object(
                div_gate, "run_yosys_script", side_effect=fake_run
            ), mock.patch.object(
                div_gate,
                "gate_provenance",
                return_value={"repository_head": "1" * 40},
            ):
                self.assertEqual(1, div_gate.port_check(args))


class DivGateCliTests(unittest.TestCase):
    def test_formal_harness_models_locked_pulse_and_cleanup_order(self) -> None:
        harness = div_gate.formal_harness("div_protocol_formal", "none")
        self.assertIn(".div(div)", harness)
        self.assertIn("phase == 6'd33", harness)
        self.assertIn("phase == 6'd35", harness)
        self.assertIn("if (phase == 6'd34)", harness)
        self.assertNotIn("model_product", harness)

    def test_formal_negative_controls_mutate_distinct_protocol_edges(self) -> None:
        early = div_gate.formal_harness("div_protocol_negative_early", "pulse_one_edge_early")
        cleanup = div_gate.formal_harness(
            "div_protocol_negative_cleanup", "cleanup_one_edge_short"
        )
        self.assertIn("phase == 6'd32", early)
        self.assertIn("phase == 6'd35", early)
        self.assertIn("phase == 6'd33", cleanup)
        self.assertIn("phase == 6'd34", cleanup)
        with self.assertRaisesRegex(div_gate.DivGateError, "unsupported formal"):
            div_gate.formal_harness("div_protocol_bad", "always_pass")

    def test_formal_result_classifiers_are_fail_closed(self) -> None:
        positive = {"returncode": 0, "timed_out": False, "warnings": []}
        positive_log = div_gate.FORMAL_PASS_BASE + "\n" + div_gate.FORMAL_PASS_INDUCTION
        self.assertTrue(div_gate.formal_positive_passed(positive, positive_log))
        self.assertFalse(div_gate.formal_positive_passed(positive, div_gate.FORMAL_PASS_BASE))
        self.assertFalse(
            div_gate.formal_positive_passed({**positive, "warnings": ["Warning: bad"]}, positive_log)
        )

        negative = {"returncode": 1, "timed_out": False, "warnings": []}
        self.assertTrue(
            div_gate.formal_negative_detected(
                negative,
                div_gate.FORMAL_COUNTEREXAMPLE + "\n" + div_gate.FORMAL_EXPECTED_FAILURE,
            )
        )
        self.assertFalse(div_gate.formal_negative_detected(negative, "generic tool failure"))
        self.assertFalse(
            div_gate.formal_negative_detected(
                negative,
                div_gate.FORMAL_COUNTEREXAMPLE
                + "\n"
                + div_gate.FORMAL_EXPECTED_FAILURE
                + "\nERROR: unrelated tool failure",
            )
        )
        self.assertFalse(
            div_gate.formal_negative_detected(
                {**negative, "timed_out": True},
                div_gate.FORMAL_COUNTEREXAMPLE + "\n" + div_gate.FORMAL_EXPECTED_FAILURE,
            )
        )

    def test_timeout_kills_command_and_returns_124(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = div_gate.run_command(
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
            rtl = root / "div.v"
            rtl.write_text("module div; endmodule\n", encoding="utf-8")
            manifest = root / "manifest.lock"
            manifest.write_text("yosys_binary_sha256=" + "0" * 64 + "\n", encoding="utf-8")
            args = SimpleNamespace(out_dir=output, rtl=rtl, manifest=manifest)
            with self.assertRaisesRegex(div_gate.DivGateError, "must be a directory"):
                div_gate.prepare_single_gate(args, "lint")

    def test_single_gate_snapshot_detects_source_and_snapshot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rtl = root / "div.v"
            rtl.write_text("module div; endmodule\n", encoding="ascii")
            manifest = root / "manifest.lock"
            manifest.write_text("", encoding="ascii")
            args = SimpleNamespace(out_dir=root / "out", rtl=rtl, manifest=manifest)
            _, snapshot, _, identity = div_gate.prepare_single_gate(args, "formal")
            self.assertTrue(div_gate.gate_input_evidence(identity)["source_stable"])
            rtl.write_text("module div; wire drift; endmodule\n", encoding="ascii")
            self.assertFalse(div_gate.gate_input_evidence(identity)["source_stable"])
            snapshot.write_text("module div; wire drift; endmodule\n", encoding="ascii")
            self.assertFalse(div_gate.gate_input_evidence(identity)["snapshot_stable"])

    def test_cli_requires_isolated_python(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(div_gate.__file__)), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("requires isolated Python", result.stderr)


if __name__ == "__main__":
    unittest.main()
