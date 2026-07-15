#!/usr/bin/env python3
"""Validate the locked openLA500 multiplier contract and golden Git blob."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping


SCHEMA_VERSION = 1
TARGET = "mul"
MODULE = "mul"
GENERATED_FILE = "mul.v"
GOLDEN_COMMIT_KEY = "team_golden_candidate"
GOLDEN_PATH = "rtl/mul.v"
GOLDEN_SHA256 = "251d2bba3e659c294c9a004bbb2b542435fcfa0b0c1582cc1a7a3edca765a4c0"
GOLDEN_SIZE = 6045
GENERATOR_MAIN = "openla500.execute.GenerateOpenLa500Mul"
LOCKED_PORTS: dict[str, dict[str, object]] = {
    "mul_clk": {"direction": "input", "width": 1},
    "reset": {"direction": "input", "width": 1},
    "mul_signed": {"direction": "input", "width": 1},
    "x": {"direction": "input", "width": 32},
    "y": {"direction": "input", "width": 32},
    "result": {"direction": "output", "width": 64},
}
TOP_FIELDS = {
    "schema_version",
    "target",
    "module",
    "generated_file",
    "generator_main",
    "golden",
    "ports",
    "protocol",
    "stimulus",
    "diff",
}
GOLDEN_FIELDS = {"commit_key", "path", "sha256", "size"}
PROTOCOL_FIELDS = {
    "clock",
    "edge",
    "reset",
    "capture_when",
    "latency_edges",
    "warmup_active_edges",
    "unknown_policy",
    "throughput_per_cycle",
}
RESET_FIELDS = {"signal", "active_level", "behavior"}
STIMULUS_FIELDS = {"seed", "random_vectors"}
DIFF_FIELDS = {"runner", "independent_model"}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SEED = re.compile(r"0x[0-9a-f]+\Z")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")


class MulContractError(ValueError):
    """Raised for a malformed or unverifiable multiplier contract."""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = OrderedDict()
    for key, value in pairs:
        if key in result:
            raise MulContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise MulContractError(f"contract must be a regular file: {path}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MulContractError(f"invalid JSON contract {path}: {error}") from error


def _require_object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise MulContractError(f"{name} must be an object")
    return value


def _require_fields(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if unknown:
            details.append(f"unknown={','.join(unknown)}")
        raise MulContractError(f"{name} fields mismatch ({'; '.join(details)})")


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise MulContractError(f"{name} must be a non-empty string")
    return value


def _require_integer(value: Any, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MulContractError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise MulContractError(f"{name} must be >= {minimum}")
    return value


def _require_relative_posix_path(value: Any, name: str) -> str:
    path = _require_string(value, name)
    if "\\" in path or path.startswith("/") or path.startswith("~"):
        raise MulContractError(f"{name} must be a relative POSIX path")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise MulContractError(f"{name} contains an invalid path segment")
    return path


def validate_contract(document: Any) -> dict[str, Any]:
    """Validate and return a contract with immutable, locked mul semantics."""

    top = _require_object(document, "contract")
    _require_fields(top, TOP_FIELDS, "contract")
    if _require_integer(top["schema_version"], "schema_version", minimum=1) != SCHEMA_VERSION:
        raise MulContractError(f"schema_version must be {SCHEMA_VERSION}")
    if top["target"] != TARGET:
        raise MulContractError(f"target must be {TARGET!r}")
    if top["module"] != MODULE or not IDENTIFIER.fullmatch(str(top["module"])):
        raise MulContractError("module must be the Verilog identifier 'mul'")
    if top["generated_file"] != GENERATED_FILE:
        raise MulContractError(f"generated_file must be {GENERATED_FILE!r}")
    if top["generator_main"] != GENERATOR_MAIN:
        raise MulContractError(f"generator_main must be {GENERATOR_MAIN}")

    golden = _require_object(top["golden"], "golden")
    _require_fields(golden, GOLDEN_FIELDS, "golden")
    if golden["commit_key"] != GOLDEN_COMMIT_KEY:
        raise MulContractError(f"golden.commit_key must be {GOLDEN_COMMIT_KEY!r}")
    if golden["path"] != GOLDEN_PATH:
        raise MulContractError(f"golden.path must be {GOLDEN_PATH!r}")
    _require_relative_posix_path(golden["path"], "golden.path")
    if not isinstance(golden["sha256"], str) or not HEX64.fullmatch(golden["sha256"]):
        raise MulContractError("golden.sha256 must be 64 lowercase hexadecimal characters")
    if golden["sha256"] != GOLDEN_SHA256:
        raise MulContractError("golden.sha256 is not the locked mul blob hash")
    if _require_integer(golden["size"], "golden.size", minimum=1) != GOLDEN_SIZE:
        raise MulContractError("golden.size is not the locked mul blob size")

    ports = _require_object(top["ports"], "ports")
    if set(ports) != set(LOCKED_PORTS):
        raise MulContractError(
            "ports must contain exactly " + ", ".join(sorted(LOCKED_PORTS))
        )
    normalized_ports: dict[str, dict[str, object]] = {}
    for name, expected in LOCKED_PORTS.items():
        port = _require_object(ports[name], f"ports.{name}")
        if set(port) != {"direction", "width"}:
            raise MulContractError(f"ports.{name} fields must be direction,width")
        direction = _require_string(port["direction"], f"ports.{name}.direction")
        if direction not in {"input", "output", "inout"}:
            raise MulContractError(f"ports.{name}.direction is invalid")
        width = _require_integer(port["width"], f"ports.{name}.width", minimum=1)
        if {"direction": direction, "width": width} != expected:
            raise MulContractError(f"ports.{name} does not match the locked interface")
        normalized_ports[name] = {"direction": direction, "width": width}

    protocol = _require_object(top["protocol"], "protocol")
    _require_fields(protocol, PROTOCOL_FIELDS, "protocol")
    if protocol["clock"] != "mul_clk" or protocol["edge"] != "posedge":
        raise MulContractError("protocol clock/edge must be mul_clk/posedge")
    reset = _require_object(protocol["reset"], "protocol.reset")
    _require_fields(reset, RESET_FIELDS, "protocol.reset")
    if reset["signal"] != "reset" or reset["active_level"] != 1:
        raise MulContractError("protocol.reset must use reset active_level=1")
    if reset["behavior"] != "synchronous_hold":
        raise MulContractError("protocol.reset.behavior must be synchronous_hold")
    if protocol["capture_when"] != "!reset":
        raise MulContractError("protocol.capture_when must be !reset")
    if _require_integer(protocol["latency_edges"], "protocol.latency_edges", minimum=1) != 1:
        raise MulContractError("protocol.latency_edges must be 1")
    if (
        _require_integer(protocol["warmup_active_edges"], "protocol.warmup_active_edges", minimum=1)
        < protocol["latency_edges"]
    ):
        raise MulContractError("protocol.warmup_active_edges must cover latency_edges")
    if protocol["unknown_policy"] != "ignore_before_first_active_capture":
        raise MulContractError("protocol.unknown_policy is invalid")
    if protocol["throughput_per_cycle"] is not True:
        raise MulContractError("protocol.throughput_per_cycle must be true")

    stimulus = _require_object(top["stimulus"], "stimulus")
    _require_fields(stimulus, STIMULUS_FIELDS, "stimulus")
    if not isinstance(stimulus["seed"], str) or not SEED.fullmatch(stimulus["seed"]):
        raise MulContractError("stimulus.seed must be a lowercase hexadecimal 0x string")
    if _require_integer(stimulus["random_vectors"], "stimulus.random_vectors", minimum=4096) < 4096:
        raise MulContractError("stimulus.random_vectors must be >= 4096")

    diff = _require_object(top["diff"], "diff")
    _require_fields(diff, DIFF_FIELDS, "diff")
    if diff["runner"] != "verilator_cycle":
        raise MulContractError("diff.runner must be verilator_cycle")
    if diff["independent_model"] is not True:
        raise MulContractError("diff.independent_model must be true")

    # Return a deep JSON-shaped copy so callers cannot mutate the parsed object
    # while the verification summary is being built.
    return json.loads(json.dumps(top))


def parse_manifest(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise MulContractError(f"manifest must be a regular file: {path}")
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise MulContractError(f"cannot read manifest: {error}") from error
    for line_number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise MulContractError(f"manifest line {line_number} is not key=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or key in values:
            raise MulContractError(f"manifest line {line_number} has an invalid/duplicate key")
        values[key] = value
    commit = values.get(GOLDEN_COMMIT_KEY, "")
    if not SHA40.fullmatch(commit):
        raise MulContractError(f"manifest {GOLDEN_COMMIT_KEY} must be a full 40-hex SHA")
    return values


def _git_dir_candidates(repo_root: Path, raw: str) -> list[Path]:
    candidates: list[Path] = []
    windows_drive = re.fullmatch(r"([A-Za-z]):[\\\\/](.+)", raw)
    if windows_drive and os.name != "nt":
        drive, suffix = windows_drive.groups()
        suffix = suffix.replace("\\", "/")
        candidates.extend(
            [Path(f"/mnt/{drive.lower()}/{suffix}"), Path(f"/cygdrive/{drive.lower()}/{suffix}")]
        )
    raw_path = Path(raw)
    candidates.append(raw_path if raw_path.is_absolute() else repo_root / raw_path)
    return candidates


def _resolve_git_dir(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git.resolve()
    if not dot_git.is_file():
        raise MulContractError(f"Git metadata is missing: {dot_git}")
    line = dot_git.read_text(encoding="utf-8").strip()
    if not line.startswith("gitdir:"):
        raise MulContractError(f"invalid Git worktree pointer: {dot_git}")
    raw = line.removeprefix("gitdir:").strip()
    for candidate in _git_dir_candidates(repo_root, raw):
        if candidate.is_dir():
            return candidate.resolve()
    raise MulContractError(f"Git worktree metadata target is missing: {raw}")


def _run_git(repo_root: Path, args: list[str]) -> bytes:
    git_dir = _resolve_git_dir(repo_root)
    try:
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", f"--work-tree={repo_root.resolve()}", *args],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except OSError as error:
        raise MulContractError(f"cannot execute git: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise MulContractError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _verify_allowlist(repo_root: Path, golden_path: str) -> None:
    allowlist = repo_root / "reference" / "golden-rtl-files.lock"
    if allowlist.is_symlink() or not allowlist.is_file():
        raise MulContractError(f"golden RTL allowlist is missing: {allowlist}")
    entries = {
        line.strip()
        for line in allowlist.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if golden_path not in entries:
        raise MulContractError(f"golden path is not in the locked allowlist: {golden_path}")


def verify_contract(contract_path: Path, manifest_path: Path, out_dir: Path) -> dict[str, Any]:
    """Verify schema, provenance and the exact locked golden blob."""

    contract_input = Path(contract_path).expanduser()
    manifest_input = Path(manifest_path).expanduser()
    out_input = Path(out_dir).expanduser()
    if contract_input.is_symlink():
        raise MulContractError(f"contract must not be a symlink: {contract_input}")
    if manifest_input.is_symlink():
        raise MulContractError(f"manifest must not be a symlink: {manifest_input}")
    if out_input.is_symlink():
        raise MulContractError(f"output directory must not be a symlink: {out_input}")
    contract_path = contract_input.resolve()
    manifest_path = manifest_input.resolve()
    out_dir = out_input.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise MulContractError(f"output directory must be fresh: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    contract = validate_contract(load_json(contract_path))
    manifest = parse_manifest(manifest_path)
    repo_root = manifest_path.parent.parent
    _verify_allowlist(repo_root, str(contract["golden"]["path"]))
    commit = manifest[GOLDEN_COMMIT_KEY]
    blob_ref = f"{commit}:{contract['golden']['path']}"
    # The object type check prevents a symlink/tree from being accepted as a blob.
    object_type = _run_git(repo_root, ["cat-file", "-t", blob_ref]).decode("ascii", errors="replace").strip()
    if object_type != "blob":
        raise MulContractError(f"golden Git object is not a blob: {blob_ref}")
    payload = _run_git(repo_root, ["cat-file", "blob", blob_ref])
    actual_sha = sha256_bytes(payload)
    actual_size = len(payload)
    if actual_sha != contract["golden"]["sha256"]:
        raise MulContractError(
            f"golden blob SHA256 mismatch: expected {contract['golden']['sha256']}, got {actual_sha}"
        )
    if actual_size != contract["golden"]["size"]:
        raise MulContractError(
            f"golden blob size mismatch: expected {contract['golden']['size']}, got {actual_size}"
        )
    head = _run_git(repo_root, ["rev-parse", "HEAD"]).decode("ascii", errors="replace").strip()
    if not SHA40.fullmatch(head):
        raise MulContractError("cannot resolve repository HEAD")
    summary: dict[str, Any] = {
        "schema_version": 1,
        "gate": "mul-contract",
        "status": "pass",
        "generated_at": now_iso(),
        "evaluator_sha256": sha256_file(Path(__file__).resolve()),
        "repository_head": head,
        "contract": {
            "path": str(contract_path),
            "sha256": sha256_file(contract_path),
        },
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
            "team_golden_candidate": commit,
        },
        "target": contract["target"],
        "module": contract["module"],
        "golden": {
            "commit": commit,
            "path": contract["golden"]["path"],
            "expected_sha256": contract["golden"]["sha256"],
            "actual_sha256": actual_sha,
            "expected_size": contract["golden"]["size"],
            "actual_size": actual_size,
            "object_type": object_type,
            "verified": True,
        },
        "ports": contract["ports"],
        "protocol": contract["protocol"],
        "stimulus": contract["stimulus"],
        "diff": contract["diff"],
    }
    return summary


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_failure(out_dir: Path, error: Exception) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "gate": "mul-contract",
        "status": "fail",
        "generated_at": now_iso(),
        "evaluator_sha256": sha256_file(Path(__file__).resolve()),
        "error": str(error),
    }
    write_json(out_dir / "summary.json", summary)
    return summary


def command_verify(args: argparse.Namespace) -> int:
    try:
        summary = verify_contract(args.contract, args.manifest, args.out_dir)
    except (MulContractError, OSError, ValueError, json.JSONDecodeError) as error:
        # A stale report must never be consumed as a successful verification.
        out_dir = args.out_dir.resolve()
        if out_dir.exists() and any(out_dir.iterdir()):
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        summary = _write_failure(out_dir, error)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 1
    write_json(args.out_dir.resolve() / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify", help="verify the locked mul contract and golden blob")
    verify.add_argument("--contract", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--out-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    if not sys.flags.isolated:
        print("mul_contract.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    if args.command == "verify":
        return command_verify(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
