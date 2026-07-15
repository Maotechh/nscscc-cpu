#!/usr/bin/env python3
"""Prove the typed AXI boundary is a field-by-field combinational adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from datetime import datetime, timezone


RAW_OUTPUTS = {
    "arid": "backendArea_core_axi_ar_payload_id",
    "araddr": "backendArea_core_axi_ar_payload_address",
    "arlen": "backendArea_core_axi_ar_payload_len",
    "arsize": "backendArea_core_axi_ar_payload_size",
    "arburst": "backendArea_core_axi_ar_payload_burst",
    "arlock": "backendArea_core_axi_ar_payload_lock",
    "arcache": "backendArea_core_axi_ar_payload_cache",
    "arprot": "backendArea_core_axi_ar_payload_prot",
    "arvalid": "backendArea_core_axi_ar_valid",
    "rready": "backendArea_core_axi_r_ready",
    "awid": "backendArea_core_axi_aw_payload_id",
    "awaddr": "backendArea_core_axi_aw_payload_address",
    "awlen": "backendArea_core_axi_aw_payload_len",
    "awsize": "backendArea_core_axi_aw_payload_size",
    "awburst": "backendArea_core_axi_aw_payload_burst",
    "awlock": "backendArea_core_axi_aw_payload_lock",
    "awcache": "backendArea_core_axi_aw_payload_cache",
    "awprot": "backendArea_core_axi_aw_payload_prot",
    "awvalid": "backendArea_core_axi_aw_valid",
    "wid": "backendArea_core_axi_w_payload_id",
    "wdata": "backendArea_core_axi_w_payload_data",
    "wstrb": "backendArea_core_axi_w_payload_byteMask",
    "wlast": "backendArea_core_axi_w_payload_last",
    "wvalid": "backendArea_core_axi_w_valid",
    "bready": "backendArea_core_axi_b_ready",
}

RAW_INPUTS = {
    "arready": "axi_ar_ready",
    "rid": "axi_r_payload_id",
    "rdata": "axi_r_payload_data",
    "rresp": "axi_r_payload_response",
    "rlast": "axi_r_payload_last",
    "rvalid": "axi_r_valid",
    "awready": "axi_aw_ready",
    "wready": "axi_w_ready",
    "bid": "axi_b_payload_id",
    "bresp": "axi_b_payload_response",
    "bvalid": "axi_b_valid",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rtl", type=Path, required=True)
    parser.add_argument("--backend-source", type=Path, required=True)
    parser.add_argument("--compat-source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rtl = args.rtl.read_text(encoding="utf-8")
    backend = args.backend_source.read_text(encoding="utf-8")
    compat = args.compat_source.read_text(encoding="utf-8")
    checks: dict[str, object] = {}
    failures: list[str] = []

    raw_names = set(RAW_OUTPUTS) | set(RAW_INPUTS)
    backend_raw = sorted(name for name in raw_names if re.search(rf"\bval\s+{re.escape(name)}\b", backend))
    checks["backend_typed_contract"] = "master(Axi3Compat())" in backend and not backend_raw
    if not checks["backend_typed_contract"]:
        failures.append(f"backend raw declarations or missing typed contract: {backend_raw}")

    checks["compat_raw_pin_owner"] = all(re.search(rf"\bval\s+{re.escape(name)}\b", compat) for name in raw_names)
    if not checks["compat_raw_pin_owner"]:
        failures.append("CoreTopCompat does not declare every raw AXI pin")

    output_checks: dict[str, str] = {}
    for raw, typed in RAW_OUTPUTS.items():
        pattern = rf"assign\s+{re.escape(raw)}\s*=\s*{re.escape(typed)}\s*;"
        output_checks[raw] = "pass" if re.search(pattern, rtl) else "fail"
        if output_checks[raw] == "fail":
            failures.append(f"missing direct output mapping {raw} <- {typed}")

    input_checks: dict[str, str] = {}
    for raw, typed in RAW_INPUTS.items():
        pattern = rf"\.{re.escape(typed)}\s*\(\s*{re.escape(raw)}(?:\[[^)]*\])?\s*\)"
        input_checks[raw] = "pass" if re.search(pattern, rtl) else "fail"
        if input_checks[raw] == "fail":
            failures.append(f"missing direct input mapping {raw} -> {typed}")

    checks["raw_output_mapping"] = output_checks
    checks["raw_input_mapping"] = input_checks
    checks["mapping_count"] = {
        "outputs": len([v for v in output_checks.values() if v == "pass"]),
        "expected_outputs": len(RAW_OUTPUTS),
        "inputs": len([v for v in input_checks.values() if v == "pass"]),
        "expected_inputs": len(RAW_INPUTS),
    }
    checks["mapping_is_direct"] = all(value == "pass" for value in output_checks.values()) and all(
        value == "pass" for value in input_checks.values()
    )
    # The exact assignment/instance regexes above are the authoritative directness check.
    checks["rtl_sha256"] = sha256(args.rtl)
    checks["source_sha256"] = {
        "backend": sha256(args.backend_source),
        "compat": sha256(args.compat_source),
    }
    status = not failures and checks["mapping_count"]["outputs"] == len(RAW_OUTPUTS) and checks["mapping_count"]["inputs"] == len(RAW_INPUTS)
    result = {
        "schema_version": 1,
        "gate": "typed-axi-boundary",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "pass" if status else "fail",
        "checks": checks,
        "failures": failures,
        "scope": "CoreTopCompat raw AXI3/WID pin to SpinalCoreBackend Axi3Compat flattening",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if status else 1


if __name__ == "__main__":
    sys.exit(main())
