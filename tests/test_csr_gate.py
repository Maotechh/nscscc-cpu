from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import csr_gate


class CsrGateTests(unittest.TestCase):
    def test_exact_port_counts(self) -> None:
        self.assertEqual(55, len(csr_gate.expected_ports(False)))
        self.assertEqual(81, len(csr_gate.expected_ports(True)))
        self.assertEqual(("input", 1), csr_gate.expected_ports(False)["clk"])
        self.assertEqual(("output", 32), csr_gate.expected_ports(True)["csr_pgdh_diff"])

    def test_module_rename_is_unique(self) -> None:
        self.assertIn(b"module csr_candidate", csr_gate.renamed_module(b"module csr();\nendmodule\n", b"csr_candidate"))
        with self.assertRaises(csr_gate.CsrGateError):
            csr_gate.renamed_module(b"module other(); endmodule\n", b"csr_candidate")

    def test_testbench_compares_architectural_state(self) -> None:
        source = csr_gate.testbench(32)
        self.assertIn("g_csr_crmd_diff", source)
        self.assertIn("c_csr_pgdh_diff", source)
        self.assertIn("CSR_MISMATCH", source)
        self.assertIn("for (i=0; i<32", source)


if __name__ == "__main__":
    unittest.main()
