from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import refactor


class LockParsingTests(unittest.TestCase):
    def test_parse_lock_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.lock"
            path.write_text("key=one\nkey=two\n", encoding="utf-8")
            with self.assertRaises(refactor.RefactorError):
                refactor.parse_lock(path)

    def test_golden_lock_excludes_known_dead_files(self) -> None:
        files = set(refactor.read_golden_files())
        self.assertTrue(files)
        self.assertFalse(files & refactor.FORBIDDEN_GOLDEN_FILES)
        self.assertIn("rtl/mycpu_top.v", files)
        self.assertIn("rtl/lacc_demo.v", files)


class VivadoProbeTests(unittest.TestCase):
    MANIFEST = {"vivado": "2023.2", "vivado_build": "4029153"}

    def test_accepts_locked_vivado_version_and_build(self) -> None:
        text = "vivado v2023.2 (64-bit)\nSW Build 4029153 on Fri Oct 13 2023\n"
        self.assertTrue(refactor.vivado_version_matches(text, self.MANIFEST))

    def test_rejects_wrong_build_or_error_output(self) -> None:
        self.assertFalse(
            refactor.vivado_version_matches(
                "vivado v2023.2 (64-bit)\nSW Build 0000000\n", self.MANIFEST
            )
        )
        self.assertFalse(
            refactor.vivado_version_matches(
                "vivado v2023.2 (64-bit)\nSW Build 4029153\nERROR: broken\n",
                self.MANIFEST,
            )
        )


class MakeContractTests(unittest.TestCase):
    ITERATION = "component-overlay-make-test"
    SOURCE_HEAD = "b" * 40
    SPEC = "tests/fixtures/component-overlay/identity.json"
    WORK_ROOT = "/tmp/component overlay work"

    def _dry_run(self, *assignments: str) -> refactor.CommandResult:
        return refactor.run_command(
            [
                "make",
                "-n",
                f"ITERATION_ID={self.ITERATION}",
                "CHIPLAB_REFERENCE=/opt/chiplab-reference",
                f"CHIPLAB_WORK_ROOT={self.WORK_ROOT}",
                *assignments,
                "chiplab-overlay",
                "rtl-smoke",
            ],
            cwd=refactor.REPO_ROOT,
        )

    def test_default_candidate_dry_run_has_no_diagnostic_override(self) -> None:
        result = self._dry_run()
        self.assertEqual(0, result.exit_code, result.stderr)
        self.assertIn('--dut-source "candidate"', result.stdout)
        self.assertNotIn("--diagnostic", result.stdout)
        self.assertNotIn("--replacement-spec", result.stdout)

    def test_diagnostic_boolean_expansion_is_exact(self) -> None:
        for value, expected_count in (("", 0), ("0", 0), ("1", 2)):
            result = self._dry_run(f"DIAGNOSTIC={value}")
            with self.subTest(value=value):
                self.assertEqual(0, result.exit_code, result.stderr)
                self.assertEqual(expected_count, result.stdout.count("--diagnostic"))
        invalid = self._dry_run("DIAGNOSTIC=0 1")
        self.assertNotEqual(0, invalid.exit_code)
        self.assertIn("DIAGNOSTIC must be empty, 0, or 1", invalid.stderr)

    def test_mixed_dry_run_forwards_all_provenance_arguments(self) -> None:
        result = self._dry_run(
            "DUT_SOURCE=mixed",
            "DIAGNOSTIC=1",
            f"REPLACEMENT_SPEC={self.SPEC}",
            f"SOURCE_HEAD={self.SOURCE_HEAD}",
        )
        self.assertEqual(0, result.exit_code, result.stderr)
        self.assertIn('--dut-source "mixed"', result.stdout)
        self.assertIn(f'--replacement-spec "{self.SPEC}"', result.stdout)
        self.assertIn(f'--source-head "{self.SOURCE_HEAD}"', result.stdout)
        self.assertEqual(2, result.stdout.count("--diagnostic"))

    def test_overlay_and_smoke_receive_the_same_work_root(self) -> None:
        result = self._dry_run()
        self.assertEqual(0, result.exit_code, result.stderr)
        self.assertEqual(
            2, result.stdout.count(f'--work-root "{self.WORK_ROOT}"')
        )


class SimulationParserTests(unittest.TestCase):
    PASS_LOG = """
Using /tmp/toolchains/nemu/la32r-nemu-interpreter-so for difftest
The first instruction of core 0 has commited. Difftest enabled.
HIT GOOD TRAP
total clock is 1234
total instruction is 1000
Reached test end PC.
"""

    def test_requires_all_positive_markers(self) -> None:
        parsed = refactor.parse_simulation_log(self.PASS_LOG)
        self.assertEqual("pass", parsed["status"])
        self.assertEqual(1000, parsed["instructions"])

    def test_exit_zero_style_mismatch_is_still_failure(self) -> None:
        parsed = refactor.parse_simulation_log(
            self.PASS_LOG + "r4 different at pc = 0x1c000100, right=1, wrong=2\n"
        )
        self.assertEqual("fail", parsed["status"])
        self.assertIn("difftest_mismatch", parsed["failures"])

    def test_bad_trap_overrides_positive_markers(self) -> None:
        parsed = refactor.parse_simulation_log(self.PASS_LOG + "HIT BAD TRAP\n")
        self.assertEqual("fail", parsed["status"])
        self.assertIn("bad_trap", parsed["failures"])

    def test_missing_difftest_marker_is_failure(self) -> None:
        parsed = refactor.parse_simulation_log("total clock is 10\ntotal instruction is 2\nReached test end PC.\n")
        self.assertEqual("fail", parsed["status"])

    def test_locked_nemu_end_marker_is_accepted_without_good_trap_text(self) -> None:
        parsed = refactor.parse_simulation_log(
            self.PASS_LOG.replace("HIT GOOD TRAP", "END by Syscall")
        )
        self.assertEqual("pass", parsed["status"])


class GeneratedDirectorySafetyTests(unittest.TestCase):
    def test_refuses_to_delete_unmarked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "existing"
            target.mkdir()
            (target / "user-data").write_text("keep", encoding="utf-8")
            with self.assertRaises(refactor.RefactorError):
                refactor.reset_generated_dir(target, root, "test")
            self.assertTrue((target / "user-data").is_file())

    def test_replaces_only_marked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "generated"
            target.mkdir()
            refactor.write_json(
                target / refactor.GENERATED_MARKER,
                {"purpose": "replacement", "resolved_path": str(target.resolve())},
            )
            (target / "old").write_text("old", encoding="utf-8")
            refactor.reset_generated_dir(target, root, "replacement")
            marker = json.loads((target / refactor.GENERATED_MARKER).read_text(encoding="utf-8"))
            self.assertEqual("replacement", marker["purpose"])
            self.assertFalse((target / "old").exists())

    def test_refuses_marker_for_another_path_or_purpose(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "generated"
            target.mkdir()
            refactor.write_json(
                target / refactor.GENERATED_MARKER,
                {"purpose": "other", "resolved_path": str(target.resolve())},
            )
            with self.assertRaises(refactor.RefactorError):
                refactor.reset_generated_dir(target, root, "replacement")


class GateIntegrityTests(unittest.TestCase):
    def test_empty_chiplab_doctor_checks_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_dir = root / "out"
            refactor.write_json(
                refactor.report_path(out_dir, "chiplab-doctor"),
                {
                    "schema_version": 1,
                    "command": "chiplab-doctor",
                    "status": "pass",
                    "checks": [],
                },
            )
            with self.assertRaisesRegex(refactor.RefactorError, "not a complete PASS"):
                refactor.require_passing_chiplab_doctor(
                    out_dir, root / "chiplab", root / "tools", 3600
                )

    def test_installed_tool_specs_include_python_evaluator(self) -> None:
        specs = refactor.installed_tool_specs(Path("/tmp/tools"), {"sbt": "1.10.11"})
        python = next(item for item in specs if item[0] == "python")
        self.assertEqual(Path(sys.executable).resolve(), python[1])
        self.assertEqual("python_binary_sha256", python[2])

    def test_cli_refuses_nonisolated_python(self) -> None:
        result = refactor.run_command(
            [sys.executable, str(Path(refactor.__file__)), "--help"], cwd=Path.cwd()
        )
        self.assertEqual(2, result.exit_code)
        self.assertIn("requires isolated Python", result.stderr)

        isolated = refactor.run_command(
            [sys.executable, "-I", str(Path(refactor.__file__)), "--help"], cwd=Path.cwd()
        )
        self.assertEqual(0, isolated.exit_code)

    def test_command_report_hash_binds_raw_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "raw.log"
            result = refactor.run_command(
                [sys.executable, "-c", "print('bound')"], cwd=root, log_path=log
            )
            report = result.as_dict()
            expected_log_sha256 = refactor.sha256_file(log)
        self.assertEqual(0, result.exit_code)
        self.assertEqual(str(log.resolve()), report["log_path"])
        self.assertEqual(expected_log_sha256, report["log_sha256"])

    def test_missing_executable_is_structured_exit_127(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = refactor.run_command(
                ["definitely-not-an-installed-command-nscscc"], cwd=Path(temporary)
            )
        self.assertEqual(127, result.exit_code)
        self.assertIn("unable to start command", result.stderr)

    def test_gate_counts_always_obey_arithmetic(self) -> None:
        for executed, passed in ((False, False), (True, False), (True, True)):
            counts = refactor.gate_counts(executed=executed, passed=passed)
            self.assertEqual(counts["executed"], counts["passed"] + counts["failed"])
            self.assertEqual(counts["planned"], counts["executed"] + counts["skipped"])

    def test_missing_compile_log_can_never_pass_static_gate(self) -> None:
        build = refactor.CommandResult(["make"], "/tmp", 0, 1.0, "", "")
        self.assertFalse(
            refactor.verilator_compile_check_passed(
                build, compile_fresh=False, warnings=[]
            )
        )
        self.assertFalse(
            refactor.verilator_compile_check_passed(
                None, compile_fresh=False, warnings=[]
            )
        )
        self.assertTrue(
            refactor.verilator_compile_check_passed(
                build, compile_fresh=True, warnings=[]
            )
        )

    def test_build_errors_override_exit_zero(self) -> None:
        build = refactor.CommandResult(["make"], "/tmp", 0, 1.0, "", "")
        errors = refactor.parse_build_errors(
            "%Error-WIDTH: broken\nmake[2]: *** [target] Error 1\n"
        )
        self.assertEqual(2, len(errors))
        self.assertFalse(
            refactor.verilator_compile_check_passed(
                build,
                compile_fresh=True,
                warnings=[],
                errors=errors,
                artifacts_fresh=True,
            )
        )

    def test_warnings_fail_compile_policy_but_not_build_integrity(self) -> None:
        build = refactor.CommandResult(["make"], "/tmp", 0, 1.0, "", "")
        warnings = [{"category": "WIDTH", "scope": "dut", "line": "warning"}]
        self.assertTrue(
            refactor.verilator_build_integrity_passed(
                build, compile_fresh=True, errors=[], artifacts_fresh=True
            )
        )
        self.assertFalse(
            refactor.verilator_compile_check_passed(
                build,
                compile_fresh=True,
                warnings=warnings,
                errors=[],
                artifacts_fresh=True,
            )
        )

    def test_missing_or_stale_build_artifact_blocks_compile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            started_ns = time.time_ns()
            paths = [
                run_dir / "log" / "compile.log",
                run_dir / "obj_dir" / "Vsimu_top.mk",
                run_dir / "obj_dir" / "Vsimu_top__ALL.a",
                run_dir / "output",
                run_dir / "obj" / "func" / "func_lab19_obj" / "obj" / "main.elf",
                run_dir / "obj" / "func" / "func_lab19_obj" / "obj" / "rom.vlog",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fresh\n", encoding="utf-8")
            entries, all_fresh = refactor.fresh_build_artifacts(
                run_dir, "func/func_lab19", started_ns
            )
            self.assertTrue(all_fresh)
            self.assertTrue(all(item["fresh"] for item in entries))
            paths[-1].unlink()
            _, all_fresh = refactor.fresh_build_artifacts(
                run_dir, "func/func_lab19", started_ns
            )
            self.assertFalse(all_fresh)

    def test_smoke_workspace_lock_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            lock = refactor.acquire_smoke_lock(work, "iteration", "run-one")
            with self.assertRaisesRegex(refactor.RefactorError, "already exists"):
                refactor.acquire_smoke_lock(work, "iteration", "run-two")
            lock.unlink()

    def test_overlay_and_smoke_share_iteration_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary)
            lock = refactor.acquire_iteration_lock(
                out_dir, "20260711-lock-test", "chiplab-overlay", "overlay-run"
            )
            with self.assertRaisesRegex(refactor.RefactorError, "already exists"):
                refactor.acquire_iteration_lock(
                    out_dir, "20260711-lock-test", "rtl-smoke", "smoke-run"
                )
            lock.unlink()

    def test_validation_roots_must_not_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_pairs = ((root / "out", root / "work"),)
            invalid_pairs = (
                (root, root),
                (root, root / "work"),
                (root / "out", root),
            )
            for out_dir, work_root in valid_pairs:
                refactor.require_nonoverlapping_validation_roots(out_dir, work_root)
            for out_dir, work_root in invalid_pairs:
                with self.subTest(
                    out_dir=out_dir, work_root=work_root
                ), self.assertRaisesRegex(refactor.RefactorError, "non-overlapping"):
                    refactor.require_nonoverlapping_validation_roots(out_dir, work_root)

    def test_overlay_failure_removes_stale_report_and_releases_locks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_dir = root / "out"
            iteration_id = "20260711-stale-overlay-test"
            stale = refactor.iteration_report_path(
                out_dir, iteration_id, "chiplab-overlay"
            )
            refactor.write_json(stale, {"status": "pass", "gate_eligible": True})
            args = SimpleNamespace(
                out_dir=str(out_dir),
                work_root=str(root / "work-root"),
                iteration_id=iteration_id,
            )
            with mock.patch.object(
                refactor,
                "_command_chiplab_overlay_locked",
                side_effect=refactor.RefactorError("intentional failure"),
            ), self.assertRaisesRegex(refactor.RefactorError, "intentional failure"):
                refactor.command_chiplab_overlay(args)
            self.assertFalse(stale.exists())
            self.assertFalse(
                (out_dir / ".locks" / "iterations" / f"{iteration_id}.lock").exists()
            )
            self.assertFalse(
                (
                    root
                    / "work-root"
                    / ".locks"
                    / "iterations"
                    / f"{iteration_id}.lock"
                ).exists()
            )

    def test_smoke_cleanup_removes_every_reusable_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            run_dir = work / "sims" / "verilator" / "run_prog"
            paths = [
                run_dir / "obj_dir" / "model.a",
                run_dir / "output",
                run_dir / "tmp" / "temporary",
                run_dir / "obj" / "func" / "func_lab19_obj" / "old.elf",
                work / "software" / "examples" / "func" / "func_lab19" / "obj" / "old.o",
                run_dir / "log" / "func" / "func_lab19_log" / "simu_trace.txt",
                run_dir / "log" / "compile.log",
                run_dir / "config-software.mak",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("old\n", encoding="utf-8")
            removed = refactor.clean_smoke_generated_paths(
                work, run_dir, "func/func_lab19"
            )
            self.assertEqual(8, len(removed))
            self.assertTrue(all(not path.exists() for path in paths))

    def test_rtl_smoke_never_simulates_when_tee_hides_verilator_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_dir = root / "out"
            work = root / "work"
            run_dir = work / "sims" / "verilator" / "run_prog"
            run_dir.mkdir(parents=True)
            iteration_id = "20260711-1200-tee-error-test"
            overlay_report = refactor.iteration_report_path(
                out_dir, iteration_id, "chiplab-overlay"
            )
            overlay = {
                "gate_eligible": True,
                "dut_source": "candidate",
                "golden_candidate_commit": "a" * 40,
                "candidate_locked": True,
            }
            marker = work / ".refactor-overlay.json"
            immutable_manifest = root / "immutable-overlay.json"
            refactor.write_json(marker, overlay)
            refactor.write_json(immutable_manifest, overlay)
            overlay_projection = {
                "work_marker_sha256": refactor.sha256_file(marker),
                "overlay_manifest": str(immutable_manifest),
                "overlay_manifest_sha256": refactor.sha256_file(immutable_manifest),
            }
            refactor.write_json(overlay_report, overlay_projection)
            overlay_report_sha = refactor.sha256_file(overlay_report)
            calls: list[list[str]] = []

            def fake_run(command: list[str], **kwargs: object) -> refactor.CommandResult:
                argv = [str(item) for item in command]
                calls.append(argv)
                if argv[0] == "./configure.sh":
                    (run_dir / "config-software.mak").write_text(
                        "RUN_SOFTWARE = func/func_lab19\n", encoding="utf-8"
                    )
                elif argv[0] == "make" and argv[1] == "verilator":
                    compile_log = run_dir / "log" / "compile.log"
                    compile_log.parent.mkdir(parents=True, exist_ok=True)
                    compile_log.write_text(
                        "%Error-WIDTH: build failed but tee returned zero\n", encoding="utf-8"
                    )
                else:
                    self.fail(f"unexpected simulation call: {argv}")
                return refactor.CommandResult(argv, str(run_dir), 0, 0.01, "", "")

            args = SimpleNamespace(
                out_dir=str(out_dir),
                iteration_id=iteration_id,
                case="func/func_lab19",
                tool_root=str(root / "tools"),
                work_root=str(root / "work-root"),
                diagnostic=False,
                doctor_max_age_seconds=3600,
                configure_timeout=10,
                build_timeout=10,
                sim_timeout=10,
            )
            with mock.patch.object(
                refactor,
                "verify_overlay_integrity",
                return_value=(
                    work,
                    overlay,
                    overlay_projection,
                    "d" * 64,
                    overlay_report_sha,
                ),
            ), mock.patch.object(
                refactor, "require_posix_validation_environment"
            ), mock.patch.object(
                refactor, "smoke_environment", return_value={"HOME": "/tmp"}
            ), mock.patch.object(
                refactor, "run_command", side_effect=fake_run
            ), mock.patch.object(
                refactor, "verify_dut_source_bindings"
            ), mock.patch.object(refactor, "print_report"):
                self.assertEqual(1, refactor.command_rtl_smoke(args))

            self.assertEqual(
                [["./configure.sh", "--run", "func/func_lab19"], ["make", "verilator", "testbench", "soft_compile"]],
                calls,
            )
            self.assertFalse((work / ".rtl-smoke.lock").exists())
            report = refactor.validate_json_file(
                refactor.iteration_report_path(out_dir, iteration_id, "rtl-smoke")
            )
            self.assertEqual("fail", report["verilator_compile_status"])
            self.assertTrue(report["build_errors"])

    def test_smoke_rejects_unlocked_case(self) -> None:
        refactor.require_locked_smoke_case("func/func_lab19")
        with self.assertRaises(refactor.RefactorError):
            refactor.require_locked_smoke_case("not/a/real/case")


class OverlayIntegrityTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, dict[str, object], Path]:
        work = root / "work"
        mycpu = work / "IP" / "myCPU"
        mycpu.mkdir(parents=True)
        rtl = mycpu / "core.v"
        rtl.write_text("module core; endmodule\n", encoding="utf-8")
        license_file = mycpu / "LICENSE"
        license_file.write_text("license\n", encoding="utf-8")
        overlay: dict[str, object] = {
            "files": [
                {
                    "path": "core.v",
                    "overlay_path": "IP/myCPU/core.v",
                    "sha256": refactor.sha256_file(rtl),
                    "overlay_sha256": refactor.sha256_file(rtl),
                    "size": rtl.stat().st_size,
                }
            ],
            "support_files": [
                {
                    "path": "IP/myCPU/LICENSE",
                    "sha256": refactor.sha256_file(license_file),
                    "size": license_file.stat().st_size,
                }
            ],
        }
        return work, overlay, rtl

    def test_pristine_overlay_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, _ = self._fixture(Path(temporary))
            refactor.verify_overlay_files(work, overlay)

    def test_tampered_overlay_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, rtl = self._fixture(Path(temporary))
            rtl.write_text("module changed; endmodule\n", encoding="utf-8")
            with self.assertRaises(refactor.RefactorError):
                refactor.verify_overlay_files(work, overlay)

    def test_unlisted_rtl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, _ = self._fixture(Path(temporary))
            (work / "IP" / "myCPU" / "extra.v").write_text(
                "module extra; endmodule\n", encoding="utf-8"
            )
            with self.assertRaises(refactor.RefactorError):
                refactor.verify_overlay_files(work, overlay)

    def test_nested_unlisted_rtl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, _ = self._fixture(Path(temporary))
            nested = work / "IP" / "myCPU" / "nested"
            nested.mkdir()
            (nested / "extra.v").write_text(
                "module extra; endmodule\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(refactor.RefactorError, "unexpected or missing DUT HDL"):
                refactor.verify_overlay_files(work, overlay)

    def test_same_basename_at_noncanonical_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, _ = self._fixture(Path(temporary))
            overlay["files"][0]["overlay_path"] = "IP/myCPU/nested/core.v"
            with self.assertRaisesRegex(refactor.RefactorError, "canonical DUT target"):
                refactor.verify_overlay_files(work, overlay)

    def test_backslash_in_logical_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, _ = self._fixture(Path(temporary))
            overlay["files"][0]["path"] = "nested\\core.v"
            overlay["files"][0]["overlay_path"] = "IP/myCPU/nested\\core.v"
            with self.assertRaisesRegex(refactor.RefactorError, "canonical DUT target"):
                refactor.verify_overlay_files(work, overlay)

    def test_overlay_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, rtl = self._fixture(Path(temporary))
            path_type = type(rtl)
            original = path_type.is_symlink

            def pretend_target_is_symlink(path: Path) -> bool:
                return path == rtl or original(path)

            with mock.patch.object(
                path_type, "is_symlink", autospec=True, side_effect=pretend_target_is_symlink
            ), self.assertRaisesRegex(refactor.RefactorError, "must not be a symlink"):
                refactor.verify_overlay_files(work, overlay)

    def test_extra_rtl_cannot_be_smuggled_as_support_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, _ = self._fixture(Path(temporary))
            evil = work / "IP" / "myCPU" / "evil.v"
            evil.write_text("module evil; endmodule\n", encoding="utf-8")
            overlay["support_files"].append(
                {
                    "path": "IP/myCPU/evil.v",
                    "sha256": refactor.sha256_file(evil),
                    "size": evil.stat().st_size,
                }
            )
            with self.assertRaisesRegex(refactor.RefactorError, "unapproved support file"):
                refactor.verify_overlay_files(work, overlay)


class ComponentReplacementValidationTests(unittest.TestCase):
    BASE_HEAD = "a" * 40
    SOURCE_HEAD = "b" * 40
    SPEC_PATH = "reference/component-replacements/identity.json"
    SOURCE_PATH = "tests/fixtures/component-overlay/icache.v"
    TARGET_PATH = "rtl/icache.v"
    BASE_PAYLOAD = b"module icache; endmodule\n"
    REPLACEMENT_PAYLOAD = b'`include "mycpu.h"\nmodule icache; endmodule\n'

    def _git_in(self, repo: Path, *args: str) -> str:
        result = refactor.run_command(["git", *args], cwd=repo)
        self.assertEqual(0, result.exit_code, result.stderr)
        return result.stdout.strip()

    def _new_source_repo(self) -> tuple[Path, str, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name)
        self._git_in(repo, "init", "-b", "refactor/eol-provenance-test")
        self._git_in(repo, "config", "user.name", "Refactor Test")
        self._git_in(repo, "config", "user.email", "refactor@example.invalid")
        self._git_in(repo, "config", "core.autocrlf", "false")
        source = repo / "rtl" / "icache.v"
        source.parent.mkdir()
        source.write_bytes(b"module icache;\nendmodule\n")
        self._git_in(repo, "add", "rtl/icache.v")
        self._git_in(repo, "commit", "-m", "fixture")
        return repo, self._git_in(repo, "rev-parse", "HEAD"), source

    def _spec(self, **entry_updates: object) -> bytes:
        entry: dict[str, object] = {
            "target": self.TARGET_PATH,
            "source": self.SOURCE_PATH,
            "base_sha256": refactor.sha256_bytes(self.BASE_PAYLOAD),
            "replacement_sha256": refactor.sha256_bytes(self.REPLACEMENT_PAYLOAD),
        }
        entry.update(entry_updates)
        return (
            json.dumps({"schema_version": 1, "replacements": [entry]}, sort_keys=True)
            + "\n"
        ).encode("utf-8")

    def _load(
        self,
        spec_payload: bytes | None = None,
        *,
        source_state_updates: dict[str, object] | None = None,
    ) -> refactor.ComponentReplacementPlan:
        payload = spec_payload if spec_payload is not None else self._spec()

        def blob(revision: str) -> bytes:
            values = {
                f"{self.SOURCE_HEAD}:{self.SPEC_PATH}": payload,
                f"{self.BASE_HEAD}:{self.TARGET_PATH}": self.BASE_PAYLOAD,
                f"{self.SOURCE_HEAD}:{self.SOURCE_PATH}": self.REPLACEMENT_PAYLOAD,
            }
            if revision not in values:
                raise AssertionError(f"unexpected blob read: {revision}")
            return values[revision]

        def tree_entry(commit: str, path: str) -> dict[str, str]:
            if (commit, path) == (self.SOURCE_HEAD, self.SPEC_PATH):
                payload_for_oid = payload
            elif (commit, path) == (self.SOURCE_HEAD, self.SOURCE_PATH):
                payload_for_oid = self.REPLACEMENT_PAYLOAD
            else:
                raise AssertionError(f"unexpected tree read: {commit}:{path}")
            return {
                "mode": "100644",
                "type": "blob",
                "oid": refactor.sha256_bytes(payload_for_oid)[:40],
                "path": path,
            }

        state = {
            "head": self.SOURCE_HEAD,
            "tree": "c" * 40,
            "branch": "refactor/component-overlay-test",
            "status_entry_count": 0,
            "porcelain_clean": True,
            "semantic_clean": True,
            "eol_normalization_only": False,
        }
        if source_state_updates is not None:
            state.update(source_state_updates)
        with mock.patch.object(
            refactor, "parse_lock", return_value={"team_golden_candidate": self.BASE_HEAD}
        ), mock.patch.object(
            refactor, "read_golden_files", return_value=[self.TARGET_PATH]
        ), mock.patch.object(
            refactor, "require_clean_source_head", return_value=state
        ), mock.patch.object(
            refactor, "git_blob", side_effect=blob
        ), mock.patch.object(
            refactor, "git_regular_blob_entry", side_effect=tree_entry
        ):
            return refactor.load_component_replacement_plan(
                self.SPEC_PATH, self.SOURCE_HEAD
            )

    def test_accepts_canonical_repo_relative_path(self) -> None:
        self.assertEqual(
            "reference/component-replacements/icache.v",
            refactor.checked_repo_git_path(
                "reference/component-replacements/icache.v", "source"
            ),
        )

    def test_overlay_source_argument_matrix_is_fail_closed(self) -> None:
        valid = SimpleNamespace(
            dut_source="mixed",
            diagnostic=True,
            replacement_spec=self.SPEC_PATH,
            source_head=self.SOURCE_HEAD,
            candidate_commit=None,
        )
        self.assertEqual(
            (self.SPEC_PATH, self.SOURCE_HEAD),
            refactor.validate_overlay_source_selection(valid),
        )
        invalid = (
            SimpleNamespace(**{**vars(valid), "source_head": None}),
            SimpleNamespace(**{**vars(valid), "replacement_spec": None}),
            SimpleNamespace(**{**vars(valid), "diagnostic": False}),
            SimpleNamespace(**{**vars(valid), "candidate_commit": "a" * 40}),
            SimpleNamespace(**{**vars(valid), "dut_source": "candidate"}),
            SimpleNamespace(**{**vars(valid), "dut_source": "official"}),
            SimpleNamespace(
                dut_source="official",
                diagnostic=False,
                replacement_spec=None,
                source_head=None,
                candidate_commit=None,
            ),
            SimpleNamespace(
                dut_source="candidate",
                diagnostic=False,
                replacement_spec=None,
                source_head=None,
                candidate_commit="a" * 40,
            ),
        )
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(refactor.RefactorError):
                refactor.validate_overlay_source_selection(args)

    def test_rejects_noncanonical_or_escaping_paths(self) -> None:
        invalid = (
            "../icache.v",
            "reference/../icache.v",
            "reference//icache.v",
            "reference/./icache.v",
            "/reference/icache.v",
            "reference\\icache.v",
            ":(literal)reference/icache.v",
            "reference/icache.v\nother",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(refactor.RefactorError):
                refactor.checked_repo_git_path(value, "source")

    def test_replacement_allows_only_literal_mycpu_header(self) -> None:
        refactor.validate_replacement_verilog(
            b'`include "mycpu.h"\nmodule icache; endmodule\n', "icache.v"
        )
        refactor.validate_replacement_verilog(
            b'// $display("ignored"); $finish;\nmodule icache; '
            b'localparam [8*8-1:0] NOTE = "$warning in text"; '
            b'localparam WIDTH = $clog2(16); '
            b'wire signed [7:0] converted = $signed($unsigned(8\'h80)); '
            b'localparam VALUE_BITS = $bits(converted); endmodule\n',
            "icache.v",
        )
        invalid = (
            b'`include "../mycpu.h"\n',
            b'`include HEADER\n',
            b'`include "extra.vh"\n',
            b'/* verilator lint_off WIDTH */\nmodule icache; endmodule\n',
            b'/* verilator lint_save */\nmodule icache; endmodule\n',
            b'module icache; initial $readmemh("unbound.hex", mem); endmodule\n',
            b'module icache; initial fd = $fopen("unbound.log", "w"); endmodule\n',
            b'import "DPI-C" function int unbound();\n',
            b'`define R $read``memh\nmodule icache; initial `R("/tmp/x.hex", mem); endmodule\n',
            b'`define D "DPI-C"\nimport `D function int unbound();\n',
            b'module icache; initial value = $fgetc(32\'h80000000); endmodule\n',
            b'module icache; initial $writememh("/tmp/x.hex", mem); endmodule\n',
            b'module icache; initial if ($test$plusargs("unsafe")) value = 1; endmodule\n',
            b'`ifdef VERILATOR\nmodule icache; endmodule\n`endif\n',
            b'module icache; initial value = $urandom; endmodule\n',
            b'module icache; initial $dumpfile("unbound.vcd"); endmodule\n',
        )
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(refactor.RefactorError):
                refactor.validate_replacement_verilog(payload, "icache.v")

    def test_replacement_rejects_minimal_forged_pass_oracle(self) -> None:
        payload = (
            b'module icache; initial begin $display("HIT GOOD TRAP"); '
            b'$finish; end endmodule\n'
        )

        with self.assertRaisesRegex(
            refactor.RefactorError, "forbidden oracle-output or simulation-control"
        ):
            refactor.validate_replacement_verilog(payload, "icache.v")

    def test_replacement_rejects_oracle_output_and_simulation_control_tasks(self) -> None:
        forbidden_tasks = (
            "$display",
            "$displayb",
            "$displayh",
            "$displayo",
            "$write",
            "$writeb",
            "$writeh",
            "$writeo",
            "$monitor",
            "$monitorb",
            "$monitorh",
            "$monitoro",
            "$monitoron",
            "$monitoroff",
            "$strobe",
            "$strobeb",
            "$strobeh",
            "$strobeo",
            "$fdisplay",
            "$fdisplayb",
            "$fdisplayh",
            "$fdisplayo",
            "$fwrite",
            "$fwriteb",
            "$fwriteh",
            "$fwriteo",
            "$fmonitor",
            "$fmonitorb",
            "$fmonitorh",
            "$fmonitoro",
            "$fstrobe",
            "$fstrobeb",
            "$fstrobeh",
            "$fstrobeo",
            "$printtimescale",
            "$finish",
            "$finish_and_return",
            "$stop",
            "$fatal",
            "$error",
            "$warning",
            "$info",
            "$exit",
        )
        for task in forbidden_tasks:
            with self.subTest(task=task), self.assertRaisesRegex(
                refactor.RefactorError, task.replace("$", r"\$")
            ):
                refactor.validate_replacement_verilog(
                    f"module icache; initial {task}; endmodule\n".encode("ascii"),
                    "icache.v",
                )

        with self.assertRaisesRegex(refactor.RefactorError, "unapproved system tasks"):
            refactor.validate_replacement_verilog(
                b"module icache; initial $custom_oracle_logger; endmodule\n",
                "icache.v",
            )

    def test_replacement_may_only_reuse_locked_base_macros(self) -> None:
        base = b'`ifdef LACC\nmodule icache; endmodule\n`endif\n'
        refactor.validate_replacement_verilog(
            base, "icache.v", base_payload=base
        )
        with self.assertRaisesRegex(refactor.RefactorError, "unbound macro dependencies"):
            refactor.validate_replacement_verilog(
                b'`ifdef VERILATOR\nmodule icache; endmodule\n`endif\n',
                "icache.v",
                base_payload=base,
            )

    def test_load_plan_binds_base_spec_and_source(self) -> None:
        plan = self._load()
        self.assertEqual(self.BASE_HEAD, plan.base_candidate_commit)
        self.assertEqual(self.SOURCE_HEAD, plan.source_head)
        self.assertEqual(refactor.sha256_bytes(self._spec()), plan.spec_sha256)
        self.assertEqual(1, len(plan.replacements))
        replacement = plan.replacements[0]
        self.assertEqual(self.TARGET_PATH, replacement.target)
        self.assertEqual(self.SOURCE_PATH, replacement.source)
        self.assertEqual(self.REPLACEMENT_PAYLOAD, replacement.payload)
        metadata = plan.metadata()
        self.assertEqual("committed_git_blobs", metadata["replacement_payload_source"])
        self.assertTrue(metadata["worktree_clean"])
        self.assertTrue(metadata["worktree_porcelain_clean"])
        self.assertTrue(metadata["worktree_semantic_clean"])

    def test_metadata_does_not_call_crlf_materialization_clean(self) -> None:
        plan = self._load(
            source_state_updates={
                "status_entry_count": 101,
                "porcelain_clean": False,
                "semantic_clean": True,
                "eol_normalization_only": True,
            }
        )

        metadata = plan.metadata()
        self.assertFalse(metadata["worktree_clean"])
        self.assertFalse(metadata["worktree_porcelain_clean"])
        self.assertTrue(metadata["worktree_semantic_clean"])
        self.assertTrue(metadata["worktree_eol_normalization_only"])
        self.assertEqual(101, metadata["worktree_raw_status_entry_count"])

    def test_load_plan_rejects_unknown_schema_fields(self) -> None:
        document = json.loads(self._spec())
        document["unexpected"] = True
        with self.assertRaisesRegex(refactor.RefactorError, "exactly schema_version"):
            self._load((json.dumps(document) + "\n").encode("utf-8"))

    def test_load_plan_rejects_boolean_or_duplicate_schema_version(self) -> None:
        boolean_schema = self._spec().replace(b'"schema_version": 1', b'"schema_version": true')
        duplicate_schema = self._spec().replace(
            b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1'
        )
        for payload in (boolean_schema, duplicate_schema):
            with self.subTest(payload=payload), self.assertRaises(refactor.RefactorError):
                self._load(payload)

    def test_load_plan_rejects_duplicate_target_or_source(self) -> None:
        document = json.loads(self._spec())
        document["replacements"].append(dict(document["replacements"][0]))
        with self.assertRaisesRegex(refactor.RefactorError, "duplicate target or source"):
            self._load((json.dumps(document) + "\n").encode("utf-8"))

    def test_load_plan_rejects_hash_or_basename_mismatch(self) -> None:
        invalid_specs = (
            self._spec(base_sha256="0" * 64),
            self._spec(replacement_sha256="0" * 64),
            self._spec(source="tests/fixtures/component-overlay/not-icache.v"),
        )
        for payload in invalid_specs:
            with self.subTest(payload=payload), self.assertRaises(refactor.RefactorError):
                self._load(payload)

    def test_requires_exact_clean_refactor_head(self) -> None:
        responses = {
            ("rev-parse", "HEAD"): self.SOURCE_HEAD,
            ("branch", "--show-current"): "refactor/component-overlay-test",
            ("ls-files", "--others", "--exclude-standard"): "",
            ("rev-parse", "HEAD^{tree}"): "c" * 40,
        }

        def git_text(args: list[str], **_: object) -> str:
            return responses[tuple(args)]

        clean_result = refactor.CommandResult([], "test", 0, 0.0, "", "")
        with mock.patch.object(
            refactor, "git_text", side_effect=git_text
        ), mock.patch.object(refactor, "git", return_value=clean_result):
            state = refactor.require_clean_source_head(self.SOURCE_HEAD)
        self.assertEqual(self.SOURCE_HEAD, state["head"])
        self.assertTrue(state["porcelain_clean"])
        self.assertTrue(state["semantic_clean"])

        dirty_result = refactor.CommandResult([], "test", 1, 0.0, "", "")

        def dirty_git(args: list[str], **_: object) -> refactor.CommandResult:
            if args[0] == "status" or "--cached" in args:
                return clean_result
            return dirty_result

        with mock.patch.object(
            refactor, "git_text", side_effect=git_text
        ), mock.patch.object(
            refactor, "git", side_effect=dirty_git
        ), self.assertRaisesRegex(refactor.RefactorError, "non-CRLF"):
            refactor.require_clean_source_head(self.SOURCE_HEAD)

        with self.assertRaisesRegex(refactor.RefactorError, "full lowercase"):
            refactor.require_clean_source_head(self.SOURCE_HEAD.upper())

    def test_source_head_accepts_only_unstaged_crlf_materialization(self) -> None:
        repo, head, source = self._new_source_repo()
        source.write_bytes(b"module icache;\r\nendmodule\r\n")

        state = refactor.require_clean_source_head(head, cwd=repo)

        self.assertFalse(state["porcelain_clean"])
        self.assertTrue(state["semantic_clean"])
        self.assertTrue(state["eol_normalization_only"])
        self.assertEqual(1, state["status_entry_count"])

    def test_source_head_rejects_spaces_or_content_hidden_behind_crlf(self) -> None:
        invalid_payloads = (
            b"module icache; \r\nendmodule\r\n",
            b"module changed;\r\nendmodule\r\n",
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                repo, head, source = self._new_source_repo()
                source.write_bytes(payload)
                with self.assertRaisesRegex(refactor.RefactorError, "non-CRLF"):
                    refactor.require_clean_source_head(head, cwd=repo)

    def test_source_head_rejects_staged_or_untracked_changes(self) -> None:
        repo, head, source = self._new_source_repo()
        source.write_bytes(b"module icache;\r\nendmodule\r\n")
        self._git_in(repo, "add", "rtl/icache.v")
        with self.assertRaisesRegex(refactor.RefactorError, "staged"):
            refactor.require_clean_source_head(head, cwd=repo)

        repo, head, _ = self._new_source_repo()
        (repo / "untracked.v").write_bytes(b"module untracked; endmodule\n")
        with self.assertRaisesRegex(refactor.RefactorError, "untracked"):
            refactor.require_clean_source_head(head, cwd=repo)

    def test_mixed_claim_shape_cannot_be_gate_eligible(self) -> None:
        overlay = {
            "dut_source": "mixed",
            "provenance_mode": "mixed_candidate",
            "gate_kind": "component_replacement",
            "mode": "diagnostic",
            "gate_eligible": True,
            "candidate_locked": False,
            "base_candidate_locked": True,
            "baseline_exact": False,
        }
        with self.assertRaisesRegex(refactor.RefactorError, "gate-eligible"):
            refactor.verify_component_replacement_bindings(
                Path("unused"), overlay, {"team_golden_candidate": "a" * 40}
            )

    def _mixed_binding_fixture(
        self,
    ) -> tuple[refactor.ComponentReplacementPlan, dict[str, object], dict[str, str]]:
        replacement = refactor.ComponentReplacement(
            target=self.TARGET_PATH,
            source=self.SOURCE_PATH,
            base_sha256=refactor.sha256_bytes(self.BASE_PAYLOAD),
            replacement_sha256=refactor.sha256_bytes(self.REPLACEMENT_PAYLOAD),
            source_oid="d" * 40,
            source_mode="100644",
            payload=self.REPLACEMENT_PAYLOAD,
        )
        plan = refactor.ComponentReplacementPlan(
            spec_path=self.SPEC_PATH,
            spec_commit=self.SOURCE_HEAD,
            spec_sha256=refactor.sha256_bytes(self._spec()),
            source_head=self.SOURCE_HEAD,
            source_tree="c" * 40,
            source_branch="refactor/component-overlay-test",
            source_status_entry_count=0,
            source_porcelain_clean=True,
            source_semantic_clean=True,
            source_eol_normalization_only=False,
            base_candidate_commit=self.BASE_HEAD,
            replacements=(replacement,),
        )
        source = f"{self.SOURCE_HEAD}:{self.SOURCE_PATH}"
        selected = {
            "logical_path": self.TARGET_PATH,
            "source": source,
            "sha256": replacement.replacement_sha256,
            "size": len(self.REPLACEMENT_PAYLOAD),
        }
        overlay: dict[str, object] = {
            "dut_source": "mixed",
            "provenance_mode": "mixed_candidate",
            "gate_kind": "component_replacement",
            "mode": "diagnostic",
            "gate_eligible": False,
            "candidate_locked": False,
            "base_candidate_locked": True,
            "baseline_exact": False,
            "golden_candidate_commit": self.BASE_HEAD,
            "component_replacement": plan.metadata(),
            "selection_sha256": refactor.sha256_bytes(
                json.dumps(
                    [selected], sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ),
            "files": [
                {
                    "path": "icache.v",
                    "logical_path": self.TARGET_PATH,
                    "overlay_path": "IP/myCPU/icache.v",
                    "source": source,
                    "source_kind": "replacement",
                    "sha256": replacement.replacement_sha256,
                    "size": len(self.REPLACEMENT_PAYLOAD),
                    "base_source": f"{self.BASE_HEAD}:{self.TARGET_PATH}",
                    "base_sha256": replacement.base_sha256,
                    "base_size": len(self.BASE_PAYLOAD),
                    "base_oid": "e" * 40,
                    "base_mode": "100644",
                    "replacement_source": source,
                    "replacement_source_path": self.SOURCE_PATH,
                    "replacement_oid": replacement.source_oid,
                    "replacement_mode": replacement.source_mode,
                    "replacement_spec_source": f"{self.SOURCE_HEAD}:{self.SPEC_PATH}",
                    "replacement_spec_sha256": plan.spec_sha256,
                }
            ],
        }
        return plan, overlay, {"team_golden_candidate": self.BASE_HEAD}

    def test_mixed_binding_recomputes_git_provenance(self) -> None:
        plan, overlay, manifest = self._mixed_binding_fixture()
        with mock.patch.object(
            refactor, "load_component_replacement_plan", return_value=plan
        ), mock.patch.object(
            refactor, "read_golden_files", return_value=[self.TARGET_PATH]
        ), mock.patch.object(
            refactor, "git_blob", return_value=self.BASE_PAYLOAD
        ), mock.patch.object(
            refactor,
            "git_regular_blob_entry",
            return_value={"oid": "e" * 40, "mode": "100644"},
        ), mock.patch.object(refactor, "verify_candidate_support_bindings"):
            refactor.verify_component_replacement_bindings(
                Path("unused"), overlay, manifest
            )

    def test_mixed_binding_rejects_manifest_tampering(self) -> None:
        plan, pristine, manifest = self._mixed_binding_fixture()
        mutations = (
            ("source_kind", "golden"),
            ("replacement_oid", "0" * 40),
            ("replacement_spec_sha256", "0" * 64),
            ("logical_path", "rtl/other.v"),
        )
        for key, value in mutations:
            overlay = copy.deepcopy(pristine)
            overlay["files"][0][key] = value
            with self.subTest(key=key), mock.patch.object(
                refactor, "load_component_replacement_plan", return_value=plan
            ), mock.patch.object(
                refactor, "read_golden_files", return_value=[self.TARGET_PATH]
            ), mock.patch.object(
                refactor, "git_blob", return_value=self.BASE_PAYLOAD
            ), mock.patch.object(
                refactor,
                "git_regular_blob_entry",
                return_value={"oid": "e" * 40, "mode": "100644"},
            ), mock.patch.object(
                refactor, "verify_candidate_support_bindings"
            ), self.assertRaises(refactor.RefactorError):
                refactor.verify_component_replacement_bindings(
                    Path("unused"), overlay, manifest
                )

        overlay = copy.deepcopy(pristine)
        overlay["selection_sha256"] = "0" * 64
        with mock.patch.object(
            refactor, "load_component_replacement_plan", return_value=plan
        ), mock.patch.object(
            refactor, "read_golden_files", return_value=[self.TARGET_PATH]
        ), mock.patch.object(
            refactor, "git_blob", return_value=self.BASE_PAYLOAD
        ), mock.patch.object(
            refactor,
            "git_regular_blob_entry",
            return_value={"oid": "e" * 40, "mode": "100644"},
        ), mock.patch.object(
            refactor, "verify_candidate_support_bindings"
        ), self.assertRaisesRegex(refactor.RefactorError, "selection hash"):
            refactor.verify_component_replacement_bindings(
                Path("unused"), overlay, manifest
            )


if __name__ == "__main__":
    unittest.main()
