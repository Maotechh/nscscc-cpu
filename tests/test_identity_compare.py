from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import identity_compare, refactor


class IdentityCompareTests(unittest.TestCase):
    LOCKED_ID = "20260711-identity-locked"
    MIXED_ID = "20260711-identity-mixed"
    FILE_SHA = "1" * 64
    ELF_SHA = "2" * 64
    ROM_SHA = "3" * 64
    TRACE_SHA = "4" * 64
    UART_SHA = "5" * 64
    TOOL_SHA = "6" * 64
    DOCTOR_SHA = "7" * 64
    EVALUATOR_SHA = "8" * 64

    def test_isolated_cli_can_load_sibling_refactor_module(self) -> None:
        script = Path(__file__).resolve().parents[1] / "tools" / "identity_compare.py"
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [sys.executable, "-I", str(script), "--help"],
                cwd=temporary,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr)

    def _write(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        refactor.write_json(path, value)

    def _paths(self, out_dir: Path, iteration_id: str) -> dict[str, Path]:
        return identity_compare._canonical_paths(out_dir, iteration_id)

    def _output(self, out_dir: Path) -> Path:
        return self._paths(out_dir, self.MIXED_ID)["smoke"].parent / "identity-comparison.json"

    def _manifest(
        self, iteration_id: str, *, mixed: bool, identity: bool = True
    ) -> dict[str, object]:
        replacement_sha = self.FILE_SHA if identity else "9" * 64
        replacement = {
            "schema_version": 1,
            "source_head": "a" * 40,
            "source_branch": "refactor/identity-test",
            "spec_path": "tests/fixtures/component-overlay/identity.json",
            "replacements": [
                {
                    "target": "rtl/alu.v",
                    "source": "tests/fixtures/component-overlay/alu.v",
                    "base_sha256": self.FILE_SHA,
                    "replacement_sha256": replacement_sha,
                    "size": 16,
                }
            ],
        }
        return {
            "schema_version": 1,
            "iteration_id": iteration_id,
            "dut_source": "mixed" if mixed else "candidate",
            "provenance_mode": "mixed_candidate" if mixed else "locked_candidate",
            "gate_kind": "component_replacement" if mixed else "baseline_candidate",
            "mode": "diagnostic" if mixed else "baseline",
            "candidate_locked": not mixed,
            "base_candidate_locked": True,
            "baseline_exact": not mixed,
            "gate_eligible": not mixed,
            "selection_sha256": ("b" if mixed else "c") * 64,
            "golden_candidate_commit": "d" * 40,
            "component_replacement": replacement if mixed else None,
            "chiplab_commit": "e" * 40,
            "chiplab_tree": "f" * 40,
            "mycpu_reference_commit": "0" * 40,
            "golden_files_lock_sha256": "a" * 64,
            "doctor_report_sha256": self.DOCTOR_SHA,
            "evaluator_sha256": self.EVALUATOR_SHA,
            "official_workspace_fingerprint": {"entry_count": 2, "sha256": "b" * 64},
            "tool_links": [{"path": "tool", "target": "/locked/tool"}],
            "tool_fingerprints": [
                {
                    "name": "verilator",
                    "manifest_key": "verilator_binary_sha256",
                    "actual_sha256": self.TOOL_SHA,
                    "expected_sha256": self.TOOL_SHA,
                    "size": 10,
                    "path": "/locked/verilator",
                }
            ],
            "support_files": [
                {
                    "path": "IP/myCPU/mycpu.h",
                    "source": "upstream:mycpu.h",
                    "sha256": "c" * 64,
                    "size": 32,
                }
            ],
            "files": [
                {
                    "logical_path": "rtl/alu.v",
                    "path": "alu.v",
                    "overlay_path": "IP/myCPU/alu.v",
                    "sha256": self.FILE_SHA,
                    "overlay_sha256": self.FILE_SHA,
                    "size": 16,
                    "base_mode": "100644",
                    "source_kind": "replacement" if mixed else "golden",
                }
            ],
        }

    def _overlay(self, manifest: dict[str, object], manifest_sha: str) -> dict[str, object]:
        return {
            key: manifest[key]
            for key in (
                "iteration_id",
                "dut_source",
                "provenance_mode",
                "gate_kind",
                "mode",
                "candidate_locked",
                "base_candidate_locked",
                "baseline_exact",
                "gate_eligible",
                "selection_sha256",
                "golden_candidate_commit",
                "component_replacement",
            )
        } | {"overlay_manifest_sha256": manifest_sha}

    def _smoke(
        self,
        overlay: dict[str, object],
        overlay_sha: str,
        manifest_sha: str,
        *,
        binary_sha: str,
    ) -> dict[str, object]:
        selection = overlay["selection_sha256"]
        return {
            "schema_version": 1,
            **{
                key: overlay[key]
                for key in (
                    "iteration_id",
                    "dut_source",
                    "provenance_mode",
                    "gate_kind",
                    "candidate_locked",
                    "base_candidate_locked",
                    "baseline_exact",
                    "gate_eligible",
                    "golden_candidate_commit",
                    "component_replacement",
                )
            },
            "selection_sha256": selection,
            "overlay_report_sha256": overlay_sha,
            "post_run_dut_verification": {
                "status": "pass",
                "selection_sha256": selection,
                "overlay_report_sha256": overlay_sha,
                "overlay_manifest_sha256": manifest_sha,
            },
            "requested_case": "func/func_lab19",
            "actual_case": "func/func_lab19",
            "commands": [
                {
                    "command": ["make", "simulation_run_prog"],
                    "cwd": "/different/cwd",
                    "exit_code": 0,
                    "timed_out": False,
                    "elapsed_seconds": 1.0,
                }
            ],
            "counts": {"planned": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0},
            "functional_counts": {
                "planned": 1,
                "executed": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
            },
            "verilator_compile_counts": {
                "planned": 1,
                "executed": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
            },
            "gate_result": "fail",
            "functional_status": "fail",
            "parser": {
                "status": "fail",
                "instructions": 12,
                "clocks": 34,
                "failures": ["difftest_mismatch"],
                "first_mismatch": "register differs",
            },
            "verilator_warnings": [
                {"scope": "dut", "category": "WIDTH", "line": "path differs"},
                {"scope": "dut", "category": "UNDRIVEN", "line": "path differs"},
                {"scope": "official_environment", "category": "WIDTH", "line": "path differs"},
                {"scope": "official_environment", "category": "WIDTH", "line": "path differs"},
                {
                    "scope": "official_environment",
                    "category": "UNOPTFLAT",
                    "line": "path differs",
                },
            ],
            "output_evidence": {
                "simu_trace": {
                    "exists": True,
                    "fresh": True,
                    "oracle_role": "trace_artifact",
                    "path": "/different/simu_trace.txt",
                    "sha256": self.TRACE_SHA,
                    "size": 100,
                },
                "uart": {
                    "exists": True,
                    "fresh": True,
                    "oracle_role": "not_applicable_for_func_lab19",
                    "path": "/different/uart_output.txt",
                    "sha256": self.UART_SHA,
                    "size": 0,
                },
                "uart_real": {
                    "exists": True,
                    "fresh": True,
                    "oracle_role": "not_applicable_for_func_lab19",
                    "path": "/different/uart_output.txt.real",
                    "sha256": self.UART_SHA,
                    "size": 0,
                },
            },
            "artifacts": [
                {"path": "/different/main.elf", "sha256": self.ELF_SHA, "size": 10},
                {"path": "/different/rom.vlog", "sha256": self.ROM_SHA, "size": 20},
                {"path": "/different/output", "sha256": binary_sha, "size": 30},
            ],
        }

    def _fixture(self, root: Path, *, identity: bool = True) -> Path:
        out_dir = root / "out"
        locked_paths = self._paths(out_dir, self.LOCKED_ID)
        mixed_paths = self._paths(out_dir, self.MIXED_ID)
        locked_manifest = self._manifest(self.LOCKED_ID, mixed=False)
        mixed_manifest = self._manifest(self.MIXED_ID, mixed=True, identity=identity)
        self._write(locked_paths["manifest"], locked_manifest)
        self._write(mixed_paths["manifest"], mixed_manifest)
        locked_manifest_sha = refactor.sha256_file(locked_paths["manifest"])
        mixed_manifest_sha = refactor.sha256_file(mixed_paths["manifest"])
        locked_overlay = self._overlay(locked_manifest, locked_manifest_sha)
        mixed_overlay = self._overlay(mixed_manifest, mixed_manifest_sha)
        self._write(locked_paths["overlay"], locked_overlay)
        self._write(mixed_paths["overlay"], mixed_overlay)
        locked_overlay_sha = refactor.sha256_file(locked_paths["overlay"])
        mixed_overlay_sha = refactor.sha256_file(mixed_paths["overlay"])
        self._write(
            locked_paths["smoke"],
            self._smoke(
                locked_overlay,
                locked_overlay_sha,
                locked_manifest_sha,
                binary_sha="d" * 64,
            ),
        )
        self._write(
            mixed_paths["smoke"],
            self._smoke(
                mixed_overlay,
                mixed_overlay_sha,
                mixed_manifest_sha,
                binary_sha="e" * 64,
            ),
        )
        return out_dir

    def _run(self, out_dir: Path, *extra: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            return identity_compare.main(
                [
                    "--out-dir",
                    str(out_dir),
                    "--locked-iteration-id",
                    self.LOCKED_ID,
                    "--mixed-iteration-id",
                    self.MIXED_ID,
                    *extra,
                ]
            )

    def test_identity_comparison_accepts_equal_failure_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = self._fixture(Path(temporary))
            self.assertEqual(0, self._run(out_dir))
            report = json.loads(self._output(out_dir).read_text(encoding="utf-8"))
            self.assertEqual("pass", report["status"])
            self.assertFalse(report["gate_eligible"])
            self.assertEqual("fail", report["observed"]["functional_status"])
            self.assertIn("simulator output binary", report["excluded_fields"])

    def test_parser_drift_writes_failure_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = self._fixture(Path(temporary))
            mixed_smoke_path = self._paths(out_dir, self.MIXED_ID)["smoke"]
            mixed_smoke = json.loads(mixed_smoke_path.read_text(encoding="utf-8"))
            mixed_smoke["parser"]["instructions"] = 99
            self._write(mixed_smoke_path, mixed_smoke)
            self.assertEqual(1, self._run(out_dir))
            report = json.loads(self._output(out_dir).read_text(encoding="utf-8"))
            self.assertEqual("fail", report["status"])
            self.assertIn("locked and mixed smoke reports differ on parser", report["mismatches"])

    def test_hash_chain_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = self._fixture(Path(temporary))
            mixed_overlay_path = self._paths(out_dir, self.MIXED_ID)["overlay"]
            mixed_overlay = json.loads(mixed_overlay_path.read_text(encoding="utf-8"))
            mixed_overlay["tampered"] = True
            self._write(mixed_overlay_path, mixed_overlay)
            self.assertEqual(1, self._run(out_dir))
            report = json.loads(self._output(out_dir).read_text(encoding="utf-8"))
            self.assertTrue(any("overlay report file" in item for item in report["mismatches"]))

    def test_nonidentity_replacement_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = self._fixture(Path(temporary), identity=False)
            self.assertEqual(1, self._run(out_dir))
            report = json.loads(self._output(out_dir).read_text(encoding="utf-8"))
            self.assertFalse(report["checks"]["identity_replacement"])

    def test_invalid_json_removes_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = self._fixture(Path(temporary))
            output = self._output(out_dir)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("stale\n", encoding="utf-8")
            self._paths(out_dir, self.MIXED_ID)["manifest"].write_text(
                '{"schema_version":1,"schema_version":1}\n', encoding="utf-8"
            )
            self.assertEqual(2, self._run(out_dir))
            self.assertFalse(output.exists())

    def test_output_cannot_replace_an_input_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = self._fixture(Path(temporary))
            manifest = self._paths(out_dir, self.MIXED_ID)["manifest"]
            before = refactor.sha256_file(manifest)
            self.assertEqual(2, self._run(out_dir, "--output", str(manifest)))
            self.assertTrue(manifest.is_file())
            self.assertEqual(before, refactor.sha256_file(manifest))


if __name__ == "__main__":
    unittest.main()
