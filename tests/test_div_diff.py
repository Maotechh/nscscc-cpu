#!/usr/bin/env python3
"""Focused tests for the fail-closed divider golden harness."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import div_diff  # noqa: E402


class DivModelTests(unittest.TestCase):
    def test_signed_unsigned_and_zero_division(self) -> None:
        self.assertEqual((3, 1), div_diff.mathematical_division(0, 10, 3))
        self.assertEqual((3, 1), div_diff.mathematical_division(1, 10, 3))
        self.assertEqual((0xFFFFFFFD, 0xFFFFFFFF), div_diff.mathematical_division(1, 0xFFFFFFF6, 3))
        self.assertEqual((0xFFFFFFFF, 0x80000000), div_diff.mathematical_division(0, 0x80000000, 0))
        self.assertEqual((1, 0x80000000), div_diff.mathematical_division(1, 0x80000000, 0))
        self.assertEqual((0x80000000, 0), div_diff.mathematical_division(1, 0x80000000, 0xFFFFFFFF))

    def test_vectors_force_both_modes_and_zero(self) -> None:
        vectors, directed = div_diff.make_vectors(div_diff.DEFAULT_SEED, div_diff.DEFAULT_VECTOR_COUNT)
        self.assertGreater(directed, 0)
        self.assertEqual(directed + div_diff.DEFAULT_VECTOR_COUNT, len(vectors))
        self.assertIn((0, 0, 0), vectors)
        self.assertIn((1, 0, 0), vectors)
        self.assertTrue(any(item[0] == 0 for item in vectors))
        self.assertTrue(any(item[0] == 1 for item in vectors))


class DivParserTests(unittest.TestCase):
    def test_complete_marker_and_fields_are_strict(self) -> None:
        text = (
            "DIV_SELF_CHECK_PASS active=4136 directed=40 signed=2068 unsigned=2068 "
            "divide_zero=20 complete_pulses=4136 pulse_s=4136 historical_r=4136 "
            "results=4136 reset=40 abort=16 late_abort=1 held_high_cleanup=1 "
            "held_high_restart=1 edges=150000\n"
        )
        parsed = div_diff.parse_driver_result(text)
        self.assertTrue(parsed["pass_marker"])
        self.assertEqual(4136, parsed["active"])
        self.assertEqual(40, parsed["directed"])
        self.assertEqual(20, parsed["divide_zero"])
        self.assertEqual(1, parsed["late_abort"])
        self.assertEqual(1, parsed["held_high_cleanup"])
        self.assertEqual(1, parsed["held_high_restart"])
        self.assertIsNone(parsed["first_mismatch"])
        self.assertIsNone(parsed["skip"])

    def test_mismatch_skip_and_near_miss_are_not_pass(self) -> None:
        mismatch = "DIV_MISMATCH kind=result edge=34 index=0\n"
        parsed = div_diff.parse_driver_result(
            mismatch
            + "DIV_SELF_CHECK_PASS active=1 directed=1 signed=1 unsigned=0 divide_zero=1 "
            "complete_pulses=1 pulse_s=1 historical_r=1 results=1 reset=3 abort=1 "
            "late_abort=1 held_high_cleanup=1 held_high_restart=1 edges=40\n"
        )
        self.assertTrue(parsed["pass_marker"])
        self.assertEqual(mismatch.strip(), parsed["first_mismatch"])
        skipped = div_diff.parse_driver_result("SKIP divider unavailable\n")
        self.assertIsNotNone(skipped["skip"])
        near = div_diff.parse_driver_result("DIV_SELF_CHECK_PASS active=1 directed=1\n")
        self.assertFalse(near["pass_marker"])

    def test_normalization_and_negative_anchors_are_unique(self) -> None:
        payload = b"module div(\n);\nassign s = TmpS[31:0];\nassign complete = (count == 8'hff);\nUnsignR <= tmp_r;\n"
        normalized = div_diff.normalize_source(payload)
        self.assertIn(b"module div_golden(", normalized)
        self.assertEqual(1, div_diff.mutate_source(payload, "result_bit_flip").count(b"^ 32'h00000001"))
        self.assertEqual(1, div_diff.mutate_source(payload, "complete_timing").count(b"8'hfe"))
        self.assertEqual(
            1,
            div_diff.mutate_source(payload, "remainder_capture_bit_flip").count(
                b"^ 33'h000000001"
            ),
        )
        with self.assertRaises(div_diff.DivDiffError):
            div_diff.normalize_source(payload + b"module div(")


class DivFailClosedTests(unittest.TestCase):
    def _args(self, root: Path) -> object:
        return type(
            "Args",
            (),
            {
                "contract": None,
                "manifest": ROOT / "reference" / "manifest.lock",
                "out_dir": root / "out",
                "vector_count": div_diff.DEFAULT_VECTOR_COUNT,
                "seed": div_diff.DEFAULT_SEED,
                "timeout": 5,
                "verilator": None,
                "waivers": ROOT / "lint-waivers.yml",
            },
        )()

    def _fake_run(self, output: str, *, timeout: bool = False):
        def run(argv, *, cwd, timeout, environment=None):
            del timeout, environment
            if argv[1:] == ["--version"]:
                name = Path(argv[0]).name
                version = "Verilator 5.020" if name == "verilator" else f"{name} test"
                return {"argv": argv, "returncode": 0, "timed_out": False, "elapsed_seconds": 0.01, "stdout": version + "\n"}
            if "--cc" in argv:
                binary = cwd / "obj_dir" / "Vdiv_golden"
                binary.parent.mkdir(parents=True, exist_ok=True)
                binary.write_bytes(b"binary")
                source = cwd / "div_golden.v"
                warning = (
                    f"%Warning-WIDTHTRUNC: {source}:82:40: {div_diff.EXPECTED_GOLDEN_WARNINGS[0][2]}\n"
                    f"%Warning-UNUSEDSIGNAL: {source}:85:13: {div_diff.EXPECTED_GOLDEN_WARNINGS[1][2]}\n"
                    f"%Warning-UNUSEDSIGNAL: {source}:85:19: {div_diff.EXPECTED_GOLDEN_WARNINGS[2][2]}\n"
                )
                return {"argv": argv, "returncode": 124 if timeout else 0, "timed_out": timeout, "elapsed_seconds": 0.01, "stdout": warning}
            return {"argv": argv, "returncode": 0, "timed_out": False, "elapsed_seconds": 0.01, "stdout": output}

        return run

    def _run_mocked(
        self,
        root: Path,
        *,
        simulation: str = "",
        compile_extra: str = "",
        timeout: bool = False,
        tamper_source: bool = False,
    ):
        args = self._args(root)
        fake_tools = {}
        for name in ("verilator", "make", "g++"):
            path = root / name
            path.write_text(name, encoding="ascii")
            path.chmod(0o755)
            fake_tools[name] = path

        def checked(values, value, name, key):
            del values, value, key
            return fake_tools[name]

        compile_timeout = timeout

        def fake_run(argv, *, cwd, timeout, environment=None):
            del timeout
            del environment
            if argv[1:] == ["--version"]:
                name = Path(argv[0]).name
                return {"argv": argv, "returncode": 0, "timed_out": False, "elapsed_seconds": 0.01, "stdout": ("Verilator 5.020" if name == "verilator" else name) + "\n"}
            if "--cc" in argv:
                binary = cwd / "obj_dir" / "Vdiv_golden"
                binary.parent.mkdir(parents=True, exist_ok=True)
                binary.write_bytes(b"binary")
                source = cwd / "div_golden.v"
                if tamper_source:
                    source.write_bytes(source.read_bytes() + b"// drift\n")
                warnings = (
                    f"%Warning-WIDTHTRUNC: {source}:82:40: {div_diff.EXPECTED_GOLDEN_WARNINGS[0][2]}\n"
                    f"%Warning-UNUSEDSIGNAL: {source}:85:13: {div_diff.EXPECTED_GOLDEN_WARNINGS[1][2]}\n"
                    f"%Warning-UNUSEDSIGNAL: {source}:85:19: {div_diff.EXPECTED_GOLDEN_WARNINGS[2][2]}\n"
                )
                return {"argv": argv, "returncode": 124 if compile_timeout else 0, "timed_out": compile_timeout, "elapsed_seconds": 0.01, "stdout": warnings + compile_extra}
            return {"argv": argv, "returncode": 0, "timed_out": False, "elapsed_seconds": 0.01, "stdout": simulation}

        payload = (
            b"module div(\n);\n" + b"assign s = TmpS[31:0];\n" + b"assign complete = (count == 8'hff);\n"
        )
        with mock.patch.object(div_diff, "_blob", return_value=payload), mock.patch.object(div_diff, "_git_head", return_value="a" * 40), mock.patch.object(div_diff, "checked_executable", side_effect=checked), mock.patch.object(div_diff, "run_command", side_effect=fake_run):
            return div_diff.run_golden(args)

    def test_warning_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary), compile_extra="%Warning-WIDTH: /tmp/other.v:1:1: drift\n")
        self.assertEqual(1, code)
        self.assertEqual("fail", summary["status"])
        self.assertIn("warning", str(summary.get("error", "")).lower())

    def test_timeout_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary), timeout=True)
        self.assertEqual(1, code)
        self.assertIn("timed out", str(summary.get("error", "")))

    def test_source_drift_during_compile_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code, summary = self._run_mocked(Path(temporary), tamper_source=True)
        self.assertEqual(1, code)
        self.assertIn("source changed during compilation", str(summary.get("error", "")))

    def test_golden_warning_waivers_are_consumed_fail_closed(self) -> None:
        evidence = div_diff.validate_waivers(ROOT / "lint-waivers.yml")
        self.assertEqual(3, len(evidence["accepted"]))
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "div_golden.v"
            source.write_text("module div_golden; endmodule\n", encoding="ascii")
            warning_text = "\n".join(
                f"%Warning-{item['rule']}: {source}:{item['line']}:1: {item['message']}"
                for item in evidence["accepted"]
            )
            passed, warnings, error = div_diff.warning_policy(
                warning_text,
                source,
                golden=True,
                approved_warnings=evidence["accepted"],
            )
        self.assertTrue(passed, error)
        self.assertEqual(
            set(div_diff.EXPECTED_GOLDEN_WAIVERS),
            {warning["waiver_id"] for warning in warnings},
        )
        document = json.loads((ROOT / "lint-waivers.yml").read_text(encoding="utf-8"))
        document["waivers"] = [
            item
            for item in document["waivers"]
            if item["id"] != "golden-div-count-index-width"
        ]
        with tempfile.TemporaryDirectory() as temporary:
            broken = Path(temporary) / "lint-waivers.yml"
            broken.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(div_diff.DivDiffError, "waiver set drifted"):
                div_diff.validate_waivers(broken)

    def test_candidate_consumes_locked_contract_stimulus(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = type(
                "Args",
                (),
                {
                    "contract": ROOT / "reference" / "component-contracts" / "div.json",
                    "manifest": ROOT / "reference" / "manifest.lock",
                    "out_dir": Path(temporary) / "out",
                    "rtl": Path(temporary) / "missing.v",
                    "vector_count": div_diff.DEFAULT_VECTOR_COUNT,
                    "seed": div_diff.DEFAULT_SEED,
                    "timeout": 5,
                    "verilator": None,
                },
            )()
            drifted = {
                "stimulus": {"seed": "0x1", "random_transactions": 4096},
                "contract": {},
                "golden": {},
                "protocol": {},
                "ports": {},
                "arithmetic": {},
            }
            with mock.patch.object(div_diff, "_contract_evidence", return_value=drifted):
                code, summary = div_diff.run_candidate(args)
        self.assertEqual(1, code)
        self.assertIn("stimulus differs", summary["error"])
        self.assertEqual(
            {"planned": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0},
            summary["counts"],
        )

    def test_golden_stability_failure_keeps_count_arithmetic(self) -> None:
        summary = {
            "golden": {"status": "pass"},
            "negative_controls": [
                {"control_pass": True},
                {"control_pass": True},
                {"control_pass": True},
            ],
            "source_stability": {
                "stable": False,
                "manifest_before_sha256": "a" * 64,
                "manifest_after_sha256": "a" * 64,
            },
        }
        counts = div_diff._golden_failure_counts(summary)
        self.assertEqual(4, counts["executed"])
        self.assertEqual(3, counts["passed"])
        self.assertEqual(counts["executed"], counts["passed"] + counts["failed"])

        early_failure = div_diff._golden_failure_counts({})
        self.assertEqual(
            {"planned": 4, "executed": 1, "passed": 0, "failed": 1, "skipped": 3},
            early_failure,
        )
        self.assertEqual(
            early_failure["planned"],
            early_failure["executed"] + early_failure["skipped"],
        )

        after_golden = div_diff._golden_failure_counts({"golden": {"status": "pass"}})
        self.assertEqual(
            {"planned": 4, "executed": 2, "passed": 1, "failed": 1, "skipped": 2},
            after_golden,
        )

        after_all_subchecks = div_diff._golden_failure_counts(
            {
                "golden": {"status": "pass"},
                "negative_controls": [
                    {"control_pass": True},
                    {"control_pass": True},
                    {"control_pass": True},
                ],
            }
        )
        self.assertEqual(
            {"planned": 4, "executed": 4, "passed": 3, "failed": 1, "skipped": 0},
            after_all_subchecks,
        )

    def test_skip_and_mismatch_fail_closed(self) -> None:
        for output, needle in (("SKIP unavailable\n", "SKIP"), ("DIV_MISMATCH kind=result edge=1\n", "DIV_MISMATCH")):
            with tempfile.TemporaryDirectory() as temporary:
                code, summary = self._run_mocked(Path(temporary), simulation=output)
            self.assertEqual(1, code)
            self.assertIn(needle, str(summary.get("error", "")))

    def test_cli_requires_isolated_python_and_floor(self) -> None:
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "div_diff.py"), "--help"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("requires isolated Python", result.stderr)
        result = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "div_diff.py"), "golden", "--manifest", "missing", "--contract", str(ROOT / "reference" / "component-contracts" / "div.json"), "--waivers", str(ROOT / "lint-waivers.yml"), "--out-dir", "unused", "--vector-count", "4095"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("vector-count must be >=4096", result.stderr)


if __name__ == "__main__":
    unittest.main()
