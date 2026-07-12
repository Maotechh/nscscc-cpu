#!/usr/bin/env python3
"""Fail-closed generation and RTL gates for the openLA500 multiplier.

The multiplier is intentionally kept separate from :mod:`alu_gate`.  This
prevents a target typo from silently checking the ALU contract and keeps the
generated top-level name (``mul``) explicit in every gate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time


MUL_TARGET = "mul"
MUL_PORTS = {
    "mul_clk": ("input", 1),
    "reset": ("input", 1),
    "mul_signed": ("input", 1),
    "x": ("input", 32),
    "y": ("input", 32),
    "result": ("output", 64),
}
GENERATOR_MAIN = "openla500.execute.GenerateOpenLa500Mul"
GOLDEN_PATH = "rtl/mul.v"
SCALA_DEPENDENCY_LOCK = "scala-dependencies.lock.json"
FORMAL_PASS_BASE = "Base case for induction length 1 proven."
FORMAL_PASS_INDUCTION = "Induction step proven: SUCCESS!"
FORMAL_EXPECTED_FAILURE = "ERROR: Called with -verify and proof did fail!"


class MulGateError(RuntimeError):
    """Raised when a multiplier gate cannot establish its contract."""


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
    if not path.is_file() or path.is_symlink():
        raise MulGateError(f"manifest.lock is missing or is a symlink: {path}")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise MulGateError(f"{path}:{line_number}: expected key=value")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or key in values:
            raise MulGateError(f"{path}:{line_number}: duplicate or empty key {key!r}")
        values[key] = value
    return values


def require_keys(values: dict[str, str], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if not values.get(key)]
    if missing:
        raise MulGateError("manifest.lock is missing keys: " + ", ".join(missing))


def resolve_executable(value: str | None, fallback: Path | None = None) -> Path:
    candidate = value or (str(fallback) if fallback is not None else None)
    if not candidate:
        raise MulGateError("required executable was not supplied")
    if os.sep not in candidate and "/" not in candidate:
        candidate = shutil.which(candidate)
    if not candidate:
        raise MulGateError("required executable is not on PATH")
    path = Path(candidate).expanduser().resolve()
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise MulGateError(f"executable is missing or not executable: {path}")
    return path


def checked_tool(values: dict[str, str], name: str, lock_key: str) -> Path:
    path = resolve_executable(name)
    expected = values.get(lock_key)
    if not expected:
        raise MulGateError(f"manifest.lock is missing {lock_key}")
    actual = sha256_file(path)
    if actual != expected:
        raise MulGateError(f"{name} binary hash differs from manifest.lock: {path}")
    return path


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> dict[str, object]:
    started = time.monotonic()
    creationflags = 0
    start_new_session = os.name != "nt"
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=start_new_session,
            creationflags=creationflags,
        )
        try:
            output, _ = process.communicate(timeout=timeout)
            returncode = process.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    process.kill()
            else:
                process.kill()
            output, _ = process.communicate()
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


def resolve_git_dir(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git.resolve()
    if not dot_git.is_file():
        raise MulGateError(f"Git metadata is missing: {dot_git}")
    line = dot_git.read_text(encoding="utf-8").strip()
    if not line.startswith("gitdir:"):
        raise MulGateError(f"invalid Git worktree pointer: {dot_git}")
    raw = line.removeprefix("gitdir:").strip()
    windows_drive = re.fullmatch(r"([A-Za-z]):[\\/](.+)", raw)
    candidates: list[Path] = []
    if windows_drive and os.name != "nt":
        drive, suffix = windows_drive.groups()
        suffix = suffix.replace("\\", "/")
        candidates.extend(
            [Path(f"/mnt/{drive.lower()}/{suffix}"), Path(f"/cygdrive/{drive.lower()}/{suffix}")]
        )
    candidates.append(Path(raw) if Path(raw).is_absolute() else repo_root / raw)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    raise MulGateError(f"Git worktree metadata target is missing: {raw}")


def git_output(repo_root: Path, args: list[str], *, binary: bool = False) -> bytes | str:
    git_dir = resolve_git_dir(repo_root)
    result = subprocess.run(
        ["git", f"--git-dir={git_dir}", f"--work-tree={repo_root.resolve()}", *args],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise MulGateError(result.stderr.decode("utf-8", errors="replace").strip())
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
        if root.is_dir()
        for path in root.rglob("*")
        if path.is_file() and "target" not in path.relative_to(spinal_dir).parts
    )
    files = sorted(set(roots), key=lambda item: item.relative_to(spinal_dir).as_posix())
    missing = [str(path) for path in files if not path.is_file()]
    symlinks = [str(path) for path in files if path.is_symlink()]
    if missing or symlinks:
        raise MulGateError(f"invalid Scala source snapshot: missing={missing} symlinks={symlinks}")
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
    raise MulGateError(f"OUT_DIR may not be inside the repository RTL directory: {path}")


def warning_lines(output: str) -> list[str]:
    ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    lines: list[str] = []
    for line in output.splitlines():
        cleaned = ansi.sub("", line).strip()
        if cleaned and re.match(
            r"^(?:warning\b|\[warn(?:ing)?\]|%warning(?:-[A-Za-z0-9_]+)?:)",
            cleaned,
            re.IGNORECASE,
        ):
            lines.append(cleaned)
    return lines


def generation_environment(
    values: dict[str, str], tool_root: Path, java: Path, runtime_root: Path
) -> tuple[dict[str, str], list[str]]:
    cache_root = tool_root / values["scala_cache_dir"]
    sbt_boot = cache_root / "sbt-boot"
    ivy_home = cache_root / "ivy2"
    coursier = cache_root / "coursier" / "v1"
    for path in (sbt_boot, ivy_home, coursier):
        if not path.is_dir():
            raise MulGateError(f"locked Scala cache path is missing: {path}")
    home, tmp, jna = runtime_root / "home", runtime_root / "tmp", runtime_root / "jna"
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
        "JAVA_TOOL_OPTIONS": f'-Duser.home="{home}" -Djava.io.tmpdir="{tmp}" -Djna.tmpdir="{jna}"',
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


def tool_root_sbt_jar(tool_root: Path, values: dict[str, str]) -> Path:
    path = tool_root / f"sbt-{values['sbt']}" / "bin" / "sbt-launch.jar"
    if not path.is_file() or sha256_file(path) != values.get("sbt_launch_jar_sha256"):
        raise MulGateError(f"SBT launcher JAR differs from manifest.lock: {path}")
    return path


def load_scala_gate(repo_root: Path) -> object:
    module_path = repo_root / "tools" / "scala_gate.py"
    if not module_path.is_file() or module_path.is_symlink():
        raise MulGateError(f"canonical Scala gate is missing: {module_path}")
    spec = importlib.util.spec_from_file_location("_locked_scala_gate", module_path)
    if spec is None or spec.loader is None:
        raise MulGateError(f"cannot load canonical Scala gate: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_scala_dependencies(
    manifest: Path, tool_root: Path, values: dict[str, str]
) -> dict[str, object]:
    lock_path = manifest.parent / SCALA_DEPENDENCY_LOCK
    if lock_path.is_symlink() or not lock_path.is_file():
        raise MulGateError(f"Scala dependency lock is missing: {lock_path}")
    expected_lock_hash = values.get("scala_dependency_lock_sha256")
    actual_lock_hash = sha256_file(lock_path)
    if not expected_lock_hash or actual_lock_hash != expected_lock_hash:
        raise MulGateError("Scala dependency lock hash differs from manifest.lock")
    cache_root = tool_root / values["scala_cache_dir"]
    scala_gate = load_scala_gate(manifest.parent.parent)
    try:
        cache_manifest = scala_gate.verify_dependency_cache(cache_root, lock_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise MulGateError(str(error)) from error
    return {
        "lock_path": str(lock_path),
        "lock_sha256": actual_lock_hash,
        "cache_root": str(cache_root),
        "artifact_count": cache_manifest["artifact_count"],
        "artifacts_sha256": cache_manifest["artifacts_sha256"],
    }


def generate(args: argparse.Namespace, *, runs: int, gate_name: str) -> int:
    started = time.monotonic()
    manifest = args.manifest.resolve()
    repo_root = manifest.parent.parent
    out_dir = args.out_dir.resolve()
    ensure_outside_repo_rtl(out_dir, repo_root)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise MulGateError(f"generation OUT_DIR must be fresh: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    values = parse_lock(manifest)
    require_keys(
        values,
        (
            "scala_cache_dir",
            "scala_dependency_lock_sha256",
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
        raise MulGateError("Java binary hash differs from manifest.lock")
    dependency_before = verify_scala_dependencies(manifest, args.tool_root.resolve(), values)
    source_before = source_fingerprint(args.spinal_dir.resolve())
    run_results: list[dict[str, object]] = []
    payloads: list[bytes] = []
    for index in range(runs):
        workspace = out_dir / "workspaces" / f"run-{index + 1}"
        isolated_spinal = copy_scala_snapshot(args.spinal_dir.resolve(), manifest, workspace)
        generated = out_dir / "generated" / f"run-{index + 1}"
        generated.mkdir(parents=True)
        runtime_id = sha256_bytes(f"{out_dir}:{index + 1}:{os.getpid()}".encode())[:12]
        runtime = Path(tempfile.gettempdir()) / f"nscscc-mul-{runtime_id}"
        if runtime.exists():
            raise MulGateError(f"short Scala runtime path already exists: {runtime}")
        environment, jvm = generation_environment(values, args.tool_root.resolve(), java, runtime)
        command = [
            str(java),
            *jvm,
            "-jar",
            str(sbt_jar),
            f"Compile / runMain {GENERATOR_MAIN} --out-dir {generated}",
        ]
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
        rtl = generated / "mul.v"
        passed = bool(
            result["returncode"] == 0
            and not result["timed_out"]
            and not warnings
            and generated_files == ["mul.v"]
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
    source_after = source_fingerprint(args.spinal_dir.resolve())
    dependency_after = verify_scala_dependencies(manifest, args.tool_root.resolve(), values)
    reproducible = len(payloads) == runs and all(payload == payloads[0] for payload in payloads)
    passed = bool(
        len(run_results) == runs
        and all(item["passed"] for item in run_results)
        and reproducible
        and source_before == source_after
        and dependency_before == dependency_after
    )
    published = out_dir / "rtl" / "mul.v"
    if passed:
        published.parent.mkdir(parents=True, exist_ok=True)
        published.write_bytes(payloads[0])
    summary = {
        "schema_version": 1,
        "gate": gate_name,
        "target": MUL_TARGET,
        "generator_main": GENERATOR_MAIN,
        "status": "pass" if passed else "fail",
        "generated_at": now_iso(),
        "repo_head_sha": git_output(repo_root, ["rev-parse", "HEAD"]),
        "source_before": source_before,
        "source_after": source_after,
        "source_stable": source_before == source_after,
        "scala_dependencies_before": dependency_before,
        "scala_dependencies_after": dependency_after,
        "scala_dependencies_stable": dependency_before == dependency_after,
        "runs": run_results,
        "reproducible": reproducible,
        "published_rtl": str(published) if published.is_file() else None,
        "published_sha256": sha256_file(published) if published.is_file() else None,
        "published_size": published.stat().st_size if published.is_file() else None,
        "manifest_sha256": sha256_file(manifest),
        "evaluator_sha256": sha256_file(Path(__file__)),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def yosys_quote(path: Path) -> str:
    return '"' + str(path.resolve()).replace("\\", "/").replace('"', '\\"') + '"'


def run_yosys_script(
    values: dict[str, str], script: str, out_dir: Path, timeout: int
) -> tuple[dict[str, object], Path]:
    yosys = checked_tool(values, "yosys", "yosys_binary_sha256")
    version = run_command([str(yosys), "-V"], cwd=out_dir, timeout=timeout)
    version_text = str(version["stdout"]).strip()
    if (
        version["returncode"] != 0
        or version["timed_out"]
        or not re.search(rf"Yosys\s+{re.escape(values.get('yosys', ''))}(?:\s|$)", version_text)
    ):
        raise MulGateError(f"locked Yosys version check failed: {version_text}")
    script_path, log_path = out_dir / "gate.ys", out_dir / "yosys.log"
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
    result["tool"] = {
        "path": str(yosys),
        "sha256": sha256_file(yosys),
        "version": version_text,
    }
    result["log"] = str(log_path)
    result["log_sha256"] = sha256_file(log_path)
    return result, log_path


def prepare_single_gate(
    args: argparse.Namespace, name: str
) -> tuple[Path, Path, dict[str, str], dict[str, object]]:
    out_dir = args.out_dir.resolve()
    if out_dir.exists():
        if not out_dir.is_dir():
            raise MulGateError(f"{name} OUT_DIR must be a directory: {out_dir}")
        if any(out_dir.iterdir()):
            raise MulGateError(f"{name} OUT_DIR must be fresh: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_rtl = Path(args.rtl).expanduser()
    if raw_rtl.is_symlink() or not raw_rtl.is_file():
        raise MulGateError(f"generated multiplier RTL is missing: {raw_rtl}")
    source = raw_rtl.resolve()
    source_sha256 = sha256_file(source)
    source_size = source.stat().st_size
    payload = source.read_bytes()
    if sha256_bytes(payload) != source_sha256 or len(payload) != source_size:
        raise MulGateError("generated multiplier RTL changed while creating the gate snapshot")
    if source.is_symlink() or not source.is_file() or sha256_file(source) != source_sha256:
        raise MulGateError("generated multiplier RTL changed while creating the gate snapshot")
    snapshot = out_dir / "input" / "mul.v"
    snapshot.parent.mkdir()
    snapshot.write_bytes(payload)
    identity = {
        "source": str(source),
        "snapshot": str(snapshot),
        "sha256": source_sha256,
        "size": source_size,
    }
    return out_dir, snapshot, parse_lock(args.manifest.resolve()), identity


def gate_input_evidence(identity: dict[str, object]) -> dict[str, object]:
    source = Path(str(identity["source"]))
    snapshot = Path(str(identity["snapshot"]))
    expected_hash = str(identity["sha256"])
    expected_size = int(identity["size"])
    source_stable = bool(
        not source.is_symlink()
        and source.is_file()
        and source.stat().st_size == expected_size
        and sha256_file(source) == expected_hash
    )
    snapshot_stable = bool(
        not snapshot.is_symlink()
        and snapshot.is_file()
        and snapshot.stat().st_size == expected_size
        and sha256_file(snapshot) == expected_hash
    )
    return {**identity, "source_stable": source_stable, "snapshot_stable": snapshot_stable}


def gate_provenance(args: argparse.Namespace) -> dict[str, object]:
    manifest = args.manifest.resolve()
    repo_root = manifest.parent.parent
    return {
        "repository_head": git_output(repo_root, ["rev-parse", "HEAD"]),
        "manifest": str(manifest),
        "manifest_sha256": sha256_file(manifest),
        "evaluator_sha256": sha256_file(Path(__file__)),
    }


def port_check(args: argparse.Namespace) -> int:
    out_dir, rtl, values, identity = prepare_single_gate(args, "port-check")
    json_path = out_dir / "mul.json"
    script = (
        f"read_verilog -sv {yosys_quote(rtl)}\n"
        "hierarchy -check -top mul\n"
        "proc\n"
        f"write_json {yosys_quote(json_path)}\n"
    )
    result, _ = run_yosys_script(values, script, out_dir, args.timeout)
    actual: dict[str, tuple[str, int]] = {}
    if result["returncode"] == 0 and json_path.is_file():
        document = json.loads(json_path.read_text(encoding="utf-8"))
        ports = document.get("modules", {}).get("mul", {}).get("ports", {})
        actual = {
            name: (str(value.get("direction")), len(value.get("bits", [])))
            for name, value in ports.items()
        }
    input_evidence = gate_input_evidence(identity)
    passed = bool(
        result["returncode"] == 0
        and not result["timed_out"]
        and not result["warnings"]
        and actual == MUL_PORTS
        and input_evidence["source_stable"]
        and input_evidence["snapshot_stable"]
    )
    summary = {
        "schema_version": 1,
        "gate": "port-check",
        "target": MUL_TARGET,
        "status": "pass" if passed else "fail",
        "expected_ports": MUL_PORTS,
        "actual_ports": actual,
        "rtl": str(rtl),
        "rtl_sha256": sha256_file(rtl),
        "input": input_evidence,
        "yosys": {key: value for key, value in result.items() if key != "stdout"},
        "provenance": gate_provenance(args),
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def lint(args: argparse.Namespace) -> int:
    out_dir, rtl, values, identity = prepare_single_gate(args, "lint")
    verilator = checked_tool(values, "verilator", "verilator_binary_sha256")
    version = run_command([str(verilator), "--version"], cwd=out_dir, timeout=args.timeout)
    version_text = str(version["stdout"]).strip()
    result = run_command(
        [str(verilator), "--lint-only", "-Wall", "--Wno-fatal", "--top-module", "mul", str(rtl)],
        cwd=out_dir,
        timeout=args.timeout,
    )
    log_path = out_dir / "verilator.log"
    log_path.write_text(str(result["stdout"]), encoding="utf-8")
    warnings = warning_lines(str(result["stdout"]))
    input_evidence = gate_input_evidence(identity)
    passed = bool(
        result["returncode"] == 0
        and not result["timed_out"]
        and version["returncode"] == 0
        and not version["timed_out"]
        and re.search(
            rf"Verilator\s+{re.escape(values.get('verilator', ''))}(?:\s|$)", version_text
        )
        and not warnings
        and input_evidence["source_stable"]
        and input_evidence["snapshot_stable"]
    )
    summary = {
        "schema_version": 1,
        "gate": "lint",
        "target": MUL_TARGET,
        "status": "pass" if passed else "fail",
        "rtl": str(rtl),
        "rtl_sha256": sha256_file(rtl),
        "input": input_evidence,
        "warnings": warnings,
        "command": {key: value for key, value in result.items() if key != "stdout"},
        "tool": {
            "path": str(verilator),
            "sha256": sha256_file(verilator),
            "version": version_text,
        },
        "provenance": gate_provenance(args),
        "log": str(log_path),
        "log_sha256": sha256_file(log_path),
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def yosys_check(args: argparse.Namespace) -> int:
    out_dir, rtl, values, identity = prepare_single_gate(args, "yosys-check")
    script = (
        f"read_verilog -sv {yosys_quote(rtl)}\n"
        "hierarchy -check -top mul\n"
        "proc\n"
        "opt\n"
        "check -assert\n"
        "stat\n"
    )
    result, _ = run_yosys_script(values, script, out_dir, args.timeout)
    input_evidence = gate_input_evidence(identity)
    passed = bool(
        result["returncode"] == 0
        and not result["timed_out"]
        and not result["warnings"]
        and input_evidence["source_stable"]
        and input_evidence["snapshot_stable"]
    )
    summary = {
        "schema_version": 1,
        "gate": "yosys-check",
        "target": MUL_TARGET,
        "status": "pass" if passed else "fail",
        "rtl": str(rtl),
        "rtl_sha256": sha256_file(rtl),
        "input": input_evidence,
        "yosys": {key: value for key, value in result.items() if key != "stdout"},
        "provenance": gate_provenance(args),
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def formal_harness(top: str, observed_result: str) -> str:
    """Build the 2-state candidate contract harness.

    ``seen`` is the only initialized state.  Candidate and model result state
    remain arbitrary until the first active capture, matching the historical
    contract instead of silently treating an uninitialized result as zero.
    """

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", top):
        raise MulGateError(f"invalid formal top name: {top!r}")
    if observed_result not in {
        "result",
        "(result ^ 64'b1)",
        "(reset ? (result ^ 64'b1) : result)",
    }:
        raise MulGateError("unsupported formal negative-control expression")
    return f"""module {top}(
  input wire mul_clk,
  input wire reset,
  input wire mul_signed,
  input wire [31:0] x,
  input wire [31:0] y
);
  wire [63:0] result;
  wire signed [31:0] signed_x = x;
  wire signed [31:0] signed_y = y;
  wire signed [63:0] signed_product = signed_x * signed_y;
  wire [63:0] unsigned_product = x * y;
  wire [63:0] model_product = mul_signed ? signed_product : unsigned_product;
  wire [63:0] observed_result = {observed_result};
  reg [63:0] expected;
  reg seen;

  initial seen = 1'b0;

  mul dut(
    .mul_clk(mul_clk), .reset(reset), .mul_signed(mul_signed),
    .x(x), .y(y), .result(result)
  );

  always @(posedge mul_clk) begin
    if (!reset) begin
      expected <= model_product;
      seen <= 1'b1;
    end
  end

  always @* begin
    if (seen)
      assert(observed_result == expected);
  end
endmodule
"""


def formal_positive_passed(result: dict[str, object], log_text: str) -> bool:
    return bool(
        result.get("returncode") == 0
        and not result.get("timed_out")
        and not result.get("warnings")
        and FORMAL_PASS_BASE in log_text
        and FORMAL_PASS_INDUCTION in log_text
        and FORMAL_EXPECTED_FAILURE not in log_text
        and "SKIP" not in log_text.upper()
    )


def formal_negative_detected(result: dict[str, object], log_text: str) -> bool:
    return bool(
        result.get("returncode") != 0
        and not result.get("timed_out")
        and not result.get("warnings")
        and FORMAL_EXPECTED_FAILURE in log_text
        and FORMAL_PASS_INDUCTION not in log_text
        and "SKIP" not in log_text.upper()
    )


def formal(args: argparse.Namespace) -> int:
    out_dir, rtl, values, identity = prepare_single_gate(args, "formal")
    cases = (
        (
            "positive",
            "mul_contract_formal",
            "result",
            "sat -seq 2 -tempinduct -maxsteps 4 -prove-asserts -verify",
            formal_positive_passed,
        ),
        (
            "negative-active",
            "mul_contract_negative_active",
            "(result ^ 64'b1)",
            "sat -seq 3 -prove-asserts -verify",
            formal_negative_detected,
        ),
        (
            "negative-hold",
            "mul_contract_negative_hold",
            "(reset ? (result ^ 64'b1) : result)",
            "sat -seq 3 -prove-asserts -verify",
            formal_negative_detected,
        ),
    )
    results: list[dict[str, object]] = []
    for case_name, top, observed_result, sat_command, classifier in cases:
        case_dir = out_dir / case_name
        case_dir.mkdir()
        harness = case_dir / "harness.sv"
        harness.write_text(formal_harness(top, observed_result), encoding="ascii")
        script = (
            f"read_verilog -formal -sv {yosys_quote(rtl)} {yosys_quote(harness)}\n"
            f"hierarchy -check -top {top}\n"
            f"prep -top {top} -flatten\n"
            "check -assert\n"
            f"{sat_command}\n"
        )
        command_result, log_path = run_yosys_script(values, script, case_dir, args.timeout)
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        case_passed = classifier(command_result, log_text)
        results.append(
            {
                "case": case_name,
                "passed": case_passed,
                "expected": "proof" if case_name == "positive" else "counterexample",
                "harness": str(harness),
                "harness_sha256": sha256_file(harness),
                "command": {key: value for key, value in command_result.items() if key != "stdout"},
            }
        )

    input_evidence = gate_input_evidence(identity)
    passed = bool(
        all(bool(item["passed"]) for item in results)
        and input_evidence["source_stable"]
        and input_evidence["snapshot_stable"]
    )
    summary = {
        "schema_version": 1,
        "gate": "mul-candidate-contract-formal",
        "target": MUL_TARGET,
        "status": "pass" if passed else "fail",
        "rtl": str(rtl),
        "rtl_sha256": sha256_file(rtl),
        "input": input_evidence,
        "proof_scope": {
            "semantics": "2-state sequential",
            "unknown_policy": "comparison starts after first !reset capture",
            "properties": ["signed_unsigned_active_capture", "synchronous_reset_hold"],
            "unbounded": True,
            "golden_formal_equivalence": False,
            "claim": "candidate satisfies the locked mathematical/timing contract only",
        },
        "negative_controls": ["active_product_bit_flip", "reset_hold_bit_flip"],
        "counts": {
            "planned": len(results),
            "executed": len(results),
            "passed": sum(bool(item["passed"]) for item in results),
            "failed": sum(not bool(item["passed"]) for item in results),
            "skipped": 0,
        },
        "cases": results,
        "evaluator_sha256": sha256_file(Path(__file__)),
        "provenance": gate_provenance(args),
        "tool": results[0]["command"].get("tool") if results else None,
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
        add_common(subparsers.add_parser(name), scala=True)
    for name in ("port-check", "lint", "yosys-check", "formal"):
        add_common(subparsers.add_parser(name), rtl=True)
    return parser


def main() -> int:
    if not sys.flags.isolated:
        print("mul_gate.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    args = build_parser().parse_args()
    if args.target != MUL_TARGET:
        print(f"ERROR: unsupported TARGET={args.target!r}; expected 'mul'", file=sys.stderr)
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
            "formal": formal,
        }[args.command](args)
    except (MulGateError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
