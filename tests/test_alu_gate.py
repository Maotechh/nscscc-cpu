from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import alu_gate


class AluGateContractTests(unittest.TestCase):
    def test_warning_parser_is_fail_closed(self) -> None:
        self.assertEqual([], alu_gate.warning_lines("all clean\n"))
        self.assertEqual(
            ["%Warning-WIDTH: bad"], alu_gate.warning_lines("%Warning-WIDTH: bad\n")
        )
        self.assertEqual(["[warn] bad"], alu_gate.warning_lines("[warn] bad\n"))

    def test_output_under_repository_rtl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "rtl").mkdir()
            with self.assertRaises(alu_gate.AluGateError):
                alu_gate.ensure_outside_repo_rtl(repo / "rtl" / "generated", repo)
            alu_gate.ensure_outside_repo_rtl(repo / "build" / "generated", repo)

    def test_duplicate_manifest_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.lock"
            path.write_text("sbt=one\nsbt=two\n", encoding="utf-8")
            with self.assertRaises(alu_gate.AluGateError):
                alu_gate.parse_lock(path)

    def test_unsupported_target_returns_nonzero(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "alu_gate.py",
                "lint",
                "--target",
                "cache",
                "--manifest",
                "missing.lock",
                "--rtl",
                "missing.v",
                "--out-dir",
                "out",
            ],
        ):
            self.assertEqual(2, alu_gate.main())


class AluPortCheckTests(unittest.TestCase):
    def _args(self, root: Path) -> SimpleNamespace:
        rtl = root / "alu.v"
        rtl.write_text("module alu; endmodule\n", encoding="utf-8")
        manifest = root / "manifest.lock"
        manifest.write_text("yosys_binary_sha256=" + "0" * 64 + "\n", encoding="utf-8")
        return SimpleNamespace(
            out_dir=root / "out", rtl=rtl, manifest=manifest, timeout=10
        )

    def test_exact_yosys_port_projection_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = self._args(root)

            def fake_run(values, script, out_dir, timeout):
                document = {
                    "modules": {
                        "alu": {
                            "ports": {
                                name: {"direction": direction, "bits": list(range(width))}
                                for name, (direction, width) in alu_gate.ALU_PORTS.items()
                            }
                        }
                    }
                }
                (out_dir / "alu.json").write_text(json.dumps(document), encoding="utf-8")
                log = out_dir / "yosys.log"
                log.write_text("clean\n", encoding="utf-8")
                return {"returncode": 0, "warnings": [], "stdout": ""}, log

            with mock.patch.object(alu_gate, "run_yosys_script", side_effect=fake_run):
                self.assertEqual(0, alu_gate.port_check(args))

    def test_extra_clock_port_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = self._args(root)

            def fake_run(values, script, out_dir, timeout):
                ports = {
                    name: {"direction": direction, "bits": list(range(width))}
                    for name, (direction, width) in alu_gate.ALU_PORTS.items()
                }
                ports["clk"] = {"direction": "input", "bits": [0]}
                (out_dir / "alu.json").write_text(
                    json.dumps({"modules": {"alu": {"ports": ports}}}), encoding="utf-8"
                )
                log = out_dir / "yosys.log"
                log.write_text("clean\n", encoding="utf-8")
                return {"returncode": 0, "warnings": [], "stdout": ""}, log

            with mock.patch.object(alu_gate, "run_yosys_script", side_effect=fake_run):
                self.assertEqual(1, alu_gate.port_check(args))


if __name__ == "__main__":
    unittest.main()
