from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import mem_stage_gate


class MemoryStageGateTests(unittest.TestCase):
    def test_locked_port_set_is_exact(self) -> None:
        ports = mem_stage_gate.expected_ports()
        self.assertEqual(49, len(ports))
        self.assertEqual({"direction": "input", "width": 425}, ports["es_to_ms_bus"])
        self.assertEqual({"direction": "output", "width": 493}, ports["ms_to_ws_bus"])
        self.assertEqual(
            {"direction": "output", "width": 39}, ports["ms_to_ds_forward_bus"]
        )

    def test_contract_records_ports_golden_and_minimum_cycles(self) -> None:
        root = Path(__file__).resolve().parents[1]
        contract = json.loads(
            (root / "reference/component-contracts/mem-stage.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(mem_stage_gate.GOLDEN_SHA256, contract["golden"]["sha256"])
        self.assertEqual(mem_stage_gate.expected_ports(), contract["ports"])
        self.assertEqual(8192, contract["differential"]["minimum_cycles"])
        self.assertTrue(contract["differential"]["compare_all_outputs_every_phase"])
        self.assertEqual(
            [mem_stage_gate.ADDRESS_SNAPSHOT_ORACLE],
            contract["differential"]["golden_corrections"],
        )
        self.assertEqual(3, len(contract["lint_allowlist"]))
        waivers = mem_stage_gate.load_central_waivers(root)
        self.assertTrue(mem_stage_gate.CENTRAL_WAIVER_IDS.issubset(waivers))

    def test_module_rename_is_unique(self) -> None:
        renamed = mem_stage_gate.renamed_module(
            b"module mem_stage(input clk);\nendmodule\n", b"mem_stage_candidate"
        )
        self.assertIn(b"module mem_stage_candidate", renamed)
        with self.assertRaises(mem_stage_gate.GateError):
            mem_stage_gate.renamed_module(b"module other(); endmodule\n", b"candidate")

    def test_first_mismatch_parser_records_outputs(self) -> None:
        parsed = mem_stage_gate.parse_first_mismatch(
            "MEM_MISMATCH cycle=19 phase=1 g_pc=1c003003 c_pc=1c003003\n"
            "MEM_OUTPUT_MISMATCH output=ms_to_ws_bus g=0 c=1\n"
        )
        self.assertEqual(19, parsed["cycle"])
        self.assertEqual(["ms_to_ws_bus"], parsed["differing_outputs"])

    def test_testbench_has_directed_random_and_negative_control(self) -> None:
        source = mem_stage_gate.testbench(8192, mem_stage_gate.DEFAULT_SEED)
        for output in mem_stage_gate.OUTPUTS:
            self.assertIn(f"g_{output}", source)
            self.assertIn(f"c_{output}", source)
        self.assertIn("Capture a returning load while WB is stalled", source)
        self.assertIn("Paging/TLB exception, DMW uncached", source)
        self.assertIn("for (i=0; i<5", source)
        self.assertIn("excp_flush=(i==0)", source)
        self.assertIn("idle_flush=(i==4)", source)
        self.assertIn("MEM_MISMATCH cycle=%0d phase=%0d", source)
        self.assertIn("MEM_OUTPUT_MISMATCH output=ms_to_ws_bus", source)
        self.assertIn(
            "{g_ms_to_ws_bus[492:368],accepted_data_index,accepted_data_offset,g_ms_to_ws_bus[355:0]}",
            source,
        )
        self.assertIn("if (es_to_ms_valid && g_ms_allowin)", source)
        self.assertIn("Hold the low physical address from the accepted request", source)
        self.assertIn("negative_control & c_ms_to_ws_valid", source)
        self.assertIn("for (i=0; i<8192", source)


if __name__ == "__main__":
    unittest.main()
