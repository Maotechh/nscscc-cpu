#!/usr/bin/env python3
"""Turn a chiplab simulation transcript into fail-closed JSON evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Any
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


from tools import refactor


def collect_warnings(text: str) -> list[dict[str, str]]:
    warnings = refactor.parse_verilator_warnings(text)
    seen = {item["line"] for item in warnings}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not re.search(r"\bwarning:", line, re.IGNORECASE) or line in seen:
            continue
        normalized = line.replace("\\", "/")
        warnings.append(
            {
                "category": "COMPILER",
                "scope": (
                    "dut"
                    if "/.work/echo/" in normalized
                    or "/chiplab-source/" in normalized
                    or "mycpu_top.v" in normalized
                    else "official_environment"
                ),
                "line": line,
            }
        )
        seen.add(line)
    return warnings


def summarize(text: str, log_path: Path) -> dict[str, Any]:
    simulation = refactor.parse_simulation_log(text)
    build_errors = refactor.parse_build_errors(text)
    warnings = collect_warnings(text)
    passed = simulation["status"] == "pass" and not build_errors and not warnings
    return {
        "schema_version": 1,
        "gate": "chiplab-simulation-transcript",
        "status": "pass" if passed else "fail",
        "generated_at": refactor.now_iso(),
        "log": str(log_path.resolve()),
        "log_sha256": refactor.sha256_file(log_path),
        "simulation": simulation,
        "build_errors": build_errors,
        "warnings": warnings,
        "warning_count": len(warnings),
        "evaluator_sha256": refactor.sha256_file(Path(__file__).resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = summarize(text, args.log)
    refactor.write_json(args.out, result)
    print(args.out)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
