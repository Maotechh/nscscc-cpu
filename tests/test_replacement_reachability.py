#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "replacement_reachability.py"
SPEC = REPO / "reference" / "component-replacements" / "active-reachable.json"
METADATA = REPO / "reference" / "component-replacements" / "active-reachable.meta.json"


class ReplacementReachabilityTest(unittest.TestCase):
    def run_gate(self, spec: Path, metadata: Path, out_dir: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-I",
                str(SCRIPT),
                "--repo-root",
                str(REPO),
                "--spec",
                str(spec),
                "--metadata",
                str(metadata),
                "--out-dir",
                str(out_dir),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_locked_active_set_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_gate(SPEC, METADATA, Path(directory) / "out")
            self.assertEqual(result.returncode, 0, result.stdout)
            report = json.loads((Path(directory) / "out" / "reachability.json").read_text())
            self.assertEqual(report["selected_count"], 13)
            self.assertEqual(report["selected_target_modules"]["rtl/wb_stage.v"], "wb_stage")
            self.assertEqual(report["selected_target_modules"]["rtl/mem_stage.v"], "mem_stage")
            self.assertEqual(report["selected_target_modules"]["rtl/id_stage.v"], "id_stage")
            id_replacement = next(
                item for item in json.loads(SPEC.read_text(encoding="utf-8"))["replacements"]
                if item["target"] == "rtl/id_stage.v"
            )
            self.assertEqual(
                id_replacement["source"],
                "reference/component-replacements/difftest/id_stage.v",
            )
            self.assertNotIn("lacc_core", report["reachable_modules"])

    def test_deferred_alu_cannot_be_duplicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = json.loads(SPEC.read_text(encoding="utf-8"))
            metadata = json.loads(METADATA.read_text(encoding="utf-8"))
            spec["replacements"].append(
                {"target": "rtl/alu.v", "source": "unused", "base_sha256": "0", "replacement_sha256": "0"}
            )
            metadata["selected_replacements"].append("rtl/alu.v")
            spec_path = root / "spec.json"
            metadata_path = root / "metadata.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            result = self.run_gate(spec_path, metadata_path, root / "out")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("must not be duplicated", result.stdout)

    def test_lacc_off_rejects_lacc_core_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = json.loads(SPEC.read_text(encoding="utf-8"))
            metadata = json.loads(METADATA.read_text(encoding="utf-8"))
            spec["replacements"].append(
                {"target": "rtl/lacc_core.v", "source": "unused", "base_sha256": "0", "replacement_sha256": "0"}
            )
            metadata["selected_replacements"].append("rtl/lacc_core.v")
            spec_path = root / "spec.json"
            metadata_path = root / "metadata.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            result = self.run_gate(spec_path, metadata_path, root / "out")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("selected replacement is unreachable", result.stdout)


if __name__ == "__main__":
    unittest.main()
