#!/usr/bin/env python3
"""Fail-closed static and cycle lockstep gate for the active IF stage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

GOLDEN_COMMIT = "a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6"
GOLDEN_PATH = "rtl/if_stage.v"
GOLDEN_SHA256 = "9fcc66200e549825c89737b420c68e97a22af1082e370536ad67e3d72e035547"
GOLDEN_SIZE = 12929
TB_PATH = "tests/rtl/if_stage_lockstep.sv"
RANDOM_SEED = "20260713"
ALLOWED_SIM_WARNINGS = {"WIDTHTRUNC"}
ALLOWED_LINT_WARNINGS = {"DECLFILENAME", "UNUSEDSIGNAL"}

INPUTS = {
    "clk": 1, "reset": 1, "ds_allowin": 1, "br_bus": 33,
    "excp_flush": 1, "ertn_flush": 1, "refetch_flush": 1, "icacop_flush": 1,
    "ws_pc": 32, "csr_eentry": 32, "csr_era": 32, "excp_tlbrefill": 1,
    "csr_tlbrentry": 32, "has_int": 1, "idle_flush": 1,
    "inst_addr_ok": 1, "inst_data_ok": 1, "icache_miss": 1, "inst_rdata": 32,
    "csr_pg": 1, "csr_da": 1, "csr_dmw0": 32, "csr_dmw1": 32,
    "csr_plv": 2, "csr_datf": 2, "disable_cache": 1,
    "btb_ret_pc": 32, "btb_taken": 1, "btb_en": 1, "btb_index": 5,
    "inst_tlb_found": 1, "inst_tlb_v": 1, "inst_tlb_d": 1,
    "inst_tlb_mat": 2, "inst_tlb_plv": 2,
}
OUTPUTS = {
    "fs_to_ds_valid": 1, "fs_to_ds_bus": 109, "inst_valid": 1, "inst_op": 1,
    "inst_wstrb": 4, "inst_wdata": 32, "inst_uncache_en": 1,
    "tlb_excp_cancel_req": 1, "fetch_pc": 32, "fetch_en": 1,
    "inst_addr": 32, "inst_addr_trans_en": 1, "dmw0_en": 1, "dmw1_en": 1,
}


class GateError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def warning_ids(output: str) -> list[str]:
    return sorted(set(re.findall(r"%Warning-([A-Z0-9_]+)", output)))


def run(argv: list[str], cwd: Path, timeout: int = 120) -> dict[str, object]:
    started = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, check=False)
        output = p.stdout.decode("utf-8", errors="replace")
        code = p.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"").decode("utf-8", errors="replace")
        code = 124
    except OSError as exc:
        output = f"failed to start: {exc}\n"
        code = 125
    return {"argv": argv, "returncode": code, "stdout": output,
            "elapsed_seconds": round(time.monotonic() - started, 3)}


def git_blob(repo: Path, revision: str) -> bytes:
    p = subprocess.run(["git", "cat-file", "blob", revision], cwd=repo,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode:
        raise GateError(p.stderr.decode("utf-8", errors="replace"))
    return p.stdout


def parse_module_ports(source: bytes) -> dict[str, dict[str, object]]:
    text = source.decode("utf-8", errors="replace")
    match = re.search(r"module\s+if_stage\s*\((.*?)\);", text, re.S)
    if not match:
        raise GateError("if_stage module declaration missing")
    ports: dict[str, dict[str, object]] = {}
    for declaration in re.finditer(r"\b(input|output)\s+(?:wire\s+)?(?:\[[^\]]+\]\s+)?(\w+)", match.group(1)):
        direction, name = declaration.groups()
        range_match = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", declaration.group(0))
        high, low = range_match.groups() if range_match else (None, None)
        width = 1 if high is None else int(high) - int(low) + 1
        # These two legacy widths are macro-defined in mycpu.h, not literal ranges.
        if high is None and name == "br_bus":
            width = 33
        elif high is None and name == "fs_to_ds_bus":
            width = 109
        ports[name] = {"direction": direction, "width": width}
    return ports


def check_ports(candidate: bytes, golden: bytes) -> None:
    expected = {**{n: {"direction": "input", "width": w} for n, w in INPUTS.items()},
                **{n: {"direction": "output", "width": w} for n, w in OUTPUTS.items()}}
    for label, source in (("golden", golden), ("candidate", candidate)):
        ports = parse_module_ports(source)
        if ports != expected:
            raise GateError(f"{label} port contract mismatch: expected {len(expected)}, got {len(ports)}")


def prepare(repo: Path, out: Path, candidate: Path) -> tuple[Path, Path]:
    golden = git_blob(repo, f"{GOLDEN_COMMIT}:{GOLDEN_PATH}")
    if len(golden) != GOLDEN_SIZE or sha256(golden) != GOLDEN_SHA256:
        raise GateError("locked golden if_stage.v identity mismatch")
    candidate_bytes = candidate.read_bytes()
    check_ports(candidate_bytes, golden)
    out.mkdir(parents=True, exist_ok=True)
    (out / "golden.v").write_bytes(golden.replace(b"module if_stage(", b"module golden_if_stage(", 1))
    (out / "candidate.v").write_bytes(candidate_bytes)
    (out / "tb.sv").write_bytes((repo / TB_PATH).read_bytes())
    (out / "mycpu.h").write_bytes(b"`define BR_BUS_WD 33\n`define FS_TO_DS_BUS_WD 109\n")
    (out / "csr.h").write_bytes(git_blob(repo, f"{GOLDEN_COMMIT}:rtl/csr.h"))
    return out / "golden.v", out / "candidate.v"


def gate(repo: Path, candidate: Path, out: Path) -> dict[str, object]:
    golden_path, candidate_path = prepare(repo, out, candidate)
    common = ["verilator", "--binary", "--timing", "-Wno-fatal", "-I" + str(out), "--top-module", "if_stage_lockstep"]
    normal = run(common + ["--Mdir", str(out / "obj"), str(out / "tb.sv"), str(golden_path), str(candidate_path)], repo)
    normal_run = run([str(out / "obj" / "Vif_stage_lockstep"), f"+verilator+seed+{RANDOM_SEED}"], repo) if normal["returncode"] == 0 else {"returncode": 125, "stdout": "compile failed"}
    negative = run(common + ["-DNEGATIVE_CONTROL", "--Mdir", str(out / "obj-negative"), str(out / "tb.sv"), str(golden_path), str(candidate_path)], repo)
    negative_run = run([str(out / "obj-negative" / "Vif_stage_lockstep"), f"+verilator+seed+{RANDOM_SEED}"], repo) if negative["returncode"] == 0 else {"returncode": 125, "stdout": "compile failed"}
    negative_ok = negative_run["returncode"] != 0 and "IF_MISMATCH" in str(negative_run.get("stdout", ""))
    lint = run(["verilator", "--lint-only", "-Wall", "-Wno-fatal", "-I" + str(out), "--top-module", "if_stage", str(candidate_path)], repo)
    lint["warning_ids"] = warning_ids(str(lint.get("stdout", "")))
    lint["unapproved_warning_ids"] = sorted(set(lint["warning_ids"]) - ALLOWED_LINT_WARNINGS)
    normal["warning_ids"] = warning_ids(str(normal.get("stdout", "")))
    normal["unapproved_warning_ids"] = sorted(set(normal["warning_ids"]) - ALLOWED_SIM_WARNINGS)
    negative["warning_ids"] = warning_ids(str(negative.get("stdout", "")))
    negative["unapproved_warning_ids"] = sorted(set(negative["warning_ids"]) - ALLOWED_SIM_WARNINGS)
    yosys = run(["yosys", "-q", "-p", f"read_verilog {candidate_path}; hierarchy -check -top if_stage; proc; check -assert"], repo)
    result = {
        "schema_version": 1, "gate": "if-stage-cycle-diff", "candidate_sha256": sha256(candidate_path.read_bytes()),
        "golden": {"commit": GOLDEN_COMMIT, "path": GOLDEN_PATH, "sha256": GOLDEN_SHA256, "size": GOLDEN_SIZE},
        "seed": RANDOM_SEED,
        "warning_policy": {"simulation_allowed": sorted(ALLOWED_SIM_WARNINGS), "lint_allowed": sorted(ALLOWED_LINT_WARNINGS)},
        "normal": {"compile": normal, "run": normal_run, "passed": normal["returncode"] == 0 and not normal["unapproved_warning_ids"] and normal_run["returncode"] == 0 and "PASS if_stage cycle lockstep" in str(normal_run.get("stdout", ""))},
        "negative_control": {"compile": negative, "run": negative_run, "passed": negative["returncode"] == 0 and not negative["unapproved_warning_ids"] and negative_ok},
        "rtl_static": {"lint": lint, "yosys": yosys,
                        "passed": lint["returncode"] == 0 and not lint["unapproved_warning_ids"] and yosys["returncode"] == 0},
    }
    result["status"] = "pass" if result["normal"]["passed"] and negative_ok and result["rtl_static"]["passed"] else "fail"
    (out / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = gate(args.repo.resolve(), args.candidate.resolve(), args.out_dir.resolve())
    except GateError as exc:
        print(f"if-stage gate failed: {exc}")
        return 2
    print(json.dumps({"status": result["status"], "summary": str(args.out_dir / "summary.json")}))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
