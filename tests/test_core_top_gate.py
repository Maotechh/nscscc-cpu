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


def top_wrapper_text(value: dict[str, object]) -> str:
    ports = value["ports"]
    assert isinstance(ports, list)
    declarations = []
    connections = []
    for raw in ports:
        assert isinstance(raw, dict)
        width = int(raw["width"])
        bit_range = "" if width == 1 else f" [{width - 1}:0]"
        declarations.append(f"  {raw['direction']} wire{bit_range} {raw['name']}")
        connections.append(f"    .{raw['name']}({raw['name']})")
    return (
        "module core_top #(parameter TLBNUM = 32) (\n"
        + ",\n".join(declarations)
        + "\n);\n"
        + "  openla500_legacy_core #(.TLBNUM(TLBNUM)) backend (\n"
        + ",\n".join(connections)
        + "\n  );\nendmodule\n\n"
        + "module openla500_legacy_core #(parameter TLBNUM = 32) ();\nendmodule\n"
    )


def yosys_document(value: dict[str, object]) -> dict[str, object]:
    ports = value["ports"]
    assert isinstance(ports, list)
    top_ports: dict[str, object] = {}
    connections: dict[str, object] = {}
    next_bit = 2
    for raw in ports:
        assert isinstance(raw, dict)
        width = int(raw["width"])
        bits = list(range(next_bit, next_bit + width))
        next_bit += width
        top_ports[str(raw["name"])] = {"direction": raw["direction"], "bits": bits}
        connections[str(raw["name"])] = list(bits)
    return {
        "modules": {
            "core_top": {
                "ports": top_ports,
                "parameter_default_values": {
                    "TLBNUM": "00000000000000000000000000100000"
                },
                "cells": {
                    "backend": {
                        "type": "openla500_legacy_core",
                        "parameters": {
                            "TLBNUM": "00000000000000000000000000100000"
                        },
                        "connections": connections,
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
    def test_top_parameter_and_backend_binding_are_deterministic(self) -> None:
        source = (
            "module core_top (\n  input wire aclk\n);\n"
            "  openla500_legacy_core #(\n    .TLBNUM(32)\n  ) backend ();\n"
            "endmodule\n"
        )
        parameterized, top_count = core_top_gate.add_top_parameter(source)
        forwarded, backend_count = core_top_gate.forward_backend_parameter(parameterized)
        self.assertEqual(1, top_count)
        self.assertEqual(1, backend_count)
        self.assertIn("parameter TLBNUM = 32", forwarded)
        self.assertIn(".TLBNUM(TLBNUM)", forwarded)
        self.assertNotIn(".TLBNUM(32)", forwarded)

    def test_tlbnum_in_comments_is_not_counted_or_rewritten(self) -> None:
        source = (
            "/* .TLBNUM(32) */\n"
            "// .TLBNUM(32)\n"
            "module core_top (\n);\n"
            "  openla500_legacy_core #(\n    .TLBNUM(32)\n  ) backend ();\n"
            "endmodule\n"
        )
        parameterized, _ = core_top_gate.add_top_parameter(source)
        forwarded, _ = core_top_gate.forward_backend_parameter(parameterized)
        self.assertIn("/* .TLBNUM(32) */", forwarded)
        self.assertIn("// .TLBNUM(32)", forwarded)
        self.assertEqual(1, core_top_gate.uncommented_tlbnum_binding_count(forwarded, "TLBNUM"))
        comments_only = "/*\n.TLBNUM(32)\n*/\n"
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "not unique"):
            core_top_gate.forward_backend_parameter(comments_only)

    def test_legacy_rename_changes_only_the_unique_module_identifier(self) -> None:
        source = b"module core_top #(parameter TLBNUM=32) ();\r\nendmodule\r\n"
        renamed, count = core_top_gate.rename_legacy_module(source)
        self.assertEqual(1, count)
        self.assertIn(b"module openla500_legacy_core", renamed)
        restored = renamed.replace(b"openla500_legacy_core", b"core_top", 1)
        self.assertEqual(source, restored)

    def test_legacy_non_unique_rename_is_rejected(self) -> None:
        duplicate = b"module core_top; endmodule\nmodule core_top; endmodule\n"
        missing = b"module another; endmodule\n"
        for payload in (duplicate, missing):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "not unique"):
                    core_top_gate.rename_legacy_module(payload)

    def test_package_uses_locked_legacy_blob(self) -> None:
        generated = (
            "module core_top (\n  input wire aclk\n);\n"
            "  openla500_legacy_core #(\n    .TLBNUM(32)\n  ) backend ();\n"
            "endmodule\n"
        )
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
        self.assertEqual(1, packaged.count("module openla500_legacy_core"))
        self.assertIn(".TLBNUM(TLBNUM)", packaged)
        expected_legacy, _ = core_top_gate.rename_legacy_module(
            core_top_gate.git_blob(
                REPOSITORY_ROOT,
                core_top_gate.parse_lock(MANIFEST_PATH)["team_golden_candidate"],
                "rtl/mycpu_top.v",
            )[0]
        )
        self.assertTrue(packaged_bytes.endswith(expected_legacy))
        self.assertTrue(summary["input_wrapper"]["stable"])
        self.assertEqual("ff286f559dbc9131349c9fb8c842110569d231b6a34e76ded172c403d8f90afa", summary["legacy_source"]["raw_sha256"])


class CoreTopConnectivityTests(unittest.TestCase):
    def test_exact_same_name_connectivity_passes(self) -> None:
        value = contract()
        result = core_top_gate.validate_connectivity(yosys_document(value), value)
        self.assertEqual(49, result["same_name_connections"])
        self.assertEqual(1, result["top_cell_count"])

    def test_port_width_mismatch_is_rejected(self) -> None:
        value = contract()
        document = yosys_document(value)
        document["modules"]["core_top"]["ports"]["arlen"]["bits"] = [1, 2, 3, 4]
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "ports differ"):
            core_top_gate.validate_connectivity(document, value)

    def test_missing_or_crossed_connection_is_rejected(self) -> None:
        value = contract()
        document = yosys_document(value)
        top = document["modules"]["core_top"]
        top["cells"]["backend"]["connections"]["arready"] = top["ports"]["wready"]["bits"]
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "same-name"):
            core_top_gate.validate_connectivity(document, value)

    def test_extra_wrapper_logic_is_rejected(self) -> None:
        value = contract()
        document = yosys_document(value)
        document["modules"]["core_top"]["cells"]["extra"] = {
            "type": "$not",
            "connections": {},
        }
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "beyond"):
            core_top_gate.validate_connectivity(document, value)

    def test_backend_tlbnum_mismatch_is_rejected(self) -> None:
        value = contract()
        document = yosys_document(value)
        document["modules"]["core_top"]["cells"]["backend"]["parameters"][
            "TLBNUM"
        ] = "00000000000000000000000000011111"
        with self.assertRaisesRegex(core_top_gate.CoreTopGateError, "TLBNUM parameter mismatch"):
            core_top_gate.validate_connectivity(document, value)

    def test_tool_failure_cannot_be_reported_as_port_pass(self) -> None:
        value = contract()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rtl = root / "mycpu_top.v"
            rtl.write_text(top_wrapper_text(value), encoding="utf-8")
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
