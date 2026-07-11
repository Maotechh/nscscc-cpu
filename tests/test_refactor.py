from __future__ import annotations

import copy
import json
import os
import stat
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
    TOOL_ROOT = "/opt/component tools"

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

    def _identity_dry_run(self) -> refactor.CommandResult:
        return refactor.run_command(
            [
                "make",
                "-n",
                "OUT_DIR=/tmp/component evidence",
                "CHIPLAB_REFERENCE=/opt/chiplab-reference",
                f"CHIPLAB_WORK_ROOT={self.WORK_ROOT}",
                f"CHIPLAB_TOOL_ROOT={self.TOOL_ROOT}",
                "LOCKED_ITERATION_ID=locked-control",
                "MIXED_ITERATION_ID=mixed-control",
                "identity-compare",
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

    def test_identity_compare_forwards_all_locked_roots_and_ids(self) -> None:
        result = self._identity_dry_run()
        self.assertEqual(0, result.exit_code, result.stderr)
        self.assertIn('--out-dir "/tmp/component evidence"', result.stdout)
        self.assertIn(f'--work-root "{self.WORK_ROOT}"', result.stdout)
        self.assertIn('--chiplab-ref "/opt/chiplab-reference"', result.stdout)
        self.assertIn(f'--tool-root "{self.TOOL_ROOT}"', result.stdout)
        self.assertIn('--locked-iteration-id "locked-control"', result.stdout)
        self.assertIn('--mixed-iteration-id "mixed-control"', result.stdout)
        self.assertNotIn("--output", result.stdout)


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


class AtomicJsonWriteTests(unittest.TestCase):
    def test_uses_unique_exclusive_regular_temporaries_without_fixed_tmp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "report.json"
            fixed_temporary = target.with_suffix(target.suffix + ".tmp")
            fixed_temporary.write_text("do-not-touch\n", encoding="utf-8")
            observed_names: list[str] = []
            observed_flags: list[int] = []
            if os.name == "posix":
                real_open = os.open

                def observe_open(path: object, flags: int, *args: object, **kwargs: object):
                    if isinstance(path, str) and path.startswith(f".{target.name}."):
                        observed_names.append(path)
                        observed_flags.append(flags)
                    return real_open(path, flags, *args, **kwargs)

                patcher = mock.patch.object(
                    refactor.os, "open", side_effect=observe_open
                )
            else:
                real_factory = tempfile.NamedTemporaryFile

                def observe_temporary(*args: object, **kwargs: object):
                    handle = real_factory(*args, **kwargs)
                    observed_names.append(Path(handle.name).name)
                    observed_flags.append(os.O_EXCL)
                    return handle

                patcher = mock.patch.object(
                    refactor.tempfile,
                    "NamedTemporaryFile",
                    side_effect=observe_temporary,
                )

            with patcher:
                refactor.write_json(target, {"generation": 1})
                refactor.write_json(target, {"generation": 2})

            self.assertEqual({"generation": 2}, json.loads(target.read_text(encoding="utf-8")))
            self.assertTrue(stat.S_ISREG(target.lstat().st_mode))
            self.assertFalse(target.is_symlink())
            self.assertEqual("do-not-touch\n", fixed_temporary.read_text(encoding="utf-8"))
            self.assertEqual(2, len(observed_names))
            self.assertEqual(2, len(set(observed_names)))
            self.assertNotIn(fixed_temporary.name, observed_names)
            self.assertTrue(all(flags & os.O_EXCL for flags in observed_flags))
            self.assertFalse(
                any(
                    path.name.startswith(f".{target.name}.")
                    and path.name.endswith(".tmp")
                    for path in root.iterdir()
                )
            )

    def test_rejects_symlink_output_target_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            victim = root / "victim.json"
            victim.write_text('{"unchanged": true}\n', encoding="utf-8")
            target = root / "report.json"
            try:
                target.symlink_to(victim)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"filesystem cannot create a file symlink: {error}")

            with self.assertRaisesRegex(refactor.RefactorError, "symlink or junction"):
                refactor.write_json(target, {"unchanged": False})

            self.assertEqual('{"unchanged": true}\n', victim.read_text(encoding="utf-8"))
            self.assertTrue(target.is_symlink())

    def test_rejects_symlink_parent_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_parent = root / "real-parent"
            real_parent.mkdir()
            linked_parent = root / "linked-parent"
            try:
                linked_parent.symlink_to(real_parent, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"filesystem cannot create a directory symlink: {error}")

            with self.assertRaisesRegex(refactor.RefactorError, "symlink or junction"):
                refactor.write_json(linked_parent / "report.json", {"status": "pass"})

            self.assertFalse((real_parent / "report.json").exists())

    def test_checked_out_dir_rejects_symlink_root_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_output = root / "real-output"
            real_output.mkdir()
            linked_output = root / "linked-output"
            try:
                linked_output.symlink_to(real_output, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"filesystem cannot create a directory symlink: {error}")

            with self.assertRaisesRegex(refactor.RefactorError, "generated OUT_DIR"):
                refactor.checked_out_dir(linked_output)

    @unittest.skipUnless(os.name == "posix", "requires POSIX dir_fd rename semantics")
    def test_parent_swap_cannot_redirect_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            parent.mkdir()
            moved = root / "moved-parent"
            external = root / "external"
            external.mkdir()
            victim = external / "report.json"
            victim.write_text("unchanged\n", encoding="utf-8")
            target = parent / "report.json"
            real_replace = os.replace

            def swap_parent(*args: object, **kwargs: object) -> None:
                parent.rename(moved)
                parent.symlink_to(external, target_is_directory=True)
                real_replace(*args, **kwargs)

            with mock.patch.object(
                refactor.os, "replace", side_effect=swap_parent
            ), self.assertRaisesRegex(refactor.RefactorError, "parent changed"):
                refactor.write_json(target, {"status": "forged"})

            self.assertEqual("unchanged\n", victim.read_text(encoding="utf-8"))
            self.assertFalse((moved / "report.json").exists())

    @unittest.skipUnless(os.name == "posix", "requires POSIX directory fsync")
    def test_directory_fsync_failure_removes_published_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "report.json"
            real_fsync = os.fsync
            calls = 0

            def fail_directory_fsync(descriptor: int) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("forced directory fsync failure")
                real_fsync(descriptor)

            with mock.patch.object(
                refactor.os, "fsync", side_effect=fail_directory_fsync
            ), self.assertRaisesRegex(OSError, "forced directory fsync failure"):
                refactor.write_json(target, {"status": "pass"})

            self.assertFalse(target.exists())


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
                fresh_ns = started_ns + 1_000_000_000
                os.utime(path, ns=(fresh_ns, fresh_ns))
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
            refactor.release_validation_lock(lock)

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
            refactor.release_validation_lock(lock)

    def test_old_owner_cannot_remove_replacement_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary)
            old = refactor.acquire_iteration_lock(
                out_dir, "20260711-lock-owner", "rtl-smoke", "old-run"
            )
            try:
                old.path.unlink()
            except OSError as error:
                refactor.abandon_validation_lock(old)
                self.skipTest(f"filesystem does not permit replacing an open lock: {error}")
            replacement = refactor.acquire_iteration_lock(
                out_dir, "20260711-lock-owner", "rtl-smoke", "new-run"
            )
            with self.assertRaisesRegex(refactor.RefactorError, "ownership changed"):
                refactor.release_validation_lock(old)
            self.assertTrue(replacement.path.is_file())
            refactor.release_validation_lock(replacement)

    def test_failed_lock_write_removes_only_partial_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary)
            lock_path = (
                out_dir / ".locks" / "iterations" / "20260711-partial-lock.lock"
            )
            with mock.patch.object(
                refactor, "_write_all", side_effect=OSError("simulated ENOSPC")
            ), self.assertRaisesRegex(OSError, "simulated ENOSPC"):
                refactor.acquire_iteration_lock(
                    out_dir,
                    "20260711-partial-lock",
                    "rtl-smoke",
                    "partial-run",
                )
            self.assertFalse(lock_path.exists())

    def test_release_all_continues_after_keyboard_interrupt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = refactor.acquire_iteration_lock(
                root / "one", "20260712-release-all", "rtl-smoke", "run-one"
            )
            second = refactor.acquire_iteration_lock(
                root / "two", "20260712-release-all", "rtl-smoke", "run-two"
            )
            real_release = refactor.release_validation_lock
            release_count = 0

            def interrupt_after_release(lock: refactor.ValidationLock) -> None:
                nonlocal release_count
                release_count += 1
                real_release(lock)
                if release_count == 1:
                    raise KeyboardInterrupt("simulated interrupt")

            with mock.patch.object(
                refactor,
                "release_validation_lock",
                side_effect=interrupt_after_release,
            ), self.assertRaises(KeyboardInterrupt):
                refactor.release_validation_locks([first, second])

            self.assertEqual(2, release_count)
            self.assertFalse(first.path.exists())
            self.assertFalse(second.path.exists())

    def test_publication_marker_is_required_and_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            iteration_id = "20260712-publication-marker"
            report_path = refactor.iteration_report_path(
                root, iteration_id, "rtl-smoke"
            )
            report = {
                "command": "rtl-smoke",
                "iteration_id": iteration_id,
                "run_id": "fixture-publication",
                "status": "pass",
            }
            publisher_sha = "a" * 64
            refactor.write_json(report_path, report)
            report_sha = refactor.sha256_file(report_path)

            with self.assertRaisesRegex(refactor.RefactorError, "invalid JSON"):
                refactor.require_report_publication(
                    report_path,
                    report,
                    report_sha,
                    command="rtl-smoke",
                    iteration_id=iteration_id,
                    publication_id="fixture-publication",
                    publisher_sha256=publisher_sha,
                )

            marker_path, _ = refactor.write_publication_marker(
                report_path,
                report,
                command="rtl-smoke",
                iteration_id=iteration_id,
                publication_id="fixture-publication",
                publisher_sha256=publisher_sha,
            )
            refactor.require_report_publication(
                report_path,
                report,
                report_sha,
                command="rtl-smoke",
                iteration_id=iteration_id,
                publication_id="fixture-publication",
                publisher_sha256=publisher_sha,
            )
            marker = refactor.validate_json_file(marker_path)
            marker["report_sha256"] = "b" * 64
            refactor.write_json(marker_path, marker)
            with self.assertRaisesRegex(refactor.RefactorError, "marker mismatch"):
                refactor.require_report_publication(
                    report_path,
                    report,
                    report_sha,
                    command="rtl-smoke",
                    iteration_id=iteration_id,
                    publication_id="fixture-publication",
                    publisher_sha256=publisher_sha,
                )

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
            self.assertFalse(refactor.publication_marker_path(stale).exists())
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

    def test_overlay_error_after_real_release_keeps_published_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_dir = root / "out"
            work_root = root / "work-root"
            iteration_id = "20260712-overlay-release-test"
            report_path = refactor.iteration_report_path(
                out_dir, iteration_id, "chiplab-overlay"
            )
            args = SimpleNamespace(
                out_dir=str(out_dir),
                work_root=str(work_root),
                iteration_id=iteration_id,
            )

            def publish(_: SimpleNamespace, run_id: str) -> int:
                report = {
                    "command": "chiplab-overlay",
                    "status": "pass",
                    "run_id": run_id,
                }
                refactor.write_json(report_path, report)
                refactor.write_publication_marker(
                    report_path,
                    report,
                    command="chiplab-overlay",
                    iteration_id=iteration_id,
                    publication_id=run_id,
                    publisher_sha256=refactor.sha256_file(Path(refactor.__file__)),
                )
                return 0

            real_release = refactor.release_validation_lock
            release_count = 0

            def release_then_fail_once(lock: refactor.ValidationLock) -> None:
                nonlocal release_count
                release_count += 1
                real_release(lock)
                if release_count == 1:
                    raise refactor.RefactorError("simulated overlay release failure")

            printer = mock.Mock()
            with mock.patch.object(
                refactor, "_command_chiplab_overlay_locked", side_effect=publish
            ), mock.patch.object(
                refactor,
                "release_validation_lock",
                side_effect=release_then_fail_once,
            ), mock.patch.object(
                refactor, "print_report", printer
            ), self.assertRaisesRegex(refactor.RefactorError, "validation lock release failed"):
                refactor.command_chiplab_overlay(args)

            self.assertEqual(2, release_count)
            self.assertTrue(report_path.is_file())
            self.assertTrue(refactor.publication_marker_path(report_path).is_file())
            printer.assert_not_called()
            for root_path in (out_dir, work_root):
                self.assertFalse(
                    (
                        root_path
                        / ".locks"
                        / "iterations"
                        / f"{iteration_id}.lock"
                    ).exists()
                )

    def test_smoke_error_after_real_release_keeps_published_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_dir = root / "out"
            work_root = root / "work-root"
            iteration_id = "20260712-smoke-release-test"
            report_path = refactor.iteration_report_path(
                out_dir, iteration_id, "rtl-smoke"
            )
            args = SimpleNamespace(
                out_dir=str(out_dir),
                work_root=str(work_root),
                iteration_id=iteration_id,
            )

            def publish(_: SimpleNamespace) -> int:
                report = {
                    "command": "rtl-smoke",
                    "status": "pass",
                    "run_id": "fixture-smoke",
                }
                refactor.write_json(report_path, report)
                refactor.write_publication_marker(
                    report_path,
                    report,
                    command="rtl-smoke",
                    iteration_id=iteration_id,
                    publication_id="fixture-smoke",
                    publisher_sha256=refactor.sha256_file(Path(refactor.__file__)),
                )
                return 0

            real_release = refactor.release_validation_lock
            release_count = 0

            def release_then_fail_once(lock: refactor.ValidationLock) -> None:
                nonlocal release_count
                release_count += 1
                real_release(lock)
                if release_count == 1:
                    raise refactor.RefactorError("simulated smoke release failure")

            printer = mock.Mock()
            with mock.patch.object(
                refactor, "_command_rtl_smoke_locked", side_effect=publish
            ), mock.patch.object(
                refactor,
                "release_validation_lock",
                side_effect=release_then_fail_once,
            ), mock.patch.object(
                refactor, "print_report", printer
            ), self.assertRaisesRegex(refactor.RefactorError, "validation lock release failed"):
                refactor.command_rtl_smoke(args)

            self.assertEqual(2, release_count)
            self.assertTrue(report_path.is_file())
            self.assertTrue(refactor.publication_marker_path(report_path).is_file())
            printer.assert_not_called()
            for root_path in (out_dir, work_root):
                self.assertFalse(
                    (
                        root_path
                        / ".locks"
                        / "iterations"
                        / f"{iteration_id}.lock"
                    ).exists()
                )

    def test_overlay_binding_failure_cannot_publish_success_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out_dir = root / "out"
            work_root = root / "work-root"
            chiplab_ref = root / "chiplab-reference"
            tool_root = root / "tools"
            iteration_id = "20260712-overlay-binding-test"
            chiplab_commit = "a" * 40
            mycpu_commit = "b" * 40
            (chiplab_ref / "IP" / "myCPU").mkdir(parents=True)
            for path in (
                tool_root
                / "loongson-gnu-toolchain-8.3-x86_64-loongarch32r-linux-gnusf-v2.0",
                tool_root / "nemu",
                tool_root / "picolibc",
            ):
                path.mkdir(parents=True)
            overlay_report = refactor.iteration_report_path(
                out_dir, iteration_id, "chiplab-overlay"
            )
            refactor.write_json(
                overlay_report, {"status": "pass", "gate_eligible": True}
            )
            work = work_root / iteration_id
            written_paths: list[Path] = []

            def fake_write_json(path: Path, value: object) -> None:
                output = Path(path)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(
                    json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                written_paths.append(output)

            def fake_reset_generated_dir(
                path: Path, allowed_root: Path, purpose: str
            ) -> None:
                self.assertEqual(work, Path(path))
                self.assertEqual(work_root, Path(allowed_root))
                Path(path).mkdir(parents=True)
                (Path(path) / refactor.GENERATED_MARKER).write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "purpose": purpose,
                            "resolved_path": str(Path(path)),
                        }
                    ),
                    encoding="utf-8",
                )

            def fake_run_command(
                command: list[str], **kwargs: object
            ) -> refactor.CommandResult:
                self.assertEqual(["git", "clone"], [str(item) for item in command[:2]])
                mycpu = work / "IP" / "myCPU"
                mycpu.mkdir(parents=True)
                (mycpu / "mycpu_top.v").write_text(
                    "module core_top; endmodule\n", encoding="utf-8"
                )
                (mycpu / "mycpu.h").write_text("// header\n", encoding="utf-8")
                (mycpu / "LICENSE").write_text("license\n", encoding="utf-8")
                return refactor.CommandResult(
                    [str(item) for item in command],
                    str(kwargs["cwd"]),
                    0,
                    0.01,
                    "",
                    "",
                )

            def fake_git_text(command: list[str], *, cwd: Path = refactor.REPO_ROOT) -> str:
                if command == ["status", "--porcelain=v1"]:
                    return ""
                if command == ["rev-parse", "HEAD"]:
                    return (
                        mycpu_commit
                        if Path(cwd) == chiplab_ref / "IP" / "myCPU"
                        else chiplab_commit
                    )
                if command == ["rev-parse", "HEAD^{tree}"]:
                    return "c" * 40
                self.fail(f"unexpected git_text call: {command} cwd={cwd}")

            args = SimpleNamespace(
                out_dir=str(out_dir),
                iteration_id=iteration_id,
                work_root=str(work_root),
                chiplab_ref=str(chiplab_ref),
                tool_root=str(tool_root),
                dut_source="official",
                diagnostic=True,
                replacement_spec=None,
                source_head=None,
                candidate_commit=None,
                doctor_max_age_seconds=3600,
            )
            manifest = {
                "chiplab_commit": chiplab_commit,
                "chiplab_mycpu_gitlink": mycpu_commit,
            }
            success = refactor.CommandResult([], str(root), 0, 0.01, "", "")
            verifier_failure = refactor.RefactorError(
                "intentional DUT binding verification failure"
            )
            print_report = mock.Mock()
            real_is_symlink = Path.is_symlink

            def fake_is_symlink(path: Path) -> bool:
                candidate = Path(path)
                return (
                    "toolchains" in candidate.parts
                    or candidate.as_posix().endswith(
                        "software/examples/func/func_lab19/Makefile"
                    )
                    or real_is_symlink(candidate)
                )

            with mock.patch.object(
                refactor, "os", SimpleNamespace(name="posix")
            ), mock.patch.object(
                refactor, "parse_lock", return_value=manifest
            ), mock.patch.object(
                refactor, "filesystem_type", return_value="ext4"
            ), mock.patch.object(
                refactor, "require_passing_chiplab_doctor",
                return_value=(
                    root / "doctor.json",
                    {"generated_at": "2026-07-12T00:00:00+08:00"},
                    "d" * 64,
                ),
            ), mock.patch.object(
                refactor, "require_tool_fingerprints", return_value={}
            ), mock.patch.object(
                refactor, "reset_generated_dir", side_effect=fake_reset_generated_dir
            ), mock.patch.object(
                refactor, "run_command", side_effect=fake_run_command
            ), mock.patch.object(
                refactor, "git", return_value=success
            ), mock.patch.object(
                refactor, "git_text", side_effect=fake_git_text
            ), mock.patch.object(
                refactor, "ensure_symlink"
            ), mock.patch.object(
                refactor, "official_workspace_fingerprint", return_value={}
            ), mock.patch.object(
                refactor,
                "verify_dut_source_bindings",
                side_effect=[None, verifier_failure],
            ) as verifier, mock.patch.object(
                refactor, "write_json", side_effect=fake_write_json
            ), mock.patch.object(
                Path, "is_symlink", side_effect=fake_is_symlink, autospec=True
            ), mock.patch.object(
                refactor, "print_report", print_report
            ), self.assertRaisesRegex(
                refactor.RefactorError, "intentional DUT binding verification failure"
            ):
                refactor._command_chiplab_overlay_locked(args, "fixture-overlay-run")

            manifest_path = refactor.iteration_report_path(
                out_dir, iteration_id, "chiplab-overlay-manifest"
            )
            self.assertEqual(2, verifier.call_count)
            self.assertIn(manifest_path, written_paths)
            self.assertIn(work / ".refactor-overlay.json", written_paths)
            self.assertNotIn(overlay_report, written_paths)
            self.assertFalse(overlay_report.exists())
            print_report.assert_not_called()

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
                run_dir / "config.log",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("old\n", encoding="utf-8")
            removed = refactor.clean_smoke_generated_paths(
                work, run_dir, "func/func_lab19"
            )
            self.assertEqual(9, len(removed))
            self.assertTrue(all(not path.exists() for path in paths))

    def test_post_smoke_integrity_allows_only_declared_generated_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / "source.txt").write_text("locked\n", encoding="utf-8")
            exclusions = refactor.smoke_generated_relative_paths(
                refactor.LOCKED_SMOKE_CASE
            )
            expected = refactor.official_workspace_fingerprint(
                work, extra_excluded_paths=exclusions
            )
            for relative in exclusions:
                generated = work / Path(relative)
                if generated.suffix or generated.name in {"output", "config-software.mak"}:
                    generated.parent.mkdir(parents=True, exist_ok=True)
                    generated.write_text("generated\n", encoding="utf-8")
                else:
                    generated.mkdir(parents=True, exist_ok=True)
                    (generated / "generated.bin").write_bytes(b"generated\n")
            (work / ".rtl-smoke.lock").write_text("{}\n", encoding="utf-8")
            clean = refactor.CommandResult(["git"], str(work), 0, 0.01, "", "")
            with mock.patch.object(refactor, "git", return_value=clean):
                refactor.require_post_smoke_official_integrity(
                    work, expected, refactor.LOCKED_SMOKE_CASE
                )
                (work / "unexpected.bin").write_bytes(b"unexpected\n")
                with self.assertRaisesRegex(
                    refactor.RefactorError, "outside the smoke generated-path contract"
                ):
                    refactor.require_post_smoke_official_integrity(
                        work, expected, refactor.LOCKED_SMOKE_CASE
                    )

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
                    fresh_ns = time.time_ns() + 1_000_000_000
                    os.utime(compile_log, ns=(fresh_ns, fresh_ns))
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
            ), mock.patch.object(
                refactor, "require_post_smoke_official_integrity"
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

    def test_unlisted_systemverilog_header_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work, overlay, _ = self._fixture(Path(temporary))
            (work / "IP" / "myCPU" / "evil.svh").write_text(
                "`define FORGED_ORACLE 1\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                refactor.RefactorError, "unexpected or missing DUT HDL"
            ):
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
