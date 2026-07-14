from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import perf_counter_gate


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "reference" / "component-contracts" / "perf-counter.json"
MANIFEST = ROOT / "reference" / "manifest.lock"
TESTBENCH = ROOT / "tests" / "rtl" / "perf_counter_lockstep.sv"


class PerfCounterContractTests(unittest.TestCase):
    def test_locked_contract_is_complete(self) -> None:
        document = perf_counter_gate.validate_contract(perf_counter_gate.load_json(CONTRACT))
        self.assertEqual(perf_counter_gate.PORT_NAMES, [item["name"] for item in document["ports"]])
        self.assertEqual(perf_counter_gate.COUNTER_NAMES, [item["counter"] for item in document["events"]])

    def test_contract_rejects_hash_port_and_seed_drift(self) -> None:
        for mutation, expected in (
            (lambda value: value.update(golden_sha256="0" * 64), "golden hash"),
            (lambda value: value["ports"].pop(), "port list"),
            (lambda value: value["random"].update(seed="0x1"), "random policy"),
        ):
            with self.subTest(expected=expected):
                document = json.loads(CONTRACT.read_text(encoding="utf-8"))
                mutation(document)
                with self.assertRaisesRegex(perf_counter_gate.PerfCounterGateError, expected):
                    perf_counter_gate.validate_contract(document)

    def test_contract_gate_binds_real_golden_blob(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "contract"
            args = perf_counter_gate.build_parser().parse_args(
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
            self.assertEqual(0, perf_counter_gate.run_contract(args))
            result = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("pass", result["status"])
            self.assertEqual(perf_counter_gate.GOLDEN_SHA256, result["golden_sha256"])
            self.assertEqual(0, result["counts"]["skipped"])


class PerfCounterHarnessTests(unittest.TestCase):
    def test_golden_rename_is_unique(self) -> None:
        source = b"module perf_counter (\nendmodule\n"
        self.assertIn(b"module golden_perf_counter (", perf_counter_gate.rename_golden(source))
        with self.assertRaisesRegex(perf_counter_gate.PerfCounterGateError, "not unique"):
            perf_counter_gate.rename_golden(source + source)

    def test_pass_marker_requires_coverage(self) -> None:
        marker = (
            "PERF_COUNTER_DIFF_PASS cycles=8192 seed=0x0158aa8e resets=8 idle=42 "
            "concurrent=7000 wrap=1 events=10,11,12,13,14,15,16\n"
        )
        parsed = perf_counter_gate.parse_pass_marker(marker)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(0x0158AA8E, parsed["seed"])
        self.assertEqual([10, 11, 12, 13, 14, 15, 16], parsed["events"])
        self.assertIsNone(perf_counter_gate.parse_pass_marker("PERF_COUNTER_DIFF_PASS cycles=8192"))

    def test_harness_observes_all_counters_wrap_and_negative_control(self) -> None:
        source = TESTBENCH.read_text(encoding="ascii")
        for name in perf_counter_gate.COUNTER_NAMES:
            self.assertIn(f"golden.{name}", source)
            self.assertIn(f"candidate.{name}", source)
        self.assertIn("32'hffffffff", source)
        self.assertIn("PERF_COUNTER_MISMATCH", source)
        self.assertIn("negative_control", source)
        self.assertIn("PERF_COUNTER_DIFF_PASS", source)

    def test_candidate_rejects_changed_stimulus_before_tools(self) -> None:
        parser = perf_counter_gate.build_parser()
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
        for extra, expected in ((["--cycles", "1"], "cycles"), (["--seed", "1"], "seed")):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as temporary:
                out = Path(temporary) / "out"
                args = parser.parse_args(common + [str(out)] + extra)
                self.assertEqual(1, perf_counter_gate.run_candidate(args))
                result = json.loads((out / "summary.json").read_text(encoding="utf-8"))
                self.assertIn(expected, result["error"])

    def test_top_integration_check_requires_all_typed_connections(self) -> None:
        connections = {
            "io_clk": "aclk",
            "io_reset": "reset",
            "io_events_dataCacheMiss": "writeback_io_perf_dataCacheMiss",
            "io_events_instructionCacheMiss": "writeback_io_perf_instructionCacheMiss",
            "io_events_retired": "writeback_io_perf_retired",
            "io_events_branch": "writeback_io_perf_branch",
            "io_events_memoryAccess": "writeback_io_perf_memoryAccess",
            "io_events_predictedBranch": "writeback_io_perf_predictedBranch",
            "io_events_predictionError": "writeback_io_perf_predictionError",
        }
        state = [
            "counters_dataCacheMiss",
            "counters_instructionCacheMiss",
            "counters_retired",
            "counters_branch",
            "counters_memoryAccess",
            "counters_predictedBranch",
            "counters_predictionError",
        ]
        instance_ports = ",\n".join(f".{port}({signal})" for port, signal in connections.items())
        source = (
            "module mycpu_top();\nOpenLa500PerfCounter performanceCounter("
            + instance_ports
            + ");\nendmodule\nmodule OpenLa500PerfCounter(input io_clk);\n"
            + "\n".join(f"reg [31:0] {name};" for name in state)
            + "\nendmodule\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            rtl = Path(temporary) / "mycpu_top.v"
            rtl.write_text(source, encoding="ascii")
            result = perf_counter_gate.verify_top_integration(rtl)
            self.assertEqual(7, result["counter_count"])
            rtl.write_text(source.replace(".io_events_retired", ".broken_retired"), encoding="ascii")
            with self.assertRaisesRegex(perf_counter_gate.PerfCounterGateError, "connection mismatch"):
                perf_counter_gate.verify_top_integration(rtl)


if __name__ == "__main__":
    unittest.main()
