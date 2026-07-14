from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import official_source_audit


class OfficialSourceAuditTests(unittest.TestCase):
    def test_classifies_enhancement_and_backup_files(self) -> None:
        self.assertEqual(official_source_audit.classify_historical("rtl/lacc_core.v", False), "team-enhancement")
        self.assertEqual(official_source_audit.classify_historical("rtl/btb.v.bak", False), "dead-or-backup")
        self.assertEqual(official_source_audit.classify_historical("rtl/soc_top.v", False), "historical-unmatched")

    def test_official_rtl_classification_is_basename_independent(self) -> None:
        self.assertEqual(official_source_audit.classify_official("mycpu_top.v"), "official-behavioral-rtl")
        self.assertEqual(official_source_audit.classify_official("doc/design.md"), "official-documentation")
        self.assertEqual(official_source_audit.classify_official("IP/data_bank_sram.xcix"), "official-memory-ip")


    def test_revisions_must_be_full_shas(self) -> None:
        self.assertEqual(official_source_audit.validate_revision("a" * 40), "a" * 40)
        with self.assertRaises(ValueError):
            official_source_audit.validate_revision("a158aa8")
if __name__ == "__main__":

    unittest.main()
