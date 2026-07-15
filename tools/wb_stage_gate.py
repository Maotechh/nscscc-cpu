#!/usr/bin/env python3
"""Fail-closed contract, static and lockstep gates for the active writeback stage."""

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
GOLDEN_PATH = "rtl/wb_stage.v"
GOLDEN_BLOB = "90ae54b4ea13298aa64ee83aa33eee14813392d7"
GOLDEN_SHA256 = "8a6f6cb282d152e4b43673397b8c00f598e3d116589e5797fb6feaadbc032a09"
GOLDEN_SIZE = 12315
CSR_PATH = "rtl/csr.h"
CSR_BLOB = "a1d8a4389e2b45afee520d5c70d728d14404e13c"
CSR_SHA256 = "11f5550b887a2b507a5b916340069d6d127848c66c761f07d0303c7cc201026d"
CSR_SIZE = 1409
DEFAULT_CYCLES = 8192
DEFAULT_SEED = 0x0158AA8C

INPUTS = {
    "clk": 1,
    "reset": 1,
    "ms_to_ws_valid": 1,
    "ms_to_ws_bus": 493,
    "debug_break_point": 1,
}

OUTPUTS = {
    "ws_allowin": 1,
    "ws_to_rf_bus": 38,
    "ws_to_ds_valid": 1,
    "csr_era": 32,
    "csr_esubcode": 9,
    "csr_ecode": 6,
    "excp_flush": 1,
    "ertn_flush": 1,
    "refetch_flush": 1,
    "icacop_flush": 1,
    "csr_wr_en": 1,
    "wr_csr_addr": 14,
    "wr_csr_data": 32,
    "va_error": 1,
    "bad_va": 32,
    "excp_tlbrefill": 1,
    "excp_tlb": 1,
    "excp_tlb_vppn": 19,
    "idle_flush": 1,
    "ws_llbit_set": 1,
    "ws_llbit": 1,
    "ws_lladdr_set": 1,
    "ws_lladdr": 28,
    "tlb_inst_stall": 1,
    "tlbsrch_en": 1,
    "tlbsrch_found": 1,
    "tlbsrch_index": 5,
    "tlbfill_en": 1,
    "tlbwr_en": 1,
    "tlbrd_en": 1,
    "invtlb_en": 1,
    "invtlb_asid": 10,
    "invtlb_vpn": 19,
    "invtlb_op": 5,
    "real_valid": 1,
    "real_br_inst": 1,
    "real_icache_miss": 1,
    "real_dcache_miss": 1,
    "real_mem_inst": 1,
    "real_br_pre": 1,
    "real_br_pre_error": 1,
    "debug_ws_valid": 1,
    "debug_wb_pc": 32,
    "debug_wb_rf_wen": 4,
    "debug_wb_rf_wnum": 5,
    "debug_wb_rf_wdata": 32,
    "debug_wb_inst": 32,
}

DIFF_OUTPUTS = {
    "ws_valid_diff": 1,
    "ws_cnt_inst_diff": 1,
    "ws_timer_64_diff": 64,
    "ws_inst_ld_en_diff": 8,
    "ws_ld_paddr_diff": 32,
    "ws_ld_vaddr_diff": 32,
    "ws_inst_st_en_diff": 8,
    "ws_st_paddr_diff": 32,
    "ws_st_vaddr_diff": 32,
    "ws_st_data_diff": 32,
    "ws_csr_rstat_en_diff": 1,
    "ws_csr_data_diff": 32,
}


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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def fresh(path: Path) -> Path:
    path = path.resolve()
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise GateError(f"output directory must be fresh: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def run(argv: list[str], cwd: Path, timeout: int = 300) -> dict[str, object]:
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
        returncode = result.returncode
        output = result.stdout.decode("utf-8", errors="replace")
        timed_out = False
    except subprocess.TimeoutExpired as error:
        returncode = 124
        output = (error.stdout or b"").decode("utf-8", errors="replace")
        timed_out = True
    except OSError as error:
        returncode = 125
        output = f"failed to start command: {error}\n"
        timed_out = False
    return {
        "argv": argv,
        "returncode": returncode,
        "stdout": output,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode:
        raise GateError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def expected_ports(diff_test: bool) -> dict[str, dict[str, object]]:
    ports = {name: {"direction": "input", "width": width} for name, width in INPUTS.items()}
    ports.update(
        {name: {"direction": "output", "width": width} for name, width in OUTPUTS.items()}
    )
    if diff_test:
        ports.update(
            {
                name: {"direction": "output", "width": width}
                for name, width in DIFF_OUTPUTS.items()
            }
        )
    return ports


def load_contract(repo: Path, path: Path) -> tuple[dict[str, object], bytes, bytes]:
    data = json.loads(path.read_text(encoding="utf-8"))
    identity = {
        "commit_key": "team_golden_candidate",
        "path": GOLDEN_PATH,
        "git_blob_sha1": GOLDEN_BLOB,
        "sha256": GOLDEN_SHA256,
        "size": GOLDEN_SIZE,
        "csr_header": {
            "path": CSR_PATH,
            "git_blob_sha1": CSR_BLOB,
            "sha256": CSR_SHA256,
            "size": CSR_SIZE,
        },
    }
    if data.get("schema_version") != 1 or data.get("target") != "wb_stage":
        raise GateError("wb_stage contract schema/target mismatch")
    if data.get("module") != "wb_stage" or data.get("golden") != identity:
        raise GateError("wb_stage golden identity mismatch")
    if data.get("bus_widths") != {"MS_TO_WS_BUS_WD": 493, "WS_TO_RF_BUS_WD": 38}:
        raise GateError("wb_stage bus width contract mismatch")
    profiles = data.get("profiles")
    if profiles != {
        "normal": {"defines": [], "port_count": 52},
        "difftest": {"defines": ["DIFFTEST_EN"], "port_count": 64},
    }:
        raise GateError("wb_stage profile contract mismatch")
    ports = data.get("ports", {})
    common = expected_ports(False)
    extras = {name: expected_ports(True)[name] for name in DIFF_OUTPUTS}
    if ports != {"common": common, "difftest_extra": extras}:
        raise GateError("wb_stage port contract differs from locked gate")
    differential = data.get("differential")
    if differential != {
        "minimum_cycles": DEFAULT_CYCLES,
        "seed": "0x0158aa8c",
        "compare_difftest_payload_while_stalled": True,
        "negative_control_required": True,
    }:
        raise GateError("wb_stage differential contract mismatch")

    manifest: dict[str, str] = {}
    for raw in (repo / "reference" / "manifest.lock").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key in manifest:
            raise GateError("invalid reference/manifest.lock")
        manifest[key] = value
    if manifest.get("team_golden_candidate") != GOLDEN_COMMIT:
        raise GateError("manifest golden commit mismatch")

    source = git_bytes(repo, "cat-file", "blob", f"{GOLDEN_COMMIT}:{GOLDEN_PATH}")
    csr = git_bytes(repo, "cat-file", "blob", f"{GOLDEN_COMMIT}:{CSR_PATH}")
    if len(source) != GOLDEN_SIZE or sha256_bytes(source) != GOLDEN_SHA256:
        raise GateError("locked wb_stage.v bytes mismatch")
    if len(csr) != CSR_SIZE or sha256_bytes(csr) != CSR_SHA256:
        raise GateError("locked csr.h bytes mismatch")
    return data, source, csr


def materialize_golden(out: Path, source: bytes, csr: bytes) -> Path:
    (out / "csr.h").write_bytes(csr)
    (out / "mycpu.h").write_text(
        "`define MS_TO_WS_BUS_WD 493\n`define WS_TO_RF_BUS_WD 38\n", encoding="ascii"
    )
    rtl = out / "wb_stage.v"
    rtl.write_bytes(source)
    return rtl


def yosys_projection(
    rtl: Path, out: Path, *, include_dir: Path | None = None, diff_test: bool = False
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    out.mkdir(parents=True, exist_ok=True)
    yosys = shutil.which("yosys")
    if not yosys:
        raise GateError("yosys is not on PATH")
    projection = out / ("ports-diff.json" if diff_test else "ports-normal.json")
    flags = []
    if include_dir is not None:
        flags.append(f"-I{include_dir.resolve().as_posix()}")
    if diff_test:
        flags.append("-D DIFFTEST_EN")
    script = (
        f"read_verilog {' '.join(flags)} {rtl.resolve().as_posix()}; "
        f"hierarchy -check -top wb_stage; proc; write_json {projection.resolve().as_posix()}"
    )
    command = run([yosys, "-q", "-p", script], out)
    if command["returncode"] != 0:
        return {}, command
    document = json.loads(projection.read_text(encoding="utf-8"))
    try:
        ports = document["modules"]["wb_stage"]["ports"]
    except (KeyError, TypeError) as error:
        raise GateError("Yosys projection does not contain wb_stage") from error
    actual = {
        name: {"direction": value["direction"], "width": len(value["bits"])}
        for name, value in ports.items()
    }
    return actual, command


def summary(gate: str, passed: bool) -> dict[str, object]:
    return {
        "schema_version": 1,
        "gate": gate,
        "status": "pass" if passed else "fail",
        "executed": 1,
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "skipped": 0,
        "generated_at": now_iso(),
    }


def command_contract(args: argparse.Namespace) -> int:
    out = fresh(args.out_dir)
    _, source, csr = load_contract(args.repo.resolve(), args.contract.resolve())
    golden = materialize_golden(out, source, csr)
    results: dict[str, object] = {}
    passed = True
    for profile, enabled in (("normal", False), ("difftest", True)):
        actual, command = yosys_projection(
            golden, out / profile, include_dir=out, diff_test=enabled
        )
        matched = command["returncode"] == 0 and actual == expected_ports(enabled)
        passed = passed and matched
        results[profile] = {
            "matched": matched,
            "expected_count": len(expected_ports(enabled)),
            "actual_count": len(actual),
            "command": command,
        }
    result = summary("wb-stage-contract", passed)
    result.update(
        {
            "golden_sha256": sha256_bytes(source),
            "csr_header_sha256": sha256_bytes(csr),
            "profiles": results,
        }
    )
    write_json(out / "summary.json", result)
    return 0 if passed else 1


def command_port(args: argparse.Namespace) -> int:
    out = fresh(args.out_dir)
    load_contract(args.repo.resolve(), args.contract.resolve())
    enabled = args.profile == "difftest"
    actual, command = yosys_projection(args.rtl.resolve(), out, diff_test=False)
    expected = expected_ports(enabled)
    passed = command["returncode"] == 0 and actual == expected
    result = summary(f"wb-stage-port-{args.profile}", passed)
    result.update(
        {
            "profile": args.profile,
            "expected_count": len(expected),
            "actual_count": len(actual),
            "matched": actual == expected,
            "rtl_sha256": sha256_file(args.rtl),
            "command": command,
        }
    )
    write_json(out / "summary.json", result)
    return 0 if passed else 1


def command_lint(args: argparse.Namespace) -> int:
    out = fresh(args.out_dir)
    load_contract(args.repo.resolve(), args.contract.resolve())
    verilator = shutil.which("verilator")
    if not verilator:
        raise GateError("verilator is not on PATH")
    command = run(
        [
            verilator,
            "--lint-only",
            "--top-module",
            "wb_stage",
            "-Wall",
            "-Wno-fatal",
            "-Wno-DECLFILENAME",
            str(args.rtl.resolve()),
        ],
        args.repo.resolve(),
    )
    (out / "verilator.log").write_text(command["stdout"], encoding="utf-8")
    blocks = re.findall(
        r"(?ms)^%Warning-([A-Z0-9_]+):\s+(.*?)(?=^%Warning-|\Z)", str(command["stdout"])
    )
    diagnostics: list[dict[str, str]] = []
    for category, block in blocks:
        signal = re.search(r"(?:Bits of signal are|Signal is) not used: '([^']+)'(\[[^]]+\])?", block)
        if category != "UNUSEDSIGNAL" or signal is None:
            diagnostics.append({"category": category, "signal": "<unparsed>", "bits": ""})
        else:
            diagnostics.append(
                {
                    "category": category,
                    "signal": signal.group(1),
                    "bits": signal.group(2) or "",
                }
            )
    common = {
        ("UNUSEDSIGNAL", "payload_exceptionCode", "[10]"),
        ("UNUSEDSIGNAL", "payload_physicalAddress", "[3:0]"),
    }
    normal_only = {
        ("UNUSEDSIGNAL", "area_stage_io_realValid", ""),
        ("UNUSEDSIGNAL", "payload_timer", ""),
        ("UNUSEDSIGNAL", "payload_isCounterInstruction", ""),
        ("UNUSEDSIGNAL", "payload_loadEvent", ""),
        ("UNUSEDSIGNAL", "payload_memoryPhysicalAddress", ""),
        ("UNUSEDSIGNAL", "payload_memoryVirtualAddress", ""),
        ("UNUSEDSIGNAL", "payload_storeEvent", ""),
        ("UNUSEDSIGNAL", "payload_storeData", ""),
        ("UNUSEDSIGNAL", "payload_csrRstatEvent", ""),
        ("UNUSEDSIGNAL", "payload_csrData", ""),
    }
    approved = common | (normal_only if args.profile == "normal" else set())
    actual = {(item["category"], item["signal"], item["bits"]) for item in diagnostics}
    unapproved = actual - approved
    missing = approved - actual
    passed = (
        command["returncode"] == 0
        and "%Error" not in command["stdout"]
        and not unapproved
        and not missing
        and len(actual) == len(diagnostics)
    )
    result = summary(f"wb-stage-lint-{args.profile}", passed)
    result.update(
        {
            "profile": args.profile,
            "diagnostics": diagnostics,
            "approved_unused": [
                {"category": category, "signal": signal, "bits": bits}
                for category, signal, bits in sorted(approved)
            ],
            "unapproved": [list(item) for item in sorted(unapproved)],
            "missing_expected": [list(item) for item in sorted(missing)],
            "suppressed_at_tool": [
                "DECLFILENAME only: reproducible one-file SpinalHDL component output"
            ],
            "command": command,
            "log_sha256": sha256_file(out / "verilator.log"),
        }
    )
    write_json(out / "summary.json", result)
    return 0 if passed else 1


def command_yosys(args: argparse.Namespace) -> int:
    out = fresh(args.out_dir)
    load_contract(args.repo.resolve(), args.contract.resolve())
    yosys = shutil.which("yosys")
    if not yosys:
        raise GateError("yosys is not on PATH")
    script = (
        f"read_verilog {args.rtl.resolve().as_posix()}; hierarchy -check -top wb_stage; "
        "proc; opt; check -assert"
    )
    command = run([yosys, "-q", "-p", script], args.repo.resolve())
    (out / "yosys.log").write_text(command["stdout"], encoding="utf-8")
    diagnostics = re.findall(r"(?im)^\s*(warning|error):", str(command["stdout"]))
    passed = command["returncode"] == 0 and not diagnostics
    result = summary(f"wb-stage-yosys-{args.profile}", passed)
    result.update(
        {
            "profile": args.profile,
            "diagnostics": diagnostics,
            "command": command,
            "log_sha256": sha256_file(out / "yosys.log"),
        }
    )
    write_json(out / "summary.json", result)
    return 0 if passed else 1


def renamed_module(payload: bytes, replacement: bytes) -> bytes:
    transformed, count = re.subn(
        rb"(?m)^module\s+wb_stage(?=\s|#|\()", b"module " + replacement, payload
    )
    if count != 1:
        raise GateError(f"expected one wb_stage module declaration, found {count}")
    return transformed


def declaration(kind: str, name: str, width: int) -> str:
    dimension = "" if width == 1 else f" [{width - 1}:0]"
    return f"  {kind}{dimension} {name};"


def testbench(cycles: int, seed: int) -> str:
    observed = {**OUTPUTS, **DIFF_OUTPUTS}
    lines = ["module tb;", *[declaration("reg", name, width) for name, width in INPUTS.items()]]
    for prefix in ("g", "c"):
        lines.extend(declaration("wire", f"{prefix}_{name}", width) for name, width in observed.items())
    input_connections = [f".{name}({name})" for name in INPUTS]
    for module, prefix in (("wb_stage_golden", "g"), ("wb_stage_candidate", "c")):
        connections = input_connections + [f".{name}({prefix}_{name})" for name in observed]
        lines.append(f"  {module} dut_{prefix} (" + ",".join(connections) + ");")
    golden_vector = ",".join(f"g_{name}" for name in observed)
    candidate_items = [
        (
            "(c_debug_ws_valid ^ (negative_control & c_debug_ws_valid))"
            if name == "debug_ws_valid"
            else f"c_{name}"
        )
        for name in observed
    ]
    candidate_vector = ",".join(candidate_items)
    lines.extend(
        [
            "  integer cycle; integer i; integer j; integer phase;",
            "  reg [31:0] lfsr; reg [511:0] random_bus; reg negative_control;",
            "  task check; begin",
            f"    if ({{{golden_vector}}} !== {{{candidate_vector}}}) begin",
            '      $display("WB_MISMATCH cycle=%0d phase=%0d g_valid=%b c_valid=%b g_pc=%h c_pc=%h g_diff_valid=%b c_diff_valid=%b", cycle, phase, g_debug_ws_valid, c_debug_ws_valid, g_debug_wb_pc, c_debug_wb_pc, g_ws_valid_diff, c_ws_valid_diff);',
            "      $fatal(1);",
            "    end",
            "  end endtask",
            "  task step; begin",
            "    phase=0; #2; check; #2; clk=1; phase=1; #1; check; #4; clk=0; phase=2; #1; check; cycle=cycle+1;",
            "  end endtask",
            "  task randomize_bus; begin",
            "    for (j=0; j<16; j=j+1) begin",
            "      lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};",
            "      random_bus[j*32 +: 32]=lfsr ^ (32'h9e3779b9*j);",
            "    end",
            "    ms_to_ws_bus=random_bus[492:0];",
            "  end endtask",
            "  initial begin",
            "    clk=0; reset=0; ms_to_ws_valid=0; ms_to_ws_bus=0; debug_break_point=0;",
            f"    cycle=0; phase=0; lfsr=32'h{seed & 0xFFFFFFFF:08x}; random_bus=0;",
            '    negative_control=$test$plusargs("negative-control");',
            "    reset=1; step; step; reset=0; step;",
            "    ms_to_ws_bus=0; ms_to_ws_bus[69]=1; ms_to_ws_bus[68:64]=5'h1d;",
            "    ms_to_ws_bus[63:32]=32'h89abcdef; ms_to_ws_bus[31:0]=32'h1c001234;",
            "    ms_to_ws_bus[282:251]=32'h00100013; ms_to_ws_bus[346:283]=64'h0123456789abcdef;",
            "    ms_to_ws_bus[347]=1; ms_to_ws_bus[355:348]=8'ha5;",
            "    ms_to_ws_bus[387:356]=32'h10001234; ms_to_ws_bus[419:388]=32'h80001234;",
            "    ms_to_ws_bus[427:420]=8'h5a; ms_to_ws_bus[459:428]=32'hdeadbeef;",
            "    ms_to_ws_bus[460]=1; ms_to_ws_bus[492:461]=32'h55aa33cc;",
            "    ms_to_ws_valid=1; step;",
            "    debug_break_point=1;",
            "    for (i=0; i<7; i=i+1) begin randomize_bus; ms_to_ws_valid=i[0]; step; end",
            "    debug_break_point=0; ms_to_ws_valid=0; step;",
            "    for (i=0; i<16; i=i+1) begin",
            "      ms_to_ws_bus=0; ms_to_ws_bus[134:119]=(16'h1 << i);",
            "      ms_to_ws_bus[31:0]=32'h1c010000+i; ms_to_ws_bus[168:137]=32'h80002000+i;",
            "      ms_to_ws_valid=1; step; ms_to_ws_valid=0; step;",
            "    end",
            f"    for (i=0; i<{cycles}; i=i+1) begin",
            "      randomize_bus;",
            "      reset=(i==2047 || i==6143);",
            "      ms_to_ws_valid=(lfsr[2:0] != 0);",
            "      debug_break_point=(lfsr[7:5] == 3'b111) && !reset;",
            "      step;",
            "    end",
            "    reset=0; debug_break_point=0; ms_to_ws_valid=0; step; step;",
            "    if (negative_control) begin $display(\"NEGATIVE_CONTROL_DID_NOT_FAIL\"); $fatal(1); end",
            f'    $display("WB_DIFF_PASS random_cycles={cycles} total_cycles=%0d", cycle); $finish;',
            "  end",
            "endmodule",
            "",
        ]
    )
    return "\n".join(lines)


def command_diff(args: argparse.Namespace) -> int:
    out = fresh(args.out_dir)
    _, source, csr = load_contract(args.repo.resolve(), args.contract.resolve())
    if args.cycles < DEFAULT_CYCLES:
        raise GateError(f"cycle count {args.cycles} is below locked minimum {DEFAULT_CYCLES}")
    (out / "csr.h").write_bytes(csr)
    (out / "mycpu.h").write_text(
        "`define MS_TO_WS_BUS_WD 493\n`define WS_TO_RF_BUS_WD 38\n", encoding="ascii"
    )
    (out / "golden.v").write_bytes(renamed_module(source, b"wb_stage_golden"))
    candidate = args.rtl.read_bytes()
    (out / "candidate.v").write_bytes(
        renamed_module(candidate, b"wb_stage_candidate")
    )
    (out / "tb.sv").write_text(testbench(args.cycles, args.seed), encoding="ascii")
    verilator = shutil.which("verilator")
    if not verilator:
        raise GateError("verilator is not on PATH")
    obj = out / "obj"
    build = run(
        [
            verilator,
            "--binary",
            "--timing",
            "--top-module",
            "tb",
            "-Wall",
            "-Wno-fatal",
            "-Wno-DECLFILENAME",
            "-Wno-UNUSEDSIGNAL",
            "-DDIFFTEST_EN",
            "--x-initial",
            "0",
            "--x-assign",
            "0",
            "-I" + str(out),
            "--Mdir",
            str(obj),
            str(out / "tb.sv"),
            str(out / "golden.v"),
            str(out / "candidate.v"),
        ],
        out,
        timeout=args.timeout,
    )
    executable = obj / ("Vtb.exe" if sys.platform == "win32" else "Vtb")
    normal = (
        run([str(executable)], out, timeout=args.timeout)
        if build["returncode"] == 0 and executable.is_file()
        else {"returncode": 125, "stdout": "simulation executable missing", "timed_out": False, "elapsed_seconds": 0}
    )
    negative = (
        run([str(executable), "+negative-control"], out, timeout=args.timeout)
        if build["returncode"] == 0 and executable.is_file()
        else {"returncode": 125, "stdout": "simulation executable missing", "timed_out": False, "elapsed_seconds": 0}
    )
    mismatch = re.search(
        r"WB_MISMATCH cycle=(\d+) phase=(\d+).*?g_pc=([0-9a-fA-F]+) c_pc=([0-9a-fA-F]+)",
        str(negative["stdout"]),
    )
    first_mismatch = (
        {
            "cycle": int(mismatch.group(1)),
            "phase": int(mismatch.group(2)),
            "golden_pc": mismatch.group(3),
            "candidate_pc": mismatch.group(4),
        }
        if mismatch
        else None
    )
    normal_pass = normal["returncode"] == 0 and f"WB_DIFF_PASS random_cycles={args.cycles}" in normal["stdout"]
    negative_pass = negative["returncode"] != 0 and first_mismatch is not None
    passed = build["returncode"] == 0 and normal_pass and negative_pass
    result = summary("wb-stage-cycle-diff", passed)
    result.update(
        {
            "cycles_requested": args.cycles,
            "seed": f"0x{args.seed & 0xFFFFFFFF:08x}",
            "golden_sha256": sha256_bytes(source),
            "candidate_sha256": sha256_bytes(candidate),
            "compared_outputs": list({**OUTPUTS, **DIFF_OUTPUTS}),
            "difftest_payload_compared_while_stalled": True,
            "simulation_compile_waivers": [
                "DECLFILENAME: combined golden/candidate one-file modules",
                "UNUSEDSIGNAL: golden oracle and testbench scaffolding only; candidate standalone lint is a separate required gate with an exact allowlist",
            ],
            "build": build,
            "normal": normal,
            "negative_control": {
                "status": "pass" if negative_pass else "fail",
                "mutation": "candidate debug_ws_valid forced low while asserted",
                "first_mismatch": first_mismatch,
                "command": negative,
            },
        }
    )
    write_json(out / "summary.json", result)
    return 0 if passed else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    contract = commands.add_parser("contract")
    contract.add_argument("--repo", type=Path, default=Path("."))
    contract.add_argument("--contract", type=Path, required=True)
    contract.add_argument("--out-dir", type=Path, required=True)

    for name in ("port-check", "lint", "yosys-check"):
        command = commands.add_parser(name)
        command.add_argument("--repo", type=Path, default=Path("."))
        command.add_argument("--contract", type=Path, required=True)
        command.add_argument("--rtl", type=Path, required=True)
        command.add_argument("--profile", choices=("normal", "difftest"), required=True)
        command.add_argument("--out-dir", type=Path, required=True)

    diff = commands.add_parser("diff")
    diff.add_argument("--repo", type=Path, default=Path("."))
    diff.add_argument("--contract", type=Path, required=True)
    diff.add_argument("--rtl", type=Path, required=True)
    diff.add_argument("--out-dir", type=Path, required=True)
    diff.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    diff.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    diff.add_argument("--timeout", type=int, default=600)
    return root


def main() -> int:
    if not sys.flags.isolated:
        print("wb_stage_gate.py requires python -I", file=sys.stderr)
        return 2
    args = parser().parse_args()
    try:
        if args.command == "contract":
            return command_contract(args)
        if args.command == "port-check":
            return command_port(args)
        if args.command == "lint":
            return command_lint(args)
        if args.command == "yosys-check":
            return command_yosys(args)
        return command_diff(args)
    except (GateError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
