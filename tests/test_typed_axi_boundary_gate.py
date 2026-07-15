from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "typed_axi_boundary_gate.py"
RTL = REPO / "rtl" / "mycpu_top.v"
BACKEND = REPO / "spinal" / "src" / "main" / "scala" / "openla500" / "compat" / "SpinalCoreBackend.scala"
COMPAT = REPO / "spinal" / "src" / "main" / "scala" / "openla500" / "compat" / "CoreTopCompat.scala"
BRIDGE = REPO / "spinal" / "src" / "main" / "scala" / "openla500" / "memory" / "OpenLa500AxiBridge.scala"


class TypedAxiBoundaryGateTest(unittest.TestCase):
    def run_gate(
        self,
        *,
        rtl_mutation: tuple[str, str] | None = None,
        bridge_mutation: tuple[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        with tempfile.TemporaryDirectory(prefix="typed-axi-gate-") as directory:
            root = Path(directory)
            rtl = root / "mycpu_top.v"
            bridge = root / "OpenLa500AxiBridge.scala"
            rtl_text = RTL.read_text(encoding="utf-8")
            bridge_text = BRIDGE.read_text(encoding="utf-8")
            if rtl_mutation is not None:
                old, new = rtl_mutation
                self.assertEqual(rtl_text.count(old), 1, f"RTL mutation anchor is not unique: {old}")
                rtl_text = rtl_text.replace(old, new, 1)
            if bridge_mutation is not None:
                old, new = bridge_mutation
                self.assertEqual(
                    bridge_text.count(old), 1, f"bridge mutation anchor is not unique: {old}"
                )
                bridge_text = bridge_text.replace(old, new, 1)
            rtl.write_text(rtl_text, encoding="utf-8")
            bridge.write_text(bridge_text, encoding="utf-8")
            report = root / "summary.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(SCRIPT),
                    "--rtl",
                    str(rtl),
                    "--backend-source",
                    str(BACKEND),
                    "--compat-source",
                    str(COMPAT),
                    "--bridge-source",
                    str(bridge),
                    "--out",
                    str(report),
                ],
                cwd=REPO,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            return completed, json.loads(report.read_text(encoding="utf-8"))

    def assert_rejected(self, **mutations: tuple[str, str]) -> None:
        completed, report = self.run_gate(**mutations)
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["failures"])

    def test_current_boundary_passes(self) -> None:
        completed, report = self.run_gate()
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["failures"], [])

    def test_rejects_generated_wire_width_change(self) -> None:
        self.assert_rejected(
            rtl_mutation=(
                "wire       [3:0]    backendArea_core_axi_ar_payload_id;",
                "wire       [4:0]    backendArea_core_axi_ar_payload_id;",
            )
        )

    def test_rejects_truncated_input_slice(self) -> None:
        self.assert_rejected(
            rtl_mutation=(
                ".axi_r_payload_id               (rid[3:0]",
                ".axi_r_payload_id               (rid[2:0]",
            )
        )

    def test_rejects_backend_port_direction_change(self) -> None:
        self.assert_rejected(
            rtl_mutation=(
                "module SpinalCoreBackend (\n"
                "  input  wire          aclk,\n"
                "  input  wire          aresetn,\n"
                "  input  wire [7:0]    intrpt,\n"
                "  output wire          axi_ar_valid,\n"
                "  input  wire          axi_ar_ready,\n"
                "  output wire [3:0]    axi_ar_payload_id,",
                "module SpinalCoreBackend (\n"
                "  input  wire          aclk,\n"
                "  input  wire          aresetn,\n"
                "  input  wire [7:0]    intrpt,\n"
                "  output wire          axi_ar_valid,\n"
                "  input  wire          axi_ar_ready,\n"
                "  input  wire [3:0]    axi_ar_payload_id,",
            )
        )

    def test_rejects_non_direct_core_top_mapping(self) -> None:
        self.assert_rejected(
            rtl_mutation=(
                "assign arid = backendArea_core_axi_ar_payload_id;",
                "assign arid = {backendArea_core_axi_ar_payload_id};",
            )
        )

    def test_rejects_internal_response_field_swap(self) -> None:
        self.assert_rejected(
            bridge_mutation=(
                "legacy.io.rid := io.axi.r.payload.id",
                "legacy.io.rid := io.axi.b.payload.id",
            )
        )

    def test_rejects_inverted_ready(self) -> None:
        self.assert_rejected(
            bridge_mutation=(
                "io.axi.r.ready := legacy.io.rready",
                "io.axi.r.ready := !legacy.io.rready",
            )
        )

    def test_rejects_stateful_adapter(self) -> None:
        self.assert_rejected(
            bridge_mutation=(
                "io.axi.r.ready := legacy.io.rready",
                "val delayedReady = RegNext(legacy.io.rready)\n  io.axi.r.ready := delayedReady",
            )
        )

    def test_comments_cannot_preserve_a_changed_direction(self) -> None:
        self.assert_rejected(
            bridge_mutation=(
                "val axi = master(Axi3Compat())",
                "// val axi = master(Axi3Compat())\n    val axi = slave(Axi3Compat())",
            )
        )


if __name__ == "__main__":
    unittest.main()
