#!/usr/bin/env python3
"""Compare generated exe_stage ports against the committed off/on manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", type=Path, required=True)
    parser.add_argument("--profile", choices=("lacc_off", "lacc_on"), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    rtl = args.rtl.resolve()
    out = args.out_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit("output directory must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(
        (root / "reference/component-contracts/exe-stage-ports.json").read_text(encoding="utf-8")
    )
    expected = {
        entry["name"]: (entry["direction"], entry["width"])
        for entry in manifest["common"] + manifest["profiles"][args.profile]["conditional"]
    }
    expected["ds_to_es_bus"] = (
        "input", manifest["profiles"][args.profile]["ds_to_es_bus_width"]
    )

    yosys_json = out / "design.json"
    script = (
        f"read_verilog -sv {rtl}; hierarchy -check -top exe_stage; proc; "
        f"write_json {yosys_json}"
    )
    result = subprocess.run(
        ["yosys", "-q", "-p", script],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    (out / "yosys.log").write_text(result.stdout, encoding="utf-8")
    actual: dict[str, tuple[str, int]] = {}
    if result.returncode == 0 and yosys_json.is_file():
        module = json.loads(yosys_json.read_text(encoding="utf-8"))["modules"]["exe_stage"]
        actual = {
            name: (port["direction"], len(port["bits"]))
            for name, port in module["ports"].items()
        }
    passed = result.returncode == 0 and actual == expected
    summary = {
        "schema_version": 1,
        "gate": "exe-stage-port-check",
        "profile": args.profile,
        "status": "pass" if passed else "fail",
        "expected": expected,
        "actual": actual,
        "yosys_exit_code": result.returncode,
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
