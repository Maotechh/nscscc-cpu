#!/usr/bin/env python3
"""Fail-closed contract, RTL static, and cycle differential gates for axi_bridge."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any


GOLDEN_COMMIT = "a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6"
GOLDEN_PATH = "rtl/axi_bridge.v"
GOLDEN_BLOB = "4219790c25c653da1a061c5f4c674e062201b8e9"
GOLDEN_SHA256 = "07c30c8e5e99373ecb988b2a5cc03e4e8cb7b6e22af26b1b37171a808b144f9e"
GOLDEN_SIZE = 10106
DEFAULT_CYCLES = 8192
DEFAULT_SEED = 0x158AA8


class GateError(RuntimeError):
    pass


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
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = OrderedDict()
    for key, value in pairs:
        if key in result:
            raise GateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise GateError(f"JSON input must be a regular file: {path}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)


def run(
    argv: list[str], cwd: Path, timeout: int = 120, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GateError(f"cannot execute {' '.join(argv)}: {error}") from error
    return result


def git(repo: Path, *args: str) -> bytes:
    result = run(["git", *args], repo, timeout=30)
    if result.returncode != 0:
        raise GateError(result.stdout.decode("utf-8", errors="replace").strip())
    return result.stdout


def prepare_out(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_symlink():
        raise GateError(f"output directory must not be a symlink: {path}")
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise GateError(f"output directory must be fresh: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def locked_inputs(repo: Path, contract_path: Path) -> tuple[dict[str, Any], bytes]:
    contract = load_json(contract_path)
    if contract.get("target") != "axi_bridge" or contract.get("module") != "axi_bridge":
        raise GateError("contract target/module must both be axi_bridge")
    ports = contract.get("ports")
    if not isinstance(ports, dict) or len(ports) != 65:
        raise GateError("contract must contain exactly 65 ports")
    if contract.get("golden") != {
        "commit_key": "team_golden_candidate",
        "path": GOLDEN_PATH,
        "git_blob_sha1": GOLDEN_BLOB,
        "sha256": GOLDEN_SHA256,
        "size": GOLDEN_SIZE,
    }:
        raise GateError("golden identity in contract is not locked")
    manifest = {}
    for raw in (repo / "reference" / "manifest.lock").read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.lstrip().startswith("#"):
            key, separator, value = raw.partition("=")
            if not separator or key in manifest:
                raise GateError("invalid or duplicate manifest entry")
            manifest[key.strip()] = value.strip()
    if manifest.get("team_golden_candidate") != GOLDEN_COMMIT:
        raise GateError("manifest golden commit mismatch")
    blob_ref = f"{GOLDEN_COMMIT}:{GOLDEN_PATH}"
    if git(repo, "rev-parse", blob_ref).decode().strip() != GOLDEN_BLOB:
        raise GateError("golden Git blob mismatch")
    payload = git(repo, "cat-file", "blob", blob_ref)
    if len(payload) != GOLDEN_SIZE or sha256_bytes(payload) != GOLDEN_SHA256:
        raise GateError("golden bytes do not match locked size/SHA256")
    return contract, payload


PORT_RE = re.compile(
    r"^\s*(input|output)\s+(?:wire\s+|reg\s*)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*[,;]?\s*$",
    re.MULTILINE,
)


def parse_ports(rtl: str) -> dict[str, dict[str, Any]]:
    header_match = re.search(r"\bmodule\s+axi_bridge\s*\((.*?)\);", rtl, re.DOTALL)
    if not header_match:
        raise GateError("cannot find axi_bridge module header")
    result: dict[str, dict[str, Any]] = {}
    for match in PORT_RE.finditer(header_match.group(1)):
        upper, lower = match.group(2), match.group(3)
        width = 1 if upper is None else int(upper) - int(lower) + 1
        name = match.group(4)
        if name in result:
            raise GateError(f"duplicate RTL port: {name}")
        result[name] = {"direction": match.group(1), "width": width}
    return result


def command_contract(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    out = prepare_out(args.out_dir)
    contract, golden = locked_inputs(repo, args.contract.resolve())
    actual = parse_ports(golden.decode("utf-8"))
    if actual != contract["ports"]:
        raise GateError("golden port declarations do not match contract")
    summary = {
        "schema_version": 1,
        "gate": "axi-bridge-contract",
        "status": "pass",
        "generated_at": now_iso(),
        "golden": {
            "commit": GOLDEN_COMMIT,
            "path": GOLDEN_PATH,
            "git_blob_sha1": GOLDEN_BLOB,
            "sha256": GOLDEN_SHA256,
            "size": GOLDEN_SIZE,
        },
        "ports": {"expected": 65, "actual": len(actual), "matched": True},
        "contract_sha256": sha256_file(args.contract.resolve()),
    }
    write_json(out / "summary.json", summary)
    return summary


def command_port(args: argparse.Namespace) -> dict[str, Any]:
    out = prepare_out(args.out_dir)
    contract, _ = locked_inputs(args.repo.resolve(), args.contract.resolve())
    if args.rtl.is_symlink() or not args.rtl.is_file():
        raise GateError(f"candidate RTL must be a regular file: {args.rtl}")
    rtl = args.rtl.read_text(encoding="utf-8")
    actual = parse_ports(rtl)
    if actual != contract["ports"]:
        missing = sorted(set(contract["ports"]) - set(actual))
        extra = sorted(set(actual) - set(contract["ports"]))
        changed = sorted(
            name
            for name in set(actual) & set(contract["ports"])
            if actual[name] != contract["ports"][name]
        )
        raise GateError(f"port mismatch: missing={missing}, extra={extra}, changed={changed}")
    module_count = len(re.findall(r"(?m)^\s*module\s+", rtl))
    if module_count != 1:
        raise GateError(f"candidate must contain exactly one module, got {module_count}")
    summary = {
        "schema_version": 1,
        "gate": "axi-bridge-port",
        "status": "pass",
        "generated_at": now_iso(),
        "ports": {"expected": 65, "actual": 65, "matched": True},
        "module": "axi_bridge",
        "rtl_sha256": sha256_file(args.rtl),
        "rtl_size": args.rtl.stat().st_size,
    }
    write_json(out / "summary.json", summary)
    return summary


COMPAT_WARNING_OPTIONS = ["-Wno-UNUSEDSIGNAL"]


def command_lint(args: argparse.Namespace) -> dict[str, Any]:
    out = prepare_out(args.out_dir)
    locked_inputs(args.repo.resolve(), args.contract.resolve())
    verilator = shutil.which("verilator")
    if not verilator:
        raise GateError("verilator is unavailable")
    argv = [
        verilator,
        "--lint-only",
        "--top-module",
        "axi_bridge",
        "-Wall",
        "-Wno-fatal",
        *COMPAT_WARNING_OPTIONS,
        str(args.rtl.resolve()),
    ]
    result = run(argv, args.repo.resolve())
    log = result.stdout.decode("utf-8", errors="replace")
    (out / "verilator.log").write_text(log, encoding="utf-8", newline="\n")
    warnings = re.findall(r"(?m)^%Warning-([A-Z0-9_]+):", log)
    if result.returncode != 0 or warnings or "%Error" in log:
        raise GateError(f"Verilator lint failed rc={result.returncode}, warnings={warnings}")
    summary = {
        "schema_version": 1,
        "gate": "axi-bridge-lint",
        "status": "pass",
        "generated_at": now_iso(),
        "returncode": result.returncode,
        "warnings": 0,
        "compatibility_waivers": [
            {
                "rule": "UNUSEDSIGNAL",
                "scope": "exact legacy dead ports and rid[3:1]",
                "reason": "ports are required by the locked 65-port compatibility boundary",
            }
        ],
        "log_sha256": sha256_file(out / "verilator.log"),
    }
    write_json(out / "summary.json", summary)
    return summary


def command_yosys(args: argparse.Namespace) -> dict[str, Any]:
    out = prepare_out(args.out_dir)
    locked_inputs(args.repo.resolve(), args.contract.resolve())
    yosys = shutil.which("yosys")
    if not yosys:
        raise GateError("yosys is unavailable")
    script = (
        f"read_verilog {args.rtl.resolve()}; hierarchy -check -top axi_bridge; "
        "proc; opt; check -assert"
    )
    result = run([yosys, "-q", "-p", script], args.repo.resolve())
    log = result.stdout.decode("utf-8", errors="replace")
    (out / "yosys.log").write_text(log, encoding="utf-8", newline="\n")
    if result.returncode != 0 or re.search(r"(?i)\b(error|warning):", log):
        raise GateError(f"Yosys check failed rc={result.returncode}")
    summary = {
        "schema_version": 1,
        "gate": "axi-bridge-yosys",
        "status": "pass",
        "generated_at": now_iso(),
        "returncode": result.returncode,
        "log_sha256": sha256_file(out / "yosys.log"),
    }
    write_json(out / "summary.json", summary)
    return summary


DRIVER = r'''
#include "Vaxi_bridge.h"
#include "verilated.h"
#include <cstdint>
#include <iomanip>
#include <iostream>

static uint64_t state = SEED_VALUE;
static uint32_t next32() {
  state ^= state << 13; state ^= state >> 7; state ^= state << 17;
  return static_cast<uint32_t>(state);
}

int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  Vaxi_bridge d;
  d.clk = 0; d.reset = 0;
  for (unsigned cycle = 0; cycle < CYCLE_COUNT; ++cycle) {
    uint32_t a = next32(), b = next32(), c = next32(), e = next32();
    d.reset = cycle < 3 || cycle == 4096;
    d.arready = (a >> 0) & 1; d.awready = (a >> 1) & 1;
    d.wready = (a >> 2) & 1; d.bvalid = (a >> 3) & 1;
    d.rvalid = (a >> 4) & 1; d.rlast = (a >> 5) & 1;
    d.rid = (a >> 6) & 15; d.rdata = b; d.rresp = (a >> 10) & 3;
    d.bid = (a >> 12) & 15; d.bresp = (a >> 16) & 3;
    d.inst_rd_req = ((a >> 18) & 15) == 0;
    d.inst_rd_type = (a >> 22) & 7; d.inst_rd_addr = c;
    d.data_rd_req = ((a >> 25) & 7) == 0;
    d.data_rd_type = (a >> 28) & 7; d.data_rd_addr = e;
    d.data_wr_req = ((b >> 3) & 15) == 0;
    d.data_wr_type = (b >> 7) & 7; d.data_wr_addr = c ^ 0x5a5a5a5aU;
    d.data_wr_wstrb = (b >> 11) & 15;
    d.data_wr_data[0] = next32(); d.data_wr_data[1] = next32();
    d.data_wr_data[2] = next32(); d.data_wr_data[3] = next32();
    d.inst_wr_req = (b >> 15) & 1; d.inst_wr_type = (b >> 16) & 7;
    d.inst_wr_addr = next32(); d.inst_wr_wstrb = (b >> 19) & 15;
    d.inst_wr_data[0] = next32(); d.inst_wr_data[1] = next32();
    d.inst_wr_data[2] = next32(); d.inst_wr_data[3] = next32();

    if (cycle == 3) { d.data_rd_req = 1; d.inst_rd_req = 1; d.data_rd_type = 4; d.arready = 0; }
    if (cycle == 4) { d.data_rd_req = 0; d.inst_rd_req = 0; d.arready = 0; }
    if (cycle == 5) d.arready = 1;
    if (cycle == 8) { d.data_wr_req = 1; d.data_wr_type = 2; d.awready = 0; }
    if (cycle == 9) d.data_wr_req = 0;
    if (cycle == 10) d.awready = 1;
    if (cycle == 11) d.wready = 0;
    if (cycle == 12) d.wready = 1;
    if (cycle == 14) { d.bvalid = 1; d.inst_rd_req = 1; }
    if (cycle == 20) { d.data_wr_req = 1; d.data_wr_type = 4; d.awready = 0; }
    if (cycle == 21) { d.data_wr_req = 0; d.awready = 1; }
    if (cycle >= 22 && cycle <= 27) d.wready = cycle != 23;
    if (cycle == 30) d.bvalid = 1;

    d.clk = 0; d.eval();
    d.clk = 1; d.eval();
    std::cout << cycle << ' ' << (d.arvalid ? unsigned(d.arid) : 0) << ' '
      << (d.arvalid ? d.araddr : 0) << ' ' << (d.arvalid ? unsigned(d.arlen) : 0)
      << ' ' << (d.arvalid ? unsigned(d.arsize) : 0) << ' ' << unsigned(d.arburst)
      << ' ' << unsigned(d.arlock) << ' ' << unsigned(d.arcache) << ' '
      << unsigned(d.arprot) << ' ' << unsigned(d.arvalid) << ' ' << unsigned(d.rready)
      << ' ' << unsigned(d.awid) << ' ' << (d.awvalid ? d.awaddr : 0) << ' '
      << (d.awvalid ? unsigned(d.awlen) : 0) << ' '
      << (d.awvalid ? unsigned(d.awsize) : 0) << ' ' << unsigned(d.awburst) << ' '
      << unsigned(d.awlock) << ' ' << unsigned(d.awcache) << ' ' << unsigned(d.awprot)
      << ' ' << unsigned(d.awvalid) << ' ' << unsigned(d.wid) << ' '
      << (d.wvalid ? d.wdata : 0) << ' ' << (d.wvalid ? unsigned(d.wstrb) : 0)
      << ' ' << (d.wvalid ? unsigned(d.wlast) : 0) << ' '
      << unsigned(d.wvalid) << ' ' << unsigned(d.bready) << ' '
      << unsigned(d.inst_rd_rdy) << ' ' << unsigned(d.inst_ret_valid) << ' '
      << unsigned(d.inst_ret_last) << ' ' << d.inst_ret_data << ' '
      << unsigned(d.inst_wr_rdy) << ' ' << unsigned(d.data_rd_rdy) << ' '
      << unsigned(d.data_ret_valid) << ' ' << unsigned(d.data_ret_last) << ' '
      << d.data_ret_data << ' ' << unsigned(d.data_wr_rdy) << ' '
      << unsigned(d.write_buffer_empty) << '\n';
  }
  d.final();
  return 0;
}
'''


def build_and_trace(
    rtl: bytes, build_dir: Path, verilator: str, cycles: int, seed: int
) -> tuple[list[str], dict[str, Any]]:
    build_dir.mkdir(parents=True)
    rtl_path = build_dir / "axi_bridge.v"
    rtl_path.write_bytes(rtl)
    driver = DRIVER.replace("CYCLE_COUNT", str(cycles)).replace("SEED_VALUE", str(seed))
    (build_dir / "driver.cpp").write_text(driver, encoding="utf-8", newline="\n")
    obj = build_dir / "obj"
    argv = [
        verilator,
        "--cc",
        "--exe",
        "--build",
        "--top-module",
        "axi_bridge",
        "-Wall",
        "-Wno-fatal",
        "-Wno-UNUSEDSIGNAL",
        "-Wno-UNUSEDPARAM",
        "--Mdir",
        str(obj),
        str(rtl_path),
        str(build_dir / "driver.cpp"),
        "-CFLAGS",
        "-std=c++17",
        "-o",
        "sim",
    ]
    started = time.monotonic()
    compiled = run(argv, build_dir, timeout=180)
    compile_log = compiled.stdout.decode("utf-8", errors="replace")
    (build_dir / "compile.log").write_text(compile_log, encoding="utf-8", newline="\n")
    unexpected = re.findall(r"(?m)^%Warning-([A-Z0-9_]+):", compile_log)
    if compiled.returncode != 0 or "%Error" in compile_log or unexpected:
        raise GateError(
            f"Verilator build failed rc={compiled.returncode}, warnings={unexpected}: {build_dir}"
        )
    executed = run([str(obj / "sim")], build_dir, timeout=60)
    if executed.returncode != 0:
        raise GateError(f"simulation failed rc={executed.returncode}: {build_dir}")
    trace_bytes = executed.stdout
    (build_dir / "trace.txt").write_bytes(trace_bytes)
    lines = trace_bytes.decode("ascii").splitlines()
    if len(lines) != cycles:
        raise GateError(f"trace length mismatch: expected {cycles}, got {len(lines)}")
    return lines, {
        "rtl_sha256": sha256_bytes(rtl),
        "compile_log_sha256": sha256_file(build_dir / "compile.log"),
        "trace_sha256": sha256_bytes(trace_bytes),
        "cycles": len(lines),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


MUTATIONS = [
    (b"if (data_rd_req) begin", b"if (1'b0 && data_rd_req) begin", "disable_data_read"),
    (b"data_rd_cache_line ? 8'b11", b"data_rd_cache_line ? 8'b10", "wrong_line_len"),
    (b"if (awready) begin", b"if (1'b0 && awready) begin", "disable_aw_handshake"),
]


def first_mismatch(left: list[str], right: list[str]) -> dict[str, Any] | None:
    for index, (expected, actual) in enumerate(zip(left, right)):
        if expected != actual:
            return {"cycle": index, "golden": expected, "candidate": actual}
    if len(left) != len(right):
        return {"cycle": min(len(left), len(right)), "golden": None, "candidate": None}
    return None


def command_diff(args: argparse.Namespace) -> dict[str, Any]:
    out = prepare_out(args.out_dir)
    _, golden = locked_inputs(args.repo.resolve(), args.contract.resolve())
    candidate = args.rtl.read_bytes()
    verilator = shutil.which("verilator")
    if not verilator:
        raise GateError("verilator is unavailable")
    golden_trace, golden_meta = build_and_trace(
        golden, out / "golden", verilator, args.cycles, args.seed
    )
    candidate_trace, candidate_meta = build_and_trace(
        candidate, out / "candidate", verilator, args.cycles, args.seed
    )
    mismatch = first_mismatch(golden_trace, candidate_trace)
    controls = []
    for old, new, name in MUTATIONS:
        if golden.count(old) != 1:
            raise GateError(f"negative control anchor is not unique: {name}")
        mutated = golden.replace(old, new, 1)
        trace, meta = build_and_trace(
            mutated, out / f"negative-{name}", verilator, args.cycles, args.seed
        )
        detected = first_mismatch(golden_trace, trace)
        if detected is None:
            raise GateError(f"negative control was not detected: {name}")
        controls.append({"name": name, "detected": True, "first_mismatch": detected, **meta})
    if mismatch is not None:
        raise GateError(f"candidate first mismatch: {mismatch}")
    summary = {
        "schema_version": 1,
        "gate": "axi-bridge-cycle-diff",
        "status": "pass",
        "generated_at": now_iso(),
        "seed": hex(args.seed),
        "cycles": args.cycles,
        "mismatches": 0,
        "golden": golden_meta,
        "candidate": candidate_meta,
        "negative_controls": controls,
        "counts": {"planned": args.cycles + 3, "executed": args.cycles + 3, "passed": args.cycles + 3, "failed": 0, "skipped": 0},
    }
    write_json(out / "summary.json", summary)
    return summary


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("contract", "port-check", "lint", "yosys-check", "diff"):
        item = sub.add_parser(name)
        item.add_argument("--repo", type=Path, default=Path("."))
        item.add_argument("--contract", type=Path, required=True)
        item.add_argument("--out-dir", type=Path, required=True)
        if name != "contract":
            item.add_argument("--rtl", type=Path, required=True)
        if name == "diff":
            item.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
            item.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    return result


def main(argv: list[str] | None = None) -> int:
    if not sys.flags.isolated:
        print("axi_bridge_gate.py requires isolated Python (-I)", file=sys.stderr)
        return 2
    args = parser().parse_args(argv)
    dispatch = {
        "contract": command_contract,
        "port-check": command_port,
        "lint": command_lint,
        "yosys-check": command_yosys,
        "diff": command_diff,
    }
    try:
        summary = dispatch[args.command](args)
    except (GateError, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
