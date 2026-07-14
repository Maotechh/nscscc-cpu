#!/usr/bin/env python3
"""Validate and compare the locked openLA500 performance counter."""

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
from typing import Any


MODULE = "perf_counter"
GOLDEN_PATH = "rtl/perf_counter.v"
GOLDEN_SHA256 = "a2f8f337422097699b91d217afb1eb896fa1aa02a7fdd1ed829c183de00935b6"
GOLDEN_COMMIT_KEY = "team_golden_candidate"
EXPECTED_VERILATOR = "5.020"
DEFAULT_CYCLES = 8192
DEFAULT_SEED = 0x0158AA8E
PORT_NAMES = [
    "clk",
    "reset",
    "dcache_miss",
    "icache_miss",
    "commit_inst",
    "br_inst",
    "mem_inst",
    "br_pre",
    "br_pre_error",
]
COUNTER_NAMES = [
    "dcache_miss_counter",
    "icache_miss_counter",
    "commit_inst_counter",
    "br_inst_counter",
    "mem_inst_counter",
    "br_pre_counter",
    "br_pre_error_counter",
]
PASS_RE = re.compile(
    r"^PERF_COUNTER_DIFF_PASS cycles=(?P<cycles>\d+) seed=0x(?P<seed>[0-9a-fA-F]+) "
    r"resets=(?P<resets>\d+) idle=(?P<idle>\d+) concurrent=(?P<concurrent>\d+) "
    r"wrap=(?P<wrap>\d+) events=(?P<events>[0-9,]+)$",
    re.MULTILINE,
)
WARNING_RE = re.compile(
    r"^%Warning-(?P<rule>[^:]+):\s+(?P<path>.+?):\d+:\d+:", re.MULTILINE
)
OBSERVER = """module perf_counter_observer (
  input wire clk, input wire reset,
  input wire dcache_miss, input wire icache_miss, input wire commit_inst,
  input wire br_inst, input wire mem_inst, input wire br_pre, input wire br_pre_error,
  output wire [31:0] c0, output wire [31:0] c1, output wire [31:0] c2,
  output wire [31:0] c3, output wire [31:0] c4, output wire [31:0] c5,
  output wire [31:0] c6
);
  perf_counter dut(.*);
  assign c0 = dut.dcache_miss_counter;
  assign c1 = dut.icache_miss_counter;
  assign c2 = dut.commit_inst_counter;
  assign c3 = dut.br_inst_counter;
  assign c4 = dut.mem_inst_counter;
  assign c5 = dut.br_pre_counter;
  assign c6 = dut.br_pre_error_counter;
endmodule
"""


class PerfCounterGateError(RuntimeError):
    """Raised when evidence cannot support the requested performance-counter claim."""


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


def load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise PerfCounterGateError(f"JSON input must be a regular file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PerfCounterGateError(f"cannot read JSON {path}: {error}") from error


def load_manifest(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise PerfCounterGateError(f"manifest must be a regular file: {path}")
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise PerfCounterGateError(f"malformed manifest line {line_number}")
        key, value = line.split("=", 1)
        if key in values:
            raise PerfCounterGateError(f"duplicate manifest key: {key}")
        values[key] = value
    return values


def validate_contract(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise PerfCounterGateError("contract root/schema is invalid")
    if document.get("id") != MODULE or document.get("module") != MODULE:
        raise PerfCounterGateError("contract id/module differs from locked boundary")
    if document.get("golden_path") != GOLDEN_PATH:
        raise PerfCounterGateError("contract golden path differs from lock")
    if document.get("golden_sha256") != GOLDEN_SHA256:
        raise PerfCounterGateError("contract golden hash differs from lock")
    if document.get("counter_width") != 32:
        raise PerfCounterGateError("counter width must remain 32")
    ports = document.get("ports")
    expected_ports = [
        {"name": name, "direction": "input", "width": 1} for name in PORT_NAMES
    ]
    if ports != expected_ports:
        raise PerfCounterGateError("contract port list differs from locked nine inputs")
    events = document.get("events")
    if not isinstance(events, list) or [item.get("counter") for item in events] != COUNTER_NAMES:
        raise PerfCounterGateError("contract counter list differs from locked state")
    random_policy = document.get("random")
    if random_policy != {"cycles": DEFAULT_CYCLES, "seed": "0x0158aa8e"}:
        raise PerfCounterGateError("contract random policy differs from lock")
    required = document.get("required_cases")
    if not isinstance(required, list) or set(required) != {
        "reset_priority",
        "idle_hold",
        "single_event",
        "all_events",
        "wraparound",
        "random_lockstep",
        "negative_control",
    }:
        raise PerfCounterGateError("contract required cases are incomplete")
    return document


def git_blob(repo: Path, revision: str, path: str) -> bytes:
    command = ["git", "-C", str(repo), "cat-file", "blob", f"{revision}:{path}"]
    result = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode and (repo / ".git").is_file():
        pointer = (repo / ".git").read_text(encoding="utf-8").strip()
        if pointer.startswith("gitdir: "):
            git_dir_text = pointer.removeprefix("gitdir: ")
            windows = re.fullmatch(r"([A-Za-z]):[\\/](.*)", git_dir_text)
            if windows and sys.platform != "win32":
                git_dir_text = (
                    f"/mnt/{windows.group(1).lower()}/"
                    + windows.group(2).replace("\\", "/")
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
        raise PerfCounterGateError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def rename_golden(payload: bytes) -> bytes:
    anchor = b"module perf_counter ("
    if payload.count(anchor) != 1:
        raise PerfCounterGateError("golden module rename anchor is not unique")
    return payload.replace(anchor, b"module golden_perf_counter (", 1)


def parse_ports(payload: str) -> list[dict[str, object]]:
    header_match = re.search(r"(?s)\bmodule\s+perf_counter\s*\((.*?)\);", payload)
    if not header_match:
        raise PerfCounterGateError("candidate does not define module perf_counter")
    header = header_match.group(1)
    declarations = re.findall(
        r"(?m)^\s*(input|output)\s+(?:wire\s+)?(?:\[[^]]+\]\s+)?"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*$",
        header,
    )
    return [
        {"name": name, "direction": direction, "width": 1}
        for direction, name in declarations
    ]


def verify_candidate_ports(rtl: Path, document: dict[str, Any]) -> dict[str, object]:
    if rtl.is_symlink() or not rtl.is_file():
        raise PerfCounterGateError(f"candidate RTL must be a regular file: {rtl}")
    text = rtl.read_text(encoding="utf-8")
    ports = parse_ports(text)
    if ports != document["ports"]:
        raise PerfCounterGateError(f"candidate port list differs from contract: {ports}")
    missing = [name for name in COUNTER_NAMES if not re.search(rf"\b{re.escape(name)}\b", text)]
    if missing:
        raise PerfCounterGateError(f"candidate lost named counter state: {missing}")
    return {"candidate_sha256": sha256_file(rtl), "ports": ports, "counters": COUNTER_NAMES}


def run_command(command: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
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
            "returncode": result.returncode,
            "stdout": result.stdout,
            "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return {
            "argv": command,
            "returncode": 124,
            "stdout": output,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def write_log(path: Path, result: dict[str, Any]) -> None:
    path.write_text(str(result["stdout"]), encoding="utf-8")


def command_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {key: result[key] for key in ("argv", "returncode", "timed_out", "elapsed_seconds")}


def warning_records(output: str) -> list[dict[str, str]]:
    return [match.groupdict() for match in WARNING_RE.finditer(output)]


def fresh_output(path: Path) -> None:
    if path.exists() and (path.is_symlink() or not path.is_dir() or any(path.iterdir())):
        raise PerfCounterGateError(f"output directory must be a fresh directory: {path}")
    path.mkdir(parents=True, exist_ok=True)


def contract_evidence(contract: Path, manifest: Path, repo: Path) -> dict[str, Any]:
    document = validate_contract(load_json(contract))
    lock = load_manifest(manifest)
    revision = lock.get(GOLDEN_COMMIT_KEY)
    if revision != document.get("golden_commit") or not re.fullmatch(r"[0-9a-f]{40}", revision or ""):
        raise PerfCounterGateError("manifest and contract golden commits differ")
    golden = git_blob(repo, revision, GOLDEN_PATH)
    if sha256_bytes(golden) != GOLDEN_SHA256:
        raise PerfCounterGateError("locked golden blob SHA256 mismatch")
    if parse_ports(golden.decode("utf-8")) != document["ports"]:
        raise PerfCounterGateError("golden port list differs from contract")
    return {
        "contract_sha256": sha256_file(contract),
        "manifest_sha256": sha256_file(manifest),
        "golden_commit": revision,
        "golden_path": GOLDEN_PATH,
        "golden_sha256": GOLDEN_SHA256,
        "document": document,
        "golden_blob": golden,
    }


def run_contract(args: argparse.Namespace) -> int:
    out = args.out_dir.resolve()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "gate": "perf-counter-contract",
        "generated_at": now_iso(),
        "status": "fail",
    }
    try:
        fresh_output(out)
        repo = Path(__file__).resolve().parents[1]
        evidence = contract_evidence(args.contract.resolve(), args.manifest.resolve(), repo)
        summary.update({key: value for key, value in evidence.items() if key not in {"document", "golden_blob"}})
        summary.update(
            {
                "status": "pass",
                "ports": evidence["document"]["ports"],
                "counters": COUNTER_NAMES,
                "counts": {"planned": 1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0},
            }
        )
    except (PerfCounterGateError, OSError) as error:
        summary["error"] = str(error)
        summary["counts"] = {"planned": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0}
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


def run_port_check(args: argparse.Namespace) -> int:
    out = args.out_dir.resolve()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "gate": "perf-counter-port-check",
        "generated_at": now_iso(),
        "status": "fail",
    }
    try:
        fresh_output(out)
        document = validate_contract(load_json(args.contract.resolve()))
        summary.update(verify_candidate_ports(args.rtl.resolve(), document))
        summary.update({"status": "pass", "counts": {"planned": 1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0}})
    except (PerfCounterGateError, OSError, UnicodeDecodeError) as error:
        summary["error"] = str(error)
        summary["counts"] = {"planned": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0}
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


def run_lint(args: argparse.Namespace) -> int:
    out = args.out_dir.resolve()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "gate": "perf-counter-observed-static-lint",
        "generated_at": now_iso(),
        "status": "fail",
    }
    try:
        fresh_output(out)
        document = validate_contract(load_json(args.contract.resolve()))
        candidate_info = verify_candidate_ports(args.rtl.resolve(), document)
        candidate = out / "candidate.v"
        observer = out / "observer.sv"
        shutil.copyfile(args.rtl.resolve(), candidate)
        observer.write_text(OBSERVER, encoding="ascii", newline="\n")
        version = run_command([args.verilator, "--version"], out, 10)
        write_log(out / "verilator-version.log", version)
        if version["returncode"] or EXPECTED_VERILATOR not in str(version["stdout"]):
            raise PerfCounterGateError(f"locked Verilator {EXPECTED_VERILATOR} unavailable")
        lint = run_command(
            [
                args.verilator,
                "--lint-only",
                "-Wall",
                "-Wno-DECLFILENAME",
                "--top-module",
                "perf_counter_observer",
                str(observer),
                str(candidate),
            ],
            out,
            args.timeout,
        )
        write_log(out / "lint.log", lint)
        warnings = warning_records(str(lint["stdout"]))
        if lint["returncode"] or warnings:
            raise PerfCounterGateError(
                f"observed candidate lint failed: exit={lint['returncode']} warnings={len(warnings)}"
            )
        summary.update(candidate_info)
        summary.update(
            {
                "status": "pass",
                "tool": str(version["stdout"]).strip(),
                "command": command_summary(lint),
                "warnings": warnings,
                "observation_policy": "hierarchical read of all seven otherwise-outputless counters",
                "counts": {"planned": 1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0},
            }
        )
    except (PerfCounterGateError, OSError, UnicodeDecodeError) as error:
        summary["error"] = str(error)
        summary["counts"] = {"planned": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0}
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


def verify_top_integration(rtl: Path) -> dict[str, object]:
    if rtl.is_symlink() or not rtl.is_file():
        raise PerfCounterGateError(f"top RTL must be a regular file: {rtl}")
    text = rtl.read_text(encoding="utf-8")
    if len(re.findall(r"(?m)^module\s+OpenLa500PerfCounter\s*\(", text)) != 1:
        raise PerfCounterGateError("top must define exactly one OpenLa500PerfCounter module")
    if re.search(r"(?m)^module\s+perf_counter\s*\(", text):
        raise PerfCounterGateError("top still embeds the legacy perf_counter module")
    instance = re.search(
        r"(?s)\bOpenLa500PerfCounter\s+performanceCounter\s*\((.*?)\);", text
    )
    if not instance:
        raise PerfCounterGateError("SpinalCoreBackend lacks performanceCounter instance")
    body = instance.group(1)
    expected_connections = {
        "io_clk": "aclk",
        "io_reset": "reset",
        "io_events_dataCacheMiss": "writeback_io_perf_dataCacheMiss",
        "io_events_instructionCacheMiss": "writeback_io_perf_instructionCacheMiss",
        "io_events_retired": "writeback_io_perf_retired",
        "io_events_branch": "writeback_io_perf_branch",
        "io_events_memoryAccess": "writeback_io_perf_memoryAccess",
        "io_events_predictedBranch": "writeback_io_perf_predictedBranch",
        "io_events_predictionError": "writeback_io_perf_predictionError",
    }
    missing = [
        f"{port}={signal}"
        for port, signal in expected_connections.items()
        if not re.search(rf"\.{port}\s*\(\s*{signal}\s*\)", body)
    ]
    if missing:
        raise PerfCounterGateError(f"top performance-counter connection mismatch: {missing}")
    module = re.search(r"(?s)module\s+OpenLa500PerfCounter\s*\((.*?)\nendmodule", text)
    if not module:
        raise PerfCounterGateError("cannot isolate OpenLa500PerfCounter definition")
    module_text = module.group(0)
    missing_state = [
        name
        for name in (
            "counters_dataCacheMiss",
            "counters_instructionCacheMiss",
            "counters_retired",
            "counters_branch",
            "counters_memoryAccess",
            "counters_predictedBranch",
            "counters_predictionError",
        )
        if not re.search(rf"\b{name}\b", module_text)
    ]
    if missing_state:
        raise PerfCounterGateError(f"top performance-counter state was pruned: {missing_state}")
    return {
        "rtl_sha256": sha256_file(rtl),
        "module": "OpenLa500PerfCounter",
        "instance": "performanceCounter",
        "connections": expected_connections,
        "counter_count": 7,
        "legacy_module_absent": True,
    }


def run_top_check(args: argparse.Namespace) -> int:
    out = args.out_dir.resolve()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "gate": "perf-counter-active-top-integration",
        "generated_at": now_iso(),
        "status": "fail",
    }
    try:
        fresh_output(out)
        summary.update(verify_top_integration(args.rtl.resolve()))
        summary.update({"status": "pass", "counts": {"planned": 1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0}})
    except (PerfCounterGateError, OSError, UnicodeDecodeError) as error:
        summary["error"] = str(error)
        summary["counts"] = {"planned": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0}
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


def parse_pass_marker(output: str) -> dict[str, Any] | None:
    match = PASS_RE.search(output)
    if not match:
        return None
    parsed: dict[str, Any] = {
        name: int(value, 16 if name == "seed" else 10)
        for name, value in match.groupdict().items()
        if name != "events"
    }
    parsed["events"] = [int(value) for value in match.group("events").split(",")]
    return parsed


def run_candidate(args: argparse.Namespace) -> int:
    out = args.out_dir.resolve()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "gate": "perf-counter-golden-candidate-cycle-lockstep",
        "generated_at": now_iso(),
        "status": "fail",
        "cycles": args.cycles,
        "seed": f"0x{args.seed:08x}",
    }
    try:
        if args.cycles != DEFAULT_CYCLES:
            raise PerfCounterGateError(f"cycles must remain locked at {DEFAULT_CYCLES}")
        if args.seed != DEFAULT_SEED:
            raise PerfCounterGateError(f"seed must remain locked at 0x{DEFAULT_SEED:08x}")
        fresh_output(out)
        repo = Path(__file__).resolve().parents[1]
        evidence = contract_evidence(args.contract.resolve(), args.manifest.resolve(), repo)
        input_dir = out / "input"
        input_dir.mkdir()
        candidate = input_dir / "candidate.v"
        golden = input_dir / "golden.v"
        testbench = input_dir / "tb.sv"
        shutil.copyfile(args.rtl.resolve(), candidate)
        candidate_info = verify_candidate_ports(candidate, evidence["document"])
        golden.write_bytes(rename_golden(evidence["golden_blob"]))
        shutil.copyfile(repo / "tests" / "rtl" / "perf_counter_lockstep.sv", testbench)

        version = run_command([args.verilator, "--version"], out, 10)
        write_log(out / "verilator-version.log", version)
        if version["returncode"] or EXPECTED_VERILATOR not in str(version["stdout"]):
            raise PerfCounterGateError(f"locked Verilator {EXPECTED_VERILATOR} unavailable")
        obj_dir = out / "obj"
        compile_result = run_command(
            [
                args.verilator,
                "--binary",
                "--timing",
                "-Wall",
                "-Wno-fatal",
                "-Wno-DECLFILENAME",
                "-Wno-BLKSEQ",
                "--top-module",
                "perf_counter_lockstep",
                "--Mdir",
                str(obj_dir),
                str(testbench),
                str(golden),
                str(candidate),
            ],
            out,
            args.compile_timeout,
        )
        write_log(out / "compile.log", compile_result)
        warnings = warning_records(str(compile_result["stdout"]))
        candidate_warnings = [item for item in warnings if Path(item["path"]).name == "candidate.v"]
        unknown_warnings = [
            item
            for item in warnings
            if Path(item["path"]).name not in {"candidate.v", "golden.v", "tb.sv"}
        ]
        if compile_result["returncode"]:
            raise PerfCounterGateError(f"lockstep compile failed with exit {compile_result['returncode']}")
        if candidate_warnings or unknown_warnings:
            raise PerfCounterGateError("lockstep compile emitted candidate or unclassified warnings")

        executable = obj_dir / "Vperf_counter_lockstep"
        if sys.platform == "win32":
            executable = executable.with_suffix(".exe")
        if not executable.is_file():
            raise PerfCounterGateError(f"lockstep executable missing: {executable}")
        base_command = [str(executable), f"+cycles={args.cycles}", f"+seed={args.seed:08x}"]
        positive = run_command(base_command, out, args.simulation_timeout)
        write_log(out / "simulation.log", positive)
        coverage = parse_pass_marker(str(positive["stdout"]))
        if positive["returncode"] or coverage is None:
            raise PerfCounterGateError("positive lockstep did not reach PERF_COUNTER_DIFF_PASS")
        if coverage["cycles"] != args.cycles or coverage["seed"] != args.seed:
            raise PerfCounterGateError("positive marker differs from locked stimulus")
        if (
            coverage["resets"] <= 0
            or coverage["idle"] <= 0
            or coverage["concurrent"] <= 0
            or coverage["wrap"] != 1
            or len(coverage["events"]) != 7
            or any(value <= 0 for value in coverage["events"])
        ):
            raise PerfCounterGateError("positive lockstep coverage is incomplete")

        negative = run_command(base_command + ["+negative-control"], out, args.simulation_timeout)
        write_log(out / "negative-control.log", negative)
        negative_detected = (
            negative["returncode"] != 0
            and "PERF_COUNTER_MISMATCH" in str(negative["stdout"])
            and "negative_control=1" in str(negative["stdout"])
        )
        if not negative_detected:
            raise PerfCounterGateError("negative control was not detected")

        summary.update({key: value for key, value in evidence.items() if key not in {"document", "golden_blob"}})
        summary.update(candidate_info)
        summary.update(
            {
                "status": "pass",
                "tool": str(version["stdout"]).strip(),
                "commands": {
                    "compile": command_summary(compile_result),
                    "positive": command_summary(positive),
                    "negative_control": command_summary(negative),
                },
                "warnings": warnings,
                "coverage": coverage,
                "negative_control": {
                    "kind": "candidate_dcache_counter_lsb_inversion",
                    "detected": True,
                    "returncode": negative["returncode"],
                },
                "counts": {"planned": 2, "executed": 2, "passed": 2, "failed": 0, "skipped": 0},
            }
        )
    except (PerfCounterGateError, OSError, UnicodeDecodeError) as error:
        summary["error"] = str(error)
        summary.setdefault("counts", {"planned": 2, "executed": 1, "passed": 0, "failed": 1, "skipped": 1})
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


def add_common_contract(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--contract", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    contract = commands.add_parser("contract")
    add_common_contract(contract)
    contract.add_argument("--manifest", type=Path, required=True)
    contract.add_argument("--out-dir", type=Path, required=True)
    contract.set_defaults(handler=run_contract)

    port = commands.add_parser("port-check")
    add_common_contract(port)
    port.add_argument("--rtl", type=Path, required=True)
    port.add_argument("--out-dir", type=Path, required=True)
    port.set_defaults(handler=run_port_check)

    lint = commands.add_parser("lint")
    add_common_contract(lint)
    lint.add_argument("--rtl", type=Path, required=True)
    lint.add_argument("--out-dir", type=Path, required=True)
    lint.add_argument("--verilator", default="verilator")
    lint.add_argument("--timeout", type=int, default=120)
    lint.set_defaults(handler=run_lint)

    top = commands.add_parser("top-check")
    top.add_argument("--rtl", type=Path, required=True)
    top.add_argument("--out-dir", type=Path, required=True)
    top.set_defaults(handler=run_top_check)

    candidate = commands.add_parser("candidate")
    add_common_contract(candidate)
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
        print("perf_counter_gate.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
