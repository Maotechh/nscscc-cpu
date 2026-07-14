#!/usr/bin/env python3
"""Capture local WSL tool and repository evidence without asserting locked reproducibility."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_tool(name: str, fallback: str | None = None) -> Path | None:
    resolved = shutil.which(name)
    if resolved:
        return Path(resolved).resolve()
    if fallback:
        candidate = Path(fallback).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def command_info(name: str, args: list[str], fallback: str | None = None) -> dict[str, Any]:
    path = resolve_tool(name, fallback)
    result: dict[str, Any] = {
        "name": name,
        "path": str(path) if path else None,
        "sha256": sha256_file(path) if path else None,
        "version": None,
        "returncode": None,
    }
    if not path:
        result["status"] = "missing"
        return result
    try:
        completed = subprocess.run(
            [str(path), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        result["version"] = completed.stdout.strip().splitlines()[:4]
        result["returncode"] = completed.returncode
        result["status"] = "present" if completed.returncode == 0 else "failed"
    except (OSError, subprocess.TimeoutExpired) as error:
        result["status"] = "failed"
        result["error"] = str(error)
    return result


def artifact_info(name: str, path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "name": name,
        "path": str(resolved),
        "sha256": sha256_file(resolved),
        "status": "present" if resolved.is_file() else "missing",
    }

def git_command(repo: Path, args: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        return {"args": args, "returncode": completed.returncode, "output": completed.stdout.strip().splitlines()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"args": args, "returncode": None, "output": [str(error)]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--official-mycpu", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    workspace = repo.parent
    official = (args.official_mycpu or workspace / "chiplab" / "IP" / "myCPU").resolve()
    chiplab = Path(os.environ.get("CHIPLAB_HOME", workspace / "chiplab")).resolve()
    toolchains = chiplab / "toolchains"
    gcc_fallback = toolchains / "loongson-gnu-toolchain-8.3-x86_64-loongarch32r-linux-gnusf-v2.0" / "bin" / "loongarch32r-linux-gnusf-gcc"
    qemu_fallback = toolchains / "la32r-QEMU-x86_64-ubuntu-22.04" / "qemu-system-loongarch32"
    nemu_fallback = toolchains / "nemu" / "la32r-nemu-interpreter-so"
    tools = {
        "java": command_info("java", ["-version"]),
        "verilator": command_info("verilator", ["--version"]),
        "python3": command_info("python3", ["--version"]),
        "make": command_info("make", ["--version"]),
        "git": command_info("git", ["--version"]),
        "sbt": command_info("sbt", ["--version"], "/home/toss-a-coin/.local/share/coursier/bin/sbt"),
        "loongarch-gcc": command_info("loongarch32r-linux-gnusf-gcc", ["--version"], str(gcc_fallback)),
        "qemu": command_info("qemu-system-loongarch32", ["--version"], str(qemu_fallback)),
        "nemu": artifact_info("la32r-nemu-interpreter-so", nemu_fallback),
        "yosys": command_info("yosys", ["--version"]),
    }
    echo_branch = git_command(repo, ["symbolic-ref", "--short", "HEAD"])
    echo_sha = git_command(repo, ["rev-parse", "refs/heads/refactor/ECHO"])
    official_sha = git_command(official, ["rev-parse", "--verify", "HEAD"])
    chiplab_status = git_command(workspace / "chiplab", ["status", "--short", "--branch"])
    echo_branch_name = echo_branch["output"][0] if echo_branch["output"] else None
    echo_head = echo_sha["output"][0] if echo_sha["output"] else None
    official_head = official_sha["output"][0] if official_sha["output"] else None
    required_tools = ("java", "verilator", "python3", "make", "git", "sbt", "loongarch-gcc", "qemu")
    required_present = all(tools[name]["status"] == "present" for name in required_tools)
    branch_ok = echo_branch_name == "refactor/ECHO"
    official_ok = official_head == "aa3bde1f3e720e71c2c78d6b81930d797b810149"
    summary: dict[str, Any] = {
        "schema_version": 1,
        "profile": "local",
        "status": "pass" if required_present and branch_ok and official_ok else "fail",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "repo": str(repo),
        "workspace": str(workspace),
        "echo_branch": echo_branch_name,
        "echo_sha": echo_head,
        "official_mycpu": str(official),
        "official_mycpu_sha": official_head,
        "official_expected_sha": "aa3bde1f3e720e71c2c78d6b81930d797b810149",
        "branch_ok": branch_ok,
        "official_ok": official_ok,
        "tools": tools,
        "git": {"echo_branch": echo_branch, "echo_sha": echo_sha, "official": official_sha, "chiplab": chiplab_status},
        "temporary_directories": {name: os.environ.get(name) for name in ("TMPDIR", "TMP", "TEMP")},
        "locked_manifest_is_not_asserted": True,
        "notes": [
            "This is local evidence, not a locked toolchain gate.",
            "Yosys is optional for local diagnosis and is reported separately when missing.",
            "Use fully qualified refs because refs/heads/HEAD exists in the ECHO repository.",
        ],
    }
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
