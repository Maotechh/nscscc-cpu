from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import identity_compare, refactor


class IdentityCompareTests(unittest.TestCase):
    LOCKED_ID = "20260711-identity-locked"
    MIXED_ID = "20260711-identity-mixed"
    HEAD_SHA = "1" * 40
    FILE_SHA = "2" * 64
    DOCTOR_SHA = "3" * 64
    EVALUATOR_SHA = "4" * 64
    COMPARATOR_SHA = "5" * 64
    MANIFEST_SHA = "6" * 64
    GOLDEN_FILES_SHA = "7" * 64
    TOOL_SHA = "8" * 64
    MARKER_SHA = "9" * 64

    BASE_BUILD_LOG = (
        "%Warning-WIDTH: /tmp/work/IP/myCPU/alu.v:1: width warning\n"
        "%Warning-UNOPTFLAT: /tmp/work/IP/AMBA/bridge.v:2: loop warning\n"
    )
    PASS_SIMULATION_LOG = (
        "Using /tmp/la32r-nemu-interpreter-so for difftest\n"
        "Difftest enabled.\n"
        "HIT GOOD TRAP\n"
        "END by Syscall\n"
        "Reached test end PC.\n"
        "total instruction is 12\n"
        "total clock is 34\n"
    )

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

    def _write_bytes(self, path: Path, payload: bytes) -> dict[str, object]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return {
            "path": str(path),
            "sha256": refactor.sha256_bytes(payload),
            "size": len(payload),
        }

    def _paths(self, out_dir: Path, iteration_id: str) -> dict[str, Path]:
        return identity_compare._canonical_paths(out_dir, iteration_id)

    def _output(self, out_dir: Path) -> Path:
        return (
            out_dir
            / "reports"
            / "iterations"
            / self.MIXED_ID
            / "identity-comparison.json"
        )

    def _replacement(self, *, identity: bool) -> dict[str, object]:
        return {
            "schema_version": 1,
            "source_head": self.HEAD_SHA,
            "source_branch": "refactor/identity-test",
            "source_tree": "a" * 40,
            "spec_path": "tests/fixtures/component-overlay/identity.json",
            "spec_sha256": "b" * 64,
            "replacement_payload_source": "committed_git_blobs",
            "worktree_clean": True,
            "worktree_porcelain_clean": True,
            "worktree_semantic_clean": True,
            "worktree_semantic_diff_policy": "ignore-cr-at-eol-only",
            "worktree_eol_normalization_only": False,
            "worktree_raw_status_entry_count": 0,
            "replacements": [
                {
                    "target": "rtl/alu.v",
                    "source": "tests/fixtures/component-overlay/alu.v",
                    "source_oid": "c" * 40,
                    "source_mode": "100644",
                    "base_sha256": self.FILE_SHA,
                    "replacement_sha256": self.FILE_SHA if identity else "d" * 64,
                    "size": 16,
                }
            ],
        }

    def _tool_fingerprints(self) -> list[dict[str, object]]:
        return [
            {
                "name": "verilator",
                "manifest_key": "verilator_binary_sha256",
                "actual_sha256": self.TOOL_SHA,
                "expected_sha256": self.TOOL_SHA,
                "size": 10,
                "path": "/locked/verilator",
            }
        ]

    def _manifest(
        self, iteration_id: str, *, mixed: bool, identity: bool = True
    ) -> dict[str, object]:
        replacement = self._replacement(identity=identity) if mixed else None
        return {
            "schema_version": 1,
            "generated_at": "2026-07-11T00:00:00+08:00",
            "iteration_id": iteration_id,
            "dut_source": "mixed" if mixed else "candidate",
            "provenance_mode": "mixed_candidate" if mixed else "locked_candidate",
            "gate_kind": "component_replacement" if mixed else "baseline_candidate",
            "mode": "diagnostic" if mixed else "baseline",
            "candidate_locked": not mixed,
            "base_candidate_locked": True,
            "baseline_exact": not mixed,
            "gate_eligible": not mixed,
            "selection_sha256": ("e" if mixed else "f") * 64,
            "golden_candidate_commit": "0" * 40,
            "component_replacement": replacement,
            "chiplab_commit": "1" * 40,
            "chiplab_tree": "2" * 40,
            "mycpu_reference_commit": "3" * 40,
            "chiplab_reference": "/locked/chiplab-reference",
            "work_filesystem": "fixturefs",
            "manifest_sha256": self.MANIFEST_SHA,
            "golden_files_lock_sha256": self.GOLDEN_FILES_SHA,
            "golden_export_manifest_sha256": "4" * 64,
            "doctor_report_sha256": self.DOCTOR_SHA,
            "evaluator_sha256": self.EVALUATOR_SHA,
            "official_workspace_fingerprint": {
                "entry_count": 2,
                "sha256": "5" * 64,
            },
            "post_smoke_official_workspace_fingerprint": {
                "entry_count": 2,
                "sha256": "a" * 64,
            },
            "tool_links": {
                "gcc": "/locked/gcc",
                "nemu": "/locked/nemu",
                "picolibc": "/locked/picolibc",
            },
            "tool_fingerprints": self._tool_fingerprints(),
            "support_files": [
                {
                    "path": "IP/myCPU/mycpu.h",
                    "source": "upstream:mycpu.h",
                    "sha256": "6" * 64,
                    "size": 32,
                },
                {
                    "path": "IP/myCPU/LICENSE",
                    "source": "upstream:LICENSE",
                    "sha256": "7" * 64,
                    "size": 64,
                },
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

    def _overlay(
        self, manifest: dict[str, object], manifest_sha: str
    ) -> dict[str, object]:
        mixed = manifest["dut_source"] == "mixed"
        return {
            "schema_version": 1,
            "command": "chiplab-overlay",
            "generated_at": "2026-07-11T00:00:01+08:00",
            "run_id": "fixture-overlay",
            "status": "diagnostic" if mixed else "pass",
            **{
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
                    "doctor_report_sha256",
                )
            },
            "work_dir": "/locked/work",
            "file_count": 1,
            "replacement_count": 1 if mixed else 0,
            "overlay_manifest": "/locked/chiplab-overlay-manifest.json",
            "overlay_manifest_sha256": manifest_sha,
            "work_marker_sha256": self.MARKER_SHA,
            "evaluator_sha256": self.EVALUATOR_SHA,
        }

    def _raw_log(
        self, out_dir: Path, iteration_id: str, name: str, text: str
    ) -> dict[str, object]:
        path = (
            out_dir
            / "raw"
            / "iterations"
            / iteration_id
            / "rtl-smoke"
            / "fixture-run"
            / name
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = text.encode("utf-8")
        path.write_bytes(payload)
        return {"path": str(path), "sha256": refactor.sha256_bytes(payload)}

    def _artifacts(self, work: Path, *, mixed: bool) -> list[dict[str, object]]:
        run = work / "sims" / "verilator" / "run_prog"
        artifacts = [
            self._write_bytes(run / "log" / "compile.log", self.BASE_BUILD_LOG.encode()),
            self._write_bytes(run / "obj_dir" / "Vsimu_top.mk", b"makefile\n"),
            self._write_bytes(run / "obj_dir" / "Vsimu_top__ALL.a", b"archive\n"),
            self._write_bytes(
                run / "output", b"mixed simulator\n" if mixed else b"locked simulator\n"
            ),
            self._write_bytes(
                run / "obj" / "func" / "func_lab19_obj" / "obj" / "main.elf",
                b"same elf\n",
            ),
            self._write_bytes(
                run / "obj" / "func" / "func_lab19_obj" / "obj" / "rom.vlog",
                b"same rom\n",
            ),
            self._write_bytes(
                run
                / "log"
                / "func"
                / "func_lab19_log"
                / "simu_trace.txt",
                b"same architectural trace\n",
            ),
            self._write_bytes(
                run
                / "log"
                / "func"
                / "func_lab19_log"
                / "uart_output.txt",
                b"",
            ),
            self._write_bytes(
                run
                / "log"
                / "func"
                / "func_lab19_log"
                / "uart_output.txt.real",
                b"",
            ),
        ]
        self.assertEqual(9, len(artifacts))
        return artifacts

    @staticmethod
    def _artifact(artifacts: list[dict[str, object]], suffix: str) -> dict[str, object]:
        matches = [
            artifact
            for artifact in artifacts
            if str(artifact["path"]).replace("\\", "/").endswith(suffix)
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one artifact ending in {suffix}: {matches}")
        return matches[0]

    def _smoke(
        self,
        out_dir: Path,
        work: Path,
        overlay: dict[str, object],
        overlay_sha: str,
        manifest_sha: str,
        *,
        mixed: bool,
    ) -> dict[str, object]:
        iteration_id = str(overlay["iteration_id"])
        configure_log = self._raw_log(
            out_dir, iteration_id, "01-configure.log", "configured func/func_lab19\n"
        )
        build_log = self._raw_log(
            out_dir, iteration_id, "02-build.log", self.BASE_BUILD_LOG
        )
        simulation_log = self._raw_log(
            out_dir, iteration_id, "03-simulation.log", self.PASS_SIMULATION_LOG
        )
        artifacts = self._artifacts(work, mixed=mixed)
        build_artifacts = [
            {**artifact, "exists": True, "fresh": True}
            for artifact in artifacts[:6]
        ]
        warnings = refactor.parse_verilator_warnings(self.BASE_BUILD_LOG)
        parser = refactor.parse_simulation_log(
            self.PASS_SIMULATION_LOG, expected_termination="end_by_syscall"
        )
        environment = {
            "HOME": "/tmp/home",
            "PATH": "/locked/tool/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "TZ": "UTC",
            "CHIPLAB_HOME": str(work.resolve()),
        }
        environment_sha = refactor.sha256_bytes(
            json.dumps(environment, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        trace = self._artifact(artifacts, "/simu_trace.txt")
        uart = self._artifact(artifacts, "/uart_output.txt")
        uart_real = self._artifact(artifacts, "/uart_output.txt.real")
        gate_fail = {"planned": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0}
        pass_counts = {
            "planned": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        return {
            "schema_version": 1,
            "command": "rtl-smoke",
            "generated_at": "2026-07-11T00:00:02+08:00",
            "status": "diagnostic" if mixed else "fail",
            "run_id": "fixture-run",
            **{
                key: overlay[key]
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
                    "golden_candidate_commit",
                    "component_replacement",
                    "selection_sha256",
                )
            },
            "chiplab_commit": "1" * 40,
            "doctor_report_sha256": self.DOCTOR_SHA,
            "evaluator_sha256": self.EVALUATOR_SHA,
            "overlay_report_sha256": overlay_sha,
            "post_run_dut_verification": {
                "status": "pass",
                "work_marker_sha256": self.MARKER_SHA,
                "selection_sha256": overlay["selection_sha256"],
                "overlay_report_sha256": overlay_sha,
                "overlay_manifest_sha256": manifest_sha,
                "official_workspace_fingerprint": {
                    "entry_count": 2,
                    "sha256": "a" * 64,
                },
                "generated_path_exclusions": sorted(
                    refactor.smoke_generated_relative_paths(refactor.LOCKED_SMOKE_CASE)
                ),
            },
            "requested_case": "func/func_lab19",
            "actual_case": "func/func_lab19",
            "configure_valid": True,
            "compile_log_fresh": True,
            "build_artifacts_fresh": True,
            "output_contract_ok": True,
            "simulation_eligible": True,
            "build_errors": [],
            "build_integrity_status": "pass",
            "verilator_compile_status": "warning",
            "rtl_static_gate": "not_executed_by_rtl_smoke",
            "gate_result": "fail",
            "observed_result": "fail" if mixed else None,
            "functional_status": "pass",
            "environment": environment,
            "environment_sha256": environment_sha,
            "result_file_policy": {
                "status": "not_provided_by_locked_func_lab19",
                "functional_oracle": (
                    "NEMU DPI DiffTest markers and simulator termination output"
                ),
            },
            "commands": [
                {
                    "command": ["./configure.sh", "--run", "func/func_lab19"],
                    "cwd": str(work / "sims" / "verilator" / "run_prog"),
                    "exit_code": 0,
                    "timed_out": False,
                    "elapsed_seconds": 0.01,
                    "log_path": configure_log["path"],
                    "log_sha256": configure_log["sha256"],
                },
                {
                    "command": ["make", "verilator", "testbench", "soft_compile"],
                    "cwd": str(work / "sims" / "verilator" / "run_prog"),
                    "exit_code": 0,
                    "timed_out": False,
                    "elapsed_seconds": 0.02,
                    "log_path": build_log["path"],
                    "log_sha256": build_log["sha256"],
                },
                {
                    "command": ["make", "simulation_run_prog"],
                    "cwd": str(work / "sims" / "verilator" / "run_prog"),
                    "exit_code": 0,
                    "timed_out": False,
                    "elapsed_seconds": 0.03,
                    "log_path": simulation_log["path"],
                    "log_sha256": simulation_log["sha256"],
                },
            ],
            "counts": gate_fail,
            "functional_counts": pass_counts,
            "verilator_compile_counts": gate_fail,
            "parser": parser,
            "verilator_warnings": warnings,
            "compile_warning_policy": {
                "status": "fail",
                "rule": "No warning is accepted without a reviewed waiver.",
                "counts_by_scope": {"dut": 1, "official_environment": 1},
            },
            "raw_dir": str(
                out_dir
                / "raw"
                / "iterations"
                / iteration_id
                / "rtl-smoke"
                / "fixture-run"
            ),
            "output_evidence": {
                "simu_trace": {
                    **trace,
                    "exists": True,
                    "fresh": True,
                    "oracle_role": "trace_artifact",
                },
                "uart": {
                    **uart,
                    "exists": True,
                    "fresh": True,
                    "oracle_role": "not_applicable_for_func_lab19",
                },
                "uart_real": {
                    **uart_real,
                    "exists": True,
                    "fresh": True,
                    "oracle_role": "not_applicable_for_func_lab19",
                },
            },
            "build_artifacts": build_artifacts,
            "artifacts": artifacts,
        }

    def _anchors(
        self, out_dir: Path, chiplab_ref: Path, tool_root: Path
    ) -> dict[str, object]:
        return {
            "doctor_path": out_dir / "reports" / "chiplab-doctor.json",
            "doctor": {"tool_fingerprints": self._tool_fingerprints()},
            "doctor_sha256": self.DOCTOR_SHA,
            "manifest": {
                "chiplab_commit": "1" * 40,
                "chiplab_mycpu_gitlink": "3" * 40,
                "team_golden_candidate": "0" * 40,
            },
            "manifest_sha256": self.MANIFEST_SHA,
            "golden_files": ["rtl/alu.v"],
            "golden_files_sha256": self.GOLDEN_FILES_SHA,
            "refactor_sha256": self.EVALUATOR_SHA,
            "comparator_sha256": self.COMPARATOR_SHA,
            "head_sha": self.HEAD_SHA,
            "source_state": {
                "head": self.HEAD_SHA,
                "tree": "a" * 40,
                "branch": "refactor/identity-test",
                "porcelain_clean": True,
                "semantic_clean": True,
                "eol_normalization_only": False,
                "status_entry_count": 0,
            },
            "chiplab_reference": str(chiplab_ref.resolve()),
            "tool_root": str(tool_root.resolve()),
        }

    def _fixture(
        self, root: Path, *, identity: bool = True
    ) -> tuple[Path, Path, Path, Path]:
        out_dir = root / "out"
        work_root = root / "work"
        chiplab_ref = root / "reference"
        tool_root = root / "tools"
        for path in (out_dir, work_root, chiplab_ref, tool_root):
            path.mkdir(parents=True, exist_ok=True)
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
        self._publish_input(locked_paths["overlay"], locked_overlay)
        self._publish_input(mixed_paths["overlay"], mixed_overlay)
        locked_overlay_sha = refactor.sha256_file(locked_paths["overlay"])
        mixed_overlay_sha = refactor.sha256_file(mixed_paths["overlay"])
        self._write(
            locked_paths["smoke"],
            self._smoke(
                out_dir,
                work_root / self.LOCKED_ID,
                locked_overlay,
                locked_overlay_sha,
                locked_manifest_sha,
                mixed=False,
            ),
        )
        self._write(
            mixed_paths["smoke"],
            self._smoke(
                out_dir,
                work_root / self.MIXED_ID,
                mixed_overlay,
                mixed_overlay_sha,
                mixed_manifest_sha,
                mixed=True,
            ),
        )
        self._publish_input(
            locked_paths["smoke"],
            json.loads(locked_paths["smoke"].read_text(encoding="utf-8")),
        )
        self._publish_input(
            mixed_paths["smoke"],
            json.loads(mixed_paths["smoke"].read_text(encoding="utf-8")),
        )
        return out_dir, work_root, chiplab_ref, tool_root

    def _publish_input(self, path: Path, report: dict[str, object]) -> None:
        refactor.write_publication_marker(
            path,
            report,
            command=str(report["command"]),
            iteration_id=str(report["iteration_id"]),
            publication_id=str(report["run_id"]),
            publisher_sha256=str(report["evaluator_sha256"]),
        )

    def _fake_runtime_bindings(self, **kwargs: object) -> None:
        mixed_manifest = kwargs["mixed_manifest"]
        anchors = kwargs["anchors"]
        assert isinstance(mixed_manifest, dict)
        assert isinstance(anchors, dict)
        replacement = mixed_manifest.get("component_replacement")
        if not isinstance(replacement, dict) or replacement.get("source_head") != anchors.get(
            "head_sha"
        ):
            raise identity_compare.IdentityCompareError(
                "mixed replacement source is not current HEAD"
            )

    def _run(
        self,
        out_dir: Path,
        work_root: Path,
        chiplab_ref: Path,
        tool_root: Path,
    ) -> int:
        return self._run_captured(out_dir, work_root, chiplab_ref, tool_root)[0]

    def _run_captured(
        self,
        out_dir: Path,
        work_root: Path,
        chiplab_ref: Path,
        tool_root: Path,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(
            identity_compare,
            "_runtime_anchors",
            return_value=self._anchors(out_dir, chiplab_ref, tool_root),
        ), mock.patch.object(
            identity_compare,
            "_validate_runtime_bindings",
            side_effect=self._fake_runtime_bindings,
        ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = identity_compare.main(
                [
                    "--out-dir",
                    str(out_dir),
                    "--work-root",
                    str(work_root),
                    "--chiplab-ref",
                    str(chiplab_ref),
                    "--tool-root",
                    str(tool_root),
                    "--locked-iteration-id",
                    self.LOCKED_ID,
                    "--mixed-iteration-id",
                    self.MIXED_ID,
                ]
            )
        return result, stdout.getvalue(), stderr.getvalue()

    def _rewrite_smoke(self, out_dir: Path, iteration_id: str, smoke: dict[str, object]) -> None:
        path = self._paths(out_dir, iteration_id)["smoke"]
        self._write(path, smoke)
        self._publish_input(path, smoke)

    def _set_simulation_log(
        self, out_dir: Path, iteration_id: str, simulation_text: str
    ) -> None:
        smoke_path = self._paths(out_dir, iteration_id)["smoke"]
        smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        log_path = Path(smoke["commands"][2]["log_path"])
        payload = simulation_text.encode("utf-8")
        log_path.write_bytes(payload)
        smoke["parser"] = refactor.parse_simulation_log(
            simulation_text, expected_termination="end_by_syscall"
        )
        smoke["commands"][2]["log_sha256"] = refactor.sha256_bytes(payload)
        self._rewrite_smoke(out_dir, iteration_id, smoke)

    def _replace_physical_artifact(
        self,
        smoke: dict[str, object],
        suffix: str,
        payload: bytes,
    ) -> None:
        artifacts = smoke["artifacts"]
        build_artifacts = smoke["build_artifacts"]
        assert isinstance(artifacts, list)
        assert isinstance(build_artifacts, list)
        matches = [
            entry
            for entry in artifacts
            if isinstance(entry, dict)
            and str(entry.get("path", "")).replace("\\", "/").endswith(suffix)
        ]
        self.assertEqual(1, len(matches))
        path = Path(str(matches[0]["path"]))
        path.write_bytes(payload)
        digest = refactor.sha256_bytes(payload)
        for collection in (artifacts, build_artifacts):
            for entry in collection:
                if isinstance(entry, dict) and Path(str(entry.get("path", ""))) == path:
                    entry["sha256"] = digest
                    entry["size"] = len(payload)

    def _set_build_log(self, out_dir: Path, iteration_id: str, build_text: str) -> None:
        smoke_path = self._paths(out_dir, iteration_id)["smoke"]
        smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        log_path = Path(smoke["commands"][1]["log_path"])
        payload = build_text.encode("utf-8")
        log_path.write_bytes(payload)
        smoke["commands"][1]["log_sha256"] = refactor.sha256_bytes(payload)
        self._replace_physical_artifact(smoke, "/log/compile.log", payload)
        warnings = refactor.parse_verilator_warnings(build_text)
        smoke["verilator_warnings"] = warnings
        smoke["build_errors"] = refactor.parse_build_errors(
            build_text + "\n" + build_text
        )
        scope_counts = {
            "dut": sum(item["scope"] == "dut" for item in warnings),
            "official_environment": sum(
                item["scope"] == "official_environment" for item in warnings
            ),
        }
        smoke["compile_warning_policy"]["counts_by_scope"] = scope_counts
        smoke["compile_warning_policy"]["status"] = "fail" if warnings else "pass"
        if warnings:
            smoke["verilator_compile_status"] = "warning"
            smoke["verilator_compile_counts"] = {
                "planned": 1,
                "executed": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
            }
            smoke["gate_result"] = "fail"
            smoke["counts"] = dict(smoke["verilator_compile_counts"])
            smoke["status"] = (
                "diagnostic" if smoke["dut_source"] == "mixed" else "fail"
            )
        else:
            smoke["verilator_compile_status"] = "pass"
            smoke["verilator_compile_counts"] = {
                "planned": 1,
                "executed": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
            }
            smoke["gate_result"] = "pass"
            smoke["counts"] = dict(smoke["verilator_compile_counts"])
            smoke["status"] = (
                "diagnostic" if smoke["dut_source"] == "mixed" else "pass"
            )
        self._rewrite_smoke(out_dir, iteration_id, smoke)

    def test_identity_comparison_accepts_equal_failure_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            self.assertEqual(0, self._run(*fixture))
            report = json.loads(self._output(fixture[0]).read_text(encoding="utf-8"))
            self.assertEqual("pass", report["status"])
            self.assertFalse(report["gate_eligible"])
            self.assertEqual("fail", report["observed"]["locked_gate_result"])
            self.assertIn("simulator output binary", report["excluded_fields"])

    def test_parser_drift_with_matching_raw_log_writes_failure_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            changed = self.PASS_SIMULATION_LOG.replace(
                "total instruction is 12", "total instruction is 99"
            )
            self._set_simulation_log(fixture[0], self.MIXED_ID, changed)
            self.assertEqual(1, self._run(*fixture))
            report = json.loads(self._output(fixture[0]).read_text(encoding="utf-8"))
            self.assertEqual("fail", report["status"])
            self.assertIn(
                "locked and mixed parser observations differ", report["mismatches"]
            )

    def test_nonidentity_replacement_writes_comparison_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary), identity=False)
            self.assertEqual(1, self._run(*fixture))
            report = json.loads(self._output(fixture[0]).read_text(encoding="utf-8"))
            self.assertFalse(report["checks"]["identity_replacement"])

    def test_hash_chain_tamper_writes_comparison_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            overlay_path = self._paths(fixture[0], self.MIXED_ID)["overlay"]
            overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
            overlay["tampered_after_smoke"] = True
            self._write(overlay_path, overlay)
            self._publish_input(overlay_path, overlay)
            self.assertEqual(1, self._run(*fixture))
            report = json.loads(self._output(fixture[0]).read_text(encoding="utf-8"))
            self.assertTrue(
                any("overlay report file" in item for item in report["mismatches"])
            )

    def test_null_hash_is_an_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            smoke_path = self._paths(fixture[0], self.MIXED_ID)["smoke"]
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            smoke["doctor_report_sha256"] = None
            self._rewrite_smoke(fixture[0], self.MIXED_ID, smoke)
            self.assertEqual(2, self._run(*fixture))
            self.assertFalse(self._output(fixture[0]).exists())

    def test_empty_command_parser_or_evidence_is_an_input_error(self) -> None:
        mutations = (
            ("commands", []),
            ("parser", {}),
            ("output_evidence", {}),
            ("build_artifacts", []),
            ("artifacts", []),
            ("environment", {}),
        )
        for field, value in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                fixture = self._fixture(Path(temporary))
                smoke_path = self._paths(fixture[0], self.MIXED_ID)["smoke"]
                smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
                smoke[field] = value
                self._rewrite_smoke(fixture[0], self.MIXED_ID, smoke)
                self.assertEqual(2, self._run(*fixture))
                self.assertFalse(self._output(fixture[0]).exists())

    def test_numeric_boolean_is_an_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            smoke_path = self._paths(fixture[0], self.MIXED_ID)["smoke"]
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            smoke["gate_eligible"] = 0
            self._rewrite_smoke(fixture[0], self.MIXED_ID, smoke)
            self.assertEqual(2, self._run(*fixture))

    def test_locked_smoke_semantics_cannot_be_changed_on_both_sides(self) -> None:
        def change_rtl_static(smoke: dict[str, object]) -> None:
            smoke["rtl_static_gate"] = "claimed_pass"

        def change_result_policy(smoke: dict[str, object]) -> None:
            smoke["result_file_policy"]["status"] = "provided"

        def change_oracle_role(smoke: dict[str, object]) -> None:
            smoke["output_evidence"]["simu_trace"]["oracle_role"] = "other"

        def change_counts(smoke: dict[str, object]) -> None:
            smoke["counts"] = {
                "planned": 2,
                "executed": 2,
                "passed": 0,
                "failed": 2,
                "skipped": 0,
            }

        def change_elapsed(smoke: dict[str, object]) -> None:
            smoke["commands"][0]["elapsed_seconds"] = float("inf")

        mutations = {
            "rtl_static": change_rtl_static,
            "result_policy": change_result_policy,
            "oracle_role": change_oracle_role,
            "counts": change_counts,
            "elapsed": change_elapsed,
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                fixture = self._fixture(Path(temporary))
                for iteration_id in (self.LOCKED_ID, self.MIXED_ID):
                    smoke_path = self._paths(fixture[0], iteration_id)["smoke"]
                    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
                    mutate(smoke)
                    self._rewrite_smoke(fixture[0], iteration_id, smoke)
                self.assertEqual(2, self._run(*fixture))
                self.assertFalse(self._output(fixture[0]).exists())

    def test_replacement_source_head_must_match_runtime_head(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            for name in ("manifest", "overlay", "smoke"):
                path = self._paths(fixture[0], self.MIXED_ID)[name]
                document = json.loads(path.read_text(encoding="utf-8"))
                document["component_replacement"]["source_head"] = "a" * 40
                self._write(path, document)
            manifest_path = self._paths(fixture[0], self.MIXED_ID)["manifest"]
            overlay_path = self._paths(fixture[0], self.MIXED_ID)["overlay"]
            manifest_sha = refactor.sha256_file(manifest_path)
            overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
            overlay["overlay_manifest_sha256"] = manifest_sha
            self._write(overlay_path, overlay)
            smoke_path = self._paths(fixture[0], self.MIXED_ID)["smoke"]
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            overlay_sha = refactor.sha256_file(overlay_path)
            smoke["overlay_report_sha256"] = overlay_sha
            smoke["post_run_dut_verification"]["overlay_report_sha256"] = overlay_sha
            smoke["post_run_dut_verification"]["overlay_manifest_sha256"] = manifest_sha
            self._write(smoke_path, smoke)
            self.assertEqual(2, self._run(*fixture))

    def test_input_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            manifest = self._paths(fixture[0], self.MIXED_ID)["manifest"]
            real = Path(temporary) / "manifest-real.json"
            real.write_bytes(manifest.read_bytes())
            manifest.unlink()
            try:
                manifest.symlink_to(real)
            except OSError as error:
                self.skipTest(f"symlink creation unavailable: {error}")
            self.assertEqual(2, self._run(*fixture))
            self.assertFalse(self._output(fixture[0]).exists())

    def test_output_symlink_cannot_clobber_victim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            output = self._output(fixture[0])
            victim = Path(temporary) / "victim.json"
            victim.write_text("do not replace\n", encoding="utf-8")
            try:
                output.symlink_to(victim)
            except OSError as error:
                self.skipTest(f"symlink creation unavailable: {error}")
            self.assertEqual(2, self._run(*fixture))
            self.assertEqual("do not replace\n", victim.read_text(encoding="utf-8"))
            self.assertTrue(output.is_symlink())

    def test_active_iteration_lock_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            lock = (
                fixture[0]
                / ".locks"
                / "iterations"
                / f"{self.LOCKED_ID}.lock"
            )
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text("{}\n", encoding="utf-8")
            self.assertEqual(2, self._run(*fixture))
            self.assertTrue(lock.is_file())
            self.assertFalse(self._output(fixture[0]).exists())

    def test_active_lock_preserves_existing_comparison_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            output = self._output(fixture[0])
            existing = '{"status":"pass","owner":"active-run"}\n'
            output.write_text(existing, encoding="utf-8")
            lock = (
                fixture[0]
                / ".locks"
                / "iterations"
                / f"{self.LOCKED_ID}.lock"
            )
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text("{}\n", encoding="utf-8")

            self.assertEqual(2, self._run(*fixture))

            self.assertEqual(existing, output.read_text(encoding="utf-8"))
            self.assertTrue(lock.is_file())

    def test_partial_lock_acquisition_releases_only_comparator_locks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            active = (
                fixture[1]
                / ".locks"
                / "iterations"
                / f"{self.LOCKED_ID}.lock"
            )
            active.parent.mkdir(parents=True, exist_ok=True)
            active.write_text("{}\n", encoding="utf-8")

            self.assertEqual(2, self._run(*fixture))

            self.assertTrue(active.is_file())
            for iteration_id in (self.LOCKED_ID, self.MIXED_ID):
                self.assertFalse(
                    (
                        fixture[0]
                        / ".locks"
                        / "iterations"
                        / f"{iteration_id}.lock"
                    ).exists()
                )
            self.assertFalse(
                (
                    fixture[1]
                    / ".locks"
                    / "iterations"
                    / f"{self.MIXED_ID}.lock"
                ).exists()
            )
            self.assertFalse(self._output(fixture[0]).exists())

    def test_partial_lock_rollback_attempts_every_release_after_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            active = (
                fixture[1]
                / ".locks"
                / "iterations"
                / f"{self.MIXED_ID}.lock"
            )
            active.parent.mkdir(parents=True, exist_ok=True)
            active.write_text("{}\n", encoding="utf-8")
            real_release = refactor.release_validation_lock
            release_count = 0

            def release_then_fail_once(lock: refactor.ValidationLock) -> None:
                nonlocal release_count
                release_count += 1
                real_release(lock)
                if release_count == 1:
                    raise refactor.RefactorError("simulated rollback release failure")

            with mock.patch.object(
                refactor,
                "release_validation_lock",
                side_effect=release_then_fail_once,
            ):
                self.assertEqual(2, self._run(*fixture))

            self.assertEqual(3, release_count)
            self.assertTrue(active.is_file())
            for root, iteration_id in (
                (fixture[0], self.LOCKED_ID),
                (fixture[0], self.MIXED_ID),
                (fixture[1], self.LOCKED_ID),
            ):
                self.assertFalse(
                    (root / ".locks" / "iterations" / f"{iteration_id}.lock").exists()
                )
            self.assertFalse(self._output(fixture[0]).exists())

    def test_release_error_after_real_release_keeps_marker_bound_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            real_release = refactor.release_validation_lock
            release_count = 0

            def release_then_fail_once(lock: refactor.ValidationLock) -> None:
                nonlocal release_count
                release_count += 1
                real_release(lock)
                if release_count == 1:
                    raise refactor.RefactorError("simulated publication release failure")

            with mock.patch.object(
                refactor,
                "release_validation_lock",
                side_effect=release_then_fail_once,
            ):
                result, stdout, _ = self._run_captured(*fixture)

            self.assertEqual(2, result)
            self.assertEqual(4, release_count)
            self.assertNotIn('"status": "pass"', stdout)
            output = self._output(fixture[0])
            self.assertTrue(output.is_file())
            report = json.loads(output.read_text(encoding="utf-8"))
            runtime = report["runtime"]
            self.assertIsInstance(runtime, dict)
            refactor.require_report_publication(
                output,
                report,
                refactor.sha256_file(output),
                command="identity-compare",
                iteration_id=self.MIXED_ID,
                publication_id=str(report["run_id"]),
                publisher_sha256=str(runtime["comparator_sha256"]),
            )
            for root in (fixture[0], fixture[1]):
                for iteration_id in (self.LOCKED_ID, self.MIXED_ID):
                    self.assertFalse(
                        (
                            root
                            / ".locks"
                            / "iterations"
                            / f"{iteration_id}.lock"
                        ).exists()
                    )

    def test_physical_artifact_tamper_is_an_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            smoke_path = self._paths(fixture[0], self.MIXED_ID)["smoke"]
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            elf = next(
                item
                for item in smoke["artifacts"]
                if str(item["path"]).replace("\\", "/").endswith("/main.elf")
            )
            Path(elf["path"]).write_bytes(b"tampered elf\n")
            self.assertEqual(2, self._run(*fixture))
            self.assertFalse(self._output(fixture[0]).exists())

    def test_unpublished_smoke_report_is_an_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            smoke_path = self._paths(fixture[0], self.MIXED_ID)["smoke"]
            refactor.publication_marker_path(smoke_path).unlink()

            self.assertEqual(2, self._run(*fixture))
            self.assertFalse(self._output(fixture[0]).exists())

    def test_hidden_physical_compile_error_is_an_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            smoke_path = self._paths(fixture[0], self.MIXED_ID)["smoke"]
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            self._replace_physical_artifact(
                smoke,
                "/log/compile.log",
                b"%Error: hidden compile failure\n",
            )
            self._rewrite_smoke(fixture[0], self.MIXED_ID, smoke)

            self.assertEqual(2, self._run(*fixture))
            self.assertFalse(self._output(fixture[0]).exists())

    def test_warning_evidence_cannot_be_forged_as_gate_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            pass_counts = {
                "planned": 1,
                "executed": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
            }
            for iteration_id in (self.LOCKED_ID, self.MIXED_ID):
                smoke_path = self._paths(fixture[0], iteration_id)["smoke"]
                smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
                smoke["compile_warning_policy"]["status"] = "pass"
                smoke["verilator_compile_status"] = "pass"
                smoke["verilator_compile_counts"] = dict(pass_counts)
                smoke["gate_result"] = "pass"
                smoke["counts"] = dict(pass_counts)
                smoke["status"] = (
                    "diagnostic" if iteration_id == self.MIXED_ID else "pass"
                )
                smoke["observed_result"] = (
                    "pass" if iteration_id == self.MIXED_ID else None
                )
                self._rewrite_smoke(fixture[0], iteration_id, smoke)

            self.assertEqual(2, self._run(*fixture))
            self.assertFalse(self._output(fixture[0]).exists())

    def test_unknown_oracle_bypass_field_is_rejected_on_both_sides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            for iteration_id in (self.LOCKED_ID, self.MIXED_ID):
                smoke_path = self._paths(fixture[0], iteration_id)["smoke"]
                smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
                smoke["oracle_bypassed"] = True
                self._rewrite_smoke(fixture[0], iteration_id, smoke)

            self.assertEqual(2, self._run(*fixture))
            self.assertFalse(self._output(fixture[0]).exists())

    def test_warning_tuple_distribution_is_compared_without_key_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            locked_build = (
                "%Warning-WIDTH: /tmp/work/IP/myCPU/alu.v:1: warning\n"
                "%Warning-UNDRIVEN: /tmp/work/IP/AMBA/bridge.v:2: warning\n"
            )
            mixed_build = (
                "%Warning-UNDRIVEN: /tmp/work/IP/myCPU/alu.v:1: warning\n"
                "%Warning-WIDTH: /tmp/work/IP/AMBA/bridge.v:2: warning\n"
            )
            self._set_build_log(fixture[0], self.LOCKED_ID, locked_build)
            self._set_build_log(fixture[0], self.MIXED_ID, mixed_build)
            self.assertEqual(1, self._run(*fixture))
            report = json.loads(self._output(fixture[0]).read_text(encoding="utf-8"))
            self.assertFalse(report["checks"]["warning_counts_equal"])
            self.assertIn("Verilator warning counts differ", report["mismatches"])

    def test_invalid_json_removes_stale_fixed_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            output = self._output(fixture[0])
            output.write_text("stale\n", encoding="utf-8")
            self._paths(fixture[0], self.MIXED_ID)["manifest"].write_text(
                '{"schema_version":1,"schema_version":1}\n', encoding="utf-8"
            )
            self.assertEqual(2, self._run(*fixture))
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
