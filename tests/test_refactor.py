from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

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
            refactor.write_json(overlay_report, {"fixture": True})
            overlay = {
                "gate_eligible": True,
                "dut_source": "candidate",
                "golden_candidate_commit": "a" * 40,
                "candidate_locked": True,
            }
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
                diagnostic=False,
                doctor_max_age_seconds=3600,
                configure_timeout=10,
                build_timeout=10,
                sim_timeout=10,
            )
            with mock.patch.object(
                refactor,
                "verify_overlay_integrity",
                return_value=(work, overlay, {}, "d" * 64),
            ), mock.patch.object(
                refactor, "require_posix_validation_environment"
            ), mock.patch.object(
                refactor, "smoke_environment", return_value={"HOME": "/tmp"}
            ), mock.patch.object(
                refactor, "run_command", side_effect=fake_run
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


if __name__ == "__main__":
    unittest.main()
