#!/usr/bin/env python3
"""Iteration-local directed lockstep gate for the d22 CACOP recovery contract."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ORACLE_COMMIT = "d22c13c1ecbee7b0423b7e4f4616f24d98457f02"
HISTORICAL_CONTROLS = {
    "d76-ghost-hit": "d76ca40be528eb8de6e258d1ba249a44eaaed6b6",
    "2ff-lookup-bypass": "2ffb1abe4e23eb2272c1b0f899a4ef0727994e05",
    "408-immediate-data-ok": "40830b8307be27128cb215dc4ea66908bd128334",
}
LOCKED_BLOBS = {
    ORACLE_COMMIT: {
        "rtl/icache.v": "5f641ae52220a8ef696b1ec8bc3a38e2a853a578",
        "rtl/dcache.v": "d9c20456b28969fe32bfaf79cc79c2fba0db2e8a",
        "rtl/tools.v": "28022d1fc25026db3282f2cfae319e8b0158d55f",
    },
    HISTORICAL_CONTROLS["d76-ghost-hit"]: {
        "rtl/icache.v": "3f2a622a394b6d4b1a8c6eae16b8a6b35dbef378",
        "rtl/dcache.v": "799e08cf55d6eb6982b20a6a288125503dc7835a",
        "rtl/tools.v": "28022d1fc25026db3282f2cfae319e8b0158d55f",
    },
    HISTORICAL_CONTROLS["2ff-lookup-bypass"]: {
        "rtl/icache.v": "b3ee28da9ce779ff663be3fa6a334ef949244b7d",
        "rtl/dcache.v": "4cb747b3c586a7084bf1c23eb838771c3824280a",
        "rtl/tools.v": "28022d1fc25026db3282f2cfae319e8b0158d55f",
    },
    HISTORICAL_CONTROLS["408-immediate-data-ok"]: {
        "rtl/icache.v": "39ec5931316a068b7e5e64169bd257f480db5640",
        "rtl/dcache.v": "755b5087d0321ab5a41596465c2352dd3ee98a4e",
        "rtl/tools.v": "28022d1fc25026db3282f2cfae319e8b0158d55f",
    },
}


class GateError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(argv: list[str], cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateError(f"cannot execute {' '.join(argv)}: {exc}") from exc


def fresh(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.exists() and (not resolved.is_dir() or any(resolved.iterdir())):
        raise GateError(f"output directory must be fresh: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def locked_source(repo: Path, commit: str, path: str) -> bytes:
    expected = LOCKED_BLOBS.get(commit, {}).get(path)
    if expected is None:
        raise GateError(f"unlocked historical source requested: {commit}:{path}")
    result = run(["git", "cat-file", "blob", f"{commit}:{path}"], repo, 30)
    if result.returncode:
        raise GateError(result.stdout.decode(errors="replace"))
    actual = git_blob_sha1(result.stdout)
    if actual != expected:
        raise GateError(f"historical blob identity mismatch: {commit}:{path} {actual} != {expected}")
    return result.stdout


I_FIELDS = (
    "reset", "valid", "op", "index", "tag", "offset", "wstrb", "wdata",
    "uncache_en", "cacop_en", "cacop_mode", "cacop_index", "cacop_tag",
    "cacop_offset", "cancel", "rd_rdy", "ret_valid", "ret_last", "ret_data", "wr_rdy",
)
D_FIELDS = (
    "reset", "valid", "op", "size", "index", "tag", "offset", "wstrb", "wdata",
    "uncache_en", "cacop_en", "cacop_mode", "preld_hint", "preld_en", "tlb_cancel",
    "sc_cancel", "rd_rdy", "ret_valid", "ret_last", "ret_data", "wr_rdy",
)


def default_vector(target: str) -> dict[str, int]:
    fields = I_FIELDS if target == "icache" else D_FIELDS
    value = {name: 0 for name in fields}
    value["rd_rdy"] = 1
    value["wr_rdy"] = 1
    return value


def generate_vectors(target: str) -> tuple[list[dict[str, int]], list[str], list[dict[str, object]]]:
    vectors: list[dict[str, int]] = []
    labels: list[str] = []
    scenarios: list[dict[str, object]] = []

    def add(label: str, count: int = 1, **signals: int) -> None:
        for _ in range(count):
            vector = default_vector(target)
            vector.update(signals)
            vectors.append(vector)
            labels.append(label)

    def fill(index: int, tag: int, label: str) -> None:
        add(f"{label}:request", valid=1, index=index, tag=tag, offset=0)
        # Legacy lookup compares the current-cycle tag input against the
        # synchronous SRAM output while index/offset come from the request buffer.
        add(f"{label}:lookup", index=index, tag=tag, offset=0)
        add(f"{label}:replace-backpressure", count=3, rd_rdy=0)
        add(f"{label}:replace-accept", rd_rdy=1)
        for beat in range(4):
            add(
                f"{label}:refill-{beat}",
                ret_valid=1,
                ret_last=int(beat == 3),
                ret_data=((index << 20) ^ (tag << 4) ^ beat ^ 0x5A5A0000) & 0xFFFFFFFF,
            )
        add(f"{label}:settle", count=2)

    def dirty_store(index: int, tag: int, label: str) -> None:
        add(
            f"{label}:store-request",
            valid=1,
            op=1,
            size=2,
            index=index,
            tag=tag,
            offset=4,
            wstrb=0xF,
            wdata=(0xD1700000 | index) & 0xFFFFFFFF,
        )
        add(f"{label}:store-lookup", index=index, tag=tag, offset=4)
        add(f"{label}:store-buffer", count=3)

    def cacop(index: int, tag: int, mode: int, way: int, dirty: bool, label: str) -> None:
        signals = {
            "cacop_en": 1,
            "cacop_mode": mode,
            "index": index,
            "tag": tag,
            "offset": way,
        }
        if target == "icache":
            signals.update(cacop_index=index, cacop_tag=tag, cacop_offset=way)
        add(f"{label}:issue", **signals)
        lookup_signals = dict(signals)
        lookup_signals["cacop_en"] = 0
        add(f"{label}:lookup", **lookup_signals)
        if target == "dcache" and dirty:
            add(f"{label}:writeback-backpressure", count=3, wr_rdy=0)
            add(f"{label}:writeback-accept", wr_rdy=1)
            add(f"{label}:replace", rd_rdy=1)
        else:
            add(f"{label}:replace-backpressure", count=3, rd_rdy=0)
            add(f"{label}:replace-accept", rd_rdy=1)
        add(f"{label}:single-cycle-invalidate")
        add(f"{label}:settle", count=2)

    add("reset", count=5, reset=1)
    add("post-reset", count=2)
    definitions = [
        (0, 0, "selected-way"),
        (0, 1, "selected-way"),
        (1, 0, "selected-way"),
        (1, 1, "selected-way"),
        (3, 0, "selected-way-alias"),
        (3, 1, "selected-way-alias"),
        (2, 0, "hit"),
        (2, 1, "hit"),
        (2, 0, "miss"),
        (2, 1, "miss"),
    ]
    for number, (mode, way, hit_kind) in enumerate(definitions):
        index = 0x20 + number
        tag0 = 0x12000 + number * 4
        tag1 = tag0 + 1
        fill(index, tag0, f"s{number}:fill-way0")
        fill(index, tag1, f"s{number}:fill-way1")
        hit = hit_kind != "miss"
        cacop_tag = (tag0, tag1)[way] if hit else tag1 + 1
        dirty = target == "dcache" and hit and mode in (1, 2, 3)
        if dirty:
            dirty_store(index, (tag0, tag1)[way], f"s{number}:dirty-way{way}")
        label = f"s{number}:mode{mode}-way{way}-{hit_kind}"
        cacop(index, cacop_tag, mode, way, dirty, label)
        # Probe the selected line.  A broken invalidation turns this fixed miss/refill
        # schedule into an immediate trace mismatch against d22.
        fill(index, (tag0, tag1)[way], f"{label}:post-probe")
        scenarios.append(
            {
                "id": f"s{number}",
                "target": target,
                "mode": mode,
                "way": way,
                "lookup": hit_kind,
                "dirty_writeback": dirty,
                "rd_rdy_backpressure": True,
                "single_cycle_invalidation": hit or mode in (0, 1, 3),
            }
        )
    add("final-settle", count=4)
    return vectors, labels, scenarios


def write_vectors(path: Path, target: str, vectors: list[dict[str, int]]) -> None:
    fields = I_FIELDS if target == "icache" else D_FIELDS
    lines = [" ".join(str(vector[name]) for name in fields) for vector in vectors]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


DRIVER_COMMON = r'''
#include "V__TARGET__.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  V__TARGET__ d;
  std::ifstream vectors("vectors.txt");
  std::ofstream trace("trace.txt");
  std::string line;
  unsigned cycle = 0;
  while (std::getline(vectors, line)) {
    if (line.empty()) continue;
    std::istringstream in(line);
    uint64_t v[32] = {};
    for (unsigned i = 0; i < __FIELD_COUNT__; ++i) {
      if (!(in >> v[i])) return 2;
    }
    __DRIVE__
    d.clk = 0;
    d.eval();
    __TRACE__
    d.clk = 1;
    d.eval();
    ++cycle;
  }
  d.final();
  return vectors.bad() ? 3 : 0;
}
'''


I_DRIVE = r'''
    d.reset=v[0]; d.valid=v[1]; d.op=v[2]; d.index=v[3]; d.tag=v[4]; d.offset=v[5];
    d.wstrb=v[6]; d.wdata=v[7]; d.uncache_en=v[8]; d.icacop_op_en=v[9];
    d.cacop_op_mode=v[10]; d.cacop_op_addr_index=v[11]; d.cacop_op_addr_tag=v[12];
    d.cacop_op_addr_offset=v[13]; d.tlb_excp_cancel_req=v[14]; d.rd_rdy=v[15];
    d.ret_valid=v[16]; d.ret_last=v[17]; d.ret_data=v[18]; d.wr_rdy=v[19];'''


I_TRACE = r'''
    trace << std::hex << cycle << ' ' << (unsigned)d.addr_ok << ' ' << (unsigned)d.data_ok << ' '
      << (d.data_ok ? d.rdata : 0) << ' ' << (unsigned)d.icache_unbusy << ' ' << (unsigned)d.rd_req << ' '
      << (d.rd_req ? (unsigned)d.rd_type : 0) << ' ' << (d.rd_req ? d.rd_addr : 0) << ' '
      << (unsigned)d.cache_miss << ' ' << (unsigned)d.wr_req << ' '
      << (d.wr_req ? (unsigned)d.wr_type : 0) << ' ' << (d.wr_req ? d.wr_addr : 0) << ' '
      << (d.wr_req ? (unsigned)d.wr_wstrb : 0) << ' ' << (d.wr_req ? d.wr_data[0] : 0) << ' '
      << (d.wr_req ? d.wr_data[1] : 0) << ' ' << (d.wr_req ? d.wr_data[2] : 0) << ' '
      << (d.wr_req ? d.wr_data[3] : 0) << '\n';'''


D_DRIVE = r'''
    d.reset=v[0]; d.valid=v[1]; d.op=v[2]; d.size=v[3]; d.index=v[4]; d.tag=v[5];
    d.offset=v[6]; d.wstrb=v[7]; d.wdata=v[8]; d.uncache_en=v[9]; d.dcacop_op_en=v[10];
    d.cacop_op_mode=v[11]; d.preld_hint=v[12]; d.preld_en=v[13]; d.tlb_excp_cancel_req=v[14];
    d.sc_cancel_req=v[15]; d.rd_rdy=v[16]; d.ret_valid=v[17]; d.ret_last=v[18];
    d.ret_data=v[19]; d.wr_rdy=v[20];'''


D_TRACE = r'''
    trace << std::hex << cycle << ' ' << (unsigned)d.addr_ok << ' ' << (unsigned)d.data_ok << ' '
      << (d.data_ok ? d.rdata : 0) << ' ' << (unsigned)d.dcache_empty << ' ' << (unsigned)d.rd_req << ' '
      << (d.rd_req ? (unsigned)d.rd_type : 0) << ' ' << (d.rd_req ? d.rd_addr : 0) << ' '
      << (unsigned)d.cache_miss << ' ' << (unsigned)d.wr_req << ' '
      << (d.wr_req ? (unsigned)d.wr_type : 0) << ' ' << (d.wr_req ? d.wr_addr : 0) << ' '
      << (d.wr_req ? (unsigned)d.wr_wstrb : 0) << ' ' << (d.wr_req ? d.wr_data[0] : 0) << ' '
      << (d.wr_req ? d.wr_data[1] : 0) << ' ' << (d.wr_req ? d.wr_data[2] : 0) << ' '
      << (d.wr_req ? d.wr_data[3] : 0) << '\n';'''


def driver_for(target: str) -> str:
    fields = I_FIELDS if target == "icache" else D_FIELDS
    drive = I_DRIVE if target == "icache" else D_DRIVE
    trace = I_TRACE if target == "icache" else D_TRACE
    return (
        DRIVER_COMMON.replace("__TARGET__", target)
        .replace("__FIELD_COUNT__", str(len(fields)))
        .replace("__DRIVE__", drive)
        .replace("__TRACE__", trace)
    )


def build_trace(
    repo: Path,
    target: str,
    source: bytes,
    build_dir: Path,
    vectors: list[dict[str, int]],
    historical: bool,
) -> list[str]:
    build_dir.mkdir(parents=True)
    rtl = build_dir / f"{target}.v"
    rtl.write_bytes(source)
    driver = build_dir / "driver.cpp"
    driver.write_text(driver_for(target), encoding="utf-8")
    write_vectors(build_dir / "vectors.txt", target, vectors)
    sources = [str(rtl)]
    defines: list[str] = []
    if historical:
        tools_rtl = build_dir / "tools.v"
        tools_rtl.write_bytes(locked_source(repo, ORACLE_COMMIT, "rtl/tools.v"))
        sources.append(str(tools_rtl))
        defines.append("-DSIMU")
        if target == "icache":
            # The historical I-cache reuses the SRAM simulation models declared by dcache.v.
            dcache_rtl = build_dir / "dcache-sram-models.v"
            dcache_rtl.write_bytes(locked_source(repo, ORACLE_COMMIT, "rtl/dcache.v"))
            sources.append(str(dcache_rtl))
    verilator = shutil.which("verilator")
    if verilator is None:
        raise GateError("verilator unavailable")
    obj = build_dir / "obj"
    command = [
        verilator,
        "--cc",
        "--exe",
        "--build",
        "--top-module",
        target,
        "-Wall",
        "-Wno-fatal",
        "--Mdir",
        str(obj),
        *defines,
        *sources,
        str(driver),
        "-CFLAGS",
        "-std=c++17",
        "-o",
        "sim",
    ]
    compiled = run(command, build_dir, 300)
    (build_dir / "compile.log").write_bytes(compiled.stdout)
    if compiled.returncode or b"%Error" in compiled.stdout:
        raise GateError(f"Verilator build failed rc={compiled.returncode}: {build_dir}")
    executed = run([str(obj / "sim")], build_dir, 90)
    (build_dir / "simulation.log").write_bytes(executed.stdout)
    if executed.returncode:
        raise GateError(f"simulation failed rc={executed.returncode}: {build_dir}")
    trace = (build_dir / "trace.txt").read_text(encoding="ascii").splitlines()
    if len(trace) != len(vectors):
        raise GateError(f"trace length mismatch for {build_dir}: {len(trace)} != {len(vectors)}")
    return trace


def first_mismatch(left: list[str], right: list[str], labels: list[str]) -> dict[str, object] | None:
    for cycle, (expected, actual) in enumerate(zip(left, right)):
        if expected != actual:
            return {
                "cycle": cycle,
                "label": labels[cycle],
                "oracle": expected,
                "observed": actual,
            }
    if len(left) != len(right):
        return {"cycle": min(len(left), len(right)), "label": "trace-length"}
    return None


def assert_directed_observations(
    target: str,
    trace: list[str],
    labels: list[str],
    scenarios: list[dict[str, object]],
) -> dict[str, int]:
    rows = [[int(field, 16) for field in line.split()] for line in trace]

    def selected(suffix: str) -> list[list[int]]:
        return [row for row, label in zip(rows, labels) if label.endswith(suffix)]

    normal_backpressure = selected(":fill-way0:replace-backpressure") + selected(
        ":fill-way1:replace-backpressure"
    )
    if not normal_backpressure or any(row[5] != 1 for row in normal_backpressure):
        raise GateError(f"{target} directed trace did not observe rd_req held during backpressure")

    cacop_lookup_labels = {
        f"{scenario['id']}:mode{scenario['mode']}-way{scenario['way']}-{scenario['lookup']}:lookup"
        for scenario in scenarios
    }
    cacop_lookup = [
        row for row, label in zip(rows, labels) if label in cacop_lookup_labels
    ]
    if len(cacop_lookup) != len(scenarios) or any(row[2] != 0 for row in cacop_lookup):
        raise GateError(f"{target} CACOP lookup produced immediate data_ok")

    invalidation_probes = 0
    retained_miss_probes = 0
    for scenario in scenarios:
        prefix = f"{scenario['id']}:mode{scenario['mode']}-way{scenario['way']}-{scenario['lookup']}"
        invalidate_rows = [
            row for row, label in zip(rows, labels) if label == f"{prefix}:single-cycle-invalidate"
        ]
        settle_rows = [row for row, label in zip(rows, labels) if label == f"{prefix}:settle"]
        if len(invalidate_rows) != 1 or len(settle_rows) != 2:
            raise GateError(f"{target} malformed single-cycle refill window: {prefix}")
        if invalidate_rows[0][4] != 0 or settle_rows[0][4] != 1:
            raise GateError(f"{target} refill/invalidate window is not exactly one cycle: {prefix}")

        probe_replace = [
            row
            for row, label in zip(rows, labels)
            if label == f"{prefix}:post-probe:replace-backpressure"
        ]
        probe_lookup = [
            row for row, label in zip(rows, labels) if label == f"{prefix}:post-probe:lookup"
        ]
        if scenario["single_cycle_invalidation"]:
            if len(probe_replace) != 3 or any(row[5] != 1 for row in probe_replace):
                raise GateError(f"{target} post-CACOP probe did not miss after invalidation: {prefix}")
            invalidation_probes += 1
        else:
            if len(probe_lookup) != 1 or probe_lookup[0][2] != 1:
                raise GateError(f"{target} mode-2 miss unexpectedly invalidated a resident line: {prefix}")
            retained_miss_probes += 1

    dirty_writebacks = 0
    if target == "dcache":
        for scenario in scenarios:
            if not scenario["dirty_writeback"]:
                continue
            prefix = f"{scenario['id']}:mode{scenario['mode']}-way{scenario['way']}-{scenario['lookup']}"
            blocked = [
                row for row, label in zip(rows, labels) if label == f"{prefix}:writeback-backpressure"
            ]
            writeback = [row for row, label in zip(rows, labels) if label == f"{prefix}:replace"]
            if len(blocked) != 3 or any(row[9] != 0 for row in blocked):
                raise GateError(f"dcache dirty CACOP did not honor wr_rdy backpressure: {prefix}")
            if len(writeback) != 1 or writeback[0][9] != 1 or writeback[0][10] != 4:
                raise GateError(f"dcache dirty CACOP did not emit line writeback: {prefix}")
            dirty_writebacks += 1

    return {
        "normal_rd_rdy_backpressure_cycles": len(normal_backpressure),
        "cacop_lookup_without_data_ok": len(cacop_lookup),
        "single_cycle_invalidation_probes": invalidation_probes,
        "mode2_miss_retention_probes": retained_miss_probes,
        "dirty_writebacks": dirty_writebacks,
    }


def command_run(args: argparse.Namespace) -> dict[str, object]:
    out = fresh(args.out_dir)
    repo = args.repo.resolve()
    candidate_paths = {"icache": args.icache_rtl.resolve(), "dcache": args.dcache_rtl.resolve()}
    for target, path in candidate_paths.items():
        if not path.is_file():
            raise GateError(f"candidate {target} RTL missing: {path}")

    candidate_results: dict[str, object] = {}
    control_results: dict[str, dict[str, object]] = {name: {} for name in HISTORICAL_CONTROLS}
    all_scenarios: list[dict[str, object]] = []
    observed_coverage: dict[str, dict[str, int]] = {}
    total_cycles = 0
    oracle_traces: dict[str, list[str]] = {}
    vector_sets: dict[str, list[dict[str, int]]] = {}
    label_sets: dict[str, list[str]] = {}

    for target in ("icache", "dcache"):
        vectors, labels, scenarios = generate_vectors(target)
        vector_sets[target] = vectors
        label_sets[target] = labels
        all_scenarios.extend(scenarios)
        total_cycles += len(vectors)
        oracle = locked_source(repo, ORACLE_COMMIT, f"rtl/{target}.v")
        oracle_trace = build_trace(repo, target, oracle, out / target / "oracle", vectors, True)
        oracle_observed = assert_directed_observations(target, oracle_trace, labels, scenarios)
        oracle_traces[target] = oracle_trace
        candidate_trace = build_trace(
            repo,
            target,
            candidate_paths[target].read_bytes(),
            out / target / "candidate",
            vectors,
            False,
        )
        mismatch = first_mismatch(oracle_trace, candidate_trace, labels)
        candidate_observed = assert_directed_observations(target, candidate_trace, labels, scenarios)
        if candidate_observed != oracle_observed:
            raise GateError(f"{target} candidate directed observations differ from oracle")
        observed_coverage[target] = candidate_observed
        candidate_results[target] = {
            "cycles": len(vectors),
            "mismatches": 0 if mismatch is None else 1,
            "first_mismatch": mismatch,
            "rtl_sha256": hashlib.sha256(candidate_paths[target].read_bytes()).hexdigest(),
        }
        if mismatch is not None:
            raise GateError(f"candidate {target} first mismatch: {mismatch}")

    for name, commit in HISTORICAL_CONTROLS.items():
        detected = False
        for target in ("icache", "dcache"):
            source = locked_source(repo, commit, f"rtl/{target}.v")
            trace = build_trace(
                repo,
                target,
                source,
                out / target / "negative" / name,
                vector_sets[target],
                True,
            )
            mismatch = first_mismatch(oracle_traces[target], trace, label_sets[target])
            control_results[name][target] = {
                "detected": mismatch is not None,
                "first_mismatch": mismatch,
            }
            detected = detected or mismatch is not None
        control_results[name]["detected"] = detected
        if not detected:
            raise GateError(f"historical negative control was not detected: {name}")

    dirty_count = sum(bool(item["dirty_writeback"]) for item in all_scenarios)
    modes = sorted({int(item["mode"]) for item in all_scenarios})
    ways = sorted({int(item["way"]) for item in all_scenarios})
    lookups = sorted({str(item["lookup"]) for item in all_scenarios})
    result: dict[str, object] = {
        "schema_version": 1,
        "gate": "cacop-d22-directed-lockstep",
        "status": "pass",
        "generated_at": now_iso(),
        "oracle": {
            "commit": ORACLE_COMMIT,
            "scope": "iteration-local CACOP recovery oracle; global manifest unchanged",
        },
        "candidate": candidate_results,
        "negative_controls": control_results,
        "coverage": {
            "scenario_count": len(all_scenarios),
            "modes": modes,
            "ways": ways,
            "lookup_classes": lookups,
            "rd_rdy_backpressure_scenarios": sum(
                bool(item["rd_rdy_backpressure"]) for item in all_scenarios
            ),
            "single_cycle_invalidation_scenarios": sum(
                bool(item["single_cycle_invalidation"]) for item in all_scenarios
            ),
            "dcache_dirty_writeback_scenarios": dirty_count,
            "scenarios": all_scenarios,
            "observed": observed_coverage,
        },
        "counts": {
            "planned": 2 * (2 + len(HISTORICAL_CONTROLS)),
            "executed": 2 * (2 + len(HISTORICAL_CONTROLS)),
            "passed": 2 * (2 + len(HISTORICAL_CONTROLS)),
            "failed": 0,
            "negative_controls_detected": len(HISTORICAL_CONTROLS),
            "skipped": 0,
            "simulation_cycles_executed": total_cycles * (2 + len(HISTORICAL_CONTROLS)),
            "candidate_lockstep_cycles": total_cycles,
        },
    }
    write_json(out / "summary.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    if not sys.flags.isolated:
        print("cacop_recovery_gate.py requires python -I", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--icache-rtl", type=Path, required=True)
    parser.add_argument("--dcache-rtl", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = command_run(args)
    except (GateError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
