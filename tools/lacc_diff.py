#!/usr/bin/env python3
"""Validate and run the locked openLA500 LACC golden/candidate lockstep."""

from __future__ import annotations

import argparse
from collections import OrderedDict
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


TARGET = "lacc"
MODULE = "lacc_core"
EXPECTED_VERILATOR = "5.020"
DEFAULT_CYCLES = 8192
DEFAULT_SEED = 0x158AA8
GOLDEN_COMMIT_KEY = "team_golden_candidate"
GOLDEN_FILES = OrderedDict(
    (
        (
            "rtl/lacc_core.v",
            "0b17abbd83cbbf088993dcb30a38981e99d600ebaeaa5c566ad4eaff75ac97b5",
        ),
        (
            "rtl/lacc_demo.v",
            "8cae09cc7f0acb0ea5cc24352704d80baf116e29f4ae372ca9eac6b63bac2ea0",
        ),
    )
)
PORTS = OrderedDict(
    (
        ("clk", {"direction": "input", "width": 1}),
        ("reset", {"direction": "input", "width": 1}),
        ("lacc_flush", {"direction": "input", "width": 1}),
        ("lacc_req_valid", {"direction": "input", "width": 1}),
        ("lacc_req_command", {"direction": "input", "width": 2}),
        ("lacc_req_imm", {"direction": "input", "width": 7}),
        ("lacc_req_rj", {"direction": "input", "width": 32}),
        ("lacc_req_rk", {"direction": "input", "width": 32}),
        ("lacc_rsp_valid", {"direction": "output", "width": 1}),
        ("lacc_rsp_rdat", {"direction": "output", "width": 32}),
        ("lacc_data_valid", {"direction": "output", "width": 1}),
        ("lacc_data_ready", {"direction": "input", "width": 1}),
        ("lacc_data_addr", {"direction": "output", "width": 32}),
        ("lacc_data_read", {"direction": "output", "width": 1}),
        ("lacc_data_wdata", {"direction": "output", "width": 32}),
        ("lacc_data_size", {"direction": "output", "width": 2}),
        ("lacc_drsp_valid", {"direction": "input", "width": 1}),
        ("lacc_drsp_rdata", {"direction": "input", "width": 32}),
    )
)
HEADER = """`ifndef MYCPU_H
`define MYCPU_H
`define LACC_OP_SIZE 3
`define LACC_OP_WIDTH $clog2(`LACC_OP_SIZE)
`endif
"""
PASS_RE = re.compile(
    r"^LACC_DIFF_PASS cycles=(?P<cycles>\d+) seed=0x(?P<seed>[0-9a-fA-F]+) "
    r"requests=(?P<requests>\d+) responses=(?P<responses>\d+) "
    r"data=(?P<data>\d+) reads=(?P<reads>\d+) writes=(?P<writes>\d+) "
    r"stalls=(?P<stalls>\d+) drsp=(?P<drsp>\d+) resets=(?P<resets>\d+) "
    r"flushes=(?P<flushes>\d+)$",
    re.MULTILINE,
)
WARNING_RE = re.compile(
    r"^%Warning-(?P<rule>[^:]+):\s+(?P<path>.+?):\d+:\d+:", re.MULTILINE
)


class LaccDiffError(RuntimeError):
    """Raised when the LACC evidence cannot support the requested claim."""


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


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = OrderedDict()
    for key, value in pairs:
        if key in result:
            raise LaccDiffError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise LaccDiffError(f"JSON input must be a regular file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LaccDiffError(f"cannot read JSON {path}: {error}") from error


def load_manifest(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise LaccDiffError(f"manifest must be a regular file: {path}")
    result: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise LaccDiffError(f"malformed manifest line {line_number}")
        key, value = line.split("=", 1)
        if key in result:
            raise LaccDiffError(f"duplicate manifest key: {key}")
        result[key] = value
    return result


def validate_contract(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise LaccDiffError("contract root must be an object")
    if document.get("schema_version") != 1:
        raise LaccDiffError("contract schema_version must be 1")
    if document.get("target") != TARGET or document.get("module") != MODULE:
        raise LaccDiffError("contract target/module differs from locked LACC boundary")
    if document.get("generated_file") != "lacc_core.v":
        raise LaccDiffError("contract generated_file must be lacc_core.v")
    golden = document.get("golden")
    if not isinstance(golden, dict) or golden.get("commit_key") != GOLDEN_COMMIT_KEY:
        raise LaccDiffError("contract golden commit key differs from lock")
    golden_files = golden.get("files")
    expected_files = [
        {"path": path, "sha256": digest} for path, digest in GOLDEN_FILES.items()
    ]
    if golden_files != expected_files:
        raise LaccDiffError("contract golden file/hash list differs from lock")
    if document.get("ports") != PORTS:
        raise LaccDiffError("contract port map differs from locked legacy interface")
    stimulus = document.get("stimulus")
    if not isinstance(stimulus, dict):
        raise LaccDiffError("contract stimulus must be an object")
    if stimulus.get("seed") != "0x158aa8":
        raise LaccDiffError("contract stimulus seed differs from lock")
    if stimulus.get("minimum_cycles") != DEFAULT_CYCLES:
        raise LaccDiffError("contract minimum cycle count differs from lock")
    if stimulus.get("legal_read_responses") is not True:
        raise LaccDiffError("contract must require legal ordered read responses")
    diff = document.get("diff")
    if not isinstance(diff, dict):
        raise LaccDiffError("contract diff must be an object")
    locked_diff = {
        "engine": "verilator_cycle_lockstep",
        "verilator": EXPECTED_VERILATOR,
        "two_state": True,
        "cycle_exact": True,
        "backpressure_stability": True,
        "negative_control": "candidate_response_valid_inversion",
    }
    if diff != locked_diff:
        raise LaccDiffError("contract differential policy differs from lock")
    return document


def git_blob(repo: Path, revision: str, path: str) -> bytes:
    command = ["git", "-C", str(repo), "cat-file", "blob", f"{revision}:{path}"]
    result = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode and (repo / ".git").is_file():
        pointer = (repo / ".git").read_text(encoding="utf-8").strip()
        if pointer.startswith("gitdir: "):
            git_dir_text = pointer.removeprefix("gitdir: ")
            if os.name != "nt":
                windows_path = re.fullmatch(r"([A-Za-z]):[\\/](.*)", git_dir_text)
                if windows_path:
                    git_dir_text = (
                        f"/mnt/{windows_path.group(1).lower()}/"
                        + windows_path.group(2).replace("\\", "/")
                    )
            git_dir = Path(git_dir_text)
            if not git_dir.is_absolute():
                git_dir = (repo / git_dir).resolve()
            result = subprocess.run(
                ["git", f"--git-dir={git_dir}", "cat-file", "blob", f"{revision}:{path}"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
    if result.returncode:
        raise LaccDiffError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def rename_golden(core: bytes, demo: bytes) -> tuple[bytes, bytes]:
    core_module = b"module lacc_core("
    demo_instance = b"lacc_demo demo("
    demo_module = b"module lacc_demo("
    if core.count(core_module) != 1 or core.count(demo_instance) != 1:
        raise LaccDiffError("golden lacc_core rename anchors are not unique")
    if demo.count(demo_module) != 1:
        raise LaccDiffError("golden lacc_demo rename anchor is not unique")
    return (
        core.replace(core_module, b"module golden_lacc_core(", 1).replace(
            demo_instance, b"golden_lacc_demo demo(", 1
        ),
        demo.replace(demo_module, b"module golden_lacc_demo(", 1),
    )


def run_command(command: list[str], *, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return {
            "argv": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        return {
            "argv": command,
            "returncode": 124,
            "stdout": stdout,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def warning_records(output: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for line in output.splitlines():
        match = WARNING_RE.match(line)
        if match:
            records.append(
                {
                    "rule": match.group("rule"),
                    "path": match.group("path"),
                    "line": line,
                }
            )
    return records


def classify_warnings(records: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    classified: dict[str, list[dict[str, str]]] = {
        "golden": [],
        "candidate": [],
        "harness": [],
        "unclassified": [],
    }
    for record in records:
        name = Path(record["path"].replace("\\", "/")).name
        if name in {"golden_lacc_core.v", "golden_lacc_demo.v"}:
            scope = "golden"
        elif name == "candidate.v":
            scope = "candidate"
        elif name in {"tb.sv", "mycpu.h", "csr.h"}:
            scope = "harness"
        else:
            scope = "unclassified"
        classified[scope].append(record)
    return classified


def parse_pass_marker(output: str) -> dict[str, int] | None:
    match = PASS_RE.search(output)
    if not match:
        return None
    return {name: int(value, 16 if name == "seed" else 10) for name, value in match.groupdict().items()}


def _fresh_output_directory(path: Path) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise LaccDiffError(f"output path must be a directory: {path}")
        if any(path.iterdir()):
            raise LaccDiffError(f"output directory must be fresh: {path}")
    path.mkdir(parents=True, exist_ok=True)


def contract_evidence(contract: Path, manifest: Path) -> dict[str, Any]:
    document = validate_contract(load_json(contract))
    lock = load_manifest(manifest)
    revision = lock.get(GOLDEN_COMMIT_KEY)
    if not revision or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise LaccDiffError(f"manifest {GOLDEN_COMMIT_KEY} must be a full Git commit")
    return {
        "contract_sha256": sha256_file(contract),
        "manifest_sha256": sha256_file(manifest),
        "golden_commit": revision,
        "golden_files": document["golden"]["files"],
        "ports": len(document["ports"]),
        "stimulus": document["stimulus"],
        "diff": document["diff"],
    }


def run_contract(args: argparse.Namespace) -> int:
    out = args.out_dir.resolve()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "gate": "lacc-contract",
        "generated_at": now_iso(),
        "status": "fail",
    }
    try:
        _fresh_output_directory(out)
        summary.update(contract_evidence(args.contract.resolve(), args.manifest.resolve()))
        summary["status"] = "pass"
        summary["counts"] = {"planned": 1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0}
    except (LaccDiffError, OSError) as error:
        summary["error"] = str(error)
        summary["counts"] = {"planned": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0}
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


def _write_log(path: Path, result: dict[str, Any]) -> None:
    path.write_text(str(result["stdout"]), encoding="utf-8", newline="\n")


def _command_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "stdout"}


def run_candidate(args: argparse.Namespace) -> int:
    repo = Path(__file__).resolve().parents[1]
    out = args.out_dir.resolve()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "gate": "lacc-golden-candidate-cycle-lockstep",
        "generated_at": now_iso(),
        "status": "fail",
        "cycles": args.cycles,
        "seed": f"0x{args.seed:x}",
    }
    try:
        if args.cycles < DEFAULT_CYCLES:
            raise LaccDiffError(f"cycles must be >= {DEFAULT_CYCLES}")
        if args.seed != DEFAULT_SEED:
            raise LaccDiffError(f"seed must remain locked at 0x{DEFAULT_SEED:x}")
        rtl = args.rtl.resolve()
        if rtl.is_symlink() or not rtl.is_file():
            raise LaccDiffError(f"candidate RTL must be a regular file: {rtl}")
        _fresh_output_directory(out)
        evidence = contract_evidence(args.contract.resolve(), args.manifest.resolve())
        summary.update(evidence)

        input_dir = out / "input"
        input_dir.mkdir()
        candidate = input_dir / "candidate.v"
        shutil.copyfile(rtl, candidate)
        candidate_hash = sha256_file(candidate)
        if candidate_hash != sha256_file(rtl):
            raise LaccDiffError("candidate RTL changed while snapshotting")
        core = git_blob(repo, evidence["golden_commit"], "rtl/lacc_core.v")
        demo = git_blob(repo, evidence["golden_commit"], "rtl/lacc_demo.v")
        if sha256_bytes(core) != GOLDEN_FILES["rtl/lacc_core.v"]:
            raise LaccDiffError("golden lacc_core SHA256 mismatch")
        if sha256_bytes(demo) != GOLDEN_FILES["rtl/lacc_demo.v"]:
            raise LaccDiffError("golden lacc_demo SHA256 mismatch")
        renamed_core, renamed_demo = rename_golden(core, demo)
        (input_dir / "golden_lacc_core.v").write_bytes(renamed_core)
        (input_dir / "golden_lacc_demo.v").write_bytes(renamed_demo)
        (input_dir / "mycpu.h").write_text(HEADER, encoding="ascii", newline="\n")
        (input_dir / "csr.h").write_text("// lacc_core consumes no CSR macro.\n", encoding="ascii")
        shutil.copyfile(repo / "tests" / "rtl" / "lacc_core_lockstep.sv", input_dir / "tb.sv")

        version = run_command([args.verilator, "--version"], cwd=out, timeout=10)
        _write_log(out / "verilator-version.log", version)
        if version["returncode"] or EXPECTED_VERILATOR not in str(version["stdout"]):
            raise LaccDiffError(f"locked Verilator {EXPECTED_VERILATOR} unavailable")

        common_lint = [args.verilator, "--lint-only", "-Wall", "-Wno-fatal", "-Wno-DECLFILENAME"]
        golden_lint = run_command(
            common_lint
            + [
                "--top-module",
                "golden_lacc_core",
                "-DHAS_LACC",
                f"-I{input_dir}",
                str(input_dir / "golden_lacc_core.v"),
                str(input_dir / "golden_lacc_demo.v"),
            ],
            cwd=out,
            timeout=args.compile_timeout,
        )
        _write_log(out / "golden-lint.log", golden_lint)
        if golden_lint["returncode"]:
            raise LaccDiffError(f"golden lint failed with exit {golden_lint['returncode']}")
        golden_warnings = warning_records(str(golden_lint["stdout"]))

        candidate_lint = run_command(
            common_lint + ["--top-module", MODULE, str(candidate)],
            cwd=out,
            timeout=args.compile_timeout,
        )
        _write_log(out / "candidate-lint.log", candidate_lint)
        if candidate_lint["returncode"]:
            raise LaccDiffError(f"candidate lint failed with exit {candidate_lint['returncode']}")
        candidate_warnings = warning_records(str(candidate_lint["stdout"]))

        obj_dir = out / "obj"
        compile_result = run_command(
            [
                args.verilator,
                "--binary",
                "--timing",
                "-Wall",
                "-Wno-fatal",
                "-Wno-DECLFILENAME",
                "--top-module",
                "lacc_core_lockstep",
                "-DHAS_LACC",
                f"-I{input_dir}",
                "--Mdir",
                str(obj_dir),
                str(input_dir / "tb.sv"),
                str(input_dir / "golden_lacc_core.v"),
                str(input_dir / "golden_lacc_demo.v"),
                str(candidate),
            ],
            cwd=out,
            timeout=args.compile_timeout,
        )
        _write_log(out / "compile.log", compile_result)
        combined_warnings = warning_records(str(compile_result["stdout"]))
        classified = classify_warnings(combined_warnings)
        summary["warnings"] = {
            "golden_lint": {
                "count": len(golden_warnings),
                "rules": sorted({item["rule"] for item in golden_warnings}),
                "records": golden_warnings,
                "classification": "historical_golden_not_candidate",
            },
            "candidate_lint": {
                "count": len(candidate_warnings),
                "rules": sorted({item["rule"] for item in candidate_warnings}),
                "records": candidate_warnings,
                "clean": not candidate_warnings,
            },
            "combined_compile": {scope: records for scope, records in classified.items()},
        }
        if compile_result["returncode"]:
            raise LaccDiffError(f"lockstep compile failed with exit {compile_result['returncode']}")
        if candidate_warnings:
            raise LaccDiffError("candidate lint emitted warnings; see candidate-lint.log")
        if classified["candidate"]:
            raise LaccDiffError("combined lockstep compile emitted candidate warnings")
        if classified["unclassified"]:
            raise LaccDiffError("combined lockstep compile emitted unclassified warnings")

        executable = obj_dir / "Vlacc_core_lockstep"
        if not executable.is_file():
            raise LaccDiffError(f"lockstep executable missing: {executable}")
        simulation_argv = [
            str(executable),
            f"+cycles={args.cycles}",
            f"+seed={args.seed:08x}",
        ]
        positive = run_command(simulation_argv, cwd=out, timeout=args.simulation_timeout)
        _write_log(out / "simulation.log", positive)
        parsed = parse_pass_marker(str(positive["stdout"]))
        if positive["returncode"] or parsed is None:
            raise LaccDiffError("positive lockstep did not reach LACC_DIFF_PASS")
        if parsed["cycles"] != args.cycles or parsed["seed"] != args.seed:
            raise LaccDiffError("positive lockstep marker differs from requested cycles/seed")

        negative = run_command(
            simulation_argv + ["+negative-control"],
            cwd=out,
            timeout=args.simulation_timeout,
        )
        _write_log(out / "negative-control.log", negative)
        negative_detected = negative["returncode"] != 0 and all(
            marker in str(negative["stdout"])
            for marker in ("LACC_MISMATCH", "negative_control=1")
        )
        if not negative_detected:
            raise LaccDiffError("negative control was not detected by the lockstep comparator")

        summary.update(
            {
                "status": "pass",
                "candidate_sha256": candidate_hash,
                "tool": {
                    "verilator": str(version["stdout"]).strip(),
                    "version_command": _command_summary(version),
                },
                "commands": {
                    "golden_lint": _command_summary(golden_lint),
                    "candidate_lint": _command_summary(candidate_lint),
                    "compile": _command_summary(compile_result),
                    "positive": _command_summary(positive),
                    "negative_control": _command_summary(negative),
                },
                "coverage": parsed,
                "negative_control": {
                    "kind": "candidate_response_valid_inversion",
                    "detected": True,
                    "returncode": negative["returncode"],
                },
                "counts": {"planned": 2, "executed": 2, "passed": 2, "failed": 0, "skipped": 0},
            }
        )
    except (LaccDiffError, OSError) as error:
        summary["error"] = str(error)
        summary.setdefault(
            "counts",
            {"planned": 2, "executed": 0, "passed": 0, "failed": 1, "skipped": 1},
        )
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    contract = subparsers.add_parser("contract", help="verify the locked LACC contract")
    contract.add_argument("--contract", type=Path, required=True)
    contract.add_argument("--manifest", type=Path, required=True)
    contract.add_argument("--out-dir", type=Path, required=True)
    contract.set_defaults(handler=run_contract)

    candidate = subparsers.add_parser("candidate", help="run golden/candidate cycle lockstep")
    candidate.add_argument("--contract", type=Path, required=True)
    candidate.add_argument("--manifest", type=Path, required=True)
    candidate.add_argument("--rtl", type=Path, required=True)
    candidate.add_argument("--out-dir", type=Path, required=True)
    candidate.add_argument("--cycles", type=lambda value: int(value, 0), default=DEFAULT_CYCLES)
    candidate.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    candidate.add_argument("--verilator", default="verilator")
    candidate.add_argument("--compile-timeout", type=int, default=180)
    candidate.add_argument("--simulation-timeout", type=int, default=120)
    candidate.set_defaults(handler=run_candidate)
    return parser


def main(argv: list[str] | None = None) -> int:
    if not sys.flags.isolated:
        print("lacc_diff.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
