#!/usr/bin/env python3
"""Reproducible baseline and chiplab validation commands.

This tool never downloads dependencies. Bootstrap is an explicit, separately
reviewed operation; normal commands only verify and consume locked inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "reference" / "manifest.lock"
GOLDEN_FILES_PATH = REPO_ROOT / "reference" / "golden-rtl-files.lock"
GENERATED_MARKER = ".nscscc-refactor-generated.json"
LOCKED_SMOKE_CASE = "func/func_lab19"
ITERATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
SHA256_HEX_PATTERN = re.compile(r"[0-9a-f]{64}")
COMPONENT_REPLACEMENT_SCHEMA_VERSION = 1
FORBIDDEN_REPLACEMENT_ORACLE_TASK_PATTERN = re.compile(
    r"\$(?:"
    r"f?(?:display|write|monitor|strobe)(?:b|h|o)?|"
    r"monitor(?:on|off)|printtimescale|"
    r"finish(?:_and_return)?|stop|fatal|error|warning|info|exit"
    r")\b",
    re.IGNORECASE,
)
REPLACEMENT_SYSTEM_IDENTIFIER_PATTERN = re.compile(r"\$[A-Za-z_][A-Za-z0-9_$]*")
SIDE_EFFECT_FREE_REPLACEMENT_SYSTEM_FUNCTIONS = frozenset(
    {
        "$bits",
        "$clog2",
        "$countbits",
        "$countones",
        "$dimensions",
        "$high",
        "$increment",
        "$isunknown",
        "$left",
        "$low",
        "$onehot",
        "$onehot0",
        "$right",
        "$signed",
        "$size",
        "$unsigned",
        "$unpacked_dimensions",
    }
)

REQUIRED_MANIFEST_KEYS = {
    "chiplab_commit",
    "chiplab_mycpu_gitlink",
    "team_golden_candidate",
    "jdk",
    "verilator",
    "yosys",
    "la32r_gcc",
    "nemu",
    "picolibc",
    "qemu",
    "scala",
    "sbt",
    "spinalhdl",
    "gcc_binary_sha256",
    "as_binary_sha256",
    "ld_binary_sha256",
    "nemu_binary_sha256",
    "picolibc_libc_sha256",
    "qemu_binary_sha256",
    "sbt_script_sha256",
    "verilator_binary_sha256",
    "yosys_binary_sha256",
    "java_binary_sha256",
    "gcc_cc1_sha256",
    "gcc_collect2_sha256",
    "sbt_launch_jar_sha256",
    "verilator_engine_sha256",
    "verilator_runtime_sha256",
    "jdk_modules_sha256",
    "python",
    "python_binary_sha256",
    "vivado_edition",
    "vivado_build",
    "vivado_windows_home",
    "vivado_windows_launcher_sha256",
    "vivado_windows_binary_sha256",
}

FORBIDDEN_GOLDEN_FILES = {
    "rtl/btb.v.bak",
    "rtl/regfile_dual.v",
    "rtl/store_buffer.v",
}


class RefactorError(RuntimeError):
    pass


@dataclass
class CommandResult:
    command: list[str]
    cwd: str
    exit_code: int
    elapsed_seconds: float
    stdout: str
    stderr: str
    timed_out: bool = False
    log_path: str | None = None
    log_sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "timed_out": self.timed_out,
            "log_path": self.log_path,
            "log_sha256": self.log_sha256,
        }


@dataclass(frozen=True)
class ValidationLock:
    path: Path
    iteration_id: str
    operation: str
    run_id: str
    descriptor: int
    device: int
    inode: int

    def __str__(self) -> str:
        return str(self.path)


@dataclass(frozen=True)
class ComponentReplacement:
    target: str
    source: str
    base_sha256: str
    replacement_sha256: str
    source_oid: str
    source_mode: str
    payload: bytes


@dataclass(frozen=True)
class ComponentReplacementPlan:
    spec_path: str
    spec_commit: str
    spec_sha256: str
    source_head: str
    source_tree: str
    source_branch: str
    source_status_entry_count: int
    source_porcelain_clean: bool
    source_semantic_clean: bool
    source_eol_normalization_only: bool
    base_candidate_commit: str
    replacements: tuple[ComponentReplacement, ...]

    def metadata(self) -> dict[str, Any]:
        return {
            "schema_version": COMPONENT_REPLACEMENT_SCHEMA_VERSION,
            "spec_path": self.spec_path,
            "spec_source": f"{self.spec_commit}:{self.spec_path}",
            "spec_commit": self.spec_commit,
            "spec_sha256": self.spec_sha256,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "source_branch": self.source_branch,
            "replacement_payload_source": "committed_git_blobs",
            "worktree_clean": self.source_porcelain_clean,
            "worktree_porcelain_clean": self.source_porcelain_clean,
            "worktree_raw_status_entry_count": self.source_status_entry_count,
            "worktree_semantic_clean": self.source_semantic_clean,
            "worktree_semantic_diff_policy": "ignore-cr-at-eol-only",
            "worktree_eol_normalization_only": self.source_eol_normalization_only,
            "base_candidate_commit": self.base_candidate_commit,
            "replacements": [
                {
                    "target": item.target,
                    "source": item.source,
                    "base_sha256": item.base_sha256,
                    "replacement_sha256": item.replacement_sha256,
                    "source_oid": item.source_oid,
                    "source_mode": item.source_mode,
                    "size": len(item.payload),
                }
                for item in self.replacements
            ],
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_payload(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def json_sha256(value: Any) -> str:
    return sha256_bytes(json_payload(value))


def write_json(path: Path, value: Any) -> None:
    path = Path(path).absolute()
    reject_link_or_reparse_path(path, "JSON output")
    path.parent.mkdir(parents=True, exist_ok=True)
    reject_link_or_reparse_path(path, "JSON output")
    payload = json_payload(value)
    if os.name == "posix":
        _write_json_posix(path, payload)
    else:
        _write_json_windows(path, payload)


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _write_json_posix(path: Path, payload: bytes) -> None:
    parent_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_fd = os.open(path.parent, parent_flags)
    temporary_name = f".{path.name}.{os.getpid()}.{secrets.token_hex(12)}.tmp"
    published = False
    try:
        parent_identity = os.fstat(parent_fd)
        path_identity = os.stat(path.parent, follow_symlinks=False)
        if not _same_file_identity(parent_identity, path_identity):
            raise RefactorError(f"JSON output parent changed before publication: {path.parent}")
        try:
            target = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            target = None
        if target is not None and not stat.S_ISREG(target.st_mode):
            raise RefactorError(f"JSON output must be a regular file: {path}")
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        current_parent = os.stat(path.parent, follow_symlinks=False)
        if not _same_file_identity(parent_identity, current_parent):
            raise RefactorError(f"JSON output parent changed before publication: {path.parent}")
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        published = True
        try:
            current_parent = os.stat(path.parent, follow_symlinks=False)
            if not _same_file_identity(parent_identity, current_parent):
                raise RefactorError(
                    f"JSON output parent changed during publication: {path.parent}"
                )
            os.fsync(parent_fd)
        except BaseException:
            try:
                os.unlink(path.name, dir_fd=parent_fd)
                published = False
                os.fsync(parent_fd)
            except OSError:
                pass
            raise
    finally:
        if not published:
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        os.close(parent_fd)


def _write_json_windows(path: Path, payload: bytes) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    candidates = list(reversed([path.parent, *path.parent.parents]))
    initial_identities = {
        candidate: candidate.stat(follow_symlinks=False) for candidate in candidates
    }
    directory_handles: list[int] = []
    try:
        for candidate in candidates:
            directory_handle = create_file(
                str(candidate),
                0x0080,
                0x00000001 | 0x00000002,
                None,
                3,
                0x02000000 | 0x00200000,
                None,
            )
            if directory_handle == wintypes.HANDLE(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            directory_handles.append(directory_handle)
        reject_link_or_reparse_path(path, "JSON output")
        for candidate, initial_identity in initial_identities.items():
            current_identity = candidate.stat(follow_symlinks=False)
            if not _same_file_identity(initial_identity, current_identity):
                raise RefactorError(
                    f"JSON output ancestor changed before publication: {candidate}"
                )
        handle = tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        )
        temporary = Path(handle.name)
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        reject_link_or_reparse_path(path, "JSON output")
        for candidate, initial_identity in initial_identities.items():
            current_identity = candidate.stat(follow_symlinks=False)
            if not _same_file_identity(initial_identity, current_identity):
                raise RefactorError(
                    f"JSON output ancestor changed during publication: {candidate}"
                )
        os.replace(temporary, path)
    finally:
        if "temporary" in locals():
            temporary.unlink(missing_ok=True)
        for directory_handle in reversed(directory_handles):
            close_handle(directory_handle)


def reject_link_or_reparse_path(path: Path, context: str) -> None:
    """Reject existing symlink/junction components without resolving the target."""

    absolute = Path(path).absolute()
    candidates = [absolute, *absolute.parents]
    for candidate in reversed(candidates):
        is_junction = bool(
            hasattr(candidate, "is_junction") and candidate.is_junction()
        )
        if candidate.is_symlink() or is_junction:
            raise RefactorError(f"{context} must not contain a symlink or junction: {candidate}")


def strict_json_loads(payload: str, context: str) -> Any:
    def object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise RefactorError(f"duplicate JSON key in {context}: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise RefactorError(f"non-standard JSON constant in {context}: {value}")

    try:
        return json.loads(
            payload,
            object_pairs_hook=object_from_pairs,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as error:
        raise RefactorError(f"invalid JSON in {context}: {error}") from error


def read_json_file_with_sha256(path: Path) -> tuple[Any, str]:
    try:
        payload = path.read_bytes()
        text = payload.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise RefactorError(f"invalid JSON {path}: {error}") from error
    return strict_json_loads(text, str(path)), sha256_bytes(payload)


def parse_lock(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RefactorError(f"{path}:{line_number}: expected key=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or not value:
            raise RefactorError(f"{path}:{line_number}: empty key or value")
        if key in values:
            raise RefactorError(f"{path}:{line_number}: duplicate key {key}")
        values[key] = value
    return values


def read_golden_files(path: Path = GOLDEN_FILES_PATH) -> list[str]:
    files = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(files) != len(set(files)):
        raise RefactorError(f"{path}: duplicate file")
    invalid = [item for item in files if not item.startswith("rtl/") or ".." in Path(item).parts]
    if invalid:
        raise RefactorError(f"{path}: invalid paths: {invalid}")
    forbidden = sorted(set(files) & FORBIDDEN_GOLDEN_FILES)
    if forbidden:
        raise RefactorError(f"{path}: forbidden dead/backup RTL: {forbidden}")
    return files


def run_command(
    command: Sequence[str | Path],
    *,
    cwd: Path,
    timeout: int = 60,
    env: dict[str, str] | None = None,
    log_path: Path | None = None,
) -> CommandResult:
    argv = [str(item) for item in command]
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
        stdout, stderr = process.communicate(timeout=timeout)
        result = CommandResult(
            command=argv,
            cwd=str(cwd),
            exit_code=process.returncode,
            elapsed_seconds=time.monotonic() - started,
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            stdout, stderr = process.communicate()
        stdout = stdout or ""
        stderr = stderr or ""
        result = CommandResult(
            command=argv,
            cwd=str(cwd),
            exit_code=124,
            elapsed_seconds=time.monotonic() - started,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )
    except OSError as error:
        result = CommandResult(
            command=argv,
            cwd=str(cwd),
            exit_code=127,
            elapsed_seconds=time.monotonic() - started,
            stdout="",
            stderr=f"unable to start command: {error}",
        )
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "$ " + " ".join(argv) + "\n\n[stdout]\n" + result.stdout + "\n[stderr]\n" + result.stderr,
            encoding="utf-8",
            newline="\n",
        )
        result.log_path = str(log_path.resolve())
        result.log_sha256 = sha256_file(log_path)
    return result


def require_command(result: CommandResult, context: str) -> None:
    if result.exit_code != 0:
        tail = (result.stdout + "\n" + result.stderr)[-2000:]
        raise RefactorError(f"{context} failed with exit {result.exit_code}:\n{tail}")


def git(args: Sequence[str], *, cwd: Path = REPO_ROOT, timeout: int = 60) -> CommandResult:
    return run_command(["git", *args], cwd=cwd, timeout=timeout)


def git_text(args: Sequence[str], *, cwd: Path = REPO_ROOT) -> str:
    result = git(args, cwd=cwd)
    require_command(result, f"git {' '.join(args)}")
    return result.stdout.strip()


def git_blob(revision_and_path: str, *, cwd: Path = REPO_ROOT) -> bytes:
    process = subprocess.run(
        ["git", "cat-file", "blob", revision_and_path],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    if process.returncode != 0:
        stderr = process.stderr.decode("utf-8", "replace")
        raise RefactorError(f"git cat-file blob {revision_and_path} failed: {stderr}")
    return process.stdout


def checked_repo_git_path(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise RefactorError(f"{context} must be a non-empty repo-relative POSIX path")
    if "\\" in value or any(ord(character) < 32 for character in value):
        raise RefactorError(f"invalid {context}: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith(":") or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise RefactorError(f"invalid {context}: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise RefactorError(f"invalid {context}: {value!r}")
    return normalized


def git_regular_blob_entry(commit: str, path: str) -> dict[str, str]:
    result = git(
        ["ls-tree", "-z", "--full-tree", commit, "--", f":(literal){path}"],
        cwd=REPO_ROOT,
    )
    require_command(result, f"inspect Git tree entry {commit}:{path}")
    records = [record for record in result.stdout.split("\0") if record]
    if len(records) != 1 or "\t" not in records[0]:
        raise RefactorError(f"replacement source must be one tracked Git blob: {commit}:{path}")
    metadata, actual_path = records[0].split("\t", 1)
    parts = metadata.split()
    if len(parts) != 3 or actual_path != path:
        raise RefactorError(f"replacement Git tree entry is malformed: {commit}:{path}")
    mode, object_type, object_id = parts
    if mode not in {"100644", "100755"} or object_type != "blob":
        raise RefactorError(
            f"replacement source must be a regular tracked blob: {commit}:{path} mode={mode} type={object_type}"
        )
    return {"mode": mode, "type": object_type, "oid": object_id, "path": actual_path}


def require_clean_source_head(
    expected_head: str, *, cwd: Path = REPO_ROOT
) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{40}", expected_head or "") is None:
        raise RefactorError("--source-head must be a full lowercase 40-character Git SHA")
    actual_head = git_text(["rev-parse", "HEAD"], cwd=cwd)
    if actual_head != expected_head:
        raise RefactorError(
            f"replacement source HEAD changed: expected={expected_head} actual={actual_head}"
        )
    branch = git_text(["branch", "--show-current"], cwd=cwd)
    if not branch.startswith("refactor/"):
        raise RefactorError(f"replacement source must be on a refactor/* branch: {branch or '<detached>'}")
    status_result = git(
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=cwd
    )
    require_command(status_result, "inspect replacement source porcelain status")
    status_entries = [entry for entry in status_result.stdout.split("\0") if entry]
    porcelain_clean = not status_entries
    eol_status_shape = all(entry.startswith(" M ") for entry in status_entries)
    staged = git(
        [
            "diff",
            "--cached",
            "--quiet",
            "--exit-code",
            "--no-ext-diff",
            "--no-textconv",
            "--ignore-submodules=none",
            "--",
        ],
        cwd=cwd,
    )
    semantic = git(
        [
            "diff",
            "--quiet",
            "--exit-code",
            "--no-ext-diff",
            "--no-textconv",
            "--ignore-submodules=none",
            "--ignore-cr-at-eol",
            "--",
        ],
        cwd=cwd,
    )
    for result, context in ((staged, "staged diff"), (semantic, "semantic worktree diff")):
        if result.exit_code not in {0, 1}:
            require_command(result, f"inspect replacement source {context}")
    untracked = git_text(
        ["ls-files", "--others", "--exclude-standard"], cwd=cwd
    )
    semantic_clean = (
        staged.exit_code == 0
        and semantic.exit_code == 0
        and not untracked
        and eol_status_shape
    )
    if not semantic_clean:
        rendered_status = "\n".join(repr(entry) for entry in status_entries)
        raise RefactorError(
            "replacement source worktree has staged, non-CRLF, untracked, or unsupported status changes:\n"
            f"status={rendered_status or '<clean>'}\n"
            f"staged_exit={staged.exit_code} semantic_exit={semantic.exit_code}\n"
            f"eol_status_shape={eol_status_shape}\n"
            f"untracked={untracked or '<none>'}"
        )
    status_entry_count = len(status_entries)
    return {
        "head": actual_head,
        "tree": git_text(["rev-parse", "HEAD^{tree}"], cwd=cwd),
        "branch": branch,
        "status_entry_count": status_entry_count,
        "porcelain_clean": porcelain_clean,
        "semantic_clean": semantic_clean,
        "eol_normalization_only": not porcelain_clean,
    }


def mask_verilog_comments_and_strings(text: str, *, mask_strings: bool) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    while index < len(text):
        character = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if character == "/" and following == "/":
                output.extend((" ", " "))
                index += 2
                state = "line_comment"
                continue
            if character == "/" and following == "*":
                output.extend((" ", " "))
                index += 2
                state = "block_comment"
                continue
            if character == '"':
                output.append(" " if mask_strings else character)
                index += 1
                state = "string"
                continue
            output.append(character)
            index += 1
            continue
        if state == "line_comment":
            output.append("\n" if character == "\n" else " ")
            index += 1
            if character == "\n":
                state = "code"
            continue
        if state == "block_comment":
            if character == "*" and following == "/":
                output.extend((" ", " "))
                index += 2
                state = "code"
            else:
                output.append("\n" if character == "\n" else " ")
                index += 1
            continue
        if character == "\\" and following:
            output.extend((" ", " ") if mask_strings else (character, following))
            index += 2
            continue
        output.append(" " if mask_strings else character)
        index += 1
        if character == '"':
            state = "code"
    return "".join(output)


def referenced_verilog_macros(text: str) -> set[str]:
    code = mask_verilog_comments_and_strings(text, mask_strings=True)
    macros = {
        match.group(1)
        for match in re.finditer(
            r"`\s*(?:ifdef|ifndef|elsif)\s+([A-Za-z_][A-Za-z0-9_$]*)",
            code,
            re.IGNORECASE,
        )
    }
    directives = {
        "begin_keywords",
        "celldefine",
        "default_nettype",
        "define",
        "else",
        "elsif",
        "end_keywords",
        "endcelldefine",
        "endif",
        "ifdef",
        "ifndef",
        "include",
        "line",
        "nounconnected_drive",
        "pragma",
        "resetall",
        "timescale",
        "unconnected_drive",
        "undef",
    }
    macros.update(
        name
        for name in re.findall(r"`\s*([A-Za-z_][A-Za-z0-9_$]*)", code)
        if name.lower() not in directives
    )
    return macros


def validate_replacement_verilog(
    payload: bytes,
    source: str,
    *,
    base_payload: bytes | None = None,
) -> None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RefactorError(f"replacement Verilog is not UTF-8: {source}") from error
    if "\x00" in text:
        raise RefactorError(f"replacement Verilog contains a NUL byte: {source}")
    if re.search(r"verilator\s+lint_(?:off|save)\b", text, re.IGNORECASE):
        raise RefactorError(f"replacement Verilog contains an inline lint waiver: {source}")
    executable_code = mask_verilog_comments_and_strings(text, mask_strings=True)
    if re.search(r"`\s*(?:define|undef)\b|``", executable_code, re.IGNORECASE):
        raise RefactorError(
            f"replacement Verilog contains a local macro or token-paste dependency: {source}"
        )
    replacement_macros = referenced_verilog_macros(text)
    if base_payload is None:
        base_macros: set[str] = set()
    else:
        try:
            base_text = base_payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RefactorError(f"locked base Verilog is not UTF-8 for {source}") from error
        base_macros = referenced_verilog_macros(base_text)
    new_macros = sorted(replacement_macros - base_macros)
    if new_macros:
        raise RefactorError(
            f"replacement Verilog adds unbound macro dependencies {new_macros}: {source}"
        )
    oracle_task = FORBIDDEN_REPLACEMENT_ORACLE_TASK_PATTERN.search(executable_code)
    if oracle_task:
        raise RefactorError(
            "replacement Verilog uses a forbidden oracle-output or simulation-control "
            f"system task {oracle_task.group(0)}: {source}"
        )
    external_task = re.search(
        r"\$(?:readmem[hb]|writemem[hb]|fopen|fclose|fread|fwrite|fscanf|fgets|fgetc|"
        r"ungetc|fseek|ftell|rewind|fflush|ferror|fdisplay|fmonitor|fstrobe|scanf|"
        r"dumpfile|dumpvars|dumpon|dumpoff|dumpall|dumpflush|random|urandom|"
        r"urandom_range|system|value\$plusargs|test\$plusargs)\b",
        executable_code,
        re.IGNORECASE,
    )
    if external_task:
        raise RefactorError(
            "replacement Verilog uses an unbound external system task "
            f"{external_task.group(0)}: {source}"
        )
    unapproved_system_identifiers = sorted(
        set(REPLACEMENT_SYSTEM_IDENTIFIER_PATTERN.findall(executable_code))
        - SIDE_EFFECT_FREE_REPLACEMENT_SYSTEM_FUNCTIONS
    )
    if unapproved_system_identifiers:
        raise RefactorError(
            "replacement Verilog uses unapproved system tasks or functions "
            f"{unapproved_system_identifiers}: {source}"
        )
    comment_free = mask_verilog_comments_and_strings(text, mask_strings=False)
    if re.search(r'\b(?:import|export)\s*"DPI(?:-C)?"', comment_free, re.IGNORECASE):
        raise RefactorError(f"replacement Verilog uses an unbound DPI dependency: {source}")
    include_pattern = re.compile(r"`include\b([^\r\n]*)")
    literal_pattern = re.compile(r'\s*"([^"]+)"\s*(?://.*)?')
    for match in include_pattern.finditer(text):
        literal = literal_pattern.fullmatch(match.group(1))
        if literal is None:
            raise RefactorError(
                f"unresolved replacement include at {source}:{text.count(chr(10), 0, match.start()) + 1}"
            )
        if literal.group(1) != "mycpu.h":
            raise RefactorError(
                f"unapproved replacement include {literal.group(1)!r} in {source}"
            )


def load_component_replacement_plan(
    spec_path_value: str,
    source_head: str,
) -> ComponentReplacementPlan:
    manifest = parse_lock(MANIFEST_PATH)
    source_state = require_clean_source_head(source_head)
    if source_state["head"] != source_head:
        raise RefactorError("replacement source HEAD changed")
    spec_path = checked_repo_git_path(spec_path_value, "replacement spec path")
    git_regular_blob_entry(source_head, spec_path)
    spec_payload = git_blob(f"{source_head}:{spec_path}")
    try:
        spec_text = spec_payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RefactorError(
            f"replacement spec is not valid UTF-8 JSON: {source_head}:{spec_path}"
        ) from error
    document = strict_json_loads(spec_text, f"replacement spec {source_head}:{spec_path}")
    if not isinstance(document, dict) or set(document) != {"schema_version", "replacements"}:
        raise RefactorError("replacement spec must contain exactly schema_version and replacements")
    if (
        type(document.get("schema_version")) is not int
        or document.get("schema_version") != COMPONENT_REPLACEMENT_SCHEMA_VERSION
    ):
        raise RefactorError("unsupported replacement spec schema_version")
    raw_replacements = document.get("replacements")
    if not isinstance(raw_replacements, list) or not raw_replacements:
        raise RefactorError("replacement spec must contain at least one replacement")

    locked_paths = read_golden_files()
    locked_set = set(locked_paths)
    base_commit = manifest["team_golden_candidate"]
    replacements: list[ComponentReplacement] = []
    targets: set[str] = set()
    sources: set[str] = set()
    required_keys = {"target", "source", "base_sha256", "replacement_sha256"}
    for index, raw in enumerate(raw_replacements):
        if not isinstance(raw, dict) or set(raw) != required_keys:
            raise RefactorError(f"replacement[{index}] must contain exactly {sorted(required_keys)}")
        target = checked_repo_git_path(raw.get("target"), f"replacement[{index}].target")
        source = checked_repo_git_path(raw.get("source"), f"replacement[{index}].source")
        if target not in locked_set or not target.endswith(".v"):
            raise RefactorError(f"replacement target is not a locked Verilog file: {target}")
        if PurePosixPath(source).name != PurePosixPath(target).name:
            raise RefactorError(
                f"replacement source basename must match target: source={source} target={target}"
            )
        if target in targets or source in sources:
            raise RefactorError(f"replacement spec has a duplicate target or source: {target} / {source}")
        base_sha = raw.get("base_sha256")
        replacement_sha = raw.get("replacement_sha256")
        if not isinstance(base_sha, str) or SHA256_HEX_PATTERN.fullmatch(base_sha) is None:
            raise RefactorError(f"replacement[{index}].base_sha256 is invalid")
        if not isinstance(replacement_sha, str) or SHA256_HEX_PATTERN.fullmatch(replacement_sha) is None:
            raise RefactorError(f"replacement[{index}].replacement_sha256 is invalid")
        base_payload = git_blob(f"{base_commit}:{target}")
        actual_base_sha = sha256_bytes(base_payload)
        if base_sha != actual_base_sha:
            raise RefactorError(
                f"replacement base blob mismatch for {target}: expected={base_sha} actual={actual_base_sha}"
            )
        source_entry = git_regular_blob_entry(source_head, source)
        replacement_payload = git_blob(f"{source_head}:{source}")
        actual_replacement_sha = sha256_bytes(replacement_payload)
        if replacement_sha != actual_replacement_sha:
            raise RefactorError(
                f"replacement source blob mismatch for {source}: expected={replacement_sha} actual={actual_replacement_sha}"
            )
        validate_replacement_verilog(
            replacement_payload,
            f"{source_head}:{source}",
            base_payload=base_payload,
        )
        replacements.append(
            ComponentReplacement(
                target=target,
                source=source,
                base_sha256=base_sha,
                replacement_sha256=replacement_sha,
                source_oid=source_entry["oid"],
                source_mode=source_entry["mode"],
                payload=replacement_payload,
            )
        )
        targets.add(target)
        sources.add(source)

    return ComponentReplacementPlan(
        spec_path=spec_path,
        spec_commit=source_state["head"],
        spec_sha256=sha256_bytes(spec_payload),
        source_head=source_state["head"],
        source_tree=source_state["tree"],
        source_branch=source_state["branch"],
        source_status_entry_count=source_state["status_entry_count"],
        source_porcelain_clean=source_state["porcelain_clean"],
        source_semantic_clean=source_state["semantic_clean"],
        source_eol_normalization_only=source_state["eol_normalization_only"],
        base_candidate_commit=base_commit,
        replacements=tuple(replacements),
    )


def report_path(out_dir: Path, name: str) -> Path:
    return out_dir / "reports" / f"{name}.json"


def checked_out_dir(value: str | Path) -> Path:
    """Allow generated output outside the repo or below the repo's build/ only."""
    requested = Path(value).absolute()
    reject_link_or_reparse_path(requested, "generated OUT_DIR")
    path = requested.resolve()
    try:
        relative = path.relative_to(REPO_ROOT)
    except ValueError:
        relative = None
    if relative is not None and (not relative.parts or relative.parts[0] != "build"):
        raise RefactorError(
            f"generated OUT_DIR inside the repository must be below {REPO_ROOT / 'build'}: {path}"
        )
    path.mkdir(parents=True, exist_ok=True)
    reject_link_or_reparse_path(path, "generated OUT_DIR")
    return path


def checked_iteration_id(value: str) -> str:
    if not ITERATION_ID_PATTERN.fullmatch(value):
        raise RefactorError(f"invalid iteration id: {value!r}")
    return value


def host_path(value: str) -> Path:
    """Resolve a manifest path on Windows or map a Windows drive into WSL."""
    match = re.fullmatch(r"([A-Za-z]):[/\\](.*)", value)
    if os.name == "posix" and match:
        parts = re.split(r"[/\\]+", match.group(2))
        return Path("/mnt") / match.group(1).lower() / Path(*parts)
    return Path(value).expanduser().resolve()


def vivado_version_matches(text: str, manifest: dict[str, str]) -> bool:
    return bool(
        re.search(rf"\bvivado\s+v{re.escape(manifest['vivado'])}\b", text, re.IGNORECASE)
        and re.search(rf"\bSW Build\s+{re.escape(manifest['vivado_build'])}\b", text)
        and not re.search(r"\b(?:ERROR|FATAL)\b", text, re.IGNORECASE)
    )


def iteration_report_path(out_dir: Path, iteration_id: str, name: str) -> Path:
    return out_dir / "reports" / "iterations" / checked_iteration_id(iteration_id) / f"{name}.json"


def publication_marker_path(report_path: Path) -> Path:
    report_path = Path(report_path).absolute()
    return report_path.with_name(f"{report_path.name}.publication.json")


def checked_publication_id(value: str) -> str:
    if not isinstance(value, str) or not ITERATION_ID_PATTERN.fullmatch(value):
        raise RefactorError(f"invalid report publication id: {value!r}")
    return value


def remove_stale_report_publication(report_path: Path) -> None:
    for path in (publication_marker_path(report_path), Path(report_path).absolute()):
        reject_link_or_reparse_path(path, "report publication cleanup")
        try:
            identity = path.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(identity.st_mode):
            raise RefactorError(f"report publication path must be a regular file: {path}")
        path.unlink()


def write_publication_marker(
    report_path: Path,
    report: dict[str, Any],
    *,
    command: str,
    iteration_id: str,
    publication_id: str,
    publisher_sha256: str,
) -> tuple[Path, str]:
    report_path = Path(report_path).absolute()
    publication_id = checked_publication_id(publication_id)
    reject_link_or_reparse_path(report_path, "report publication")
    if re.fullmatch(r"[0-9a-f]{64}", publisher_sha256) is None:
        raise RefactorError("report publisher SHA256 is invalid")
    expected_report_sha256 = json_sha256(report)
    if sha256_file(report_path) != expected_report_sha256:
        raise RefactorError(f"report changed before publication marker: {report_path}")
    marker = {
        "schema_version": 1,
        "iteration_id": checked_iteration_id(iteration_id),
        "operation": command,
        "publication_id": publication_id,
        "report_name": report_path.name,
        "report_sha256": expected_report_sha256,
        "publisher_sha256": publisher_sha256,
    }
    marker_path = publication_marker_path(report_path)
    write_json(marker_path, marker)
    marker_sha256 = json_sha256(marker)
    if sha256_file(marker_path) != marker_sha256:
        raise RefactorError(f"publication marker changed while being written: {marker_path}")
    return marker_path, marker_sha256


def require_report_publication(
    report_path: Path,
    report: dict[str, Any],
    report_sha256: str,
    *,
    command: str,
    iteration_id: str,
    publication_id: str,
    publisher_sha256: str,
) -> tuple[Path, dict[str, Any], str]:
    publication_id = checked_publication_id(publication_id)
    marker_path = publication_marker_path(report_path)
    reject_link_or_reparse_path(Path(report_path).absolute(), "published report")
    reject_link_or_reparse_path(marker_path, "report publication marker")
    if re.fullmatch(r"[0-9a-f]{64}", publisher_sha256) is None:
        raise RefactorError("report publisher SHA256 is invalid")
    if sha256_file(Path(report_path)) != report_sha256:
        raise RefactorError(f"published report changed before consumption: {report_path}")
    marker, marker_sha256 = read_json_file_with_sha256(marker_path)
    if not isinstance(marker, dict) or set(marker) != {
        "schema_version",
        "iteration_id",
        "operation",
        "publication_id",
        "report_name",
        "report_sha256",
        "publisher_sha256",
    }:
        raise RefactorError(f"publication marker has an invalid schema: {marker_path}")
    expected = {
        "schema_version": 1,
        "iteration_id": checked_iteration_id(iteration_id),
        "operation": command,
        "publication_id": publication_id,
        "report_name": Path(report_path).name,
        "report_sha256": report_sha256,
        "publisher_sha256": publisher_sha256,
    }
    if marker != expected or report_sha256 != json_sha256(report):
        raise RefactorError(f"report publication marker mismatch: {marker_path}")
    return marker_path, marker, marker_sha256


def print_report(report: dict[str, Any]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    *,
    expected: Any = None,
    actual: Any = None,
    detail: str | None = None,
) -> None:
    entry: dict[str, Any] = {"name": name, "status": "pass" if passed else "fail"}
    if expected is not None:
        entry["expected"] = expected
    if actual is not None:
        entry["actual"] = actual
    if detail:
        entry["detail"] = detail
    checks.append(entry)


def tool_output(command: Sequence[str], cwd: Path = REPO_ROOT) -> tuple[int, str]:
    result = run_command(command, cwd=cwd)
    return result.exit_code, (result.stdout + "\n" + result.stderr).strip()


def command_doctor(args: argparse.Namespace) -> int:
    out_dir = checked_out_dir(args.out_dir)
    manifest = parse_lock(MANIFEST_PATH)
    checks: list[dict[str, Any]] = []
    missing = sorted(REQUIRED_MANIFEST_KEYS - manifest.keys())
    add_check(checks, "manifest.required_keys", not missing, expected="all required", actual=missing)
    pending = sorted(key for key, value in manifest.items() if "pending" in value.lower())
    add_check(checks, "manifest.no_pending_values", not pending, expected=[], actual=pending)

    branch = git_text(["branch", "--show-current"])
    add_check(
        checks,
        "git.protected_branch",
        branch not in {"main", "master"} and branch.startswith("refactor/"),
        expected="refactor/* and not main/master",
        actual=branch,
    )
    head = git_text(["rev-parse", "HEAD"])
    status = git_text(["status", "--porcelain=v1", "--untracked-files=all"])
    add_check(checks, "git.head", bool(re.fullmatch(r"[0-9a-f]{40}", head)), actual=head)
    add_check(
        checks,
        "git.worktree_recorded",
        True,
        actual={"dirty": bool(status), "entries": status.splitlines()},
        detail="A dirty iteration branch is allowed; the exact entries are evidence.",
    )

    candidate = manifest["team_golden_candidate"]
    candidate_actual = git_text(["rev-parse", f"{candidate}^{{commit}}"])
    add_check(checks, "golden.commit", candidate_actual == candidate, expected=candidate, actual=candidate_actual)
    golden_files = read_golden_files()
    tree_paths = set(git_text(["ls-tree", "-r", "--name-only", candidate]).splitlines())
    absent = [item for item in golden_files if item not in tree_paths]
    add_check(checks, "golden.files_exist", not absent, expected="all locked files", actual=absent)
    add_check(
        checks,
        "golden.dead_files_excluded",
        not (set(golden_files) & FORBIDDEN_GOLDEN_FILES),
        expected=sorted(FORBIDDEN_GOLDEN_FILES),
        actual=sorted(set(golden_files) & FORBIDDEN_GOLDEN_FILES),
    )

    build_sbt = (REPO_ROOT / "spinal" / "build.sbt").read_text(encoding="utf-8")
    properties = (REPO_ROOT / "spinal" / "project" / "build.properties").read_text(encoding="utf-8")
    plugins = (REPO_ROOT / "spinal" / "project" / "plugins.sbt").read_text(encoding="utf-8")
    scalafmt = (REPO_ROOT / "spinal" / ".scalafmt.conf").read_text(encoding="utf-8")
    add_check(checks, "spinal.scala_version", 'scalaVersion := lockedVersion("scala")' in build_sbt)
    add_check(checks, "spinal.spinalhdl_version", 'lockedVersion("spinalhdl")' in build_sbt)
    add_check(checks, "spinal.scalatest_version", 'lockedVersion("scalatest")' in build_sbt)
    add_check(checks, "spinal.sbt_version", f'sbt.version={manifest["sbt"]}' in properties)
    add_check(checks, "spinal.sbt_scalafmt_version", f'% "{manifest["sbt_scalafmt"]}"' in plugins)
    add_check(checks, "spinal.scalafmt_version", f'version = {manifest["scalafmt"]}' in scalafmt)
    add_check(
        checks,
        "spinal.idsl_plugin",
        "spinalhdl-idsl-plugin" in build_sbt and "compilerPlugin" in build_sbt,
        expected="matching compilerPlugin declaration",
        actual="present" if "spinalhdl-idsl-plugin" in build_sbt else "missing",
    )

    vivado_home = host_path(args.vivado_home or manifest["vivado_windows_home"])
    vivado_launcher = vivado_home / "bin" / "vivado.bat"
    vivado_binary = vivado_home / "bin" / "unwrapped" / "win64.o" / "vivado.exe"
    for name, path, key in (
        ("launcher", vivado_launcher, "vivado_windows_launcher_sha256"),
        ("binary", vivado_binary, "vivado_windows_binary_sha256"),
    ):
        actual_hash = sha256_file(path) if path.is_file() else None
        add_check(
            checks,
            f"vivado.{name}_sha256",
            actual_hash == manifest[key],
            expected=manifest[key],
            actual=actual_hash or f"missing: {path}",
        )
    add_check(
        checks,
        "vivado.edition_lock",
        manifest["vivado_edition"] == "ML Standard",
        expected="ML Standard",
        actual=manifest["vivado_edition"],
        detail="The product edition is user-confirmed; device/license availability is checked by rtl-fpga.",
    )
    vivado_probe: CommandResult | None = None
    if os.name == "nt" and vivado_launcher.is_file():
        probe_script = REPO_ROOT / "tools" / "vivado_probe.tcl"
        vivado_probe = run_command(
            [
                str(vivado_launcher),
                "-mode",
                "batch",
                "-nolog",
                "-nojournal",
                "-notrace",
                "-source",
                str(probe_script),
            ],
            cwd=REPO_ROOT,
            timeout=180,
        )
        version_text = vivado_probe.stdout + "\n" + vivado_probe.stderr
        version_ok = vivado_probe.exit_code == 0 and vivado_version_matches(version_text, manifest)
        version_actual = next(
            (
                line
                for line in version_text.splitlines()
                if line.startswith("NSCSCC_VIVADO_VERSION=")
            ),
            f"exit={vivado_probe.exit_code}",
        )
    else:
        version_ok = vivado_launcher.is_file() and vivado_binary.is_file()
        version_actual = f"hash-only host check: {vivado_home}"
    add_check(
        checks,
        "vivado.version_build",
        version_ok,
        expected=f"Vivado v{manifest['vivado']} SW Build {manifest['vivado_build']}",
        actual=version_actual,
        detail=(
            "Windows launcher output is parsed; WSL validates the same locked Windows files by hash."
        ),
    )

    report = {
        "schema_version": 1,
        "command": "doctor",
        "generated_at": now_iso(),
        "repo": str(REPO_ROOT),
        "head_sha": head,
        "branch": branch,
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "golden_files_sha256": sha256_file(GOLDEN_FILES_PATH),
        "vivado_home": str(vivado_home),
        "vivado_probe": vivado_probe.as_dict() if vivado_probe is not None else None,
        "checks": checks,
    }
    report["status"] = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    write_json(report_path(out_dir, "doctor"), report)
    print_report(report)
    return 0 if report["status"] == "pass" else 1


def verify_download(
    checks: list[dict[str, Any]],
    downloads: Path,
    manifest: dict[str, str],
    prefix: str,
) -> None:
    asset = downloads / manifest[f"{prefix}_asset"]
    exists = asset.is_file()
    add_check(checks, f"tool.{prefix}.asset_exists", exists, expected=str(asset), actual=exists)
    if exists:
        actual = sha256_file(asset)
        expected = manifest[f"{prefix}_sha256"]
        add_check(checks, f"tool.{prefix}.sha256", actual == expected, expected=expected, actual=actual)


def installed_tool_specs(tool_root: Path, manifest: dict[str, str]) -> list[tuple[str, Path, str]]:
    gcc_bin = (
        tool_root
        / "loongson-gnu-toolchain-8.3-x86_64-loongarch32r-linux-gnusf-v2.0"
        / "bin"
    )

    def executable(name: str) -> Path:
        resolved = shutil.which(name)
        return Path(resolved).resolve() if resolved else Path(f"/__missing__/{name}")

    return [
        ("gcc", gcc_bin / "loongarch32r-linux-gnusf-gcc", "gcc_binary_sha256"),
        ("as", gcc_bin / "loongarch32r-linux-gnusf-as", "as_binary_sha256"),
        ("ld", gcc_bin / "loongarch32r-linux-gnusf-ld", "ld_binary_sha256"),
        (
            "gcc_cc1",
            tool_root
            / "loongson-gnu-toolchain-8.3-x86_64-loongarch32r-linux-gnusf-v2.0"
            / "libexec"
            / "gcc"
            / "loongarch32r-linux-gnusf"
            / "8.3.0"
            / "cc1",
            "gcc_cc1_sha256",
        ),
        (
            "gcc_collect2",
            tool_root
            / "loongson-gnu-toolchain-8.3-x86_64-loongarch32r-linux-gnusf-v2.0"
            / "libexec"
            / "gcc"
            / "loongarch32r-linux-gnusf"
            / "8.3.0"
            / "collect2",
            "gcc_collect2_sha256",
        ),
        ("nemu", tool_root / "nemu" / "la32r-nemu-interpreter-so", "nemu_binary_sha256"),
        ("picolibc", tool_root / "picolibc" / "lib" / "libc.a", "picolibc_libc_sha256"),
        (
            "qemu",
            tool_root / "la32r-QEMU-x86_64-ubuntu-22.04" / "qemu-system-loongarch32",
            "qemu_binary_sha256",
        ),
        ("sbt", tool_root / f"sbt-{manifest['sbt']}" / "bin" / "sbt", "sbt_script_sha256"),
        (
            "sbt_launch_jar",
            tool_root / f"sbt-{manifest['sbt']}" / "bin" / "sbt-launch.jar",
            "sbt_launch_jar_sha256",
        ),
        ("verilator", executable("verilator"), "verilator_binary_sha256"),
        ("verilator_engine", Path("/usr/bin/verilator_bin"), "verilator_engine_sha256"),
        (
            "verilator_runtime",
            Path("/usr/share/verilator/include/verilated.cpp"),
            "verilator_runtime_sha256",
        ),
        ("yosys", executable("yosys"), "yosys_binary_sha256"),
        ("java", executable("java"), "java_binary_sha256"),
        ("python", Path(sys.executable).resolve(), "python_binary_sha256"),
        (
            "jdk_modules",
            Path("/usr/lib/jvm/java-17-openjdk-amd64/lib/modules"),
            "jdk_modules_sha256",
        ),
    ]


def tool_fingerprints(tool_root: Path, manifest: dict[str, str]) -> list[dict[str, Any]]:
    fingerprints: list[dict[str, Any]] = []
    for name, path, manifest_key in installed_tool_specs(tool_root, manifest):
        fingerprints.append(
            {
                "name": name,
                "path": str(path),
                "manifest_key": manifest_key,
                "expected_sha256": manifest[manifest_key],
                "actual_sha256": sha256_file(path) if path.is_file() else None,
                "size": path.stat().st_size if path.is_file() else None,
            }
        )
    return fingerprints


def require_tool_fingerprints(tool_root: Path, manifest: dict[str, str]) -> list[dict[str, Any]]:
    fingerprints = tool_fingerprints(tool_root, manifest)
    failures = [
        item
        for item in fingerprints
        if item["actual_sha256"] is None or item["actual_sha256"] != item["expected_sha256"]
    ]
    if failures:
        details = ", ".join(
            f"{item['name']} expected={item['expected_sha256']} actual={item['actual_sha256']}"
            for item in failures
        )
        raise RefactorError(f"installed tool fingerprint mismatch: {details}")
    return fingerprints


def expected_chiplab_doctor_check_names(
    tool_root: Path, manifest: dict[str, str]
) -> set[str]:
    names = {
        "host.locked_platform",
        "chiplab.path",
        "chiplab.filesystem",
        "chiplab.commit",
        "chiplab.clean",
        "chiplab.mycpu_gitlink",
        "chiplab.symlink_checkout",
        "chiplab.official_paths",
    }
    names.update(
        f"tool.{prefix}.{suffix}"
        for prefix in ("la32r_gcc", "nemu", "picolibc", "qemu", "sbt")
        for suffix in ("asset_exists", "sha256")
    )
    names.update(
        f"tool.{name}.installed_sha256"
        for name, _, _ in installed_tool_specs(tool_root, manifest)
    )
    names.update(
        f"tool.{name}.version"
        for name in ("verilator", "yosys", "java", "python", "gcc", "sbt")
    )
    names.update(
        f"package.{package}.dpkg_verify"
        for package in ("verilator", "yosys", "openjdk-17-jre-headless")
    )
    return names


def command_chiplab_doctor(args: argparse.Namespace) -> int:
    out_dir = checked_out_dir(args.out_dir)
    chiplab = Path(args.chiplab_ref).resolve() if args.chiplab_ref else Path()
    tool_root = Path(args.tool_root).resolve()
    manifest = parse_lock(MANIFEST_PATH)
    checks: list[dict[str, Any]] = []

    host_ok = os.name == "posix" and platform.system() == "Linux" and platform.machine().lower() in {
        "x86_64",
        "amd64",
    }
    add_check(
        checks,
        "host.locked_platform",
        host_ok,
        expected="Linux x86_64 (WSL or native)",
        actual={"os_name": os.name, "system": platform.system(), "machine": platform.machine()},
    )
    add_check(checks, "chiplab.path", bool(args.chiplab_ref) and chiplab.is_dir(), actual=str(chiplab))
    if chiplab.is_dir():
        fs_type = filesystem_type(chiplab)
        add_check(
            checks,
            "chiplab.filesystem",
            fs_type.lower() not in {"9p", "v9fs", "drvfs", "fuseblk"},
            expected="Linux filesystem preserving symlinks",
            actual=fs_type,
        )
        head = git_text(["rev-parse", "HEAD"], cwd=chiplab)
        add_check(checks, "chiplab.commit", head == manifest["chiplab_commit"], expected=manifest["chiplab_commit"], actual=head)
        status = git_text(["status", "--porcelain=v1"], cwd=chiplab)
        add_check(checks, "chiplab.clean", not status, expected="clean", actual=status or "clean")
        submodule = chiplab / "IP" / "myCPU"
        submodule_head = git_text(["rev-parse", "HEAD"], cwd=submodule) if submodule.is_dir() else "missing"
        add_check(
            checks,
            "chiplab.mycpu_gitlink",
            submodule_head == manifest["chiplab_mycpu_gitlink"],
            expected=manifest["chiplab_mycpu_gitlink"],
            actual=submodule_head,
        )
        symlink = chiplab / "software" / "examples" / "func" / "func_lab19" / "Makefile"
        add_check(
            checks,
            "chiplab.symlink_checkout",
            symlink.is_symlink(),
            expected="real symlink",
            actual=f"symlink={symlink.is_symlink()} path={symlink}",
            detail="Windows checkouts that materialize mode 120000 as text are rejected.",
        )
        required_paths = [
            "sims/verilator/run_prog/configure.sh",
            "sims/verilator/run_prog/Makefile",
            "sims/verilator/run_prog/Makefile_run",
            "sims/verilator/testbench/difftest.cpp",
            "software/examples/func/func_lab19",
        ]
        absent = [path for path in required_paths if not (chiplab / path).exists()]
        add_check(checks, "chiplab.official_paths", not absent, expected="all present", actual=absent)

    downloads = tool_root.parent / "downloads"
    for prefix in ("la32r_gcc", "nemu", "picolibc", "qemu", "sbt"):
        verify_download(checks, downloads, manifest, prefix)

    specs = installed_tool_specs(tool_root, manifest)
    spec_paths = {name: path for name, path, _ in specs}
    fingerprints = tool_fingerprints(tool_root, manifest)
    for item in fingerprints:
        add_check(
            checks,
            f"tool.{item['name']}.installed_sha256",
            item["actual_sha256"] == item["expected_sha256"],
            expected=item["expected_sha256"],
            actual=item["actual_sha256"] or f"missing: {item['path']}",
        )

    version_commands = {
        "verilator": (["verilator", "--version"], manifest["verilator"]),
        "yosys": (["yosys", "-V"], manifest["yosys"]),
        "java": (["java", "-version"], manifest["jdk"].split("+")[0]),
        "python": ([str(spec_paths["python"]), "--version"], manifest["python"]),
        "gcc": ([str(spec_paths["gcc"]), "--version"], "8.3.0"),
        "sbt": ([str(spec_paths["sbt"]), "--script-version"], manifest["sbt"]),
    }
    for name, (command, expected) in version_commands.items():
        exit_code, output = tool_output(command, cwd=tool_root if tool_root.is_dir() else REPO_ROOT)
        add_check(
            checks,
            f"tool.{name}.version",
            exit_code == 0 and expected in output,
            expected=expected,
            actual=output.splitlines()[0] if output else f"exit={exit_code}",
        )
    for package in ("verilator", "yosys", "openjdk-17-jre-headless"):
        result = run_command(["dpkg", "-V", package], cwd=tool_root, timeout=120)
        verification_output = (result.stdout + "\n" + result.stderr).strip()
        add_check(
            checks,
            f"package.{package}.dpkg_verify",
            result.exit_code == 0 and not verification_output,
            expected="dpkg -V exit=0 with no modified package files",
            actual=verification_output or f"exit={result.exit_code}",
        )

    report = {
        "schema_version": 1,
        "command": "chiplab-doctor",
        "generated_at": now_iso(),
        "chiplab_reference": str(chiplab),
        "tool_root": str(tool_root),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "evaluator_sha256": sha256_file(Path(__file__)),
        "repo_head_sha": git_text(["rev-parse", "HEAD"]),
        "tool_fingerprints": fingerprints,
        "checks": checks,
    }
    report["status"] = "pass" if checks and all(item["status"] == "pass" for item in checks) else "fail"
    write_json(report_path(out_dir, "chiplab-doctor"), report)
    print_report(report)
    return 0 if report["status"] == "pass" else 1


def reset_generated_dir(path: Path, allowed_root: Path, purpose: str) -> None:
    path = path.resolve()
    allowed_root = allowed_root.resolve()
    try:
        path.relative_to(allowed_root)
    except ValueError as error:
        raise RefactorError(f"refusing to replace {path}: outside {allowed_root}") from error
    if path == allowed_root:
        raise RefactorError(f"refusing to replace generated root itself: {path}")
    if path.exists():
        marker = path / GENERATED_MARKER
        if not marker.is_file():
            raise RefactorError(f"refusing to replace unmarked directory: {path}")
        marker_data = validate_json_file(marker)
        if marker_data.get("resolved_path") != str(path) or marker_data.get("purpose") != purpose:
            raise RefactorError(
                f"refusing to replace directory with mismatched marker: {path}"
            )
        shutil.rmtree(path)
    path.mkdir(parents=True)
    write_json(
        path / GENERATED_MARKER,
        {
            "schema_version": 1,
            "purpose": purpose,
            "resolved_path": str(path),
            "created_at": now_iso(),
        },
    )


def export_golden(
    out_dir: Path,
    candidate_override: str | None = None,
    *,
    diagnostic: bool = False,
    export_id: str = "standalone",
    replacement_plan: ComponentReplacementPlan | None = None,
) -> tuple[Path, dict[str, Any]]:
    manifest = parse_lock(MANIFEST_PATH)
    if candidate_override and not diagnostic:
        raise RefactorError("candidate override requires explicit --diagnostic mode")
    requested_candidate = candidate_override or manifest["team_golden_candidate"]
    candidate = git_text(["rev-parse", f"{requested_candidate}^{{commit}}"])
    base_candidate_locked = candidate == manifest["team_golden_candidate"]
    if replacement_plan is not None:
        if not diagnostic or not base_candidate_locked or candidate_override is not None:
            raise RefactorError("component replacements require the locked base in diagnostic mode")
        if replacement_plan.base_candidate_commit != candidate:
            raise RefactorError("component replacement base differs from the locked candidate")
    candidate_locked = base_candidate_locked and replacement_plan is None
    if not diagnostic and not candidate_locked:
        raise RefactorError("baseline export must use the locked candidate")
    files = read_golden_files()
    basenames = [Path(item).name for item in files]
    duplicates = sorted({name for name in basenames if basenames.count(name) > 1})
    if duplicates:
        raise RefactorError(f"golden export has duplicate basenames: {duplicates}")
    destination = out_dir / "reference" / "golden-rtl" / checked_iteration_id(export_id)
    reset_generated_dir(destination, out_dir, "golden-rtl-export")
    entries: list[dict[str, Any]] = []
    replacements = {
        item.target: item for item in replacement_plan.replacements
    } if replacement_plan is not None else {}
    for source_path in files:
        base_payload = git_blob(f"{candidate}:{source_path}")
        base_tree_entry = git_regular_blob_entry(candidate, source_path)
        replacement = replacements.get(source_path)
        payload = replacement.payload if replacement is not None else base_payload
        target = destination / Path(source_path).name
        target.write_bytes(payload)
        entry: dict[str, Any] = {
            "path": target.name,
            "logical_path": source_path,
            "source": (
                f"{replacement_plan.source_head}:{replacement.source}"
                if replacement is not None and replacement_plan is not None
                else f"{candidate}:{source_path}"
            ),
            "source_kind": "replacement" if replacement is not None else "golden",
            "sha256": sha256_bytes(payload),
            "size": len(payload),
            "base_source": f"{candidate}:{source_path}",
            "base_sha256": sha256_bytes(base_payload),
            "base_size": len(base_payload),
            "base_oid": base_tree_entry["oid"],
            "base_mode": base_tree_entry["mode"],
        }
        if replacement is not None and replacement_plan is not None:
            entry.update(
                {
                    "replacement_source": f"{replacement_plan.source_head}:{replacement.source}",
                    "replacement_source_path": replacement.source,
                    "replacement_oid": replacement.source_oid,
                    "replacement_mode": replacement.source_mode,
                    "replacement_spec_source": (
                        f"{replacement_plan.spec_commit}:{replacement_plan.spec_path}"
                    ),
                    "replacement_spec_sha256": replacement_plan.spec_sha256,
                }
            )
        entries.append(entry)
    selection_payload = json.dumps(
        [
            {
                "logical_path": entry["logical_path"],
                "source": entry["source"],
                "sha256": entry["sha256"],
                "size": entry["size"],
            }
            for entry in entries
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    export_manifest = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "candidate_commit": candidate,
        "candidate_locked": candidate_locked,
        "base_candidate_locked": base_candidate_locked,
        "baseline_exact": replacement_plan is None and base_candidate_locked,
        "provenance_mode": (
            "mixed_candidate"
            if replacement_plan is not None
            else "locked_candidate"
            if base_candidate_locked
            else "diagnostic_candidate"
        ),
        "gate_kind": (
            "component_replacement"
            if replacement_plan is not None
            else "baseline_candidate"
            if base_candidate_locked
            else "candidate_override"
        ),
        "mode": "diagnostic" if diagnostic else "baseline",
        "gate_eligible": not diagnostic and candidate_locked,
        "evaluator_sha256": sha256_file(Path(__file__)),
        "files_lock_sha256": sha256_file(GOLDEN_FILES_PATH),
        "files": entries,
        "file_count": len(entries),
        "replacement_count": len(replacements),
        "base_selected_count": len(entries) - len(replacements),
        "selection_sha256": sha256_bytes(selection_payload),
        "component_replacement": (
            replacement_plan.metadata() if replacement_plan is not None else None
        ),
        "excluded_dead_or_backup": sorted(FORBIDDEN_GOLDEN_FILES),
    }
    write_json(destination / "manifest.json", export_manifest)
    return destination, export_manifest


def command_golden_export(args: argparse.Namespace) -> int:
    out_dir = checked_out_dir(args.out_dir)
    current_report = report_path(out_dir, "golden-export")
    if current_report.exists():
        current_report.unlink()
    destination, export_manifest = export_golden(
        out_dir,
        args.candidate_commit,
        diagnostic=args.diagnostic,
    )
    gate_eligible = bool(export_manifest["gate_eligible"])
    report = {
        "schema_version": 1,
        "command": "golden-export",
        "generated_at": now_iso(),
        "status": "pass" if gate_eligible else "diagnostic",
        "gate_eligible": gate_eligible,
        "mode": export_manifest["mode"],
        "destination": str(destination),
        "candidate_commit": export_manifest["candidate_commit"],
        "candidate_locked": export_manifest["candidate_locked"],
        "file_count": len(export_manifest["files"]),
        "manifest_sha256": sha256_file(destination / "manifest.json"),
    }
    write_json(current_report, report)
    print_report(report)
    return 0


def ensure_symlink(link: Path, target: Path) -> None:
    if link.exists() or link.is_symlink():
        raise RefactorError(f"toolchain overlay target already exists: {link}")
    link.symlink_to(target, target_is_directory=target.is_dir())


def filesystem_type(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    result = run_command(["stat", "-f", "-c", "%T", str(path)], cwd=path)
    require_command(result, f"detect filesystem type for {path}")
    return result.stdout.strip()


def smoke_generated_relative_paths(case: str) -> frozenset[str]:
    require_locked_smoke_case(case)
    run_dir = PurePosixPath("sims/verilator/run_prog")
    return frozenset(
        {
            str(run_dir / "obj_dir"),
            str(run_dir / "output"),
            str(run_dir / "tmp"),
            str(run_dir / "obj" / f"{case}_obj"),
            f"software/examples/{case}/obj",
            str(run_dir / "log" / f"{case}_log"),
            str(run_dir / "log" / "compile.log"),
            str(run_dir / "config-software.mak"),
            str(run_dir / "config.log"),
        }
    )


def official_workspace_fingerprint(
    work: Path, *, extra_excluded_paths: Iterable[str] = ()
) -> dict[str, Any]:
    """Hash every non-DUT file in the fresh chiplab copy, including ignored extras."""
    excluded_roots = {".git", "IP/myCPU", "toolchains"}
    excluded_files = {GENERATED_MARKER, ".refactor-overlay.json", ".rtl-smoke.lock"}
    extra_excluded = frozenset(extra_excluded_paths)
    for relative in extra_excluded:
        pure = PurePosixPath(relative)
        if (
            not relative
            or pure.is_absolute()
            or ".." in pure.parts
            or "." in pure.parts
            or "\\" in relative
        ):
            raise RefactorError(f"invalid workspace fingerprint exclusion: {relative!r}")

    def excluded(relative: str) -> bool:
        prefixes = excluded_roots | set(extra_excluded)
        return relative in prefixes or any(
            relative.startswith(prefix + "/") for prefix in prefixes
        )

    entries: list[dict[str, Any]] = []
    for root, directories, files in os.walk(work, followlinks=False):
        root_path = Path(root)
        relative_root = root_path.relative_to(work).as_posix()
        kept_directories: list[str] = []
        for name in sorted(directories):
            path = root_path / name
            relative = path.relative_to(work).as_posix()
            if excluded(relative):
                continue
            if path.is_symlink():
                entries.append({"path": relative, "kind": "symlink", "target": os.readlink(path)})
            else:
                kept_directories.append(name)
        directories[:] = kept_directories
        for name in sorted(files):
            path = root_path / name
            relative = path.relative_to(work).as_posix()
            if relative in excluded_files or relative_root in excluded_roots:
                continue
            if excluded(relative):
                continue
            if path.is_symlink():
                entries.append({"path": relative, "kind": "symlink", "target": os.readlink(path)})
            else:
                entries.append(
                    {
                        "path": relative,
                        "kind": "file",
                        "size": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"sha256": sha256_bytes(canonical), "entry_count": len(entries)}


def require_official_worktree_integrity(work: Path, expected: dict[str, Any]) -> None:
    current = official_workspace_fingerprint(work)
    if current != expected:
        raise RefactorError(
            f"official chiplab inputs changed after overlay: expected={expected} actual={current}"
        )
    diff = git(
        ["diff", "--name-only", "HEAD", "--", ".", ":(exclude)IP/myCPU"],
        cwd=work,
    )
    require_command(diff, "check official chiplab tracked inputs")
    if diff.stdout.strip():
        raise RefactorError(f"official chiplab tracked inputs are dirty: {diff.stdout.strip()}")


def require_post_smoke_official_integrity(
    work: Path,
    expected: dict[str, Any],
    case: str,
) -> None:
    exclusions = smoke_generated_relative_paths(case)
    current = official_workspace_fingerprint(
        work, extra_excluded_paths=exclusions
    )
    if current != expected:
        raise RefactorError(
            "official chiplab inputs changed outside the smoke generated-path contract: "
            f"expected={expected} actual={current}"
        )
    diff = git(
        ["diff", "--name-only", "HEAD", "--", ".", ":(exclude)IP/myCPU"],
        cwd=work,
    )
    require_command(diff, "check post-smoke official tracked inputs")
    if diff.stdout.strip():
        raise RefactorError(
            f"official chiplab tracked inputs are dirty after smoke: {diff.stdout.strip()}"
        )


def require_passing_chiplab_doctor(
    out_dir: Path,
    chiplab_ref: Path,
    tool_root: Path,
    max_age_seconds: int,
) -> tuple[Path, dict[str, Any], str]:
    if not 1 <= max_age_seconds <= 86400:
        raise RefactorError("doctor freshness limit must be between 1 second and 24 hours")
    path = report_path(out_dir, "chiplab-doctor")
    if not path.is_file():
        raise RefactorError(f"missing chiplab doctor report: {path}")
    data, report_sha256 = read_json_file_with_sha256(path)
    checks = data.get("checks")
    if (
        data.get("schema_version") != 1
        or data.get("command") != "chiplab-doctor"
        or data.get("status") != "pass"
        or not isinstance(checks, list)
        or not checks
        or any(not isinstance(item, dict) for item in checks)
        or any(item.get("status") != "pass" for item in checks if isinstance(item, dict))
    ):
        raise RefactorError("chiplab doctor report is not a complete PASS")
    check_names = [item.get("name") for item in checks]
    if any(not isinstance(name, str) or not name for name in check_names):
        raise RefactorError("chiplab doctor report has a malformed check name")
    if len(check_names) != len(set(check_names)):
        raise RefactorError("chiplab doctor report has duplicate check names")
    manifest = parse_lock(MANIFEST_PATH)
    expected_names = expected_chiplab_doctor_check_names(tool_root, manifest)
    if set(check_names) != expected_names:
        raise RefactorError(
            "chiplab doctor check set is incomplete or unexpected: "
            f"missing={sorted(expected_names - set(check_names))} "
            f"extra={sorted(set(check_names) - expected_names)}"
        )
    expected = {
        "chiplab_reference": str(chiplab_ref),
        "tool_root": str(tool_root),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "evaluator_sha256": sha256_file(Path(__file__)),
        "repo_head_sha": git_text(["rev-parse", "HEAD"]),
    }
    mismatches = {
        key: {"expected": value, "actual": data.get(key)}
        for key, value in expected.items()
        if data.get(key) != value
    }
    if mismatches:
        raise RefactorError(f"chiplab doctor binding mismatch: {mismatches}")
    try:
        generated = datetime.fromisoformat(str(data["generated_at"])).timestamp()
    except (KeyError, TypeError, ValueError) as error:
        raise RefactorError("chiplab doctor has an invalid generated_at") from error
    age = time.time() - generated
    if age < -300 or age > max_age_seconds:
        raise RefactorError(
            f"chiplab doctor is stale or from the future: age={age:.1f}s limit={max_age_seconds}s"
        )
    current_fingerprints = require_tool_fingerprints(tool_root, manifest)
    if data.get("tool_fingerprints") != current_fingerprints:
        raise RefactorError("installed tool fingerprints changed after chiplab doctor")
    return path, data, report_sha256


def command_chiplab_overlay(args: argparse.Namespace) -> int:
    out_dir = checked_out_dir(args.out_dir)
    iteration_id = checked_iteration_id(args.iteration_id)
    work_root = Path(args.work_root).resolve()
    require_nonoverlapping_validation_roots(out_dir, work_root)
    run_id = f"overlay-{time.time_ns()}-{os.getpid()}"
    overlay_report_path = iteration_report_path(out_dir, iteration_id, "chiplab-overlay")
    locks: list[ValidationLock] = []
    report: dict[str, Any] | None = None
    report_sha256: str | None = None
    result_code = 2
    try:
        locks.append(
            acquire_iteration_lock(out_dir, iteration_id, "chiplab-overlay", run_id)
        )
        locks.append(
            acquire_iteration_lock(work_root, iteration_id, "chiplab-overlay", run_id)
        )
        remove_stale_report_publication(overlay_report_path)
        result_code = _command_chiplab_overlay_locked(args, run_id)
        stored, report_sha256 = read_json_file_with_sha256(overlay_report_path)
        if not isinstance(stored, dict):
            raise RefactorError("chiplab overlay report must be a JSON object")
        report = stored
        require_report_publication(
            overlay_report_path,
            report,
            report_sha256,
            command="chiplab-overlay",
            iteration_id=iteration_id,
            publication_id=run_id,
            publisher_sha256=sha256_file(Path(__file__)),
        )
    finally:
        body_error = sys.exc_info()[1]
        try:
            release_validation_locks(locks)
        except BaseException as release_error:
            if body_error is not None:
                raise RefactorError(
                    "chiplab overlay failed and validation lock release also failed: "
                    f"body={body_error}; release={release_error}"
                ) from body_error
            raise
    if report is None or report_sha256 is None:
        raise RefactorError("chiplab overlay completed without a published report")
    print_report(report)
    return result_code


def validate_overlay_source_selection(
    args: argparse.Namespace,
) -> tuple[str | None, str | None]:
    replacement_spec = getattr(args, "replacement_spec", None)
    source_head = getattr(args, "source_head", None)
    if bool(replacement_spec) != bool(source_head):
        raise RefactorError("--replacement-spec and --source-head must be provided together")
    if args.dut_source == "mixed":
        if not args.diagnostic or not replacement_spec or not source_head:
            raise RefactorError(
                "mixed DUT requires --diagnostic, --replacement-spec, and --source-head"
            )
        if args.candidate_commit:
            raise RefactorError(
                "mixed DUT always uses the locked base; --candidate-commit is forbidden"
            )
    elif replacement_spec or source_head:
        raise RefactorError(
            "component replacement arguments are only valid with --dut-source mixed"
        )
    if args.candidate_commit and not args.diagnostic:
        raise RefactorError("candidate override requires explicit --diagnostic mode")
    if args.dut_source == "official" and not args.diagnostic:
        raise RefactorError("official control runs require explicit --diagnostic mode")
    return replacement_spec, source_head


def _command_chiplab_overlay_locked(args: argparse.Namespace, run_id: str) -> int:
    if os.name != "posix":
        raise RefactorError("chiplab overlay must run in WSL/Linux so official symlinks remain symlinks")
    out_dir = checked_out_dir(args.out_dir)
    iteration_id = checked_iteration_id(args.iteration_id)
    overlay_report_path = iteration_report_path(out_dir, iteration_id, "chiplab-overlay")
    remove_stale_report_publication(overlay_report_path)
    work_root = Path(args.work_root).resolve()
    chiplab_ref = Path(args.chiplab_ref).resolve()
    tool_root = Path(args.tool_root).resolve()
    manifest = parse_lock(MANIFEST_PATH)
    replacement_spec, source_head = validate_overlay_source_selection(args)
    if not chiplab_ref.is_dir():
        raise RefactorError(f"missing --chiplab-ref directory: {chiplab_ref}")
    fs_type = filesystem_type(work_root)
    if fs_type.lower() in {"9p", "v9fs", "drvfs", "fuseblk"}:
        raise RefactorError(
            f"chiplab work root must be on Linux ext4, not {fs_type}: {work_root}"
        )
    if git_text(["rev-parse", "HEAD"], cwd=chiplab_ref) != manifest["chiplab_commit"]:
        raise RefactorError("chiplab reference commit differs from manifest.lock")
    if git_text(["status", "--porcelain=v1"], cwd=chiplab_ref):
        raise RefactorError("chiplab reference is dirty")
    if git_text(["rev-parse", "HEAD"], cwd=chiplab_ref / "IP" / "myCPU") != manifest["chiplab_mycpu_gitlink"]:
        raise RefactorError("chiplab reference myCPU gitlink differs from manifest.lock")
    doctor_path, doctor_report, doctor_sha256 = require_passing_chiplab_doctor(
        out_dir,
        chiplab_ref,
        tool_root,
        args.doctor_max_age_seconds,
    )
    runtime_fingerprints = require_tool_fingerprints(tool_root, manifest)

    golden_dir: Path | None = None
    golden_manifest: dict[str, Any] | None = None
    replacement_plan: ComponentReplacementPlan | None = None
    if args.dut_source == "mixed":
        assert replacement_spec is not None and source_head is not None
        replacement_plan = load_component_replacement_plan(replacement_spec, source_head)
        if doctor_report.get("repo_head_sha") != replacement_plan.source_head:
            raise RefactorError("chiplab doctor source HEAD differs from mixed replacement source")
    if args.dut_source in {"candidate", "mixed"}:
        golden_dir, golden_manifest = export_golden(
            out_dir,
            args.candidate_commit,
            diagnostic=args.diagnostic,
            export_id=iteration_id,
            replacement_plan=replacement_plan,
        )
    work = work_root / iteration_id
    reset_generated_dir(work, work_root, "chiplab-validation-copy")
    marker_payload = json.loads((work / GENERATED_MARKER).read_text(encoding="utf-8"))
    (work / GENERATED_MARKER).unlink()
    work.rmdir()

    clone = run_command(
        ["git", "clone", "--local", "--no-hardlinks", "--no-checkout", str(chiplab_ref), str(work)],
        cwd=out_dir,
        timeout=300,
    )
    if work.is_dir():
        write_json(work / GENERATED_MARKER, marker_payload)
    require_command(clone, "clone isolated chiplab")
    checkout = git(["checkout", "--detach", manifest["chiplab_commit"]], cwd=work, timeout=120)
    require_command(checkout, "checkout locked chiplab")
    config_submodule = git(
        ["config", "submodule.IP/myCPU.url", str(chiplab_ref / "IP" / "myCPU")], cwd=work
    )
    require_command(config_submodule, "configure local myCPU source")
    update_submodule = git(
        [
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "update",
            "--init",
            "--recursive",
            "IP/myCPU",
        ],
        cwd=work,
        timeout=300,
    )
    require_command(update_submodule, "checkout locked myCPU")

    if not (work / "software" / "examples" / "func" / "func_lab19" / "Makefile").is_symlink():
        raise RefactorError("isolated chiplab lost official symlinks")

    tools_dir = work / "toolchains"
    gcc_dir = tool_root / "loongson-gnu-toolchain-8.3-x86_64-loongarch32r-linux-gnusf-v2.0"
    for name, target in (
        (gcc_dir.name, gcc_dir),
        ("nemu", tool_root / "nemu"),
        ("picolibc", tool_root / "picolibc"),
    ):
        if not target.exists():
            raise RefactorError(f"missing locked tool: {target}")
        ensure_symlink(tools_dir / name, target)
    mycpu = work / "IP" / "myCPU"
    removed_stale: list[str] = []
    overlay_entries: list[dict[str, Any]] = []
    support_files: list[dict[str, Any]] = []
    if args.dut_source in {"candidate", "mixed"}:
        assert golden_dir is not None and golden_manifest is not None
        upstream_header = git_blob(f"{manifest['openla500_upstream']}:mycpu.h", cwd=mycpu)
        upstream_header_sha = sha256_bytes(upstream_header)
        if upstream_header_sha != manifest["openla500_mycpu_h_sha256"]:
            raise RefactorError(
                "openLA500 mycpu.h differs from manifest.lock: "
                f"expected {manifest['openla500_mycpu_h_sha256']}, got {upstream_header_sha}"
            )
        (mycpu / "mycpu.h").write_bytes(upstream_header)
        support_files.append(
            {
                "path": "IP/myCPU/mycpu.h",
                "source": f"{manifest['openla500_upstream']}:mycpu.h",
                "sha256": upstream_header_sha,
                "size": len(upstream_header),
                "reason": "a158aa8 omitted this included header; the chiplab gitlink header lacks LACC definitions",
            }
        )
        locked_names = {Path(path).name for path in read_golden_files()}
        for old_rtl in mycpu.glob("*.v"):
            if old_rtl.name not in locked_names:
                removed_stale.append(old_rtl.name)
                old_rtl.unlink()
        for entry in golden_manifest["files"]:
            source = golden_dir / entry["path"]
            target = mycpu / entry["path"]
            shutil.copyfile(source, target)
            overlay_entries.append(
                {
                    **entry,
                    "overlay_path": str(target.relative_to(work)),
                    "overlay_sha256": sha256_file(target),
                }
            )
    else:
        for target in sorted([*mycpu.glob("*.v"), *mycpu.glob("*.h")]):
            overlay_entries.append(
                {
                    "path": target.name,
                    "source": f"{manifest['chiplab_mycpu_gitlink']}:{target.name}",
                    "sha256": sha256_file(target),
                    "size": target.stat().st_size,
                    "overlay_path": str(target.relative_to(work)),
                    "overlay_sha256": sha256_file(target),
                }
            )
    if not (mycpu / "LICENSE").is_file() or not (mycpu / "mycpu.h").is_file():
        raise RefactorError("official LICENSE or required mycpu.h is missing")
    support_files.append(
        {
            "path": "IP/myCPU/LICENSE",
            "source": f"{manifest['chiplab_mycpu_gitlink']}:LICENSE",
            "sha256": sha256_file(mycpu / "LICENSE"),
            "size": (mycpu / "LICENSE").stat().st_size,
            "reason": "preserved official Mulan PSL v2 license",
        }
    )
    top_text = (mycpu / "mycpu_top.v").read_text(encoding="utf-8")
    if len(re.findall(r"(?m)^\s*module\s+core_top\b", top_text)) != 1:
        raise RefactorError("golden overlay does not define exactly one core_top")

    overlay_manifest = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "iteration_id": iteration_id,
        "run_id": run_id,
        "dut_source": args.dut_source,
        "provenance_mode": (
            golden_manifest.get("provenance_mode") if golden_manifest is not None else "official_control"
        ),
        "gate_kind": (
            golden_manifest.get("gate_kind") if golden_manifest is not None else "official_control"
        ),
        "mode": "diagnostic" if args.diagnostic else "baseline",
        "gate_eligible": bool(
            not args.diagnostic
            and args.dut_source == "candidate"
            and golden_manifest is not None
            and golden_manifest["candidate_locked"]
        ),
        "chiplab_reference": str(chiplab_ref),
        "chiplab_commit": git_text(["rev-parse", "HEAD"], cwd=work),
        "chiplab_tree": git_text(["rev-parse", "HEAD^{tree}"], cwd=work),
        "mycpu_reference_commit": manifest["chiplab_mycpu_gitlink"],
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "golden_files_lock_sha256": sha256_file(GOLDEN_FILES_PATH),
        "golden_export_manifest_sha256": (
            sha256_file(golden_dir / "manifest.json") if golden_dir is not None else None
        ),
        "golden_candidate_commit": golden_manifest["candidate_commit"] if golden_manifest is not None else None,
        "candidate_locked": golden_manifest["candidate_locked"] if golden_manifest is not None else None,
        "base_candidate_locked": (
            golden_manifest.get("base_candidate_locked") if golden_manifest is not None else None
        ),
        "baseline_exact": golden_manifest.get("baseline_exact") if golden_manifest is not None else None,
        "component_replacement": (
            golden_manifest.get("component_replacement") if golden_manifest is not None else None
        ),
        "selection_sha256": (
            golden_manifest.get("selection_sha256") if golden_manifest is not None else None
        ),
        "files": overlay_entries,
        "removed_stale_verilog": sorted(removed_stale),
        "preserved_official_files": ["IP/myCPU/LICENSE"],
        "support_files": support_files,
        "tool_links": {
            "gcc": str(gcc_dir),
            "nemu": str(tool_root / "nemu"),
            "picolibc": str(tool_root / "picolibc"),
        },
        "tool_fingerprints": runtime_fingerprints,
        "doctor_report": str(doctor_path),
        "doctor_report_sha256": doctor_sha256,
        "doctor_generated_at": doctor_report["generated_at"],
        "evaluator_sha256": sha256_file(Path(__file__)),
        "official_workspace_fingerprint": official_workspace_fingerprint(work),
        "post_smoke_official_workspace_fingerprint": official_workspace_fingerprint(
            work,
            extra_excluded_paths=smoke_generated_relative_paths(LOCKED_SMOKE_CASE),
        ),
        "work_filesystem": fs_type,
    }
    if replacement_plan is not None:
        final_source_state = require_clean_source_head(replacement_plan.source_head)
        if (
            final_source_state["tree"] != replacement_plan.source_tree
            or final_source_state["branch"] != replacement_plan.source_branch
        ):
            raise RefactorError("replacement source tree or branch changed during overlay")
    verify_dut_source_bindings(work, overlay_manifest, manifest)
    overlay_manifest_path = iteration_report_path(out_dir, iteration_id, "chiplab-overlay-manifest")
    write_json(overlay_manifest_path, overlay_manifest)
    marker_path = work / ".refactor-overlay.json"
    write_json(marker_path, overlay_manifest)
    stored_manifest, overlay_manifest_sha256 = read_json_file_with_sha256(
        overlay_manifest_path
    )
    stored_marker, marker_sha256 = read_json_file_with_sha256(marker_path)
    if stored_manifest != overlay_manifest or stored_marker != overlay_manifest:
        raise RefactorError("overlay manifest changed while it was being published")
    verify_dut_source_bindings(work, stored_manifest, manifest)
    gate_eligible = bool(overlay_manifest["gate_eligible"])
    report = {
        "schema_version": 1,
        "command": "chiplab-overlay",
        "generated_at": now_iso(),
        "status": "pass" if gate_eligible else "diagnostic",
        "mode": overlay_manifest["mode"],
        "gate_eligible": gate_eligible,
        "iteration_id": iteration_id,
        "run_id": run_id,
        "work_dir": str(work),
        "file_count": len(overlay_entries),
        "dut_source": args.dut_source,
        "provenance_mode": overlay_manifest["provenance_mode"],
        "gate_kind": overlay_manifest["gate_kind"],
        "candidate_locked": overlay_manifest["candidate_locked"],
        "base_candidate_locked": overlay_manifest["base_candidate_locked"],
        "baseline_exact": overlay_manifest["baseline_exact"],
        "golden_candidate_commit": overlay_manifest["golden_candidate_commit"],
        "selection_sha256": overlay_manifest["selection_sha256"],
        "component_replacement": overlay_manifest["component_replacement"],
        "replacement_count": (
            len(replacement_plan.replacements) if replacement_plan is not None else 0
        ),
        "overlay_manifest": str(overlay_manifest_path),
        "overlay_manifest_sha256": overlay_manifest_sha256,
        "work_marker_sha256": marker_sha256,
        "doctor_report_sha256": doctor_sha256,
        "evaluator_sha256": sha256_file(Path(__file__)),
    }
    write_json(overlay_report_path, report)
    if sha256_file(overlay_report_path) != json_sha256(report):
        raise RefactorError("chiplab overlay report changed during publication")
    write_publication_marker(
        overlay_report_path,
        report,
        command="chiplab-overlay",
        iteration_id=iteration_id,
        publication_id=run_id,
        publisher_sha256=sha256_file(Path(__file__)),
    )
    return 0


def parse_verilator_warnings(text: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for line in text.splitlines():
        match = re.search(r"%Warning(?:-([A-Z0-9_]+))?:\s*(.*)", line)
        if match:
            warnings.append(
                {
                    "category": match.group(1) or "GENERIC",
                    "scope": "dut" if "/IP/myCPU/" in line.replace("\\", "/") else "official_environment",
                    "line": line.strip(),
                }
            )
    return warnings


def parse_build_errors(text: str) -> list[str]:
    patterns = (
        r"^%Error(?:-[A-Z0-9_]+)?:",
        r"^%Fatal(?:-[A-Z0-9_]+)?:",
        r"^make(?:\[\d+\])?: \*\*\*",
        r"(?:g\+\+|gcc|collect2): (?:fatal )?error:",
        r"No rule to make target",
    )
    return [
        line.strip()
        for line in text.splitlines()
        if any(re.search(pattern, line.strip(), re.IGNORECASE) for pattern in patterns)
    ]


def parse_simulation_log(
    text: str, *, expected_termination: str | None = None
) -> dict[str, Any]:
    if expected_termination not in {None, "good_trap", "end_by_syscall"}:
        raise RefactorError(f"unsupported simulation termination expectation: {expected_termination}")
    bad_patterns = {
        "difftest_mismatch": r"different at pc",
        "trace_error": r"Error\(Code:",
        "time_limit": r"Time limit exceeded",
        "dead_clock": r"CPU status no change",
        "unhandled": r"Reached unhandled situation",
        "bad_trap": r"HIT BAD TRAP",
        "abort": r"\bABORT\b",
    }
    failures = [name for name, pattern in bad_patterns.items() if re.search(pattern, text, re.IGNORECASE)]
    instruction_match = re.search(r"total instruction\s+is\s+(\d+)", text)
    clock_match = re.search(r"total clock\s+is\s+(\d+)", text)
    instructions = int(instruction_match.group(1)) if instruction_match else 0
    clocks = int(clock_match.group(1)) if clock_match else 0
    markers = {
        "difftest_library_loaded": bool(re.search(r"Using .*la32r-nemu-interpreter-so for difftest", text)),
        "difftest_enabled": "Difftest enabled." in text,
        "good_trap": "HIT GOOD TRAP" in text,
        "end_by_syscall": "END by Syscall" in text,
        "reached_test_end": "Reached test end PC." in text,
        "nonzero_instructions": instructions > 0,
        "nonzero_clocks": clocks > 0,
    }
    if markers["end_by_syscall"]:
        termination_mode = "end_by_syscall"
    elif markers["good_trap"]:
        termination_mode = "good_trap"
    else:
        termination_mode = "missing"
    termination_valid = (
        termination_mode != "missing"
        if expected_termination is None
        else markers[expected_termination]
    )
    diagnostic_lines = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"different at pc|Error\(Code:|Both Error|HIT BAD TRAP|ABORT", line)
    ]
    if not termination_valid:
        failures.append("termination_marker")
        diagnostic_lines.append(
            f"termination marker mismatch: expected {expected_termination or 'good_trap-or-syscall'}, "
            f"observed {termination_mode}"
        )
    mismatch_lines = [line.strip() for line in text.splitlines() if "different at pc" in line]
    mandatory_markers = (
        markers["difftest_library_loaded"]
        and markers["difftest_enabled"]
        and termination_valid
        and markers["reached_test_end"]
        and markers["nonzero_instructions"]
        and markers["nonzero_clocks"]
    )
    return {
        "status": "pass" if mandatory_markers and not failures else "fail",
        "markers": markers,
        "termination_expectation": expected_termination,
        "termination_mode": termination_mode,
        "termination_valid": termination_valid,
        "failures": failures,
        "instructions": instructions,
        "clocks": clocks,
        "first_mismatch": mismatch_lines[0] if mismatch_lines else None,
        "failure_excerpt": diagnostic_lines[:20],
    }


def smoke_environment(work: Path, tool_root: Path) -> dict[str, str]:
    home = os.environ.get("HOME")
    if not home:
        raise RefactorError("HOME is required for locked chiplab tools")
    path_entries = [
        tool_root / "loongson-gnu-toolchain-8.3-x86_64-loongarch32r-linux-gnusf-v2.0" / "bin",
        tool_root / "la32r-QEMU-x86_64-ubuntu-22.04",
        Path("/usr/local/bin"),
        Path("/usr/bin"),
        Path("/bin"),
    ]
    return {
        "HOME": home,
        "PATH": os.pathsep.join(str(item) for item in path_entries),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "CHIPLAB_HOME": str(work),
    }


def parse_make_assignments(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:?+]?=\s*(.*?)\s*$", raw_line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def gate_counts(*, executed: bool, passed: bool) -> dict[str, int]:
    if not executed:
        return {"planned": 1, "executed": 0, "passed": 0, "failed": 0, "skipped": 1}
    return {
        "planned": 1,
        "executed": 1,
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "skipped": 0,
    }


def require_locked_smoke_case(case: str) -> None:
    if case != LOCKED_SMOKE_CASE:
        raise RefactorError(
            f"rtl-smoke is locked to {LOCKED_SMOKE_CASE}; broader suites use their dedicated gate"
        )


def verilator_build_integrity_passed(
    build: CommandResult | None,
    *,
    compile_fresh: bool,
    errors: Sequence[str] = (),
    artifacts_fresh: bool = True,
) -> bool:
    return bool(
        build is not None
        and build.exit_code == 0
        and not build.timed_out
        and compile_fresh
        and not errors
        and artifacts_fresh
    )


def verilator_compile_check_passed(
    build: CommandResult | None,
    *,
    compile_fresh: bool,
    warnings: Sequence[dict[str, str]],
    errors: Sequence[str] = (),
    artifacts_fresh: bool = True,
) -> bool:
    return bool(
        verilator_build_integrity_passed(
            build,
            compile_fresh=compile_fresh,
            errors=errors,
            artifacts_fresh=artifacts_fresh,
        )
        and not warnings
    )


def acquire_iteration_lock(
    out_dir: Path,
    iteration_id: str,
    operation: str,
    run_id: str,
) -> ValidationLock:
    if operation not in {"chiplab-overlay", "rtl-smoke", "identity-compare"}:
        raise RefactorError(f"unsupported validation lock operation: {operation}")
    lock_root_candidate = out_dir / ".locks" / "iterations"
    reject_link_or_reparse_path(lock_root_candidate, "iteration validation lock root")
    lock_root = resolved_below(
        lock_root_candidate, out_dir, "iteration validation lock root"
    )
    lock_root.mkdir(parents=True, exist_ok=True)
    reject_link_or_reparse_path(lock_root, "iteration validation lock root")
    lock_candidate = lock_root / f"{checked_iteration_id(iteration_id)}.lock"
    reject_link_or_reparse_path(lock_candidate, "iteration validation lock")
    lock_path = resolved_below(
        lock_candidate,
        out_dir,
        "iteration validation lock",
    )
    payload = {
        "schema_version": 1,
        "iteration_id": iteration_id,
        "operation": operation,
        "run_id": run_id,
        "pid": os.getpid(),
        "created_at": now_iso(),
        "evaluator_sha256": sha256_file(Path(__file__)),
    }
    return _acquire_validation_lock(
        lock_path,
        payload,
        exists_message=(
            f"iteration validation lock already exists: {lock_path}; "
            "wait for the active overlay/smoke process or inspect a stale lock explicitly"
        ),
    )


def require_nonoverlapping_validation_roots(out_dir: Path, work_root: Path) -> None:
    out_resolved = out_dir.resolve()
    work_resolved = work_root.resolve()
    if (
        out_resolved == work_resolved
        or out_resolved in work_resolved.parents
        or work_resolved in out_resolved.parents
    ):
        raise RefactorError(
            "OUT_DIR and CHIPLAB_WORK_ROOT must be non-overlapping directories: "
            f"out_dir={out_resolved} work_root={work_resolved}"
        )


def acquire_smoke_lock(work: Path, iteration_id: str, run_id: str) -> ValidationLock:
    lock_candidate = work / ".rtl-smoke.lock"
    reject_link_or_reparse_path(lock_candidate, "RTL smoke lock")
    lock_path = resolved_below(lock_candidate, work, "RTL smoke lock")
    payload = {
        "schema_version": 1,
        "iteration_id": iteration_id,
        "operation": "rtl-smoke-workspace",
        "run_id": run_id,
        "pid": os.getpid(),
        "created_at": now_iso(),
        "evaluator_sha256": sha256_file(Path(__file__)),
    }
    return _acquire_validation_lock(
        lock_path,
        payload,
        exists_message=(
            f"RTL smoke lock already exists: {lock_path}; rebuild the isolated overlay "
            "instead of reusing a workspace from an interrupted run"
        ),
    )


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("validation lock write made no progress")
        offset += written


def _acquire_validation_lock(
    path: Path,
    payload: dict[str, Any],
    *,
    exists_message: str,
) -> ValidationLock:
    try:
        descriptor = _open_exclusive_lock_descriptor(path)
    except FileExistsError as error:
        raise RefactorError(exists_message) from error
    identity = os.fstat(descriptor)
    lease = ValidationLock(
        path=path,
        iteration_id=str(payload["iteration_id"]),
        operation=str(payload["operation"]),
        run_id=str(payload["run_id"]),
        descriptor=descriptor,
        device=identity.st_dev,
        inode=identity.st_ino,
    )
    try:
        encoded = (
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        _write_all(descriptor, encoded)
        os.fsync(descriptor)
    except BaseException:
        _remove_owned_lock(lease, allow_partial=True)
        raise
    return lease


def _open_exclusive_lock_descriptor(path: Path) -> int:
    if os.name != "nt":
        return os.open(
            path,
            os.O_RDWR
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )

    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        str(path),
        0x80000000 | 0x40000000 | 0x00010000,
        0x00000001 | 0x00000002,
        None,
        1,
        0x00000080 | 0x00200000,
        None,
    )
    if handle == wintypes.HANDLE(-1).value:
        error_code = ctypes.get_last_error()
        if error_code in {80, 183}:
            raise FileExistsError(error_code, "validation lock already exists", str(path))
        raise ctypes.WinError(error_code)
    try:
        return msvcrt.open_osfhandle(
            handle, os.O_RDWR | getattr(os, "O_BINARY", 0)
        )
    except BaseException:
        kernel32.CloseHandle(handle)
        raise


def _mark_windows_lock_for_deletion(descriptor: int) -> None:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class FileDispositionInfo(ctypes.Structure):
        _fields_ = [("delete_file", wintypes.BOOL)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    set_information = kernel32.SetFileInformationByHandle
    set_information.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    set_information.restype = wintypes.BOOL
    information = FileDispositionInfo(True)
    handle = msvcrt.get_osfhandle(descriptor)
    if not set_information(
        handle,
        4,
        ctypes.byref(information),
        ctypes.sizeof(information),
    ):
        raise ctypes.WinError(ctypes.get_last_error())


def _remove_owned_lock(lease: ValidationLock, *, allow_partial: bool) -> None:
    descriptor_open = True
    try:
        descriptor_identity = os.fstat(lease.descriptor)
        try:
            path_identity = lease.path.lstat()
        except FileNotFoundError as error:
            raise RefactorError(
                f"validation lock disappeared before release: {lease.path}"
            ) from error
        if (
            not stat.S_ISREG(path_identity.st_mode)
            or (descriptor_identity.st_dev, descriptor_identity.st_ino)
            != (lease.device, lease.inode)
            or (path_identity.st_dev, path_identity.st_ino)
            != (lease.device, lease.inode)
        ):
            raise RefactorError(
                f"validation lock ownership changed before release: {lease.path}"
            )
        if not allow_partial:
            os.lseek(lease.descriptor, 0, os.SEEK_SET)
            chunks: list[bytes] = []
            while True:
                chunk = os.read(lease.descriptor, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            try:
                stored = strict_json_loads(b"".join(chunks).decode("utf-8"), str(lease.path))
            except (UnicodeError, RefactorError) as error:
                raise RefactorError(f"validation lock metadata is unreadable: {lease.path}") from error
            if (
                not isinstance(stored, dict)
                or stored.get("iteration_id") != lease.iteration_id
                or stored.get("operation") != lease.operation
                or stored.get("run_id") != lease.run_id
            ):
                raise RefactorError(
                    f"validation lock metadata changed before release: {lease.path}"
                )
        if os.name == "nt":
            _mark_windows_lock_for_deletion(lease.descriptor)
        else:
            lease.path.unlink()
    finally:
        if descriptor_open:
            os.close(lease.descriptor)


def release_validation_lock(lease: ValidationLock) -> None:
    _remove_owned_lock(lease, allow_partial=False)


def release_validation_locks(leases: list[ValidationLock]) -> None:
    """Release every lease and report all failures after cleanup is attempted."""

    failures: list[tuple[Path, BaseException]] = []
    for lease in reversed(leases):
        try:
            release_validation_lock(lease)
        except BaseException as error:
            failures.append((lease.path, error))
    if failures:
        details = "; ".join(f"{path}: {error}" for path, error in failures)
        if not isinstance(failures[0][1], Exception):
            raise failures[0][1]
        raise RefactorError(f"validation lock release failed: {details}") from failures[0][1]


def abandon_validation_lock(lease: ValidationLock) -> None:
    os.close(lease.descriptor)


def clean_smoke_generated_paths(work: Path, run_dir: Path, case: str) -> list[str]:
    paths = [
        run_dir / "obj_dir",
        run_dir / "output",
        run_dir / "tmp",
        run_dir / "obj" / f"{case}_obj",
        work / "software" / "examples" / case / "obj",
        run_dir / "log" / f"{case}_log",
        run_dir / "log" / "compile.log",
        run_dir / "config-software.mak",
        run_dir / "config.log",
    ]
    removed: list[str] = []
    for path in paths:
        target = resolved_below(path, work, "RTL smoke generated path")
        if target.exists() or target.is_symlink():
            remove_generated_path(target, work)
            removed.append(str(target))
    return removed


def require_posix_validation_environment() -> None:
    if os.name != "posix":
        raise RefactorError("rtl-smoke must run in the WSL/Linux validation environment")


def remove_generated_path(path: Path, work: Path) -> None:
    target = resolved_below(path, work, "generated build path")
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)


def fresh_build_artifacts(
    run_dir: Path,
    case: str,
    build_started_ns: int,
) -> tuple[list[dict[str, Any]], bool]:
    paths = [
        run_dir / "log" / "compile.log",
        run_dir / "obj_dir" / "Vsimu_top.mk",
        run_dir / "obj_dir" / "Vsimu_top__ALL.a",
        run_dir / "output",
        run_dir / "obj" / f"{case}_obj" / "obj" / "main.elf",
        run_dir / "obj" / f"{case}_obj" / "obj" / "rom.vlog",
    ]
    entries: list[dict[str, Any]] = []
    all_fresh = True
    for path in paths:
        exists = path.is_file()
        fresh = exists and path.stat().st_mtime_ns >= build_started_ns
        all_fresh = all_fresh and fresh
        entries.append(
            {
                "path": str(path),
                "exists": exists,
                "fresh": fresh,
                "size": path.stat().st_size if exists else None,
                "sha256": sha256_file(path) if exists else None,
            }
        )
    return entries, all_fresh


def resolved_below(path: Path, root: Path, context: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise RefactorError(f"{context} escapes validation workspace: {path}") from error
    return resolved


def verify_overlay_files(work: Path, overlay: dict[str, Any]) -> None:
    mycpu = work / "IP" / "myCPU"
    hdl_suffixes = {".v", ".sv", ".vh", ".svh", ".h"}
    expected_hdl: set[str] = set()
    overlay_paths: set[str] = set()
    logical_names: set[str] = set()
    files = overlay.get("files")
    support_files = overlay.get("support_files")
    if not isinstance(files, list) or not isinstance(support_files, list):
        raise RefactorError("overlay manifest file lists are malformed")
    for entry in files:
        if not isinstance(entry, dict):
            raise RefactorError("overlay manifest has a malformed file entry")
        overlay_path = str(entry.get("overlay_path", ""))
        logical_name = str(entry.get("path", ""))
        expected_path = f"IP/myCPU/{logical_name}"
        if (
            not logical_name
            or "\\" in logical_name
            or any(ord(character) < 32 for character in logical_name)
            or PurePosixPath(logical_name).name != logical_name
            or overlay_path != expected_path
        ):
            raise RefactorError(
                f"overlay path is not the canonical DUT target: path={logical_name!r} overlay={overlay_path!r}"
            )
        if overlay_path in overlay_paths or logical_name in logical_names:
            raise RefactorError(f"overlay manifest has duplicate DUT path: {overlay_path}")
        overlay_paths.add(overlay_path)
        logical_names.add(logical_name)
        relative = Path(overlay_path)
        unresolved_target = work / relative
        if unresolved_target.is_symlink():
            raise RefactorError(f"overlay file must not be a symlink: {relative}")
        target = resolved_below(unresolved_target, work, "overlay file")
        expected_target = (mycpu / logical_name).resolve()
        if target != expected_target or not target.is_file():
            raise RefactorError(f"overlay file disappeared or moved: {relative}")
        actual_sha = sha256_file(target)
        if actual_sha != entry.get("overlay_sha256") or actual_sha != entry.get("sha256"):
            raise RefactorError(f"overlay file hash mismatch: {relative}")
        if entry.get("size") is not None and target.stat().st_size != entry.get("size"):
            raise RefactorError(f"overlay file size mismatch: {relative}")
        if target.suffix.lower() in hdl_suffixes:
            expected_hdl.add(logical_name)
    allowed_support_paths = {"IP/myCPU/LICENSE", "IP/myCPU/mycpu.h"}
    support_paths: list[str] = []
    for entry in support_files:
        if not isinstance(entry, dict):
            raise RefactorError("overlay manifest has a malformed support-file entry")
        support_path = str(entry.get("path", ""))
        support_paths.append(support_path)
        if support_path not in allowed_support_paths:
            raise RefactorError(f"overlay manifest has an unapproved support file: {support_path}")
        unresolved_target = work / Path(support_path)
        if unresolved_target.is_symlink():
            raise RefactorError(f"support file must not be a symlink: {support_path}")
        target = resolved_below(unresolved_target, work, "support file")
        if not target.is_file() or sha256_file(target) != entry.get("sha256"):
            raise RefactorError(f"support file hash mismatch: {entry.get('path')}")
        if entry.get("size") is not None and target.stat().st_size != entry.get("size"):
            raise RefactorError(f"support file size mismatch: {entry.get('path')}")
        if target.suffix.lower() in hdl_suffixes:
            expected_hdl.add(target.relative_to(mycpu).as_posix())
    if len(support_paths) != len(set(support_paths)):
        raise RefactorError("overlay manifest has duplicate support-file paths")
    actual_hdl: set[str] = set()
    for path in mycpu.rglob("*"):
        relative = path.relative_to(mycpu).as_posix()
        if path.is_symlink():
            raise RefactorError(f"DUT tree contains a symlink: IP/myCPU/{relative}")
        if path.is_file() and path.suffix.lower() in hdl_suffixes:
            actual_hdl.add(relative)
    if actual_hdl != expected_hdl:
        raise RefactorError(
            "unexpected or missing DUT HDL after overlay: "
            f"expected={sorted(expected_hdl)} actual={sorted(actual_hdl)}"
        )


def verify_candidate_support_bindings(
    work: Path,
    overlay: dict[str, Any],
    manifest: dict[str, str],
) -> None:
    support_entries = overlay.get("support_files", [])
    if not isinstance(support_entries, list):
        raise RefactorError("candidate support-file list is malformed")
    support = {
        entry.get("path"): entry
        for entry in support_entries
        if isinstance(entry, dict)
    }
    expected_support = {"IP/myCPU/mycpu.h", "IP/myCPU/LICENSE"}
    if len(support_entries) != len(expected_support) or set(support) != expected_support:
        raise RefactorError(
            "candidate support files differ from the locked header/license set: "
            f"actual={sorted(str(item) for item in support)}"
        )
    header = support.get("IP/myCPU/mycpu.h")
    mycpu = work / "IP" / "myCPU"
    header_payload = git_blob(
        f"{manifest['openla500_upstream']}:mycpu.h",
        cwd=mycpu,
    )
    if (
        header is None
        or header.get("source") != f"{manifest['openla500_upstream']}:mycpu.h"
        or header.get("sha256") != sha256_bytes(header_payload)
        or header.get("sha256") != manifest["openla500_mycpu_h_sha256"]
        or header.get("size") != len(header_payload)
    ):
        raise RefactorError("openLA500 support header binding mismatch")
    license_entry = support.get("IP/myCPU/LICENSE")
    license_payload = git_blob(
        f"{manifest['chiplab_mycpu_gitlink']}:LICENSE",
        cwd=mycpu,
    )
    if (
        license_entry is None
        or license_entry.get("source") != f"{manifest['chiplab_mycpu_gitlink']}:LICENSE"
        or license_entry.get("sha256") != sha256_bytes(license_payload)
        or license_entry.get("size") != len(license_payload)
    ):
        raise RefactorError("official license binding mismatch")


def verify_candidate_source_bindings(
    work: Path,
    overlay: dict[str, Any],
    manifest: dict[str, str],
) -> None:
    candidate = overlay.get("golden_candidate_commit")
    if not isinstance(candidate, str) or re.fullmatch(r"[0-9a-f]{40}", candidate) is None:
        raise RefactorError("candidate overlay lacks a full source commit")
    locked = candidate == manifest["team_golden_candidate"]
    expected_provenance = "locked_candidate" if locked else "diagnostic_candidate"
    expected_gate_kind = "baseline_candidate" if locked else "candidate_override"
    if (
        overlay.get("dut_source") != "candidate"
        or overlay.get("candidate_locked") is not locked
        or overlay.get("base_candidate_locked") is not locked
        or overlay.get("baseline_exact") is not locked
        or overlay.get("provenance_mode") != expected_provenance
        or overlay.get("gate_kind") != expected_gate_kind
        or overlay.get("component_replacement") is not None
    ):
        raise RefactorError("candidate overlay provenance shape does not match its source commit")
    locked_paths = read_golden_files()
    entries = overlay.get("files")
    if not isinstance(entries, list) or len(entries) != len(locked_paths):
        raise RefactorError("candidate overlay file count differs from golden allowlist")
    by_logical: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RefactorError("candidate overlay has a malformed file entry")
        logical_path = entry.get("logical_path")
        if not isinstance(logical_path, str) or logical_path in by_logical:
            raise RefactorError("candidate overlay has a missing or duplicate logical path")
        by_logical[logical_path] = entry
    selection: list[dict[str, Any]] = []
    for source_path in locked_paths:
        source = f"{candidate}:{source_path}"
        entry = by_logical.get(source_path)
        if entry is None:
            raise RefactorError(f"candidate overlay is missing selected source: {source}")
        expected_target = f"IP/myCPU/{Path(source_path).name}"
        if (
            entry.get("overlay_path") != expected_target
            or entry.get("path") != Path(source_path).name
            or entry.get("source") != source
            or entry.get("source_kind") != "golden"
        ):
            raise RefactorError(f"candidate overlay target mismatch for {source}")
        payload = git_blob(source)
        expected_hash = sha256_bytes(payload)
        tree_entry = git_regular_blob_entry(candidate, source_path)
        if (
            entry.get("sha256") != expected_hash
            or entry.get("size") != len(payload)
            or entry.get("base_source") != source
            or entry.get("base_sha256") != expected_hash
            or entry.get("base_size") != len(payload)
            or entry.get("base_oid") != tree_entry["oid"]
            or entry.get("base_mode") != tree_entry["mode"]
        ):
            raise RefactorError(f"candidate source blob mismatch for {source}")
        selection.append(
            {
                "logical_path": source_path,
                "source": source,
                "sha256": expected_hash,
                "size": len(payload),
            }
        )
    if set(by_logical) != set(locked_paths):
        raise RefactorError("candidate overlay logical paths differ from the locked exact union")
    selection_sha = sha256_bytes(
        json.dumps(selection, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    if overlay.get("selection_sha256") != selection_sha:
        raise RefactorError("candidate overlay selection hash mismatch")

    verify_candidate_support_bindings(work, overlay, manifest)


def verify_official_source_bindings(
    work: Path,
    overlay: dict[str, Any],
    manifest: dict[str, str],
) -> None:
    if (
        overlay.get("dut_source") != "official"
        or overlay.get("provenance_mode") != "official_control"
        or overlay.get("gate_kind") != "official_control"
        or overlay.get("mode") != "diagnostic"
        or overlay.get("gate_eligible") is not False
        or overlay.get("golden_candidate_commit") is not None
        or overlay.get("candidate_locked") is not None
        or overlay.get("base_candidate_locked") is not None
        or overlay.get("baseline_exact") is not None
        or overlay.get("component_replacement") is not None
        or overlay.get("selection_sha256") is not None
    ):
        raise RefactorError("official control overlay provenance shape is invalid")
    mycpu = work / "IP" / "myCPU"
    commit = manifest["chiplab_mycpu_gitlink"]
    tree_names = git_text(["ls-tree", "--name-only", commit], cwd=mycpu).splitlines()
    expected_names = sorted(
        name
        for name in tree_names
        if "/" not in name and PurePosixPath(name).suffix.lower() in {".v", ".h"}
    )
    entries = overlay.get("files")
    if not isinstance(entries, list) or len(entries) != len(expected_names):
        raise RefactorError("official control file count differs from the locked gitlink")
    by_name: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RefactorError("official control has a malformed file entry")
        name = entry.get("path")
        if not isinstance(name, str) or name in by_name:
            raise RefactorError("official control has a missing or duplicate file path")
        by_name[name] = entry
    for name in expected_names:
        entry = by_name.get(name)
        source = f"{commit}:{name}"
        payload = git_blob(source, cwd=mycpu)
        expected_sha = sha256_bytes(payload)
        if (
            entry is None
            or entry.get("source") != source
            or entry.get("overlay_path") != f"IP/myCPU/{name}"
            or entry.get("sha256") != expected_sha
            or entry.get("size") != len(payload)
        ):
            raise RefactorError(f"official control source binding mismatch: {source}")
    if set(by_name) != set(expected_names):
        raise RefactorError("official control paths differ from the locked gitlink")
    support = overlay.get("support_files")
    if not isinstance(support, list) or len(support) != 1 or not isinstance(support[0], dict):
        raise RefactorError("official control support-file list is malformed")
    license_entry = support[0]
    license_payload = git_blob(f"{commit}:LICENSE", cwd=mycpu)
    if (
        license_entry.get("path") != "IP/myCPU/LICENSE"
        or license_entry.get("source") != f"{commit}:LICENSE"
        or license_entry.get("sha256") != sha256_bytes(license_payload)
        or license_entry.get("size") != len(license_payload)
    ):
        raise RefactorError("official control license binding mismatch")


def verify_component_replacement_bindings(
    work: Path,
    overlay: dict[str, Any],
    manifest: dict[str, str],
) -> None:
    if (
        overlay.get("dut_source") != "mixed"
        or overlay.get("provenance_mode") != "mixed_candidate"
        or overlay.get("gate_kind") != "component_replacement"
        or overlay.get("mode") != "diagnostic"
        or overlay.get("gate_eligible") is not False
        or overlay.get("candidate_locked") is not False
        or overlay.get("base_candidate_locked") is not True
        or overlay.get("baseline_exact") is not False
    ):
        raise RefactorError("mixed overlay has a gate-eligible or locked baseline shape")
    metadata = overlay.get("component_replacement")
    if not isinstance(metadata, dict):
        raise RefactorError("mixed overlay lacks component replacement provenance")
    spec_path = metadata.get("spec_path")
    source_head = metadata.get("source_head")
    if not isinstance(spec_path, str) or not isinstance(source_head, str):
        raise RefactorError("mixed overlay replacement provenance is malformed")
    plan = load_component_replacement_plan(spec_path, source_head)
    if metadata != plan.metadata():
        raise RefactorError("component replacement spec or source binding changed after overlay")
    if overlay.get("golden_candidate_commit") != manifest["team_golden_candidate"]:
        raise RefactorError("mixed overlay base candidate differs from manifest.lock")

    locked_paths = read_golden_files()
    entries = overlay.get("files")
    if not isinstance(entries, list) or len(entries) != len(locked_paths):
        raise RefactorError("mixed overlay file count differs from the locked exact union")
    by_logical: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RefactorError("mixed overlay has a malformed file entry")
        logical_path = entry.get("logical_path")
        if not isinstance(logical_path, str) or logical_path in by_logical:
            raise RefactorError("mixed overlay has a missing or duplicate logical path")
        by_logical[logical_path] = entry
    replacements = {item.target: item for item in plan.replacements}
    selection: list[dict[str, Any]] = []
    for logical_path in locked_paths:
        entry = by_logical.get(logical_path)
        if entry is None:
            raise RefactorError(f"mixed overlay is missing locked target: {logical_path}")
        target_name = PurePosixPath(logical_path).name
        expected_overlay = f"IP/myCPU/{target_name}"
        if entry.get("path") != target_name or entry.get("overlay_path") != expected_overlay:
            raise RefactorError(f"mixed overlay target mismatch for {logical_path}")
        base_payload = git_blob(f"{manifest['team_golden_candidate']}:{logical_path}")
        base_sha = sha256_bytes(base_payload)
        base_tree_entry = git_regular_blob_entry(manifest["team_golden_candidate"], logical_path)
        if (
            entry.get("base_source") != f"{manifest['team_golden_candidate']}:{logical_path}"
            or entry.get("base_sha256") != base_sha
            or entry.get("base_size") != len(base_payload)
            or entry.get("base_oid") != base_tree_entry["oid"]
            or entry.get("base_mode") != base_tree_entry["mode"]
        ):
            raise RefactorError(f"mixed overlay base blob mismatch for {logical_path}")
        replacement = replacements.get(logical_path)
        if replacement is None:
            expected_source = f"{manifest['team_golden_candidate']}:{logical_path}"
            expected_payload = base_payload
            if entry.get("source_kind") != "golden":
                raise RefactorError(f"mixed overlay selection mismatch for {logical_path}")
        else:
            expected_source = f"{plan.source_head}:{replacement.source}"
            expected_payload = replacement.payload
            if (
                entry.get("source_kind") != "replacement"
                or entry.get("replacement_source") != expected_source
                or entry.get("replacement_source_path") != replacement.source
                or entry.get("replacement_oid") != replacement.source_oid
                or entry.get("replacement_mode") != replacement.source_mode
                or entry.get("replacement_spec_source")
                != f"{plan.spec_commit}:{plan.spec_path}"
                or entry.get("replacement_spec_sha256") != plan.spec_sha256
            ):
                raise RefactorError(f"mixed overlay replacement blob mismatch for {logical_path}")
        expected_sha = sha256_bytes(expected_payload)
        if (
            entry.get("source") != expected_source
            or entry.get("sha256") != expected_sha
            or entry.get("size") != len(expected_payload)
        ):
            raise RefactorError(f"mixed overlay installed source mismatch for {logical_path}")
        selection.append(
            {
                "logical_path": logical_path,
                "source": expected_source,
                "sha256": expected_sha,
                "size": len(expected_payload),
            }
        )
    if set(by_logical) != set(locked_paths):
        raise RefactorError("mixed overlay logical paths differ from the locked exact union")
    selection_sha = sha256_bytes(
        json.dumps(selection, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    if overlay.get("selection_sha256") != selection_sha:
        raise RefactorError("mixed overlay selection hash mismatch")
    verify_candidate_support_bindings(work, overlay, manifest)


def verify_dut_source_bindings(
    work: Path,
    overlay: dict[str, Any],
    manifest: dict[str, str],
) -> None:
    verify_overlay_files(work, overlay)
    dut_source = overlay.get("dut_source")
    if dut_source == "mixed":
        verify_component_replacement_bindings(work, overlay, manifest)
    elif dut_source == "candidate":
        verify_candidate_source_bindings(work, overlay, manifest)
    elif dut_source == "official":
        verify_official_source_bindings(work, overlay, manifest)
    else:
        raise RefactorError(f"unknown DUT source in overlay: {dut_source!r}")


def verify_overlay_integrity(
    *,
    out_dir: Path,
    iteration_id: str,
    tool_root: Path,
    work_root: Path,
    diagnostic: bool,
    doctor_max_age_seconds: int,
    post_smoke: bool = False,
) -> tuple[Path, dict[str, Any], dict[str, Any], str, str]:
    manifest = parse_lock(MANIFEST_PATH)
    overlay_report_path = iteration_report_path(out_dir, iteration_id, "chiplab-overlay")
    if not overlay_report_path.is_file():
        raise RefactorError(f"missing iteration overlay report: {overlay_report_path}")
    overlay_report, overlay_report_sha256 = read_json_file_with_sha256(
        overlay_report_path
    )
    if not isinstance(overlay_report, dict):
        raise RefactorError("overlay report must be a JSON object")
    overlay_run_id = str(overlay_report.get("run_id", ""))
    require_report_publication(
        overlay_report_path,
        overlay_report,
        overlay_report_sha256,
        command="chiplab-overlay",
        iteration_id=iteration_id,
        publication_id=overlay_run_id,
        publisher_sha256=str(overlay_report.get("evaluator_sha256", "")),
    )
    if overlay_report.get("iteration_id") != iteration_id:
        raise RefactorError("overlay report iteration id mismatch")
    expected_mode = "diagnostic" if diagnostic else "baseline"
    if overlay_report.get("mode") != expected_mode:
        raise RefactorError(
            f"overlay mode mismatch: expected {expected_mode}, got {overlay_report.get('mode')}"
        )
    if diagnostic:
        if overlay_report.get("status") != "diagnostic" or overlay_report.get("gate_eligible"):
            raise RefactorError("diagnostic overlay has a gate-eligible PASS shape")
    elif overlay_report.get("status") != "pass" or not overlay_report.get("gate_eligible"):
        raise RefactorError("baseline smoke requires a gate-eligible locked overlay PASS")

    work = Path(str(overlay_report.get("work_dir", ""))).resolve()
    expected_work = (work_root.resolve() / iteration_id).resolve()
    if work != expected_work:
        raise RefactorError(
            f"overlay work directory differs from --work-root: expected={expected_work} actual={work}"
        )
    work_marker = work / GENERATED_MARKER
    marker = work / ".refactor-overlay.json"
    if not work_marker.is_file() or not marker.is_file():
        raise RefactorError(f"validation workspace markers are missing: {work}")
    generated_marker = validate_json_file(work_marker)
    if (
        generated_marker.get("purpose") != "chiplab-validation-copy"
        or generated_marker.get("resolved_path") != str(work)
    ):
        raise RefactorError("validation workspace generated marker is invalid")
    smoke_lock = work / ".rtl-smoke.lock"
    if smoke_lock.exists() or smoke_lock.is_symlink():
        raise RefactorError(
            f"RTL smoke lock remains from an interrupted or concurrent run: {smoke_lock}; "
            "rebuild the isolated overlay before retrying"
        )
    overlay, marker_sha = read_json_file_with_sha256(marker)
    if marker_sha != overlay_report.get("work_marker_sha256"):
        raise RefactorError("work overlay marker was modified after overlay")
    overlay_manifest_path = Path(str(overlay_report.get("overlay_manifest", ""))).resolve()
    if not overlay_manifest_path.is_file():
        raise RefactorError("overlay manifest path is missing")
    immutable_overlay, overlay_manifest_sha256 = read_json_file_with_sha256(
        overlay_manifest_path
    )
    if overlay_manifest_sha256 != overlay_report.get("overlay_manifest_sha256"):
        raise RefactorError("overlay manifest hash differs from overlay report")
    if immutable_overlay != overlay:
        raise RefactorError("work marker and immutable overlay manifest differ")
    if overlay.get("iteration_id") != iteration_id or overlay.get("mode") != expected_mode:
        raise RefactorError("overlay manifest is not bound to this smoke run")
    projected_fields = {
        "iteration_id": overlay.get("iteration_id"),
        "work_dir": str(work),
        "file_count": len(overlay.get("files", [])) if isinstance(overlay.get("files"), list) else None,
        "dut_source": overlay.get("dut_source"),
        "provenance_mode": overlay.get("provenance_mode"),
        "gate_kind": overlay.get("gate_kind"),
        "mode": overlay.get("mode"),
        "gate_eligible": overlay.get("gate_eligible"),
        "candidate_locked": overlay.get("candidate_locked"),
        "base_candidate_locked": overlay.get("base_candidate_locked"),
        "baseline_exact": overlay.get("baseline_exact"),
        "golden_candidate_commit": overlay.get("golden_candidate_commit"),
        "selection_sha256": overlay.get("selection_sha256"),
        "component_replacement": overlay.get("component_replacement"),
        "replacement_count": (
            len(overlay.get("component_replacement", {}).get("replacements", []))
            if isinstance(overlay.get("component_replacement"), dict)
            else 0
        ),
    }
    projection_mismatches = {
        key: {"report": overlay_report.get(key), "manifest": value}
        for key, value in projected_fields.items()
        if overlay_report.get(key) != value
    }
    if projection_mismatches:
        raise RefactorError(f"overlay report projection mismatch: {projection_mismatches}")
    if overlay.get("evaluator_sha256") != sha256_file(Path(__file__)):
        raise RefactorError("overlay was produced by a different evaluator revision")
    if overlay.get("manifest_sha256") != sha256_file(MANIFEST_PATH):
        raise RefactorError("overlay manifest.lock hash is stale")
    if overlay.get("golden_files_lock_sha256") != sha256_file(GOLDEN_FILES_PATH):
        raise RefactorError("overlay golden file allowlist hash is stale")
    if overlay.get("chiplab_commit") != manifest["chiplab_commit"]:
        raise RefactorError("overlay marker no longer matches manifest.lock")
    if overlay.get("mycpu_reference_commit") != manifest["chiplab_mycpu_gitlink"]:
        raise RefactorError("overlay myCPU gitlink no longer matches manifest.lock")
    if overlay.get("work_filesystem") != filesystem_type(work):
        raise RefactorError("overlay work filesystem changed after creation")
    if overlay.get("chiplab_tree") != git_text(["rev-parse", "HEAD^{tree}"], cwd=work):
        raise RefactorError("validation chiplab tree differs from overlay")
    if git_text(["rev-parse", "HEAD"], cwd=work) != manifest["chiplab_commit"]:
        raise RefactorError("validation chiplab HEAD changed after overlay")
    if git_text(["rev-parse", "HEAD"], cwd=work / "IP" / "myCPU") != manifest["chiplab_mycpu_gitlink"]:
        raise RefactorError("validation myCPU reference HEAD changed after overlay")

    chiplab_ref = Path(str(overlay.get("chiplab_reference", ""))).resolve()
    doctor_path, current_doctor, current_doctor_sha256 = require_passing_chiplab_doctor(
        out_dir,
        chiplab_ref,
        tool_root,
        doctor_max_age_seconds,
    )
    if current_doctor_sha256 != overlay.get("doctor_report_sha256"):
        raise RefactorError("chiplab doctor report changed after overlay")
    current_fingerprints = require_tool_fingerprints(tool_root, manifest)
    if current_fingerprints != overlay.get("tool_fingerprints"):
        raise RefactorError("runtime tool fingerprints changed after overlay")

    expected_links = {
        "gcc": tool_root / "loongson-gnu-toolchain-8.3-x86_64-loongarch32r-linux-gnusf-v2.0",
        "nemu": tool_root / "nemu",
        "picolibc": tool_root / "picolibc",
    }
    for name, expected_target in expected_links.items():
        link = work / "toolchains" / expected_target.name
        if not link.is_symlink() or link.resolve() != expected_target.resolve():
            raise RefactorError(f"tool link {name} changed after overlay: {link}")
        if overlay.get("tool_links", {}).get(name) != str(expected_target):
            raise RefactorError(f"tool link manifest mismatch for {name}")

    if post_smoke:
        require_post_smoke_official_integrity(
            work,
            overlay.get("post_smoke_official_workspace_fingerprint", {}),
            LOCKED_SMOKE_CASE,
        )
    else:
        require_official_worktree_integrity(
            work, overlay.get("official_workspace_fingerprint", {})
        )
    if overlay.get("dut_source") in {"candidate", "mixed"}:
        export_manifest = (
            out_dir / "reference" / "golden-rtl" / iteration_id / "manifest.json"
        )
        if (
            not export_manifest.is_file()
            or sha256_file(export_manifest) != overlay.get("golden_export_manifest_sha256")
        ):
            raise RefactorError("golden export manifest is missing or stale")
    dut_source = overlay.get("dut_source")
    if dut_source == "mixed":
        metadata = overlay.get("component_replacement")
        source_head = metadata.get("source_head") if isinstance(metadata, dict) else None
        if current_doctor.get("repo_head_sha") != source_head:
            raise RefactorError("chiplab doctor no longer matches mixed replacement source HEAD")
        verify_dut_source_bindings(work, overlay, manifest)
    elif dut_source == "candidate":
        verify_dut_source_bindings(work, overlay, manifest)
        if not diagnostic and (
            not overlay.get("candidate_locked")
            or not overlay.get("baseline_exact")
            or overlay.get("golden_candidate_commit") != manifest["team_golden_candidate"]
        ):
            raise RefactorError("baseline smoke requires candidate_locked=true candidate RTL")
    elif dut_source == "official":
        if not diagnostic:
            raise RefactorError("official control cannot satisfy a baseline gate")
        verify_dut_source_bindings(work, overlay, manifest)
    else:
        raise RefactorError(f"unknown DUT source in overlay: {dut_source!r}")
    return (
        work,
        overlay,
        overlay_report,
        current_doctor_sha256,
        overlay_report_sha256,
    )


def command_rtl_smoke(args: argparse.Namespace) -> int:
    out_dir = checked_out_dir(args.out_dir)
    iteration_id = checked_iteration_id(args.iteration_id)
    work_root = Path(args.work_root).resolve()
    require_nonoverlapping_validation_roots(out_dir, work_root)
    run_id = f"smoke-{time.time_ns()}-{os.getpid()}"
    smoke_report_path = iteration_report_path(out_dir, iteration_id, "rtl-smoke")
    locks: list[ValidationLock] = []
    report: dict[str, Any] | None = None
    report_sha256: str | None = None
    result_code = 2
    try:
        locks.append(acquire_iteration_lock(out_dir, iteration_id, "rtl-smoke", run_id))
        locks.append(
            acquire_iteration_lock(work_root, iteration_id, "rtl-smoke", run_id)
        )
        remove_stale_report_publication(smoke_report_path)
        result_code = _command_rtl_smoke_locked(args)
        stored, report_sha256 = read_json_file_with_sha256(smoke_report_path)
        if not isinstance(stored, dict):
            raise RefactorError("RTL smoke report must be a JSON object")
        report = stored
        publication_id = str(report.get("run_id", ""))
        require_report_publication(
            smoke_report_path,
            report,
            report_sha256,
            command="rtl-smoke",
            iteration_id=iteration_id,
            publication_id=publication_id,
            publisher_sha256=sha256_file(Path(__file__)),
        )
    finally:
        body_error = sys.exc_info()[1]
        try:
            release_validation_locks(locks)
        except BaseException as release_error:
            if body_error is not None:
                raise RefactorError(
                    "RTL smoke failed and validation lock release also failed: "
                    f"body={body_error}; release={release_error}"
                ) from body_error
            raise
    if report is None or report_sha256 is None:
        raise RefactorError("RTL smoke completed without a published report")
    print_report(report)
    return result_code


def _command_rtl_smoke_locked(args: argparse.Namespace) -> int:
    require_posix_validation_environment()
    out_dir = checked_out_dir(args.out_dir)
    iteration_id = checked_iteration_id(args.iteration_id)
    smoke_report_path = iteration_report_path(out_dir, iteration_id, "rtl-smoke")
    remove_stale_report_publication(smoke_report_path)
    require_locked_smoke_case(args.case)
    tool_root = Path(args.tool_root).resolve()
    work, overlay, overlay_report, doctor_sha, overlay_report_sha = verify_overlay_integrity(
        out_dir=out_dir,
        iteration_id=iteration_id,
        tool_root=tool_root,
        work_root=Path(args.work_root),
        diagnostic=args.diagnostic,
        doctor_max_age_seconds=args.doctor_max_age_seconds,
    )
    overlay_report_path = iteration_report_path(out_dir, iteration_id, "chiplab-overlay")
    manifest = parse_lock(MANIFEST_PATH)
    env = smoke_environment(work, tool_root)
    run_dir = work / "sims" / "verilator" / "run_prog"
    run_id = f"{time.time_ns()}-{os.getpid()}"
    lock_path = acquire_smoke_lock(work, iteration_id, run_id)
    release_attempted = False
    publication_sha256: str | None = None
    result_code = 1
    try:
        raw_dir = out_dir / "raw" / "iterations" / iteration_id / "rtl-smoke" / run_id
        raw_dir.mkdir(parents=True, exist_ok=False)
        removed_paths = clean_smoke_generated_paths(work, run_dir, args.case)

        commands: list[CommandResult] = []
        compile_log = run_dir / "log" / "compile.log"
        config_file = run_dir / "config-software.mak"
        case_log_dir = run_dir / "log" / f"{args.case}_log"

        configure = run_command(
            ["./configure.sh", "--run", args.case],
            cwd=run_dir,
            timeout=args.configure_timeout,
            env=env,
            log_path=raw_dir / "01-configure.log",
        )
        commands.append(configure)
        config_values = parse_make_assignments(config_file)
        configure_output = configure.stdout + "\n" + configure.stderr
        actual_case = config_values.get("RUN_SOFTWARE")
        configure_ok = (
            configure.exit_code == 0
            and not configure.timed_out
            and "unavailable" not in configure_output.lower()
            and actual_case == args.case
        )

        build: CommandResult | None = None
        build_started_ns: int | None = None
        if configure_ok:
            build_started_ns = time.time_ns()
            build = run_command(
                ["make", "verilator", "testbench", "soft_compile"],
                cwd=run_dir,
                timeout=args.build_timeout,
                env=env,
                log_path=raw_dir / "02-build.log",
            )
            commands.append(build)

        build_artifacts: list[dict[str, Any]] = []
        build_artifacts_fresh = False
        if build is not None and build_started_ns is not None:
            build_artifacts, build_artifacts_fresh = fresh_build_artifacts(
                run_dir, args.case, build_started_ns
            )
        compile_entry = next(
            (entry for entry in build_artifacts if entry["path"] == str(compile_log)), None
        )
        compile_fresh = bool(compile_entry and compile_entry["fresh"])
        compile_text = (
            compile_log.read_text(encoding="utf-8", errors="replace") if compile_fresh else ""
        )
        build_text = (
            compile_text + "\n" + build.stdout + "\n" + build.stderr if build is not None else ""
        )
        warnings = parse_verilator_warnings(compile_text)
        build_errors = parse_build_errors(build_text)
        build_integrity_ok = verilator_build_integrity_passed(
            build,
            compile_fresh=compile_fresh,
            errors=build_errors,
            artifacts_fresh=build_artifacts_fresh,
        )
        warning_clean = not warnings
        verilator_compile_ok = build_integrity_ok and warning_clean

        simulation: CommandResult | None = None
        simulation_started_ns: int | None = None
        if build_integrity_ok:
            simulation_started_ns = time.time_ns()
            simulation = run_command(
                ["make", "simulation_run_prog"],
                cwd=run_dir,
                timeout=args.sim_timeout,
                env=env,
                log_path=raw_dir / "03-simulation.log",
            )
            commands.append(simulation)
        simulation_text = (simulation.stdout + "\n" + simulation.stderr) if simulation else ""
        parsed = parse_simulation_log(
            simulation_text,
            expected_termination=(
                "end_by_syscall" if args.case == LOCKED_SMOKE_CASE else None
            ),
        )
        output_paths = {
            "simu_trace": case_log_dir / "simu_trace.txt",
            "uart": case_log_dir / "uart_output.txt",
            "uart_real": case_log_dir / "uart_output.txt.real",
        }
        output_evidence: dict[str, dict[str, Any]] = {}
        for name, path in output_paths.items():
            exists = path.is_file()
            fresh = bool(
                exists
                and simulation_started_ns is not None
                and path.stat().st_mtime_ns >= simulation_started_ns
            )
            output_evidence[name] = {
                "path": str(path),
                "exists": exists,
                "fresh": fresh,
                "size": path.stat().st_size if exists else None,
                "sha256": sha256_file(path) if exists else None,
            }
        output_evidence["uart"]["oracle_role"] = "not_applicable_for_func_lab19"
        output_evidence["uart_real"]["oracle_role"] = "not_applicable_for_func_lab19"
        output_evidence["simu_trace"]["oracle_role"] = "trace_artifact"
        output_contract_ok = bool(
            output_evidence["simu_trace"]["fresh"]
            and output_evidence["simu_trace"]["size"]
            and output_evidence["uart"]["fresh"]
            and output_evidence["uart_real"]["fresh"]
        )
        commands_ok = (
            configure_ok
            and build is not None
            and simulation is not None
            and all(item.exit_code == 0 and not item.timed_out for item in commands)
        )
        functional_ok = commands_ok and output_contract_ok and parsed["status"] == "pass"
        gate_result = "pass" if functional_ok and verilator_compile_ok else "fail"
        result_status = "diagnostic" if args.diagnostic else gate_result

        artifacts_by_path: dict[str, dict[str, Any]] = {
            entry["path"]: {
                "path": entry["path"],
                "size": entry["size"],
                "sha256": entry["sha256"],
            }
            for entry in build_artifacts
            if entry["exists"]
        }
        for path in output_paths.values():
            if path.is_file():
                artifacts_by_path[str(path)] = {
                    "path": str(path),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }

        environment_sha256 = sha256_bytes(
            json.dumps(env, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        current_marker = work / ".refactor-overlay.json"
        if not current_marker.is_file():
            raise RefactorError("DUT overlay marker disappeared during RTL smoke")
        post_marker, current_marker_sha = read_json_file_with_sha256(current_marker)
        if (
            current_marker_sha != overlay_report.get("work_marker_sha256")
            or post_marker != overlay
        ):
            raise RefactorError("DUT overlay marker changed during RTL smoke")
        post_overlay_report, post_overlay_report_sha = read_json_file_with_sha256(
            overlay_report_path
        )
        if (
            post_overlay_report_sha != overlay_report_sha
            or post_overlay_report != overlay_report
        ):
            raise RefactorError("DUT overlay report changed during RTL smoke")
        overlay_manifest_path = Path(
            str(overlay_report.get("overlay_manifest", ""))
        ).resolve()
        post_overlay_manifest, post_overlay_manifest_sha = read_json_file_with_sha256(
            overlay_manifest_path
        )
        if (
            post_overlay_manifest != overlay
            or post_overlay_manifest_sha
            != overlay_report.get("overlay_manifest_sha256")
        ):
            raise RefactorError("immutable DUT overlay manifest changed during RTL smoke")
        verify_dut_source_bindings(work, overlay, manifest)
        require_post_smoke_official_integrity(
            work,
            overlay.get("post_smoke_official_workspace_fingerprint", {}),
            args.case,
        )
        post_run_dut_verification = {
            "status": "pass",
            "work_marker_sha256": current_marker_sha,
            "overlay_report_sha256": overlay_report_sha,
            "overlay_manifest_sha256": post_overlay_manifest_sha,
            "selection_sha256": overlay.get("selection_sha256"),
            "official_workspace_fingerprint": overlay.get(
                "post_smoke_official_workspace_fingerprint"
            ),
            "generated_path_exclusions": sorted(
                smoke_generated_relative_paths(args.case)
            ),
        }
        report = {
            "schema_version": 1,
            "command": "rtl-smoke",
            "generated_at": now_iso(),
            "status": result_status,
            "gate_result": gate_result,
            "gate_eligible": not args.diagnostic and bool(overlay.get("gate_eligible")),
            "mode": "diagnostic" if args.diagnostic else "baseline",
            "functional_status": (
                "pass" if functional_ok else "fail" if simulation is not None else "not_run"
            ),
            "verilator_compile_status": (
                "pass"
                if verilator_compile_ok
                else "warning"
                if build_integrity_ok
                else "fail"
                if build is not None
                else "not_run"
            ),
            "build_integrity_status": (
                "pass" if build_integrity_ok else "fail" if build is not None else "not_run"
            ),
            "simulation_eligible": build_integrity_ok,
            "rtl_static_gate": "not_executed_by_rtl_smoke",
            "iteration_id": iteration_id,
            "run_id": run_id,
            "chiplab_commit": manifest["chiplab_commit"],
            "dut_source": overlay.get("dut_source"),
            "provenance_mode": overlay.get("provenance_mode"),
            "gate_kind": overlay.get("gate_kind"),
            "golden_candidate_commit": overlay.get("golden_candidate_commit"),
            "candidate_locked": overlay.get("candidate_locked"),
            "base_candidate_locked": overlay.get("base_candidate_locked"),
            "baseline_exact": overlay.get("baseline_exact"),
            "component_replacement": overlay.get("component_replacement"),
            "selection_sha256": overlay.get("selection_sha256"),
            "observed_result": gate_result if args.diagnostic else None,
            "requested_case": args.case,
            "actual_case": actual_case,
            "configure_valid": configure_ok,
            "removed_generated_paths": removed_paths,
            "compile_log_fresh": compile_fresh,
            "build_artifacts_fresh": build_artifacts_fresh,
            "build_artifacts": build_artifacts,
            "build_errors": build_errors,
            "output_contract_ok": output_contract_ok,
            "output_evidence": output_evidence,
            "post_run_dut_verification": post_run_dut_verification,
            "environment": env,
            "environment_sha256": environment_sha256,
            "result_file_policy": {
                "status": "not_provided_by_locked_func_lab19",
                "functional_oracle": "NEMU DPI DiffTest markers and simulator termination output",
            },
            "overlay_report_sha256": overlay_report_sha,
            "doctor_report_sha256": doctor_sha,
            "evaluator_sha256": sha256_file(Path(__file__)),
            "commands": [item.as_dict() for item in commands],
            "counts": gate_counts(executed=True, passed=gate_result == "pass"),
            "functional_counts": gate_counts(executed=simulation is not None, passed=functional_ok),
            "verilator_compile_counts": gate_counts(
                executed=build is not None, passed=verilator_compile_ok
            ),
            "parser": parsed,
            "verilator_warnings": warnings,
            "compile_warning_policy": {
                "status": "pass" if verilator_compile_ok else "fail",
                "rule": "No warning is accepted without a file/line-specific reviewed waiver.",
                "counts_by_scope": {
                    "dut": sum(item["scope"] == "dut" for item in warnings),
                    "official_environment": sum(
                        item["scope"] == "official_environment" for item in warnings
                    ),
                },
            },
            "lock_policy": {
                "path": str(lock_path),
                "release": "normal report completion only",
                "interrupted_run_requires_new_overlay": True,
            },
            "artifacts": list(artifacts_by_path.values()),
            "raw_dir": str(raw_dir),
        }
        write_json(smoke_report_path, report)
        publication_sha256 = json_sha256(report)
        if sha256_file(smoke_report_path) != publication_sha256:
            raise RefactorError("RTL smoke report changed during publication")
        result_code = 0 if gate_result == "pass" else 1
        release_attempted = True
        release_validation_lock(lock_path)
        write_publication_marker(
            smoke_report_path,
            report,
            command="rtl-smoke",
            iteration_id=iteration_id,
            publication_id=run_id,
            publisher_sha256=sha256_file(Path(__file__)),
        )
    except BaseException as command_error:
        failures: list[Exception] = []
        try:
            remove_stale_report_publication(smoke_report_path)
        except Exception as error:
            failures.append(error)
        if not release_attempted:
            try:
                abandon_validation_lock(lock_path)
            except Exception as error:
                failures.append(error)
        if failures:
            details = "; ".join(str(error) for error in failures)
            raise RefactorError(
                f"RTL smoke failure cleanup failed: {details}"
            ) from command_error
        raise
    return result_code


def validate_json_file(path: Path) -> Any:
    value, _ = read_json_file_with_sha256(path)
    return value


ITERATION_STATUSES = frozenset({"draft", "blocked", "ready", "complete"})
GATE_STATUSES = frozenset({"pass", "fail", "pending", "skipped", "unavailable", "warning"})
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
REVIEW_RAW_PATH = "reviews/claude-raw.md"


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RefactorError(f"{context} must be an object")
    return value


def _require_nonempty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RefactorError(f"{context} must be a non-empty string")
    return value


def _require_git_sha(value: Any, context: str) -> str:
    value = _require_nonempty_string(value, context)
    if GIT_SHA_PATTERN.fullmatch(value) is None:
        raise RefactorError(f"{context} must be a full lowercase 40-character Git SHA")
    return value


def _require_nonnegative_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RefactorError(f"{context} must be a nonnegative integer")
    return value


def _validate_gate(gate_name: str, value: Any) -> dict[str, Any]:
    gate = _require_object(value, f"gate {gate_name}")
    status = gate.get("status")
    if status not in GATE_STATUSES:
        raise RefactorError(f"gate {gate_name}.status must be one of {sorted(GATE_STATUSES)}")
    counts = {
        field: _require_nonnegative_int(gate.get(field), f"gate {gate_name}.{field}")
        for field in ("planned", "executed", "passed", "failed", "skipped")
    }
    if counts["executed"] != counts["passed"] + counts["failed"]:
        raise RefactorError(
            f"gate {gate_name}: executed must equal passed + failed "
            f"({counts['executed']} != {counts['passed']} + {counts['failed']})"
        )
    if counts["planned"] != counts["executed"] + counts["skipped"]:
        raise RefactorError(
            f"gate {gate_name}: planned must equal executed + skipped "
            f"({counts['planned']} != {counts['executed']} + {counts['skipped']})"
        )
    if counts["planned"] == 0:
        raise RefactorError(f"gate {gate_name}.planned must be greater than zero")
    if status == "pass" and not (
        counts["planned"] > 0
        and counts["passed"] == counts["planned"]
        and counts["failed"] == 0
        and counts["skipped"] == 0
    ):
        raise RefactorError(f"gate {gate_name}: status=pass contradicts its counts")
    if status == "fail" and counts["failed"] == 0:
        raise RefactorError(f"gate {gate_name}: status=fail requires at least one failure")
    if status in {"pending", "skipped"} and counts["executed"] != 0:
        raise RefactorError(f"gate {gate_name}: status={status} cannot contain executed tests")
    if status == "unavailable" and counts["failed"] + counts["skipped"] == 0:
        raise RefactorError(f"gate {gate_name}: unavailable must record a failure or skip")
    return gate


def _validate_required_gates(summary: dict[str, Any], gates: dict[str, dict[str, Any]], status: str) -> None:
    required = summary.get("required_gates")
    if required is None:
        if status in {"ready", "complete"}:
            raise RefactorError(f"a {status} iteration requires a non-empty required_gates list")
        return
    if not isinstance(required, list) or any(
        not isinstance(item, str) or not item.strip() for item in required
    ):
        raise RefactorError("summary.required_gates must be a list of non-empty gate names")
    if len(required) != len(set(required)):
        raise RefactorError("summary.required_gates must not contain duplicates")
    unknown = sorted(set(required) - gates.keys())
    if unknown:
        raise RefactorError(f"summary.required_gates names missing gates: {unknown}")
    if status not in {"ready", "complete"}:
        return
    if not required:
        raise RefactorError(f"a {status} iteration requires at least one required gate")
    for gate_name in required:
        gate = gates[gate_name]
        planned = gate["planned"]
        if not (
            planned > 0
            and gate["executed"] == planned
            and gate["passed"] == planned
            and gate["failed"] == 0
            and gate["skipped"] == 0
        ):
            raise RefactorError(f"required gate {gate_name} is not fully executed and passing")
        if "status" in gate and gate["status"] != "pass":
            raise RefactorError(f"required gate {gate_name} must report status=pass")


def _validate_summary(iteration_dir: Path, value: Any) -> tuple[dict[str, Any], str, str]:
    summary = _require_object(value, "summary.json")
    iteration_id = _require_nonempty_string(summary.get("iteration_id"), "summary.iteration_id")
    if iteration_id != iteration_dir.name:
        raise RefactorError(
            f"summary.iteration_id does not match directory name: {iteration_id!r} != {iteration_dir.name!r}"
        )
    status = summary.get("status")
    if status not in ITERATION_STATUSES:
        raise RefactorError(f"summary.status must be one of {sorted(ITERATION_STATUSES)}")
    _require_git_sha(summary.get("base_sha"), "summary.base_sha")
    head_sha = _require_git_sha(summary.get("head_sha"), "summary.head_sha")
    current_head = git_text(["rev-parse", "HEAD"])
    if head_sha != current_head:
        _review_target_is_acceptable(head_sha, current_head, context="summary.head_sha")
    gates_value = summary.get("gates")
    if not isinstance(gates_value, dict) or not gates_value:
        raise RefactorError("summary.gates must be a non-empty object")
    gates: dict[str, dict[str, Any]] = {}
    for gate_name, gate_value in gates_value.items():
        if not isinstance(gate_name, str) or not gate_name.strip():
            raise RefactorError("summary.gates keys must be non-empty strings")
        gates[gate_name] = _validate_gate(gate_name, gate_value)
    _validate_required_gates(summary, gates, status)
    if status in {"ready", "complete"}:
        _require_git_sha(summary.get("review_target_sha"), "summary.review_target_sha")
    elif summary.get("review_target_sha") is not None:
        _require_git_sha(summary.get("review_target_sha"), "summary.review_target_sha")
    return summary, status, current_head


def _has_evidence(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and all(_has_evidence(item) for item in value)
    if isinstance(value, dict):
        return bool(value)
    return False


def _parse_iso_timestamp(value: Any, context: str) -> datetime:
    text = _require_nonempty_string(value, context)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise RefactorError(f"{context} must be an ISO-8601 timestamp") from error
    if parsed.utcoffset() is None:
        raise RefactorError(f"{context} must include a timezone")
    return parsed


def _validate_commands(path: Path) -> int:
    records = 0
    try:
        stream = path.open(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RefactorError(f"cannot read {path}: {error}") from error
    with stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise RefactorError(f"commands.jsonl:{line_number}: {error}") from error
            record = _require_object(record, f"commands.jsonl:{line_number}")
            argv = record.get("argv")
            if not isinstance(argv, list) or not argv or any(
                not isinstance(item, str) or not item for item in argv
            ):
                raise RefactorError(f"commands.jsonl:{line_number}.argv must be a non-empty string list")
            _require_nonempty_string(record.get("cwd"), f"commands.jsonl:{line_number}.cwd")
            if isinstance(record.get("exit_code"), bool) or not isinstance(record.get("exit_code"), int):
                raise RefactorError(f"commands.jsonl:{line_number}.exit_code must be an integer")
            has_started = "started_at" in record
            has_finished = "finished_at" in record
            has_elapsed = "elapsed_seconds" in record
            if has_started != has_finished:
                raise RefactorError(
                    f"commands.jsonl:{line_number} must provide both started_at and finished_at"
                )
            if not ((has_started and has_finished) or has_elapsed):
                raise RefactorError(
                    f"commands.jsonl:{line_number} requires started_at/finished_at or elapsed_seconds"
                )
            if has_started:
                started = _parse_iso_timestamp(record["started_at"], f"commands.jsonl:{line_number}.started_at")
                finished = _parse_iso_timestamp(record["finished_at"], f"commands.jsonl:{line_number}.finished_at")
                if finished < started:
                    raise RefactorError(f"commands.jsonl:{line_number}.finished_at precedes started_at")
            if has_elapsed:
                elapsed = record["elapsed_seconds"]
                if (
                    isinstance(elapsed, bool)
                    or not isinstance(elapsed, (int, float))
                    or not 0 <= elapsed < float("inf")
                ):
                    raise RefactorError(
                        f"commands.jsonl:{line_number}.elapsed_seconds must be a finite nonnegative number"
                    )
            if not _has_evidence(record.get("evidence")):
                raise RefactorError(f"commands.jsonl:{line_number}.evidence must be non-empty")
            records += 1
    if records == 0:
        raise RefactorError("commands.jsonl must contain at least one command record")
    return records


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_artifact_path(raw_path: str, iteration_dir: Path) -> Path:
    declared = Path(raw_path)
    candidates = [declared] if declared.is_absolute() else [iteration_dir / declared, REPO_ROOT / declared]
    allowed_roots = {iteration_dir.resolve(), REPO_ROOT.resolve()}
    existing: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved in existing:
            continue
        if not any(_path_is_within(resolved, root) for root in allowed_roots):
            continue
        if resolved.is_file():
            existing.append(resolved)
    if not existing:
        raise RefactorError(
            f"artifact path does not name an existing file inside the workspace or iteration: {raw_path}"
        )
    if len(existing) != 1:
        raise RefactorError(f"artifact path is ambiguous between workspace and iteration: {raw_path}")
    return existing[0]


def _validate_artifacts(iteration_dir: Path, iteration_id: str, value: Any) -> int:
    document = _require_object(value, "artifacts.json")
    if document.get("iteration_id") is not None and document.get("iteration_id") != iteration_id:
        raise RefactorError("artifacts.json iteration_id does not match summary.iteration_id")
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise RefactorError("artifacts.json.artifacts must be a list")
    seen_paths: set[Path] = set()
    seen_ids: set[str] = set()
    for index, item in enumerate(artifacts):
        context = f"artifacts.json.artifacts[{index}]"
        artifact = _require_object(item, context)
        raw_path = _require_nonempty_string(artifact.get("path"), f"{context}.path")
        expected_sha = artifact.get("sha256")
        if not isinstance(expected_sha, str) or SHA256_PATTERN.fullmatch(expected_sha) is None:
            raise RefactorError(f"{context}.sha256 must be a lowercase SHA-256 digest")
        expected_size = _require_nonnegative_int(artifact.get("size"), f"{context}.size")
        resolved = _resolve_artifact_path(raw_path, iteration_dir)
        if resolved in seen_paths:
            raise RefactorError(f"{context}.path duplicates another artifact: {raw_path}")
        seen_paths.add(resolved)
        artifact_id = artifact.get("id")
        if artifact_id is not None:
            artifact_id = _require_nonempty_string(artifact_id, f"{context}.id")
            if artifact_id in seen_ids:
                raise RefactorError(f"duplicate artifact id: {artifact_id}")
            seen_ids.add(artifact_id)
        actual_size = resolved.stat().st_size
        if actual_size != expected_size:
            raise RefactorError(
                f"{context}.size mismatch for {raw_path}: expected {expected_size}, got {actual_size}"
            )
        actual_sha = sha256_file(resolved)
        if actual_sha != expected_sha:
            raise RefactorError(
                f"{context}.sha256 mismatch for {raw_path}: expected {expected_sha}, got {actual_sha}"
            )
    return len(artifacts)


def _raw_review_events(raw_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    candidates = [raw_text.strip(), *(line.strip() for line in raw_text.splitlines())]
    for candidate in candidates:
        if not candidate.startswith("{") or not candidate.endswith("}"):
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value not in events:
            events.append(value)
    return events


def _review_event_field(event: dict[str, Any], snake: str, camel: str | None = None) -> Any:
    if snake in event:
        return event[snake]
    return event.get(camel) if camel is not None else None


def _review_target_is_acceptable(
    target_sha: str,
    current_head: str,
    *,
    context: str = "review_target_sha",
) -> None:
    if target_sha == current_head:
        return
    parent_line = git_text(["rev-list", "--parents", "-n", "1", current_head])
    if target_sha not in parent_line.split()[1:]:
        raise RefactorError(f"{context} must be current HEAD or one of its direct parents")
    changed = git_text(["diff", "--name-only", "--no-renames", f"{target_sha}..{current_head}", "--"])
    paths = [line.strip().replace("\\", "/") for line in changed.splitlines() if line.strip()]
    disallowed = [
        path
        for path in paths
        if not (path.startswith("logs/refactor/") or path == "docs/refactor/status.yml")
    ]
    if disallowed:
        raise RefactorError(
            f"{context} is stale because post-target commits changed non-evidence files: "
            f"{disallowed}"
        )


def _validate_review(iteration_dir: Path, summary: dict[str, Any], status: str, current_head: str) -> str:
    raw_path = iteration_dir / REVIEW_RAW_PATH
    summary_path = iteration_dir / "reviews" / "claude-summary.json"
    missing = [str(path.relative_to(iteration_dir)) for path in (raw_path, summary_path) if not path.is_file()]
    if missing:
        raise RefactorError(f"iteration requires Claude review attempt evidence: {missing}")
    try:
        raw_text = raw_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RefactorError(f"cannot read Claude raw review: {error}") from error
    if not raw_text.strip():
        raise RefactorError("reviews/claude-raw.md must be non-empty")
    review = _require_object(validate_json_file(summary_path), "reviews/claude-summary.json")
    if review.get("iteration_id") != summary["iteration_id"]:
        raise RefactorError("Claude review iteration_id does not match summary.iteration_id")
    review_status = review.get("status")
    if review_status not in {"pass", "failed", "unavailable"}:
        raise RefactorError("Claude review status must be pass, failed, or unavailable")
    job_id = _require_nonempty_string(review.get("job_id"), "Claude review job_id")
    expected_raw_sha = review.get("raw_sha256")
    if not isinstance(expected_raw_sha, str) or SHA256_PATTERN.fullmatch(expected_raw_sha) is None:
        raise RefactorError("Claude review raw_sha256 must be a lowercase SHA-256 digest")
    actual_raw_sha = sha256_file(raw_path)
    if expected_raw_sha != actual_raw_sha:
        raise RefactorError("Claude review raw_sha256 does not match reviews/claude-raw.md")

    reviewer = review.get("reviewer") if isinstance(review.get("reviewer"), dict) else {}
    provider = review.get("provider", reviewer.get("provider"))
    model = review.get("model", reviewer.get("model"))
    reviewed_head_sha = review.get("reviewed_head_sha")
    provenance = _require_object(review.get("provenance"), "Claude review provenance")
    expected_provenance = {
        "source": "claude-review-mcp",
        "raw_path": REVIEW_RAW_PATH,
        "raw_sha256": expected_raw_sha,
        "job_id": job_id,
        "provider": provider,
        "model": model,
        "reviewed_head_sha": reviewed_head_sha,
    }
    mismatched_provenance = [
        key for key, expected in expected_provenance.items() if provenance.get(key) != expected
    ]
    if mismatched_provenance:
        raise RefactorError(f"Claude review provenance mismatch: {mismatched_provenance}")

    matching_events = [
        event
        for event in _raw_review_events(raw_text)
        if _review_event_field(event, "job_id", "jobId") == job_id
    ]
    if not matching_events:
        raise RefactorError("Claude raw review contains no structured event for summary.job_id")

    if review_status == "pass":
        provider = _require_nonempty_string(provider, "Claude review provider")
        model = _require_nonempty_string(model, "Claude review model")
        if "claude" not in model.lower():
            raise RefactorError("a passing Claude review must identify a Claude model")
        reviewed_head_sha = _require_git_sha(reviewed_head_sha, "Claude review reviewed_head_sha")
        target_sha = summary.get("review_target_sha", summary["head_sha"])
        if reviewed_head_sha != target_sha:
            raise RefactorError("Claude reviewed_head_sha does not match summary.review_target_sha")
        _review_target_is_acceptable(target_sha, current_head)
        terminal_events = [
            event
            for event in matching_events
            if str(event.get("status", "")).lower() in {"pass", "passed", "completed", "succeeded"}
            and event.get("done") is True
            and _review_event_field(event, "provider") == provider
            and _review_event_field(event, "model") == model
            and _has_evidence(event.get("response"))
        ]
        if not terminal_events:
            raise RefactorError("Claude raw review lacks a matching successful terminal event and response")
        if _require_nonnegative_int(review.get("open_blocking_count"), "Claude open_blocking_count") != 0:
            raise RefactorError("a passing Claude review cannot have open blocking findings")
        for field in ("fresh_against_head", "allow_ready", "allow_status_promotion"):
            if review.get(field) is not True:
                raise RefactorError(f"a passing Claude review requires {field}=true")
    else:
        if status in {"ready", "complete"}:
            raise RefactorError(f"a {status} iteration requires Claude review status=pass")
        error_text = _require_nonempty_string(review.get("error"), "failed Claude review error")
        terminal_events = [
            event
            for event in matching_events
            if str(event.get("status", "")).lower() in {"failed", "error", "unavailable"}
            and event.get("done") is True
            and event.get("error") == error_text
        ]
        if not terminal_events:
            raise RefactorError("Claude unavailable/failed summary is not supported by its raw terminal event")
        if _require_nonnegative_int(review.get("open_blocking_count"), "Claude open_blocking_count") < 1:
            raise RefactorError("an unavailable/failed Claude review must record an open blocking finding")
        if review.get("fresh_against_head") is not False:
            raise RefactorError("an unavailable/failed Claude review must not claim freshness")
        for field in ("allow_ready", "allow_status_promotion"):
            if review.get(field) is not False:
                raise RefactorError(f"an unavailable/failed Claude review requires {field}=false")
        if reviewed_head_sha is not None:
            reviewed_head_sha = _require_git_sha(reviewed_head_sha, "Claude review reviewed_head_sha")
            target_sha = summary.get("review_target_sha", summary["head_sha"])
            if reviewed_head_sha != target_sha:
                raise RefactorError("failed Claude review target does not match the iteration review target")
            _review_target_is_acceptable(target_sha, current_head)
    return review_status


def command_validate_iteration(args: argparse.Namespace) -> int:
    iteration_dir = Path(args.iteration_dir).resolve()
    required = ["iteration.md", "summary.json", "commands.jsonl", "artifacts.json", "pr.md"]
    missing = [name for name in required if not (iteration_dir / name).is_file()]
    if missing:
        raise RefactorError(f"iteration is missing required files: {missing}")
    summary, status, current_head = _validate_summary(
        iteration_dir, validate_json_file(iteration_dir / "summary.json")
    )
    artifact_count = _validate_artifacts(
        iteration_dir,
        summary["iteration_id"],
        validate_json_file(iteration_dir / "artifacts.json"),
    )
    jsonl_count = _validate_commands(iteration_dir / "commands.jsonl")
    iteration_text = (iteration_dir / "iteration.md").read_text(encoding="utf-8")
    if not re.search(r"[\u4e00-\u9fff]", iteration_text):
        raise RefactorError("iteration.md must contain the required Chinese iteration log")
    if not (iteration_dir / "pr.md").read_text(encoding="utf-8").strip():
        raise RefactorError("pr.md must be non-empty")
    review_status = _validate_review(iteration_dir, summary, status, current_head)
    if status in {"ready", "complete"}:
        raise RefactorError(
            f"local evidence validation cannot authorize status={status}; keep the iteration "
            "draft/blocked until a trusted CI or maintainer attestation is implemented"
        )
    report = {
        "schema_version": 1,
        "command": "validate-iteration",
        "generated_at": now_iso(),
        "status": "pass",
        "iteration_dir": str(iteration_dir),
        "iteration_status": status,
        "command_records": jsonl_count,
        "artifact_count": artifact_count,
        "gate_count": len(summary["gates"]),
        "review_status": review_status,
    }
    print_report(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--out-dir", default="build")
    doctor.add_argument("--vivado-home")
    doctor.set_defaults(handler=command_doctor)

    chiplab_doctor = subparsers.add_parser("chiplab-doctor")
    chiplab_doctor.add_argument("--out-dir", default="build")
    chiplab_doctor.add_argument("--chiplab-ref", required=True)
    chiplab_doctor.add_argument("--tool-root", default="/opt/chiplab-tools/root")
    chiplab_doctor.set_defaults(handler=command_chiplab_doctor)

    golden_export = subparsers.add_parser("golden-export")
    golden_export.add_argument("--out-dir", default="build")
    golden_export.add_argument("--candidate-commit")
    golden_export.add_argument("--diagnostic", action="store_true")
    golden_export.set_defaults(handler=command_golden_export)

    overlay = subparsers.add_parser("chiplab-overlay")
    overlay.add_argument("--out-dir", default="build")
    overlay.add_argument("--work-root", default="/tmp/nscscc-refactor-work")
    overlay.add_argument("--iteration-id", required=True)
    overlay.add_argument("--chiplab-ref", required=True)
    overlay.add_argument("--tool-root", default="/opt/chiplab-tools/root")
    overlay.add_argument(
        "--dut-source", choices=("candidate", "mixed", "official"), default="candidate"
    )
    overlay.add_argument("--diagnostic", action="store_true")
    overlay.add_argument("--doctor-max-age-seconds", type=int, default=3600)
    overlay.add_argument(
        "--candidate-commit",
        help="Diagnostic override. Reports candidate_locked=false and cannot establish the locked baseline.",
    )
    overlay.add_argument(
        "--replacement-spec",
        help="Committed repo-relative JSON selection; only valid for a diagnostic mixed DUT.",
    )
    overlay.add_argument(
        "--source-head",
        help="Full clean source HEAD containing the replacement spec and replacement Verilog.",
    )
    overlay.set_defaults(handler=command_chiplab_overlay)

    smoke = subparsers.add_parser("rtl-smoke")
    smoke.add_argument("--out-dir", default="build")
    smoke.add_argument("--iteration-id", required=True)
    smoke.add_argument("--tool-root", default="/opt/chiplab-tools/root")
    smoke.add_argument("--work-root", default="/tmp/nscscc-refactor-work")
    smoke.add_argument("--case", default="func/func_lab19")
    smoke.add_argument("--diagnostic", action="store_true")
    smoke.add_argument("--doctor-max-age-seconds", type=int, default=3600)
    smoke.add_argument("--configure-timeout", type=int, default=60)
    smoke.add_argument("--build-timeout", type=int, default=900)
    smoke.add_argument("--sim-timeout", type=int, default=600)
    smoke.set_defaults(handler=command_rtl_smoke)

    validate = subparsers.add_parser("validate-iteration")
    validate.add_argument("--iteration-dir", required=True)
    validate.set_defaults(handler=command_validate_iteration)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if not sys.flags.isolated:
        print("ERROR: refactor.py requires isolated Python; invoke python -I", file=sys.stderr)
        return 2
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except RefactorError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
