#!/usr/bin/env python3
"""Cycle-accurate differential harness for the locked openLA500 divider.

The historical divider is a particularly awkward Verilog leaf: the module and
one of its ports are both named ``div`` (which older simulators accepted, but
Verilator's C++ backend rejects), and the result is only valid on the re-arm
edge following the one-cycle ``complete`` pulse.  This runner keeps the source
blob immutable, applies one auditable module-name-only normalization in a
fresh build directory, and drives an independent mathematical model.

The golden command is deliberately fail-closed.  A warning outside the exact
three warnings emitted by the locked source, a timeout, a malformed/``SKIP``
marker, a source change, or a missing result is a failed gate.  Two mutated
golden controls are compiled and expected to fail, so a permanently passing
driver cannot masquerade as differential evidence.
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
import time
from typing import Any, Iterable


GOLDEN_COMMIT_KEY = "team_golden_candidate"
GOLDEN_PATH = "rtl/div.v"
GOLDEN_SHA256 = "7e499f4c43c92154d1d4e21be2f269ac140b4f2b2d944677c71f6f4213b66dc6"
GOLDEN_SIZE = 2642
DEFAULT_SEED = 0x158AA8
DEFAULT_VECTOR_COUNT = 4096
MASK32 = (1 << 32) - 1
DRIVER_VERSION = "div-diff-driver-v1"
NORMALIZED_MODULE = "div_golden"

# These are source-bound approvals, not a global warning suppression.  The
# source hash and transformed-source hash are recorded beside every result;
# any message/line drift or an additional warning fails the gate.
EXPECTED_GOLDEN_WARNINGS = (
    (
        "WIDTHTRUNC",
        82,
        "Bit extraction of var[32:0] requires 6 bit index, not 8 bits.",
    ),
    ("UNUSEDSIGNAL", 85, "Bits of signal are not used: 'TmpS'[32]"),
    ("UNUSEDSIGNAL", 85, "Bits of signal are not used: 'TmpR'[32]"),
)
LOCKED_ARITHMETIC = {
    "quotient": "truncate_toward_zero",
    "remainder_sign": "dividend",
    "signed_overflow": "wrap_32bit",
    "divide_by_zero": {
        "unsigned_quotient": "0xffffffff",
        "signed_nonnegative_quotient": "0xffffffff",
        "signed_negative_quotient": "0x00000001",
        "remainder": "dividend_bits",
    },
    "output_width": 32,
}


class DivDiffError(RuntimeError):
    """Raised when the harness cannot establish a trustworthy result."""


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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    temporary.replace(path)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = OrderedDict()
    for key, value in pairs:
        if key in result:
            raise DivDiffError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise DivDiffError(f"JSON artifact must be a regular file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DivDiffError(f"invalid JSON artifact {path}: {error}") from error


def parse_manifest(path: Path) -> dict[str, str]:
    """Parse the lock file and reject duplicate or malformed entries."""

    if path.is_symlink() or not path.is_file():
        raise DivDiffError(f"manifest must be a regular file: {path}")
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise DivDiffError(f"cannot read manifest: {error}") from error
    for line_number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise DivDiffError(f"manifest line {line_number} is not key=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or key in values:
            raise DivDiffError(f"manifest line {line_number} has an invalid/duplicate key")
        values[key] = value
    commit = values.get(GOLDEN_COMMIT_KEY, "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise DivDiffError(f"manifest {GOLDEN_COMMIT_KEY} must be a full 40-hex SHA")
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
        raise DivDiffError(f"Git metadata is missing: {dot_git}")
    line = dot_git.read_text(encoding="utf-8").strip()
    if not line.startswith("gitdir:"):
        raise DivDiffError(f"invalid Git worktree pointer: {dot_git}")
    raw = line.removeprefix("gitdir:").strip()
    for candidate in _git_dir_candidates(repo_root, raw):
        if candidate.is_dir():
            return candidate.resolve()
    raise DivDiffError(f"Git worktree metadata target is missing: {raw}")


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
        raise DivDiffError(f"cannot execute git: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise DivDiffError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _git_head(repo_root: Path) -> str:
    head = _run_git(repo_root, ["rev-parse", "HEAD"]).decode("ascii", errors="replace").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise DivDiffError("cannot resolve repository HEAD")
    return head


def _blob(repo_root: Path, manifest: dict[str, str]) -> bytes:
    ref = f"{manifest[GOLDEN_COMMIT_KEY]}:{GOLDEN_PATH}"
    object_type = _run_git(repo_root, ["cat-file", "-t", ref]).decode("ascii", errors="replace").strip()
    if object_type != "blob":
        raise DivDiffError(f"locked golden object is not a blob: {ref}")
    payload = _run_git(repo_root, ["cat-file", "blob", ref])
    if sha256_bytes(payload) != GOLDEN_SHA256 or len(payload) != GOLDEN_SIZE:
        raise DivDiffError("locked div blob hash/size differs from the contract")
    return payload


def resolve_executable(value: str | None, default: str) -> Path:
    candidate = value or shutil.which(default)
    if not candidate:
        raise DivDiffError(f"required executable is not on PATH: {default}")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise DivDiffError(f"executable is missing or not executable: {path}")
    return path


def checked_executable(values: dict[str, str], value: str | None, name: str, lock_key: str) -> Path:
    path = resolve_executable(value, name)
    expected = values.get(lock_key)
    if not expected:
        raise DivDiffError(f"manifest.lock is missing {lock_key}")
    if sha256_file(path) != expected:
        raise DivDiffError(f"{name} binary hash differs from manifest.lock: {path}")
    return path


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a command with process-group timeout and captured output."""

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


def signed32(value: int) -> int:
    value &= MASK32
    return value - (1 << 32) if value & (1 << 31) else value


def mathematical_division(signed_mode: int, x: int, y: int) -> tuple[int, int]:
    """Return the LA32R DIV.W quotient/remainder, masked to 32 bits."""

    x &= MASK32
    y &= MASK32
    sx = signed32(x)
    sy = signed32(y)
    if y == 0:
        # This is the architectural openLA500 behavior, not Python's choice.
        if signed_mode and sx < 0:
            return 1, x
        return MASK32, x
    if not signed_mode:
        return (x // y) & MASK32, (x % y) & MASK32
    ax = abs(sx)
    ay = abs(sy)
    quotient = ax // ay
    remainder = ax % ay
    if (sx < 0) != (sy < 0):
        quotient = -quotient
    if sx < 0:
        remainder = -remainder
    return quotient & MASK32, remainder & MASK32


def directed_vectors() -> list[tuple[int, int, int]]:
    values = [
        (0x00000000, 0x00000000),
        (0x00000000, 0x00000001),
        (0x00000001, 0x00000001),
        (0x00000001, 0x00000002),
        (0x00000002, 0x00000001),
        (0x00000007, 0x00000003),
        (0xFFFFFFFF, 0x00000001),
        (0xFFFFFFFF, 0xFFFFFFFF),
        (0x80000000, 0x00000001),
        (0x80000000, 0x00000002),
        (0x7FFFFFFF, 0x00000002),
        (0x7FFFFFFF, 0x7FFFFFFF),
        (0x80000000, 0xFFFFFFFF),
        (0xFFFFFFFF, 0x80000000),
        (0x80000000, 0x80000000),
        (0xAAAAAAAA, 0x55555555),
        (0x55555555, 0xAAAAAAAA),
        (0x12345678, 0x00000100),
        (0xDEADBEEF, 0x00000007),
        (0x00000001, 0x80000000),
    ]
    return [(signed, x, y) for signed in (0, 1) for x, y in values]


def make_vectors(seed: int, random_count: int) -> tuple[list[tuple[int, int, int]], int]:
    if random_count < DEFAULT_VECTOR_COUNT:
        raise DivDiffError(f"vector-count must be >={DEFAULT_VECTOR_COUNT}")
    rng = random.Random(seed)
    vectors = directed_vectors()
    directed_count = len(vectors)
    for index in range(random_count):
        signed_mode = rng.getrandbits(1)
        x = rng.getrandbits(32)
        # Force frequent divide-by-zero and sign/boundary coverage instead of
        # relying on a negligible random chance of drawing y==0.
        if index % 257 == 0:
            y = 0
        elif index % 257 == 1:
            y = 1 << 31
        else:
            y = rng.getrandbits(32)
        vectors.append((signed_mode, x, y))
    return vectors, directed_count


def write_vector_file(path: Path, vectors: Iterable[tuple[int, int, int]]) -> int:
    rows = ["# div-diff vectors: signed x y; operands are held through complete"]
    count = 0
    for signed_mode, x, y in vectors:
        if signed_mode not in (0, 1) or not 0 <= x <= MASK32 or not 0 <= y <= MASK32:
            raise DivDiffError("vector contains a value outside the locked width")
        rows.append(f"{signed_mode} {x:08x} {y:08x}")
        count += 1
    if not count:
        raise DivDiffError("zero vectors are not allowed")
    with path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write("\n".join(rows) + "\n")
    return count


CPP_DRIVER = r'''// Generated by tools/div_diff.py; the DUT is never used as an oracle.
#include "Vdiv_golden.h"
#include "verilated.h"

#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

static constexpr uint32_t MASK32 = 0xffffffffU;

static int64_t signed32(uint32_t value) {
    return (value & 0x80000000U) ? static_cast<int64_t>(value) - 0x100000000LL
                                 : static_cast<int64_t>(value);
}

struct Result { uint32_t q; uint32_t r; };

static Result model(unsigned signed_mode, uint32_t x, uint32_t y) {
    const int64_t sx = signed32(x);
    const int64_t sy = signed32(y);
    if (y == 0U) {
        if (signed_mode != 0U && sx < 0) return {1U, x};
        return {MASK32, x};
    }
    if (signed_mode == 0U) return {x / y, x % y};
    const uint64_t ax = sx < 0 ? static_cast<uint64_t>(-sx) : static_cast<uint64_t>(sx);
    const uint64_t ay = sy < 0 ? static_cast<uint64_t>(-sy) : static_cast<uint64_t>(sy);
    int64_t q = static_cast<int64_t>(ax / ay);
    int64_t r = static_cast<int64_t>(ax % ay);
    if ((sx < 0) != (sy < 0)) q = -q;
    if (sx < 0) r = -r;
    return {static_cast<uint32_t>(q), static_cast<uint32_t>(r)};
}

static uint32_t unsigned_remainder_model(unsigned signed_mode, uint32_t x, uint32_t y) {
    if (signed_mode == 0U) return y == 0U ? x : x % y;
    const int64_t sx = signed32(x);
    const int64_t sy = signed32(y);
    const uint64_t ax = sx < 0 ? static_cast<uint64_t>(-sx) : static_cast<uint64_t>(sx);
    if (y == 0U) return static_cast<uint32_t>(ax);
    const uint64_t ay = sy < 0 ? static_cast<uint64_t>(-sy) : static_cast<uint64_t>(sy);
    return static_cast<uint32_t>(ax % ay);
}

static void eval(Vdiv_golden* dut) { dut->eval(); }

static void tick(Vdiv_golden* dut) {
    dut->div_clk = 0; eval(dut);
    dut->div_clk = 1; eval(dut);
    dut->div_clk = 0; eval(dut);
}

static bool fail(const std::string& kind, uint64_t edge, size_t index,
                 unsigned signed_mode, uint32_t x, uint32_t y,
                 uint32_t expected_q, uint32_t expected_r,
                 uint32_t actual_q, uint32_t actual_r) {
    std::cerr << "DIV_MISMATCH kind=" << kind << " edge=" << edge
              << " index=" << index << " signed=" << signed_mode
              << " x=0x" << std::hex << std::setw(8) << std::setfill('0') << x
              << " y=0x" << std::setw(8) << y
              << " expected_s=0x" << std::setw(8) << expected_q
              << " expected_r=0x" << std::setw(8) << expected_r
              << " actual_s=0x" << std::setw(8) << actual_q
              << " actual_r=0x" << std::setw(8) << actual_r << std::dec << "\n";
    return false;
}

static bool parse_vector(const std::string& line, unsigned& signed_mode,
                         uint32_t& x, uint32_t& y) {
    std::istringstream stream(line);
    std::string sx, sy;
    if (!(stream >> signed_mode >> sx >> sy) || signed_mode > 1U) return false;
    try {
        size_t ex = 0, ey = 0;
        const unsigned long long xv = std::stoull(sx, &ex, 16);
        const unsigned long long yv = std::stoull(sy, &ey, 16);
        if (ex != sx.size() || ey != sy.size() || xv > MASK32 || yv > MASK32) return false;
        std::string extra;
        if (stream >> extra) return false;
        x = static_cast<uint32_t>(xv); y = static_cast<uint32_t>(yv);
        return true;
    } catch (...) { return false; }
}

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: Vdiv_golden <vectors> <expected_count> <directed_count>\n";
        return 2;
    }
    std::ifstream input(argv[1]);
    if (!input) { std::cerr << "DIV_ERROR cannot open vectors\n"; return 2; }
    size_t expected_count = 0, directed_count = 0;
    try {
        expected_count = static_cast<size_t>(std::stoull(argv[2]));
        directed_count = static_cast<size_t>(std::stoull(argv[3]));
    } catch (...) { std::cerr << "DIV_ERROR malformed counts\n"; return 2; }
    if (!expected_count || !directed_count) {
        std::cerr << "DIV_ERROR zero vector count\n"; return 2;
    }

    VerilatedContext* context = new VerilatedContext;
    Vdiv_golden* dut = new Vdiv_golden{context};
    dut->div_clk = 0; dut->reset = 1; dut->div = 0;
    dut->div_signed = 0; dut->x = 0; dut->y = 0; eval(dut);
    uint64_t edge = 0;
    size_t reset_checks = 0, abort_checks = 0, active = 0;
    size_t complete_pulses = 0, result_checks = 0, divide_zero = 0;
    size_t pulse_quotient_checks = 0, historical_remainder_checks = 0;
    size_t signed_count = 0, unsigned_count = 0;
    uint32_t historical_unsigned_remainder = 0;

    // Synchronous reset is held for two edges before any output is observed.
    for (unsigned i = 0; i < 2; ++i) {
        tick(dut); ++edge;
        if (dut->complete != 0) {
            fail("reset_complete", edge, 0, 0, 0, 0, 0, 0, dut->s, dut->r);
            delete dut; delete context; return 1;
        }
        ++reset_checks;
    }
    dut->reset = 0; dut->div = 0; tick(dut); ++edge;
    if (dut->complete != 0) {
        fail("idle_complete", edge, 0, 0, 0, 0, 0, 0, dut->s, dut->r);
        delete dut; delete context; return 1;
    }
    ++reset_checks;

    size_t index = 0;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') continue;
        unsigned signed_mode = 0; uint32_t x = 0, y = 0;
        if (!parse_vector(line, signed_mode, x, y)) {
            std::cerr << "DIV_ERROR malformed vector at index " << index << "\n";
            delete dut; delete context; return 2;
        }
        if (signed_mode) ++signed_count; else ++unsigned_count;
        if (y == 0) ++divide_zero;

        // Abort a held request periodically.  The low request edge must clear
        // the partial state and must not produce a completion pulse.
        if ((index % 263U) == 0U) {
            dut->reset = 0; dut->div = 1; dut->div_signed = signed_mode;
            dut->x = x; dut->y = y;
            for (unsigned hold = 0; hold < 7; ++hold) {
                tick(dut); ++edge;
                if (dut->complete != 0) {
                    fail("abort_early_complete", edge, index, signed_mode, x, y,
                         0, 0, dut->s, dut->r);
                    delete dut; delete context; return 1;
                }
            }
            dut->div = 0; dut->x = x ^ 0x55aa55aaU; dut->y = y ^ 0xaa55aa55U;
            tick(dut); ++edge;
            if (dut->complete != 0) {
                fail("abort_complete", edge, index, signed_mode, x, y,
                     0, 0, dut->s, dut->r);
                delete dut; delete context; return 1;
            }
            ++abort_checks;
        }

        // Reset during an in-flight request.  Outputs are intentionally not
        // compared during reset because the historical RTL does not clear
        // every combinationally visible result register in that branch.
        if ((index % 257U) == 0U) {
            dut->reset = 0; dut->div = 1; dut->div_signed = signed_mode;
            dut->x = x; dut->y = y;
            for (unsigned hold = 0; hold < 5; ++hold) { tick(dut); ++edge; }
            dut->reset = 1; dut->div = 1;
            for (unsigned hold = 0; hold < 2; ++hold) {
                dut->x = x + hold + 1U; dut->y = y ^ (0x11111111U + hold);
                tick(dut); ++edge;
                if (dut->complete != 0) {
                    fail("reset_complete", edge, index, signed_mode, x, y,
                         0, 0, dut->s, dut->r);
                    delete dut; delete context; return 1;
                }
                ++reset_checks;
            }
            historical_unsigned_remainder = 0;
            dut->reset = 0; dut->div = 0; tick(dut); ++edge; ++reset_checks;
        }

        // A legal transaction holds all operands and the request high for all
        // 33 division edges.  The result is sampled only on the following
        // re-arm edge, when complete has fallen and both s/r are final.
        dut->reset = 0; dut->div = 1; dut->div_signed = signed_mode;
        dut->x = x; dut->y = y; eval(dut);
        const Result expected = model(signed_mode, x, y);
        for (unsigned held = 1; held <= 33; ++held) {
            tick(dut); ++edge;
            const int expected_complete = (held == 33) ? 1 : 0;
            if (dut->complete != expected_complete) {
                fail("complete_timing", edge, index, signed_mode, x, y,
                     expected_complete, 0, dut->complete, 0);
                delete dut; delete context; return 1;
            }
            if (expected_complete) {
                // E33 is a notification window.  The quotient is final, but
                // r still exposes the previously captured unsigned remainder
                // under the current transaction's sign correction.
                const uint32_t historical_r =
                    (signed_mode != 0U && (x & 0x80000000U) != 0U)
                        ? static_cast<uint32_t>(0U - historical_unsigned_remainder)
                        : historical_unsigned_remainder;
                if (static_cast<uint32_t>(dut->s) != expected.q ||
                    static_cast<uint32_t>(dut->r) != historical_r) {
                    fail("complete_window", edge, index, signed_mode, x, y,
                         expected.q, historical_r, dut->s, dut->r);
                    delete dut; delete context; return 1;
                }
                ++complete_pulses; ++pulse_quotient_checks;
                ++historical_remainder_checks;
            }
        }
        // Keep request and operands stable through the pulse and one capture
        // edge.  The golden's quotient may look settled one edge earlier, but
        // remainder/sign correction is not a valid contract until this edge.
        tick(dut); ++edge;
        if (dut->complete != 0 || static_cast<uint32_t>(dut->s) != expected.q ||
            static_cast<uint32_t>(dut->r) != expected.r) {
            fail("result", edge, index, signed_mode, x, y, expected.q, expected.r,
                 dut->s, dut->r);
            delete dut; delete context; return 1;
        }
        historical_unsigned_remainder = unsigned_remainder_model(signed_mode, x, y);
        ++result_checks; ++active; ++index;
        dut->div = 0; dut->x = x ^ 0xa5a5a5a5U; dut->y = y ^ 0x5a5a5a5aU;
        tick(dut); ++edge;
        if (dut->complete != 0) {
            fail("rearm_complete", edge, index, signed_mode, x, y,
                 expected.q, expected.r, dut->s, dut->r);
            delete dut; delete context; return 1;
        }
    }
    if (index != expected_count || active != expected_count ||
        directed_count > active || complete_pulses != active ||
        result_checks != active || reset_checks == 0 || abort_checks == 0 ||
        pulse_quotient_checks != active || historical_remainder_checks != active ||
        divide_zero == 0 || signed_count == 0 || unsigned_count == 0) {
        std::cerr << "DIV_ERROR count/check coverage mismatch expected=" << expected_count
                  << " active=" << active << " directed=" << directed_count
                  << " complete=" << complete_pulses << " results=" << result_checks
                  << " pulse_s=" << pulse_quotient_checks
                  << " historical_r=" << historical_remainder_checks
                  << " reset=" << reset_checks << " abort=" << abort_checks
                  << " divide_zero=" << divide_zero << " signed=" << signed_count
                  << " unsigned=" << unsigned_count << "\n";
        delete dut; delete context; return 1;
    }
    std::cout << "DIV_SELF_CHECK_PASS active=" << active
              << " directed=" << directed_count
              << " signed=" << signed_count << " unsigned=" << unsigned_count
              << " divide_zero=" << divide_zero
              << " complete_pulses=" << complete_pulses
              << " pulse_s=" << pulse_quotient_checks
              << " historical_r=" << historical_remainder_checks
              << " results=" << result_checks
              << " reset=" << reset_checks << " abort=" << abort_checks
              << " edges=" << edge << "\n";
    delete dut; delete context; return 0;
}
'''


def parse_verilator_warnings(text: str, source: Path) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"^%Warning-(?P<rule>[A-Za-z0-9_]+):\s+(?P<file>.+?):(?P<line>\d+):\d+:\s+(?P<message>.*)$"
    )
    warnings: list[dict[str, Any]] = []
    for raw in text.splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        warning_path = Path(match.group("file")).resolve()
        warnings.append(
            {
                "rule": match.group("rule"),
                "file": str(warning_path),
                "line": int(match.group("line")),
                "message": match.group("message").strip(),
                "source_path_match": warning_path == source.resolve(),
                "raw": raw.strip(),
            }
        )
    return warnings


def generic_warning_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("%Warning-")
        and re.search(r"\bwarning\s*:", line, flags=re.IGNORECASE)
    ]


def unparsed_warning_lines(text: str, parsed: list[dict[str, Any]]) -> list[str]:
    parsed_raw = {str(item.get("raw", "")).strip() for item in parsed}
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("%Warning-") and line.strip() not in parsed_raw
    ]


def warning_signature(warning: dict[str, Any]) -> tuple[str, int, str]:
    return str(warning["rule"]), int(warning["line"]), str(warning["message"])


def warning_policy(
    text: str, source: Path, *, golden: bool
) -> tuple[bool, list[dict[str, Any]], str | None]:
    parsed = parse_verilator_warnings(text, source)
    generic = generic_warning_lines(text)
    unparsed = unparsed_warning_lines(text, parsed)
    if generic or unparsed:
        return False, parsed, "unparsed or compiler warning emitted"
    if not all(item["source_path_match"] for item in parsed):
        return False, parsed, "warning references a non-input source"
    signatures = tuple(sorted(warning_signature(item) for item in parsed))
    if golden:
        if signatures != tuple(sorted(EXPECTED_GOLDEN_WARNINGS)):
            return False, parsed, (
                "golden warning set drifted: "
                f"expected={EXPECTED_GOLDEN_WARNINGS!r} actual={signatures!r}"
            )
    elif parsed:
        return False, parsed, "candidate/negative source emitted an unapproved warning"
    return True, parsed, None


def parse_driver_result(text: str) -> dict[str, Any]:
    mismatch = next(
        (line.strip() for line in text.splitlines() if line.startswith("DIV_MISMATCH ")),
        None,
    )
    error = next(
        (line.strip() for line in text.splitlines() if line.startswith("DIV_ERROR ")),
        None,
    )
    marker = re.search(
        r"^DIV_SELF_CHECK_PASS active=(\d+) directed=(\d+) signed=(\d+) unsigned=(\d+) "
        r"divide_zero=(\d+) complete_pulses=(\d+) pulse_s=(\d+) historical_r=(\d+) "
        r"results=(\d+) reset=(\d+) abort=(\d+) edges=(\d+)$",
        text,
        flags=re.MULTILINE,
    )
    skip = next(
        (line.strip() for line in text.splitlines() if re.search(r"\bSKIP\b", line, flags=re.IGNORECASE)),
        None,
    )
    return {
        "pass_marker": marker is not None,
        "active": int(marker.group(1)) if marker else 0,
        "directed": int(marker.group(2)) if marker else 0,
        "signed": int(marker.group(3)) if marker else 0,
        "unsigned": int(marker.group(4)) if marker else 0,
        "divide_zero": int(marker.group(5)) if marker else 0,
        "complete_pulses": int(marker.group(6)) if marker else 0,
        "pulse_s": int(marker.group(7)) if marker else 0,
        "historical_r": int(marker.group(8)) if marker else 0,
        "results": int(marker.group(9)) if marker else 0,
        "reset": int(marker.group(10)) if marker else 0,
        "abort": int(marker.group(11)) if marker else 0,
        "edges": int(marker.group(12)) if marker else 0,
        "first_mismatch": mismatch,
        "first_error": error,
        "skip": skip,
    }


def _write_driver(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(CPP_DRIVER)


def normalize_source(payload: bytes) -> bytes:
    """Rename only the module declaration to avoid Verilator's div/div clash."""

    needle = b"module div("
    if payload.count(needle) != 1:
        raise DivDiffError("golden source module declaration is not uniquely recognized")
    transformed = payload.replace(needle, b"module div_golden(", 1)
    if transformed.count(b"module div_golden(") != 1:
        raise DivDiffError("normalized source module declaration is not unique")
    return transformed


def mutate_source(payload: bytes, kind: str) -> bytes:
    if kind == "result_bit_flip":
        needle = b"assign s = TmpS[31:0];"
        replacement = b"assign s = TmpS[31:0] ^ 32'h00000001;"
    elif kind == "complete_timing":
        needle = b"assign complete = (count == 8'hff);"
        replacement = b"assign complete = (count == 8'hfe);"
    else:
        raise DivDiffError(f"unknown negative control: {kind}")
    if payload.count(needle) != 1:
        raise DivDiffError(f"negative control anchor is not unique: {kind}")
    return payload.replace(needle, replacement, 1)


def parse_manifest_tool(values: dict[str, str], value: str | None, name: str, key: str) -> Path:
    return checked_executable(values, value, name, key)


def _base_summary(args: argparse.Namespace, command: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "div-golden-diff" if command == "golden" else "div-candidate-diff",
        "status": "fail",
        "generated_at": now_iso(),
        "command": command,
        "vector_count": args.vector_count,
        "seed": args.seed,
        "claim_scope": "locked openLA500 div cycle behavior against an independent mathematical model",
        "counts": {"planned": 1, "executed": 0, "passed": 0, "failed": 1, "skipped": 0},
    }


def _fresh_out(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.exists() and (path.is_symlink() or not path.is_dir() or any(path.iterdir())):
        raise DivDiffError(f"output directory must be a fresh directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _persist(path: Path, summary: dict[str, Any]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    write_json(path / "summary.json", summary)


def _contract_evidence(args: argparse.Namespace, manifest: Path, out_dir: Path) -> dict[str, Any]:
    """Use div_contract.py when present, otherwise retain a locked fallback."""

    if args.contract is None:
        return {
            "contract": None,
            "golden": {"path": GOLDEN_PATH, "sha256": GOLDEN_SHA256, "size": GOLDEN_SIZE},
            "arithmetic": LOCKED_ARITHMETIC,
            "protocol": {
                "clock": "div_clk",
                "edge": "posedge",
                "reset": {"signal": "reset", "active_level": 1, "behavior": "synchronous"},
                "request": "div",
                "operands_stable": "from_accept_through_result_capture",
                "complete": {"assert_after_consecutive_request_edges": 33, "pulse_edges": 1},
                "result": {
                    "capture_edge": "first_posedge_after_complete",
                    "consecutive_request_edges_to_capture": 34,
                    "valid_window_edges": 1,
                    "complete_level_during_valid_window": 0,
                },
                "unknown_policy": "ignore_results_before_capture_edge",
            },
            "ports": {
                name: {"direction": direction, "width": width}
                for name, direction, width in (
                    ("div_clk", "input", 1), ("reset", "input", 1), ("div", "input", 1),
                    ("div_signed", "input", 1), ("x", "input", 32), ("y", "input", 32),
                    ("s", "output", 32), ("r", "output", 32), ("complete", "output", 1),
                )
            },
            "stimulus": {"seed": f"0x{args.seed:x}", "random_transactions": args.vector_count},
            "diff": {"runner": "verilator_cycle", "independent_model": True, "cycle_exact": True},
        }
    contract = args.contract.resolve()
    if contract.is_symlink() or not contract.is_file():
        raise DivDiffError(f"contract must be a regular file: {contract}")
    module_path = manifest.parent.parent / "tools" / "div_contract.py"
    if not module_path.is_file():
        raise DivDiffError(f"div contract validator is missing: {module_path}")
    spec = importlib.util.spec_from_file_location("_locked_div_contract", module_path)
    if spec is None or spec.loader is None:
        raise DivDiffError("cannot load div contract validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        evidence = module.verify_contract(contract, manifest, out_dir)
    except Exception as error:
        raise DivDiffError(str(error)) from error
    if not isinstance(evidence, dict):
        raise DivDiffError("div contract validator returned a non-object")
    if evidence.get("arithmetic") != LOCKED_ARITHMETIC:
        raise DivDiffError("div contract arithmetic differs from the runner's independent oracle")
    protocol = evidence.get("protocol")
    if not isinstance(protocol, dict):
        raise DivDiffError("div contract protocol evidence is missing")
    complete = protocol.get("complete")
    result = protocol.get("result")
    if (
        not isinstance(complete, dict)
        or complete.get("assert_after_consecutive_request_edges") != 33
        or complete.get("pulse_edges") != 1
        or not isinstance(result, dict)
        or result.get("capture_edge") != "first_posedge_after_complete"
        or result.get("consecutive_request_edges_to_capture") != 34
        or result.get("valid_window_edges") != 1
        or result.get("complete_level_during_valid_window") != 0
    ):
        raise DivDiffError("div contract E33/E34 timing differs from the cycle driver")
    return evidence


def _compile_and_run(
    *,
    source_payload: bytes,
    source_kind: str,
    vectors_path: Path,
    expected_count: int,
    directed_count: int,
    model_dir: Path,
    verilator: Path,
    timeout: int,
    values: dict[str, str],
    expected_compile_pass: bool,
) -> dict[str, Any]:
    model_dir.mkdir(parents=True, exist_ok=True)
    source_path = model_dir / "div_golden.v"
    transformed = normalize_source(source_payload)
    source_path.write_bytes(transformed)
    source_hash_before = sha256_file(source_path)
    driver_path = model_dir / "div_diff_driver.cpp"
    _write_driver(driver_path)
    driver_hash_before = sha256_file(driver_path)
    obj_dir = model_dir / "obj_dir"
    binary = obj_dir / "Vdiv_golden"
    compile_argv = [
        str(verilator), "--cc", "--exe", "--build", "--Wall", "--Wno-fatal",
        "--top-module", NORMALIZED_MODULE, "--prefix", "Vdiv_golden",
        "--Mdir", str(obj_dir), str(source_path), str(driver_path),
    ]
    compile_result = run_command(compile_argv, cwd=model_dir, timeout=timeout)
    compile_log = model_dir / "compile.log"
    compile_log.write_text(str(compile_result.get("stdout", "")), encoding="utf-8", errors="replace")
    warning_ok, warnings, warning_error = warning_policy(
        str(compile_result.get("stdout", "")),
        source_path,
        golden=(source_kind == "golden" or source_kind.startswith("negative:")),
    )
    compile_summary: dict[str, Any] = {
        "argv": compile_argv,
        "returncode": compile_result["returncode"],
        "timed_out": compile_result["timed_out"],
        "elapsed_seconds": compile_result["elapsed_seconds"],
        "log": str(compile_log),
        "log_sha256": sha256_file(compile_log),
        "warnings": warnings,
        "warning_count": len(warnings),
        "warning_policy_pass": warning_ok,
        "warning_error": warning_error,
        "error_lines": [line for line in str(compile_result.get("stdout", "")).splitlines() if line.startswith("%Error")],
    }
    result: dict[str, Any] = {
        "source_kind": source_kind,
        "source": {
            "path": str(source_path),
            "sha256": source_hash_before,
            "size": source_path.stat().st_size,
            "original_sha256": sha256_bytes(source_payload),
            "original_size": len(source_payload),
            "normalization": "single module declaration div -> div_golden; no signal/body edits",
            "stable": False,
        },
        "driver": {"path": str(driver_path), "sha256": driver_hash_before, "version": DRIVER_VERSION},
        "compile": compile_summary,
        "status": "fail",
    }
    source_stable = sha256_file(source_path) == source_hash_before
    driver_stable = sha256_file(driver_path) == driver_hash_before
    result["source"]["stable"] = source_stable
    result["driver"]["stable"] = driver_stable
    if not source_stable:
        result["error"] = "normalized source changed during compilation"
        return result
    if not driver_stable:
        result["error"] = "driver changed during compilation"
        return result
    if compile_result["returncode"] != 0 or compile_result["timed_out"]:
        result["error"] = "Verilator compile failed or timed out"
        return result
    if not warning_ok:
        result["error"] = warning_error or "compile warning policy failed"
        return result
    if not binary.is_file() or binary.stat().st_size == 0:
        result["error"] = f"Verilator binary artifact is missing: {binary}"
        return result
    simulation_argv = [str(binary), str(vectors_path), str(expected_count), str(directed_count)]
    simulation_result = run_command(simulation_argv, cwd=model_dir, timeout=timeout)
    simulation_log = model_dir / "simulation.log"
    simulation_log.write_text(str(simulation_result.get("stdout", "")), encoding="utf-8", errors="replace")
    parsed = parse_driver_result(str(simulation_result.get("stdout", "")))
    result["simulation"] = {
        "argv": simulation_argv,
        "returncode": simulation_result["returncode"],
        "timed_out": simulation_result["timed_out"],
        "elapsed_seconds": simulation_result["elapsed_seconds"],
        "log": str(simulation_log),
        "log_sha256": sha256_file(simulation_log),
        "parsed": parsed,
    }
    if simulation_result["returncode"] != 0 or simulation_result["timed_out"]:
        result["error"] = "simulation failed or timed out"
        return result
    if parsed["skip"]:
        result["error"] = f"simulation emitted SKIP: {parsed['skip']}"
        return result
    if parsed["first_mismatch"] or parsed["first_error"] or not parsed["pass_marker"]:
        result["error"] = parsed["first_mismatch"] or parsed["first_error"] or "missing self-check marker"
        return result
    if parsed["active"] != expected_count or parsed["directed"] != directed_count:
        result["error"] = "simulation marker count differs from requested vectors"
        return result
    result["status"] = "pass"
    return result


def _toolchain(values: dict[str, str], args: argparse.Namespace, out_dir: Path) -> tuple[Path, dict[str, Any]]:
    verilator = parse_manifest_tool(values, args.verilator, "verilator", "verilator_binary_sha256")
    version = run_command([str(verilator), "--version"], cwd=out_dir, timeout=args.timeout)
    version_text = str(version["stdout"]).strip()
    if version["returncode"] != 0 or version["timed_out"] or not re.search(r"Verilator\s+5\.020(?:\s|$)", version_text):
        raise DivDiffError(f"locked Verilator 5.020 check failed: {version_text}")
    tools: dict[str, Any] = {
        "verilator": {"path": str(verilator), "sha256": sha256_file(verilator), "version": version_text}
    }
    for name, key in (("make", "make_binary_sha256"), ("g++", "gpp_binary_sha256")):
        tool = parse_manifest_tool(values, None, name, key)
        tool_version = run_command([str(tool), "--version"], cwd=out_dir, timeout=args.timeout)
        if tool_version["returncode"] != 0 or tool_version["timed_out"]:
            raise DivDiffError(f"locked {name} version check failed")
        tools[name] = {"path": str(tool), "sha256": sha256_file(tool), "version": str(tool_version["stdout"]).splitlines()[0] if str(tool_version["stdout"]).splitlines() else ""}
    return verilator, tools


def run_golden(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    started = time.monotonic()
    out_dir = _fresh_out(args.out_dir)
    summary = _base_summary(args, "golden")
    manifest_path = args.manifest.resolve()
    manifest_hash_before = sha256_file(manifest_path)
    repo_root = manifest_path.parent.parent
    try:
        values = parse_manifest(manifest_path)
        summary["repository_head"] = _git_head(repo_root)
        summary["manifest"] = {"path": str(manifest_path), "sha256": manifest_hash_before, "team_golden_candidate": values[GOLDEN_COMMIT_KEY]}
        contract_dir = out_dir / "contract"
        contract = _contract_evidence(args, manifest_path, contract_dir)
        summary["contract"] = contract.get("contract")
        summary["golden_contract"] = contract.get("golden")
        summary["protocol"] = contract.get("protocol")
        summary["ports"] = contract.get("ports")
        summary["arithmetic"] = contract.get("arithmetic")
        stimulus = contract.get("stimulus", {})
        expected_seed = int(str(stimulus.get("seed", f"0x{args.seed:x}")), 0)
        expected_random = int(
            stimulus.get("random_transactions", stimulus.get("random_vectors", args.vector_count))
        )
        if args.seed != expected_seed or args.vector_count != expected_random:
            raise DivDiffError("CLI stimulus differs from locked div contract")
        vectors, directed_count = make_vectors(args.seed, args.vector_count)
        vectors_path = out_dir / "vectors.txt"
        total = write_vector_file(vectors_path, vectors)
        summary["stimulus"] = {"seed": f"0x{args.seed:x}", "random_transactions": args.vector_count}
        summary["vectors"] = {"path": str(vectors_path), "sha256": sha256_file(vectors_path), "directed": directed_count, "random": args.vector_count, "total": total}
        verilator, tools = _toolchain(values, args, out_dir)
        summary["toolchain"] = tools
        blob_payload = _blob(repo_root, values)
        golden_dir = out_dir / "golden"
        golden_dir.mkdir(parents=True, exist_ok=True)
        golden_path = golden_dir / "div.v"
        golden_path.write_bytes(blob_payload)
        summary["golden_artifact"] = {"path": str(golden_path), "sha256": sha256_file(golden_path), "size": golden_path.stat().st_size, "git_ref": f"{values[GOLDEN_COMMIT_KEY]}:{GOLDEN_PATH}"}
        baseline_blob_hash = sha256_bytes(blob_payload)
        result = _compile_and_run(source_payload=blob_payload, source_kind="golden", vectors_path=vectors_path, expected_count=total, directed_count=directed_count, model_dir=golden_dir, verilator=verilator, timeout=args.timeout, values=values, expected_compile_pass=True)
        summary["golden"] = result
        if result.get("status") != "pass":
            raise DivDiffError(str(result.get("error", "golden differential failed")))
        controls: list[dict[str, Any]] = []
        for name in ("result_bit_flip", "complete_timing"):
            control_payload = mutate_source(blob_payload, name)
            control = _compile_and_run(source_payload=control_payload, source_kind=f"negative:{name}", vectors_path=vectors_path, expected_count=total, directed_count=directed_count, model_dir=out_dir / "negative" / name, verilator=verilator, timeout=args.timeout, values=values, expected_compile_pass=False)
            control["expected_failure"] = True
            control["control_source_sha256"] = sha256_bytes(control_payload)
            parsed_control = control.get("simulation", {}).get("parsed", {})
            expected_kind = "complete_window" if name == "result_bit_flip" else "complete_timing"
            mismatch = str(parsed_control.get("first_mismatch") or "")
            control["expected_mismatch_kind"] = expected_kind
            control["control_pass"] = (
                control.get("status") == "fail"
                and control.get("compile", {}).get("returncode") == 0
                and control.get("compile", {}).get("timed_out") is False
                and control.get("simulation", {}).get("returncode") == 1
                and control.get("simulation", {}).get("timed_out") is False
                and parsed_control.get("skip") is None
                and mismatch.startswith(f"DIV_MISMATCH kind={expected_kind} ")
            )
            controls.append(control)
            if not control["control_pass"]:
                raise DivDiffError(f"negative control did not fail as expected: {name}")
        summary["negative_controls"] = controls
        blob_after = _blob(repo_root, values)
        summary["source_stability"] = {
            "golden_blob_before_sha256": baseline_blob_hash,
            "golden_blob_after_sha256": sha256_bytes(blob_after),
            "stable": sha256_bytes(blob_after) == baseline_blob_hash,
            "manifest_before_sha256": manifest_hash_before,
            "manifest_after_sha256": sha256_file(manifest_path),
        }
        if not summary["source_stability"]["stable"] or summary["source_stability"]["manifest_before_sha256"] != summary["source_stability"]["manifest_after_sha256"]:
            raise DivDiffError("locked golden source or manifest changed during run")
        summary["counts"] = {"planned": 3, "executed": 3, "passed": 3, "failed": 0, "skipped": 0}
        summary["status"] = "pass"
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        _persist(out_dir, summary)
        return 0, summary
    except Exception as error:
        summary["status"] = "fail"
        summary["error"] = str(error)
        summary["counts"] = {"planned": 3, "executed": int("golden" in summary) + len(summary.get("negative_controls", [])), "passed": 0, "failed": 1, "skipped": 0}
        _persist(out_dir, summary)
        return 1, summary


def run_candidate(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    out_dir = _fresh_out(args.out_dir)
    summary = _base_summary(args, "candidate")
    try:
        values = parse_manifest(args.manifest.resolve())
        source = args.rtl.expanduser().resolve()
        if source.is_symlink() or not source.is_file():
            raise DivDiffError(f"candidate RTL must be a regular file: {source}")
        payload_before = source.read_bytes()
        vectors, directed_count = make_vectors(args.seed, args.vector_count)
        vectors_path = out_dir / "vectors.txt"
        total = write_vector_file(vectors_path, vectors)
        verilator, tools = _toolchain(values, args, out_dir)
        summary["toolchain"] = tools
        result = _compile_and_run(source_payload=payload_before, source_kind="candidate", vectors_path=vectors_path, expected_count=total, directed_count=directed_count, model_dir=out_dir / "candidate", verilator=verilator, timeout=args.timeout, values=values, expected_compile_pass=True)
        result["candidate_source"] = {"path": str(source), "sha256_before": sha256_bytes(payload_before), "sha256_after": sha256_file(source), "stable": sha256_file(source) == sha256_bytes(payload_before)}
        summary["candidate"] = result
        if not result["candidate_source"]["stable"]:
            raise DivDiffError("candidate source changed during compilation")
        if result.get("status") != "pass":
            raise DivDiffError(str(result.get("error", "candidate differential failed")))
        summary["counts"] = {"planned": 1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0}
        summary["status"] = "pass"
        _persist(out_dir, summary)
        return 0, summary
    except Exception as error:
        summary["error"] = str(error)
        _persist(out_dir, summary)
        return 1, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("golden", "candidate"):
        sub = subparsers.add_parser(command, help=f"run locked {command} divider differential")
        sub.add_argument("--manifest", type=Path, required=True)
        sub.add_argument("--contract", type=Path, default=None)
        sub.add_argument("--out-dir", type=Path, required=True)
        sub.add_argument("--vector-count", type=int, default=DEFAULT_VECTOR_COUNT)
        sub.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
        sub.add_argument("--timeout", type=int, default=900)
        sub.add_argument("--verilator", type=str, default=None)
        if command == "candidate":
            sub.add_argument("--rtl", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    if not sys.flags.isolated:
        print("div_diff.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    if args.vector_count < DEFAULT_VECTOR_COUNT:
        print(f"vector-count must be >={DEFAULT_VECTOR_COUNT}", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("timeout must be positive", file=sys.stderr)
        return 2
    try:
        code, summary = run_golden(args) if args.command == "golden" else run_candidate(args)
    except (DivDiffError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
