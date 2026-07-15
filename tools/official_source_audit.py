#!/usr/bin/env python3
"""Build an official aa3bde1 versus historical a158aa8 source provenance audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
from typing import Any


OFFICIAL_REVISION = "aa3bde1f3e720e71c2c78d6b81930d797b810149"
HISTORICAL_REVISION = "a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6"
RTL_SUFFIXES = {".v", ".h"}
ENHANCEMENTS = {"lacc_core.v", "lacc_demo.v", "store_buffer.v"}
BACKUPS = {"btb.v.bak", "regfile_dual.v"}


def git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def tree(repo: Path, revision: str, prefix: str = "") -> list[str]:
    args = ["ls-tree", "-z", "-r", "--name-only", revision]
    if prefix:
        args.extend(["--", prefix])
    raw = git(repo, *args, binary=True)
    assert isinstance(raw, bytes)
    return [item.decode("utf-8", errors="surrogateescape") for item in raw.split(bytes([0])) if item]


def blob(repo: Path, revision: str, path: str) -> dict[str, Any]:
    spec = f"{revision}:{path}"
    blob_sha1 = str(git(repo, "rev-parse", spec))
    payload = git(repo, "cat-file", "blob", spec, binary=True)
    assert isinstance(payload, bytes)
    return {
        "path": path,
        "blob_sha1": blob_sha1,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }


def validate_revision(revision: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError(f"revision must be a full lowercase SHA: {revision}")
    return revision


def classify_official(path: str) -> str:
    if Path(path).suffix in RTL_SUFFIXES:
        return "official-behavioral-rtl"
    if path in {"LICENSE", "README.md"} or path.startswith("doc/"):
        return "official-documentation"
    if path.startswith("IP/"):
        return "official-memory-ip"
    return "official-support"


def classify_historical(path: str, overlaps: bool) -> str:
    name = Path(path).name
    if overlaps:
        return "official-overlap"
    if name in ENHANCEMENTS:
        return "team-enhancement"
    if name in BACKUPS:
        return "dead-or-backup"
    if path.startswith("soc/") or path.startswith("sw/") or path.startswith("xilinx_ip/"):
        return "test-or-integration-support"
    return "historical-unmatched"


def audit(official_repo: Path, candidate_repo: Path, official_revision: str, historical_revision: str) -> dict[str, Any]:
    validate_revision(official_revision)
    validate_revision(historical_revision)
    official_paths = tree(official_repo, official_revision)
    official_files = [blob(official_repo, official_revision, path) for path in official_paths]
    official_by_name = {Path(item["path"]).name: item for item in official_files}
    for item in official_files:
        item["classification"] = classify_official(item["path"])

    historical_paths = tree(candidate_repo, historical_revision, "rtl")
    historical_files: list[dict[str, Any]] = []
    for path in historical_paths:
        item = blob(candidate_repo, historical_revision, path)
        overlap = Path(path).name in official_by_name
        item["classification"] = classify_historical(path, overlap)
        item["official_path"] = official_by_name.get(Path(path).name, {}).get("path")
        item["official_sha256"] = official_by_name.get(Path(path).name, {}).get("sha256")
        historical_files.append(item)

    official_rtl = [item for item in official_files if item["classification"] == "official-behavioral-rtl"]
    return {
        "schema_version": 1,
        "official": {
            "repository": str(official_repo.resolve()),
            "revision": official_revision,
            "files": official_files,
            "behavioral_rtl_count": len(official_rtl),
        },
        "historical": {
            "repository": str(candidate_repo.resolve()),
            "revision": historical_revision,
            "files": historical_files,
        },
        "classification_policy": {
            "official-behavioral-rtl": "aa3bde1 root-level Verilog/header implementation files",
            "official-overlap": "a158aa8 rtl basename matches an official aa3bde1 source",
            "team-enhancement": "LACC/store-buffer candidate-only implementation",
            "dead-or-backup": "backup or duplicate register-file source not in official baseline",
            "test-or-integration-support": "SoC/software/Xilinx support outside the CPU RTL boundary",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    official = report["official"]
    historical = report["historical"]
    counts: dict[str, int] = {}
    for item in historical["files"]:
        key = str(item["classification"])
        counts[key] = counts.get(key, 0) + 1
    lines = [
        "# Official OpenLA500 source audit",
        "",
        f"Official nested source: `{official['revision']}` at `{official['repository']}`.",
        f"Historical team tree: `{historical['revision']}` in `{historical['repository']}`.",
        "The official tree is the default provenance; a158aa8 is diagnostic only.",
        "",
        "## Classification counts",
        "",
        f"- official aa3 behavioral RTL: {official['behavioral_rtl_count']}",
    ]
    for key in sorted(counts):
        lines.append(f"- historical {key}: {counts[key]}")
    lines.extend(["", "## Official files", "", "| path | class | blob SHA1 | raw SHA256 | bytes |", "| --- | --- | --- | --- | ---: |"])
    for item in official["files"]:
        lines.append(f"| `{item['path']}` | {item['classification']} | `{item['blob_sha1']}` | `{item['sha256']}` | {item['size']} |")
    lines.extend(["", "## Historical comparison", "", "| path | class | official basename | historical SHA256 | official SHA256 |", "| --- | --- | --- | --- | --- |"])
    for item in historical["files"]:
        lines.append(f"| `{item['path']}` | {item['classification']} | `{item['official_path'] or ''}` | `{item['sha256']}` | `{item['official_sha256'] or ''}` |")
    lines.extend([
        "",
        "## Default-profile conclusion",
        "",
        "The default profile must source behavior from SpinalHDL generated `core_top`;",
        "official aa3 functionality is the reference contract. LACC, store buffer,",
        "backup, and unmatched historical files remain optional or diagnostic and are",
        "not part of the official default generation or acceptance claim.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-mycpu", type=Path, required=True)
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--official-revision", default=OFFICIAL_REVISION)
    parser.add_argument("--historical-revision", default=HISTORICAL_REVISION)
    args = parser.parse_args()
    report = audit(args.official_mycpu, args.candidate_repo, args.official_revision, args.historical_revision)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "aa3bde1-vs-a158aa8.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / "aa3bde1-vs-a158aa8.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"official_files": len(report["official"]["files"]), "historical_rtl_files": len(report["historical"]["files"]), "out_dir": str(args.out_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
