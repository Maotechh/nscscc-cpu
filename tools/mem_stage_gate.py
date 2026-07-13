#!/usr/bin/env python3
"""Fail-closed contract, static and cycle differential gates for mem_stage."""

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
GOLDEN_PATH = "rtl/mem_stage.v"
GOLDEN_BLOB = "ebeacf81c498b3041f5c55b16c2abe220e87ecd4"
GOLDEN_SHA256 = "86592ed33afd5dde9e944860c7088ad70e5d62ee22f72999e336a64902d881a7"
GOLDEN_SIZE = 13988
CSR_PATH = "rtl/csr.h"
CSR_BLOB = "a1d8a4389e2b45afee520d5c70d728d14404e13c"
CSR_SHA256 = "11f5550b887a2b507a5b916340069d6d127848c66c761f07d0303c7cc201026d"
CSR_SIZE = 1409
DEFAULT_CYCLES = 8192
DEFAULT_SEED = 0x0158AA8D

INPUTS = {
    "clk": 1,
    "reset": 1,
    "ws_allowin": 1,
    "es_to_ms_valid": 1,
    "es_to_ms_bus": 425,
    "div_result": 32,
    "mod_result": 32,
    "mul_result": 64,
    "excp_flush": 1,
    "ertn_flush": 1,
    "refetch_flush": 1,
    "icacop_flush": 1,
    "idle_flush": 1,
    "data_data_ok": 1,
    "dcache_miss": 1,
    "data_rdata": 32,
    "csr_pg": 1,
    "csr_da": 1,
    "csr_dmw0": 32,
    "csr_dmw1": 32,
    "csr_plv": 2,
    "csr_datm": 2,
    "disable_cache": 1,
    "lladdr": 28,
    "data_index_diff": 8,
    "data_tag_diff": 20,
    "data_offset_diff": 4,
    "data_tlb_found": 1,
    "data_tlb_index": 5,
    "data_tlb_v": 1,
    "data_tlb_d": 1,
    "data_tlb_mat": 2,
    "data_tlb_plv": 2,
    "data_tlb_ppn": 20,
}

OUTPUTS = {
    "ms_allowin": 1,
    "ms_to_ws_valid": 1,
    "ms_to_ws_bus": 493,
    "ms_to_ds_forward_bus": 39,
    "ms_to_ds_valid": 1,
    "tlb_inst_stall": 1,
    "ms_wr_tlbehi": 1,
    "ms_flush": 1,
    "data_uncache_en": 1,
    "tlb_excp_cancel_req": 1,
    "sc_cancel_req": 1,
    "data_addr_trans_en": 1,
    "dmw0_en": 1,
    "dmw1_en": 1,
    "cacop_op_mode_di": 1,
}

DIRECTED_SCENARIOS = [
    "reset_and_flush_priority",
    "alu_and_mul_div_result_selection",
    "load_alignment_and_sign_extension",
    "load_response_buffer_under_writeback_backpressure",
    "tlb_exception_and_address_translation",
    "dmw_uncached_and_sc_cancel",
]

LINT_ALLOWLIST = {
    ("UNUSEDSIGNAL", "csr_dmw0", "[28:6,2:1]"),
    ("UNUSEDSIGNAL", "csr_dmw1", "[28:6,2:1]"),
    ("UNUSEDSIGNAL", "payload_preload", ""),
}
CENTRAL_WAIVER_IDS = {
    "mem-stage-legacy-dmw0-reserved-bits",
    "mem-stage-legacy-dmw1-reserved-bits",
    "mem-stage-preload-payload-compat",
    "mem-stage-one-file-component-name",
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


def expected_ports() -> dict[str, dict[str, object]]:
    ports = {name: {"direction": "input", "width": width} for name, width in INPUTS.items()}
    ports.update(
        {name: {"direction": "output", "width": width} for name, width in OUTPUTS.items()}
    )
    return ports


def load_central_waivers(repo: Path) -> dict[str, dict[str, object]]:
    document = json.loads((repo / "lint-waivers.yml").read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("waivers"), list):
        raise GateError("invalid lint-waivers.yml schema")
    indexed = {item.get("id"): item for item in document["waivers"] if isinstance(item, dict)}
    if not CENTRAL_WAIVER_IDS.issubset(indexed):
        raise GateError("central mem_stage lint waivers are missing")
    for waiver_id in CENTRAL_WAIVER_IDS:
        waiver = indexed[waiver_id]
        if (
            waiver.get("owner") != "pipeline"
            or not waiver.get("reason")
            or not waiver.get("expires_when")
            or waiver.get("source_sha256") != sha256_file(repo / "reference/component-replacements/mem_stage.v")
        ):
            raise GateError(f"invalid central lint waiver: {waiver_id}")
    return indexed


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
    if data.get("schema_version") != 1 or data.get("target") != "mem_stage":
        raise GateError("mem_stage contract schema/target mismatch")
    if data.get("module") != "mem_stage" or data.get("golden") != identity:
        raise GateError("mem_stage golden identity mismatch")
    if data.get("bus_widths") != {
        "ES_TO_MS_BUS_WD": 425,
        "MS_TO_WS_BUS_WD": 493,
        "MS_TO_DS_FORWARD_BUS": 39,
    }:
        raise GateError("mem_stage bus width contract mismatch")
    if data.get("profile") != {"defines": [], "port_count": 49}:
        raise GateError("mem_stage profile contract mismatch")
    if data.get("ports") != expected_ports():
        raise GateError("mem_stage port contract differs from locked gate")
    if data.get("differential") != {
        "minimum_cycles": DEFAULT_CYCLES,
        "seed": "0x0158aa8d",
        "compare_all_outputs_every_phase": True,
        "negative_control_required": True,
        "directed_scenarios": DIRECTED_SCENARIOS,
    }:
        raise GateError("mem_stage differential contract mismatch")
    expected_lint = [
        {"category": category, "signal": signal, "bits": bits}
        for category, signal, bits in sorted(LINT_ALLOWLIST)
    ]
    if data.get("lint_allowlist") != expected_lint:
        raise GateError("mem_stage lint allowlist mismatch")
    load_central_waivers(repo)

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
        raise GateError("locked mem_stage.v bytes mismatch")
    if len(csr) != CSR_SIZE or sha256_bytes(csr) != CSR_SHA256:
        raise GateError("locked csr.h bytes mismatch")
    return data, source, csr


def write_headers(out: Path, csr: bytes) -> None:
    (out / "csr.h").write_bytes(csr)
    (out / "mycpu.h").write_text(
        "`define ES_TO_MS_BUS_WD 425\n"
        "`define MS_TO_WS_BUS_WD 493\n"
        "`define MS_TO_DS_FORWARD_BUS 39\n",
        encoding="ascii",
    )


def materialize_golden(out: Path, source: bytes, csr: bytes) -> Path:
    write_headers(out, csr)
    rtl = out / "mem_stage.v"
    rtl.write_bytes(source)
    return rtl


def yosys_projection(
    rtl: Path, out: Path, *, include_dir: Path | None = None
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    out.mkdir(parents=True, exist_ok=True)
    yosys = shutil.which("yosys")
    if not yosys:
        raise GateError("yosys is not on PATH")
    projection = out / "ports.json"
    flags = f"-I{include_dir.resolve().as_posix()} " if include_dir is not None else ""
    script = (
        f"read_verilog {flags}{rtl.resolve().as_posix()}; "
        f"hierarchy -check -top mem_stage; proc; write_json {projection.resolve().as_posix()}"
    )
    command = run([yosys, "-q", "-p", script], out)
    if command["returncode"] != 0:
        return {}, command
    document = json.loads(projection.read_text(encoding="utf-8"))
    try:
        ports = document["modules"]["mem_stage"]["ports"]
    except (KeyError, TypeError) as error:
        raise GateError("Yosys projection does not contain mem_stage") from error
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
    actual, command = yosys_projection(golden, out / "projection", include_dir=out)
    matched = command["returncode"] == 0 and actual == expected_ports()
    result = summary("mem-stage-contract", matched)
    result.update(
        {
            "golden_sha256": sha256_bytes(source),
            "csr_header_sha256": sha256_bytes(csr),
            "expected_count": len(expected_ports()),
            "actual_count": len(actual),
            "matched": actual == expected_ports(),
            "command": command,
        }
    )
    write_json(out / "summary.json", result)
    return 0 if matched else 1


def command_port(args: argparse.Namespace) -> int:
    out = fresh(args.out_dir)
    load_contract(args.repo.resolve(), args.contract.resolve())
    actual, command = yosys_projection(args.rtl.resolve(), out)
    matched = command["returncode"] == 0 and actual == expected_ports()
    result = summary("mem-stage-port", matched)
    result.update(
        {
            "expected_count": len(expected_ports()),
            "actual_count": len(actual),
            "matched": actual == expected_ports(),
            "rtl_sha256": sha256_file(args.rtl),
            "command": command,
        }
    )
    write_json(out / "summary.json", result)
    return 0 if matched else 1


def command_lint(args: argparse.Namespace) -> int:
    out = fresh(args.out_dir)
    repo = args.repo.resolve()
    load_contract(repo, args.contract.resolve())
    central_waivers = load_central_waivers(repo)
    verilator = shutil.which("verilator")
    if not verilator:
        raise GateError("verilator is not on PATH")
    command = run(
        [
            verilator,
            "--lint-only",
            "--top-module",
            "mem_stage",
            "-Wall",
            "-Wno-fatal",
            "-Wno-DECLFILENAME",
            str(args.rtl.resolve()),
        ],
        args.repo.resolve(),
    )
    (out / "verilator.log").write_text(command["stdout"], encoding="utf-8")
    blocks = re.findall(
        r"(?ms)^%Warning-([A-Z0-9_]+):\s+(.*?)(?=^%Warning-|^%Error|\Z)",
        str(command["stdout"]),
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
    actual = {(item["category"], item["signal"], item["bits"]) for item in diagnostics}
    unapproved = actual - LINT_ALLOWLIST
    missing = LINT_ALLOWLIST - actual
    passed = (
        command["returncode"] == 0
        and "%Error" not in command["stdout"]
        and not unapproved
        and not missing
        and len(actual) == len(diagnostics)
    )
    result = summary("mem-stage-lint", passed)
    result.update(
        {
            "diagnostics": diagnostics,
            "approved_unused": [
                {"category": category, "signal": signal, "bits": bits}
                for category, signal, bits in sorted(LINT_ALLOWLIST)
            ],
            "unapproved": [list(item) for item in sorted(unapproved)],
            "missing_expected": [list(item) for item in sorted(missing)],
            "suppressed_at_tool": [
                "DECLFILENAME only: reproducible one-file SpinalHDL component output"
            ],
            "central_waiver_ids": sorted(CENTRAL_WAIVER_IDS),
            "central_waiver_source_sha256": central_waivers[
                "mem-stage-one-file-component-name"
            ]["source_sha256"],
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
        f"read_verilog {args.rtl.resolve().as_posix()}; hierarchy -check -top mem_stage; "
        "proc; opt; check -assert"
    )
    command = run([yosys, "-q", "-p", script], args.repo.resolve())
    (out / "yosys.log").write_text(command["stdout"], encoding="utf-8")
    diagnostics = re.findall(r"(?im)^\s*(warning|error):", str(command["stdout"]))
    passed = command["returncode"] == 0 and not diagnostics
    result = summary("mem-stage-yosys", passed)
    result.update(
        {
            "diagnostics": diagnostics,
            "command": command,
            "log_sha256": sha256_file(out / "yosys.log"),
        }
    )
    write_json(out / "summary.json", result)
    return 0 if passed else 1


def renamed_module(payload: bytes, replacement: bytes) -> bytes:
    transformed, count = re.subn(
        rb"(?m)^module\s+mem_stage(?=\s|#|\()", b"module " + replacement, payload
    )
    if count != 1:
        raise GateError(f"expected one mem_stage module declaration, found {count}")
    return transformed


def declaration(kind: str, name: str, width: int) -> str:
    dimension = "" if width == 1 else f" [{width - 1}:0]"
    return f"  {kind}{dimension} {name};"


def parse_first_mismatch(output: str) -> dict[str, object] | None:
    mismatch = re.search(
        r"MEM_MISMATCH cycle=(\d+) phase=(\d+).*?g_pc=([0-9a-fA-F]+) c_pc=([0-9a-fA-F]+)",
        output,
    )
    if not mismatch:
        return None
    return {
        "cycle": int(mismatch.group(1)),
        "phase": int(mismatch.group(2)),
        "golden_pc": mismatch.group(3),
        "candidate_pc": mismatch.group(4),
        "differing_outputs": re.findall(r"MEM_OUTPUT_MISMATCH output=([a-zA-Z0-9_]+)", output),
    }


def testbench(cycles: int, seed: int) -> str:
    lines = ["module tb;", *[declaration("reg", name, width) for name, width in INPUTS.items()]]
    for prefix in ("g", "c"):
        lines.extend(declaration("wire", f"{prefix}_{name}", width) for name, width in OUTPUTS.items())
    input_connections = [f".{name}({name})" for name in INPUTS]
    for module, prefix in (("mem_stage_golden", "g"), ("mem_stage_candidate", "c")):
        connections = input_connections + [f".{name}({prefix}_{name})" for name in OUTPUTS]
        lines.append(f"  {module} dut_{prefix} (" + ",".join(connections) + ");")
    golden_vector = ",".join(f"g_{name}" for name in OUTPUTS)
    candidate_values = {
        name: (
            "(c_ms_to_ws_valid ^ (negative_control & c_ms_to_ws_valid))"
            if name == "ms_to_ws_valid"
            else f"c_{name}"
        )
        for name in OUTPUTS
    }
    candidate_vector = ",".join(candidate_values.values())
    lines.extend(
        [
            "  integer cycle; integer i; integer j; integer phase;",
            "  reg [31:0] lfsr; reg [1023:0] random_bus; reg negative_control;",
            "  task check; begin",
            f"    if ({{{golden_vector}}} !== {{{candidate_vector}}}) begin",
            '      $display("MEM_MISMATCH cycle=%0d phase=%0d g_valid=%b c_valid=%b g_allow=%b c_allow=%b g_pc=%h c_pc=%h", cycle, phase, g_ms_to_ws_valid, c_ms_to_ws_valid, g_ms_allowin, c_ms_allowin, g_ms_to_ws_bus[31:0], c_ms_to_ws_bus[31:0]);',
            *[
                f'      if (g_{name} !== {candidate_values[name]}) $display("MEM_OUTPUT_MISMATCH output={name} g=%h c=%h", g_{name}, {candidate_values[name]});'
                for name in OUTPUTS
            ],
            "      $fatal(1);",
            "    end",
            "  end endtask",
            "  task step; begin",
            "    phase=0; #2; check; #2; clk=1; phase=1; #1; check; #4; clk=0; phase=2; #1; check; cycle=cycle+1;",
            "  end endtask",
            "  task clear_controls; begin",
            "    es_to_ms_valid=0; excp_flush=0; ertn_flush=0; refetch_flush=0; icacop_flush=0; idle_flush=0; data_data_ok=0; dcache_miss=0;",
            "  end endtask",
            "  task randomize_inputs; begin",
            "    for (j=0; j<32; j=j+1) begin",
            "      lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};",
            "      random_bus[j*32 +: 32]=lfsr ^ (32'h9e3779b9*j);",
            "    end",
            "    es_to_ms_bus=random_bus[424:0]; div_result=random_bus[456:425]; mod_result=random_bus[488:457]; mul_result=random_bus[552:489];",
            "    ws_allowin=random_bus[553]; es_to_ms_valid=random_bus[554]; data_data_ok=random_bus[555]; dcache_miss=random_bus[556]; data_rdata=random_bus[588:557];",
            "    csr_pg=random_bus[589]; csr_da=random_bus[590]; csr_dmw0=random_bus[622:591]; csr_dmw1=random_bus[654:623]; csr_plv=random_bus[656:655]; csr_datm=random_bus[658:657];",
            "    disable_cache=random_bus[659]; lladdr=random_bus[687:660]; data_index_diff=random_bus[695:688]; data_tag_diff=random_bus[715:696]; data_offset_diff=random_bus[719:716];",
            "    data_tlb_found=random_bus[720]; data_tlb_index=random_bus[725:721]; data_tlb_v=random_bus[726]; data_tlb_d=random_bus[727]; data_tlb_mat=random_bus[729:728]; data_tlb_plv=random_bus[731:730]; data_tlb_ppn=random_bus[751:732];",
            "    excp_flush=&random_bus[759:752]; ertn_flush=&random_bus[767:760]; refetch_flush=&random_bus[775:768]; icacop_flush=&random_bus[783:776]; idle_flush=&random_bus[791:784];",
            "  end endtask",
            "  initial begin",
            "    clk=0; reset=0; ws_allowin=1; es_to_ms_valid=0; es_to_ms_bus=0; div_result=0; mod_result=0; mul_result=0;",
            "    excp_flush=0; ertn_flush=0; refetch_flush=0; icacop_flush=0; idle_flush=0; data_data_ok=0; dcache_miss=0; data_rdata=0;",
            "    csr_pg=0; csr_da=1; csr_dmw0=0; csr_dmw1=0; csr_plv=0; csr_datm=1; disable_cache=0; lladdr=0;",
            "    data_index_diff=0; data_tag_diff=0; data_offset_diff=0; data_tlb_found=1; data_tlb_index=0; data_tlb_v=1; data_tlb_d=1; data_tlb_mat=1; data_tlb_plv=0; data_tlb_ppn=0;",
            f"    cycle=0; phase=0; lfsr=32'h{seed & 0xFFFFFFFF:08x}; random_bus=0;",
            '    negative_control=$test$plusargs("negative-control");',
            "    reset=1; step; step; reset=0; step;",
            "    // ALU pass-through, then every mul/div result selector.",
            "    es_to_ms_bus=0; es_to_ms_bus[69]=1; es_to_ms_bus[68:64]=5'h1d; es_to_ms_bus[63:32]=32'h89abcdef; es_to_ms_bus[31:0]=32'h1c001234; es_to_ms_valid=1; step; clear_controls; step;",
            "    for (i=0; i<4; i=i+1) begin es_to_ms_bus=0; es_to_ms_bus[74:71]=(4'b1 << i); es_to_ms_bus[31:0]=32'h1c002000+i; es_to_ms_valid=1; div_result=32'h11112222; mod_result=32'h33334444; mul_result=64'h5555666677778888; step; clear_controls; step; end",
            "    // Byte/half/word load extraction, both signed and unsigned.",
            "    for (i=0; i<8; i=i+1) begin es_to_ms_bus=0; es_to_ms_bus[70]=1; es_to_ms_bus[76:75]=(i[1:0]==0)?2'b00:((i[1:0]==1)?2'b01:2'b10); es_to_ms_bus[174]=i[2]; es_to_ms_bus[33:32]=i[1:0]; es_to_ms_bus[31:0]=32'h1c003000+i; data_rdata=32'h80ff7f01; data_data_ok=1; es_to_ms_valid=1; step; clear_controls; step; end",
            "    // Capture a returning load while WB is stalled, then perturb live rdata.",
            "    ws_allowin=0; es_to_ms_bus=0; es_to_ms_bus[70]=1; es_to_ms_bus[76:75]=2'b00; es_to_ms_bus[31:0]=32'h1c004000; es_to_ms_valid=1; step; es_to_ms_valid=0; data_data_ok=1; data_rdata=32'hdeadbeef; step; data_data_ok=0; data_rdata=32'h01234567; step; ws_allowin=1; step;",
            "    // Paging/TLB exception, DMW uncached, then SC address mismatch.",
            "    csr_da=0; csr_pg=1; data_tlb_found=0; data_tlb_v=0; es_to_ms_bus=0; es_to_ms_bus[70]=1; es_to_ms_bus[214:183]=32'h81234004; es_to_ms_valid=1; step; clear_controls; step;",
            "    data_tlb_found=1; data_tlb_v=1; csr_dmw0=32'h80000001; csr_datm=1; es_to_ms_bus=0; es_to_ms_bus[70]=1; es_to_ms_bus[214:183]=32'h81234004; es_to_ms_valid=1; data_data_ok=1; step; clear_controls; step;",
            "    csr_dmw0=0; csr_da=1; csr_pg=0; csr_datm=0; lladdr=28'h1234567; data_tlb_ppn=20'h76543; es_to_ms_bus=0; es_to_ms_bus[137]=1; es_to_ms_bus[138]=1; es_to_ms_bus[214:183]=32'h00000010; es_to_ms_valid=1; step; clear_controls; step;",
            "    // Each external flush kills a resident entry even with a coincident input/response/stall.",
            "    for (i=0; i<5; i=i+1) begin",
            "      ws_allowin=0; es_to_ms_bus=0; es_to_ms_bus[70]=1; es_to_ms_bus[31:0]=32'h1c005000+i; es_to_ms_valid=1; step;",
            "      es_to_ms_bus[31:0]=32'h1c005100+i; data_data_ok=1; data_rdata=32'hcafe0000+i;",
            "      excp_flush=(i==0); ertn_flush=(i==1); refetch_flush=(i==2); icacop_flush=(i==3); idle_flush=(i==4); step;",
            "      clear_controls; ws_allowin=1; step;",
            "    end",
            f"    for (i=0; i<{cycles}; i=i+1) begin",
            "      randomize_inputs; reset=(i==2047 || i==6143); step;",
            "    end",
            "    reset=0; clear_controls; ws_allowin=1; step; step;",
            '    if (negative_control) begin $display("NEGATIVE_CONTROL_DID_NOT_FAIL"); $fatal(1); end',
            f'    $display("MEM_DIFF_PASS random_cycles={cycles} total_cycles=%0d", cycle); $finish;',
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
    write_headers(out, csr)
    (out / "golden.v").write_bytes(renamed_module(source, b"mem_stage_golden"))
    candidate = args.rtl.read_bytes()
    (out / "candidate.v").write_bytes(renamed_module(candidate, b"mem_stage_candidate"))
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
    warning_blocks = re.findall(
        r"(?ms)^%Warning-([A-Z0-9_]+):\s+(.*?)(?=^%Warning-|^make:|\Z)",
        str(build["stdout"]),
    )
    build_warnings: list[tuple[str, str]] = []
    for category, block in warning_blocks:
        signal = re.search(r"VARREF '([^']+)'", block)
        build_warnings.append((category, signal.group(1) if signal else "<unparsed>"))
    expected_build_warnings = {
        ("WIDTHTRUNC", "ms_mem_size"),
        ("WIDTHTRUNC", "ms_mul_div_op"),
    }
    actual_build_warnings = set(build_warnings)
    build_warning_policy_pass = (
        len(build_warnings) == len(actual_build_warnings)
        and actual_build_warnings == expected_build_warnings
    )
    missing = {
        "returncode": 125,
        "stdout": "simulation executable missing",
        "timed_out": False,
        "elapsed_seconds": 0,
    }
    normal = run([str(executable)], out, timeout=args.timeout) if build["returncode"] == 0 and executable.is_file() else missing
    negative = run([str(executable), "+negative-control"], out, timeout=args.timeout) if build["returncode"] == 0 and executable.is_file() else missing
    normal_first_mismatch = parse_first_mismatch(str(normal["stdout"]))
    first_mismatch = parse_first_mismatch(str(negative["stdout"]))
    normal_pass = normal["returncode"] == 0 and f"MEM_DIFF_PASS random_cycles={args.cycles}" in normal["stdout"]
    negative_pass = negative["returncode"] != 0 and first_mismatch is not None
    passed = (
        build["returncode"] == 0
        and build_warning_policy_pass
        and normal_pass
        and negative_pass
    )
    result = summary("mem-stage-cycle-diff", passed)
    result.update(
        {
            "cycles_requested": args.cycles,
            "seed": f"0x{args.seed & 0xFFFFFFFF:08x}",
            "golden_sha256": sha256_bytes(source),
            "candidate_sha256": sha256_bytes(candidate),
            "compared_outputs": list(OUTPUTS),
            "comparison_phases_per_cycle": 3,
            "directed_scenarios": DIRECTED_SCENARIOS,
            "simulation_compile_waivers": [
                "DECLFILENAME: combined golden/candidate one-file modules",
                "UNUSEDSIGNAL: golden oracle and testbench scaffolding only; candidate standalone lint is a separate required gate",
            ],
            "build": build,
            "build_warning_policy": {
                "status": "pass" if build_warning_policy_pass else "fail",
                "actual": [list(item) for item in sorted(actual_build_warnings)],
                "expected_golden_only": [list(item) for item in sorted(expected_build_warnings)],
            },
            "normal": {**normal, "first_mismatch": normal_first_mismatch},
            "negative_control": {
                "status": "pass" if negative_pass else "fail",
                "mutation": "candidate ms_to_ws_valid forced low while asserted",
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
        command.add_argument("--out-dir", type=Path, required=True)
    diff = commands.add_parser("diff")
    diff.add_argument("--repo", type=Path, default=Path("."))
    diff.add_argument("--contract", type=Path, required=True)
    diff.add_argument("--rtl", type=Path, required=True)
    diff.add_argument("--out-dir", type=Path, required=True)
    diff.add_argument("--cycles", type=lambda value: int(value, 0), default=DEFAULT_CYCLES)
    diff.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    diff.add_argument("--timeout", type=int, default=300)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return {
            "contract": command_contract,
            "port-check": command_port,
            "lint": command_lint,
            "yosys-check": command_yosys,
            "diff": command_diff,
        }[args.command](args)
    except (GateError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
