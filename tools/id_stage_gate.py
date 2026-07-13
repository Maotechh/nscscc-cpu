#!/usr/bin/env python3
"""Locked cycle differential gate for the active openLA500 decode stage."""

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
GOLDEN_SHA256 = "dcd896a12fda42faff9f7c1bcd43de3bbd7bb181be688b0cef21dded5e05d807"
MINIMUM_CYCLES = 8192


class GateError(RuntimeError):
    pass


def run(argv: list[str], cwd: Path, timeout: int) -> dict[str, object]:
    started = time.monotonic()
    try:
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
            "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout": result.stdout,
        }
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return {
            "argv": argv,
            "returncode": 124,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout": output,
        }


def git_blob(repo: Path, path: str) -> bytes:
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{GOLDEN_COMMIT}:{path}"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise GateError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def renamed(payload: bytes, replacement: bytes) -> bytes:
    output, count = re.subn(
        rb"(?m)^module\s+id_stage(?=\s|#|\()", b"module " + replacement, payload
    )
    if count != 1:
        raise GateError(f"expected one id_stage declaration, found {count}")
    return output


def header(lacc: bool) -> str:
    width = 353 if lacc else 350
    lacc_lines = "`define LACC_OP_WIDTH 2\n`define LACC_OP_SIZE 3\n" if lacc else ""
    return (
        "`ifndef MYCPU_H\n`define MYCPU_H\n"
        "`define BR_BUS_WD 33\n`define FS_TO_DS_BUS_WD 109\n"
        f"`define DS_TO_ES_BUS_WD {width}\n"
        "`define ES_TO_MS_BUS_WD 425\n`define MS_TO_WS_BUS_WD 493\n"
        "`define WS_TO_RF_BUS_WD 38\n`define ES_TO_DS_FORWARD_BUS 39\n"
        "`define MS_TO_DS_FORWARD_BUS 39\n"
        f"{lacc_lines}`endif\n"
    )


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--rtl", type=Path, required=True)
    parser.add_argument(
        "--profile", choices=("normal", "difftest", "lacc", "lacc-difftest"), required=True
    )
    parser.add_argument("--cycles", type=int, default=MINIMUM_CYCLES)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if not sys.flags.isolated:
        print("id_stage_gate.py requires python -I", file=sys.stderr)
        return 2
    try:
        if args.cycles < MINIMUM_CYCLES:
            raise GateError(f"cycles must be at least {MINIMUM_CYCLES}")
        repo = args.repo.resolve()
        out = args.out_dir.resolve()
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        golden = git_blob(repo, "rtl/id_stage.v")
        if sha256(golden) != GOLDEN_SHA256:
            raise GateError("locked golden id_stage.v bytes mismatch")
        candidate = args.rtl.resolve().read_bytes()
        (out / "golden.v").write_bytes(renamed(golden, b"id_stage_golden"))
        (out / "candidate.v").write_bytes(renamed(candidate, b"id_stage_candidate"))
        (out / "regfile.v").write_bytes(git_blob(repo, "rtl/regfile.v"))
        (out / "tools.v").write_bytes(git_blob(repo, "rtl/tools.v"))
        (out / "mycpu.h").write_text(
            header(args.profile.startswith("lacc")), encoding="ascii"
        )
        shutil.copyfile(repo / "tests/rtl/id_stage_lockstep.sv", out / "tb.sv")
        verilator = shutil.which("verilator")
        if not verilator:
            raise GateError("verilator is not on PATH")
        definitions = [f"-DID_RANDOM_CYCLES={args.cycles}"]
        if args.profile.startswith("lacc"):
            definitions.append("-DHAS_LACC")
        if "difftest" in args.profile:
            definitions.append("-DDIFFTEST_EN")
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
                "-Wno-UNOPTFLAT",
                "--x-initial",
                "0",
                "--x-assign",
                "0",
                *definitions,
                f"-I{out}",
                "--Mdir",
                str(out / "obj"),
                str(out / "tb.sv"),
                str(out / "golden.v"),
                str(out / "candidate.v"),
                str(out / "regfile.v"),
                str(out / "tools.v"),
            ],
            out,
            args.timeout,
        )
        executable = out / "obj" / ("Vtb.exe" if sys.platform == "win32" else "Vtb")
        normal = run([str(executable)], out, args.timeout) if executable.is_file() else {
            "returncode": 125,
            "timed_out": False,
            "elapsed_seconds": 0,
            "stdout": "simulation executable missing",
        }
        negative = run([str(executable), "+negative-control"], out, args.timeout) if executable.is_file() else {
            "returncode": 125,
            "timed_out": False,
            "elapsed_seconds": 0,
            "stdout": "simulation executable missing",
        }
        first = re.search(r"ID_MISMATCH cycle=(\d+)", str(negative["stdout"]))
        passed = (
            build["returncode"] == 0
            and normal["returncode"] == 0
            and "ID_DIFF_PASS" in str(normal["stdout"])
            and negative["returncode"] != 0
            and first is not None
        )
        summary = {
            "schema_version": 1,
            "gate": "id-stage-cycle-diff",
            "status": "pass" if passed else "fail",
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "profile": args.profile,
            "cycles_requested": args.cycles,
            "total_cycles": args.cycles + 67,
            "golden_sha256": sha256(golden),
            "candidate_sha256": sha256(candidate),
            "compared_legacy_outputs": 18,
            "compared_gpr_state": "difftest" in args.profile,
            "build": build,
            "normal": normal,
            "negative_control": {
                "status": "pass" if negative["returncode"] != 0 and first else "fail",
                "mutation": "flip candidate debug_rf_rdata1 bit zero",
                "first_mismatch_cycle": int(first.group(1)) if first else None,
                "command": negative,
            },
            "executed": 2,
            "passed": 2 if passed else 0,
            "failed": 0 if passed else 1,
            "skipped": 0,
        }
        write_json(out / "summary.json", summary)
        return 0 if passed else 1
    except (GateError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
