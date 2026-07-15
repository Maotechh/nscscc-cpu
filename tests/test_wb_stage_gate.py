from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import wb_stage_gate


class WritebackStageGateTests(unittest.TestCase):
    def test_locked_profiles_have_exact_ports(self) -> None:
        normal = wb_stage_gate.expected_ports(False)
        difftest = wb_stage_gate.expected_ports(True)
        self.assertEqual(52, len(normal))
        self.assertEqual(64, len(difftest))
        self.assertEqual({"direction": "input", "width": 493}, normal["ms_to_ws_bus"])
        self.assertNotIn("ws_timer_64_diff", normal)
        self.assertEqual(
            {"direction": "output", "width": 64}, difftest["ws_timer_64_diff"]
        )

    def test_contract_records_full_port_sets_and_golden_hash(self) -> None:
        root = Path(__file__).resolve().parents[1]
        contract = json.loads(
            (root / "reference/component-contracts/wb-stage.json").read_text(encoding="utf-8")
        )
        self.assertEqual(wb_stage_gate.GOLDEN_SHA256, contract["golden"]["sha256"])
        self.assertEqual(
            wb_stage_gate.expected_ports(False), contract["ports"]["common"]
        )
        self.assertEqual(
            set(wb_stage_gate.DIFF_OUTPUTS), set(contract["ports"]["difftest_extra"])
        )
        self.assertEqual(8192, contract["differential"]["minimum_cycles"])

    def test_module_rename_is_unique(self) -> None:
        renamed = wb_stage_gate.renamed_module(
            b"module wb_stage(input clk);\nendmodule\n", b"wb_stage_candidate"
        )
        self.assertIn(b"module wb_stage_candidate", renamed)
        with self.assertRaises(wb_stage_gate.GateError):
            wb_stage_gate.renamed_module(b"module other(); endmodule\n", b"candidate")

    def test_testbench_compares_latched_difftest_payload_during_stall(self) -> None:
        source = wb_stage_gate.testbench(8192, wb_stage_gate.DEFAULT_SEED)
        self.assertIn("g_ws_timer_64_diff", source)
        self.assertIn("c_ws_st_data_diff", source)
        self.assertIn("debug_break_point=1", source)
        self.assertIn("for (i=0; i<7", source)
        self.assertIn("WB_MISMATCH cycle=%0d phase=%0d", source)
        self.assertIn("negative_control & c_debug_ws_valid", source)
        self.assertIn("for (i=0; i<8192", source)


if __name__ == "__main__":
    unittest.main()
