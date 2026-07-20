#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cacop_recovery_gate", ROOT / "tools" / "cacop_recovery_gate.py"
)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class CacopRecoveryGateTests(unittest.TestCase):
    def test_iteration_oracle_does_not_replace_global_lock(self) -> None:
        manifest = (ROOT / "reference" / "manifest.lock").read_text(encoding="utf-8")
        self.assertIn("team_golden_candidate=a158aa8", manifest)
        self.assertEqual("d22c13c1ecbee7b0423b7e4f4616f24d98457f02", gate.ORACLE_COMMIT)
        self.assertNotIn("manifest.lock", Path(gate.__file__).read_text(encoding="utf-8"))

    def test_all_historical_controls_are_identity_locked(self) -> None:
        self.assertEqual(3, len(gate.HISTORICAL_CONTROLS))
        for commit in (gate.ORACLE_COMMIT, *gate.HISTORICAL_CONTROLS.values()):
            with self.subTest(commit=commit):
                self.assertEqual(
                    {"rtl/icache.v", "rtl/dcache.v", "rtl/tools.v"},
                    set(gate.LOCKED_BLOBS[commit]),
                )

    def test_directed_vectors_cover_contract_dimensions(self) -> None:
        combined = []
        for target in ("icache", "dcache"):
            vectors, labels, scenarios = gate.generate_vectors(target)
            self.assertEqual(len(vectors), len(labels))
            self.assertGreater(len(vectors), 0)
            combined.extend(scenarios)
        self.assertEqual({0, 1, 2, 3}, {item["mode"] for item in combined})
        self.assertEqual({0, 1}, {item["way"] for item in combined})
        self.assertEqual({"selected-way", "selected-way-alias", "hit", "miss"}, {item["lookup"] for item in combined})
        self.assertTrue(all(item["rd_rdy_backpressure"] for item in combined))
        invalidating = [item for item in combined if item["single_cycle_invalidation"]]
        retained = [item for item in combined if not item["single_cycle_invalidation"]]
        self.assertTrue(invalidating)
        self.assertTrue(all(item["mode"] == 2 and item["lookup"] == "miss" for item in retained))
        dirty = [item for item in combined if item["dirty_writeback"]]
        self.assertTrue(any(item["mode"] == 1 for item in dirty))
        self.assertTrue(any(item["mode"] == 2 for item in dirty))
        self.assertEqual({0, 1}, {item["way"] for item in dirty})

if __name__ == "__main__":
    unittest.main()
