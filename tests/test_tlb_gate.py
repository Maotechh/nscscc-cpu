#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tlb_gate", ROOT / "tools" / "tlb_gate.py")
assert SPEC is not None and SPEC.loader is not None
tlb_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tlb_gate)


class TlbGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.golden = subprocess.run(
            ["git", "cat-file", "blob", f"{tlb_gate.GOLDEN_COMMIT}:{tlb_gate.GOLDEN_PATH}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout

    def test_locked_golden_identity(self) -> None:
        self.assertEqual(len(self.golden), tlb_gate.GOLDEN_SIZE)
        self.assertEqual(tlb_gate.sha256_bytes(self.golden), tlb_gate.GOLDEN_SHA256)

    def test_negative_control_anchor_is_unique(self) -> None:
        for anchor, replacement, name in tlb_gate.NEGATIVE_MUTATIONS:
            with self.subTest(name=name):
                self.assertEqual(self.golden.count(anchor), 1)
                self.assertNotEqual(anchor, replacement)

    def test_testbench_contains_all_required_directed_cases(self) -> None:
        bench = tlb_gate.testbench(17, 0x158AA8)
        for marker in (
            "for (i=0; i<32; i=i+1)",
            "fetch_pair",
            "small-page/odd search expectation failed",
            "large-page/global search expectation failed",
            "multi-match OR index expectation failed",
            "invalidate(0",
            "invalidate(1",
            "invalidate(2",
            "invalidate(3",
            "invalidate(4",
            "invalidate(5",
            "invalidate(6",
            "wins over simultaneous invalidation",
            "for (i=0; i<17; i=i+1)",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, bench)

    def test_module_rename_is_exact_and_fail_closed(self) -> None:
        renamed = tlb_gate.rename_module(self.golden, b"tlb_entry_candidate")
        self.assertIn(b"module tlb_entry_candidate", renamed)
        with self.assertRaisesRegex(tlb_gate.GateError, "exactly one"):
            tlb_gate.rename_module(b"module unrelated; endmodule\n", b"candidate")

    def test_makefile_exposes_tlb_unit_target(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("else ifeq ($(TARGET),tlb)", makefile)
        self.assertIn("tools/tlb_gate.py diff", makefile)

if __name__ == "__main__":
    unittest.main()
