#!/usr/bin/env python3
"""Locked, reproducible SpinalHDL RTL generation.

This command is deliberately independent from the component-specific gates.
It accepts only a repository ``openla500.*`` main class, runs it from copied
Scala sources with the locked offline toolchain, and publishes RTL only after
all requested runs produce the same validated bytes.
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
from typing import Iterable


SCALA_DEPENDENCY_LOCK = "scala-dependencies.lock.json"
MAIN_CLASS_RE = re.compile(r"openla500(?:\.[A-Za-z_][A-Za-z0-9_]*)+")
VERILOG_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class SpinalGenerateError(RuntimeError):
    """Raised when generation cannot establish all required evidence."""


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
    if path.is_symlink() or not path.is_file():
        raise SpinalGenerateError(f"manifest.lock is missing or is a symlink: {path}")
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SpinalGenerateError(f"{path}:{number}: expected key=value")
        key, value = (item.strip() for item in line.split("=", 1))
        if not key or key in values:
            raise SpinalGenerateError(f"{path}:{number}: duplicate or empty key {key!r}")
        values[key] = value
    return values


def require_keys(values: dict[str, str], keys: Iterable[str]) -> None:
    missing = [key for key in keys if not values.get(key)]
    if missing:
        raise SpinalGenerateError("manifest.lock is missing keys: " + ", ".join(missing))


def resolve_executable(value: str) -> Path:
    candidate: str | None = value
    if os.sep not in value and "/" not in value:
        candidate = shutil.which(value)
    if not candidate:
        raise SpinalGenerateError(f"executable is not on PATH: {value}")
    path = Path(candidate).expanduser().resolve()
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise SpinalGenerateError(f"executable is missing or not executable: {path}")
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
            returncode, timed_out = process.returncode, False
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    process.kill()
            else:
                process.kill()
            output, _ = process.communicate()
            returncode, timed_out = 124, True
    except OSError as error:
        output, returncode, timed_out = f"failed to start command: {error}\n", 125, False
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
        raise SpinalGenerateError(f"Git metadata is missing: {dot_git}")
    line = dot_git.read_text(encoding="utf-8").strip()
    if not line.startswith("gitdir:"):
        raise SpinalGenerateError(f"invalid Git worktree pointer: {dot_git}")
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
    raise SpinalGenerateError(f"Git worktree metadata target is missing: {raw}")


def git_output(repo_root: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        [
            "git",
            f"--git-dir={resolve_git_dir(repo_root)}",
            f"--work-tree={repo_root.resolve()}",
            *arguments,
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    value = result.stdout.strip()
    if result.returncode != 0:
        raise SpinalGenerateError(result.stderr.strip())
    return value


def source_files(spinal_dir: Path) -> list[Path]:
    required = [
        spinal_dir / "build.sbt",
        spinal_dir / ".scalafmt.conf",
        spinal_dir / "project" / "build.properties",
        spinal_dir / "project" / "plugins.sbt",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SpinalGenerateError(f"Scala source inputs are missing: {missing}")
    runner_options = [spinal_dir / ".sbtopts", spinal_dir / ".jvmopts"]
    present_options = [str(path) for path in runner_options if path.exists()]
    if present_options:
        raise SpinalGenerateError(f"project-local SBT/JVM options are forbidden: {present_options}")
    discovered = list(required)
    for root in (spinal_dir / "project", spinal_dir / "src"):
        if root.is_symlink() or not root.is_dir():
            raise SpinalGenerateError(f"Scala source directory is missing: {root}")
        for path in root.rglob("*"):
            if path.is_symlink():
                raise SpinalGenerateError(f"Scala source snapshot must not contain symlinks: {path}")
            if path.is_file() and "target" not in path.relative_to(spinal_dir).parts:
                discovered.append(path)
    files = sorted(set(discovered), key=lambda item: item.relative_to(spinal_dir).as_posix())
    symlinks = [str(path) for path in files if path.is_symlink()]
    if symlinks:
        raise SpinalGenerateError(f"Scala source snapshot must not contain symlinks: {symlinks}")
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


def tree_fingerprint(root: Path) -> dict[str, object]:
    if not root.is_dir() or root.is_symlink():
        raise SpinalGenerateError(f"protected tree is missing or is a symlink: {root}")
    entries: list[dict[str, object]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append({"path": relative, "kind": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            entries.append(
                {"path": relative, "kind": "file", "size": path.stat().st_size, "sha256": sha256_file(path)}
            )
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"sha256": sha256_bytes(canonical), "entries": entries}


def copy_scala_snapshot(
    spinal_dir: Path, manifest: Path, dependency_lock: Path, destination: Path
) -> tuple[Path, Path, Path]:
    if destination.exists():
        raise SpinalGenerateError(f"isolated Scala workspace already exists: {destination}")
    isolated_spinal = destination / "spinal"
    for source in source_files(spinal_dir):
        target = isolated_spinal / source.relative_to(spinal_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    isolated_reference = destination / "reference"
    isolated_reference.mkdir(parents=True, exist_ok=True)
    isolated_manifest = isolated_reference / manifest.name
    isolated_dependency_lock = isolated_reference / dependency_lock.name
    shutil.copyfile(manifest, isolated_manifest)
    shutil.copyfile(dependency_lock, isolated_dependency_lock)
    return isolated_spinal, isolated_manifest, isolated_dependency_lock


def reject_linked_path(path: Path, label: str) -> Path:
    """Return an absolute path only when no existing component redirects it."""

    absolute = Path(os.path.abspath(os.fspath(path.expanduser())))
    for component in [*reversed(absolute.parents), absolute]:
        is_junction = getattr(component, "is_junction", None)
        if component.is_symlink() or (callable(is_junction) and is_junction()):
            raise SpinalGenerateError(
                f"{label} path must not contain a symlink or junction: {component}"
            )
    return absolute


def validate_request(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    if MAIN_CLASS_RE.fullmatch(args.main_class) is None:
        raise SpinalGenerateError("main class must be a repository openla500.* identifier")
    if VERILOG_IDENTIFIER_RE.fullmatch(args.expected_module) is None:
        raise SpinalGenerateError(f"invalid expected Verilog module: {args.expected_module!r}")
    expected_path = Path(args.expected_file)
    if (
        expected_path.name != args.expected_file
        or expected_path.suffix != ".v"
        or args.expected_file in {".", ".."}
    ):
        raise SpinalGenerateError("expected file must be a plain .v basename")
    if args.runs < 2:
        raise SpinalGenerateError("runs must be at least 2 for reproducibility")
    if args.timeout <= 0:
        raise SpinalGenerateError("timeout must be positive")

    manifest_argument = args.manifest.expanduser().absolute()
    if manifest_argument.is_symlink():
        raise SpinalGenerateError(f"manifest must not be a symlink: {manifest_argument}")
    manifest = manifest_argument.resolve()
    if manifest.name != "manifest.lock" or manifest.parent.name != "reference":
        raise SpinalGenerateError("manifest must be the repository reference/manifest.lock")
    repo_root = manifest.parent.parent.resolve()
    spinal_argument = args.spinal_dir.expanduser().absolute()
    if spinal_argument.is_symlink():
        raise SpinalGenerateError(f"spinal-dir must not be a symlink: {spinal_argument}")
    spinal_dir = spinal_argument.resolve()
    if spinal_dir != (repo_root / "spinal").resolve():
        raise SpinalGenerateError("spinal-dir must be the repository spinal directory")
    out_argument = reject_linked_path(args.out_dir, "OUT_DIR")
    out_dir = out_argument.resolve()
    protected_rtl = (repo_root / "rtl").resolve()
    try:
        out_dir.relative_to(protected_rtl)
    except ValueError:
        pass
    else:
        raise SpinalGenerateError(f"OUT_DIR may not be inside the repository RTL directory: {out_dir}")
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        raise SpinalGenerateError(f"OUT_DIR must be a fresh directory: {out_dir}")
    return manifest, repo_root, spinal_dir, out_dir


def find_main_source(spinal_dir: Path, main_class: str) -> dict[str, object]:
    package_name, object_name = main_class.rsplit(".", 1)
    package_pattern = re.compile(rf"(?m)^\s*package\s+{re.escape(package_name)}\s*$")
    object_pattern = re.compile(rf"\bobject\s+{re.escape(object_name)}\b")
    matches: list[Path] = []
    for path in source_files(spinal_dir):
        if path.suffix != ".scala" or "src/main/scala" not in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        if package_pattern.search(text) and object_pattern.search(text):
            matches.append(path)
    if len(matches) != 1:
        raise SpinalGenerateError(
            f"main class must resolve to exactly one repository Scala object: {main_class}: {matches}"
        )
    source = matches[0]
    return {
        "path": source.relative_to(spinal_dir).as_posix(),
        "size": source.stat().st_size,
        "sha256": sha256_file(source),
    }


def load_scala_gate(repo_root: Path) -> tuple[object, dict[str, object]]:
    path = repo_root / "tools" / "scala_gate.py"
    if path.is_symlink() or not path.is_file():
        raise SpinalGenerateError(f"canonical Scala policy tool is missing: {path}")
    spec = importlib.util.spec_from_file_location("_spinal_generate_scala_gate", path)
    if spec is None or spec.loader is None:
        raise SpinalGenerateError(f"cannot load canonical Scala policy tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, {"path": str(path), "sha256": sha256_file(path)}


def verify_scala_dependencies(
    manifest: Path, tool_root: Path, values: dict[str, str], scala_gate: object
) -> dict[str, object]:
    dependency_lock = manifest.parent / SCALA_DEPENDENCY_LOCK
    if dependency_lock.is_symlink() or not dependency_lock.is_file():
        raise SpinalGenerateError(f"Scala dependency lock is missing: {dependency_lock}")
    lock_sha = sha256_file(dependency_lock)
    if lock_sha != values.get("scala_dependency_lock_sha256"):
        raise SpinalGenerateError("Scala dependency lock hash differs from manifest.lock")
    cache_root = tool_root / values["scala_cache_dir"]
    try:
        cache = scala_gate.verify_dependency_cache(cache_root, dependency_lock)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SpinalGenerateError(str(error)) from error
    return {
        "lock_path": str(dependency_lock),
        "lock_sha256": lock_sha,
        "cache_root": str(cache_root),
        "artifact_count": cache["artifact_count"],
        "artifacts_sha256": cache["artifacts_sha256"],
    }


def locked_tools(
    values: dict[str, str], tool_root: Path, java_home: str | None, out_dir: Path
) -> tuple[Path, Path, dict[str, object]]:
    sbt_jar = tool_root / f"sbt-{values['sbt']}" / "bin" / "sbt-launch.jar"
    if sbt_jar.is_symlink() or not sbt_jar.is_file():
        raise SpinalGenerateError(f"locked SBT launcher is missing: {sbt_jar}")
    if sha256_file(sbt_jar) != values["sbt_launch_jar_sha256"]:
        raise SpinalGenerateError("SBT launcher JAR differs from manifest.lock")
    java_name = "java.exe" if os.name == "nt" else "java"
    java = resolve_executable(str(Path(java_home) / "bin" / java_name) if java_home else java_name)
    if sha256_file(java) != values["java_binary_sha256"]:
        raise SpinalGenerateError("Java binary differs from manifest.lock")
    version = run_command(
        [str(java), "-version"],
        cwd=out_dir,
        timeout=30,
        environment={
            "HOME": str(out_dir),
            "PATH": os.pathsep.join([str(java.parent), "/usr/bin", "/bin"]),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "TZ": "UTC",
        },
    )
    version_text = str(version["stdout"])
    base, _, build = values["jdk"].partition("+")
    version_ok = bool(
        version["returncode"] == 0
        and not version["timed_out"]
        and f'"{base}"' in version_text
        and (not build or f"{base}+{build}" in version_text)
    )
    if not version_ok:
        raise SpinalGenerateError(f"Java version differs from locked JDK {values['jdk']}")
    return java, sbt_jar, {
        "java": str(java),
        "java_sha256": sha256_file(java),
        "jdk": values["jdk"],
        "java_version_output_sha256": sha256_bytes(version_text.encode("utf-8")),
        "sbt": values["sbt"],
        "sbt_launcher": str(sbt_jar),
        "sbt_launcher_sha256": sha256_file(sbt_jar),
        "scala": values.get("scala"),
        "spinalhdl": values.get("spinalhdl"),
    }


def generation_environment(
    values: dict[str, str], tool_root: Path, java: Path, runtime: Path
) -> tuple[dict[str, str], list[str]]:
    cache_root = tool_root / values["scala_cache_dir"]
    sbt_boot = cache_root / "sbt-boot"
    ivy_home = cache_root / "ivy2"
    coursier = cache_root / "coursier" / "v1"
    for path in (sbt_boot, ivy_home, coursier):
        if not path.is_dir():
            raise SpinalGenerateError(f"locked Scala cache path is missing: {path}")
    home, tmp, jna = runtime / "home", runtime / "tmp", runtime / "jna"
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
        f"-Dsbt.global.base={runtime / 'sbt-global'}",
        f"-Dsbt.boot.directory={sbt_boot}",
        f"-Dsbt.ivy.home={ivy_home}",
        "-Dsbt.offline=true",
        "-Dsbt.supershell=false",
        "-Dsbt.log.noformat=true",
    ]
    return environment, jvm


def warning_lines(output: str) -> list[str]:
    warnings: list[str] = []
    for line in output.splitlines():
        cleaned = ANSI_RE.sub("", line).strip()
        if cleaned and re.match(
            r"^(?:warning\b|\[warn(?:ing)?\]|%warning(?:-[A-Za-z0-9_]+)?(?::|\b))",
            cleaned,
            re.IGNORECASE,
        ):
            warnings.append(cleaned)
    return warnings


def failure_marker_lines(output: str, *, trusted_java_tool_options: str | None = None) -> list[str]:
    markers: list[str] = []
    patterns = (
        re.compile(r"\bSKIP(?:PED)?\b", re.IGNORECASE),
        re.compile(r"^\[error\]", re.IGNORECASE),
        re.compile(r"\bException in thread\b", re.IGNORECASE),
        re.compile(r"\b(?:caught|captured)\s+exception\b", re.IGNORECASE),
        re.compile(r"\bSpinalExit\b"),
        re.compile(r"\bError detected in phase\b", re.IGNORECASE),
    )
    trusted_marker = (
        f"[error] Picked up JAVA_TOOL_OPTIONS: {trusted_java_tool_options}"
        if trusted_java_tool_options is not None
        else None
    )
    for line in output.splitlines():
        cleaned = ANSI_RE.sub("", line).strip()
        if trusted_marker is not None and cleaned == trusted_marker:
            continue
        if cleaned and any(pattern.search(cleaned) for pattern in patterns):
            markers.append(cleaned)
    return markers


def inspect_generated_rtl(generated: Path, expected_file: str, expected_module: str) -> dict[str, object]:
    files: list[Path] = []
    for path in generated.rglob("*"):
        if path.is_symlink():
            raise SpinalGenerateError(f"generated output contains a symlink: {path}")
        if path.is_file():
            files.append(path)
    relative_files = sorted(path.relative_to(generated).as_posix() for path in files)
    if relative_files != [expected_file]:
        raise SpinalGenerateError(
            f"generated files differ from the locked expectation: {relative_files} != {[expected_file]}"
        )
    rtl = generated / expected_file
    if rtl.stat().st_size <= 0:
        raise SpinalGenerateError(f"generated RTL is empty: {rtl}")
    try:
        text = rtl.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise SpinalGenerateError(f"generated RTL is not UTF-8: {rtl}") from error
    without_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    without_comments = re.sub(r"//[^\n]*", "", without_comments)
    modules = re.findall(
        r"(?m)^\s*module\s+(?:automatic\s+)?([A-Za-z_][A-Za-z0-9_$]*)\b",
        without_comments,
    )
    endmodules = len(re.findall(r"\bendmodule\b", without_comments))
    duplicates = sorted({name for name in modules if modules.count(name) > 1})
    if modules.count(expected_module) != 1 or duplicates or endmodules != len(modules):
        raise SpinalGenerateError(
            "generated module declarations are not unique and balanced: "
            f"expected={expected_module!r} modules={modules} endmodules={endmodules}"
        )
    return {
        "file": expected_file,
        "module": expected_module,
        "module_declarations": modules,
        "module_count": len(modules),
        "sha256": sha256_file(rtl),
        "size": rtl.stat().st_size,
        "payload": rtl.read_bytes(),
    }


def sbt_path_argument(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    if any(character in value for character in ('"', "\n", "\r")):
        raise SpinalGenerateError(f"output path cannot be encoded for SBT: {path}")
    return '"' + value + '"'


def generate(args: argparse.Namespace) -> int:
    started = time.monotonic()
    manifest, repo_root, spinal_dir, out_dir = validate_request(args)
    reject_linked_path(out_dir, "OUT_DIR")
    out_dir.mkdir(parents=True, exist_ok=True)
    reject_linked_path(out_dir, "OUT_DIR")
    values = parse_lock(manifest)
    require_keys(
        values,
        (
            "jdk",
            "java_binary_sha256",
            "sbt",
            "sbt_launch_jar_sha256",
            "scala",
            "spinalhdl",
            "scala_cache_dir",
            "scala_dependency_lock_sha256",
        ),
    )
    main_source = find_main_source(spinal_dir, args.main_class)
    scala_gate, scala_policy = load_scala_gate(repo_root)
    tool_root = args.tool_root.resolve()
    manifest_before = {"sha256": sha256_file(manifest), "size": manifest.stat().st_size}
    dependency_before = verify_scala_dependencies(manifest, tool_root, values, scala_gate)
    source_before = source_fingerprint(spinal_dir)
    rtl_before = tree_fingerprint(repo_root / "rtl")
    head_before = git_output(repo_root, ["rev-parse", "HEAD"])
    evaluator_before = sha256_file(Path(__file__))
    java, sbt_jar, toolchain = locked_tools(values, tool_root, args.java_home, out_dir)

    dependency_lock = manifest.parent / SCALA_DEPENDENCY_LOCK
    run_results: list[dict[str, object]] = []
    payloads: list[bytes] = []
    for index in range(args.runs):
        workspace = out_dir / "workspaces" / f"run-{index + 1}"
        isolated_spinal, isolated_manifest, isolated_dependency_lock = copy_scala_snapshot(
            spinal_dir, manifest, dependency_lock, workspace
        )
        snapshot_before = source_fingerprint(isolated_spinal)
        snapshot_matches_source = snapshot_before == source_before
        generated = out_dir / "generated" / f"run-{index + 1}"
        generated.mkdir(parents=True)
        runtime_id = sha256_bytes(f"{out_dir}:{index + 1}:{os.getpid()}".encode("utf-8"))[:12]
        runtime = Path(tempfile.gettempdir()) / f"nscscc-spinalgen-{runtime_id}"
        if runtime.exists():
            raise SpinalGenerateError(f"short Scala runtime path already exists: {runtime}")
        environment, jvm = generation_environment(values, tool_root, java, runtime)
        command = [
            str(java),
            *jvm,
            "-jar",
            str(sbt_jar),
            (
                f"Compile / runMain {args.main_class} "
                f"--out-dir {sbt_path_argument(generated)}"
            ),
        ]
        result = run_command(command, cwd=isolated_spinal, timeout=args.timeout, environment=environment)
        log_path = out_dir / f"generate-{index + 1}.log"
        log_path.write_text(str(result["stdout"]), encoding="utf-8")
        cleanup_error: str | None = None
        try:
            shutil.rmtree(runtime)
        except OSError as error:
            cleanup_error = str(error)
        warnings = warning_lines(str(result["stdout"]))
        failure_markers = failure_marker_lines(
            str(result["stdout"]),
            trusted_java_tool_options=environment["JAVA_TOOL_OPTIONS"],
        )
        rtl_evidence: dict[str, object] | None = None
        output_error: str | None = None
        try:
            rtl_evidence = inspect_generated_rtl(
                generated, args.expected_file, args.expected_module
            )
            payloads.append(rtl_evidence.pop("payload"))
        except (OSError, UnicodeError, SpinalGenerateError) as error:
            output_error = str(error)
        snapshot_after = source_fingerprint(isolated_spinal)
        snapshot_stable = snapshot_before == snapshot_after
        isolated_locks_stable = bool(
            sha256_file(isolated_manifest) == manifest_before["sha256"]
            and sha256_file(isolated_dependency_lock) == dependency_before["lock_sha256"]
        )
        passed = bool(
            result["returncode"] == 0
            and not result["timed_out"]
            and not warnings
            and not failure_markers
            and rtl_evidence is not None
            and snapshot_matches_source
            and snapshot_stable
            and isolated_locks_stable
            and not runtime.exists()
            and cleanup_error is None
        )
        run_results.append(
            {
                "run": index + 1,
                "passed": passed,
                "returncode": result["returncode"],
                "timed_out": result["timed_out"],
                "elapsed_seconds": result["elapsed_seconds"],
                "warnings": warnings,
                "failure_markers": failure_markers,
                "output_error": output_error,
                "rtl": rtl_evidence,
                "snapshot_before": snapshot_before,
                "snapshot_after": snapshot_after,
                "snapshot_matches_source": snapshot_matches_source,
                "snapshot_stable": snapshot_stable,
                "isolated_locks_stable": isolated_locks_stable,
                "runtime_workspace": str(runtime),
                "runtime_workspace_cleaned": not runtime.exists(),
                "cleanup_error": cleanup_error,
                "log": str(log_path),
                "log_sha256": sha256_file(log_path),
                "command": {key: value for key, value in result.items() if key != "stdout"},
            }
        )

    source_after = source_fingerprint(spinal_dir)
    dependency_after = verify_scala_dependencies(manifest, tool_root, values, scala_gate)
    manifest_after = {"sha256": sha256_file(manifest), "size": manifest.stat().st_size}
    rtl_after = tree_fingerprint(repo_root / "rtl")
    head_after = git_output(repo_root, ["rev-parse", "HEAD"])
    evaluator_after = sha256_file(Path(__file__))
    toolchain_after = {
        "java_sha256": sha256_file(java),
        "sbt_launcher_sha256": sha256_file(sbt_jar),
    }
    toolchain_stable = bool(
        toolchain_after["java_sha256"] == toolchain["java_sha256"]
        and toolchain_after["sbt_launcher_sha256"] == toolchain["sbt_launcher_sha256"]
    )
    reproducible = bool(
        len(payloads) == args.runs and payloads and all(payload == payloads[0] for payload in payloads)
    )
    snapshots_match_source = bool(
        len(run_results) == args.runs
        and all(item["snapshot_matches_source"] for item in run_results)
    )
    stable_inputs = bool(
        source_before == source_after
        and dependency_before == dependency_after
        and manifest_before == manifest_after
        and rtl_before == rtl_after
        and head_before == head_after
        and evaluator_before == evaluator_after
        and toolchain_stable
        and snapshots_match_source
    )
    passed = bool(
        len(run_results) == args.runs
        and all(item["passed"] for item in run_results)
        and reproducible
        and stable_inputs
    )
    published = out_dir / "rtl" / args.expected_file
    if passed:
        published.parent.mkdir(parents=True, exist_ok=True)
        published.write_bytes(payloads[0])
    summary = {
        "schema_version": 1,
        "gate": "spinal-generate",
        "status": "pass" if passed else "fail",
        "generated_at": now_iso(),
        "main_class": args.main_class,
        "main_source": main_source,
        "expected_module": args.expected_module,
        "expected_file": args.expected_file,
        "repo_head_sha": head_before,
        "repo_head_before": head_before,
        "repo_head_after": head_after,
        "source_before": source_before,
        "source_after": source_after,
        "source_stable": source_before == source_after,
        "manifest_before": manifest_before,
        "manifest_after": manifest_after,
        "manifest_stable": manifest_before == manifest_after,
        "scala_dependencies_before": dependency_before,
        "scala_dependencies_after": dependency_after,
        "scala_dependencies_stable": dependency_before == dependency_after,
        "protected_rtl_before": rtl_before,
        "protected_rtl_after": rtl_after,
        "protected_rtl_stable": rtl_before == rtl_after,
        "scala_policy": scala_policy,
        "toolchain": toolchain,
        "toolchain_after": toolchain_after,
        "toolchain_stable": toolchain_stable,
        "runs": run_results,
        "counts": {
            "planned": args.runs,
            "executed": len(run_results),
            "passed": sum(bool(item["passed"]) for item in run_results),
            "failed": sum(not bool(item["passed"]) for item in run_results),
            "skipped": 0,
            "not_executed": args.runs - len(run_results),
        },
        "reproducible": reproducible,
        "isolated_snapshots_match_source": snapshots_match_source,
        "stable_inputs": stable_inputs,
        "published_rtl": str(published) if published.is_file() else None,
        "published_sha256": sha256_file(published) if published.is_file() else None,
        "published_size": published.stat().st_size if published.is_file() else None,
        "evaluator_sha256": evaluator_before,
        "evaluator_sha256_after": evaluator_after,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--spinal-dir", type=Path, required=True)
    parser.add_argument("--tool-root", type=Path, required=True)
    parser.add_argument("--main-class", required=True)
    parser.add_argument("--expected-module", required=True)
    parser.add_argument("--expected-file", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--java-home")
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=900)
    return parser


def main() -> int:
    if not sys.flags.isolated:
        print("spinal_generate.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    args = build_parser().parse_args()
    try:
        return generate(args)
    except (SpinalGenerateError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
