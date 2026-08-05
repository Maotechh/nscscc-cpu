#!/usr/bin/env python3
"""Fail-closed generation and differential gates for the openLA500 ALU."""

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
import tempfile
import time
from xml.etree import ElementTree


ALU_TARGET = "alu"
ALU_PORTS = {
    "alu_op": ("input", 14),
    "alu_src1": ("input", 32),
    "alu_src2": ("input", 32),
    "alu_result": ("output", 32),
}
GENERATOR_MAIN = "miku.execute.GenerateOpenLa500Alu"
GOLDEN_PATH = "rtl/alu.v"


class AluGateError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_lock(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise AluGateError(f"{path}:{line_number}: expected key=value")
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values:
            raise AluGateError(f"{path}:{line_number}: duplicate key {key}")
        values[key] = value.strip()
    return values


def require_keys(values: dict[str, str], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if not values.get(key)]
    if missing:
        raise AluGateError(f"manifest.lock is missing keys: {', '.join(missing)}")


def resolve_executable(value: str | None, fallback: Path | None = None) -> Path:
    candidate = value or (str(fallback) if fallback is not None else None)
    if not candidate:
        raise AluGateError("required executable was not supplied")
    if os.sep not in candidate and "/" not in candidate:
        candidate = shutil.which(candidate)
    if not candidate:
        raise AluGateError("required executable is not on PATH")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise AluGateError(f"executable is missing or not executable: {path}")
    return path


def checked_tool(values: dict[str, str], name: str, lock_key: str) -> Path:
    path = resolve_executable(name)
    expected = values.get(lock_key)
    if not expected or sha256_file(path) != expected:
        raise AluGateError(f"{name} binary hash differs from manifest.lock: {path}")
    return path


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> dict[str, object]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env=environment,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        returncode = result.returncode
        output = result.stdout or ""
        timed_out = False
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        returncode = 124
        timed_out = True
    except OSError as error:
        output = f"failed to start command: {error}\n"
        returncode = 125
        timed_out = False
    return {
        "argv": argv,
        "returncode": returncode,
        "stdout": output,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def git_output(repo_root: Path, args: list[str], *, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise AluGateError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout if binary else result.stdout.decode("utf-8", errors="strict").strip()


def source_files(spinal_dir: Path) -> list[Path]:
    roots = [
        spinal_dir / "build.sbt",
        spinal_dir / ".scalafmt.conf",
        spinal_dir / "project" / "build.properties",
        spinal_dir / "project" / "plugins.sbt",
    ]
    roots.extend(
        path
        for root in (spinal_dir / "project", spinal_dir / "src")
        for path in root.rglob("*")
        if path.is_file() and "target" not in path.relative_to(spinal_dir).parts
    )
    files = sorted(set(roots), key=lambda item: item.relative_to(spinal_dir).as_posix())
    missing = [str(path) for path in files if not path.is_file()]
    symlinks = [str(path) for path in files if path.is_symlink()]
    if missing or symlinks:
        raise AluGateError(f"invalid Scala source snapshot: missing={missing} symlinks={symlinks}")
    return files


def source_fingerprint(spinal_dir: Path) -> dict[str, object]:
    entries = [
        {
            "path": path.relative_to(spinal_dir).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in source_files(spinal_dir)
    ]
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"sha256": sha256_bytes(canonical), "files": entries}


def copy_scala_snapshot(spinal_dir: Path, manifest: Path, destination: Path) -> Path:
    isolated_spinal = destination / "spinal"
    for source in source_files(spinal_dir):
        target = isolated_spinal / source.relative_to(spinal_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    isolated_manifest = destination / "reference" / "manifest.lock"
    isolated_manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest, isolated_manifest)
    return isolated_spinal


def ensure_outside_repo_rtl(path: Path, repo_root: Path) -> None:
    resolved = path.resolve()
    protected = (repo_root / "rtl").resolve()
    try:
        resolved.relative_to(protected)
    except ValueError:
        return
    raise AluGateError(f"OUT_DIR may not be inside the repository RTL directory: {path}")


def warning_lines(output: str) -> list[str]:
    ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    return [
        cleaned
        for line in output.splitlines()
        if (
            cleaned := ansi.sub("", line).strip()
        )
        and re.match(r"^(?:warning\b|\[warn(?:ing)?\]|%warning(?:-[A-Za-z0-9_]+)?:)", cleaned, re.I)
    ]


def generation_environment(
    values: dict[str, str], tool_root: Path, java: Path, runtime_root: Path
) -> tuple[dict[str, str], list[str]]:
    cache_root = tool_root / values["scala_cache_dir"]
    sbt_boot = cache_root / "sbt-boot"
    ivy_home = cache_root / "ivy2"
    coursier = cache_root / "coursier" / "v1"
    for path in (sbt_boot, ivy_home, coursier):
        if not path.is_dir():
            raise AluGateError(f"locked Scala cache path is missing: {path}")
    home = runtime_root / "home"
    tmp = runtime_root / "tmp"
    jna = runtime_root / "jna"
    for path in (home, tmp, jna):
        path.mkdir(parents=True, exist_ok=False)
    environment = {
        "HOME": str(home),
        "PATH": os.pathsep.join([str(java.parent), "/usr/bin", "/bin"]),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "COURSIER_MODE": "offline",
        "COURSIER_CACHE": str(coursier),
        "JAVA_HOME": str(java.parent.parent),
        "JAVA_TOOL_OPTIONS": (
            f'-Duser.home="{home}" -Djava.io.tmpdir="{tmp}" -Djna.tmpdir="{jna}"'
        ),
    }
    jvm = [
        f"-Dsbt.global.base={runtime_root / 'sbt-global'}",
        f"-Dsbt.boot.directory={sbt_boot}",
        f"-Dsbt.ivy.home={ivy_home}",
        "-Dsbt.offline=true",
        "-Dsbt.supershell=false",
        "-Dsbt.log.noformat=true",
    ]
    return environment, jvm


def generate(args: argparse.Namespace, *, runs: int, gate_name: str) -> int:
    started = time.monotonic()
    repo_root = args.manifest.resolve().parent.parent
    out_dir = args.out_dir.resolve()
    ensure_outside_repo_rtl(out_dir, repo_root)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise AluGateError(f"generation OUT_DIR must be fresh: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    values = parse_lock(args.manifest.resolve())
    require_keys(
        values,
        (
            "team_golden_candidate",
            "scala_cache_dir",
            "sbt",
            "sbt_launch_jar_sha256",
            "java_binary_sha256",
        ),
    )
    sbt_jar = tool_root_sbt_jar(args.tool_root.resolve(), values)
    java = resolve_executable(
        str(Path(args.java_home) / "bin" / "java") if args.java_home else "java"
    )
    if sha256_file(java) != values["java_binary_sha256"]:
        raise AluGateError("Java binary hash differs from manifest.lock")
    source_before = source_fingerprint(args.spinal_dir.resolve())
    run_results: list[dict[str, object]] = []
    payloads: list[bytes] = []
    for index in range(runs):
        workspace = out_dir / "workspaces" / f"run-{index + 1}"
        isolated_spinal = copy_scala_snapshot(
            args.spinal_dir.resolve(), args.manifest.resolve(), workspace
        )
        generated = out_dir / "generated" / f"run-{index + 1}"
        generated.mkdir(parents=True)
        runtime_id = sha256_bytes(
            f"{out_dir}:{index + 1}:{os.getpid()}".encode("utf-8")
        )[:12]
        runtime = Path(tempfile.gettempdir()) / f"nag-{runtime_id}"
        if runtime.exists():
            raise AluGateError(f"short Scala runtime path already exists: {runtime}")
        environment, jvm = generation_environment(values, args.tool_root.resolve(), java, runtime)
        task = f"Compile / runMain {GENERATOR_MAIN} --out-dir {generated}"
        command = [str(java), *jvm, "-jar", str(sbt_jar), task]
        result = run_command(command, cwd=isolated_spinal, timeout=args.timeout, environment=environment)
        log_path = out_dir / f"generate-{index + 1}.log"
        log_path.write_text(str(result["stdout"]), encoding="utf-8")
        cleanup_error = None
        try:
            shutil.rmtree(runtime)
        except OSError as error:
            cleanup_error = str(error)
        runtime_cleaned = not runtime.exists()
        generated_files = sorted(path.name for path in generated.glob("*.v"))
        warnings = warning_lines(str(result["stdout"]))
        rtl = generated / "alu.v"
        passed = (
            result["returncode"] == 0
            and not warnings
            and generated_files == ["alu.v"]
            and rtl.is_file()
            and rtl.stat().st_size > 0
            and runtime_cleaned
        )
        if rtl.is_file():
            payloads.append(rtl.read_bytes())
        run_results.append(
            {
                "run": index + 1,
                "passed": passed,
                "returncode": result["returncode"],
                "timed_out": result["timed_out"],
                "elapsed_seconds": result["elapsed_seconds"],
                "warnings": warnings,
                "runtime_workspace": str(runtime),
                "runtime_workspace_cleaned": runtime_cleaned,
                "cleanup_error": cleanup_error,
                "generated_files": generated_files,
                "rtl_sha256": sha256_file(rtl) if rtl.is_file() else None,
                "rtl_size": rtl.stat().st_size if rtl.is_file() else None,
                "log": str(log_path),
                "log_sha256": sha256_file(log_path),
            }
        )
        if not passed:
            break
    reproducible = len(payloads) == runs and all(payload == payloads[0] for payload in payloads)
    source_after = source_fingerprint(args.spinal_dir.resolve())
    passed = len(run_results) == runs and all(item["passed"] for item in run_results)
    passed = bool(passed and reproducible and source_before == source_after)
    published = out_dir / "rtl" / "alu.v"
    if passed:
        published.parent.mkdir(parents=True)
        published.write_bytes(payloads[0])
    summary = {
        "schema_version": 1,
        "gate": gate_name,
        "status": "pass" if passed else "fail",
        "generated_at": now_iso(),
        "repo_head_sha": git_output(repo_root, ["rev-parse", "HEAD"]),
        "source_before": source_before,
        "source_after": source_after,
        "source_stable": source_before == source_after,
        "runs": run_results,
        "reproducible": reproducible,
        "published_rtl": str(published) if published.is_file() else None,
        "published_sha256": sha256_file(published) if published.is_file() else None,
        "published_size": published.stat().st_size if published.is_file() else None,
        "manifest_sha256": sha256_file(args.manifest.resolve()),
        "evaluator_sha256": sha256_file(Path(__file__)),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def tool_root_sbt_jar(tool_root: Path, values: dict[str, str]) -> Path:
    path = tool_root / f"sbt-{values['sbt']}" / "bin" / "sbt-launch.jar"
    if not path.is_file() or sha256_file(path) != values["sbt_launch_jar_sha256"]:
        raise AluGateError(f"SBT launcher JAR differs from manifest.lock: {path}")
    return path


def yosys_quote(path: Path) -> str:
    return '"' + str(path.resolve()).replace("\\", "/").replace('"', '\\"') + '"'


def run_yosys_script(
    values: dict[str, str], script: str, out_dir: Path, timeout: int
) -> tuple[dict[str, object], Path]:
    yosys = checked_tool(values, "yosys", "yosys_binary_sha256")
    script_path = out_dir / "gate.ys"
    log_path = out_dir / "yosys.log"
    script_path.write_text(script, encoding="utf-8")
    result = run_command(
        [str(yosys), "-l", str(log_path), "-s", str(script_path)],
        cwd=out_dir,
        timeout=timeout,
    )
    if not log_path.is_file():
        log_path.write_text(str(result["stdout"]), encoding="utf-8")
    result["warnings"] = [
        line.strip()
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.lstrip().startswith("Warning:")
    ]
    result["log"] = str(log_path)
    result["log_sha256"] = sha256_file(log_path)
    return result, log_path


def prepare_single_gate(args: argparse.Namespace, name: str) -> tuple[Path, Path, dict[str, str]]:
    out_dir = args.out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise AluGateError(f"{name} OUT_DIR must be fresh: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    rtl = args.rtl.resolve()
    if not rtl.is_file():
        raise AluGateError(f"generated ALU RTL is missing: {rtl}")
    values = parse_lock(args.manifest.resolve())
    return out_dir, rtl, values


def port_check(args: argparse.Namespace) -> int:
    out_dir, rtl, values = prepare_single_gate(args, "port-check")
    json_path = out_dir / "alu.json"
    script = (
        f"read_verilog -sv {yosys_quote(rtl)}\n"
        "hierarchy -check -top alu\n"
        "proc\n"
        f"write_json {yosys_quote(json_path)}\n"
    )
    result, _ = run_yosys_script(values, script, out_dir, args.timeout)
    actual: dict[str, tuple[str, int]] = {}
    if result["returncode"] == 0 and json_path.is_file():
        document = json.loads(json_path.read_text(encoding="utf-8"))
        ports = document.get("modules", {}).get("alu", {}).get("ports", {})
        actual = {
            name: (str(value.get("direction")), len(value.get("bits", [])))
            for name, value in ports.items()
        }
    passed = result["returncode"] == 0 and not result["warnings"] and actual == ALU_PORTS
    summary = {
        "schema_version": 1,
        "gate": "port-check",
        "status": "pass" if passed else "fail",
        "expected_ports": ALU_PORTS,
        "actual_ports": actual,
        "rtl": str(rtl),
        "rtl_sha256": sha256_file(rtl),
        "yosys": {key: value for key, value in result.items() if key != "stdout"},
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def lint(args: argparse.Namespace) -> int:
    out_dir, rtl, values = prepare_single_gate(args, "lint")
    verilator = checked_tool(values, "verilator", "verilator_binary_sha256")
    result = run_command(
        [
            str(verilator),
            "--lint-only",
            "-Wall",
            "--Wno-fatal",
            "--top-module",
            "alu",
            str(rtl),
        ],
        cwd=out_dir,
        timeout=args.timeout,
    )
    log_path = out_dir / "verilator.log"
    log_path.write_text(str(result["stdout"]), encoding="utf-8")
    warnings = warning_lines(str(result["stdout"]))
    passed = result["returncode"] == 0 and not warnings
    summary = {
        "schema_version": 1,
        "gate": "lint",
        "status": "pass" if passed else "fail",
        "rtl": str(rtl),
        "rtl_sha256": sha256_file(rtl),
        "warnings": warnings,
        "command": {key: value for key, value in result.items() if key != "stdout"},
        "log": str(log_path),
        "log_sha256": sha256_file(log_path),
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def yosys_check(args: argparse.Namespace) -> int:
    out_dir, rtl, values = prepare_single_gate(args, "yosys-check")
    script = (
        f"read_verilog -sv {yosys_quote(rtl)}\n"
        "hierarchy -check -top alu\n"
        "proc\n"
        "opt\n"
        "check -assert\n"
        "stat\n"
    )
    result, _ = run_yosys_script(values, script, out_dir, args.timeout)
    passed = result["returncode"] == 0 and not result["warnings"]
    summary = {
        "schema_version": 1,
        "gate": "yosys-check",
        "status": "pass" if passed else "fail",
        "rtl": str(rtl),
        "rtl_sha256": sha256_file(rtl),
        "yosys": {key: value for key, value in result.items() if key != "stdout"},
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def formal(args: argparse.Namespace) -> int:
    out_dir, rtl, values = prepare_single_gate(args, "formal")
    repo_root = args.manifest.resolve().parent.parent
    golden_commit = values.get("team_golden_candidate")
    if not golden_commit:
        raise AluGateError("team_golden_candidate is not locked")
    golden_payload = git_output(repo_root, ["show", f"{golden_commit}:{GOLDEN_PATH}"], binary=True)
    assert isinstance(golden_payload, bytes)
    golden = out_dir / "golden" / "alu.v"
    golden.parent.mkdir(parents=True)
    golden.write_bytes(golden_payload)
    script = (
        f"read_verilog -formal {yosys_quote(golden)}\n"
        "rename alu alu_golden\n"
        f"read_verilog -formal {yosys_quote(rtl)}\n"
        "rename alu alu_spinal\n"
        "proc\n"
        "memory\n"
        "equiv_make alu_golden alu_spinal equiv\n"
        "hierarchy -check -top equiv\n"
        "equiv_simple\n"
        "equiv_status -assert\n"
    )
    result, log_path = run_yosys_script(values, script, out_dir, args.timeout)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    proven = "Equivalence successfully proven!" in log_text
    passed = result["returncode"] == 0 and not result["warnings"] and proven
    summary = {
        "schema_version": 1,
        "gate": "formal",
        "status": "pass" if passed else "fail",
        "method": "Yosys equiv_make/equiv_simple/equiv_status -assert",
        "input_bits_exhaustively_covered": 78,
        "golden_source": f"{golden_commit}:{GOLDEN_PATH}",
        "golden_sha256": sha256_file(golden),
        "rtl": str(rtl),
        "rtl_sha256": sha256_file(rtl),
        "proven": proven,
        "yosys": {key: value for key, value in result.items() if key != "stdout"},
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def unit(args: argparse.Namespace) -> int:
    out_dir = args.out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise AluGateError(f"unit OUT_DIR must be fresh: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = args.manifest.resolve().parent.parent
    scala_out = out_dir / "scala-check"
    command = [
        sys.executable,
        "-I",
        str(repo_root / "tools" / "scala_gate.py"),
        "--manifest",
        str(args.manifest.resolve()),
        "--spinal-dir",
        str(args.spinal_dir.resolve()),
        "--tool-root",
        str(args.tool_root.resolve()),
        "--out-dir",
        str(scala_out),
        "--timeout",
        str(args.timeout),
    ]
    if args.java_home:
        command.extend(["--java-home", args.java_home])
    result = run_command(command, cwd=repo_root, timeout=args.timeout * 4)
    scala_summary_path = scala_out / "summary.json"
    scala_summary = (
        json.loads(scala_summary_path.read_text(encoding="utf-8"))
        if scala_summary_path.is_file()
        else {}
    )
    workspace = Path(str(scala_summary.get("build_workspace", "")))
    report = workspace / "spinal" / "target" / "test-reports" / (
        "TEST-miku.execute.OpenLa500AluSpec.xml"
    )
    counts: dict[str, int] = {}
    if report.is_file():
        root = ElementTree.parse(report).getroot()
        counts = {
            key: int(root.attrib.get(key, "0"))
            for key in ("tests", "failures", "errors", "skipped")
        }
    passed = bool(
        result["returncode"] == 0
        and scala_summary.get("status") == "pass"
        and counts.get("tests") == 3
        and all(counts.get(key) == 0 for key in ("failures", "errors", "skipped"))
    )
    summary = {
        "schema_version": 1,
        "gate": "unit-diff",
        "status": "pass" if passed else "fail",
        "oracle": "independent Scala model of locked shared-adder/shared-shifter masked-OR contract",
        "directed_test": "OpenLa500AluSpec directed",
        "random_seed": "0x158aa8",
        "random_vectors": 4096,
        "test_report": str(report),
        "test_report_sha256": sha256_file(report) if report.is_file() else None,
        "test_counts": counts,
        "scala_summary": str(scala_summary_path),
        "scala_summary_sha256": (
            sha256_file(scala_summary_path) if scala_summary_path.is_file() else None
        ),
        "command": {key: value for key, value in result.items() if key != "stdout"},
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def add_common(parser: argparse.ArgumentParser, *, rtl: bool = False, scala: bool = False) -> None:
    parser.add_argument("--target", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=900)
    if rtl:
        parser.add_argument("--rtl", type=Path, required=True)
    if scala:
        parser.add_argument("--spinal-dir", type=Path, required=True)
        parser.add_argument("--tool-root", type=Path, required=True)
        parser.add_argument("--java-home")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("elaborate", "generate"):
        child = subparsers.add_parser(name)
        add_common(child, scala=True)
    for name in ("port-check", "lint", "yosys-check", "formal"):
        child = subparsers.add_parser(name)
        add_common(child, rtl=True)
    child = subparsers.add_parser("unit")
    add_common(child, scala=True)
    return parser


def main() -> int:
    if not sys.flags.isolated:
        print("alu_gate.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    args = build_parser().parse_args()
    if args.target != ALU_TARGET:
        print(f"ERROR: unsupported TARGET={args.target!r}; expected 'alu'", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("ERROR: timeout must be positive", file=sys.stderr)
        return 2
    try:
        if args.command == "elaborate":
            return generate(args, runs=1, gate_name="elaborate")
        if args.command == "generate":
            return generate(args, runs=2, gate_name="generate")
        return {
            "port-check": port_check,
            "lint": lint,
            "yosys-check": yosys_check,
            "unit": unit,
            "formal": formal,
        }[args.command](args)
    except (AluGateError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
