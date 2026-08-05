from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import div_contract


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "reference" / "component-contracts" / "div.json"
MANIFEST_PATH = ROOT / "reference" / "manifest.lock"


class DivContractSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = div_contract.load_json(CONTRACT_PATH)

    def changed(self) -> dict[str, object]:
        return copy.deepcopy(self.document)

    def test_locked_contract_validates(self) -> None:
        validated = div_contract.validate_contract(self.changed())
        self.assertEqual("div", validated["target"])
        self.assertEqual(9, len(validated["ports"]))
        self.assertEqual(33, validated["protocol"]["active_edges_to_complete"])
        self.assertEqual(
            34,
            validated["protocol"]["result"]["consecutive_request_edges_to_capture"],
        )
        self.assertEqual(div_contract.GENERATOR_MAIN, validated["generator_main"])

    def test_unknown_top_level_field_is_rejected(self) -> None:
        document = self.changed()
        document["unexpected"] = True
        with self.assertRaisesRegex(
            div_contract.DivContractError, "unknown=unexpected"
        ):
            div_contract.validate_contract(document)

    def test_duplicate_json_key_is_rejected(self) -> None:
        payload = CONTRACT_PATH.read_text(encoding="utf-8").replace(
            '"target": "div",', '"target": "div",\n  "target": "div",', 1
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaisesRegex(
                div_contract.DivContractError, "duplicate JSON key"
            ):
                div_contract.load_json(path)

    def test_path_traversal_is_rejected(self) -> None:
        document = self.changed()
        document["golden"]["path"] = "../rtl/div.v"
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)

    def test_exact_nine_ports_are_required(self) -> None:
        document = self.changed()
        del document["ports"]["complete"]
        with self.assertRaisesRegex(div_contract.DivContractError, "exactly"):
            div_contract.validate_contract(document)

    def test_wrong_port_width_is_rejected(self) -> None:
        document = self.changed()
        document["ports"]["r"]["width"] = 33
        with self.assertRaisesRegex(div_contract.DivContractError, "locked interface"):
            div_contract.validate_contract(document)

    def test_wrong_port_direction_is_rejected(self) -> None:
        document = self.changed()
        document["ports"]["complete"]["direction"] = "input"
        with self.assertRaisesRegex(div_contract.DivContractError, "locked interface"):
            div_contract.validate_contract(document)

    def test_reset_must_be_high_active_synchronous_clear(self) -> None:
        for field, replacement in (
            ("active_level", 0),
            ("behavior", "asynchronous_clear"),
        ):
            with self.subTest(field=field):
                document = self.changed()
                document["protocol"]["reset"][field] = replacement
                with self.assertRaises(div_contract.DivContractError):
                    div_contract.validate_contract(document)

    def test_request_must_be_level_and_held_through_result_capture(self) -> None:
        for field, replacement in (("mode", "pulse"), ("hold_through", "complete")):
            with self.subTest(field=field):
                document = self.changed()
                document["protocol"]["request"][field] = replacement
                with self.assertRaises(div_contract.DivContractError):
                    div_contract.validate_contract(document)

    def test_complete_must_assert_after_exactly_33_active_edges(self) -> None:
        for replacement in (32, 34):
            with self.subTest(active_edges=replacement):
                document = self.changed()
                document["protocol"]["active_edges_to_complete"] = replacement
                with self.assertRaises(div_contract.DivContractError):
                    div_contract.validate_contract(document)
        document = self.changed()
        document["protocol"]["complete"]["assert_after_consecutive_request_edges"] = 34
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)

    def test_complete_pulse_must_be_one_edge(self) -> None:
        document = self.changed()
        document["protocol"]["complete"]["pulse_edges"] = 2
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)

    def test_joint_result_capture_is_the_34th_request_edge(self) -> None:
        document = self.changed()
        document["protocol"]["result"]["consecutive_request_edges_to_capture"] = 33
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)
        document = self.changed()
        document["protocol"]["result"]["complete_level_during_valid_window"] = 1
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)

    def test_operand_stability_window_is_locked(self) -> None:
        document = self.changed()
        document["protocol"]["operands_stable"] = "from_accept_through_complete"
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)

    def test_abort_trigger_order_and_behavior_are_locked(self) -> None:
        document = self.changed()
        document["protocol"]["abort"]["triggers"].reverse()
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)
        document = self.changed()
        document["protocol"]["abort"]["behavior"] = "pause"
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)

    def test_rearm_schedule_is_locked(self) -> None:
        document = self.changed()
        document["protocol"]["rearm"]["held_high_cleanup_edges"] = 1
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)

    def test_arithmetic_edge_policies_are_locked(self) -> None:
        for field, replacement in (
            ("quotient", "floor"),
            ("signed_overflow", "saturate"),
        ):
            with self.subTest(field=field):
                document = self.changed()
                document["arithmetic"][field] = replacement
                with self.assertRaises(div_contract.DivContractError):
                    div_contract.validate_contract(document)
        document = self.changed()
        document["arithmetic"]["divide_by_zero"][
            "signed_negative_quotient"
        ] = "0xffffffff"
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)

    def test_generator_main_is_locked(self) -> None:
        document = self.changed()
        document["generator_main"] = "miku.DividerGen"
        with self.assertRaisesRegex(div_contract.DivContractError, "generator_main"):
            div_contract.validate_contract(document)

    def test_seed_is_locked_and_random_floor_is_enforced(self) -> None:
        document = self.changed()
        document["stimulus"]["seed"] = "0x1"
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)
        document = self.changed()
        document["stimulus"]["random_transactions"] = 4095
        with self.assertRaisesRegex(div_contract.DivContractError, ">= 4096"):
            div_contract.validate_contract(document)

    def test_boolean_fields_reject_integer_one(self) -> None:
        document = self.changed()
        document["diff"]["cycle_exact"] = 1
        with self.assertRaises(div_contract.DivContractError):
            div_contract.validate_contract(document)


class DivContractGoldenTests(unittest.TestCase):
    def test_windows_worktree_pointer_has_wsl_and_cygwin_candidates(self) -> None:
        candidates = div_contract._git_dir_candidates(
            Path("/workspace"), r"D:\repo\.git\worktrees\div"
        )
        if os.name == "nt":
            self.assertEqual([Path(r"D:\repo\.git\worktrees\div")], candidates)
        else:
            self.assertEqual(Path("/mnt/d/repo/.git/worktrees/div"), candidates[0])
            self.assertEqual(Path("/cygdrive/d/repo/.git/worktrees/div"), candidates[1])

    def test_locked_git_blob_oid_hash_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = div_contract.verify_contract(
                CONTRACT_PATH, MANIFEST_PATH, Path(temporary) / "summary"
            )
        self.assertEqual("pass", summary["status"])
        self.assertEqual(
            div_contract.GOLDEN_GIT_BLOB_SHA1,
            summary["golden"]["actual_git_blob_sha1"],
        )
        self.assertEqual(div_contract.GOLDEN_SHA256, summary["golden"]["actual_sha256"])
        self.assertEqual(div_contract.GOLDEN_SIZE, summary["golden"]["actual_size"])
        self.assertTrue(summary["golden"]["verified"])
        self.assertEqual(
            div_contract.sha256_file(Path(div_contract.__file__).resolve()),
            summary["evaluator_sha256"],
        )

    def test_manifest_commit_is_locked_not_just_well_formed(self) -> None:
        payload = MANIFEST_PATH.read_text(encoding="utf-8").replace(
            div_contract.GOLDEN_COMMIT, "0" * 40, 1
        )
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "manifest.lock"
            manifest.write_text(payload, encoding="utf-8")
            with self.assertRaisesRegex(
                div_contract.DivContractError, "locked golden commit"
            ):
                div_contract.parse_manifest(manifest)

    def test_hash_oid_and_size_tampering_fail_before_git_verification(self) -> None:
        mutations = (
            ("git_blob_sha1", "0" * 40, "git_blob_sha1"),
            ("sha256", "0" * 64, "golden.sha256"),
            ("size", 2641, "golden.size"),
        )
        for field, replacement, error in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                document = copy.deepcopy(div_contract.load_json(CONTRACT_PATH))
                document["golden"][field] = replacement
                contract = Path(temporary) / "div.json"
                contract.write_text(json.dumps(document), encoding="utf-8")
                with self.assertRaisesRegex(div_contract.DivContractError, error):
                    div_contract.verify_contract(
                        contract, MANIFEST_PATH, Path(temporary) / "out"
                    )

    def test_stale_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary) / "out"
            out_dir.mkdir()
            marker = out_dir / "stale.json"
            marker.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(div_contract.DivContractError, "must be fresh"):
                div_contract.verify_contract(CONTRACT_PATH, MANIFEST_PATH, out_dir)
            self.assertEqual("{}\n", marker.read_text(encoding="utf-8"))

    def test_output_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            output = root / "out"
            try:
                output.symlink_to(target, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlink creation unavailable: {error}")
            with self.assertRaisesRegex(
                div_contract.DivContractError, "must not be a symlink"
            ):
                div_contract.verify_contract(CONTRACT_PATH, MANIFEST_PATH, output)

    def test_fresh_cli_failure_writes_machine_readable_fail_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = copy.deepcopy(div_contract.load_json(CONTRACT_PATH))
            document["protocol"]["active_edges_to_complete"] = 34
            contract = root / "bad.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            out_dir = root / "out"
            result = div_contract.command_verify(
                argparse.Namespace(
                    contract=contract, manifest=MANIFEST_PATH, out_dir=out_dir
                )
            )
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(1, result)
        self.assertEqual("fail", summary["status"])
        self.assertEqual("div-contract", summary["gate"])

    def test_stale_cli_failure_does_not_overwrite_existing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary) / "out"
            out_dir.mkdir()
            marker = out_dir / "summary.json"
            marker.write_text('{"status":"prior"}\n', encoding="utf-8")
            result = div_contract.command_verify(
                argparse.Namespace(
                    contract=CONTRACT_PATH, manifest=MANIFEST_PATH, out_dir=out_dir
                )
            )
            preserved = marker.read_text(encoding="utf-8")
        self.assertEqual(2, result)
        self.assertEqual('{"status":"prior"}\n', preserved)


if __name__ == "__main__":
    unittest.main()
