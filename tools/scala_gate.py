#!/usr/bin/env python3
"""Run the locked, evidence-producing Scala gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Iterable
from xml.etree import ElementTree


TASKS = (
    ("scalafmt", "scalafmtCheckAll"),
    ("compile", "Compile / compile"),
    ("test-compile", "Test / compile"),
    ("test", "Test / test"),
)
DEPENDENCY_LOCK_NAME = "scala-dependencies.lock.json"
DEPENDENCY_CACHE_DIRS = {
    "coursier": Path("coursier") / "v1",
    "sbt_boot": Path("sbt-boot"),
    "ivy": Path("ivy2"),
}
DEPENDENCY_SUFFIXES = (".jar", ".pom", ".xml", ".properties")
REQUIRED_WARNING_CATEGORIES = ("WIDTH", "UNOPTFLAT", "CMPCONST", "UNSIGNED")
PROHIBITED_WARNING_CATEGORIES = frozenset(
    {
        "WIDTH",
        "LATCH",
        "UNDRIVEN",
        "UNOPTFLAT",
        "MULTIDRIVEN",
        "SYNCASYNCNET",
        "CLKDATA",
    }
)


def parse_lock(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{number}: expected key=value")
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values:
            raise ValueError(f"{path}:{number}: duplicate key: {key}")
        values[key] = value.strip()
    return values


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def dependency_cache_manifest(cache_root: Path) -> dict[str, object]:
    artifacts: list[dict[str, object]] = []
    for cache_id, relative_root in DEPENDENCY_CACHE_DIRS.items():
        root = cache_root / relative_root
        if not root.is_dir():
            raise ValueError(f"Scala dependency cache directory is missing: {root}")
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            if path.is_symlink():
                raise ValueError(f"Scala dependency cache must not contain symlinks: {path}")
            if not path.is_file() or not path.name.endswith(DEPENDENCY_SUFFIXES):
                continue
            artifacts.append(
                {
                    "cache": cache_id,
                    "path": path.relative_to(root).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    if not artifacts:
        raise ValueError(f"Scala dependency cache contains no semantic artifacts: {cache_root}")
    canonical = json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": 1,
        "artifact_count": len(artifacts),
        "artifacts_sha256": sha256_bytes(canonical),
        "artifacts": artifacts,
    }


def tree_fingerprint(root: Path, *, excluded_names: frozenset[str] = frozenset()) -> dict[str, object]:
    if not root.is_dir():
        raise ValueError(f"tool tree is missing: {root}")
    entries: list[dict[str, object]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.name in excluded_names:
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append({"path": relative, "kind": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            entries.append(
                {
                    "path": relative,
                    "kind": "file",
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "sha256": sha256_bytes(canonical),
        "entry_count": len(entries),
    }


def verify_dependency_cache(cache_root: Path, lock_path: Path) -> dict[str, object]:
    if not lock_path.is_file():
        raise ValueError(f"Scala dependency lock is missing: {lock_path}")
    try:
        expected = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Scala dependency lock is invalid: {lock_path}: {error}") from error
    actual = dependency_cache_manifest(cache_root)
    if expected != actual:
        raise ValueError(
            "Scala dependency cache differs from scala-dependencies.lock.json: "
            f"expected={expected.get('artifacts_sha256') if isinstance(expected, dict) else None} "
            f"actual={actual['artifacts_sha256']}"
        )
    return actual


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def source_inputs(spinal_dir: Path) -> list[Path]:
    required = [
        spinal_dir / "build.sbt",
        spinal_dir / ".scalafmt.conf",
        spinal_dir / "project" / "build.properties",
        spinal_dir / "project" / "plugins.sbt",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError(f"Scala gate inputs are missing: {missing}")
    forbidden_runner_options = [spinal_dir / ".sbtopts", spinal_dir / ".jvmopts"]
    present_options = [str(path) for path in forbidden_runner_options if path.exists()]
    if present_options:
        raise ValueError(f"project-local SBT/JVM runner options are forbidden: {present_options}")
    discovered = [
        *required,
        *(
            path
            for root in (spinal_dir / "project", spinal_dir / "src")
            for path in root.rglob("*")
            if path.is_file() and "target" not in path.relative_to(spinal_dir).parts
        ),
    ]
    inputs = sorted(set(discovered), key=lambda path: path.relative_to(spinal_dir).as_posix())
    symlinks = [str(path) for path in inputs if path.is_symlink()]
    if symlinks:
        raise ValueError(f"Scala gate inputs must not be symlinks: {symlinks}")
    return inputs


def source_fingerprint(spinal_dir: Path) -> dict[str, object]:
    inputs = source_inputs(spinal_dir)
    entries = [
        {
            "path": path.relative_to(spinal_dir).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in inputs
    ]
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"sha256": sha256_bytes(canonical), "files": entries}


def copy_source_snapshot(
    spinal_dir: Path,
    manifest_path: Path,
    workspace_root: Path,
) -> tuple[Path, Path]:
    isolated_spinal = workspace_root / "spinal"
    isolated_manifest = workspace_root / "reference" / "manifest.lock"
    if workspace_root.exists():
        raise ValueError(f"isolated Scala workspace already exists: {workspace_root}")
    for source in source_inputs(spinal_dir):
        target = isolated_spinal / source.relative_to(spinal_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    isolated_manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest_path, isolated_manifest)
    return isolated_spinal, isolated_manifest


def git_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    head = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise ValueError(f"cannot resolve repository HEAD: {result.stderr.strip()}")
    return head


def require_lock(lock: dict[str, str], keys: Iterable[str]) -> None:
    missing = [key for key in keys if not lock.get(key)]
    if missing:
        raise ValueError(f"manifest.lock is missing: {', '.join(missing)}")


def resolve_executable(value: str | None, fallback: Path | None = None) -> Path:
    candidate = value or (str(fallback) if fallback is not None else None)
    if candidate is None:
        raise ValueError("no executable path was supplied")
    if os.sep not in candidate and "/" not in candidate:
        located = shutil.which(candidate)
        if located is None:
            raise ValueError(f"executable not found on PATH: {candidate}")
        candidate = located
    path = Path(candidate).expanduser()
    if not path.is_file():
        raise ValueError(f"executable does not exist: {path}")
    if not os.access(path, os.X_OK):
        raise ValueError(f"file is not executable: {path}")
    return path.resolve()


def java_binary(java_home: str | None) -> Path:
    if java_home:
        name = "java.exe" if os.name == "nt" else "java"
        return resolve_executable(str(Path(java_home) / "bin" / name))
    return resolve_executable("java")


def clean_environment(
    path_entries: list[Path], extra: dict[str, str], *, home: Path | None = None
) -> dict[str, str]:
    home_text = str(home) if home is not None else os.environ.get("HOME")
    if not home_text:
        raise ValueError("an isolated HOME is required for the Scala gate")
    clean_home = Path(home_text)
    clean_home.mkdir(parents=True, exist_ok=True)
    environment = {
        "HOME": str(clean_home),
        "PATH": os.pathsep.join([*(str(path) for path in path_entries), "/usr/bin", "/bin"]),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
    }
    environment.update(extra)
    return environment


def trusted_java_tool_options(properties: dict[str, Path]) -> str:
    """Encode the fixed JVM paths inherited by SBT's forked test JVM."""
    options: list[str] = []
    for key in sorted(properties):
        value = str(properties[key].resolve())
        if any(character in value for character in ('"', "\n", "\r")):
            raise ValueError(f"JVM isolation path cannot be encoded safely: {value}")
        options.append(f'-D{key}="{value}"')
    return " ".join(options)


def run_capture(command: list[str], cwd: Path, environment: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=os.name == "posix",
    )
    try:
        stdout, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            stdout, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            stdout, _ = process.communicate()
        raise subprocess.TimeoutExpired(command, timeout, output=stdout or "") from error
    return subprocess.CompletedProcess(command, process.returncode, stdout or "", None)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def scala_test_outcome(output: str) -> dict[str, int]:
    patterns = {
        "total": r"Total number of tests run:\s+(\d+)",
        "succeeded": r"Tests:\s+succeeded\s+(\d+)",
        "failed": r"Tests:\s+succeeded\s+\d+,\s+failed\s+(\d+)",
        "canceled": r"Tests:.*?canceled\s+(\d+)",
        "ignored": r"Tests:.*?ignored\s+(\d+)",
        "pending": r"Tests:.*?pending\s+(\d+)",
        "aborted_suites": r"Suites:\s+completed\s+\d+,\s+aborted\s+(\d+)",
    }
    outcome: dict[str, int] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        outcome[key] = int(match.group(1)) if match else -1
    return outcome


def scala_test_outcome_passed(outcome: dict[str, int]) -> bool:
    return bool(
        outcome.get("total", -1) > 0
        and outcome.get("succeeded") == outcome["total"]
        and all(
            outcome.get(key) == 0
            for key in ("failed", "canceled", "ignored", "pending", "aborted_suites")
        )
    )


def path_is_within(path: str, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def scala_test_runtime_isolation(
    report_root: Path, expected_properties: dict[str, Path]
) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    dispatch_paths: list[str] = []
    for report_path in sorted(report_root.glob("TEST-*.xml")):
        try:
            root = ElementTree.parse(report_path).getroot()
        except (ElementTree.ParseError, OSError) as error:
            reports.append(
                {
                    "path": str(report_path),
                    "sha256": sha256(report_path) if report_path.is_file() else None,
                    "passed": False,
                    "error": str(error),
                }
            )
            continue
        properties = {
            item.attrib.get("name", ""): item.attrib.get("value", "")
            for item in root.findall("./properties/property")
        }
        mismatches = {
            key: {"expected": str(expected.resolve()), "actual": properties.get(key)}
            for key, expected in expected_properties.items()
            if properties.get(key) != str(expected.resolve())
        }
        dispatch_path = properties.get("jnidispatch.path")
        if dispatch_path:
            dispatch_paths.append(dispatch_path)
        reports.append(
            {
                "path": str(report_path),
                "sha256": sha256(report_path),
                "property_mismatches": mismatches,
                "jnidispatch_path": dispatch_path,
                "passed": not mismatches,
            }
        )
    jna_root = expected_properties["jna.tmpdir"]
    dispatch_paths_within_jna = bool(dispatch_paths) and all(
        path_is_within(path, jna_root) for path in dispatch_paths
    )
    return {
        "report_count": len(reports),
        "reports": reports,
        "jnidispatch_paths": dispatch_paths,
        "jnidispatch_paths_within_jna_tmpdir": dispatch_paths_within_jna,
        "passed": bool(reports)
        and all(bool(report["passed"]) for report in reports)
        and dispatch_paths_within_jna,
    }


def forbidden_warning_lines(output: str) -> list[str]:
    ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    warnings: list[str] = []
    for line in output.splitlines():
        cleaned = ansi.sub("", line).strip()
        if re.match(
            r"^(?:\[(?:warning|warn)\]|warning\b|%warning(?:-[a-z0-9_]+)?\b)",
            cleaned,
            re.IGNORECASE,
        ):
            warnings.append(cleaned)
    return warnings


def compiled_source_count(output: str, target_fragment: str) -> int:
    counts = []
    for line in output.splitlines():
        match = re.search(r"compiling\s+(\d+)\s+Scala sources?\s+to\s+(.*)", line)
        if match and target_fragment in match.group(2).replace("\\", "/"):
            counts.append(int(match.group(1)))
    return sum(counts)


def verilator_script_policy(script: Path) -> dict[str, object]:
    text = script.read_text(encoding="utf-8", errors="replace")
    parse_error = None
    try:
        tokens = shlex.split(text, comments=True, posix=True)
    except ValueError as error:
        tokens = []
        parse_error = str(error)
    effective = {
        match.group(2).upper(): match.group(1).lower()
        for token in tokens
        if (match := re.fullmatch(r"-(Wno|Wwarn)-([A-Za-z0-9_-]+)", token, re.IGNORECASE))
    }
    required = {
        category: effective.get(category, "missing") for category in REQUIRED_WARNING_CATEGORIES
    }
    prohibited_suppressions = sorted(
        category
        for category, state in effective.items()
        if state == "wno"
        and (category in PROHIBITED_WARNING_CATEGORIES or "CDC" in category)
    )
    wall_enabled = any(token.lower() == "-wall" for token in tokens)
    response_file_tokens: list[str] = []
    rtl_inputs: list[Path] = []
    include_dirs: list[Path] = []
    for index, token in enumerate(tokens):
        if token in {"-f", "-F"}:
            response_file_tokens.append(
                f"{token} {tokens[index + 1]}" if index + 1 < len(tokens) else f"{token} <missing>"
            )
        elif token.startswith("@"):
            response_file_tokens.append(token)
        elif token.lower().endswith(".vlt"):
            response_file_tokens.append(token)
        elif token.lower().endswith((".v", ".sv")):
            candidate = Path(token)
            rtl_inputs.append(candidate if candidate.is_absolute() else script.parent / candidate)
        elif token.startswith("+incdir+"):
            for directory in token.removeprefix("+incdir+").split("+"):
                candidate = Path(directory)
                include_dirs.append(
                    candidate if candidate.is_absolute() else script.parent / candidate
                )
        elif token.startswith("-I") and len(token) > 2:
            if index > 0 and tokens[index - 1] in {"-CFLAGS", "-LDFLAGS"}:
                continue
            candidate = Path(token[2:])
            include_dirs.append(candidate if candidate.is_absolute() else script.parent / candidate)

    discovered_vlt = sorted(str(path) for path in script.parent.rglob("*.vlt"))
    missing_rtl_inputs = sorted(str(path) for path in rtl_inputs if not path.is_file())
    inline_waivers: list[dict[str, object]] = []
    inline_pattern = re.compile(r"verilator\s+lint_(?:off|save)\b", re.IGNORECASE)
    include_directive_pattern = re.compile(r"`include\b([^\r\n]*)")
    literal_include_pattern = re.compile(r"\s*\"([^\"]+)\"")
    pending = [path.resolve() for path in rtl_inputs if path.is_file()]
    scanned: set[Path] = set()
    missing_includes: list[dict[str, object]] = []
    unresolved_include_directives: list[dict[str, object]] = []
    while pending:
        rtl_path = pending.pop()
        if rtl_path in scanned:
            continue
        scanned.add(rtl_path)
        rtl_text = rtl_path.read_text(encoding="utf-8", errors="replace")
        for match in inline_pattern.finditer(rtl_text):
            inline_waivers.append(
                {
                    "path": str(rtl_path),
                    "line": rtl_text.count("\n", 0, match.start()) + 1,
                    "text": " ".join(match.group(0).split()),
                }
            )
        for match in include_directive_pattern.finditer(rtl_text):
            literal = literal_include_pattern.fullmatch(match.group(1).strip())
            if literal is None:
                unresolved_include_directives.append(
                    {
                        "path": str(rtl_path),
                        "line": rtl_text.count("\n", 0, match.start()) + 1,
                        "directive": match.group(0).strip(),
                    }
                )
                continue
            include_name = literal.group(1)
            candidates = [rtl_path.parent / include_name]
            candidates.extend(directory / include_name for directory in include_dirs)
            included = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
            if included is None:
                missing_includes.append(
                    {
                        "path": str(rtl_path),
                        "line": rtl_text.count("\n", 0, match.start()) + 1,
                        "include": include_name,
                    }
                )
            elif included not in scanned:
                pending.append(included)
    passed = (
        parse_error is None
        and wall_enabled
        and all(value == "wwarn" for value in required.values())
        and not prohibited_suppressions
        and not response_file_tokens
        and not discovered_vlt
        and not missing_rtl_inputs
        and not missing_includes
        and not unresolved_include_directives
        and not inline_waivers
    )
    return {
        "path": str(script),
        "sha256": sha256(script),
        "wall_enabled": wall_enabled,
        "effective_warning_flags": required,
        "all_effective_warning_flags": effective,
        "prohibited_suppressions": prohibited_suppressions,
        "parse_error": parse_error,
        "response_file_tokens": response_file_tokens,
        "discovered_vlt_files": discovered_vlt,
        "missing_rtl_inputs": missing_rtl_inputs,
        "include_dirs": sorted(str(path.resolve()) for path in include_dirs),
        "scanned_rtl_inputs": sorted(str(path) for path in scanned),
        "missing_includes": missing_includes,
        "unresolved_include_directives": unresolved_include_directives,
        "inline_waivers": inline_waivers,
        "passed": passed,
    }


def acquire_gate_lock(out_dir: Path, run_id: str) -> Path:
    lock_path = out_dir / ".scala-check.lock"
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "pid": os.getpid(),
        "created_at": now_iso(),
        "evaluator_sha256": sha256(Path(__file__)),
    }
    try:
        with lock_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as error:
        raise ValueError(
            f"Scala gate lock already exists: {lock_path}; use a fresh OUT_DIR after interruption"
        ) from error
    return lock_path


def simulation_artifacts(simulation_workspace: Path) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    for path in sorted(
        (
            candidate
            for candidate in simulation_workspace.rglob("*")
            if candidate.is_file()
            and (
                candidate.suffix in {".v", ".sv"}
                or candidate.name == "verilatorScript.sh"
                or os.access(candidate, os.X_OK)
            )
        ),
        key=lambda candidate: candidate.as_posix(),
    ):
        artifacts.append(
            {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": sha256(path),
                "executable": os.access(path, os.X_OK),
            }
        )
    return artifacts


def main() -> int:
    if not sys.flags.isolated:
        print("scala_gate.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--spinal-dir", type=Path, required=True)
    parser.add_argument("--tool-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--sbt")
    parser.add_argument("--java-home")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    started = time.monotonic()
    manifest_path = args.manifest.resolve()
    spinal_dir = args.spinal_dir.resolve()
    tool_root = args.tool_root.resolve()
    out_dir = args.out_dir.resolve()
    repo_root = manifest_path.parent.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{time.time_ns()}-{os.getpid()}"
    try:
        gate_lock = acquire_gate_lock(out_dir, run_id)
    except ValueError as error:
        print(f"scala-check refused concurrent/stale OUT_DIR: {error}", file=sys.stderr)
        return 1
    summary_path = out_dir / "summary.json"
    summary: dict[str, object] = {
        "schema_version": 1,
        "gate": "scala-check",
        "status": "fail",
        "generated_at": now_iso(),
        "planned": len(TASKS),
        "executed": 0,
        "passed": 0,
        "failed": 0,
        "skipped": len(TASKS),
        "tasks": [],
    }
    runtime_workspace: Path | None = None

    try:
        lock = parse_lock(manifest_path)
        require_lock(
            lock,
            (
                "sbt",
                "sbt_script_sha256",
                "jdk",
                "java_binary_sha256",
                "verilator",
                "verilator_binary_sha256",
                "verilator_engine_sha256",
                "verilator_runtime_sha256",
                "scala",
                "spinalhdl",
                "scalatest",
                "sbt_scalafmt",
                "scalafmt",
                "sbt_launch_jar_sha256",
                "jdk_modules_sha256",
                "scala_cache_dir",
                "scala_dependency_lock_sha256",
                "verilator_include_tree_sha256",
                "jdk_include_tree_sha256",
                "jdk_lib_tree_sha256",
                "gpp_binary_sha256",
                "make_binary_sha256",
                "perl_binary_sha256",
                "sh_binary_sha256",
                "host_ld_binary_sha256",
                "host_ar_binary_sha256",
                "python",
                "python_binary_sha256",
            ),
        )
        default_sbt = tool_root / f"sbt-{lock['sbt']}" / "bin" / "sbt"
        sbt = resolve_executable(args.sbt, default_sbt)
        java = java_binary(args.java_home)
        verilator = resolve_executable("verilator")
        verilator_engine = Path("/usr/bin/verilator_bin")
        verilator_runtime = Path("/usr/share/verilator/include/verilated.cpp")
        verilator_include = Path("/usr/share/verilator/include")
        sbt_launch_jar = sbt.parent / "sbt-launch.jar"
        jdk_modules = java.parent.parent / "lib" / "modules"
        jdk_include = java.parent.parent / "include"
        jdk_lib = java.parent.parent / "lib"
        native_tools = {
            "gpp": resolve_executable("g++"),
            "make": resolve_executable("make"),
            "perl": resolve_executable("perl"),
            "sh": resolve_executable("sh"),
            "ld": resolve_executable("ld"),
            "ar": resolve_executable("ar"),
        }
        python = Path(sys.executable).resolve()

        if sha256(sbt) != lock["sbt_script_sha256"]:
            raise ValueError(f"SBT launcher hash does not match manifest.lock: {sbt}")
        if sha256(java) != lock["java_binary_sha256"]:
            raise ValueError(f"Java binary hash does not match manifest.lock: {java}")
        if sha256(verilator) != lock["verilator_binary_sha256"]:
            raise ValueError(f"Verilator binary hash does not match manifest.lock: {verilator}")
        if sha256(python) != lock["python_binary_sha256"]:
            raise ValueError(f"Python evaluator binary hash does not match manifest.lock: {python}")
        if platform.python_version() != lock["python"]:
            raise ValueError(f"Python evaluator version does not match manifest.lock: {python}")
        for name, path, key in (
            ("Verilator engine", verilator_engine, "verilator_engine_sha256"),
            ("Verilator runtime", verilator_runtime, "verilator_runtime_sha256"),
            ("SBT launcher JAR", sbt_launch_jar, "sbt_launch_jar_sha256"),
            ("JDK modules", jdk_modules, "jdk_modules_sha256"),
        ):
            if not path.is_file() or sha256(path) != lock[key]:
                raise ValueError(f"{name} hash does not match manifest.lock: {path}")
        native_hashes = {name: sha256(path) for name, path in native_tools.items()}
        native_lock_keys = {
            "gpp": "gpp_binary_sha256",
            "make": "make_binary_sha256",
            "perl": "perl_binary_sha256",
            "sh": "sh_binary_sha256",
            "ld": "host_ld_binary_sha256",
            "ar": "host_ar_binary_sha256",
        }
        for name, actual_hash in native_hashes.items():
            if actual_hash != lock[native_lock_keys[name]]:
                raise ValueError(f"native tool {name} hash does not match manifest.lock")
        tool_trees = {
            "verilator_include": tree_fingerprint(verilator_include),
            "jdk_include": tree_fingerprint(jdk_include),
            "jdk_lib": tree_fingerprint(jdk_lib, excluded_names=frozenset({"modules"})),
        }
        for name, fingerprint in tool_trees.items():
            if fingerprint["sha256"] != lock[f"{name}_tree_sha256"]:
                raise ValueError(f"{name} tree hash does not match manifest.lock")

        build_properties = spinal_dir / "project" / "build.properties"
        expected_property = f"sbt.version={lock['sbt']}"
        property_lines = [
            line.strip()
            for line in build_properties.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if property_lines != [expected_property]:
            raise ValueError(f"{build_properties} must contain exactly {expected_property}")
        build_text = (spinal_dir / "build.sbt").read_text(encoding="utf-8")
        plugin_text = (spinal_dir / "project" / "plugins.sbt").read_text(encoding="utf-8")
        scalafmt_text = (spinal_dir / ".scalafmt.conf").read_text(encoding="utf-8")
        if 'lockedVersion("scalatest")' not in build_text:
            raise ValueError("ScalaTest version must be read from manifest.lock")
        if f'% "{lock["sbt_scalafmt"]}"' not in plugin_text:
            raise ValueError("sbt-scalafmt plugin version differs from manifest.lock")
        if f'version = {lock["scalafmt"]}' not in scalafmt_text:
            raise ValueError("scalafmt version differs from manifest.lock")

        source_before = source_fingerprint(spinal_dir)
        workspace_root = out_dir / "workspaces" / run_id
        build_spinal_dir, isolated_manifest = copy_source_snapshot(
            spinal_dir, manifest_path, workspace_root
        )
        if sha256(isolated_manifest) != sha256(manifest_path):
            raise ValueError("isolated manifest copy differs from the locked source manifest")
        isolated_source_before = source_fingerprint(build_spinal_dir)
        if isolated_source_before != source_before:
            raise ValueError("isolated Scala source snapshot differs from the source workspace")

        dependency_lock_path = manifest_path.parent / DEPENDENCY_LOCK_NAME
        if sha256(dependency_lock_path) != lock["scala_dependency_lock_sha256"]:
            raise ValueError("Scala dependency lock hash differs from manifest.lock")
        dependency_cache_root = tool_root / lock["scala_cache_dir"]
        dependency_manifest = verify_dependency_cache(
            dependency_cache_root, dependency_lock_path
        )
        sbt_boot = dependency_cache_root / DEPENDENCY_CACHE_DIRS["sbt_boot"]
        ivy_home = dependency_cache_root / "ivy2"
        coursier_cache = dependency_cache_root / DEPENDENCY_CACHE_DIRS["coursier"]

        java_home = java.parent.parent
        simulation_workspace = workspace_root / "sim-workspace"
        runtime_workspace = Path(tempfile.gettempdir()) / (
            "nsg-" + sha256_bytes(run_id.encode("utf-8"))[:12]
        )
        runtime_workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
        isolated_home = runtime_workspace / "home"
        isolated_tmp = runtime_workspace / "tmp"
        isolated_jna = runtime_workspace / "jna"
        runtime_properties = {
            "user.home": isolated_home,
            "java.io.tmpdir": isolated_tmp,
            "jna.tmpdir": isolated_jna,
        }
        for path in runtime_properties.values():
            path.mkdir(parents=True, exist_ok=True)
        sbt_global = workspace_root / "sbt-global"
        environment = clean_environment(
            [java.parent, verilator.parent, sbt.parent],
            {
                "JAVA_HOME": str(java_home),
                "SPINAL_SIM_WORKSPACE": str(simulation_workspace),
                "COURSIER_MODE": "offline",
                "COURSIER_CACHE": str(coursier_cache),
                "JAVA_TOOL_OPTIONS": trusted_java_tool_options(runtime_properties),
            },
            home=isolated_home,
        )
        java_result = run_capture([str(java), "-version"], build_spinal_dir, environment, 30)
        java_output = java_result.stdout
        (out_dir / "toolchain.log").write_text(
            f"manifest={manifest_path}\n"
            f"sbt={sbt}\n"
            f"sbt_sha256={sha256(sbt)}\n"
            f"java={java}\n"
            f"java_sha256={sha256(java)}\n"
            f"verilator={verilator}\n"
            f"verilator_sha256={sha256(verilator)}\n"
            f"verilator_engine_sha256={sha256(verilator_engine)}\n"
            f"verilator_runtime_sha256={sha256(verilator_runtime)}\n"
            f"sbt_launch_jar_sha256={sha256(sbt_launch_jar)}\n"
            f"jdk_modules_sha256={sha256(jdk_modules)}\n"
            f"python_binary_sha256={sha256(python)}\n"
            f"native_tools={json.dumps(native_hashes, sort_keys=True)}\n"
            f"tool_trees={json.dumps(tool_trees, sort_keys=True)}\n"
            f"{java_output}",
            encoding="utf-8",
        )
        if java_result.returncode != 0:
            raise ValueError("java -version failed")
        jdk_base, _, jdk_build = lock["jdk"].partition("+")
        if f'"{jdk_base}"' not in java_output or (jdk_build and f"{jdk_base}+{jdk_build}" not in java_output):
            raise ValueError(f"Java version does not match locked JDK {lock['jdk']}")

        summary.update(
            {
                "repo_head_sha": git_head(repo_root),
                "manifest": str(manifest_path),
                "manifest_sha256": sha256(manifest_path),
                "evaluator_sha256": sha256(Path(__file__)),
                "source_before": source_before,
                "isolated_source_before": isolated_source_before,
                "build_workspace": str(workspace_root),
            }
        )
        summary["toolchain"] = {
            "manifest": str(manifest_path),
            "sbt": str(sbt),
            "sbt_version": lock["sbt"],
            "sbt_sha256": sha256(sbt),
            "java": str(java),
            "jdk_version": lock["jdk"],
            "java_sha256": sha256(java),
            "python": str(python),
            "python_version": platform.python_version(),
            "python_sha256": sha256(python),
            "verilator": str(verilator),
            "verilator_version": lock["verilator"],
            "verilator_sha256": sha256(verilator),
            "verilator_engine_sha256": sha256(verilator_engine),
            "verilator_runtime_sha256": sha256(verilator_runtime),
            "sbt_launch_jar_sha256": sha256(sbt_launch_jar),
            "jdk_modules_sha256": sha256(jdk_modules),
            "native_tools": {
                name: {"path": str(native_tools[name]), "sha256": native_hashes[name]}
                for name in sorted(native_tools)
            },
            "tool_trees": tool_trees,
            "scala_version": lock["scala"],
            "spinalhdl_version": lock["spinalhdl"],
            "scalatest_version": lock["scalatest"],
            "sbt_scalafmt_version": lock["sbt_scalafmt"],
            "scalafmt_version": lock["scalafmt"],
            "simulation_workspace": str(simulation_workspace),
            "jvm_runtime_workspace": str(runtime_workspace),
            "jvm_runtime_workspace_retention": "deleted after ScalaTest XML verification",
            "isolated_home": str(isolated_home),
            "isolated_tmp": str(isolated_tmp),
            "isolated_jna_tmp": str(isolated_jna),
            "sbt_boot": str(sbt_boot),
            "ivy_home": str(ivy_home),
            "coursier_cache": str(coursier_cache),
            "dependency_cache_root": str(dependency_cache_root),
            "dependency_lock": str(dependency_lock_path),
            "dependency_lock_sha256": sha256(dependency_lock_path),
            "dependency_artifact_count": dependency_manifest["artifact_count"],
            "dependency_artifacts_sha256": dependency_manifest["artifacts_sha256"],
            "environment": {key: environment[key] for key in sorted(environment)},
            "environment_sha256": sha256_bytes(
                json.dumps(environment, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ),
        }

        task_results: list[dict[str, object]] = []
        expected_compile_counts = {
            "compile": len(list((build_spinal_dir / "src" / "main" / "scala").rglob("*.scala"))),
            "test-compile": len(
                list((build_spinal_dir / "src" / "test" / "scala").rglob("*.scala"))
            ),
        }
        for task_id, sbt_task in TASKS:
            task_started = time.monotonic()
            command = [
                str(java),
                f"-Dsbt.global.base={sbt_global}",
                f"-Dsbt.boot.directory={sbt_boot}",
                f"-Dsbt.ivy.home={ivy_home}",
                "-Dsbt.offline=true",
                "-Dsbt.supershell=false",
                "-Dsbt.log.noformat=true",
                "-jar",
                str(sbt_launch_jar),
                sbt_task,
            ]
            log_path = out_dir / f"{task_id}.log"
            try:
                result = run_capture(command, build_spinal_dir, environment, args.timeout)
                output = result.stdout
                returncode = result.returncode
                timed_out = False
            except subprocess.TimeoutExpired as error:
                chunks = (error.stdout, error.stderr)
                output = "".join(
                    chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else (chunk or "")
                    for chunk in chunks
                )
                returncode = 124
                timed_out = True
            except OSError as error:
                output = f"scala-check: failed to start SBT task: {error}\n"
                returncode = 125
                timed_out = False
            test_outcome = scala_test_outcome(output) if task_id == "test" else None
            if task_id == "test" and returncode == 0 and not scala_test_outcome_passed(test_outcome):
                output += "\nscala-check: tests were missing, skipped, canceled, pending, or failed\n"
                returncode = 3
            compile_count = None
            if task_id in expected_compile_counts and returncode == 0:
                target_fragment = (
                    "/target/scala-2.13/test-classes"
                    if task_id == "test-compile"
                    else "/target/scala-2.13/classes"
                )
                compile_count = compiled_source_count(output, target_fragment)
                if compile_count != expected_compile_counts[task_id]:
                    output += (
                        "\nscala-check: isolated clean compilation count mismatch: "
                        f"expected {expected_compile_counts[task_id]}, got {compile_count}\n"
                    )
                    returncode = 5
            warnings = forbidden_warning_lines(output)
            if returncode == 0 and warnings:
                output += "\nscala-check: unwaived Spinal/Verilator warning detected\n"
                returncode = 4
            log_path.write_text(output, encoding="utf-8")
            passed = returncode == 0
            task_result = {
                "id": task_id,
                "sbt_task": sbt_task,
                "argv": command,
                "returncode": returncode,
                "passed": passed,
                "timed_out": timed_out,
                "forbidden_warnings": warnings,
                "compiled_source_count": compile_count,
                "expected_source_count": expected_compile_counts.get(task_id),
                "test_outcome": test_outcome,
                "elapsed_seconds": round(time.monotonic() - task_started, 3),
                "log": str(log_path.resolve()),
                "log_sha256": sha256(log_path),
            }
            task_results.append(task_result)
            passed_count = sum(bool(item["passed"]) for item in task_results)
            summary.update(
                {
                    "executed": len(task_results),
                    "passed": passed_count,
                    "failed": len(task_results) - passed_count,
                    "skipped": len(TASKS) - len(task_results),
                    "tasks": task_results,
                }
            )
            write_json(summary_path, summary)
            state = "PASS" if passed else "FAIL"
            print(f"[{state}] {sbt_task} ({task_result['elapsed_seconds']}s): {log_path}")
            if not passed:
                tail = "\n".join(output.splitlines()[-20:])
                print(tail, file=sys.stderr)

        runtime_isolation = scala_test_runtime_isolation(
            build_spinal_dir / "target" / "test-reports", runtime_properties
        )
        if not runtime_isolation["passed"]:
            summary["integrity_error"] = (
                "ScalaTest JVM home/tmp/JNA paths escaped the isolated workspace"
            )

        scripts = sorted(simulation_workspace.rglob("verilatorScript.sh"))
        simulator_policies = [verilator_script_policy(script) for script in scripts]
        simulator_policy_passed = bool(
            len(simulator_policies) == 1 and simulator_policies[0]["passed"]
        )
        if not simulator_policy_passed:
            summary["integrity_error"] = (
                "generated Verilator command did not effectively enable -Wall and all locked warnings"
            )
        sim_artifacts = simulation_artifacts(simulation_workspace)
        if not sim_artifacts:
            summary["integrity_error"] = "Scala simulation produced no hashable RTL/script/binary artifacts"

        passed_count = sum(bool(item["passed"]) for item in task_results)
        source_after = source_fingerprint(spinal_dir)
        isolated_source_after = source_fingerprint(build_spinal_dir)
        dependency_manifest_after = verify_dependency_cache(
            dependency_cache_root, dependency_lock_path
        )
        summary.update(
            {
                "executed": len(task_results),
                "passed": passed_count,
                "failed": len(task_results) - passed_count,
                "skipped": 0,
                "tasks": task_results,
                "source_after": source_after,
                "isolated_source_after": isolated_source_after,
                "source_stable": (
                    source_after == source_before
                    and isolated_source_after == isolated_source_before
                ),
                "dependency_cache_stable": dependency_manifest_after == dependency_manifest,
                "test_runtime_isolation": runtime_isolation,
                "simulator_policies": simulator_policies,
                "simulator_policy_passed": simulator_policy_passed,
                "simulation_artifacts": sim_artifacts,
            }
        )
        if source_after != source_before or isolated_source_after != isolated_source_before:
            summary["status"] = "fail"
            summary["integrity_error"] = "Scala source/config changed while scala-check was running"
        if dependency_manifest_after != dependency_manifest:
            summary["status"] = "fail"
            summary["integrity_error"] = "Scala dependency cache changed while scala-check was running"
    except (OSError, ValueError) as error:
        summary["toolchain_error"] = str(error)
        print(f"scala-check toolchain verification failed: {error}", file=sys.stderr)
    finally:
        runtime_workspace_cleaned = runtime_workspace is None
        if runtime_workspace is not None:
            try:
                if runtime_workspace.exists():
                    shutil.rmtree(runtime_workspace)
                runtime_workspace_cleaned = not runtime_workspace.exists()
            except OSError as error:
                summary["cleanup_error"] = str(error)
        summary["runtime_workspace_cleaned"] = runtime_workspace_cleaned
        gate_ok = (
            summary["failed"] == 0
            and summary["skipped"] == 0
            and summary.get("source_stable") is True
            and summary.get("dependency_cache_stable") is True
            and "toolchain_error" not in summary
            and "integrity_error" not in summary
            and "cleanup_error" not in summary
        )
        if gate_ok:
            summary["status"] = "pass"
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_json(summary_path, summary)
        print(f"scala-check summary: {summary_path}")
        gate_lock.unlink()

    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
