#!/usr/bin/env python3
"""Run the locked openLA500 multiplier golden against an independent model.

This gate deliberately validates the historical ``mul`` contract before a
Spinal replacement exists.  The Verilog source is extracted from the locked
Git blob, compiled by the locked Verilator, and driven by a small C++ cycle
driver.  The driver does not use the DUT to calculate its expected value.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable


GOLDEN_COMMIT_KEY = "team_golden_candidate"
GOLDEN_PATH = "rtl/mul.v"
GOLDEN_SHA256 = "251d2bba3e659c294c9a004bbb2b542435fcfa0b0c1582cc1a7a3edca765a4c0"
GOLDEN_SIZE = 6045
EXPECTED_WARNING = {
    "rule": "WIDTHEXPAND",
    "line": 195,
    "message": "Operator ADD expects 64 bits on the RHS, but RHS's SEL generates 1 bits.",
}
DEFAULT_SEED = 0x158AA8
DEFAULT_VECTOR_COUNT = 4096
MASK32 = (1 << 32) - 1
MASK64 = (1 << 64) - 1
DRIVER_VERSION = "mul-diff-driver-v1"


class MulDiffError(RuntimeError):
    """Raised when the gate cannot establish a trustworthy result."""


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


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = OrderedDict()
    for key, value in pairs:
        if key in result:
            raise MulDiffError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise MulDiffError(f"JSON artifact must be a regular file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MulDiffError(f"invalid JSON artifact {path}: {error}") from error


def parse_manifest(path: Path) -> dict[str, str]:
    """Parse the lock file without accepting duplicate or malformed keys."""

    if path.is_symlink() or not path.is_file():
        raise MulDiffError(f"manifest must be a regular file: {path}")
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise MulDiffError(f"cannot read manifest: {error}") from error
    for line_number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise MulDiffError(f"manifest line {line_number} is not key=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or key in values:
            raise MulDiffError(f"manifest line {line_number} has an invalid/duplicate key")
        values[key] = value
    commit = values.get(GOLDEN_COMMIT_KEY, "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise MulDiffError(f"manifest {GOLDEN_COMMIT_KEY} must be a full 40-hex SHA")
    return values


def _mul_contract_module(repo_root: Path) -> Any:
    """Load the sibling contract validator under both normal and ``-I`` Python."""

    module_path = repo_root / "tools" / "mul_contract.py"
    if not module_path.is_file():
        raise MulDiffError(f"locked mul contract validator is missing: {module_path}")
    spec = importlib.util.spec_from_file_location("_locked_mul_contract", module_path)
    if spec is None or spec.loader is None:
        raise MulDiffError(f"cannot load contract validator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_contract(contract: Path, manifest: Path, out_dir: Path) -> dict[str, Any]:
    """Run the canonical schema/provenance validator and return its evidence."""

    module = _mul_contract_module(manifest.resolve().parent.parent)
    try:
        return module.verify_contract(contract.resolve(), manifest.resolve(), out_dir.resolve())
    except Exception as error:  # normalize the sibling validator's exception type
        if isinstance(error, (OSError, ValueError, json.JSONDecodeError)):
            raise MulDiffError(str(error)) from error
        raise


def contract_evaluator_evidence(
    repo_root: Path, contract_evidence: dict[str, Any]
) -> dict[str, str]:
    """Bind a canonical contract result to the validator bytes that produced it."""

    validator = (repo_root / "tools" / "mul_contract.py").resolve()
    if validator.is_symlink() or not validator.is_file():
        raise MulDiffError(f"locked mul contract validator is not a regular file: {validator}")
    actual_sha256 = sha256_file(validator)
    reported_sha256 = contract_evidence.get("evaluator_sha256")
    if reported_sha256 != actual_sha256:
        raise MulDiffError(
            "contract evaluator hash mismatch: "
            f"reported={reported_sha256!r} actual={actual_sha256}"
        )
    return {"path": str(validator), "sha256": actual_sha256}


def _git_bytes(repo_root: Path, args: list[str]) -> bytes:
    """Use the canonical contract validator's cross-platform worktree resolver."""

    module = _mul_contract_module(repo_root)
    try:
        return module._run_git(repo_root, args)
    except Exception as error:  # normalize the sibling validator's exception type
        raise MulDiffError(str(error)) from error


def resolve_executable(value: str | None, default: str) -> Path:
    candidate = value or shutil.which(default)
    if not candidate:
        raise MulDiffError(f"required executable is not on PATH: {default}")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise MulDiffError(f"executable is missing or not executable: {path}")
    return path


def checked_executable(values: dict[str, str], value: str | None, name: str, lock_key: str) -> Path:
    path = resolve_executable(value, name)
    expected = values.get(lock_key)
    if expected and sha256_file(path) != expected:
        raise MulDiffError(f"{name} binary hash differs from manifest.lock: {path}")
    if not expected:
        raise MulDiffError(f"manifest.lock is missing {lock_key}")
    return path


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a command with a process-group timeout and captured combined output."""

    started = time.monotonic()
    creationflags = 0
    start_new_session = os.name != "nt"
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=start_new_session,
            creationflags=creationflags,
        )
        try:
            output, _ = process.communicate(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired as error:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    process.kill()
            else:
                process.kill()
            output, _ = process.communicate()
            output = (error.stdout or "") + (output or "")
            timed_out = True
        returncode = process.returncode if not timed_out else 124
    except OSError as error:
        output = f"failed to start command: {error}\n"
        returncode = 125
        timed_out = False
    return {
        "argv": argv,
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout": output or "",
    }


def _parse_waiver_document(path: Path) -> list[dict[str, Any]]:
    """Parse JSON-syntax YAML with duplicate-key rejection and no PyYAML dependency."""

    document = load_json(path)
    if not isinstance(document, dict) or set(document) != {"schema_version", "waivers"}:
        raise MulDiffError("lint waiver document must contain only schema_version and waivers")
    if document["schema_version"] != 1 or not isinstance(document["waivers"], list):
        raise MulDiffError("lint waiver schema_version/waivers is invalid")
    waivers: list[dict[str, Any]] = []
    expected_fields = {
        "id",
        "rule",
        "file",
        "line",
        "source_sha256",
        "scope",
        "reason",
        "owner",
        "expires_when",
    }
    for index, item in enumerate(document["waivers"]):
        if not isinstance(item, dict) or set(item) != expected_fields:
            raise MulDiffError(f"waivers[{index}] fields are invalid")
        if not isinstance(item["line"], int) or isinstance(item["line"], bool) or item["line"] < 1:
            raise MulDiffError(f"waivers[{index}].line is invalid")
        for field in expected_fields - {"line"}:
            if not isinstance(item[field], str) or not item[field].strip():
                raise MulDiffError(f"waivers[{index}].{field} is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", item["source_sha256"]):
            raise MulDiffError(f"waivers[{index}].source_sha256 is invalid")
        waivers.append(dict(item))
    return waivers


def approved_warning_suppressions(
    waiver_path: Path, *, golden_ref: str, golden_sha256: str, warnings: list[dict[str, Any]]
) -> tuple[bool, list[dict[str, Any]], str | None]:
    """Match every emitted warning to a file/line/hash-specific active waiver."""

    if waiver_path.is_symlink() or not waiver_path.is_file():
        return False, [], f"waiver file is missing: {waiver_path}"
    waivers = _parse_waiver_document(waiver_path)
    approved: list[dict[str, Any]] = []
    for warning in warnings:
        matches = [
            waiver
            for waiver in waivers
            if waiver["rule"] == warning["rule"]
            and waiver["line"] == warning["line"]
            and waiver["file"] == golden_ref
            and waiver["source_sha256"] == golden_sha256
        ]
        if len(matches) != 1:
            return False, approved, (
                f"warning {warning['rule']} at line {warning['line']} has no unique active waiver"
            )
        waiver = matches[0]
        if warning.get("message") != EXPECTED_WARNING["message"]:
            return False, approved, f"warning message mismatch for {warning['rule']} line {warning['line']}"
        approved.append(
            {
                "id": waiver["id"],
                "rule": waiver["rule"],
                "file": waiver["file"],
                "line": waiver["line"],
                "source_sha256": waiver["source_sha256"],
                "scope": waiver["scope"],
            }
        )
    expected_rules = {item["rule"] for item in approved}
    if expected_rules != {EXPECTED_WARNING["rule"]}:
        return False, approved, "locked golden warning waiver set is incomplete"
    return True, approved, None


def parse_verilator_warnings(text: str, golden_path: Path) -> list[dict[str, Any]]:
    """Extract Verilator warning headers and their source line/message."""

    warnings: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^%Warning-(?P<rule>[A-Za-z0-9_]+):\s+(?P<file>.+?):(?P<line>\d+):\d+:\s+(?P<message>.*)$"
    )
    for raw in text.splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        source = Path(match.group("file")).resolve()
        warnings.append(
            {
                "rule": match.group("rule"),
                "file": str(source),
                "line": int(match.group("line")),
                "message": match.group("message").strip(),
                "golden_path_match": source == golden_path.resolve(),
                "raw": raw.strip(),
            }
        )
    return warnings


def generic_warning_lines(text: str) -> list[str]:
    """Find compiler warnings that are not Verilator ``%Warning-*`` headers."""

    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("%Warning-"):
            continue
        if re.search(r"\bwarning\s*:", stripped, flags=re.IGNORECASE):
            lines.append(stripped)
    return lines


def unparsed_verilator_warning_lines(
    text: str, parsed_warnings: list[dict[str, Any]]
) -> list[str]:
    """Return every Verilator warning header the structured parser did not bind.

    A warning that cannot be mapped to a source file/line is not safe to waive.  Keeping
    this separate from ``generic_warning_lines`` also catches unusual ``%Warning-*``
    formatting emitted by a future Verilator build.
    """

    parsed_raw = {str(item.get("raw", "")).strip() for item in parsed_warnings}
    return [
        stripped
        for raw in text.splitlines()
        if (stripped := raw.strip()).startswith("%Warning-") and stripped not in parsed_raw
    ]


def signed32(value: int) -> int:
    value &= MASK32
    return value - (1 << 32) if value & (1 << 31) else value


def mathematical_product(mul_signed: int, x: int, y: int) -> int:
    x &= MASK32
    y &= MASK32
    if mul_signed:
        return (signed32(x) * signed32(y)) & MASK64
    return (x * y) & MASK64


def directed_vectors() -> list[tuple[int, int, int]]:
    values = [
        (0x00000000, 0x00000000),
        (0x00000000, 0x00000001),
        (0x00000001, 0x00000001),
        (0x00000001, 0xFFFFFFFF),
        (0xFFFFFFFF, 0xFFFFFFFF),
        (0x80000000, 0x00000001),
        (0x00000001, 0x80000000),
        (0x80000000, 0xFFFFFFFF),
        (0xFFFFFFFF, 0x80000000),
        (0x80000000, 0x00000002),
        (0x7FFFFFFF, 0x7FFFFFFF),
        (0x80000000, 0x80000000),
        (0x7FFFFFFF, 0xFFFFFFFF),
        (0xFFFFFFFF, 0x7FFFFFFF),
        (0xAAAAAAAA, 0x55555555),
        (0x55555555, 0xAAAAAAAA),
    ]
    return [(signed, x, y) for signed in (0, 1) for x, y in values]


def make_vectors(seed: int, random_count: int) -> tuple[list[tuple[int, int, int]], int]:
    if random_count <= 0:
        raise MulDiffError("random vector count must be positive")
    rng = random.Random(seed)
    vectors = directed_vectors()
    directed_count = len(vectors)
    vectors.extend(
        (rng.getrandbits(1), rng.getrandbits(32), rng.getrandbits(32))
        for _ in range(random_count)
    )
    return vectors, directed_count


def write_vector_file(path: Path, vectors: Iterable[tuple[int, int, int]]) -> int:
    rows = ["# mul-diff vectors: signed x y"]
    count = 0
    for signed, x, y in vectors:
        if signed not in (0, 1) or not 0 <= x <= MASK32 or not 0 <= y <= MASK32:
            raise MulDiffError("vector contains a value outside the locked width")
        rows.append(f"{signed} {x:08x} {y:08x}")
        count += 1
    if count == 0:
        raise MulDiffError("zero vectors are not allowed")
    path.write_text("\n".join(rows) + "\n", encoding="ascii")
    return count


CPP_DRIVER = r'''// Generated by tools/mul_diff.py; do not use the DUT as an oracle.
#include "Vmul.h"
#include "verilated.h"

#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

static constexpr uint64_t MASK64 = UINT64_MAX;

static uint64_t model_product(unsigned signed_mode, uint32_t x, uint32_t y) {
    if (signed_mode != 0U) {
        const int64_t sx = static_cast<int64_t>(static_cast<int32_t>(x));
        const int64_t sy = static_cast<int64_t>(static_cast<int32_t>(y));
        return static_cast<uint64_t>(sx * sy);
    }
    return static_cast<uint64_t>(x) * static_cast<uint64_t>(y);
}

static uint64_t dut_result(const Vmul* dut) {
    return static_cast<uint64_t>(dut->result);
}

static bool parse_vector(const std::string& line, unsigned& signed_mode,
                         uint32_t& x, uint32_t& y) {
    std::istringstream stream(line);
    std::string sx, sy;
    if (!(stream >> signed_mode >> sx >> sy)) return false;
    if (signed_mode > 1U) return false;
    try {
        size_t end_x = 0, end_y = 0;
        unsigned long xv = std::stoul(sx, &end_x, 16);
        unsigned long yv = std::stoul(sy, &end_y, 16);
        if (end_x != sx.size() || end_y != sy.size() || xv > 0xffffffffUL || yv > 0xffffffffUL) return false;
        x = static_cast<uint32_t>(xv);
        y = static_cast<uint32_t>(yv);
        std::string extra;
        return !(stream >> extra);
    } catch (...) {
        return false;
    }
}

static void eval(Vmul* dut) { dut->eval(); }

static void tick(Vmul* dut) {
    dut->mul_clk = 0;
    eval(dut);
    dut->mul_clk = 1;
    eval(dut);
    dut->mul_clk = 0;
    eval(dut);
}

static bool fail(const std::string& kind, uint64_t edge, size_t index,
                 unsigned signed_mode, uint32_t x, uint32_t y,
                 uint64_t expected, uint64_t actual) {
    std::cerr << "MUL_MISMATCH kind=" << kind << " edge=" << edge
              << " index=" << index << " signed=" << signed_mode
              << " x=0x" << std::hex << std::setw(8) << std::setfill('0') << x
              << " y=0x" << std::setw(8) << y
              << " expected=0x" << std::setw(16) << expected
              << " actual=0x" << std::setw(16) << actual << std::dec << "\n";
    return false;
}

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: Vmul <vectors> <expected_count> <directed_count>\n";
        return 2;
    }
    std::ifstream input(argv[1]);
    if (!input) { std::cerr << "MUL_ERROR cannot open vectors\n"; return 2; }
    const size_t expected_count = static_cast<size_t>(std::stoull(argv[2]));
    const size_t directed_count = static_cast<size_t>(std::stoull(argv[3]));
    if (expected_count == 0 || directed_count == 0) {
        std::cerr << "MUL_ERROR zero vector count\n";
        return 2;
    }

    VerilatedContext* context = new VerilatedContext;
    Vmul* dut = new Vmul{context};
    dut->mul_clk = 0;
    dut->reset = 1;
    dut->mul_signed = 0;
    dut->x = 0;
    dut->y = 0;
    eval(dut);

    // The golden state has no reset assignment.  Deliberately do not inspect
    // result until the first !reset edge has captured a complete input.
    for (unsigned i = 0; i < 2; ++i) tick(dut);

    uint64_t edge = 0;
    size_t index = 0;
    size_t active = 0;
    size_t perturb_checks = 0;
    size_t reset_hold_checks = 0;
    uint64_t last_known = 0;
    bool known = false;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') continue;
        unsigned signed_mode = 0;
        uint32_t x = 0, y = 0;
        if (!parse_vector(line, signed_mode, x, y)) {
            std::cerr << "MUL_ERROR malformed vector at index " << index << "\n";
            delete dut; delete context; return 2;
        }
        dut->reset = 0;
        dut->mul_signed = signed_mode;
        dut->x = x;
        dut->y = y;
        eval(dut);
        // Inputs may move while the clock is low; the registered result must
        // remain unchanged after the first valid capture.
        if (known) {
            dut->mul_signed = signed_mode ^ 1U;
            dut->x = x ^ 0xa5a5a5a5U;
            dut->y = y ^ 0x5a5a5a5aU;
            eval(dut);
            const uint64_t perturbed = dut_result(dut);
            if (perturbed != last_known) {
                fail("no_clock", edge, index, signed_mode, x, y, last_known, perturbed);
                delete dut; delete context; return 1;
            }
            ++perturb_checks;
            dut->mul_signed = signed_mode;
            dut->x = x;
            dut->y = y;
            eval(dut);
        }
        tick(dut);
        ++edge;
        const uint64_t expected = model_product(signed_mode, x, y);
        const uint64_t actual = dut_result(dut);
        if (actual != expected) {
            fail("active", edge, index, signed_mode, x, y, expected, actual);
            delete dut; delete context; return 1;
        }
        last_known = actual;
        known = true;
        ++active;
        ++index;

        // Periodically exercise synchronous reset hold with changing inputs.
        if ((active % 257U) == 0U) {
            for (unsigned hold = 0; hold < 2; ++hold) {
                dut->reset = 1;
                dut->mul_signed = (signed_mode ^ hold) & 1U;
                dut->x = x + hold + 0x11111111U;
                dut->y = y ^ (0x33333333U + hold);
                tick(dut);
                ++edge;
                const uint64_t held = dut_result(dut);
                if (held != last_known) {
                    fail("reset_hold", edge, index, signed_mode, x, y, last_known, held);
                    delete dut; delete context; return 1;
                }
                ++reset_hold_checks;
            }
            dut->reset = 0;
        }
    }
    if (index != expected_count || active != expected_count) {
        std::cerr << "MUL_ERROR vector count mismatch expected=" << expected_count
                  << " actual=" << index << "\n";
        delete dut; delete context; return 1;
    }
    if (active < directed_count || perturb_checks == 0 || reset_hold_checks == 0 || !known) {
        std::cerr << "MUL_ERROR required checks were not executed\n";
        delete dut; delete context; return 1;
    }
    std::cout << "MUL_SELF_CHECK_PASS active=" << active
              << " directed=" << directed_count
              << " perturb=" << perturb_checks
              << " reset_hold=" << reset_hold_checks
              << " edges=" << edge << "\n";
    delete dut;
    delete context;
    return 0;
}
'''


def parse_driver_result(text: str) -> dict[str, Any]:
    mismatch = None
    for line in text.splitlines():
        if line.startswith("MUL_MISMATCH "):
            mismatch = line.strip()
            break
    marker = re.search(
        r"^MUL_SELF_CHECK_PASS active=(\d+) directed=(\d+) perturb=(\d+) reset_hold=(\d+) edges=(\d+)$",
        text,
        flags=re.MULTILINE,
    )
    return {
        "pass_marker": marker is not None,
        "active": int(marker.group(1)) if marker else 0,
        "directed": int(marker.group(2)) if marker else 0,
        "perturb": int(marker.group(3)) if marker else 0,
        "reset_hold": int(marker.group(4)) if marker else 0,
        "edges": int(marker.group(5)) if marker else 0,
        "first_mismatch": mismatch,
    }


def _write_driver(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CPP_DRIVER, encoding="utf-8", newline="\n")


def _write_command_log(path: Path, result: dict[str, Any]) -> None:
    path.write_text(str(result.get("stdout", "")), encoding="utf-8", errors="replace")


def _base_summary(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "mul-golden-diff",
        "status": "fail",
        "generated_at": now_iso(),
        "command": "golden",
        "vector_count": args.vector_count,
        "seed": args.seed,
        "claim_scope": "locked golden self-check against independent mathematical model only",
    }


def run_golden(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    started = time.monotonic()
    out_dir = args.out_dir.resolve()
    if out_dir.exists() and (out_dir.is_symlink() or any(out_dir.iterdir())):
        raise MulDiffError(f"output directory must be fresh: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = _base_summary(args)
    repo_root = args.manifest.resolve().parent.parent
    summary["repository_head"] = None
    try:
        values = parse_manifest(args.manifest.resolve())
        summary["manifest"] = {
            "path": str(args.manifest.resolve()),
            "sha256": sha256_file(args.manifest.resolve()),
            "team_golden_candidate": values[GOLDEN_COMMIT_KEY],
        }
        contract_dir = out_dir / "contract"
        contract_evidence = verify_contract(args.contract.resolve(), args.manifest.resolve(), contract_dir)
        summary["contract_evaluator"] = contract_evaluator_evidence(
            repo_root, contract_evidence
        )
        summary["contract"] = contract_evidence.get("contract")
        summary["golden_contract"] = contract_evidence.get("golden")
        summary["protocol"] = contract_evidence.get("protocol")
        summary["ports"] = contract_evidence.get("ports")
        stimulus = contract_evidence.get("stimulus", {})
        expected_seed = int(str(stimulus.get("seed", "0x0")), 0)
        expected_random = int(stimulus.get("random_vectors", 0))
        if args.seed != expected_seed or args.vector_count != expected_random:
            raise MulDiffError(
                f"CLI stimulus differs from locked contract: seed/count {args.seed:#x}/{args.vector_count} "
                f"!= {expected_seed:#x}/{expected_random}"
            )
        summary["stimulus"] = {
            "seed": f"0x{args.seed:x}",
            "random_vectors": args.vector_count,
        }
        blob_ref = f"{values[GOLDEN_COMMIT_KEY]}:{GOLDEN_PATH}"
        golden_dir = out_dir / "golden"
        golden_dir.mkdir(parents=True, exist_ok=True)
        golden = golden_dir / "mul.v"
        # Use cat-file via the contract validator's verified source, then read
        # it back from our own artifact so the compiler input is hash-bound.
        golden.write_bytes(_git_bytes(repo_root, ["cat-file", "blob", blob_ref]))
        if sha256_file(golden) != GOLDEN_SHA256 or golden.stat().st_size != GOLDEN_SIZE:
            raise MulDiffError("compiler golden artifact hash/size differs from locked blob")
        summary["golden_artifact"] = {
            "path": str(golden),
            "sha256": sha256_file(golden),
            "size": golden.stat().st_size,
            "git_ref": blob_ref,
        }

        vectors, directed_count = make_vectors(args.seed, args.vector_count)
        vector_path = out_dir / "vectors.txt"
        actual_count = write_vector_file(vector_path, vectors)
        if actual_count != directed_count + args.vector_count:
            raise MulDiffError("vector file count mismatch")
        summary["vectors"] = {
            "path": str(vector_path),
            "sha256": sha256_file(vector_path),
            "directed": directed_count,
            "random": args.vector_count,
            "total": actual_count,
        }

        waiver_path = args.waivers.resolve()
        summary["waivers"] = {"path": str(waiver_path), "sha256": sha256_file(waiver_path) if waiver_path.is_file() else None}
        driver_path = out_dir / "driver" / "mul_diff_driver.cpp"
        _write_driver(driver_path)
        summary["driver"] = {"path": str(driver_path), "sha256": sha256_file(driver_path), "version": DRIVER_VERSION}
        verilator = checked_executable(values, args.verilator, "verilator", "verilator_binary_sha256")
        summary["verilator"] = {"path": str(verilator), "sha256": sha256_file(verilator)}
        version = run_command([str(verilator), "--version"], cwd=out_dir, timeout=args.timeout)
        version_text = str(version["stdout"]).strip()
        summary["verilator"]["version"] = version_text
        if version["returncode"] != 0 or version["timed_out"] or not re.search(r"Verilator\s+5\.020(?:\s|$)", version_text):
            raise MulDiffError(f"locked Verilator 5.020 check failed: {version_text}")

        # Verilator's --build delegates compilation to make and g++. Bind
        # both helpers to the same lock so an unrecorded host toolchain cannot
        # influence the cycle result.
        toolchain: dict[str, dict[str, Any]] = {}
        for tool_name, lock_key in (("make", "make_binary_sha256"), ("g++", "gpp_binary_sha256")):
            tool = checked_executable(values, None, tool_name, lock_key)
            tool_version = run_command([str(tool), "--version"], cwd=out_dir, timeout=args.timeout)
            if tool_version["returncode"] != 0 or tool_version["timed_out"]:
                raise MulDiffError(f"locked {tool_name} version check failed")
            lines = str(tool_version["stdout"]).splitlines()
            toolchain[tool_name] = {
                "path": str(tool),
                "sha256": sha256_file(tool),
                "version": lines[0] if lines else "",
            }
        summary["toolchain"] = toolchain

        obj_dir = out_dir / "obj_dir"
        binary = obj_dir / "Vmul"
        compile_argv = [
            str(verilator),
            "--cc",
            "--exe",
            "--build",
            "--top-module",
            "mul",
            "--Mdir",
            str(obj_dir),
            "--Wno-fatal",
            str(golden),
            str(driver_path),
        ]
        compile_result = run_command(compile_argv, cwd=out_dir, timeout=args.timeout)
        compile_log = out_dir / "compile.log"
        _write_command_log(compile_log, compile_result)
        warnings = parse_verilator_warnings(str(compile_result["stdout"]), golden)
        unparsed_warnings = unparsed_verilator_warning_lines(str(compile_result["stdout"]), warnings)
        generic_warnings = generic_warning_lines(str(compile_result["stdout"]))
        summary["compile"] = {
            "argv": compile_argv,
            "returncode": compile_result["returncode"],
            "timed_out": compile_result["timed_out"],
            "elapsed_seconds": compile_result["elapsed_seconds"],
            "log": str(compile_log),
            "log_sha256": sha256_file(compile_log),
            "warnings": warnings,
            "unparsed_verilator_warnings": unparsed_warnings,
            "generic_warnings": generic_warnings,
        }
        golden_ref = f"{values[GOLDEN_COMMIT_KEY]}:{GOLDEN_PATH}"
        warnings_for_match = [
            warning
            for warning in warnings
            if warning["golden_path_match"]
        ]
        non_golden_warnings = [
            warning
            for warning in warnings
            if not warning["golden_path_match"]
        ]
        summary["compile"]["non_golden_warnings"] = non_golden_warnings
        warning_ok, approved, warning_error = approved_warning_suppressions(
            waiver_path,
            golden_ref=golden_ref,
            golden_sha256=GOLDEN_SHA256,
            warnings=warnings_for_match,
        )
        summary["waivers"]["approved_warning_suppressions"] = approved
        summary["waivers"]["warning_error"] = warning_error
        if compile_result["returncode"] != 0 or compile_result["timed_out"]:
            raise MulDiffError("Verilator compile failed or timed out")
        if generic_warnings or non_golden_warnings or unparsed_warnings:
            raise MulDiffError(
                "compile emitted a warning outside the locked golden waiver scope"
            )
        if len(warnings_for_match) != 1 or not warning_ok:
            raise MulDiffError(warning_error or "compile emitted an unapproved warning")
        if not binary.is_file() or binary.stat().st_size == 0:
            raise MulDiffError(f"Verilator binary artifact is missing: {binary}")
        summary["binary"] = {"path": str(binary), "sha256": sha256_file(binary), "size": binary.stat().st_size}

        simulation_argv = [str(binary), str(vector_path), str(actual_count), str(directed_count)]
        simulation_result = run_command(simulation_argv, cwd=out_dir, timeout=args.timeout)
        simulation_log = out_dir / "simulation.log"
        _write_command_log(simulation_log, simulation_result)
        parsed = parse_driver_result(str(simulation_result["stdout"]))
        summary["simulation"] = {
            "argv": simulation_argv,
            "returncode": simulation_result["returncode"],
            "timed_out": simulation_result["timed_out"],
            "elapsed_seconds": simulation_result["elapsed_seconds"],
            "log": str(simulation_log),
            "log_sha256": sha256_file(simulation_log),
            "parser": parsed,
            "warnings": generic_warning_lines(str(simulation_result["stdout"])),
        }
        if simulation_result["returncode"] != 0 or simulation_result["timed_out"]:
            raise MulDiffError("cycle driver failed or timed out")
        if summary["simulation"]["warnings"] or "SKIP" in str(simulation_result["stdout"]).upper():
            raise MulDiffError("cycle driver emitted warning or SKIP")
        if not parsed["pass_marker"] or parsed["active"] != actual_count or parsed["directed"] != directed_count:
            raise MulDiffError("cycle driver did not publish the complete PASS marker")
        if parsed["first_mismatch"]:
            raise MulDiffError(parsed["first_mismatch"])
        summary["counts"] = {
            "planned": actual_count,
            "executed": parsed["active"],
            "passed": parsed["active"],
            "failed": 0,
            "skipped": 0,
        }
        summary["status"] = "pass"
        return 0, summary
    except (MulDiffError, OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        summary["error"] = str(error)
        summary.setdefault("counts", {"planned": 0, "executed": 0, "passed": 0, "failed": 1, "skipped": 0})
        return 1, summary
    finally:
        summary["repository_head"] = _git_head(repo_root)
        summary["evaluator_sha256"] = sha256_file(Path(__file__))
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_json(out_dir / "summary.json", summary)


def _fresh_output_directory(path: Path) -> Path:
    """Resolve an output path without following a caller-supplied symlink."""

    raw = Path(path).expanduser()
    if raw.is_symlink():
        raise MulDiffError(f"output directory must not be a symlink: {raw}")
    resolved = raw.resolve()
    if resolved.exists():
        if not resolved.is_dir():
            raise MulDiffError(f"output path must be a directory: {resolved}")
        if any(resolved.iterdir()):
            raise MulDiffError(f"output directory must be fresh: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _candidate_source(path: Path) -> tuple[Path, str, int]:
    """Return a regular candidate source and its initial content identity."""

    raw = Path(path).expanduser()
    if raw.is_symlink() or not raw.is_file():
        raise MulDiffError(f"candidate RTL must be a regular file: {raw}")
    resolved = raw.resolve()
    if resolved.is_symlink() or not resolved.is_file():
        raise MulDiffError(f"candidate RTL changed to a non-regular file: {resolved}")
    return resolved, sha256_file(resolved), resolved.stat().st_size


def _candidate_source_stable(path: Path, before_sha256: str) -> tuple[bool, str, int]:
    """Re-check source identity after compilation to catch in-place tampering."""

    if path.is_symlink() or not path.is_file():
        raise MulDiffError(f"candidate RTL disappeared or became a symlink: {path}")
    after_sha256 = sha256_file(path)
    after_size = path.stat().st_size
    return after_sha256 == before_sha256, after_sha256, after_size


def _snapshot_candidate(
    candidate: Path, source_sha256: str, source_size: int, out_dir: Path
) -> Path:
    """Copy the hash-bound source once and make all tools consume that snapshot."""

    snapshot_dir = out_dir / "input"
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    snapshot = snapshot_dir / "mul.v"
    payload = candidate.read_bytes()
    if len(payload) != source_size or sha256_bytes(payload) != source_sha256:
        raise MulDiffError("candidate RTL changed while its input snapshot was created")
    snapshot.write_bytes(payload)
    if snapshot.is_symlink() or not snapshot.is_file():
        raise MulDiffError(f"candidate snapshot is not a regular file: {snapshot}")
    if snapshot.stat().st_size != source_size or sha256_file(snapshot) != source_sha256:
        raise MulDiffError("candidate snapshot hash/size differs from the source")
    return snapshot


def run_candidate(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    """Run the candidate RTL against the independent cycle driver.

    Candidate compilation is stricter than the golden-only gate: every warning is an
    error, and the candidate source hash must remain stable for the complete compile.
    """

    started = time.monotonic()
    out_dir = _fresh_output_directory(args.out_dir)
    summary = _base_summary(args)
    summary["gate"] = "mul-candidate-diff"
    summary["command"] = "candidate"
    summary["claim_scope"] = "candidate cycle differential against independent mathematical model"
    manifest_path = Path(args.manifest).expanduser()
    repo_root = manifest_path.resolve().parent.parent
    summary["repository_head"] = None
    try:
        values = parse_manifest(manifest_path.resolve())
        summary["manifest"] = {
            "path": str(manifest_path.resolve()),
            "sha256": sha256_file(manifest_path.resolve()),
            "team_golden_candidate": values[GOLDEN_COMMIT_KEY],
        }
        contract_dir = out_dir / "contract"
        contract_evidence = verify_contract(
            Path(args.contract).expanduser(), manifest_path, contract_dir
        )
        summary["contract_evaluator"] = contract_evaluator_evidence(
            repo_root, contract_evidence
        )
        summary["contract"] = contract_evidence.get("contract")
        summary["golden_contract"] = contract_evidence.get("golden")
        summary["protocol"] = contract_evidence.get("protocol")
        summary["ports"] = contract_evidence.get("ports")
        stimulus = contract_evidence.get("stimulus", {})
        expected_seed = int(str(stimulus.get("seed", "0x0")), 0)
        expected_random = int(stimulus.get("random_vectors", 0))
        if args.seed != expected_seed or args.vector_count != expected_random:
            raise MulDiffError(
                f"CLI stimulus differs from locked contract: seed/count {args.seed:#x}/{args.vector_count} "
                f"!= {expected_seed:#x}/{expected_random}"
            )
        summary["stimulus"] = {
            "seed": f"0x{args.seed:x}",
            "random_vectors": args.vector_count,
        }

        candidate, source_sha256, source_size = _candidate_source(args.rtl)
        summary["candidate"] = {
            "path": str(candidate),
            "sha256_before": source_sha256,
            "sha256": source_sha256,
            "size_before": source_size,
            "size": source_size,
        }
        snapshot = _snapshot_candidate(candidate, source_sha256, source_size, out_dir)
        summary["candidate"].update(
            {
                "snapshot": str(snapshot),
                "snapshot_sha256": sha256_file(snapshot),
                "snapshot_size": snapshot.stat().st_size,
            }
        )

        vectors, directed_count = make_vectors(args.seed, args.vector_count)
        vector_path = out_dir / "vectors.txt"
        actual_count = write_vector_file(vector_path, vectors)
        if actual_count != directed_count + args.vector_count:
            raise MulDiffError("vector file count mismatch")
        summary["vectors"] = {
            "path": str(vector_path),
            "sha256": sha256_file(vector_path),
            "directed": directed_count,
            "random": args.vector_count,
            "total": actual_count,
        }

        driver_path = out_dir / "driver" / "mul_diff_driver.cpp"
        _write_driver(driver_path)
        summary["driver"] = {
            "path": str(driver_path),
            "sha256": sha256_file(driver_path),
            "version": DRIVER_VERSION,
        }
        verilator = checked_executable(
            values, args.verilator, "verilator", "verilator_binary_sha256"
        )
        summary["verilator"] = {"path": str(verilator), "sha256": sha256_file(verilator)}
        version = run_command([str(verilator), "--version"], cwd=out_dir, timeout=args.timeout)
        version_text = str(version["stdout"]).strip()
        summary["verilator"]["version"] = version_text
        if version["returncode"] != 0 or version["timed_out"] or not re.search(
            r"Verilator\s+5\.020(?:\s|$)", version_text
        ):
            raise MulDiffError(f"locked Verilator 5.020 check failed: {version_text}")

        toolchain: dict[str, dict[str, Any]] = {}
        for tool_name, lock_key in (("make", "make_binary_sha256"), ("g++", "gpp_binary_sha256")):
            tool = checked_executable(values, None, tool_name, lock_key)
            tool_version = run_command([str(tool), "--version"], cwd=out_dir, timeout=args.timeout)
            if tool_version["returncode"] != 0 or tool_version["timed_out"]:
                raise MulDiffError(f"locked {tool_name} version check failed")
            lines = str(tool_version["stdout"]).splitlines()
            toolchain[tool_name] = {
                "path": str(tool),
                "sha256": sha256_file(tool),
                "version": lines[0] if lines else "",
            }
        summary["toolchain"] = toolchain

        obj_dir = out_dir / "obj_dir"
        binary = obj_dir / "Vmul"
        compile_argv = [
            str(verilator),
            "--cc",
            "--exe",
            "--build",
            "--top-module",
            "mul",
            "--Mdir",
            str(obj_dir),
            "-Wall",
            "--Wno-fatal",
            str(snapshot),
            str(driver_path),
        ]
        compile_result = run_command(compile_argv, cwd=out_dir, timeout=args.timeout)
        compile_log = out_dir / "compile.log"
        _write_command_log(compile_log, compile_result)
        warnings = parse_verilator_warnings(str(compile_result["stdout"]), snapshot)
        unparsed_warnings = unparsed_verilator_warning_lines(
            str(compile_result["stdout"]), warnings
        )
        generic_warnings = generic_warning_lines(str(compile_result["stdout"]))
        source_stable, source_after_sha256, source_after_size = _candidate_source_stable(
            candidate, source_sha256
        )
        snapshot_stable, snapshot_after_sha256, snapshot_after_size = _candidate_source_stable(
            snapshot, source_sha256
        )
        summary["candidate"].update(
            {
                "sha256_after": source_after_sha256,
                "size_after": source_after_size,
                "snapshot_sha256_after": snapshot_after_sha256,
                "snapshot_size_after": snapshot_after_size,
                "source_stable": source_stable,
                "snapshot_stable": snapshot_stable,
            }
        )
        summary["compile"] = {
            "argv": compile_argv,
            "returncode": compile_result["returncode"],
            "timed_out": compile_result["timed_out"],
            "elapsed_seconds": compile_result["elapsed_seconds"],
            "log": str(compile_log),
            "log_sha256": sha256_file(compile_log),
            "warnings": warnings,
            "unparsed_verilator_warnings": unparsed_warnings,
            "generic_warnings": generic_warnings,
            "warning_count": len(warnings) + len(unparsed_warnings) + len(generic_warnings),
        }
        if compile_result["returncode"] != 0 or compile_result["timed_out"]:
            raise MulDiffError("candidate Verilator compile failed or timed out")
        if not source_stable:
            raise MulDiffError("candidate RTL changed during compilation")
        if not snapshot_stable:
            raise MulDiffError("candidate snapshot changed during compilation")
        if warnings or unparsed_warnings or generic_warnings:
            raise MulDiffError("candidate Verilator -Wall emitted a warning")
        if not binary.is_file() or binary.stat().st_size == 0:
            raise MulDiffError(f"candidate Verilator binary artifact is missing: {binary}")
        summary["binary"] = {
            "path": str(binary),
            "sha256": sha256_file(binary),
            "size": binary.stat().st_size,
        }

        simulation_argv = [str(binary), str(vector_path), str(actual_count), str(directed_count)]
        simulation_result = run_command(simulation_argv, cwd=out_dir, timeout=args.timeout)
        simulation_log = out_dir / "simulation.log"
        _write_command_log(simulation_log, simulation_result)
        parsed = parse_driver_result(str(simulation_result["stdout"]))
        summary["simulation"] = {
            "argv": simulation_argv,
            "returncode": simulation_result["returncode"],
            "timed_out": simulation_result["timed_out"],
            "elapsed_seconds": simulation_result["elapsed_seconds"],
            "log": str(simulation_log),
            "log_sha256": sha256_file(simulation_log),
            "parser": parsed,
            "warnings": generic_warning_lines(str(simulation_result["stdout"])),
        }
        if simulation_result["returncode"] != 0 or simulation_result["timed_out"]:
            raise MulDiffError("candidate cycle driver failed or timed out")
        if summary["simulation"]["warnings"] or "SKIP" in str(simulation_result["stdout"]).upper():
            raise MulDiffError("candidate cycle driver emitted warning or SKIP")
        if not parsed["pass_marker"] or parsed["active"] != actual_count or parsed["directed"] != directed_count:
            raise MulDiffError("candidate cycle driver did not publish the complete PASS marker")
        if parsed["first_mismatch"]:
            raise MulDiffError(parsed["first_mismatch"])
        final_stable, final_sha256, final_size = _candidate_source_stable(
            candidate, source_sha256
        )
        snapshot_final_stable, snapshot_final_sha256, snapshot_final_size = (
            _candidate_source_stable(snapshot, source_sha256)
        )
        summary["candidate"].update(
            {
                "sha256_final": final_sha256,
                "size_final": final_size,
                "snapshot_sha256_final": snapshot_final_sha256,
                "snapshot_size_final": snapshot_final_size,
                "source_stable": source_stable and final_stable,
                "snapshot_stable": snapshot_stable and snapshot_final_stable,
            }
        )
        if not final_stable:
            raise MulDiffError("candidate RTL changed during simulation")
        if not snapshot_final_stable:
            raise MulDiffError("candidate snapshot changed during simulation")
        summary["counts"] = {
            "planned": actual_count,
            "executed": parsed["active"],
            "passed": parsed["active"],
            "failed": 0,
            "skipped": 0,
        }
        summary["status"] = "pass"
        return 0, summary
    except (
        MulDiffError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        summary["error"] = str(error)
        summary.setdefault(
            "counts", {"planned": 0, "executed": 0, "passed": 0, "failed": 1, "skipped": 0}
        )
        return 1, summary
    finally:
        summary["repository_head"] = _git_head(repo_root)
        summary["evaluator_sha256"] = sha256_file(Path(__file__))
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_json(out_dir / "summary.json", summary)


def _git_head(repo_root: Path) -> str | None:
    try:
        return _git_bytes(repo_root, ["rev-parse", "HEAD"]).decode("ascii").strip()
    except (MulDiffError, OSError, UnicodeError, subprocess.SubprocessError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    golden = subparsers.add_parser("golden", help="run locked golden cycle differential")
    golden.add_argument("--contract", type=Path, required=True)
    golden.add_argument("--manifest", type=Path, required=True)
    golden.add_argument("--out-dir", type=Path, required=True)
    golden.add_argument("--vector-count", type=int, default=DEFAULT_VECTOR_COUNT)
    golden.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    golden.add_argument("--timeout", type=int, default=900)
    golden.add_argument("--verilator", type=str, default=None)
    golden.add_argument("--waivers", type=Path, default=Path("lint-waivers.yml"))
    candidate = subparsers.add_parser(
        "candidate", help="run candidate RTL against the independent cycle model"
    )
    candidate.add_argument("--contract", type=Path, required=True)
    candidate.add_argument("--manifest", type=Path, required=True)
    candidate.add_argument("--rtl", type=Path, required=True)
    candidate.add_argument("--out-dir", type=Path, required=True)
    candidate.add_argument("--vector-count", type=int, default=DEFAULT_VECTOR_COUNT)
    candidate.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    candidate.add_argument("--timeout", type=int, default=900)
    candidate.add_argument("--verilator", type=str, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    if not sys.flags.isolated:
        print("mul_diff.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    if args.command not in {"golden", "candidate"}:
        return 2
    if args.vector_count < 4096 or args.seed < 0 or args.timeout <= 0:
        print("ERROR: vector-count must be >=4096, seed non-negative, timeout positive", file=sys.stderr)
        return 2
    try:
        if args.command == "golden":
            code, summary = run_golden(args)
        else:
            code, summary = run_candidate(args)
    except MulDiffError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
