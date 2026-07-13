from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

from tools import axi_bridge_gate


REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "reference" / "component-contracts" / "axi-bridge.json"


class AxiBridgeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.golden = subprocess.run(
            [
                "git",
                "cat-file",
                "blob",
                f"{axi_bridge_gate.GOLDEN_COMMIT}:{axi_bridge_gate.GOLDEN_PATH}",
            ],
            cwd=REPO,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout

    def test_locked_golden_identity_and_port_count(self) -> None:
        self.assertEqual(len(self.golden), axi_bridge_gate.GOLDEN_SIZE)
        self.assertEqual(
            axi_bridge_gate.sha256_bytes(self.golden), axi_bridge_gate.GOLDEN_SHA256
        )
        self.assertEqual(len(self.contract["ports"]), 65)
        self.assertEqual(
            axi_bridge_gate.parse_ports(self.golden.decode("utf-8")),
            self.contract["ports"],
        )

    def test_all_negative_control_anchors_are_unique(self) -> None:
        for old, replacement, name in axi_bridge_gate.MUTATIONS:
            with self.subTest(name=name):
                self.assertEqual(self.golden.count(old), 1)
                self.assertNotEqual(old, replacement)

    def test_port_parser_rejects_missing_module(self) -> None:
        with self.assertRaisesRegex(axi_bridge_gate.GateError, "module header"):
            axi_bridge_gate.parse_ports("module wrong(input clk); endmodule")

    def test_driver_masks_payload_when_channel_is_invalid(self) -> None:
        self.assertIn("d.arvalid ? d.araddr : 0", axi_bridge_gate.DRIVER)
        self.assertIn("d.awvalid ? d.awaddr : 0", axi_bridge_gate.DRIVER)
        self.assertIn("d.wvalid ? d.wdata : 0", axi_bridge_gate.DRIVER)

    def test_candidate_unused_waiver_is_exactly_the_legacy_dead_boundary(self) -> None:
        self.assertEqual(
            axi_bridge_gate.EXPECTED_COMPAT_UNUSED,
            {
                "rid",
                "rresp",
                "bid",
                "bresp",
                "inst_wr_req",
                "inst_wr_type",
                "inst_wr_addr",
                "inst_wr_wstrb",
                "inst_wr_data",
            },
        )


if __name__ == "__main__":
    unittest.main()
