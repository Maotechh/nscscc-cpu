import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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
            result = run(argparse.Namespace(rtl=rtl_path, root_module="core_top", overlay_dir=overlay_path, repo_root=None, out=out_path))
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

    def test_repository_allows_only_generated_top_and_testbenches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rtl = root / "rtl" / "mycpu_top.v"
            rtl.parent.mkdir()
            rtl.write_text("module core_top; endmodule\n", encoding="utf-8")
            testbench = root / "tests" / "rtl" / "if_stage_lockstep.sv"
            testbench.parent.mkdir(parents=True)
            testbench.write_text("module tb; endmodule\n", encoding="utf-8")
            out = root / "report.json"
            result = run(
                argparse.Namespace(
                    rtl=rtl,
                    root_module="core_top",
                    overlay_dir=None,
                    repo_root=root,
                    out=out,
                )
            )
            report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(0, result)
        self.assertEqual("pass", report["repository_purity_status"])

    def test_repository_rejects_historical_core_verilog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rtl = root / "rtl" / "mycpu_top.v"
            rtl.parent.mkdir()
            rtl.write_text("module core_top; endmodule\n", encoding="utf-8")
            legacy = root / "reference" / "component-replacements" / "alu.v"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("module alu; endmodule\n", encoding="utf-8")
            out = root / "report.json"
            result = run(
                argparse.Namespace(
                    rtl=rtl,
                    root_module="core_top",
                    overlay_dir=None,
                    repo_root=root,
                    out=out,
                )
            )
            report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(1, result)
        self.assertEqual("fail", report["repository_purity_status"])
        self.assertEqual(
            ["reference/component-replacements/alu.v"],
            report["repository_hdl"]["blocking_entries"],
        )


if __name__ == "__main__":
    unittest.main()
