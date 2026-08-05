#!/usr/bin/env python3
"""Validate the locked openLA500 divider contract and golden Git blob."""

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
TARGET = "div"
MODULE = "div"
GENERATED_FILE = "div.v"
GENERATOR_MAIN = "miku.execute.GenerateOpenLa500Div"
GOLDEN_COMMIT_KEY = "team_golden_candidate"
GOLDEN_COMMIT = "a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6"
GOLDEN_PATH = "rtl/div.v"
GOLDEN_GIT_BLOB_SHA1 = "225827c7d69addd280cb671c17e067a406a9171f"
GOLDEN_SHA256 = "7e499f4c43c92154d1d4e21be2f269ac140b4f2b2d944677c71f6f4213b66dc6"
GOLDEN_SIZE = 2642
STIMULUS_SEED = "0x158aa8"
MIN_RANDOM_TRANSACTIONS = 4096

LOCKED_PORTS: dict[str, dict[str, object]] = {
    "div_clk": {"direction": "input", "width": 1},
    "reset": {"direction": "input", "width": 1},
    "div": {"direction": "input", "width": 1},
    "div_signed": {"direction": "input", "width": 1},
    "x": {"direction": "input", "width": 32},
    "y": {"direction": "input", "width": 32},
    "s": {"direction": "output", "width": 32},
    "r": {"direction": "output", "width": 32},
    "complete": {"direction": "output", "width": 1},
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
    "arithmetic",
    "stimulus",
    "diff",
}
GOLDEN_FIELDS = {"commit_key", "path", "git_blob_sha1", "sha256", "size"}
PROTOCOL_FIELDS = {
    "clock",
    "edge",
    "reset",
    "request",
    "operands_stable",
    "active_edges_to_complete",
    "complete",
    "result",
    "abort",
    "rearm",
    "unknown_policy",
}
RESET_FIELDS = {"signal", "active_level", "behavior"}
REQUEST_FIELDS = {"signal", "active_level", "mode", "accept", "hold_through"}
COMPLETE_FIELDS = {
    "signal",
    "active_level",
    "assert_after_consecutive_request_edges",
    "pulse_edges",
}
RESULT_FIELDS = {
    "capture_edge",
    "consecutive_request_edges_to_capture",
    "valid_window_edges",
    "complete_level_during_valid_window",
}
ABORT_FIELDS = {"triggers", "behavior"}
REARM_FIELDS = {"low_edges_before_restart", "held_high_cleanup_edges"}
ARITHMETIC_FIELDS = {
    "quotient",
    "remainder_sign",
    "signed_overflow",
    "divide_by_zero",
    "output_width",
}
DIVIDE_BY_ZERO_FIELDS = {
    "unsigned_quotient",
    "signed_nonnegative_quotient",
    "signed_negative_quotient",
    "remainder",
}
STIMULUS_FIELDS = {"seed", "random_transactions"}
DIFF_FIELDS = {"runner", "independent_model", "cycle_exact"}

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")


class DivContractError(ValueError):
    """Raised for a malformed or unverifiable divider contract."""


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
            raise DivContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise DivContractError(f"contract must be a regular file: {path}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DivContractError(f"invalid JSON contract {path}: {error}") from error


def _require_object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise DivContractError(f"{name} must be an object")
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
        raise DivContractError(f"{name} fields mismatch ({'; '.join(details)})")


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise DivContractError(f"{name} must be a non-empty string")
    return value


def _require_integer(value: Any, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DivContractError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise DivContractError(f"{name} must be >= {minimum}")
    return value


def _require_relative_posix_path(value: Any, name: str) -> str:
    path = _require_string(value, name)
    if "\\" in path or path.startswith(("/", "~")):
        raise DivContractError(f"{name} must be a relative POSIX path")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise DivContractError(f"{name} contains an invalid path segment")
    return path


def _require_exact(value: Any, expected: Any, name: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise DivContractError(f"{name} must be {expected!r}")


def validate_contract(document: Any) -> dict[str, Any]:
    """Return a deep copy after enforcing the complete locked div contract."""

    top = _require_object(document, "contract")
    _require_fields(top, TOP_FIELDS, "contract")
    _require_exact(top["schema_version"], SCHEMA_VERSION, "schema_version")
    _require_exact(top["target"], TARGET, "target")
    _require_exact(top["module"], MODULE, "module")
    if not IDENTIFIER.fullmatch(str(top["module"])):
        raise DivContractError("module is not a legal Verilog identifier")
    _require_exact(top["generated_file"], GENERATED_FILE, "generated_file")
    _require_exact(top["generator_main"], GENERATOR_MAIN, "generator_main")

    golden = _require_object(top["golden"], "golden")
    _require_fields(golden, GOLDEN_FIELDS, "golden")
    _require_exact(golden["commit_key"], GOLDEN_COMMIT_KEY, "golden.commit_key")
    _require_exact(golden["path"], GOLDEN_PATH, "golden.path")
    _require_relative_posix_path(golden["path"], "golden.path")
    if not isinstance(golden["git_blob_sha1"], str) or not HEX40.fullmatch(
        golden["git_blob_sha1"]
    ):
        raise DivContractError(
            "golden.git_blob_sha1 must be 40 lowercase hexadecimal characters"
        )
    _require_exact(
        golden["git_blob_sha1"], GOLDEN_GIT_BLOB_SHA1, "golden.git_blob_sha1"
    )
    if not isinstance(golden["sha256"], str) or not HEX64.fullmatch(golden["sha256"]):
        raise DivContractError(
            "golden.sha256 must be 64 lowercase hexadecimal characters"
        )
    _require_exact(golden["sha256"], GOLDEN_SHA256, "golden.sha256")
    _require_exact(golden["size"], GOLDEN_SIZE, "golden.size")

    ports = _require_object(top["ports"], "ports")
    if set(ports) != set(LOCKED_PORTS):
        raise DivContractError(
            "ports must contain exactly " + ", ".join(sorted(LOCKED_PORTS))
        )
    normalized_ports: dict[str, dict[str, object]] = {}
    for name, expected in LOCKED_PORTS.items():
        port = _require_object(ports[name], f"ports.{name}")
        _require_fields(port, {"direction", "width"}, f"ports.{name}")
        direction = _require_string(port["direction"], f"ports.{name}.direction")
        width = _require_integer(port["width"], f"ports.{name}.width", minimum=1)
        actual = {"direction": direction, "width": width}
        if actual != expected:
            raise DivContractError(f"ports.{name} does not match the locked interface")
        normalized_ports[name] = actual

    protocol = _require_object(top["protocol"], "protocol")
    _require_fields(protocol, PROTOCOL_FIELDS, "protocol")
    _require_exact(protocol["clock"], "div_clk", "protocol.clock")
    _require_exact(protocol["edge"], "posedge", "protocol.edge")

    reset = _require_object(protocol["reset"], "protocol.reset")
    _require_fields(reset, RESET_FIELDS, "protocol.reset")
    _require_exact(reset["signal"], "reset", "protocol.reset.signal")
    _require_exact(reset["active_level"], 1, "protocol.reset.active_level")
    _require_exact(
        reset["behavior"], "synchronous_clear_idle", "protocol.reset.behavior"
    )

    request = _require_object(protocol["request"], "protocol.request")
    _require_fields(request, REQUEST_FIELDS, "protocol.request")
    locked_request = {
        "signal": "div",
        "active_level": 1,
        "mode": "level",
        "accept": "first_active_edge_from_idle",
        "hold_through": "result_capture_edge",
    }
    for name, expected in locked_request.items():
        _require_exact(request[name], expected, f"protocol.request.{name}")

    _require_exact(
        protocol["operands_stable"],
        "from_accept_through_result_capture",
        "protocol.operands_stable",
    )
    _require_exact(
        protocol["active_edges_to_complete"], 33, "protocol.active_edges_to_complete"
    )

    complete = _require_object(protocol["complete"], "protocol.complete")
    _require_fields(complete, COMPLETE_FIELDS, "protocol.complete")
    locked_complete = {
        "signal": "complete",
        "active_level": 1,
        "assert_after_consecutive_request_edges": 33,
        "pulse_edges": 1,
    }
    for name, expected in locked_complete.items():
        _require_exact(complete[name], expected, f"protocol.complete.{name}")

    result = _require_object(protocol["result"], "protocol.result")
    _require_fields(result, RESULT_FIELDS, "protocol.result")
    locked_result = {
        "capture_edge": "first_posedge_after_complete",
        "consecutive_request_edges_to_capture": 34,
        "valid_window_edges": 1,
        "complete_level_during_valid_window": 0,
    }
    for name, expected in locked_result.items():
        _require_exact(result[name], expected, f"protocol.result.{name}")

    abort = _require_object(protocol["abort"], "protocol.abort")
    _require_fields(abort, ABORT_FIELDS, "protocol.abort")
    _require_exact(
        abort["triggers"],
        ["reset_active_edge", "request_low_before_result_capture"],
        "protocol.abort.triggers",
    )
    _require_exact(
        abort["behavior"],
        "synchronous_rearm_no_valid_result",
        "protocol.abort.behavior",
    )

    rearm = _require_object(protocol["rearm"], "protocol.rearm")
    _require_fields(rearm, REARM_FIELDS, "protocol.rearm")
    _require_exact(
        rearm["low_edges_before_restart"], 1, "protocol.rearm.low_edges_before_restart"
    )
    _require_exact(
        rearm["held_high_cleanup_edges"], 2, "protocol.rearm.held_high_cleanup_edges"
    )
    _require_exact(
        protocol["unknown_policy"],
        "ignore_results_before_capture_edge",
        "protocol.unknown_policy",
    )

    arithmetic = _require_object(top["arithmetic"], "arithmetic")
    _require_fields(arithmetic, ARITHMETIC_FIELDS, "arithmetic")
    locked_arithmetic = {
        "quotient": "truncate_toward_zero",
        "remainder_sign": "dividend",
        "signed_overflow": "wrap_32bit",
        "output_width": 32,
    }
    for name, expected in locked_arithmetic.items():
        _require_exact(arithmetic[name], expected, f"arithmetic.{name}")
    divide_by_zero = _require_object(
        arithmetic["divide_by_zero"], "arithmetic.divide_by_zero"
    )
    _require_fields(divide_by_zero, DIVIDE_BY_ZERO_FIELDS, "arithmetic.divide_by_zero")
    locked_divide_by_zero = {
        "unsigned_quotient": "0xffffffff",
        "signed_nonnegative_quotient": "0xffffffff",
        "signed_negative_quotient": "0x00000001",
        "remainder": "dividend_bits",
    }
    for name, expected in locked_divide_by_zero.items():
        _require_exact(
            divide_by_zero[name], expected, f"arithmetic.divide_by_zero.{name}"
        )

    stimulus = _require_object(top["stimulus"], "stimulus")
    _require_fields(stimulus, STIMULUS_FIELDS, "stimulus")
    _require_exact(stimulus["seed"], STIMULUS_SEED, "stimulus.seed")
    random_transactions = _require_integer(
        stimulus["random_transactions"], "stimulus.random_transactions", minimum=1
    )
    if random_transactions < MIN_RANDOM_TRANSACTIONS:
        raise DivContractError(
            f"stimulus.random_transactions must be >= {MIN_RANDOM_TRANSACTIONS}"
        )

    diff = _require_object(top["diff"], "diff")
    _require_fields(diff, DIFF_FIELDS, "diff")
    _require_exact(diff["runner"], "verilator_cycle", "diff.runner")
    _require_exact(diff["independent_model"], True, "diff.independent_model")
    _require_exact(diff["cycle_exact"], True, "diff.cycle_exact")

    normalized = json.loads(json.dumps(top))
    normalized["ports"] = normalized_ports
    return normalized


def parse_manifest(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise DivContractError(f"manifest must be a regular file: {path}")
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise DivContractError(f"cannot read manifest: {error}") from error
    for line_number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise DivContractError(f"manifest line {line_number} is not key=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or key in values:
            raise DivContractError(
                f"manifest line {line_number} has an invalid/duplicate key"
            )
        values[key] = value
    commit = values.get(GOLDEN_COMMIT_KEY, "")
    if not HEX40.fullmatch(commit):
        raise DivContractError(
            f"manifest {GOLDEN_COMMIT_KEY} must be a full 40-hex SHA"
        )
    if commit != GOLDEN_COMMIT:
        raise DivContractError(
            f"manifest {GOLDEN_COMMIT_KEY} is not the locked golden commit"
        )
    return values


def _git_dir_candidates(repo_root: Path, raw: str) -> list[Path]:
    candidates: list[Path] = []
    windows_drive = re.fullmatch(r"([A-Za-z]):[\\/](.+)", raw)
    if windows_drive and os.name != "nt":
        drive, suffix = windows_drive.groups()
        suffix = suffix.replace("\\", "/")
        candidates.extend(
            [
                Path(f"/mnt/{drive.lower()}/{suffix}"),
                Path(f"/cygdrive/{drive.lower()}/{suffix}"),
            ]
        )
    raw_path = Path(raw)
    candidates.append(raw_path if raw_path.is_absolute() else repo_root / raw_path)
    return candidates


def _resolve_git_dir(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git.resolve()
    if not dot_git.is_file():
        raise DivContractError(f"Git metadata is missing: {dot_git}")
    try:
        line = dot_git.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise DivContractError(f"cannot read Git worktree pointer: {error}") from error
    if not line.startswith("gitdir:"):
        raise DivContractError(f"invalid Git worktree pointer: {dot_git}")
    raw = line.removeprefix("gitdir:").strip()
    if not raw:
        raise DivContractError(f"empty Git worktree pointer: {dot_git}")
    for candidate in _git_dir_candidates(repo_root, raw):
        if candidate.is_dir():
            return candidate.resolve()
    raise DivContractError(f"Git worktree metadata target is missing: {raw}")


def _run_git(repo_root: Path, args: list[str]) -> bytes:
    git_dir = _resolve_git_dir(repo_root)
    try:
        result = subprocess.run(
            [
                "git",
                f"--git-dir={git_dir}",
                f"--work-tree={repo_root.resolve()}",
                *args,
            ],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DivContractError(f"cannot execute git: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise DivContractError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _verify_allowlist(repo_root: Path, golden_path: str) -> None:
    allowlist = repo_root / "reference" / "golden-rtl-files.lock"
    if allowlist.is_symlink() or not allowlist.is_file():
        raise DivContractError(f"golden RTL allowlist is missing: {allowlist}")
    try:
        entries = {
            line.strip()
            for line in allowlist.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    except (OSError, UnicodeError) as error:
        raise DivContractError(f"cannot read golden RTL allowlist: {error}") from error
    if golden_path not in entries:
        raise DivContractError(
            f"golden path is not in the locked allowlist: {golden_path}"
        )


def verify_contract(
    contract_path: Path, manifest_path: Path, out_dir: Path
) -> dict[str, Any]:
    """Verify schema, provenance, object identity and the exact golden blob."""

    contract_input = Path(contract_path).expanduser()
    manifest_input = Path(manifest_path).expanduser()
    out_input = Path(out_dir).expanduser()
    if contract_input.is_symlink():
        raise DivContractError(f"contract must not be a symlink: {contract_input}")
    if manifest_input.is_symlink():
        raise DivContractError(f"manifest must not be a symlink: {manifest_input}")
    if out_input.is_symlink():
        raise DivContractError(f"output directory must not be a symlink: {out_input}")

    contract_path = contract_input.resolve()
    manifest_path = manifest_input.resolve()
    out_dir = out_input.resolve()
    if out_dir.exists():
        if not out_dir.is_dir():
            raise DivContractError(f"output path must be a directory: {out_dir}")
        if any(out_dir.iterdir()):
            raise DivContractError(f"output directory must be fresh: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    contract = validate_contract(load_json(contract_path))
    manifest = parse_manifest(manifest_path)
    repo_root = manifest_path.parent.parent
    _verify_allowlist(repo_root, str(contract["golden"]["path"]))

    commit = manifest[GOLDEN_COMMIT_KEY]
    blob_ref = f"{commit}:{contract['golden']['path']}"
    object_type = (
        _run_git(repo_root, ["cat-file", "-t", blob_ref])
        .decode("ascii", errors="replace")
        .strip()
    )
    if object_type != "blob":
        raise DivContractError(f"golden Git object is not a blob: {blob_ref}")
    object_id = (
        _run_git(repo_root, ["rev-parse", blob_ref])
        .decode("ascii", errors="replace")
        .strip()
    )
    if object_id != GOLDEN_GIT_BLOB_SHA1:
        raise DivContractError(
            f"golden Git blob SHA-1 mismatch: expected {GOLDEN_GIT_BLOB_SHA1}, got {object_id}"
        )
    payload = _run_git(repo_root, ["cat-file", "blob", blob_ref])
    actual_sha256 = sha256_bytes(payload)
    actual_size = len(payload)
    if actual_sha256 != contract["golden"]["sha256"]:
        raise DivContractError(
            "golden blob SHA256 mismatch: "
            f"expected {contract['golden']['sha256']}, got {actual_sha256}"
        )
    if actual_size != contract["golden"]["size"]:
        raise DivContractError(
            "golden blob size mismatch: "
            f"expected {contract['golden']['size']}, got {actual_size}"
        )

    head = (
        _run_git(repo_root, ["rev-parse", "HEAD"])
        .decode("ascii", errors="replace")
        .strip()
    )
    if not HEX40.fullmatch(head):
        raise DivContractError("cannot resolve repository HEAD")

    return {
        "schema_version": 1,
        "gate": "div-contract",
        "status": "pass",
        "generated_at": now_iso(),
        "evaluator_sha256": sha256_file(Path(__file__).resolve()),
        "repository_head": head,
        "contract": {"path": str(contract_path), "sha256": sha256_file(contract_path)},
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
            GOLDEN_COMMIT_KEY: commit,
        },
        "target": contract["target"],
        "module": contract["module"],
        "golden": {
            "commit": commit,
            "path": contract["golden"]["path"],
            "expected_git_blob_sha1": contract["golden"]["git_blob_sha1"],
            "actual_git_blob_sha1": object_id,
            "expected_sha256": contract["golden"]["sha256"],
            "actual_sha256": actual_sha256,
            "expected_size": contract["golden"]["size"],
            "actual_size": actual_size,
            "object_type": object_type,
            "verified": True,
        },
        "ports": contract["ports"],
        "protocol": contract["protocol"],
        "arithmetic": contract["arithmetic"],
        "stimulus": contract["stimulus"],
        "diff": contract["diff"],
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _write_failure(out_dir: Path, error: Exception) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "gate": "div-contract",
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
    except (DivContractError, OSError, ValueError, json.JSONDecodeError) as error:
        out_dir = args.out_dir.expanduser()
        if out_dir.is_symlink() or (
            out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir()))
        ):
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        summary = _write_failure(out_dir.resolve(), error)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 1
    write_json(args.out_dir.expanduser().resolve() / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser(
        "verify", help="verify the locked div contract and golden blob"
    )
    verify.add_argument("--contract", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--out-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    if not sys.flags.isolated:
        print(
            "div_contract.py requires isolated Python; invoke python -I",
            file=sys.stderr,
        )
        return 2
    args = build_parser().parse_args(argv)
    if args.command == "verify":
        return command_verify(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
