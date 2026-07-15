#!/usr/bin/env python3
"""Audit the typed cache/AXI boundary and its generated core_top wiring.

This gate is deliberately structural.  It does not claim AXI protocol or CPU
behavioral equivalence; those are covered by RTL static, sequential
equivalence, and chiplab smoke gates.  The gate does ensure that a mutation of
direction, width, field selection, or combinational-vs-stateful adaptation
cannot pass because an expected string survived in a comment.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


RAW_OUTPUTS: dict[str, tuple[str, int]] = {
    "arid": ("backendArea_core_axi_ar_payload_id", 4),
    "araddr": ("backendArea_core_axi_ar_payload_address", 32),
    "arlen": ("backendArea_core_axi_ar_payload_len", 8),
    "arsize": ("backendArea_core_axi_ar_payload_size", 3),
    "arburst": ("backendArea_core_axi_ar_payload_burst", 2),
    "arlock": ("backendArea_core_axi_ar_payload_lock", 2),
    "arcache": ("backendArea_core_axi_ar_payload_cache", 4),
    "arprot": ("backendArea_core_axi_ar_payload_prot", 3),
    "arvalid": ("backendArea_core_axi_ar_valid", 1),
    "rready": ("backendArea_core_axi_r_ready", 1),
    "awid": ("backendArea_core_axi_aw_payload_id", 4),
    "awaddr": ("backendArea_core_axi_aw_payload_address", 32),
    "awlen": ("backendArea_core_axi_aw_payload_len", 8),
    "awsize": ("backendArea_core_axi_aw_payload_size", 3),
    "awburst": ("backendArea_core_axi_aw_payload_burst", 2),
    "awlock": ("backendArea_core_axi_aw_payload_lock", 2),
    "awcache": ("backendArea_core_axi_aw_payload_cache", 4),
    "awprot": ("backendArea_core_axi_aw_payload_prot", 3),
    "awvalid": ("backendArea_core_axi_aw_valid", 1),
    "wid": ("backendArea_core_axi_w_payload_id", 4),
    "wdata": ("backendArea_core_axi_w_payload_data", 32),
    "wstrb": ("backendArea_core_axi_w_payload_byteMask", 4),
    "wlast": ("backendArea_core_axi_w_payload_last", 1),
    "wvalid": ("backendArea_core_axi_w_valid", 1),
    "bready": ("backendArea_core_axi_b_ready", 1),
}

RAW_INPUTS: dict[str, tuple[str, int]] = {
    "arready": ("axi_ar_ready", 1),
    "rid": ("axi_r_payload_id", 4),
    "rdata": ("axi_r_payload_data", 32),
    "rresp": ("axi_r_payload_response", 2),
    "rlast": ("axi_r_payload_last", 1),
    "rvalid": ("axi_r_valid", 1),
    "awready": ("axi_aw_ready", 1),
    "wready": ("axi_w_ready", 1),
    "bid": ("axi_b_payload_id", 4),
    "bresp": ("axi_b_payload_response", 2),
    "bvalid": ("axi_b_valid", 1),
}

ADAPTER_ASSIGNMENTS: dict[str, str] = {
    "legacy.io.inst_rd_req": "io.inst.read.valid",
    "legacy.io.inst_rd_type": "io.inst.read.payload.requestType",
    "legacy.io.inst_rd_addr": "io.inst.read.payload.address.asBits",
    "io.inst.read.ready": "legacy.io.inst_rd_rdy",
    "io.inst.readResponse.valid": "legacy.io.inst_ret_valid",
    "io.inst.readResponse.payload.last": "legacy.io.inst_ret_last",
    "io.inst.readResponse.payload.data": "legacy.io.inst_ret_data",
    "legacy.io.inst_wr_req": "io.inst.write.valid",
    "legacy.io.inst_wr_type": "io.inst.write.payload.requestType",
    "legacy.io.inst_wr_addr": "io.inst.write.payload.address.asBits",
    "legacy.io.inst_wr_wstrb": "io.inst.write.payload.byteMask",
    "legacy.io.inst_wr_data": "io.inst.write.payload.data",
    "io.inst.write.ready": "legacy.io.inst_wr_rdy",
    "legacy.io.data_rd_req": "io.data.read.valid",
    "legacy.io.data_rd_type": "io.data.read.payload.requestType",
    "legacy.io.data_rd_addr": "io.data.read.payload.address.asBits",
    "io.data.read.ready": "legacy.io.data_rd_rdy",
    "io.data.readResponse.valid": "legacy.io.data_ret_valid",
    "io.data.readResponse.payload.last": "legacy.io.data_ret_last",
    "io.data.readResponse.payload.data": "legacy.io.data_ret_data",
    "legacy.io.data_wr_req": "io.data.write.valid",
    "legacy.io.data_wr_type": "io.data.write.payload.requestType",
    "legacy.io.data_wr_addr": "io.data.write.payload.address.asBits",
    "legacy.io.data_wr_wstrb": "io.data.write.payload.byteMask",
    "legacy.io.data_wr_data": "io.data.write.payload.data",
    "io.data.write.ready": "legacy.io.data_wr_rdy",
    "io.writeBufferEmpty": "legacy.io.write_buffer_empty",
    "legacy.io.arready": "io.axi.ar.ready",
    "legacy.io.rid": "io.axi.r.payload.id",
    "legacy.io.rdata": "io.axi.r.payload.data",
    "legacy.io.rresp": "io.axi.r.payload.response",
    "legacy.io.rlast": "io.axi.r.payload.last",
    "legacy.io.rvalid": "io.axi.r.valid",
    "legacy.io.awready": "io.axi.aw.ready",
    "legacy.io.wready": "io.axi.w.ready",
    "legacy.io.bid": "io.axi.b.payload.id",
    "legacy.io.bresp": "io.axi.b.payload.response",
    "legacy.io.bvalid": "io.axi.b.valid",
    "io.axi.ar.payload.id": "legacy.io.arid",
    "io.axi.ar.payload.address": "legacy.io.araddr",
    "io.axi.ar.payload.len": "legacy.io.arlen",
    "io.axi.ar.payload.size": "legacy.io.arsize",
    "io.axi.ar.payload.burst": "legacy.io.arburst",
    "io.axi.ar.payload.lock": "legacy.io.arlock",
    "io.axi.ar.payload.cache": "legacy.io.arcache",
    "io.axi.ar.payload.prot": "legacy.io.arprot",
    "io.axi.ar.valid": "legacy.io.arvalid",
    "io.axi.r.ready": "legacy.io.rready",
    "io.axi.aw.payload.id": "legacy.io.awid",
    "io.axi.aw.payload.address": "legacy.io.awaddr",
    "io.axi.aw.payload.len": "legacy.io.awlen",
    "io.axi.aw.payload.size": "legacy.io.awsize",
    "io.axi.aw.payload.burst": "legacy.io.awburst",
    "io.axi.aw.payload.lock": "legacy.io.awlock",
    "io.axi.aw.payload.cache": "legacy.io.awcache",
    "io.axi.aw.payload.prot": "legacy.io.awprot",
    "io.axi.aw.valid": "legacy.io.awvalid",
    "io.axi.w.payload.id": "legacy.io.wid",
    "io.axi.w.payload.data": "legacy.io.wdata",
    "io.axi.w.payload.byteMask": "legacy.io.wstrb",
    "io.axi.w.payload.last": "legacy.io.wlast",
    "io.axi.w.valid": "legacy.io.wvalid",
    "io.axi.b.ready": "legacy.io.bready",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_scala_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)//[^\n]*", "", text)


def extract_scala_class(text: str, class_name: str) -> str:
    clean = strip_scala_comments(text)
    match = re.search(rf"\bfinal\s+class\s+{re.escape(class_name)}\b[^{{]*{{", clean)
    if match is None:
        raise ValueError(f"Scala class {class_name} is missing")
    start = match.end() - 1
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(clean)):
        char = clean[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return clean[start + 1 : index]
    raise ValueError(f"Scala class {class_name} has unbalanced braces")


def assignment_present(body: str, left: str, right: str) -> bool:
    pattern = rf"(?m)^\s*{re.escape(left)}\s*:=\s*{re.escape(right)}\s*$"
    return re.search(pattern, body) is not None


def parse_verilog_declarations(text: str) -> dict[str, tuple[int, str]]:
    declarations: dict[str, tuple[int, str]] = {}
    pattern = re.compile(
        r"(?m)^\s*(?P<kind>wire|reg)\s+"
        r"(?:\[(?P<msb>\d+)\s*:\s*(?P<lsb>\d+)\]\s+)?"
        r"(?P<name>[A-Za-z_$][\w$]*)\s*;"
    )
    for match in pattern.finditer(text):
        msb, lsb = match.group("msb"), match.group("lsb")
        width = 1 if msb is None else abs(int(msb) - int(lsb)) + 1
        declarations[match.group("name")] = (width, match.group("kind"))
    return declarations


def parse_module_ports(text: str, module_name: str) -> dict[str, tuple[str, int]]:
    header_match = re.search(
        rf"(?ms)^\s*module\s+{re.escape(module_name)}\s*\(.*?^\s*\);", text
    )
    if header_match is None:
        raise ValueError(f"missing module declaration {module_name}")
    ports: dict[str, tuple[str, int]] = {}
    pattern = re.compile(
        r"(?m)^\s*(?P<direction>input|output)\s+wire\s+"
        r"(?:\[(?P<msb>\d+)\s*:\s*(?P<lsb>\d+)\]\s+)?"
        r"(?P<name>[A-Za-z_$][\w$]*)\s*[,)]"
    )
    for match in pattern.finditer(header_match.group(0)):
        msb, lsb = match.group("msb"), match.group("lsb")
        width = 1 if msb is None else abs(int(msb) - int(lsb)) + 1
        ports[match.group("name")] = (match.group("direction"), width)
    return ports


def extract_verilog_instance(text: str, module_name: str, instance_name: str) -> str:
    match = re.search(
        rf"(?ms)^\s*{re.escape(module_name)}\s+{re.escape(instance_name)}\s*\("
        r".*?^\s*\);",
        text,
    )
    if match is None:
        raise ValueError(f"missing {module_name} instance {instance_name}")
    return match.group(0)


def parse_named_connections(instance: str) -> dict[str, str]:
    return {
        name: re.sub(r"\s+", "", expression)
        for name, expression in re.findall(
            r"\.(?P<name>[A-Za-z_$][\w$]*)\s*\(\s*(?P<expression>[^()]*)\s*\)", instance
        )
    }


def expected_signal(name: str, width: int) -> str:
    return name if width == 1 else f"{name}[{width - 1}:0]"


def verify_scala_sources(
    backend_source: Path, compat_source: Path, bridge_source: Path
) -> tuple[dict[str, Any], list[str]]:
    checks: dict[str, Any] = {}
    failures: list[str] = []
    backend = strip_scala_comments(backend_source.read_text(encoding="utf-8"))
    compat = strip_scala_comments(compat_source.read_text(encoding="utf-8"))
    try:
        adapter = extract_scala_class(bridge_source.read_text(encoding="utf-8"), "OpenLa500TypedAxiBridge")
    except ValueError as error:
        return {"error": str(error)}, [str(error)]

    checks["backend_typed_contract"] = (
        re.search(r"\bval\s+axi\s*=\s*master\(Axi3Compat\(\)\)", backend) is not None
        and not re.search(r"\b(?:inst|data)_rd_req\b|\b(?:inst|data)_wr_req\b", backend)
    )
    if not checks["backend_typed_contract"]:
        failures.append("backend exposes legacy cache/AXI pins or lacks master(Axi3Compat())")

    raw_declarations = {
        name: bool(re.search(rf"\bval\s+{re.escape(name)}\s*=", compat))
        for name in [*RAW_OUTPUTS, *RAW_INPUTS]
    }
    checks["compat_raw_pin_declarations"] = raw_declarations
    if not all(raw_declarations.values()):
        failures.append("CoreTopCompat is missing one or more locked raw pins")

    checks["adapter_typed_io"] = {
        "inst": re.search(r"\bval\s+inst\s*=\s*slave\(LineReadWritePort\(\)\)", adapter)
        is not None,
        "data": re.search(r"\bval\s+data\s*=\s*slave\(LineReadWritePort\(\)\)", adapter)
        is not None,
        "axi": re.search(r"\bval\s+axi\s*=\s*master\(Axi3Compat\(\)\)", adapter)
        is not None,
    }
    if not all(checks["adapter_typed_io"].values()):
        failures.append("typed adapter does not expose the expected directioned contracts")

    mapping_checks = {
        left: assignment_present(adapter, left, right)
        for left, right in ADAPTER_ASSIGNMENTS.items()
    }
    checks["adapter_combinational_mapping"] = mapping_checks
    failures.extend(
        f"typed adapter mapping missing or changed: {left} := {right}"
        for (left, right), passed in zip(ADAPTER_ASSIGNMENTS.items(), mapping_checks.values())
        if not passed
    )
    forbidden_state = sorted(
        token
        for token in ("Reg(", "RegNext(", "ClockingArea", "StateMachine", "when(")
        if token in adapter
    )
    checks["adapter_has_no_state_or_control"] = not forbidden_state
    checks["adapter_forbidden_tokens"] = forbidden_state
    if forbidden_state:
        failures.append(f"typed adapter contains state/control tokens: {forbidden_state}")
    return checks, failures


def verify_generated_rtl(rtl: str) -> tuple[dict[str, Any], list[str]]:
    checks: dict[str, Any] = {}
    failures: list[str] = []
    declarations = parse_verilog_declarations(rtl)
    wire_checks: dict[str, bool] = {}
    for _, (typed, width) in RAW_OUTPUTS.items():
        actual = declarations.get(typed)
        passed = actual is not None and actual[0] == width
        wire_checks[typed] = passed
        if not passed:
            failures.append(f"generated backend signal {typed} has wrong/missing width {width}")
    checks["generated_typed_wire_widths"] = wire_checks

    try:
        instance = extract_verilog_instance(rtl, "SpinalCoreBackend", "backendArea_core")
        connections = parse_named_connections(instance)
    except ValueError as error:
        checks["backend_instance"] = {"error": str(error)}
        failures.append(str(error))
        connections = {}
    connection_checks: dict[str, bool] = {}
    for raw, (backend_port, width) in RAW_INPUTS.items():
        expected = expected_signal(raw, width)
        actual = connections.get(backend_port)
        passed = actual == expected
        connection_checks[backend_port] = passed
        if not passed:
            failures.append(f"backend connection {backend_port} expected {expected}, got {actual!r}")
    for _, (typed_signal, width) in RAW_OUTPUTS.items():
        backend_port = typed_signal.removeprefix("backendArea_core_")
        expected = expected_signal(typed_signal, width)
        actual = connections.get(backend_port)
        passed = actual == expected
        connection_checks[backend_port] = passed
        if not passed:
            failures.append(f"backend connection {backend_port} expected {expected}, got {actual!r}")
    checks["backend_instance_connections"] = connection_checks

    output_checks: dict[str, bool] = {}
    for raw, (typed, _) in RAW_OUTPUTS.items():
        passed = re.search(
            rf"(?m)^\s*assign\s+{re.escape(raw)}\s*=\s*{re.escape(typed)}\s*;\s*$", rtl
        ) is not None
        output_checks[raw] = passed
        if not passed:
            failures.append(f"core_top output {raw} is not a direct assignment from {typed}")
    checks["core_top_direct_outputs"] = output_checks
    try:
        backend_ports = parse_module_ports(rtl, "SpinalCoreBackend")
    except ValueError as error:
        backend_ports = {}
        failures.append(str(error))
    port_checks: dict[str, bool] = {}
    for _, (backend_port, width) in RAW_INPUTS.items():
        passed = backend_ports.get(backend_port) == ("input", width)
        port_checks[backend_port] = passed
        if not passed:
            failures.append(
                f"SpinalCoreBackend port {backend_port} expected input[{width}], "
                f"got {backend_ports.get(backend_port)!r}"
            )
    for _, (typed_signal, width) in RAW_OUTPUTS.items():
        backend_port = typed_signal.removeprefix("backendArea_core_")
        passed = backend_ports.get(backend_port) == ("output", width)
        port_checks[backend_port] = passed
        if not passed:
            failures.append(
                f"SpinalCoreBackend port {backend_port} expected output[{width}], "
                f"got {backend_ports.get(backend_port)!r}"
            )
    checks["backend_module_ports"] = port_checks
    return checks, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rtl", type=Path, required=True)
    parser.add_argument("--backend-source", type=Path, required=True)
    parser.add_argument("--compat-source", type=Path, required=True)
    parser.add_argument(
        "--bridge-source",
        type=Path,
        default=Path("spinal/src/main/scala/openla500/memory/OpenLa500AxiBridge.scala"),
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    failures: list[str] = []
    try:
        source_checks, source_failures = verify_scala_sources(
            args.backend_source, args.compat_source, args.bridge_source
        )
        failures.extend(source_failures)
        rtl_checks, rtl_failures = verify_generated_rtl(args.rtl.read_text(encoding="utf-8"))
        failures.extend(rtl_failures)
    except (OSError, UnicodeError, ValueError) as error:
        source_checks = {}
        rtl_checks = {}
        failures.append(str(error))

    result = {
        "schema_version": 2,
        "gate": "typed-axi-boundary",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "pass" if not failures else "fail",
        "checks": {"source": source_checks, "generated_rtl": rtl_checks},
        "failures": failures,
        "scope": "typed LineReadWritePort/Axi3Compat adapter and generated SpinalCoreBackend/core_top wiring",
        "claim_boundary": "structural mapping only; no AXI protocol or CPU behavioral equivalence claim",
        "sha256": {
            "rtl": sha256(args.rtl),
            "backend_source": sha256(args.backend_source),
            "compat_source": sha256(args.compat_source),
            "bridge_source": sha256(args.bridge_source),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
