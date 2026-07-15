import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.candidate_closure_gate import run


class CandidateClosureGateTest(unittest.TestCase):
    def invoke(self, rtl: str, overlay: dict[str, str] | None = None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rtl_path = root / "core_top.v"
            out_path = root / "report.json"
            rtl_path.write_text(rtl, encoding="utf-8")
            overlay_path = None
            if overlay is not None:
                overlay_path = root / "overlay"
                overlay_path.mkdir()
                for name, content in overlay.items():
                    (overlay_path / name).write_text(content, encoding="utf-8")
            result = run(argparse.Namespace(rtl=rtl_path, root_module="core_top", overlay_dir=overlay_path, out=out_path))
            return result, json.loads(out_path.read_text(encoding="utf-8"))

    def test_spinal_closure_passes(self):
        result, report = self.invoke(
            "module core_top;\nmodule OpenLa500Alu; endmodule\n"
        )
        self.assertEqual(result, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["legacy_instances"], [])

    def test_legacy_instance_fails(self):
        result, report = self.invoke("module core_top;\nif_stage old0();\nendmodule\n")
        self.assertEqual(result, 1)
        self.assertEqual(report["legacy_instances"], ["if_stage"])

    def test_module_free_overlay_is_allowed(self):
        result, report = self.invoke(
            "module core_top; endmodule\n",
            {"if_stage.v": "// intentionally module-free deferred source\n"},
        )
        self.assertEqual(result, 0)
        self.assertEqual(report["pure_overlay_status"], "pass")

    def test_legacy_overlay_module_fails(self):
        result, report = self.invoke(
            "module core_top; endmodule\n",
            {"if_stage.v": "module if_stage; endmodule\n"},
        )
        self.assertEqual(result, 1)
        self.assertEqual(report["pure_overlay_status"], "fail")


if __name__ == "__main__":
    unittest.main()
