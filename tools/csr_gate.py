#!/usr/bin/env python3
"""Fail-closed port, static, and cycle-differential gates for the active CSR."""

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


INPUTS = {
    "clk": 1,
    "reset": 1,
    "rd_addr": 14,
    "csr_wr_en": 1,
    "wr_addr": 14,
    "wr_data": 32,
    "interrupt": 8,
    "excp_flush": 1,
    "ertn_flush": 1,
    "era_in": 32,
    "esubcode_in": 9,
    "ecode_in": 6,
    "va_error_in": 1,
    "bad_va_in": 32,
    "tlbsrch_en": 1,
    "tlbsrch_found": 1,
    "tlbsrch_index": 5,
    "excp_tlbrefill": 1,
    "excp_tlb": 1,
    "excp_tlb_vppn": 19,
    "llbit_in": 1,
    "llbit_set_in": 1,
    "lladdr_in": 28,
    "lladdr_set_in": 1,
    "tlbrd_en": 1,
    "tlbehi_in": 32,
    "tlbelo0_in": 32,
    "tlbelo1_in": 32,
    "tlbidx_in": 32,
    "asid_in": 10,
}

OUTPUTS = {
    "rd_data": 32,
    "timer_64_out": 64,
    "tid_out": 32,
    "has_int": 1,
    "llbit_out": 1,
    "vppn_out": 19,
    "lladdr_out": 28,
    "eentry_out": 32,
    "era_out": 32,
    "tlbrentry_out": 32,
    "disable_cache_out": 1,
    "asid_out": 10,
    "rand_index": 5,
    "tlbehi_out": 32,
    "tlbelo0_out": 32,
    "tlbelo1_out": 32,
    "tlbidx_out": 32,
    "pg_out": 1,
    "da_out": 1,
    "dmw0_out": 32,
    "dmw1_out": 32,
    "datf_out": 2,
    "datm_out": 2,
    "ecode_out": 6,
    "plv_out": 2,
}

DIFF_OUTPUTS = {
    name: 32
    for name in (
        "csr_crmd_diff",
        "csr_prmd_diff",
        "csr_ectl_diff",
        "csr_estat_diff",
        "csr_era_diff",
        "csr_badv_diff",
        "csr_eentry_diff",
        "csr_tlbidx_diff",
        "csr_tlbehi_diff",
        "csr_tlbelo0_diff",
        "csr_tlbelo1_diff",
        "csr_asid_diff",
        "csr_save0_diff",
        "csr_save1_diff",
        "csr_save2_diff",
        "csr_save3_diff",
        "csr_tid_diff",
        "csr_tcfg_diff",
        "csr_tval_diff",
        "csr_ticlr_diff",
        "csr_llbctl_diff",
        "csr_tlbrentry_diff",
        "csr_dmw0_diff",
        "csr_dmw1_diff",
        "csr_pgdl_diff",
        "csr_pgdh_diff",
    )
}


class CsrGateError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(argv: list[str], cwd: Path, timeout: int = 300) -> dict[str, object]:
    started = time.monotonic()
    result = subprocess.run(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return {
        "argv": argv,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode:
        raise CsrGateError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def parse_yosys_ports(path: Path) -> dict[str, tuple[str, int]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    try:
        ports = document["modules"]["csr"]["ports"]
    except (KeyError, TypeError) as error:
        raise CsrGateError("Yosys JSON does not contain module csr") from error
    return {name: (value["direction"], len(value["bits"])) for name, value in ports.items()}


def expected_ports(diff_test: bool) -> dict[str, tuple[str, int]]:
    ports = {name: ("input", width) for name, width in INPUTS.items()}
    ports.update({name: ("output", width) for name, width in OUTPUTS.items()})
    if diff_test:
        ports.update({name: ("output", width) for name, width in DIFF_OUTPUTS.items()})
    return ports


def yosys_projection(rtl: Path, output: Path) -> dict[str, object]:
    yosys = shutil.which("yosys")
    if not yosys:
        raise CsrGateError("yosys is not on PATH")
    script = f"read_verilog {rtl.resolve().as_posix()}; hierarchy -check -top csr; proc; check -assert; write_json {output.resolve().as_posix()}"
    return run([yosys, "-q", "-p", script], output.parent)


def port_check(args: argparse.Namespace) -> int:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    projection = args.out_dir / "csr.json"
    command = yosys_projection(args.rtl, projection)
    actual = parse_yosys_ports(projection) if command["returncode"] == 0 else {}
    expected = expected_ports(args.diff_test)
    passed = command["returncode"] == 0 and actual == expected
    summary = base_summary("csr-port-check", passed)
    summary.update({"diff_test": args.diff_test, "expected": expected, "actual": actual, "command": command})
    write_json(args.out_dir / "summary.json", summary)
    return 0 if passed else 1


def static_check(args: argparse.Namespace) -> int:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    verilator = shutil.which("verilator")
    if not verilator:
        raise CsrGateError("verilator is not on PATH")
    lint = run(
        [
            verilator,
            "--lint-only",
            "-Wall",
            "-Wno-fatal",
            "-Wno-UNUSEDSIGNAL",
            "-Wno-SYMRSVDWORD",
            "-Wno-UNUSEDPARAM",
            str(args.rtl.resolve()),
        ],
        args.out_dir,
    )
    warnings = [line for line in lint["stdout"].splitlines() if line.startswith("%Warning")]
    projection = args.out_dir / "csr.json"
    yosys = yosys_projection(args.rtl, projection)
    passed = lint["returncode"] == 0 and not warnings and yosys["returncode"] == 0
    summary = base_summary("csr-static", passed)
    summary.update(
        {
            "lint": lint,
            "lint_warnings": warnings,
            "yosys": yosys,
            "applied_waivers": [
                "csr-legacy-unused-tlbehi-input-bits",
                "csr-legacy-unused-tlbelo0-input-bits",
                "csr-legacy-unused-tlbelo1-input-bits",
                "csr-legacy-unused-tlbidx-input-bits",
                "csr-legacy-unused-brk-state",
                "csr-legacy-disable-cache-upper-bits",
                "csr-legacy-interrupt-port-name",
                "csr-locked-tlbnum-compat-parameter",
            ],
        }
    )
    write_json(args.out_dir / "summary.json", summary)
    return 0 if passed else 1


def renamed_module(payload: bytes, replacement: bytes) -> bytes:
    transformed, count = re.subn(rb"(?m)^module\s+csr\b", b"module " + replacement, payload)
    if count != 1:
        raise CsrGateError(f"expected one csr module declaration, found {count}")
    return transformed


def declaration(kind: str, name: str, width: int) -> str:
    suffix = "" if width == 1 else f" [{width - 1}:0]"
    return f"  {kind}{suffix} {name};"


def testbench(cycles: int) -> str:
    outputs = {**OUTPUTS, **DIFF_OUTPUTS}
    lines = ["module tb;", *[declaration("reg", n, w) for n, w in INPUTS.items()]]
    for prefix in ("g", "c"):
        lines.extend(declaration("wire", f"{prefix}_{n}", w) for n, w in outputs.items())
    input_connections = [f".{name}({name})" for name in INPUTS]
    for module, prefix in (("csr_golden", "g"), ("csr_candidate", "c")):
        connections = input_connections + [f".{name}({prefix}_{name})" for name in outputs]
        lines.append(f"  {module} dut_{prefix} (" + ",".join(connections) + ");")
    golden_vector = ",".join(f"g_{name}" for name in outputs)
    candidate_vector = ",".join(f"c_{name}" for name in outputs)
    lines.extend(
        [
            "  integer cycle; integer i; reg [31:0] lfsr;",
            "  task check; begin",
            f"    if ({{{golden_vector}}} !== {{{candidate_vector}}}) begin",
            '      $display("CSR_MISMATCH cycle=%0d rd_addr=%h wr_addr=%h wr_data=%h", cycle, rd_addr, wr_addr, wr_data);',
            "      $fatal(1);",
            "    end",
            "  end endtask",
            "  task step; begin #4; clk=1; #1; check; #4; clk=0; #1; cycle=cycle+1; check; end endtask",
            "  task csr_write(input [13:0] address, input [31:0] data); begin",
            "    csr_wr_en=1; wr_addr=address; wr_data=data; rd_addr=address; step;",
            "    csr_wr_en=0; step;",
            "  end endtask",
            "  initial begin",
            "    clk=0; cycle=0; lfsr=32'h158aa8c5;",
        ]
    )
    lines.extend(f"    {name}=0;" for name in INPUTS if name != "clk")
    addresses = [
        0x0, 0x1, 0x4, 0x5, 0x6, 0x7, 0xC, 0x10, 0x11, 0x12, 0x13, 0x18,
        0x19, 0x1A, 0x30, 0x31, 0x32, 0x33, 0x40, 0x41, 0x43, 0x44, 0x60,
        0x88, 0x100, 0x101, 0x180, 0x181,
        0xB1, 0xB2, 0xC0, 0xC1, 0xC2, 0xC3,
    ]
    lines.extend(["    reset=1; step; step; reset=0; step;"])
    for index, address in enumerate(addresses):
        lines.append(f"    csr_write(14'h{address:03x}, 32'h{(0x9e3779b9 * (index + 1)) & 0xffffffff:08x});")
    lines.extend(
        [
            "    excp_flush=1; era_in=32'h1c001234; ecode_in=6'h3f; esubcode_in=9'h155; excp_tlbrefill=1; excp_tlb=1; excp_tlb_vppn=19'h54321; va_error_in=1; bad_va_in=32'hdeadbeef; step;",
            "    excp_flush=0; excp_tlbrefill=0; excp_tlb=0; va_error_in=0; ertn_flush=1; step; ertn_flush=0;",
            "    tlbsrch_en=1; tlbsrch_found=1; tlbsrch_index=5'h1d; step; tlbsrch_found=0; step; tlbsrch_en=0;",
            "    tlbrd_en=1; tlbidx_in=32'h0c000012; tlbehi_in=32'habcde000; tlbelo0_in=32'h01234567; tlbelo1_in=32'h07654321; asid_in=10'h2aa; step; tlbidx_in[31]=1; step; tlbrd_en=0;",
            "    llbit_set_in=1; llbit_in=1; lladdr_set_in=1; lladdr_in=28'h1234567; step; llbit_set_in=0; lladdr_set_in=0;",
            f"    for (i=0; i<{cycles}; i=i+1) begin",
            "      lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};",
            "      reset=(i%521)==520; rd_addr=lfsr[13:0]; csr_wr_en=lfsr[0]&lfsr[5]; wr_addr=lfsr[27:14]; wr_data=lfsr^{lfsr[15:0],lfsr[31:16]};",
            "      interrupt=lfsr[15:8]; excp_flush=lfsr[2]&lfsr[7]&lfsr[12]; ertn_flush=lfsr[3]&lfsr[8]&lfsr[13];",
            "      era_in=lfsr+32'h1c000000; esubcode_in=lfsr[8:0]; ecode_in=lfsr[5:0]; va_error_in=lfsr[4]&lfsr[9]; bad_va_in=~lfsr;",
            "      tlbsrch_en=lfsr[6]&lfsr[11]; tlbsrch_found=lfsr[16]; tlbsrch_index=lfsr[20:16]; excp_tlbrefill=lfsr[17]&lfsr[22]; excp_tlb=lfsr[18]&lfsr[23]; excp_tlb_vppn=lfsr[31:13];",
            "      llbit_in=lfsr[24]; llbit_set_in=lfsr[19]&lfsr[24]; lladdr_in=lfsr[27:0]; lladdr_set_in=lfsr[20]&lfsr[25];",
            "      tlbrd_en=lfsr[21]&lfsr[26]; tlbehi_in=lfsr; tlbelo0_in=lfsr^32'ha5a5a5a5; tlbelo1_in=~lfsr; tlbidx_in={lfsr[31],lfsr[30:0]}; asid_in=lfsr[9:0]; step;",
            "    end",
            '    $display("CSR_DIFF_PASS cycles=%0d", cycle); $finish;',
            "  end",
            "endmodule",
            "",
        ]
    )
    return "\n".join(lines)


def differential(args: argparse.Namespace) -> int:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    source = git_bytes(args.repo, "show", f"{args.golden_commit}:rtl/csr.v")
    header = git_bytes(args.repo, "show", f"{args.golden_commit}:rtl/csr.h")
    if sha256_bytes(source) != args.golden_sha256:
        raise CsrGateError("golden csr.v SHA256 does not match the locked contract")
    (args.out_dir / "csr.h").write_bytes(header)
    (args.out_dir / "mycpu.h").write_text("\n", encoding="ascii")
    (args.out_dir / "golden.v").write_bytes(renamed_module(source, b"csr_golden"))
    (args.out_dir / "candidate.v").write_bytes(
        renamed_module(args.rtl.read_bytes(), b"csr_candidate")
    )
    (args.out_dir / "tb.sv").write_text(testbench(args.cycles), encoding="ascii")
    verilator = shutil.which("verilator")
    if not verilator:
        raise CsrGateError("verilator is not on PATH")
    build = run(
        [
            verilator,
            "--binary",
            "--timing",
            "-Wall",
            "-Wno-fatal",
            "-DDIFFTEST_EN",
            "--x-initial", "0",
            "--x-assign", "0",
            "--top-module", "tb",
            "-I" + str(args.out_dir.resolve()),
            "--Mdir", str((args.out_dir / "obj").resolve()),
            str((args.out_dir / "tb.sv").resolve()),
            str((args.out_dir / "golden.v").resolve()),
            str((args.out_dir / "candidate.v").resolve()),
        ],
        args.out_dir,
        timeout=args.timeout,
    )
    executable = args.out_dir / "obj" / ("Vtb.exe" if sys.platform == "win32" else "Vtb")
    simulation = (
        run([str(executable)], args.out_dir, timeout=args.timeout)
        if build["returncode"] == 0 and executable.is_file()
        else {"returncode": 125, "stdout": "simulation executable missing", "elapsed_seconds": 0}
    )
    passed = build["returncode"] == 0 and simulation["returncode"] == 0 and "CSR_DIFF_PASS" in simulation["stdout"]
    summary = base_summary("csr-cycle-diff", passed)
    summary.update(
        {
            "cycles_requested": args.cycles,
            "golden_sha256": sha256_bytes(source),
            "candidate_sha256": sha256_file(args.rtl),
            "build": build,
            "simulation": simulation,
        }
    )
    write_json(args.out_dir / "summary.json", summary)
    return 0 if passed else 1


def base_summary(gate: str, passed: bool) -> dict[str, object]:
    return {
        "schema_version": 1,
        "gate": gate,
        "status": "pass" if passed else "fail",
        "executed": 1,
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "skipped": 0,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    ports = commands.add_parser("port-check")
    ports.add_argument("--rtl", type=Path, required=True)
    ports.add_argument("--out-dir", type=Path, required=True)
    ports.add_argument("--diff-test", action="store_true")
    static = commands.add_parser("static")
    static.add_argument("--rtl", type=Path, required=True)
    static.add_argument("--out-dir", type=Path, required=True)
    diff = commands.add_parser("diff")
    diff.add_argument("--repo", type=Path, default=Path("."))
    diff.add_argument("--rtl", type=Path, required=True)
    diff.add_argument("--out-dir", type=Path, required=True)
    diff.add_argument("--golden-commit", default="a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6")
    diff.add_argument("--golden-sha256", default="7349b5b83975b6da8efe69f42d8ee43d93312f7e13def4ed2f6c48a3a868c433")
    diff.add_argument("--cycles", type=int, default=4096)
    diff.add_argument("--timeout", type=int, default=600)
    return root


def main() -> int:
    if not sys.flags.isolated:
        print("csr_gate.py requires python -I", file=sys.stderr)
        return 2
    args = parser().parse_args()
    try:
        if args.command == "port-check":
            return port_check(args)
        if args.command == "static":
            return static_check(args)
        return differential(args)
    except (CsrGateError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
