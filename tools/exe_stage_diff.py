#!/usr/bin/env python3
"""Run the locked a158aa8 EXE-stage cycle lockstep with Verilator 5.020."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


GOLDEN_COMMIT = "a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6"
GOLDEN_PATH = "rtl/exe_stage.v"
GOLDEN_SHA256 = "cab20e05205c6bddff19f01fd15ad4cb671144debf0836982b45b334c686f526"
EXPECTED_VERILATOR = "5.020"
PASS_MARKER = "PASS exe_stage cycle lockstep cycles=8192 seed=0x00158aa8"

HEADER = r"""`ifndef MYCPU_H
`define MYCPU_H
`define LACC_OP_SIZE 3
`define LACC_OP_WIDTH $clog2(`LACC_OP_SIZE)
`define DS_TO_ES_BUS_WD (350 \
`ifdef HAS_LACC \
+`LACC_OP_WIDTH+1 \
`endif \
)
`define ES_TO_MS_BUS_WD 425
`define ES_TO_DS_FORWARD_BUS 39
`endif
"""


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def git_blob(root: Path, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", f"{GOLDEN_COMMIT}:{path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def run(command: list[str], *, timeout: int) -> tuple[int, str]:
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def warning_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith("%Warning-")]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", type=Path, required=True)
    parser.add_argument("--profile", choices=("lacc_off", "lacc_on"), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--negative-control", action="store_true")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    rtl = args.rtl.resolve()
    out = args.out_dir.resolve()
    if rtl.is_symlink() or not rtl.is_file():
        raise SystemExit("candidate RTL must be a regular file")
    if out.exists() and any(out.iterdir()):
        raise SystemExit("output directory must be fresh")
    out.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "schema_version": 1,
        "gate": "exe-stage-cycle-lockstep",
        "generated_at": now_iso(),
        "profile": args.profile,
        "negative_control": args.negative_control,
        "status": "fail",
    }
    try:
        golden = git_blob(root, GOLDEN_PATH)
        if sha256(golden) != GOLDEN_SHA256:
            raise RuntimeError("golden exe_stage SHA256 mismatch")
        golden = golden.replace(b"module exe_stage(", b"module golden_exe_stage(", 1)
        (out / "golden_exe_stage.v").write_bytes(golden)
        (out / "alu.v").write_bytes(git_blob(root, "rtl/alu.v"))
        (out / "tools.v").write_bytes(git_blob(root, "rtl/tools.v"))
        (out / "mycpu.h").write_text(HEADER, encoding="ascii", newline="\n")
        (out / "csr.h").write_text("// No CSR macro is consumed by exe_stage.\n", encoding="ascii")
        shutil.copyfile(root / "tests" / "rtl" / "exe_stage_lockstep.sv", out / "tb.sv")

        candidate = rtl.read_bytes()
        if args.negative_control:
            original = b"assign es_to_ms_valid = area_stage_io_output_valid;"
            mutated = b"assign es_to_ms_valid = ~area_stage_io_output_valid;"
            if candidate.count(original) != 1:
                raise RuntimeError("negative-control mutation anchor is not unique")
            candidate = candidate.replace(original, mutated, 1)
        (out / "candidate.v").write_bytes(candidate)

        version_code, version_output = run(["verilator", "--version"], timeout=10)
        if version_code or EXPECTED_VERILATOR not in version_output:
            raise RuntimeError(f"locked Verilator {EXPECTED_VERILATOR} unavailable")

        command = [
            "verilator", "--binary", "--timing", "--top-module", "exe_stage_lockstep",
            f"-I{out}", "-Wall", "-Wno-fatal", "-Wno-DECLFILENAME",
            "--Mdir", str(out / "obj"),
        ]
        if args.profile == "lacc_on":
            command.append("-DHAS_LACC")
        command.extend(str(out / name) for name in (
            "tb.sv", "golden_exe_stage.v", "alu.v", "tools.v", "candidate.v"
        ))
        compile_code, compile_output = run(command, timeout=180)
        (out / "compile.log").write_text(compile_output, encoding="utf-8")
        if compile_code:
            raise RuntimeError(f"Verilator compile failed with exit {compile_code}")
        compile_warnings = warning_lines(compile_output)
        candidate_warning_paths = [
            line for line in compile_warnings if str(out / "candidate.v") in line
        ]
        if candidate_warning_paths:
            raise RuntimeError(
                "lockstep compile emitted candidate warnings: "
                + "; ".join(candidate_warning_paths[:4])
            )

        # The lockstep translation unit intentionally includes the historical
        # golden RTL and randomized testbench.  Lint the candidate separately
        # so a warning introduced by the replacement cannot be hidden by those
        # known harness warnings.
        candidate_lint = [
            "verilator", "--lint-only", "-Wall", "-Wno-fatal", "-Wno-DECLFILENAME",
            "--top-module", "exe_stage", str(out / "candidate.v"),
        ]
        candidate_lint_code, candidate_lint_output = run(candidate_lint, timeout=120)
        (out / "candidate-lint.log").write_text(candidate_lint_output, encoding="utf-8")
        candidate_warnings = warning_lines(candidate_lint_output)
        if candidate_lint_code:
            raise RuntimeError(f"candidate Verilator lint failed with exit {candidate_lint_code}")
        if candidate_warnings:
            raise RuntimeError(
                "candidate Verilator lint emitted warnings: "
                + "; ".join(candidate_warnings[:4])
            )

        binary = out / "obj" / "Vexe_stage_lockstep"
        simulation_code, simulation_output = run([str(binary)], timeout=60)
        (out / "simulation.log").write_text(simulation_output, encoding="utf-8")
        detected_mismatch = "MISMATCH cycle=" in simulation_output
        if args.negative_control:
            passed = simulation_code != 0 and detected_mismatch
        else:
            passed = simulation_code == 0 and PASS_MARKER in simulation_output
        summary.update({
            "status": "pass" if passed else "fail",
            "cycles": 8192,
            "seed": "0x00158aa8",
            "compile_exit_code": compile_code,
            "simulation_exit_code": simulation_code,
            "mismatch_detected": detected_mismatch,
            "compile_warning_count": len(compile_warnings),
            "compile_warning_ids": sorted(
                {line.split(":", 1)[0].removeprefix("%Warning-") for line in compile_warnings}
            ),
            "compile_warning_scope": "golden_or_harness_only",
            "candidate_lint_exit_code": candidate_lint_code,
            "candidate_lint_warning_count": len(candidate_warnings),
            "candidate_sha256": sha256(rtl.read_bytes()),
            "golden_sha256": GOLDEN_SHA256,
            "verilator": version_output.strip(),
        })
        write_json(out / "summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if passed else 1
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        summary["error"] = str(error)
        write_json(out / "summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
