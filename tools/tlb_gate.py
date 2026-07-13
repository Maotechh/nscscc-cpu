#!/usr/bin/env python3
"""Locked golden/candidate cycle differential gate for openLA500 tlb_entry."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any


GOLDEN_COMMIT = "a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6"
GOLDEN_PATH = "rtl/tlb_entry.v"
GOLDEN_BLOB = "0dad79a3947675efc2115a10d6dfcbdbb4038a5a"
GOLDEN_SHA256 = "a3e3508a0c755375336ba6db392f9038e1d793042fc21b7cd088fde9febcba1f"
GOLDEN_SIZE = 9268
TOOLS_PATH = "rtl/tools.v"
TOOLS_BLOB = "e4599aa111da7a9a84d417bd4f5b4a820c9fbc95"
TOOLS_SIZE = 4758
DEFAULT_CYCLES = 2048
DEFAULT_SEED = 0x158AA8


class GateError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def run(argv: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": argv,
            "returncode": result.returncode,
            "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout": result.stdout.decode("utf-8", errors="replace"),
        }
    except subprocess.TimeoutExpired as error:
        output = error.stdout.decode("utf-8", errors="replace") if error.stdout else ""
        return {
            "argv": argv,
            "returncode": 124,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout": output,
        }
    except OSError as error:
        return {
            "argv": argv,
            "returncode": 125,
            "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout": str(error),
        }


def resolve_git_dir(repo: Path) -> Path:
    dot_git = repo / ".git"
    if dot_git.is_dir():
        return dot_git.resolve()
    if not dot_git.is_file():
        raise GateError(f"Git metadata is missing: {dot_git}")
    line = dot_git.read_text(encoding="utf-8").strip()
    if not line.startswith("gitdir:"):
        raise GateError(f"invalid Git worktree pointer: {dot_git}")
    raw = line.removeprefix("gitdir:").strip()
    candidates: list[Path] = []
    windows_drive = re.fullmatch(r"([A-Za-z]):[\\/](.+)", raw)
    if windows_drive and os.name != "nt":
        drive, suffix = windows_drive.groups()
        candidates.append(Path(f"/mnt/{drive.lower()}/{suffix.replace(chr(92), '/') }"))
    candidates.append(Path(raw) if Path(raw).is_absolute() else repo / raw)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    raise GateError(f"Git worktree metadata target is missing: {raw}")


def git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        [
            "git",
            f"--git-dir={resolve_git_dir(repo)}",
            f"--work-tree={repo.resolve()}",
            *args,
        ],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise GateError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def locked_sources(repo: Path) -> tuple[bytes, bytes]:
    manifest = {}
    for raw in (repo / "reference" / "manifest.lock").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key in manifest:
            raise GateError("invalid or duplicate manifest entry")
        manifest[key] = value
    if manifest.get("team_golden_candidate") != GOLDEN_COMMIT:
        raise GateError("manifest golden commit mismatch")

    identities = (
        (GOLDEN_PATH, GOLDEN_BLOB, GOLDEN_SIZE),
        (TOOLS_PATH, TOOLS_BLOB, TOOLS_SIZE),
    )
    payloads = []
    for path, blob, size in identities:
        reference = f"{GOLDEN_COMMIT}:{path}"
        actual_blob = git_bytes(repo, "rev-parse", reference).decode().strip()
        payload = git_bytes(repo, "cat-file", "blob", reference)
        if actual_blob != blob or len(payload) != size:
            raise GateError(f"locked source identity mismatch: {path}")
        payloads.append(payload)
    if sha256_bytes(payloads[0]) != GOLDEN_SHA256:
        raise GateError("golden tlb_entry SHA256 mismatch")
    return payloads[0], payloads[1]


def rename_module(payload: bytes, replacement: bytes) -> bytes:
    transformed, count = re.subn(
        rb"(?m)^module\s+tlb_entry\b", b"module " + replacement, payload, count=1
    )
    if count != 1:
        raise GateError(f"expected exactly one tlb_entry declaration, found {count}")
    return transformed


INPUTS = [
    "clk", "s0_fetch", "s0_vppn", "s0_odd_page", "s0_asid",
    "s1_fetch", "s1_vppn", "s1_odd_page", "s1_asid", "we", "w_index",
    "w_vppn", "w_asid", "w_g", "w_ps", "w_e", "w_v0", "w_d0", "w_mat0",
    "w_plv0", "w_ppn0", "w_v1", "w_d1", "w_mat1", "w_plv1", "w_ppn1",
    "r_index", "inv_en", "inv_op", "inv_asid", "inv_vpn",
]

OUTPUTS = [
    "s0_found", "s0_index", "s0_ps", "s0_ppn", "s0_v", "s0_d", "s0_mat",
    "s0_plv", "s1_found", "s1_index", "s1_ps", "s1_ppn", "s1_v", "s1_d",
    "s1_mat", "s1_plv", "r_vppn", "r_asid", "r_g", "r_ps", "r_e", "r_v0",
    "r_d0", "r_mat0", "r_plv0", "r_ppn0", "r_v1", "r_d1", "r_mat1",
    "r_plv1", "r_ppn1",
]

WIDTHS = {
    "s0_vppn": 19, "s0_asid": 10, "s1_vppn": 19, "s1_asid": 10,
    "w_index": 5, "w_vppn": 19, "w_asid": 10, "w_ps": 6, "w_mat0": 2,
    "w_plv0": 2, "w_ppn0": 20, "w_mat1": 2, "w_plv1": 2, "w_ppn1": 20,
    "r_index": 5, "inv_op": 5, "inv_asid": 10, "inv_vpn": 19,
    "s0_index": 5, "s0_ps": 6, "s0_ppn": 20, "s0_mat": 2, "s0_plv": 2,
    "s1_index": 5, "s1_ps": 6, "s1_ppn": 20, "s1_mat": 2, "s1_plv": 2,
    "r_vppn": 19, "r_asid": 10, "r_ps": 6, "r_mat0": 2, "r_plv0": 2,
    "r_ppn0": 20, "r_mat1": 2, "r_plv1": 2, "r_ppn1": 20,
}


def declaration(kind: str, name: str, width: int | None = None) -> str:
    width = WIDTHS.get(name, 1) if width is None else width
    dimension = "" if width == 1 else f" [{width - 1}:0]"
    return f"  {kind}{dimension} {name};"


def testbench(cycles: int, seed: int) -> str:
    lines = ["`timescale 1ns/1ps", "module tb;"]
    lines.extend(declaration("reg", name) for name in INPUTS)
    for prefix in ("g", "c"):
        lines.extend(
            declaration("wire", f"{prefix}_{name}", WIDTHS.get(name, 1)) for name in OUTPUTS
        )
    common = [f".{name}({name})" for name in INPUTS]
    for module, prefix in (("tlb_entry_golden", "g"), ("tlb_entry_candidate", "c")):
        connections = common + [f".{name}({prefix}_{name})" for name in OUTPUTS]
        lines.append(f"  {module} dut_{prefix} (" + ",".join(connections) + ");")
    golden_vector = ",".join(f"g_{name}" for name in OUTPUTS)
    candidate_vector = ",".join(f"c_{name}" for name in OUTPUTS)
    lines.extend(
        [
            "  integer cycle; integer i; integer checks; reg [31:0] lfsr;",
            "  task defaults; begin",
            "    s0_fetch=0; s0_vppn=0; s0_odd_page=0; s0_asid=0;",
            "    s1_fetch=0; s1_vppn=0; s1_odd_page=0; s1_asid=0;",
            "    we=0; w_index=0; w_vppn=0; w_asid=0; w_g=0; w_ps=0; w_e=0;",
            "    w_v0=0; w_d0=0; w_mat0=0; w_plv0=0; w_ppn0=0;",
            "    w_v1=0; w_d1=0; w_mat1=0; w_plv1=0; w_ppn1=0;",
            "    r_index=0; inv_en=0; inv_op=0; inv_asid=0; inv_vpn=0;",
            "  end endtask",
            "  task compare; begin",
            f"    if ({{{golden_vector}}} !== {{{candidate_vector}}}) begin",
            '      $display("TLB_MISMATCH cycle=%0d checks=%0d s0=%h/%h s1=%h/%h r=%0d", cycle, checks, g_s0_index, c_s0_index, g_s1_index, c_s1_index, r_index);',
            f"      $display(\"golden=%h candidate=%h\", {{{golden_vector}}}, {{{candidate_vector}}});",
            "      $fatal(1);",
            "    end",
            "    checks=checks+1;",
            "  end endtask",
            "  task tick(input do_check); begin",
            "    #2; clk=1; #2; if (do_check) compare; #2; clk=0; #2; if (do_check) compare; cycle=cycle+1;",
            "  end endtask",
            "  task write_entry(input [4:0] idx, input [18:0] vpn, input [9:0] aid, input glob, input [5:0] ps, input ena); begin",
            "    we=1; w_index=idx; w_vppn=vpn; w_asid=aid; w_g=glob; w_ps=ps; w_e=ena;",
            "    w_v0=idx[0]; w_d0=idx[1]; w_mat0=idx[3:2]; w_plv0=idx[1:0]; w_ppn0=20'h10000+{{15{1'b0}},idx};",
            "    w_v1=~idx[0]; w_d1=~idx[1]; w_mat1=~idx[3:2]; w_plv1=~idx[1:0]; w_ppn1=20'h20000+{{15{1'b0}},idx};",
            "    tick(1); we=0;",
            "  end endtask",
            "  task fetch_pair(input [18:0] vpn0, input odd0, input [9:0] aid0, input [18:0] vpn1, input odd1, input [9:0] aid1); begin",
            "    s0_fetch=1; s0_vppn=vpn0; s0_odd_page=odd0; s0_asid=aid0;",
            "    s1_fetch=1; s1_vppn=vpn1; s1_odd_page=odd1; s1_asid=aid1;",
            "    tick(1); s0_fetch=0; s1_fetch=0; #1; compare;",
            "  end endtask",
            "  task invalidate(input [4:0] op, input [9:0] aid, input [18:0] vpn); begin",
            "    inv_en=1; inv_op=op; inv_asid=aid; inv_vpn=vpn; tick(1); inv_en=0; #1; compare;",
            "  end endtask",
            "  task expect_read_enabled(input [4:0] idx, input expected); begin",
            "    r_index=idx; #1; compare; if (g_r_e !== expected) begin",
            '      $display("TLB_GOLDEN_EXPECTATION_FAILED cycle=%0d index=%0d expected_e=%0d actual=%0d", cycle, idx, expected, g_r_e); $fatal(1);',
            "    end",
            "  end endtask",
            "  initial begin",
            f"    clk=0; cycle=0; checks=0; lfsr=32'h{seed & 0xFFFFFFFF:08x}; defaults;",
            "    // Initialize every entry because the locked TLB intentionally has no reset.",
            "    for (i=0; i<32; i=i+1) begin",
            "      write_entry(i[4:0], {14'h0800,i[4:0]}, i[9:0], 1'b0, 6'd12, 1'b1);",
            "    end",
            "    fetch_pair(19'h7ffff,0,0,19'h7fffe,0,0);",
            "    for (i=0; i<32; i=i+1) expect_read_enabled(i[4:0],1'b1);",
            "",
            "    // Dual search, small-page odd selection, large-page VPPN[8], ASID and global match.",
            "    write_entry(5'd2,19'h12345,10'h155,0,6'd12,1);",
            "    write_entry(5'd3,19'h2aa00,10'h011,1,6'd21,1);",
            "    fetch_pair(19'h12345,1,10'h155,19'h2ab00,0,10'h3ff);",
            "    if (!g_s0_found || g_s0_index!=5'd2 || g_s0_ppn!=20'h20002) begin $display(\"small-page/odd search got found=%0d index=%0d ppn=%h\",g_s0_found,g_s0_index,g_s0_ppn); $fatal(1,\"small-page/odd search expectation failed\"); end",
            "    if (!g_s1_found || g_s1_index!=5'd3 || g_s1_ppn!=20'h20003) begin $display(\"large-page/global search got found=%0d index=%0d ppn=%h\",g_s1_found,g_s1_index,g_s1_ppn); $fatal(1,\"large-page/global search expectation failed\"); end",
            "    fetch_pair(19'h12345,0,10'h154,19'h2aa00,0,10'h3fe);",
            "    if (g_s0_found || !g_s1_found) $fatal(1,\"ASID/global expectation failed\");",
            "",
            "    // Multi-match encoding is the bitwise OR of every matching index (5 | 10 = 15).",
            "    write_entry(5'd5,19'h34567,0,1,6'd12,1);",
            "    write_entry(5'd10,19'h34567,0,1,6'd12,1);",
            "    write_entry(5'd15,19'h45678,0,0,6'd12,1);",
            "    fetch_pair(19'h34567,0,10'h3ff,19'h34567,1,10'h2aa);",
            "    if (!g_s0_found || g_s0_index!=5'd15 || g_s0_ppn!=20'h1000f) $fatal(1,\"multi-match OR index expectation failed\");",
            "",
            "    // Invalidate op 0 and 1: clear all entries.",
            "    write_entry(0,19'h00100,1,0,6'd12,1); invalidate(0,0,0); expect_read_enabled(0,0);",
            "    write_entry(1,19'h00101,1,0,6'd12,1); invalidate(1,0,0); expect_read_enabled(1,0);",
            "    // Op 2 clears global only; op 3 clears non-global only.",
            "    write_entry(2,19'h00200,2,1,6'd12,1); write_entry(3,19'h00300,3,0,6'd12,1);",
            "    invalidate(2,0,0); expect_read_enabled(2,0); expect_read_enabled(3,1);",
            "    write_entry(2,19'h00200,2,1,6'd12,1); invalidate(3,0,0); expect_read_enabled(2,1); expect_read_enabled(3,0);",
            "    // Op 4 clears matching non-global ASID only.",
            "    write_entry(4,19'h00400,10'h044,0,6'd12,1); write_entry(5,19'h00500,10'h045,0,6'd12,1); write_entry(6,19'h00600,10'h044,1,6'd12,1);",
            "    invalidate(4,10'h044,0); expect_read_enabled(4,0); expect_read_enabled(5,1); expect_read_enabled(6,1);",
            "    // Op 5 covers exact small-page and upper-VPPN large-page local matches.",
            "    write_entry(8,19'h15555,10'h055,0,6'd12,1); write_entry(9,19'h15401,10'h055,0,6'd21,1);",
            "    write_entry(10,19'h15555,10'h056,0,6'd12,1); write_entry(11,19'h15555,10'h055,1,6'd12,1);",
            "    invalidate(5,10'h055,19'h15555); expect_read_enabled(8,0); expect_read_enabled(9,0); expect_read_enabled(10,1); expect_read_enabled(11,1);",
            "    // Op 6 accepts global or matching ASID, and still applies page matching.",
            "    write_entry(12,19'h16666,10'h066,0,6'd12,1); write_entry(13,19'h16601,10'h067,1,6'd21,1); write_entry(14,19'h16666,10'h067,0,6'd12,1);",
            "    invalidate(6,10'h066,19'h16666); expect_read_enabled(12,0); expect_read_enabled(13,0); expect_read_enabled(14,1);",
            "",
            "    // A write to the selected entry wins over simultaneous invalidation.",
            "    write_entry(12,19'h1aaaa,10'h012,0,6'd12,1); write_entry(13,19'h1bbbb,10'h013,0,6'd12,1);",
            "    we=1; w_index=12; w_vppn=19'h1cccc; w_asid=10'h012; w_g=0; w_ps=12; w_e=1;",
            "    w_v0=1; w_d0=1; w_mat0=2; w_plv0=3; w_ppn0=20'habcde; w_v1=1; w_d1=0; w_mat1=1; w_plv1=2; w_ppn1=20'hdef01;",
            "    inv_en=1; inv_op=0; tick(1); we=0; inv_en=0; expect_read_enabled(12,1); expect_read_enabled(13,0);",
            "",
            f"    // Deterministic randomized tail ({cycles} cycles), after all state has been initialized.",
            f"    for (i=0; i<{cycles}; i=i+1) begin",
            "      lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};",
            "      we=(lfsr[3:0]==0); w_index=lfsr[8:4]; w_vppn=lfsr[27:9]; w_asid=lfsr[18:9]; w_g=lfsr[19]; w_ps=lfsr[20]?6'd12:6'd21; w_e=lfsr[21];",
            "      w_v0=lfsr[22]; w_d0=lfsr[23]; w_mat0=lfsr[25:24]; w_plv0=lfsr[27:26]; w_ppn0={lfsr[19:0]};",
            "      w_v1=lfsr[28]; w_d1=lfsr[29]; w_mat1=lfsr[31:30]; w_plv1=lfsr[1:0]; w_ppn1={lfsr[9:0],lfsr[31:22]};",
            "      inv_en=(lfsr[7:4]==4'hf); inv_op=lfsr[12:8]%7; inv_asid=lfsr[22:13]; inv_vpn=lfsr[31:13];",
            "      s0_fetch=lfsr[0]; s0_vppn=lfsr[26:8]; s0_odd_page=lfsr[27]; s0_asid=lfsr[17:8];",
            "      s1_fetch=lfsr[1]; s1_vppn={lfsr[7:0],lfsr[31:21]}; s1_odd_page=lfsr[28]; s1_asid=lfsr[19:10]; r_index=lfsr[31:27];",
            "      tick(1);",
            "    end",
            '    $display("TLB_DIFF_PASS cycles=%0d checks=%0d random_cycles=%0d", cycle, checks, i);',
            "    $finish;",
            "  end",
            "endmodule",
            "",
        ]
    )
    return "\n".join(lines)


NEGATIVE_MUTATIONS = [
    (
        b"else if (inv_en) begin",
        b"if (inv_en) begin",
        "invalidate_overrides_simultaneous_write",
    )
]


def compile_and_run(
    golden: bytes,
    candidate: bytes,
    tools: bytes,
    out: Path,
    cycles: int,
    seed: int,
    timeout: int,
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=False)
    (out / "golden.v").write_bytes(rename_module(golden, b"tlb_entry_golden"))
    (out / "candidate.v").write_bytes(rename_module(candidate, b"tlb_entry_candidate"))
    (out / "tools.v").write_bytes(tools)
    (out / "tb.sv").write_text(testbench(cycles, seed), encoding="ascii", newline="\n")
    verilator = shutil.which("verilator")
    if not verilator:
        raise GateError("verilator is unavailable")
    obj = out / "obj"
    build = run(
        [
            verilator,
            "--binary",
            "-j",
            "0",
            "--timing",
            "--top-module",
            "tb",
            "-Wall",
            "-Wno-fatal",
            "-Wno-DECLFILENAME",
            "-Wno-UNUSEDSIGNAL",
            "--x-initial",
            "0",
            "--x-assign",
            "0",
            "--Mdir",
            str(obj.resolve()),
            str((out / "tb.sv").resolve()),
            str((out / "golden.v").resolve()),
            str((out / "candidate.v").resolve()),
            str((out / "tools.v").resolve()),
        ],
        out,
        timeout,
    )
    (out / "compile.log").write_text(build["stdout"], encoding="utf-8", newline="\n")
    warning_categories = re.findall(r"(?m)^%Warning-([A-Z0-9_]+):", build["stdout"])
    executable = obj / ("Vtb.exe" if sys.platform == "win32" else "Vtb")
    simulation = (
        run([str(executable)], out, timeout)
        if build["returncode"] == 0 and executable.is_file()
        else {
            "argv": [str(executable)],
            "returncode": 125,
            "timed_out": False,
            "elapsed_seconds": 0.0,
            "stdout": "simulation executable missing",
        }
    )
    (out / "simulation.log").write_text(
        simulation["stdout"], encoding="utf-8", newline="\n"
    )
    return {
        "build": {key: value for key, value in build.items() if key != "stdout"},
        "simulation": {key: value for key, value in simulation.items() if key != "stdout"},
        "compile_log_sha256": sha256_file(out / "compile.log"),
        "warning_categories": warning_categories,
        "simulation_log_sha256": sha256_file(out / "simulation.log"),
        "simulation_tail": simulation["stdout"].splitlines()[-8:],
    }


def command_diff(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    out = args.out_dir.resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise GateError(f"output directory must be fresh: {out}")
    out.mkdir(parents=True, exist_ok=True)
    golden, tools = locked_sources(repo)
    if args.rtl.is_symlink() or not args.rtl.is_file():
        raise GateError(f"candidate RTL must be a regular file: {args.rtl}")
    candidate = args.rtl.read_bytes()

    main = compile_and_run(
        golden, candidate, tools, out / "main", args.cycles, args.seed, args.timeout
    )
    main_pass = (
        main["build"]["returncode"] == 0
        and not main["warning_categories"]
        and main["simulation"]["returncode"] == 0
        and any("TLB_DIFF_PASS" in line for line in main["simulation_tail"])
    )

    controls = []
    for anchor, replacement, name in NEGATIVE_MUTATIONS:
        if golden.count(anchor) != 1:
            raise GateError(f"negative-control anchor count changed: {name}")
        mutated = golden.replace(anchor, replacement, 1)
        result = compile_and_run(
            golden,
            mutated,
            tools,
            out / f"negative-{name}",
            args.cycles,
            args.seed,
            args.timeout,
        )
        detected = (
            result["build"]["returncode"] == 0
            and not result["warning_categories"]
            and result["simulation"]["returncode"] != 0
            and any("TLB_MISMATCH" in line for line in result["simulation_tail"])
        )
        controls.append({"name": name, "detected": detected, "result": result})

    passed = main_pass and all(control["detected"] for control in controls)
    summary = {
        "schema_version": 1,
        "gate": "tlb-entry-cycle-diff",
        "status": "pass" if passed else "fail",
        "generated_at": now_iso(),
        "golden": {
            "commit": GOLDEN_COMMIT,
            "path": GOLDEN_PATH,
            "git_blob_sha1": GOLDEN_BLOB,
            "sha256": GOLDEN_SHA256,
            "size": GOLDEN_SIZE,
            "tools_path": TOOLS_PATH,
            "tools_git_blob_sha1": TOOLS_BLOB,
        },
        "candidate": {
            "path": str(args.rtl.resolve()),
            "sha256": sha256_bytes(candidate),
            "size": len(candidate),
        },
        "configuration": {"tlb_entries": 32, "random_cycles": args.cycles, "seed": args.seed},
        "directed_coverage": [
            "initialize_and_read_all_32_entries",
            "dual_registered_search_ports",
            "small_page_explicit_odd_page",
            "large_page_vppn_bit_8",
            "asid_and_global_match",
            "multi_match_bitwise_or_index",
            "invalidate_op_0_through_6",
            "simultaneous_write_invalidate_priority",
        ],
        "main": main,
        "negative_controls": controls,
    }
    write_json(out / "summary.json", summary)
    return 0 if passed else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    diff = sub.add_parser("diff")
    diff.add_argument("--repo", type=Path, default=Path("."))
    diff.add_argument("--rtl", type=Path, required=True)
    diff.add_argument("--out-dir", type=Path, required=True)
    diff.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    diff.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    diff.add_argument("--timeout", type=int, default=300)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.cycles < 1 or args.timeout < 1:
            raise GateError("cycles and timeout must be positive")
        return command_diff(args)
    except GateError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
