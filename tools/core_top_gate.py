#!/usr/bin/env python3
"""Fail-closed contract, packaging, and whole-RTL static gates for ``core_top``."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from typing import Any


TARGET = "core-top-compat"
TOP_MODULE = "core_top"
FORBIDDEN_LEGACY_MARKER = "openla500_legacy_core"
EXPECTED_PORT_COUNT = 49
EXPECTED_INPUT_COUNT = 17
EXPECTED_OUTPUT_COUNT = 32
PUBLISHED_TARGET = "rtl/mycpu_top.v"
PUBLISHED_SOURCE = "reference/component-replacements/mycpu_top.v"
ALLOWED_CONTRACT_KEYS = {
    "schema_version",
    "module",
    "port_count",
    "input_count",
    "output_count",
    "parameters",
    "sources",
    "clock_reset",
    "ports",
    "known_integration_risks",
}


class CoreTopGateError(RuntimeError):
    """Raised when evidence cannot establish the requested gate."""


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


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CoreTopGateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_strict(path: Path) -> dict[str, Any]:
    path = checked_regular_file(path, "JSON input")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CoreTopGateError(f"invalid JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise CoreTopGateError(f"JSON root must be an object: {path}")
    return value


def parse_lock(path: Path) -> dict[str, str]:
    path = checked_regular_file(path, "manifest.lock")
    result: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise CoreTopGateError(f"{path}:{line_number}: expected key=value")
        key, value = (item.strip() for item in line.split("=", 1))
        if not key or key in result:
            raise CoreTopGateError(f"{path}:{line_number}: duplicate or empty key {key!r}")
        result[key] = value
    return result


def _lstat(path: Path, label: str) -> os.stat_result:
    try:
        return os.lstat(path)
    except OSError as error:
        raise CoreTopGateError(f"{label} cannot be inspected safely: {path}: {error}") from error


def checked_regular_file(path: Path, label: str) -> Path:
    raw = path.expanduser()
    metadata = _lstat(raw, label)
    if stat.S_ISLNK(metadata.st_mode):
        raise CoreTopGateError(f"{label} must not be a symlink: {raw}")
    if not stat.S_ISREG(metadata.st_mode):
        raise CoreTopGateError(f"{label} must be a regular file: {raw}")
    return raw.resolve(strict=True)


def checked_directory(path: Path, label: str) -> Path:
    raw = path.expanduser()
    metadata = _lstat(raw, label)
    if stat.S_ISLNK(metadata.st_mode):
        raise CoreTopGateError(f"{label} must not be a symlink: {raw}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise CoreTopGateError(f"{label} must be a directory: {raw}")
    return raw.resolve(strict=True)


def ensure_fresh_out(path: Path, gate: str) -> Path:
    raw = path.expanduser()
    try:
        metadata = os.lstat(raw)
    except FileNotFoundError:
        metadata = None
    except OSError as error:
        raise CoreTopGateError(f"{gate} OUT_DIR cannot be inspected safely: {raw}: {error}") from error
    if metadata is not None:
        if stat.S_ISLNK(metadata.st_mode):
            raise CoreTopGateError(f"{gate} OUT_DIR must not be a symlink: {raw}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise CoreTopGateError(f"{gate} OUT_DIR must be a directory: {raw}")
        resolved = raw.resolve(strict=True)
        if any(resolved.iterdir()):
            raise CoreTopGateError(f"{gate} OUT_DIR must be fresh: {resolved}")
    else:
        resolved = raw.resolve(strict=False)
        resolved.mkdir(parents=True, exist_ok=False)
    final_metadata = _lstat(resolved, f"{gate} OUT_DIR")
    if stat.S_ISLNK(final_metadata.st_mode) or not stat.S_ISDIR(final_metadata.st_mode):
        raise CoreTopGateError(f"{gate} OUT_DIR changed during validation: {resolved}")
    return resolved


def validated_out(args: argparse.Namespace, gate: str) -> Path:
    out_dir = ensure_fresh_out(args.out_dir, gate)
    args._validated_out_dir = out_dir
    return out_dir


def resolve_git_dir(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git.resolve()
    if not dot_git.is_file():
        raise CoreTopGateError(f"Git metadata is missing: {dot_git}")
    line = dot_git.read_text(encoding="utf-8").strip()
    if not line.startswith("gitdir:"):
        raise CoreTopGateError(f"invalid Git worktree pointer: {dot_git}")
    raw = line.removeprefix("gitdir:").strip()
    candidates: list[Path] = []
    windows = re.fullmatch(r"([A-Za-z]):[\\/](.+)", raw)
    if windows and os.name != "nt":
        drive, suffix = windows.groups()
        suffix = suffix.replace("\\", "/")
        candidates.extend(
            (Path(f"/mnt/{drive.lower()}/{suffix}"), Path(f"/cygdrive/{drive.lower()}/{suffix}"))
        )
    candidate = Path(raw)
    candidates.append(candidate if candidate.is_absolute() else repo_root / candidate)
    for item in candidates:
        if item.is_dir():
            return item.resolve()
    raise CoreTopGateError(f"Git worktree metadata target is missing: {raw}")


def git_output(repo_root: Path, args: list[str], *, binary: bool = False) -> bytes | str:
    root = repo_root.resolve()
    git_dir = resolve_git_dir(root)
    try:
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", f"--work-tree={root}", *args],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CoreTopGateError(f"Git command failed to run: {error}") from error
    if result.returncode != 0:
        raise CoreTopGateError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout if binary else result.stdout.decode("utf-8", errors="strict").strip()


def git_blob(repo_root: Path, revision: str, path: str) -> tuple[bytes, str, str]:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise CoreTopGateError(f"Git revision must be a locked full SHA: {revision}")
    if not path or Path(path).is_absolute() or ".." in Path(path).parts:
        raise CoreTopGateError(f"unsafe Git object path: {path}")
    resolved = str(git_output(repo_root, ["rev-parse", revision]))
    if resolved != revision:
        raise CoreTopGateError(f"locked Git revision resolved unexpectedly: {resolved}")
    spec = f"{revision}:{path}"
    blob_sha1 = str(git_output(repo_root, ["rev-parse", spec]))
    if not re.fullmatch(r"[0-9a-f]{40}", blob_sha1):
        raise CoreTopGateError(f"invalid blob identity for {spec}: {blob_sha1}")
    payload = git_output(repo_root, ["cat-file", "blob", spec], binary=True)
    assert isinstance(payload, bytes)
    return payload, blob_sha1, resolved


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CoreTopGateError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CoreTopGateError(f"{label} must be an array")
    return value


def load_port_contract(path: Path) -> dict[str, Any]:
    contract = load_json_strict(path)
    unknown = set(contract) - ALLOWED_CONTRACT_KEYS
    missing = ALLOWED_CONTRACT_KEYS - set(contract)
    if unknown or missing:
        raise CoreTopGateError(f"contract keys differ: missing={sorted(missing)} unknown={sorted(unknown)}")
    if contract.get("schema_version") != 1 or contract.get("module") != TOP_MODULE:
        raise CoreTopGateError("unsupported core_top contract identity")
    if (
        contract.get("port_count") != EXPECTED_PORT_COUNT
        or contract.get("input_count") != EXPECTED_INPUT_COUNT
        or contract.get("output_count") != EXPECTED_OUTPUT_COUNT
    ):
        raise CoreTopGateError("core_top contract counts differ from the locked 49-port surface")
    parameters = _require_list(contract.get("parameters"), "parameters")
    if parameters != [{"name": "TLBNUM", "default": 32}]:
        raise CoreTopGateError("the only supported top parameter is TLBNUM=32")
    ports = _require_list(contract.get("ports"), "ports")
    if len(ports) != EXPECTED_PORT_COUNT:
        raise CoreTopGateError("ports array does not contain exactly 49 entries")
    seen: set[str] = set()
    input_count = output_count = 0
    normalized_ports: list[dict[str, Any]] = []
    for index, raw in enumerate(ports):
        port = _require_dict(raw, f"ports[{index}]")
        if set(port) != {"name", "direction", "width"}:
            raise CoreTopGateError(f"ports[{index}] has an invalid schema")
        name, direction, width = port.get("name"), port.get("direction"), port.get("width")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise CoreTopGateError(f"ports[{index}] has an invalid name")
        if name in seen:
            raise CoreTopGateError(f"duplicate port name: {name}")
        if direction not in {"input", "output"} or not isinstance(width, int) or width <= 0:
            raise CoreTopGateError(f"ports[{index}] has an invalid direction or width")
        seen.add(name)
        input_count += direction == "input"
        output_count += direction == "output"
        normalized_ports.append({"name": name, "direction": direction, "width": width})
    if input_count != EXPECTED_INPUT_COUNT or output_count != EXPECTED_OUTPUT_COUNT:
        raise CoreTopGateError("ports array direction counts differ")
    contract["ports"] = normalized_ports
    sources = _require_dict(contract.get("sources"), "sources")
    if set(sources) != {
        "team_golden",
        "chiplab_mycpu",
        "normalized_header_sha256",
        "headers_equal",
    }:
        raise CoreTopGateError("contract sources schema differs")
    if sources.get("headers_equal") is not True or not re.fullmatch(
        r"[0-9a-f]{64}", str(sources.get("normalized_header_sha256", ""))
    ):
        raise CoreTopGateError("contract header identity is invalid")
    for label in ("team_golden", "chiplab_mycpu"):
        source = _require_dict(sources.get(label), f"sources.{label}")
        if set(source) != {"commit", "path", "blob_sha1", "raw_sha256"}:
            raise CoreTopGateError(f"sources.{label} schema differs")
        if not re.fullmatch(r"[0-9a-f]{7,40}", str(source.get("commit", ""))):
            raise CoreTopGateError(f"sources.{label}.commit is invalid")
        if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("blob_sha1", ""))):
            raise CoreTopGateError(f"sources.{label}.blob_sha1 is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", str(source.get("raw_sha256", ""))):
            raise CoreTopGateError(f"sources.{label}.raw_sha256 is invalid")
    return contract


def mask_verilog_comments(text: str) -> str:
    """Replace comment bytes with spaces while preserving offsets and newlines."""

    def mask(match: re.Match[str]) -> str:
        return "".join(char if char in "\r\n" else " " for char in match.group(0))

    return re.sub(r"//[^\r\n]*|/\*.*?\*/", mask, text, flags=re.DOTALL)


def uncommented_matches(pattern: re.Pattern[str], text: str) -> list[re.Match[str]]:
    return list(pattern.finditer(mask_verilog_comments(text)))


def extract_normalized_header(payload: bytes) -> str:
    try:
        text = payload.decode("utf-8")
    except UnicodeError as error:
        raise CoreTopGateError(f"core_top source is not UTF-8: {error}") from error
    masked = mask_verilog_comments(text)
    declarations = list(re.finditer(r"(?m)^[ \t]*module\s+core_top\b", masked))
    if len(declarations) != 1:
        raise CoreTopGateError(f"core_top module declaration is not unique: {len(declarations)}")
    match = re.search(
        r"(?ms)^[ \t]*module\s+core_top\b.*?^[ \t]*\);[ \t]*\r?$", masked
    )
    if match is None:
        raise CoreTopGateError("could not extract the ANSI core_top header")
    return text[match.start() : match.end()].replace("\r\n", "\n").strip()


def parse_header_contract(header: str) -> tuple[list[dict[str, Any]], int]:
    masked = mask_verilog_comments(header)
    parameter = re.search(r"\bparameter\s+(?:integer\s+)?TLBNUM\s*=\s*(\d+)\b", masked)
    if parameter is None:
        raise CoreTopGateError("core_top header does not declare TLBNUM")
    ports: list[dict[str, Any]] = []
    declaration = re.compile(
        r"^\s*(input|output)\s+(?:(?:wire|reg)\s+)?"
        r"(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s+)?"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*$"
    )
    for raw_line, line in zip(header.splitlines(), masked.splitlines(), strict=True):
        line = line.rstrip()
        if not re.match(r"^\s*(?:input|output)\b", line):
            continue
        match = declaration.fullmatch(line)
        if match is None:
            raise CoreTopGateError(f"unsupported port declaration: {raw_line.strip()}")
        direction, msb, lsb, name = match.groups()
        width = 1 if msb is None else abs(int(msb) - int(lsb)) + 1
        ports.append({"name": name, "direction": direction, "width": width})
    return ports, int(parameter.group(1))


def verify_locked_source(
    repo_root: Path,
    revision: str,
    source: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    prefix = str(source["commit"])
    if not revision.startswith(prefix):
        raise CoreTopGateError(f"locked revision {revision} does not match contract prefix {prefix}")
    payload, blob_sha1, resolved = git_blob(repo_root, revision, str(source["path"]))
    header = extract_normalized_header(payload)
    ports, tlbnum = parse_header_contract(header)
    expected_header_hash = str(contract["sources"]["normalized_header_sha256"])
    checks = {
        "commit": resolved,
        "path": source["path"],
        "blob_sha1": blob_sha1,
        "raw_sha256": sha256_bytes(payload),
        "raw_size": len(payload),
        "normalized_header_sha256": sha256_bytes(header.encode("utf-8")),
        "ports": ports,
        "tlbnum_default": tlbnum,
    }
    if blob_sha1 != source["blob_sha1"]:
        raise CoreTopGateError("locked core_top blob SHA-1 differs from the contract")
    if checks["raw_sha256"] != source["raw_sha256"]:
        raise CoreTopGateError("locked core_top raw SHA256 differs from the contract")
    if checks["normalized_header_sha256"] != expected_header_hash:
        raise CoreTopGateError("locked core_top header SHA256 differs from the contract")
    if ports != contract["ports"] or tlbnum != 32:
        raise CoreTopGateError("locked core_top header ports or TLBNUM differ from the contract")
    return {**checks, "payload": payload, "header": header}


def repository_provenance(repo_root: Path, manifest: Path, ports: Path) -> dict[str, Any]:
    status = str(git_output(repo_root, ["status", "--porcelain=v1", "--untracked-files=all"]))
    return {
        "repository": str(repo_root.resolve()),
        "repository_head": git_output(repo_root, ["rev-parse", "HEAD"]),
        "repository_status_sha256": sha256_bytes(status.encode("utf-8")),
        "manifest": str(manifest.resolve()),
        "manifest_sha256": sha256_file(manifest.resolve()),
        "ports_contract": str(ports.resolve()),
        "ports_contract_sha256": sha256_file(ports.resolve()),
        "evaluator": str(Path(__file__).resolve()),
        "evaluator_sha256": sha256_file(Path(__file__).resolve()),
    }


def contract_gate(args: argparse.Namespace) -> dict[str, Any]:
    if args.chiplab_mycpu is None:
        raise CoreTopGateError("contract requires --chiplab-mycpu for the locked aa3b source")
    manifest_path = checked_regular_file(args.manifest, "manifest.lock")
    ports_path = checked_regular_file(args.ports, "ports contract")
    repo_root = checked_directory(args.repo_root, "repository root")
    chiplab_root = checked_directory(args.chiplab_mycpu, "locked chiplab myCPU")
    out_dir = validated_out(args, "contract")
    values = parse_lock(manifest_path)
    contract = load_port_contract(ports_path)
    team_revision = values.get("team_golden_candidate", "")
    if not re.fullmatch(r"[0-9a-f]{40}", team_revision):
        raise CoreTopGateError("manifest.lock team_golden_candidate must be a full SHA")
    team = verify_locked_source(
        repo_root, team_revision, contract["sources"]["team_golden"], contract
    )
    chiplab_revision = values.get("chiplab_mycpu_gitlink", "")
    if not re.fullmatch(r"[0-9a-f]{40}", chiplab_revision):
        raise CoreTopGateError("manifest.lock chiplab_mycpu_gitlink must be a full SHA")
    chiplab = verify_locked_source(
        chiplab_root,
        chiplab_revision,
        contract["sources"]["chiplab_mycpu"],
        contract,
    )
    if chiplab["header"] != team["header"]:
        raise CoreTopGateError("team and chiplab core_top headers differ")
    summary = {
        "schema_version": 1,
        "gate": "contract",
        "target": TARGET,
        "status": "pass",
        "generated_at": now_iso(),
        "counts": {
            "ports": len(contract["ports"]),
            "inputs": sum(port["direction"] == "input" for port in contract["ports"]),
            "outputs": sum(port["direction"] == "output" for port in contract["ports"]),
        },
        "team_golden": {key: value for key, value in team.items() if key not in {"payload", "header"}},
        "chiplab_mycpu": {
            key: value for key, value in chiplab.items() if key not in {"payload", "header"}
        },
        "provenance": repository_provenance(repo_root, manifest_path, ports_path),
    }
    write_json(out_dir / "summary.json", summary)
    return summary


def module_declaration_count(text: str, name: str) -> int:
    return len(
        uncommented_matches(
            re.compile(rf"(?m)^[ \t]*module\s+{re.escape(name)}\b"), text
        )
    )


def extract_module(text: str, name: str) -> str:
    masked = mask_verilog_comments(text)
    matches = list(re.finditer(rf"(?m)^[ \t]*module\s+{re.escape(name)}\b", masked))
    if len(matches) != 1:
        raise CoreTopGateError(f"module {name} declaration is not unique: {len(matches)}")
    end = re.search(r"(?m)^[ \t]*endmodule\b[^\r\n]*", masked[matches[0].start() :])
    if end is None:
        raise CoreTopGateError(f"module {name} has no endmodule")
    return text[matches[0].start() : matches[0].start() + end.end()]


def add_top_parameter(wrapper: str) -> tuple[str, int]:
    newline = "\r\n" if "\r\n" in wrapper else "\n"
    pattern = re.compile(r"(?m)^([ \t]*)module\s+core_top[ \t]*\([ \t]*\r?$")
    matches = uncommented_matches(pattern, wrapper)
    if len(matches) != 1:
        raise CoreTopGateError(f"plain core_top declaration is not unique: {len(matches)}")
    replacement = (
        f"{matches[0].group(1)}module core_top #(\n"
        "  parameter TLBNUM = 32\n"
        ") ("
    ).replace("\n", newline)
    match = matches[0]
    return wrapper[: match.start()] + replacement + wrapper[match.end() :], 1


def has_uncommented_top_tlbnum_default(wrapper: str) -> bool:
    masked = mask_verilog_comments(wrapper)
    return bool(
        re.search(
            r"(?s)module\s+core_top\s*#\s*\(.*?parameter\s+(?:integer\s+)?TLBNUM\s*=\s*32\b",
            masked,
        )
    )


def ensure_top_parameter(rtl: str) -> tuple[str, int]:
    """Expose the locked top parameter while leaving all generated RTL intact."""

    top = extract_module(rtl, TOP_MODULE)
    masked_top = mask_verilog_comments(top)
    if re.search(r"\bparameter\s+(?:integer\s+)?TLBNUM\b", masked_top):
        if not has_uncommented_top_tlbnum_default(top):
            raise CoreTopGateError("generated core_top declares TLBNUM with an unsupported default")
        return rtl, 0
    return add_top_parameter(rtl)


def verify_complete_rtl(text: str, contract: dict[str, Any]) -> dict[str, Any]:
    if module_declaration_count(text, TOP_MODULE) != 1:
        raise CoreTopGateError("complete Spinal RTL must define exactly one core_top")
    if FORBIDDEN_LEGACY_MARKER in text:
        raise CoreTopGateError("complete Spinal RTL must not contain openla500_legacy_core")
    header = extract_normalized_header(text.encode("utf-8"))
    ports, tlbnum = parse_header_contract(header)
    if ports != contract["ports"]:
        raise CoreTopGateError("complete Spinal core_top ports differ from the 49-port contract")
    if tlbnum != 32:
        raise CoreTopGateError("complete Spinal core_top TLBNUM default differs from 32")
    return {
        "module_count": module_declaration_count(text, TOP_MODULE),
        "port_count": len(ports),
        "input_count": sum(port["direction"] == "input" for port in ports),
        "output_count": sum(port["direction"] == "output" for port in ports),
        "tlbnum_default": tlbnum,
        "legacy_backend_absent": True,
        "header_sha256": sha256_bytes(header.encode("utf-8")),
    }


def package_gate(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = checked_regular_file(args.manifest, "manifest.lock")
    ports_path = checked_regular_file(args.ports, "ports contract")
    rtl_path = checked_regular_file(args.rtl, "complete Spinal RTL")
    repo_root = checked_directory(args.repo_root, "repository root")
    out_dir = validated_out(args, "package")
    parse_lock(manifest_path)
    contract = load_port_contract(ports_path)
    input_payload = rtl_path.read_bytes()
    try:
        input_rtl = input_payload.decode("utf-8")
    except UnicodeError as error:
        raise CoreTopGateError(f"complete Spinal RTL is not UTF-8: {error}") from error
    transformed, top_count = ensure_top_parameter(input_rtl)
    contract_check = verify_complete_rtl(transformed, contract)
    packaged = transformed.encode("utf-8")
    packaged_text = packaged.decode("utf-8")
    verify_complete_rtl(packaged_text, contract)
    published = out_dir / "rtl" / "mycpu_top.v"
    published.parent.mkdir()
    temporary = published.with_suffix(".v.tmp")
    temporary.write_bytes(packaged)
    temporary.replace(published)
    if sha256_file(published) != sha256_bytes(packaged):
        raise CoreTopGateError("published package changed while it was written")
    source_stable = bool(
        not stat.S_ISLNK(_lstat(rtl_path, "complete Spinal RTL").st_mode)
        and rtl_path.stat().st_size == len(input_payload)
        and sha256_file(rtl_path) == sha256_bytes(input_payload)
    )
    if not source_stable:
        raise CoreTopGateError("complete Spinal RTL changed during packaging")
    summary = {
        "schema_version": 1,
        "gate": "core-top-package",
        "target": TARGET,
        "scope": "complete-spinal-rtl-publication",
        "status": "pass",
        "generated_at": now_iso(),
        "input_rtl": {
            "path": str(rtl_path),
            "sha256": sha256_bytes(input_payload),
            "size": len(input_payload),
            "stable": source_stable,
        },
        "transformations": {
            "top_parameter_insertions": top_count,
        },
        "contract": contract_check,
        "published_rtl": str(published),
        "published_sha256": sha256_file(published),
        "published_size": published.stat().st_size,
        "provenance": repository_provenance(repo_root, manifest_path, ports_path),
    }
    write_json(out_dir / "summary.json", summary)
    return summary


def publish_check_gate(args: argparse.Namespace) -> dict[str, Any]:
    manifest = checked_regular_file(args.manifest, "manifest.lock")
    ports_path = checked_regular_file(args.ports, "ports contract")
    fresh = checked_regular_file(args.rtl, "fresh package RTL")
    tracked = checked_regular_file(args.tracked_rtl, "tracked package RTL")
    spec_path = checked_regular_file(args.replacement_spec, "replacement spec")
    repo_root = checked_directory(args.repo_root, "repository root")
    contract = load_port_contract(ports_path)
    parse_lock(manifest)
    expected_tracked = checked_regular_file(repo_root / PUBLISHED_SOURCE, "published source")
    if tracked != expected_tracked:
        raise CoreTopGateError(
            f"tracked RTL must be {PUBLISHED_SOURCE}: got {tracked}"
        )
    spec = load_json_strict(spec_path)
    if set(spec) != {"schema_version", "replacements"} or spec.get("schema_version") != 1:
        raise CoreTopGateError("replacement spec root schema differs")
    replacements = _require_list(spec.get("replacements"), "replacement spec entries")
    entries = []
    for index, raw in enumerate(replacements):
        entry = _require_dict(raw, f"replacement[{index}]")
        if set(entry) != {"target", "source", "base_sha256", "replacement_sha256"}:
            raise CoreTopGateError(f"replacement[{index}] schema differs")
        for hash_key in ("base_sha256", "replacement_sha256"):
            if re.fullmatch(r"[0-9a-f]{64}", str(entry.get(hash_key, ""))) is None:
                raise CoreTopGateError(f"replacement[{index}].{hash_key} is invalid")
        if entry.get("target") == PUBLISHED_TARGET:
            entries.append(entry)
    if len(entries) != 1:
        raise CoreTopGateError(
            f"replacement spec must contain exactly one {PUBLISHED_TARGET} entry"
        )
    entry = entries[0]
    if entry["source"] != PUBLISHED_SOURCE:
        raise CoreTopGateError("core_top replacement source path differs")
    expected_base = contract["sources"]["team_golden"]["raw_sha256"]
    if entry["base_sha256"] != expected_base:
        raise CoreTopGateError("core_top replacement base hash differs from the locked source")
    fresh_payload, tracked_payload = fresh.read_bytes(), tracked.read_bytes()
    fresh_hash, tracked_hash = sha256_bytes(fresh_payload), sha256_bytes(tracked_payload)
    if fresh_payload != tracked_payload:
        raise CoreTopGateError("tracked core_top package is stale relative to the fresh package")
    if entry["replacement_sha256"] != fresh_hash or tracked_hash != fresh_hash:
        raise CoreTopGateError("core_top replacement hash differs from package bytes")
    for path, payload, label in (
        (fresh, fresh_payload, "fresh package RTL"),
        (tracked, tracked_payload, "tracked package RTL"),
    ):
        metadata = _lstat(path, label)
        if stat.S_ISLNK(metadata.st_mode) or path.stat().st_size != len(payload):
            raise CoreTopGateError(f"{label} changed during publish-check")
        if sha256_file(path) != sha256_bytes(payload):
            raise CoreTopGateError(f"{label} changed during publish-check")
    out_dir = validated_out(args, "publish-check")
    summary = {
        "schema_version": 1,
        "gate": "publish-check",
        "target": TARGET,
        "scope": "publication-consistency",
        "status": "pass",
        "generated_at": now_iso(),
        "published_target": PUBLISHED_TARGET,
        "published_source": PUBLISHED_SOURCE,
        "fresh_package": str(fresh),
        "tracked_package": str(tracked),
        "package_sha256": fresh_hash,
        "package_size": len(fresh_payload),
        "replacement_spec": str(spec_path),
        "replacement_spec_sha256": sha256_file(spec_path),
        "base_sha256": entry["base_sha256"],
        "replacement_sha256": entry["replacement_sha256"],
        "provenance": repository_provenance(repo_root, manifest, ports_path),
    }
    write_json(out_dir / "summary.json", summary)
    return summary


def prepare_complete_rtl(
    args: argparse.Namespace, gate: str
) -> tuple[Path, Path, dict[str, Any], dict[str, str], dict[str, Any]]:
    manifest = checked_regular_file(args.manifest, "manifest.lock")
    ports = checked_regular_file(args.ports, "ports contract")
    rtl = checked_regular_file(args.rtl, "complete packaged RTL")
    checked_directory(args.repo_root, "repository root")
    out_dir = validated_out(args, gate)
    contract = load_port_contract(ports)
    values = parse_lock(manifest)
    payload = rtl.read_bytes()
    text = payload.decode("utf-8", errors="strict")
    contract_check = verify_complete_rtl(text, contract)
    rtl_snapshot = out_dir / "input" / "core_top.v"
    rtl_snapshot.parent.mkdir()
    rtl_snapshot.write_bytes(payload)
    source_stable = bool(
        not stat.S_ISLNK(_lstat(rtl, "complete packaged RTL").st_mode)
        and rtl.stat().st_size == len(payload)
        and sha256_file(rtl) == sha256_bytes(payload)
    )
    if not source_stable or rtl_snapshot.read_bytes() != payload:
        raise CoreTopGateError("complete packaged RTL changed while preparing static checks")
    identity = {
        "complete_rtl": str(rtl),
        "complete_rtl_sha256": sha256_bytes(payload),
        "complete_rtl_size": len(payload),
        "stable": source_stable,
        "snapshot": str(rtl_snapshot),
        "snapshot_sha256": sha256_file(rtl_snapshot),
        "contract": contract_check,
    }
    return out_dir, rtl_snapshot, contract, values, identity


def resolve_executable(value: str | None, fallback: str) -> Path:
    candidate = value or shutil.which(fallback)
    if not candidate:
        raise CoreTopGateError(f"required executable is not on PATH: {fallback}")
    path = Path(candidate).expanduser().resolve()
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise CoreTopGateError(f"executable is missing or not executable: {path}")
    return path


def checked_tool(values: dict[str, str], supplied: str | None, name: str, hash_key: str) -> Path:
    path = resolve_executable(supplied, name)
    expected = values.get(hash_key)
    if not expected or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise CoreTopGateError(f"manifest.lock is missing a valid {hash_key}")
    if sha256_file(path) != expected:
        raise CoreTopGateError(f"{name} binary hash differs from manifest.lock: {path}")
    return path


def run_command(argv: list[str], *, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name != "nt",
            creationflags=creationflags,
        )
        try:
            output, _ = process.communicate(timeout=timeout)
            returncode, timed_out = process.returncode, False
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    process.kill()
            else:
                process.kill()
            output, _ = process.communicate()
            returncode, timed_out = 124, True
    except OSError as error:
        output, returncode, timed_out = f"failed to start command: {error}\n", 125, False
    return {
        "argv": argv,
        "returncode": returncode,
        "stdout": output,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def warning_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if re.search(r"(?:%warning|\bwarning:|\[warn\])", line, flags=re.IGNORECASE)
    ]


def skip_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if re.search(r"\bskip(?:ped)?\b", line, flags=re.IGNORECASE)
    ]


def yosys_quote(path: Path) -> str:
    return '"' + str(path.resolve()).replace("\\", "/").replace('"', '\\"') + '"'


def run_yosys(
    values: dict[str, str], supplied: str | None, script: str, out_dir: Path, timeout: int
) -> dict[str, Any]:
    yosys = checked_tool(values, supplied, "yosys", "yosys_binary_sha256")
    version = run_command([str(yosys), "-V"], cwd=out_dir, timeout=timeout)
    if version["returncode"] != 0 or version["timed_out"]:
        raise CoreTopGateError("locked Yosys version probe failed")
    expected_version = values.get("yosys", "")
    if expected_version and not re.search(
        rf"Yosys\s+{re.escape(expected_version)}(?:\s|$)", str(version["stdout"])
    ):
        raise CoreTopGateError(f"Yosys version differs: {str(version['stdout']).strip()}")
    script_path, log_path = out_dir / "gate.ys", out_dir / "yosys.log"
    script_path.write_text(script, encoding="utf-8")
    result = run_command(
        [str(yosys), "-l", str(log_path), "-s", str(script_path)], cwd=out_dir, timeout=timeout
    )
    if not log_path.is_file():
        log_path.write_text(str(result["stdout"]), encoding="utf-8")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    result["warnings"] = warning_lines(log)
    result["skip_markers"] = skip_lines(log + "\n" + str(result["stdout"]))
    result["tool"] = {
        "path": str(yosys),
        "sha256": sha256_file(yosys),
        "version": str(version["stdout"]).strip(),
    }
    result["log"] = str(log_path)
    result["log_sha256"] = sha256_file(log_path)
    return result


def project_ports(module: dict[str, Any]) -> list[dict[str, Any]]:
    ports = _require_dict(module.get("ports"), "Yosys top ports")
    result = []
    for name, raw in ports.items():
        port = _require_dict(raw, f"Yosys port {name}")
        bits = _require_list(port.get("bits"), f"Yosys port {name}.bits")
        result.append({"name": name, "direction": port.get("direction"), "width": len(bits)})
    return result


def yosys_binary_int(value: Any, label: str) -> int:
    if not isinstance(value, str) or not value or re.fullmatch(r"[01]+", value) is None:
        raise CoreTopGateError(f"{label} is not a concrete Yosys binary value")
    return int(value, 2)


def validate_top_contract(document: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    modules = _require_dict(document.get("modules"), "Yosys modules")
    top = _require_dict(modules.get(TOP_MODULE), "Yosys core_top")
    actual_ports = project_ports(top)
    if actual_ports != contract["ports"]:
        raise CoreTopGateError("Yosys core_top ports differ from the 49-port contract")
    top_parameters = _require_dict(
        top.get("parameter_default_values"), "core_top parameter defaults"
    )
    top_tlbnum = yosys_binary_int(top_parameters.get("TLBNUM"), "core_top TLBNUM")
    if top_tlbnum != 32:
        raise CoreTopGateError(f"core_top TLBNUM parameter mismatch: {top_tlbnum}")
    if FORBIDDEN_LEGACY_MARKER in modules:
        raise CoreTopGateError("Yosys design still contains openla500_legacy_core")
    cells = _require_dict(top.get("cells", {}), "Yosys core_top cells")
    return {
        "actual_ports": actual_ports,
        "top_tlbnum": top_tlbnum,
        "top_cell_count": len(cells),
        "design_module_count": len(modules),
        "legacy_backend_absent": True,
    }


def gate_provenance(args: argparse.Namespace) -> dict[str, Any]:
    return repository_provenance(
        checked_directory(args.repo_root, "repository root"),
        checked_regular_file(args.manifest, "manifest.lock"),
        checked_regular_file(args.ports, "ports contract"),
    )


def port_check_gate(args: argparse.Namespace) -> dict[str, Any]:
    out_dir, rtl, contract, values, identity = prepare_complete_rtl(args, "port-check")
    json_path = out_dir / "core_top-raw.json"
    script = (
        f"read_verilog -sv {yosys_quote(rtl)}\n"
        f"hierarchy -check -top {TOP_MODULE}\n"
        "proc\n"
        f"write_json {yosys_quote(json_path)}\n"
    )
    result = run_yosys(values, args.yosys, script, out_dir, args.timeout)
    if (
        result["returncode"] != 0
        or result["timed_out"]
        or result["warnings"]
        or result["skip_markers"]
    ):
        raise CoreTopGateError("Yosys port/connectivity command failed or warned")
    if not json_path.is_file():
        raise CoreTopGateError("Yosys did not produce the connectivity JSON")
    document = load_json_strict(json_path)
    top_contract = validate_top_contract(document, contract)
    summary = {
        "schema_version": 1,
        "gate": "core-top-port-check",
        "target": TARGET,
        "scope": "complete-spinal-rtl",
        "status": "pass",
        "generated_at": now_iso(),
        "input": identity,
        "contract": top_contract,
        "yosys": {key: value for key, value in result.items() if key != "stdout"},
        "provenance": gate_provenance(args),
    }
    write_json(out_dir / "summary.json", summary)
    return summary


def lint_gate(args: argparse.Namespace) -> dict[str, Any]:
    out_dir, rtl, _, values, identity = prepare_complete_rtl(args, "lint")
    verilator = checked_tool(values, args.verilator, "verilator", "verilator_binary_sha256")
    version = run_command([str(verilator), "--version"], cwd=out_dir, timeout=args.timeout)
    if version["returncode"] != 0 or version["timed_out"]:
        raise CoreTopGateError("locked Verilator version probe failed")
    expected_version = values.get("verilator", "")
    if expected_version and not re.search(
        rf"Verilator\s+{re.escape(expected_version)}(?:\s|$)", str(version["stdout"])
    ):
        raise CoreTopGateError(f"Verilator version differs: {str(version['stdout']).strip()}")
    result = run_command(
        [
            str(verilator),
            "--lint-only",
            "-Wall",
            "--top-module",
            TOP_MODULE,
            str(rtl),
        ],
        cwd=out_dir,
        timeout=args.timeout,
    )
    log_path = out_dir / "verilator.log"
    log_path.write_text(str(result["stdout"]), encoding="utf-8")
    warnings = warning_lines(str(result["stdout"]))
    skips = skip_lines(str(result["stdout"]))
    if result["returncode"] != 0 or result["timed_out"] or warnings or skips:
        raise CoreTopGateError("Verilator complete core_top lint failed or warned")
    summary = {
        "schema_version": 1,
        "gate": "core-top-lint",
        "target": TARGET,
        "scope": "complete-spinal-rtl",
        "status": "pass",
        "generated_at": now_iso(),
        "input": identity,
        "warnings": warnings,
        "skip_markers": skips,
        "verilator": {
            "path": str(verilator),
            "sha256": sha256_file(verilator),
            "version": str(version["stdout"]).strip(),
            "returncode": result["returncode"],
            "timed_out": result["timed_out"],
            "elapsed_seconds": result["elapsed_seconds"],
            "log": str(log_path),
            "log_sha256": sha256_file(log_path),
        },
        "provenance": gate_provenance(args),
    }
    write_json(out_dir / "summary.json", summary)
    return summary


def yosys_check_gate(args: argparse.Namespace) -> dict[str, Any]:
    out_dir, rtl, _, values, identity = prepare_complete_rtl(args, "yosys-check")
    script = (
        f"read_verilog -sv {yosys_quote(rtl)}\n"
        f"hierarchy -check -top {TOP_MODULE}\n"
        "proc\n"
        "opt_clean\n"
        "check -assert\n"
        "stat\n"
    )
    result = run_yosys(values, args.yosys, script, out_dir, args.timeout)
    if (
        result["returncode"] != 0
        or result["timed_out"]
        or result["warnings"]
        or result["skip_markers"]
    ):
        raise CoreTopGateError("Yosys complete core_top check failed or warned")
    summary = {
        "schema_version": 1,
        "gate": "core-top-yosys-check",
        "target": TARGET,
        "scope": "complete-spinal-rtl",
        "status": "pass",
        "generated_at": now_iso(),
        "input": identity,
        "yosys": {key: value for key, value in result.items() if key != "stdout"},
        "provenance": gate_provenance(args),
    }
    write_json(out_dir / "summary.json", summary)
    return summary


def add_common(parser: argparse.ArgumentParser, *, rtl: bool = False) -> None:
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, default=Path("reference/manifest.lock"))
    parser.add_argument("--ports", type=Path, default=Path("reference/core-top.ports.json"))
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=120)
    if rtl:
        parser.add_argument("--rtl", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    contract = subparsers.add_parser("contract")
    add_common(contract)
    contract.add_argument("--chiplab-mycpu", type=Path, required=True)
    package = subparsers.add_parser("package")
    add_common(package, rtl=True)
    publish = subparsers.add_parser("publish-check")
    add_common(publish, rtl=True)
    publish.add_argument("--tracked-rtl", type=Path, required=True)
    publish.add_argument("--replacement-spec", type=Path, required=True)
    port = subparsers.add_parser("port-check")
    add_common(port, rtl=True)
    port.add_argument("--yosys")
    lint = subparsers.add_parser("lint")
    add_common(lint, rtl=True)
    lint.add_argument("--verilator")
    yosys = subparsers.add_parser("yosys-check")
    add_common(yosys, rtl=True)
    yosys.add_argument("--yosys")
    return parser


def _failure_summary(args: argparse.Namespace, error: Exception) -> None:
    out_dir = getattr(args, "_validated_out_dir", None)
    if not isinstance(out_dir, Path):
        return
    try:
        metadata = os.lstat(out_dir)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            return
        summary_path = out_dir / "summary.json"
        if summary_path.exists() or summary_path.is_symlink():
            return
        write_json(
            summary_path,
            {
                "schema_version": 1,
                "gate": getattr(args, "command", "unknown"),
                "target": TARGET,
                "status": "fail",
                "generated_at": now_iso(),
                "error": str(error),
                "evaluator_sha256": sha256_file(Path(__file__).resolve()),
            },
        )
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    if args.timeout <= 0:
        print("error: timeout must be positive", file=sys.stderr)
        return 2
    gates = {
        "contract": contract_gate,
        "package": package_gate,
        "publish-check": publish_check_gate,
        "port-check": port_check_gate,
        "lint": lint_gate,
        "yosys-check": yosys_check_gate,
    }
    try:
        summary = gates[args.command](args)
    except (CoreTopGateError, OSError, UnicodeError) as error:
        _failure_summary(args, error)
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
