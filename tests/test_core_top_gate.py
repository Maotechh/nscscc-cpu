from __future__ import annotations

import copy
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import core_top_gate


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PORTS_PATH = REPOSITORY_ROOT / "reference" / "core-top.ports.json"
MANIFEST_PATH = REPOSITORY_ROOT / "reference" / "manifest.lock"


def contract() -> dict[str, object]:
    return core_top_gate.load_port_contract(PORTS_PATH)


def complete_top_text(value: dict[str, object], *, parameter: bool = True) -> str:
    ports = value["ports"]
    assert isinstance(ports, list)
    declarations = []
    for raw in ports:
        assert isinstance(raw, dict)
        width = int(raw["width"])
        bit_range = "" if width == 1 else f" [{width - 1}:0]"
        declarations.append(f"  {raw['direction']} wire{bit_range} {raw['name']}")
    top = "module core_top"
    if parameter:
        top += " #(parameter TLBNUM = 32)"
    return (
        top
        + " (\n"
        + ",\n".join(declarations)
        + "\n);\n"
        + "  reg activity;\n"
        + "  always @(posedge aclk) activity <= ~activity;\n"
        + "endmodule\n"
    )


def yosys_document(value: dict[str, object]) -> dict[str, object]:
    ports = value["ports"]
    assert isinstance(ports, list)
    top_ports: dict[str, object] = {}
    next_bit = 2
    for raw in ports:
        assert isinstance(raw, dict)
        width = int(raw["width"])
        bits = list(range(next_bit, next_bit + width))
        next_bit += width
        top_ports[str(raw["name"])] = {"direction": raw["direction"], "bits": bits}
    return {
        "modules": {
            "core_top": {
                "ports": top_ports,
                "parameter_default_values": {
                    "TLBNUM": "00000000000000000000000000100000"
                },
                "cells": {
                    "state": {
                        "type": "$dff",
                        "parameters": {},
                        "connections": {},
                    }
                },
            }
        }
    }


class CoreTopContractTests(unittest.TestCase):
    def test_locked_contract_has_exact_counts_and_key_widths(self) -> None:
        value = contract()
        ports = value["ports"]
        self.assertEqual(49, len(ports))
        self.assertEqual(17, sum(port["direction"] == "input" for port in ports))
        self.assertEqual(32, sum(port["direction"] == "output" for port in ports))
        projection = {port["name"]: (port["direction"], port["width"]) for port in ports}
        self.assertEqual(("output", 8), projection["arlen"])
        self.assertEqual(("output", 8), projection["awlen"])
        self.assertEqual(("output", 4), projection["debug0_wb_rf_wen"])
        self.assertEqual([{"name": "TLBNUM", "default": 32}], value["parameters"])

    def test_locked_team_git_object_is_verified(self) -> None:
        value = contract()
        revision = core_top_gate.parse_lock(MANIFEST_PATH)["team_golden_candidate"]
        evidence = core_top_gate.verify_locked_source(
            REPOSITORY_ROOT, revision, value["sources"]["team_golden"], value
        )
        self.assertEqual("64725d67fb79cf1b43ee88f7a898ecd20052cdf0", evidence["blob_sha1"])
        self.assertEqual(49, len(evidence["ports"]))

    def test_contract_requires_chiplab_before_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "must-not-exist"
            args = SimpleNamespace(
                out_dir=out,
                repo_root=REPOSITORY_ROOT,
                manifest=MANIFEST_PATH,
                ports=PORTS_PATH,
                chiplab_mycpu=None,
            )
            with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "requires --chiplab"):
                core_top_gate.contract_gate(args)
            self.assertFalse(out.exists())

    def test_changed_port_width_cannot_match_locked_header(self) -> None:
        value = copy.deepcopy(contract())
        for port in value["ports"]:
            if port["name"] == "arlen":
                port["width"] = 4
        revision = core_top_gate.parse_lock(MANIFEST_PATH)["team_golden_candidate"]
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "ports or TLBNUM"):
            core_top_gate.verify_locked_source(
                REPOSITORY_ROOT,
                revision,
                value["sources"]["team_golden"],
                value,
            )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
            with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "duplicate JSON key"):
                core_top_gate.load_json_strict(path)


class CoreTopPackagingTests(unittest.TestCase):
    def test_top_parameter_insertion_is_deterministic(self) -> None:
        source = "module core_top (\n  input wire aclk\n);\nendmodule\n"
        parameterized, top_count = core_top_gate.ensure_top_parameter(source)
        self.assertEqual(1, top_count)
        self.assertIn("parameter TLBNUM = 32", parameterized)

    def test_existing_top_parameter_is_preserved_byte_for_byte(self) -> None:
        source = (
            "module core_top #(\n  parameter integer TLBNUM = 32\n) (\n);\nendmodule\n"
        )
        transformed, count = core_top_gate.ensure_top_parameter(source)
        self.assertEqual(0, count)
        self.assertEqual(source, transformed)

    def test_wrong_existing_top_parameter_is_rejected(self) -> None:
        source = "module core_top #(parameter TLBNUM = 16) ();\nendmodule\n"
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "unsupported default"):
            core_top_gate.ensure_top_parameter(source)

    def test_package_publishes_only_complete_spinal_rtl(self) -> None:
        generated = complete_top_text(contract(), parameter=False)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rtl = root / "generated.v"
            rtl.write_text(generated, encoding="utf-8")
            args = SimpleNamespace(
                out_dir=root / "package",
                repo_root=REPOSITORY_ROOT,
                manifest=MANIFEST_PATH,
                ports=PORTS_PATH,
                rtl=rtl,
            )
            summary = core_top_gate.package_gate(args)
            packaged_bytes = (args.out_dir / "rtl" / "mycpu_top.v").read_bytes()
            packaged = packaged_bytes.decode("utf-8")
        self.assertEqual("pass", summary["status"])
        self.assertEqual(1, packaged.count("module core_top #("))
        self.assertNotIn("openla500_legacy_core", packaged)
        self.assertIn("always @(posedge aclk)", packaged)
        self.assertTrue(summary["input_rtl"]["stable"])
        self.assertTrue(summary["contract"]["legacy_backend_absent"])
        self.assertEqual(49, summary["contract"]["port_count"])

    def test_package_rejects_any_legacy_backend_marker(self) -> None:
        generated = complete_top_text(contract(), parameter=False) + "// openla500_legacy_core\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rtl = root / "generated.v"
            rtl.write_text(generated, encoding="utf-8")
            args = SimpleNamespace(
                out_dir=root / "package",
                repo_root=REPOSITORY_ROOT,
                manifest=MANIFEST_PATH,
                ports=PORTS_PATH,
                rtl=rtl,
            )
            with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "must not contain"):
                core_top_gate.package_gate(args)


class CoreTopConnectivityTests(unittest.TestCase):
    def test_exact_top_contract_with_internal_logic_passes(self) -> None:
        value = contract()
        result = core_top_gate.validate_top_contract(yosys_document(value), value)
        self.assertEqual(1, result["top_cell_count"])
        self.assertTrue(result["legacy_backend_absent"])

    def test_port_width_mismatch_is_rejected(self) -> None:
        value = contract()
        document = yosys_document(value)
        document["modules"]["core_top"]["ports"]["arlen"]["bits"] = [1, 2, 3, 4]
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "ports differ"):
            core_top_gate.validate_top_contract(document, value)

    def test_legacy_module_is_rejected(self) -> None:
        value = contract()
        document = yosys_document(value)
        document["modules"]["openla500_legacy_core"] = {"ports": {}}
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "still contains"):
            core_top_gate.validate_top_contract(document, value)

    def test_arbitrary_internal_logic_is_allowed(self) -> None:
        value = contract()
        document = yosys_document(value)
        document["modules"]["core_top"]["cells"]["extra"] = {
            "type": "$not",
            "connections": {},
        }
        result = core_top_gate.validate_top_contract(document, value)
        self.assertEqual(2, result["top_cell_count"])

    def test_top_tlbnum_mismatch_is_rejected(self) -> None:
        value = contract()
        document = yosys_document(value)
        document["modules"]["core_top"]["parameter_default_values"]["TLBNUM"] = (
            "00000000000000000000000000011111"
        )
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "TLBNUM parameter mismatch"):
            core_top_gate.validate_top_contract(document, value)

    def test_tool_failure_cannot_be_reported_as_port_pass(self) -> None:
        value = contract()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rtl = root / "mycpu_top.v"
            rtl.write_text(complete_top_text(value), encoding="utf-8")
            manifest = root / "manifest.lock"
            manifest.write_text("yosys_binary_sha256=" + "0" * 64 + "\n", encoding="utf-8")
            args = SimpleNamespace(
                out_dir=root / "port",
                repo_root=REPOSITORY_ROOT,
                manifest=manifest,
                ports=PORTS_PATH,
                rtl=rtl,
                yosys=None,
                timeout=10,
            )
            failure = {
                "returncode": 1,
                "timed_out": False,
                "warnings": [],
                "skip_markers": [],
                "stdout": "ERROR",
            }
            with mock.patch.object(core_top_gate, "run_yosys", return_value=failure):
                with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "failed or warned"):
                    core_top_gate.port_check_gate(args)

    def test_port_check_reads_complete_rtl_without_a_backend_stub(self) -> None:
        value = contract()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rtl = root / "mycpu_top.v"
            rtl.write_text(complete_top_text(value) + "module helper; endmodule\n", encoding="utf-8")
            args = SimpleNamespace(
                out_dir=root / "port",
                repo_root=REPOSITORY_ROOT,
                manifest=MANIFEST_PATH,
                ports=PORTS_PATH,
                rtl=rtl,
                yosys=None,
                timeout=10,
            )
            captured: dict[str, str] = {}

            def fake_yosys(_values, _supplied, script, out_dir, _timeout):
                captured["script"] = script
                (out_dir / "core_top-raw.json").write_text(
                    json.dumps(yosys_document(value)), encoding="utf-8"
                )
                return {
                    "returncode": 0,
                    "timed_out": False,
                    "warnings": [],
                    "skip_markers": [],
                    "stdout": "",
                }

            with mock.patch.object(core_top_gate, "run_yosys", side_effect=fake_yosys):
                summary = core_top_gate.port_check_gate(args)
        self.assertEqual("complete-spinal-rtl", summary["scope"])
        self.assertEqual(1, captured["script"].count("read_verilog"))
        self.assertNotIn("openla500_legacy_core", captured["script"])
        self.assertTrue(summary["input"]["stable"])


class CoreTopStaticGateTests(unittest.TestCase):
    def _args(self, root: Path, command: str) -> SimpleNamespace:
        rtl = root / "mycpu_top.v"
        rtl.write_text(complete_top_text(contract()), encoding="utf-8")
        return SimpleNamespace(
            out_dir=root / command,
            repo_root=REPOSITORY_ROOT,
            manifest=MANIFEST_PATH,
            ports=PORTS_PATH,
            rtl=rtl,
            verilator=None,
            yosys=None,
            timeout=10,
        )

    def test_lint_invokes_verilator_on_one_complete_rtl_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary), "lint")
            commands: list[list[str]] = []
            version = core_top_gate.parse_lock(MANIFEST_PATH)["verilator"]

            def fake_command(argv, *, cwd, timeout):
                commands.append(argv)
                stdout = f"Verilator {version}\n" if "--version" in argv else ""
                return {
                    "argv": argv,
                    "returncode": 0,
                    "stdout": stdout,
                    "timed_out": False,
                    "elapsed_seconds": 0.01,
                }

            with mock.patch.object(
                core_top_gate, "checked_tool", return_value=Path(sys.executable)
            ), mock.patch.object(core_top_gate, "run_command", side_effect=fake_command):
                summary = core_top_gate.lint_gate(args)
        lint_argv = commands[1]
        self.assertEqual(1, sum(item.endswith("core_top.v") for item in lint_argv))
        self.assertFalse(any("legacy" in item for item in lint_argv))
        self.assertEqual("complete-spinal-rtl", summary["scope"])

    def test_yosys_check_reads_one_complete_rtl_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = self._args(Path(temporary), "yosys")
            captured: dict[str, str] = {}

            def fake_yosys(_values, _supplied, script, _out_dir, _timeout):
                captured["script"] = script
                return {
                    "returncode": 0,
                    "timed_out": False,
                    "warnings": [],
                    "skip_markers": [],
                    "stdout": "",
                }

            with mock.patch.object(core_top_gate, "run_yosys", side_effect=fake_yosys):
                summary = core_top_gate.yosys_check_gate(args)
        self.assertEqual(1, captured["script"].count("read_verilog"))
        self.assertNotIn("openla500_legacy_core", captured["script"])
        self.assertIn("hierarchy -check -top core_top", captured["script"])
        self.assertIn("\nproc\n", captured["script"])
        self.assertEqual("complete-spinal-rtl", summary["scope"])


class CoreTopSafetyTests(unittest.TestCase):
    def test_warning_and_skip_detection_is_case_insensitive(self) -> None:
        self.assertEqual(["%wArNiNg-WIDTH: bad"], core_top_gate.warning_lines("%wArNiNg-WIDTH: bad\n"))
        self.assertEqual(["result: skipped"], core_top_gate.skip_lines("result: skipped\n"))
        self.assertEqual(["SKIP"], core_top_gate.skip_lines("SKIP\n"))
        self.assertEqual([], core_top_gate.skip_lines("Skipping optimization\n"))

    def test_lstat_rejects_symlink_before_resolve(self) -> None:
        fake = SimpleNamespace(st_mode=stat.S_IFLNK)
        with mock.patch.object(core_top_gate.os, "lstat", return_value=fake), mock.patch.object(
            Path, "resolve", side_effect=AssertionError("resolve must not run")
        ):
            with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "symlink"):
                core_top_gate.checked_regular_file(Path("unsafe"), "manifest.lock")

    def test_failure_summary_does_not_create_unvalidated_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "unsafe"
            args = SimpleNamespace(out_dir=out, command="contract")
            core_top_gate._failure_summary(args, core_top_gate.CoreTopGateError("bad"))
            self.assertFalse(out.exists())

    def test_unsafe_output_symlink_is_rejected_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            link = root / "out"
            try:
                os.symlink(target, link, target_is_directory=True)
            except OSError:
                fake = SimpleNamespace(st_mode=stat.S_IFLNK)
                with mock.patch.object(core_top_gate.os, "lstat", return_value=fake):
                    with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "symlink"):
                        core_top_gate.ensure_fresh_out(link, "test")
            else:
                with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "symlink"):
                    core_top_gate.ensure_fresh_out(link, "test")
            self.assertEqual([], list(target.iterdir()))


class CoreTopPublishTests(unittest.TestCase):
    def _fixture(self, root: Path, *, tracked: bytes = b"package", spec_hash: str | None = None):
        repo = root / "repo"
        published = repo / core_top_gate.PUBLISHED_SOURCE
        published.parent.mkdir(parents=True)
        published.write_bytes(tracked)
        fresh = root / "fresh.v"
        fresh.write_bytes(b"package")
        replacement_hash = spec_hash or core_top_gate.sha256_bytes(b"package")
        spec = root / "core-top.json"
        spec.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "replacements": [
                        {
                            "target": core_top_gate.PUBLISHED_TARGET,
                            "source": core_top_gate.PUBLISHED_SOURCE,
                            "base_sha256": contract()["sources"]["team_golden"][
                                "raw_sha256"
                            ],
                            "replacement_sha256": replacement_hash,
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(
            repo_root=repo,
            manifest=MANIFEST_PATH,
            ports=PORTS_PATH,
            rtl=fresh,
            tracked_rtl=published,
            replacement_spec=spec,
            out_dir=root / "out",
        )

    def test_publish_check_requires_exact_bytes_hash_target_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = self._fixture(Path(temporary))
            with mock.patch.object(core_top_gate, "repository_provenance", return_value={}):
                summary = core_top_gate.publish_check_gate(args)
            self.assertEqual("pass", summary["status"])
            self.assertEqual(core_top_gate.sha256_bytes(b"package"), summary["package_sha256"])

    def test_stale_tracked_package_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = self._fixture(Path(temporary), tracked=b"stale")
            with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "stale"):
                core_top_gate.publish_check_gate(args)
            self.assertFalse(args.out_dir.exists())

    def test_stale_replacement_spec_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = self._fixture(Path(temporary), spec_hash="0" * 64)
            with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "hash differs"):
                core_top_gate.publish_check_gate(args)
            self.assertFalse(args.out_dir.exists())


class CoreTopCliTests(unittest.TestCase):
    def test_non_positive_timeout_is_rejected(self) -> None:
        code = core_top_gate.main(
            [
                "contract",
                "--chiplab-mycpu",
                ".",
                "--out-dir",
                "unused",
                "--timeout",
                "0",
            ]
        )
        self.assertEqual(2, code)


if __name__ == "__main__":
    unittest.main()
