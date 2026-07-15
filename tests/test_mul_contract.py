from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import mul_contract


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "reference" / "component-contracts" / "mul.json"
MANIFEST_PATH = ROOT / "reference" / "manifest.lock"


class MulContractSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = mul_contract.load_json(CONTRACT_PATH)

    def test_locked_contract_validates(self) -> None:
        validated = mul_contract.validate_contract(copy.deepcopy(self.document))
        self.assertEqual("mul", validated["target"])
        self.assertEqual(64, validated["ports"]["result"]["width"])
        self.assertEqual(mul_contract.GENERATOR_MAIN, validated["generator_main"])

    def test_unknown_top_level_field_is_rejected(self) -> None:
        document = copy.deepcopy(self.document)
        document["unexpected"] = True
        with self.assertRaisesRegex(mul_contract.MulContractError, "unknown=unexpected"):
            mul_contract.validate_contract(document)

    def test_duplicate_json_key_is_rejected(self) -> None:
        payload = CONTRACT_PATH.read_text(encoding="utf-8").replace(
            '"target": "mul",', '"target": "mul",\n  "target": "mul",', 1
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaisesRegex(mul_contract.MulContractError, "duplicate JSON key"):
                mul_contract.load_json(path)

    def test_path_traversal_is_rejected(self) -> None:
        document = copy.deepcopy(self.document)
        document["golden"]["path"] = "../rtl/mul.v"
        with self.assertRaises(mul_contract.MulContractError):
            mul_contract.validate_contract(document)

    def test_wrong_port_width_is_rejected(self) -> None:
        document = copy.deepcopy(self.document)
        document["ports"]["result"]["width"] = 32
        with self.assertRaisesRegex(mul_contract.MulContractError, "does not match"):
            mul_contract.validate_contract(document)

    def test_reset_protocol_must_be_synchronous_hold(self) -> None:
        document = copy.deepcopy(self.document)
        document["protocol"]["reset"]["behavior"] = "asynchronous_clear"
        with self.assertRaises(mul_contract.MulContractError):
            mul_contract.validate_contract(document)

    def test_generator_main_must_be_the_locked_spinal_entry(self) -> None:
        document = copy.deepcopy(self.document)
        document["generator_main"] = None
        with self.assertRaisesRegex(mul_contract.MulContractError, "generator_main"):
            mul_contract.validate_contract(document)

    def test_random_vector_floor_is_enforced(self) -> None:
        document = copy.deepcopy(self.document)
        document["stimulus"]["random_vectors"] = 4095
        with self.assertRaises(mul_contract.MulContractError):
            mul_contract.validate_contract(document)


class MulContractGoldenTests(unittest.TestCase):
    def test_windows_worktree_pointer_has_wsl_and_cygwin_candidates(self) -> None:
        candidates = mul_contract._git_dir_candidates(
            Path("/workspace"), r"D:\repo\.git\worktrees\mul"
        )
        if os.name == "nt":
            self.assertEqual([Path(r"D:\repo\.git\worktrees\mul")], candidates)
        else:
            self.assertEqual(Path("/mnt/d/repo/.git/worktrees/mul"), candidates[0])
            self.assertEqual(Path("/cygdrive/d/repo/.git/worktrees/mul"), candidates[1])

    def test_locked_git_blob_hash_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = mul_contract.verify_contract(
                CONTRACT_PATH, MANIFEST_PATH, Path(temporary) / "summary"
            )
        self.assertEqual("pass", summary["status"])
        self.assertEqual(mul_contract.GOLDEN_SHA256, summary["golden"]["actual_sha256"])
        self.assertEqual(mul_contract.GOLDEN_SIZE, summary["golden"]["actual_size"])
        self.assertTrue(summary["golden"]["verified"])
        self.assertEqual(
            mul_contract.sha256_file(Path(mul_contract.__file__).resolve()),
            summary["evaluator_sha256"],
        )

    def test_hash_tampering_fails_before_git_verification(self) -> None:
        document = copy.deepcopy(mul_contract.load_json(CONTRACT_PATH))
        document["golden"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            contract = Path(temporary) / "mul.json"
            contract.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(mul_contract.MulContractError, "locked mul blob hash"):
                mul_contract.verify_contract(contract, MANIFEST_PATH, Path(temporary) / "out")

    def test_stale_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary) / "out"
            out_dir.mkdir()
            (out_dir / "stale.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(mul_contract.MulContractError, "must be fresh"):
                mul_contract.verify_contract(CONTRACT_PATH, MANIFEST_PATH, out_dir)

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
            with self.assertRaisesRegex(mul_contract.MulContractError, "must not be a symlink"):
                mul_contract.verify_contract(CONTRACT_PATH, MANIFEST_PATH, output)


if __name__ == "__main__":
    unittest.main()
