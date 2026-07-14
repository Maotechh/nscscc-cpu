from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import lacc_diff


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "reference" / "component-contracts" / "lacc.json"
MANIFEST = ROOT / "reference" / "manifest.lock"
TESTBENCH = ROOT / "tests" / "rtl" / "lacc_core_lockstep.sv"


class LaccContractTests(unittest.TestCase):
    def test_locked_contract_is_complete(self) -> None:
        document = lacc_diff.validate_contract(lacc_diff.load_json(CONTRACT))
        self.assertEqual(lacc_diff.PORTS, document["ports"])
        self.assertEqual(8192, document["stimulus"]["minimum_cycles"])
        self.assertTrue(document["stimulus"]["legal_read_responses"])
        self.assertTrue(document["diff"]["two_state"])

    def test_contract_rejects_golden_hash_drift(self) -> None:
        document = json.loads(CONTRACT.read_text(encoding="utf-8"))
        document["golden"]["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(lacc_diff.LaccDiffError, "golden file/hash"):
            lacc_diff.validate_contract(document)

    def test_contract_rejects_port_drift(self) -> None:
        document = json.loads(CONTRACT.read_text(encoding="utf-8"))
        document["ports"]["lacc_data_addr"]["width"] = 31
        with self.assertRaisesRegex(lacc_diff.LaccDiffError, "port map"):
            lacc_diff.validate_contract(document)

    def test_contract_gate_writes_machine_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "contract"
            args = lacc_diff.build_parser().parse_args(
                [
                    "contract",
                    "--contract",
                    str(CONTRACT),
                    "--manifest",
                    str(MANIFEST),
                    "--out-dir",
                    str(out),
                ]
            )
            self.assertEqual(0, lacc_diff.run_contract(args))
            result = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("pass", result["status"])
            self.assertEqual(0, result["counts"]["skipped"])


class LaccHarnessTests(unittest.TestCase):
    def test_golden_rename_requires_unique_anchors(self) -> None:
        core = b"module lacc_core(\nlacc_demo demo(\n"
        demo = b"module lacc_demo(\n"
        renamed_core, renamed_demo = lacc_diff.rename_golden(core, demo)
        self.assertIn(b"module golden_lacc_core(", renamed_core)
        self.assertIn(b"golden_lacc_demo demo(", renamed_core)
        self.assertIn(b"module golden_lacc_demo(", renamed_demo)
        with self.assertRaisesRegex(lacc_diff.LaccDiffError, "not unique"):
            lacc_diff.rename_golden(core + core, demo)

    def test_git_blob_converts_windows_worktree_pointer_under_posix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / ".git").write_text(
                "gitdir: D:/repo/.git/worktrees/consolidated\n", encoding="ascii"
            )
            failed = mock.Mock(returncode=128, stdout=b"", stderr=b"not a repository")
            passed = mock.Mock(returncode=0, stdout=b"golden", stderr=b"")
            with mock.patch.object(lacc_diff.os, "name", "posix"), mock.patch.object(
                lacc_diff.subprocess, "run", side_effect=(failed, passed)
            ) as invoked:
                self.assertEqual(b"golden", lacc_diff.git_blob(repo, "a" * 40, "rtl/lacc.v"))
            fallback = invoked.call_args_list[1].args[0]
            self.assertEqual(
                "--git-dir=/mnt/d/repo/.git/worktrees/consolidated", fallback[1]
            )

    def test_warning_scopes_cannot_hide_candidate_warning(self) -> None:
        output = "\n".join(
            (
                "%Warning-WIDTHEXPAND: /tmp/golden_lacc_demo.v:80:65: historical",
                "%Warning-UNUSEDSIGNAL: /tmp/candidate.v:22:8: candidate",
                "%Warning-UNUSEDSIGNAL: /tmp/tb.sv:30:8: harness",
                "%Warning-MULTITOP: /tmp/other.v:1:1: unknown",
            )
        )
        classified = lacc_diff.classify_warnings(lacc_diff.warning_records(output))
        self.assertEqual(["WIDTHEXPAND"], [item["rule"] for item in classified["golden"]])
        self.assertEqual(["UNUSEDSIGNAL"], [item["rule"] for item in classified["candidate"]])
        self.assertEqual(["UNUSEDSIGNAL"], [item["rule"] for item in classified["harness"]])
        self.assertEqual(["MULTITOP"], [item["rule"] for item in classified["unclassified"]])

    def test_pass_marker_requires_all_coverage_counts(self) -> None:
        marker = (
            "LACC_DIFF_PASS cycles=8192 seed=0x00158aa8 requests=25 responses=24 "
            "data=122 reads=50 writes=25 stalls=47 drsp=50 resets=9 flushes=30\n"
        )
        parsed = lacc_diff.parse_pass_marker(marker)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(8192, parsed["cycles"])
        self.assertEqual(0x158AA8, parsed["seed"])
        self.assertEqual(25, parsed["writes"])
        self.assertIsNone(lacc_diff.parse_pass_marker("LACC_DIFF_PASS cycles=8192\n"))

    def test_testbench_compares_valid_payloads_and_has_negative_control(self) -> None:
        source = TESTBENCH.read_text(encoding="ascii")
        self.assertEqual(1, source.count("c_lacc_rsp_valid ^ negative_control"))
        self.assertIn("if (g_lacc_rsp_valid &&", source)
        self.assertIn("if (g_lacc_data_valid) begin", source)
        self.assertIn("if (!g_lacc_data_read &&", source)
        self.assertIn("backpressure_payload_stability", source)
        self.assertIn("LACC_MISMATCH", source)
        self.assertIn("NEGATIVE_CONTROL_DID_NOT_FAIL", source)
        self.assertIn("LACC_DIFF_PASS", source)

    def test_candidate_arguments_reject_short_or_changed_stimulus(self) -> None:
        parser = lacc_diff.build_parser()
        common = [
            "candidate",
            "--contract",
            str(CONTRACT),
            "--manifest",
            str(MANIFEST),
            "--rtl",
            str(TESTBENCH),
            "--out-dir",
        ]
        for extra, expected in ((["--cycles", "8191"], "cycles"), (["--seed", "1"], "seed")):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as temporary:
                args = parser.parse_args(common + [str(Path(temporary) / "out")] + extra)
                self.assertEqual(1, lacc_diff.run_candidate(args))
                result = json.loads(
                    (Path(temporary) / "out" / "summary.json").read_text(encoding="utf-8")
                )
                self.assertIn(expected, result["error"])


if __name__ == "__main__":
    unittest.main()
