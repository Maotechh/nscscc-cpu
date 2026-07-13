#!/usr/bin/env python3
"""Fail-closed contract, static and cycle differential gates for the active I-cache."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

GOLDEN_COMMIT = "a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6"
GOLDEN_PATH = "rtl/icache.v"
GOLDEN_BLOB = "39ec5931316a068b7e5e64169bd257f480db5640"
GOLDEN_SHA256 = "85ba1acc69616dd8b19dae1578fc7e002c83fd435f90227f54068e4fa492675b"
GOLDEN_SIZE = 14887
DEFAULT_CYCLES = 12000


class GateError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(argv: list[str], cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateError(f"cannot execute {' '.join(argv)}: {exc}") from exc


def fresh(path: Path) -> Path:
    path = path.resolve()
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise GateError(f"output directory must be fresh: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def git_blob(repo: Path) -> bytes:
    p = run(["git", "cat-file", "blob", f"{GOLDEN_COMMIT}:{GOLDEN_PATH}"], repo, 30)
    if p.returncode:
        raise GateError(p.stdout.decode(errors="replace"))
    return p.stdout


PORT_RE = re.compile(
    r"^\s*(input|output)\s+(?:wire\s+|reg\s*)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*[,;]?\s*(?://.*)?$",
    re.MULTILINE,
)


def parse_ports(rtl: str) -> dict[str, dict[str, object]]:
    header = re.search(r"\bmodule\s+icache\s*\((.*?)\);", rtl, re.DOTALL)
    if not header:
        raise GateError("icache module header missing")
    result: dict[str, dict[str, object]] = {}
    for match in PORT_RE.finditer(header.group(1)):
        hi, lo = match.group(2), match.group(3)
        result[match.group(4)] = {"direction": match.group(1), "width": 1 if hi is None else int(hi) - int(lo) + 1}
    return result


def locked(repo: Path, contract: Path) -> tuple[dict, bytes]:
    data = json.loads(contract.read_text(encoding="utf-8"))
    if data.get("target") != "icache" or data.get("module") != "icache":
        raise GateError("contract target/module mismatch")
    if data.get("golden") != {"commit_key": "team_golden_candidate", "path": GOLDEN_PATH, "git_blob_sha1": GOLDEN_BLOB, "sha256": GOLDEN_SHA256, "size": GOLDEN_SIZE}:
        raise GateError("contract golden identity mismatch")
    manifest = {}
    for line in (repo / "reference" / "manifest.lock").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, sep, value = line.partition("=")
            if not sep or key.strip() in manifest:
                raise GateError("invalid manifest.lock")
            manifest[key.strip()] = value.strip()
    if manifest.get("team_golden_candidate") != GOLDEN_COMMIT:
        raise GateError("manifest golden commit mismatch")
    golden = git_blob(repo)
    if len(golden) != GOLDEN_SIZE or sha256_bytes(golden) != GOLDEN_SHA256:
        raise GateError("golden bytes mismatch")
    if parse_ports(golden.decode()) != data.get("ports"):
        raise GateError("golden ports differ from contract")
    return data, golden


def command_contract(args: argparse.Namespace) -> dict:
    out = fresh(args.out_dir)
    _, golden = locked(args.repo.resolve(), args.contract.resolve())
    result = {"schema_version": 1, "gate": "icache-contract", "status": "pass", "generated_at": now_iso(), "ports": {"expected": 34, "actual": len(parse_ports(golden.decode())), "matched": True}, "golden_sha256": sha256_bytes(golden)}
    write_json(out / "summary.json", result)
    return result


def command_port(args: argparse.Namespace) -> dict:
    out = fresh(args.out_dir)
    contract, _ = locked(args.repo.resolve(), args.contract.resolve())
    rtl = args.rtl.read_text(encoding="utf-8")
    actual = parse_ports(rtl)
    if actual != contract["ports"]:
        raise GateError(f"port mismatch: expected {len(contract['ports'])}, got {len(actual)}")
    if len(re.findall(r"(?m)^\s*module\s+", rtl)) != 1:
        raise GateError("candidate must contain one module")
    result = {"schema_version": 1, "gate": "icache-port", "status": "pass", "generated_at": now_iso(), "ports": {"expected": 34, "actual": len(actual), "matched": True}, "rtl_sha256": sha256_file(args.rtl), "rtl_size": args.rtl.stat().st_size}
    write_json(out / "summary.json", result)
    return result


def command_lint(args: argparse.Namespace) -> dict:
    out = fresh(args.out_dir)
    locked(args.repo.resolve(), args.contract.resolve())
    verilator = shutil.which("verilator")
    if not verilator:
        raise GateError("verilator unavailable")
    base = [verilator, "--lint-only", "--top-module", "icache", "-Wall", "-Wno-fatal"]
    unwaived = run([*base, str(args.rtl.resolve())], args.repo.resolve())
    unwaived_log = unwaived.stdout.decode(errors="replace")
    (out / "verilator-unwaived.log").write_text(unwaived_log, encoding="utf-8")
    blocks = re.findall(r"(?ms)^%Warning-([A-Z0-9_]+): (.*?)(?=^%Warning-|\Z)", unwaived_log)
    signals = []
    for category, block in blocks:
        match = re.search(r"Signal is not used: '([^']+)'", block)
        if category != "UNUSEDSIGNAL" or not match:
            raise GateError(f"unexpected lint warning category/content: {category}")
        signals.append(match.group(1))
    approved = {"op", "wstrb", "wdata", "wr_rdy"}
    if unwaived.returncode or set(signals) != approved or len(signals) != len(approved):
        raise GateError(f"unwaived warning set changed: {signals}")
    result = run([*base, "-Wno-UNUSEDSIGNAL", str(args.rtl.resolve())], args.repo.resolve())
    log = result.stdout.decode(errors="replace")
    (out / "verilator.log").write_text(log, encoding="utf-8")
    warnings = re.findall(r"(?m)^%Warning-([A-Z0-9_]+):", log)
    if result.returncode or "%Error" in log or warnings:
        raise GateError(f"Verilator lint failed rc={result.returncode}, warnings={warnings}")
    summary = {"schema_version": 1, "gate": "icache-lint", "status": "pass", "generated_at": now_iso(), "warnings": {"approved": 4, "unapproved": 0}, "approved_unused_signals": sorted(approved), "log_sha256": sha256_file(out / "verilator.log"), "unwaived_log_sha256": sha256_file(out / "verilator-unwaived.log")}
    write_json(out / "summary.json", summary)
    return summary


def command_yosys(args: argparse.Namespace) -> dict:
    out = fresh(args.out_dir)
    yosys = shutil.which("yosys")
    if not yosys:
        raise GateError("yosys unavailable")
    result = run([yosys, "-q", "-p", f"read_verilog {args.rtl.resolve()}; hierarchy -check -top icache; proc; opt; check -assert"], args.repo.resolve())
    log = result.stdout.decode(errors="replace")
    (out / "yosys.log").write_text(log, encoding="utf-8")
    if result.returncode or re.search(r"(?i)\b(error|warning):", log):
        raise GateError(f"Yosys check failed rc={result.returncode}")
    summary = {"schema_version": 1, "gate": "icache-yosys", "status": "pass", "generated_at": now_iso(), "log_sha256": sha256_file(out / "yosys.log")}
    write_json(out / "summary.json", summary)
    return summary


DRIVER = r'''
#include "Vicache.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iomanip>

static uint64_t s = 0x158aa8ULL;
static uint32_t rnd() { s ^= s << 13; s ^= s >> 7; s ^= s << 17; return (uint32_t)s; }
static uint32_t mix(uint32_t a, uint32_t b) { return a ^ (b * 0x9e3779b9U) ^ 0xa5a5a5a5U; }

int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv); Vicache d; std::ofstream trace("trace.txt");
  int pending = 0, delay = 0; bool line = false; uint32_t base = 0;
  for (unsigned c = 0; c < CYCLE_COUNT; ++c) {
    uint32_t a = rnd(), b = rnd(), q = rnd();
    d.clk = 0; d.reset = (c < 5 || c == 4096 || c == 9000);
    d.valid = ((a >> 0) & 7) != 0; d.op = (a >> 3) & 1;
    d.index = (a >> 4) & 0xff; d.tag = (b >> 0) & 0xfffff; d.offset = (b >> 20) & 0xf;
    d.wstrb = (q >> 0) & 0xf; d.wdata = q ^ 0x12345678U; d.uncache_en = ((a >> 8) & 31) == 0;
    d.icacop_op_en = ((a >> 13) & 127) == 0; d.cacop_op_mode = (a >> 20) & 3;
    d.cacop_op_addr_index = (b >> 8) & 0xff; d.cacop_op_addr_tag = (b >> 16) & 0xfffff; d.cacop_op_addr_offset = (q >> 4) & 0xf;
    d.tlb_excp_cancel_req = ((q >> 8) & 127) == 0; d.rd_rdy = ((a >> 24) & 3) != 0;
    d.ret_valid = pending > 0 && delay == 0 && !d.reset; d.ret_last = d.ret_valid && pending == 1;
    d.ret_data = mix(base, (uint32_t)(4 - pending)); d.wr_rdy = (b >> 31) & 1;
    d.clk = 0; d.eval(); d.clk = 1; d.eval();
    if (d.reset) { pending = 0; delay = 0; }
    if (d.ret_valid) { pending--; if (pending == 0) delay = 0; }
    if (delay > 0) delay--;
    if (d.rd_req && d.rd_rdy && !d.reset) { line = d.rd_type == 4; pending = line ? 4 : 1; delay = 1; base = d.rd_addr; }
    trace << std::hex << c << ' ' << (unsigned)d.addr_ok << ' ' << (unsigned)d.data_ok << ' ' << d.rdata << ' '
      << (unsigned)d.icache_unbusy << ' ' << (unsigned)d.rd_req << ' ' << (unsigned)d.rd_type << ' ' << d.rd_addr << ' '
      << (unsigned)d.cache_miss << ' ' << (unsigned)d.wr_req << ' ' << (unsigned)d.wr_type << ' ' << d.wr_addr << ' '
      << (unsigned)d.wr_wstrb << ' ' << d.wr_data[0] << ' ' << d.wr_data[1] << ' ' << d.wr_data[2] << ' ' << d.wr_data[3] << '\n';
  }
  d.final(); return 0;
}
'''


def build_trace(args: argparse.Namespace, source: bytes, build_dir: Path, golden: bool, cycles: int) -> list[str]:
    build_dir.mkdir(parents=True)
    rtl = build_dir / "icache.v"; rtl.write_bytes(source)
    driver = build_dir / "driver.cpp"; driver.write_text(DRIVER.replace("CYCLE_COUNT", str(cycles)), encoding="utf-8")
    sources = [str(rtl)]
    defines: list[str] = []
    if golden:
        dcache = args.repo.resolve() / ".gate-cache" / "dcache-simu.v"
        dcache.parent.mkdir(parents=True, exist_ok=True)
        dcache_result = run(["git", "show", f"{GOLDEN_COMMIT}:rtl/dcache.v"], args.repo, 30)
        if dcache_result.returncode:
            raise GateError("cannot read locked dcache SRAM models")
        dcache.write_bytes(dcache_result.stdout)
        tools_rtl = args.repo.resolve() / ".gate-cache" / "tools.v"
        tools_result = run(["git", "show", f"{GOLDEN_COMMIT}:rtl/tools.v"], args.repo, 30)
        if tools_result.returncode:
            raise GateError("cannot read locked helper modules")
        tools_rtl.write_bytes(tools_result.stdout)
        sources.extend((str(dcache), str(tools_rtl))); defines.append("-DSIMU")
    verilator = shutil.which("verilator")
    obj = build_dir / "obj"
    cmd = [verilator, "--cc", "--exe", "--build", "--top-module", "icache", "-Wall", "-Wno-fatal", "--Mdir", str(obj), *defines, *sources, str(driver), "-CFLAGS", "-std=c++17", "-o", "sim"]
    compiled = run(cmd, build_dir, timeout=240)
    log = compiled.stdout.decode(errors="replace"); (build_dir / "compile.log").write_text(log, encoding="utf-8")
    if compiled.returncode or "%Error" in log:
        raise GateError(f"Verilator build failed rc={compiled.returncode}: {build_dir}")
    executed = run([str(obj / "sim")], build_dir, timeout=90)
    if executed.returncode:
        raise GateError(f"simulation failed rc={executed.returncode}")
    trace = (build_dir / "trace.txt").read_text(encoding="utf-8").splitlines()
    if len(trace) != cycles:
        raise GateError(f"trace length {len(trace)} != {cycles}")
    return trace


def first_mismatch(left: list[str], right: list[str]) -> dict | None:
    for cycle, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return {"cycle": cycle, "golden": a, "candidate": b}
    return None if len(left) == len(right) else {"cycle": min(len(left), len(right))}


def command_diff(args: argparse.Namespace) -> dict:
    out = fresh(args.out_dir)
    _, golden = locked(args.repo.resolve(), args.contract.resolve())
    golden_trace = build_trace(args, golden, out / "golden", True, args.cycles)
    candidate_trace = build_trace(args, args.rtl.read_bytes(), out / "candidate", False, args.cycles)
    mismatch = first_mismatch(golden_trace, candidate_trace)
    if mismatch:
        raise GateError(f"candidate first mismatch: {mismatch}")
    # A transaction-level negative control must be observable on the first actual miss.
    anchor = b"assign rd_req  = main_state_is_replace &&"
    if golden.count(anchor) != 1:
        raise GateError("negative-control anchor changed")
    mutated = golden.replace(anchor, anchor + b" 1'b0 &&", 1)
    negative = build_trace(args, mutated, out / "negative", True, min(args.cycles, 4096))
    control = first_mismatch(golden_trace[: len(negative)], negative)
    if control is None:
        raise GateError("negative control was not detected")
    result = {"schema_version": 1, "gate": "icache-cycle-diff", "status": "pass", "generated_at": now_iso(), "cycles": args.cycles, "mismatches": 0, "negative_control": control, "counts": {"planned": args.cycles + len(negative), "executed": args.cycles + len(negative), "passed": args.cycles + len(negative), "failed": 0, "skipped": 0}}
    write_json(out / "summary.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    if not sys.flags.isolated:
        print("icache_gate.py requires python -I", file=sys.stderr); return 2
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="command", required=True)
    for name in ("contract", "port-check", "lint", "yosys-check", "diff"):
        q = sub.add_parser(name); q.add_argument("--repo", type=Path, default=Path(".")); q.add_argument("--contract", type=Path, required=True); q.add_argument("--out-dir", type=Path, required=True)
        if name != "contract": q.add_argument("--rtl", type=Path, required=True)
        if name == "diff": q.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    args = p.parse_args(argv)
    try:
        result = {"contract": command_contract, "port-check": command_port, "lint": command_lint, "yosys-check": command_yosys, "diff": command_diff}[args.command](args)
    except (GateError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
