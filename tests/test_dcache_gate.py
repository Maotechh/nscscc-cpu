#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dcache_gate", ROOT / "tools" / "dcache_gate.py")
assert SPEC is not None and SPEC.loader is not None
dcache_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dcache_gate)


class DCacheGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.golden = subprocess.run(
            ["git", "cat-file", "blob", f"{dcache_gate.GOLDEN_COMMIT}:{dcache_gate.GOLDEN_PATH}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        cls.contract = json.loads(
            (ROOT / "reference" / "component-contracts" / "dcache.json").read_text(encoding="utf-8")
        )

    def test_locked_identity_and_ports(self) -> None:
        self.assertEqual(dcache_gate.GOLDEN_SIZE, len(self.golden))
        self.assertEqual(dcache_gate.GOLDEN_SHA256, dcache_gate.sha256_bytes(self.golden))
        self.assertEqual(35, len(self.contract["ports"]))
        self.assertEqual(self.contract["ports"], dcache_gate.parse_ports(self.golden.decode("utf-8")))

    def test_negative_control_anchor_is_unique(self) -> None:
        anchor = b"assign rd_req  = main_state_is_replace &&"
        self.assertEqual(1, self.golden.count(anchor))

    def test_driver_observes_complete_output_contract(self) -> None:
        for output in (
            "addr_ok", "data_ok", "rdata", "dcache_empty", "rd_req", "rd_type",
            "rd_addr", "wr_req", "wr_type", "wr_addr", "wr_wstrb", "wr_data", "cache_miss",
        ):
            with self.subTest(output=output):
                self.assertIn(f"d.{output}", dcache_gate.DRIVER)

    def test_gate_does_not_write_shared_cache_directory(self) -> None:
        self.assertNotIn(".gate-cache", Path(dcache_gate.__file__).read_text(encoding="utf-8"))

    def test_makefile_dispatches_all_dcache_gates(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("openla500.memory.GenerateOpenLa500DCache", makefile)
        for command in ("port-check", "lint", "yosys-check", "diff"):
            with self.subTest(command=command):
                self.assertIn(f"tools/dcache_gate.py {command}", makefile)


if __name__ == "__main__":
    unittest.main()
