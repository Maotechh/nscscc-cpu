#!/usr/bin/env python3
"""Prove that generated core_top does not instantiate legacy CPU Verilog modules."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1
OLD_FILES = (
    "addr_trans.v", "alu.v", "axi_bridge.v", "btb.v", "csr.v", "dcache.v",
    "div.v", "exe_stage.v", "icache.v", "id_stage.v", "if_stage.v",
    "lacc_core.v", "lacc_demo.v", "mem_stage.v", "mul.v", "perf_counter.v",
    "regfile.v", "tlb_entry.v", "tools.v", "wb_stage.v",
)
OLD_MODULES = frozenset(Path(name).stem for name in OLD_FILES)
ALLOWED_EXTERNAL = frozenset({"ChiplabDiffTestBlackBox"})
IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_$]*"


def _mask_comments(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', text)


def _definitions(text: str) -> set[str]:
    return set(re.findall(rf"(?m)^\s*module\s+({IDENTIFIER})\b", text))


def _instances(text: str) -> set[str]:
    masked = _mask_comments(text)
    names: set[str] = set()
    pattern = re.compile(rf"(?m)^\s*({IDENTIFIER})\s+(?:#\s*\([^;]*?\)\s*)?{IDENTIFIER}\s*\(")
    for match in pattern.finditer(masked):
        name = match.group(1)
        if name not in {"module", "assign", "if", "else", "always", "function", "task", "end"}:
            names.add(name)
    return names


def _file_modules(path: Path) -> set[str]:
    try:
        return _definitions(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError(f"{path} is not UTF-8: {error}") from error


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    rtl = args.rtl.resolve()
    if not rtl.is_file():
        raise ValueError(f"missing generated RTL: {rtl}")
    text = rtl.read_text(encoding="utf-8")
    definitions = _definitions(text)
    instances = _instances(text)
    legacy_definitions = sorted(definitions & OLD_MODULES)
    legacy_instances = sorted(instances & OLD_MODULES)
    unresolved = sorted(
        name for name in instances - definitions - ALLOWED_EXTERNAL
        if not name.startswith("Difftest")
    )
    root_count = sum(1 for name in definitions if name == args.root_module)

    overlay = None
    pure_overlay_status = "not_checked"
    if args.overlay_dir is not None:
        overlay_root = args.overlay_dir.resolve()
        if not overlay_root.is_dir():
            raise ValueError(f"missing overlay directory: {overlay_root}")
        entries = []
        blocking_files = []
        for filename in OLD_FILES:
            path = overlay_root / filename
            if not path.exists():
                entries.append({"path": filename, "present": False, "module_definitions": []})
                continue
            modules = sorted(_file_modules(path))
            entries.append({"path": filename, "present": True, "module_definitions": modules})
            if modules:
                blocking_files.append(filename)
        pure_overlay_status = "pass" if not blocking_files else "fail"
        overlay = {"root": str(overlay_root), "entries": entries, "blocking_files": blocking_files, "status": pure_overlay_status}

    report = {
        "schema_version": SCHEMA_VERSION,
        "gate": "candidate-closure",
        "rtl": str(rtl),
        "rtl_sha256": hashlib.sha256(rtl.read_bytes()).hexdigest(),
        "root_module": args.root_module,
        "root_module_count": root_count,
        "module_definitions": sorted(definitions),
        "instance_types": sorted(instances),
        "legacy_module_names": sorted(OLD_MODULES),
        "legacy_definitions": legacy_definitions,
        "legacy_instances": legacy_instances,
        "unresolved_instance_types": unresolved,
        "allowed_external_instance_types": sorted(ALLOWED_EXTERNAL),
        "pure_overlay": overlay,
        "pure_overlay_status": pure_overlay_status,
        "status": "pass" if root_count == 1 and not legacy_definitions and not legacy_instances and not unresolved else "fail",
    }
    _write_report(args.out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" and pure_overlay_status != "fail" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rtl", type=Path, required=True)
    parser.add_argument("--root-module", default="core_top")
    parser.add_argument("--overlay-dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
