from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import mul_diff


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "reference" / "component-contracts" / "mul.json"
MANIFEST_PATH = ROOT / "reference" / "manifest.lock"
WAIVER_PATH = ROOT / "lint-waivers.yml"
GOLDEN_REF = (
    "a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/mul.v"
)


def command_result(
    stdout: str = "", *, returncode: int = 0, timed_out: bool = False
) -> dict[str, object]:
    return {
        "argv": [],
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_seconds": 0.001,
        "stdout": stdout,
    }


class MulDiffWarningTests(unittest.TestCase):
    def _locked_warning(self) -> dict[str, object]:
        return {
            "rule": mul_diff.EXPECTED_WARNING["rule"],
            "line": mul_diff.EXPECTED_WARNING["line"],
            "message": mul_diff.EXPECTED_WARNING["message"],
        }

    def test_exact_golden_warning_has_one_approved_waiver(self) -> None:
        accepted, approved, error = mul_diff.approved_warning_suppressions(
            WAIVER_PATH,
            golden_ref=GOLDEN_REF,
            golden_sha256=mul_diff.GOLDEN_SHA256,
            warnings=[self._locked_warning()],
        )
        self.assertTrue(accepted)
        self.assertIsNone(error)
        self.assertEqual(["golden-mul-result-carry-width"], [item["id"] for item in approved])

    def test_warning_message_drift_is_not_waived(self) -> None:
        warning = self._locked_warning()
        warning["message"] = "same rule and line, different semantics"
        accepted, approved, error = mul_diff.approved_warning_suppressions(
            WAIVER_PATH,
            golden_ref=GOLDEN_REF,
            golden_sha256=mul_diff.GOLDEN_SHA256,
            warnings=[warning],
        )
        self.assertFalse(accepted)
        self.assertEqual([], approved)
        self.assertIn("message mismatch", str(error))

    def test_wrong_source_hash_is_not_waived(self) -> None:
        accepted, approved, error = mul_diff.approved_warning_suppressions(
            WAIVER_PATH,
            golden_ref=GOLDEN_REF,
            golden_sha256="0" * 64,
            warnings=[self._locked_warning()],
        )
        self.assertFalse(accepted)
        self.assertEqual([], approved)
        self.assertIn("no unique active waiver", str(error))

    def test_duplicate_matching_waivers_are_rejected(self) -> None:
        document = json.loads(WAIVER_PATH.read_text(encoding="utf-8"))
        duplicate = dict(document["waivers"][0])
        duplicate["id"] = "duplicate-id"
        document["waivers"].append(duplicate)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "waivers.yml"
            path.write_text(json.dumps(document), encoding="utf-8")
            accepted, approved, error = mul_diff.approved_warning_suppressions(
                path,
                golden_ref=GOLDEN_REF,
                golden_sha256=mul_diff.GOLDEN_SHA256,
                warnings=[self._locked_warning()],
            )
        self.assertFalse(accepted)
        self.assertEqual([], approved)
        self.assertIn("no unique active waiver", str(error))

    def test_warning_parser_distinguishes_non_golden_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            golden = root / "golden" / "mul.v"
            other = root / "driver" / "mul_diff_driver.cpp"
            text = (
                f"%Warning-WIDTHEXPAND: {golden}:195:54: "
                f"{mul_diff.EXPECTED_WARNING['message']}\n"
                f"%Warning-WIDTH: {other}:9:2: candidate-side warning\n"
            )
            warnings = mul_diff.parse_verilator_warnings(text, golden)
        self.assertEqual(2, len(warnings))
        self.assertTrue(warnings[0]["golden_path_match"])
        self.assertFalse(warnings[1]["golden_path_match"])

    def test_generic_compiler_warning_is_detected(self) -> None:
        text = "driver.cpp:3:7: warning: unused value [-Wunused-value]\n"
        self.assertEqual([text.strip()], mul_diff.generic_warning_lines(text))


class MulDiffParserTests(unittest.TestCase):
    def test_complete_driver_marker_is_parsed(self) -> None:
        parsed = mul_diff.parse_driver_result(
            "MUL_SELF_CHECK_PASS active=4128 directed=32 perturb=4127 "
            "reset_hold=32 edges=4160\n"
        )
        self.assertTrue(parsed["pass_marker"])
        self.assertEqual(4128, parsed["active"])
        self.assertEqual(32, parsed["directed"])
        self.assertEqual(4127, parsed["perturb"])
        self.assertEqual(32, parsed["reset_hold"])
        self.assertEqual(4160, parsed["edges"])
        self.assertIsNone(parsed["first_mismatch"])

    def test_near_miss_marker_is_not_accepted(self) -> None:
        parsed = mul_diff.parse_driver_result(
            "MUL_SELF_CHECK_PASS active=4128 directed=32 skipped=1\n"
        )
        self.assertFalse(parsed["pass_marker"])
        self.assertEqual(0, parsed["active"])

    def test_first_mismatch_is_preserved_even_with_pass_text(self) -> None:
        mismatch = (
            "MUL_MISMATCH kind=active edge=3 index=2 signed=1 "
            "x=0xffffffff y=0x2 expected=0xfffffffffffffffe actual=0x2"
        )
        parsed = mul_diff.parse_driver_result(
            mismatch
            + "\nMUL_SELF_CHECK_PASS active=4128 directed=32 perturb=4127 "
            "reset_hold=32 edges=4160\n"
        )
        self.assertTrue(parsed["pass_marker"])
        self.assertEqual(mismatch, parsed["first_mismatch"])


class MulDiffCliAndToolTests(unittest.TestCase):
    def test_cli_parses_hex_seed_and_explicit_limits(self) -> None:
        args = mul_diff.build_parser().parse_args(
            [
                "golden",
                "--contract",
                str(CONTRACT_PATH),
                "--manifest",
                str(MANIFEST_PATH),
                "--out-dir",
                "out",
                "--vector-count",
                "4096",
                "--seed",
                "0x158aa8",
                "--timeout",
                "7",
            ]
        )
        self.assertEqual(0x158AA8, args.seed)
        self.assertEqual(4096, args.vector_count)
        self.assertEqual(7, args.timeout)

    def test_cli_rejects_vector_count_below_contract_floor(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                str(Path(mul_diff.__file__)),
                "golden",
                "--contract",
                "missing.json",
                "--manifest",
                "missing.lock",
                "--out-dir",
                "unused",
                "--vector-count",
                "4095",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("vector-count must be >=4096", result.stderr)

    def test_cli_requires_isolated_python(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(mul_diff.__file__)), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("requires isolated Python", result.stderr)

    def test_missing_explicit_tool_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "does-not-exist"
            with self.assertRaisesRegex(mul_diff.MulDiffError, "missing or not executable"):
                mul_diff.resolve_executable(str(missing), "verilator")

    def test_tool_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / ("tool.exe" if os.name == "nt" else "tool")
            executable.write_bytes(b"not-the-locked-tool")
            executable.chmod(0o755)
            with self.assertRaisesRegex(mul_diff.MulDiffError, "binary hash differs"):
                mul_diff.checked_executable(
                    {"tool_sha256": "0" * 64},
                    str(executable),
                    "test-tool",
                    "tool_sha256",
                )

    def test_command_timeout_returns_nonzero_and_timeout_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = mul_diff.run_command(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                cwd=Path(temporary),
                timeout=1,
            )
        self.assertEqual(124, result["returncode"])
        self.assertTrue(result["timed_out"])

    def test_output_path_must_be_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "summary.json"
            output.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(mul_diff.MulDiffError, "must be a directory"):
                mul_diff._fresh_output_directory(output)


class MulDiffGoldenFailClosedTests(unittest.TestCase):
    def _args(self, root: Path) -> SimpleNamespace:
        return SimpleNamespace(
            contract=CONTRACT_PATH,
            manifest=MANIFEST_PATH,
            waivers=WAIVER_PATH,
            out_dir=root / "out",
            vector_count=mul_diff.DEFAULT_VECTOR_COUNT,
            seed=mul_diff.DEFAULT_SEED,
            timeout=10,
            verilator=None,
        )

    def _contract_evidence(self) -> dict[str, object]:
        return {
            "contract": {"sha256": "contract"},
            "golden": {"verified": True},
            "protocol": {"latency_edges": 1},
            "ports": {"result": {"width": 64}},
            "stimulus": {
                "seed": f"0x{mul_diff.DEFAULT_SEED:x}",
                "random_vectors": mul_diff.DEFAULT_VECTOR_COUNT,
            },
        }

    def _run_mocked(
        self,
        root: Path,
        *,
        extra_compile_output: str = "",
        compile_timeout: bool = False,
        create_binary: bool = True,
    ) -> tuple[int, dict[str, object]]:
        args = self._args(root)
        tools = {}
        for name in ("verilator", "make", "g++"):
            path = root / name
            path.write_text(name, encoding="ascii")
            path.chmod(0o755)
            tools[name] = path

        def checked_tool(
            values: dict[str, str], value: str | None, name: str, lock_key: str
        ) -> Path:
            del values, value, lock_key
            return tools[name]

        def fake_run(
            argv: list[str],
            *,
            cwd: Path,
            timeout: int,
            environment: dict[str, str] | None = None,
        ) -> dict[str, object]:
            del timeout, environment
            executable = Path(argv[0]).name
            if argv[1:] == ["--version"]:
                version = "Verilator 5.020" if executable == "verilator" else f"{executable} test version"
                return command_result(version + "\n")
            if "--cc" in argv:
                if create_binary:
                    binary = cwd / "obj_dir" / "Vmul"
                    binary.parent.mkdir(parents=True, exist_ok=True)
                    binary.write_bytes(b"mock-verilated-binary")
                golden = cwd / "golden" / "mul.v"
                warning = (
                    f"%Warning-WIDTHEXPAND: {golden}:195:54: "
                    f"{mul_diff.EXPECTED_WARNING['message']}\n"
                )
                return command_result(
                    warning + extra_compile_output,
                    returncode=124 if compile_timeout else 0,
                    timed_out=compile_timeout,
                )
            active = int(argv[2])
            directed = int(argv[3])
            return command_result(
                f"MUL_SELF_CHECK_PASS active={active} directed={directed} "
                f"perturb={active - 1} reset_hold=32 edges={active + 32}\n"
            )

        with mock.patch.object(
            mul_diff, "verify_contract", return_value=self._contract_evidence()
        ), mock.patch.object(
            mul_diff, "checked_executable", side_effect=checked_tool
        ), mock.patch.object(mul_diff, "run_command", side_effect=fake_run):
            return mul_diff.run_golden(args)

    def test_non_golden_verilator_warning_fails_and_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            other = root / "out" / "driver" / "mul_diff_driver.cpp"
            output = f"%Warning-WIDTH: {other}:9:2: candidate-side warning\n"
            code, summary = self._run_mocked(root, extra_compile_output=output)
            persisted = json.loads((root / "out" / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(1, code)
        self.assertEqual("fail", summary["status"])
        self.assertIn("outside the locked golden waiver scope", str(summary["error"]))
        self.assertEqual(1, len(summary["compile"]["non_golden_warnings"]))
        self.assertEqual("fail", persisted["status"])
        self.assertEqual(1, persisted["counts"]["failed"])

    def test_compile_timeout_fails_even_with_expected_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary), compile_timeout=True)
        self.assertEqual(1, code)
        self.assertIn("compile failed or timed out", str(summary["error"]))
        self.assertTrue(summary["compile"]["timed_out"])

    def test_missing_simulation_binary_fails_before_driver(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary), create_binary=False)
        self.assertEqual(1, code)
        self.assertIn("binary artifact is missing", str(summary["error"]))
        self.assertNotIn("simulation", summary)

    def test_expected_warning_and_complete_marker_can_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary))
        self.assertEqual(0, code)
        self.assertEqual("pass", summary["status"])
        self.assertEqual(0, summary["counts"]["failed"])
        self.assertEqual(0, summary["counts"]["skipped"])
        self.assertEqual(summary["counts"]["planned"], summary["counts"]["executed"])


class MulDiffCandidateFailClosedTests(unittest.TestCase):
    def _args(self, root: Path) -> SimpleNamespace:
        candidate = root / "mul.v"
        candidate.write_text("module mul; endmodule\n", encoding="ascii")
        return SimpleNamespace(
            contract=CONTRACT_PATH,
            manifest=MANIFEST_PATH,
            rtl=candidate,
            out_dir=root / "out",
            vector_count=mul_diff.DEFAULT_VECTOR_COUNT,
            seed=mul_diff.DEFAULT_SEED,
            timeout=10,
            verilator=None,
        )

    def _contract_evidence(self) -> dict[str, object]:
        return {
            "contract": {"sha256": "contract"},
            "golden": {"verified": True},
            "protocol": {"latency_edges": 1},
            "ports": {"result": {"width": 64}},
            "stimulus": {
                "seed": f"0x{mul_diff.DEFAULT_SEED:x}",
                "random_vectors": mul_diff.DEFAULT_VECTOR_COUNT,
            },
        }

    def _run_mocked(
        self,
        root: Path,
        *,
        extra_compile_output: str = "",
        compile_timeout: bool = False,
        create_binary: bool = True,
        simulation_output: str | None = None,
        tamper_source: bool = False,
    ) -> tuple[int, dict[str, object]]:
        args = self._args(root)
        tools = {}
        for name in ("verilator", "make", "g++"):
            path = root / name
            path.write_text(name, encoding="ascii")
            path.chmod(0o755)
            tools[name] = path
        observed_compile: list[str] = []

        def checked_tool(
            values: dict[str, str], value: str | None, name: str, lock_key: str
        ) -> Path:
            del values, value, lock_key
            return tools[name]

        def fake_run(
            argv: list[str],
            *,
            cwd: Path,
            timeout: int,
            environment: dict[str, str] | None = None,
        ) -> dict[str, object]:
            del timeout, environment
            executable = Path(argv[0]).name
            if argv[1:] == ["--version"]:
                version = "Verilator 5.020" if executable == "verilator" else f"{executable} test version"
                return command_result(version + "\n")
            if "--cc" in argv:
                observed_compile.extend(argv)
                if tamper_source:
                    args.rtl.write_text("module mul; wire tampered; endmodule\n", encoding="ascii")
                if create_binary:
                    binary = cwd / "obj_dir" / "Vmul"
                    binary.parent.mkdir(parents=True, exist_ok=True)
                    binary.write_bytes(b"mock-verilated-binary")
                return command_result(
                    extra_compile_output,
                    returncode=124 if compile_timeout else 0,
                    timed_out=compile_timeout,
                )
            if simulation_output is not None:
                return command_result(simulation_output)
            active = int(argv[2])
            directed = int(argv[3])
            return command_result(
                f"MUL_SELF_CHECK_PASS active={active} directed={directed} "
                f"perturb={active - 1} reset_hold=32 edges={active + 32}\n"
            )

        with mock.patch.object(
            mul_diff, "verify_contract", return_value=self._contract_evidence()
        ), mock.patch.object(
            mul_diff, "checked_executable", side_effect=checked_tool
        ), mock.patch.object(mul_diff, "run_command", side_effect=fake_run):
            code, summary = mul_diff.run_candidate(args)
        summary["_observed_compile"] = observed_compile
        return code, summary

    def test_candidate_pass_records_hash_and_wall(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary))
        self.assertEqual(0, code)
        self.assertEqual("pass", summary["status"])
        self.assertTrue(summary["candidate"]["source_stable"])
        self.assertEqual(summary["candidate"]["sha256_before"], summary["candidate"]["sha256_after"])
        self.assertIn("-Wall", summary["_observed_compile"])
        self.assertIn("--Wno-fatal", summary["_observed_compile"])
        self.assertEqual(0, summary["compile"]["warning_count"])
        self.assertEqual(0, summary["counts"]["skipped"])

    def test_candidate_warning_is_never_waived(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "mul.v"
            output = f"%Warning-WIDTH: {candidate}:1:2: candidate warning\n"
            code, summary = self._run_mocked(root, extra_compile_output=output)
        self.assertEqual(1, code)
        self.assertEqual("fail", summary["status"])
        self.assertIn("emitted a warning", str(summary["error"]))
        self.assertEqual(1, summary["compile"]["warning_count"])
        self.assertEqual(1, summary["counts"]["failed"])

    def test_missing_candidate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = self._args(root)
            args.rtl.unlink()
            with mock.patch.object(mul_diff, "verify_contract", return_value=self._contract_evidence()):
                code, summary = mul_diff.run_candidate(args)
        self.assertEqual(1, code)
        self.assertEqual("fail", summary["status"])
        self.assertIn("regular file", str(summary["error"]))

    def test_source_tamper_during_compile_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary), tamper_source=True)
        self.assertEqual(1, code)
        self.assertIn("changed during compilation", str(summary["error"]))
        self.assertFalse(summary["candidate"]["source_stable"])

    def test_missing_candidate_binary_fails_before_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary), create_binary=False)
        self.assertEqual(1, code)
        self.assertIn("binary artifact is missing", str(summary["error"]))
        self.assertNotIn("simulation", summary)

    def test_candidate_mismatch_and_skip_are_failures(self) -> None:
        mismatch = (
            "MUL_MISMATCH kind=active edge=1 index=0 signed=0 x=0x00000000 "
            "y=0x00000000 expected=0x0000000000000000 actual=0x1\n"
            "MUL_SELF_CHECK_PASS active=4128 directed=32 perturb=4127 reset_hold=32 edges=4160\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary), simulation_output=mismatch)
        self.assertEqual(1, code)
        self.assertIn("MUL_MISMATCH", str(summary["error"]))

        with tempfile.TemporaryDirectory() as temporary:
            skipped = "SKIP candidate\n"
            code, summary = self._run_mocked(Path(temporary), simulation_output=skipped)
        self.assertEqual(1, code)
        self.assertIn("SKIP", str(summary["error"]))


if __name__ == "__main__":
    unittest.main()
