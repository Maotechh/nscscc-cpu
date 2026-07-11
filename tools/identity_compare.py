#!/usr/bin/env python3
"""Compare a locked chiplab smoke run with an identity mixed overlay run."""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import math
import os
import re
import stat
import sys
import time
from pathlib import Path
from typing import Any

try:
    from tools import refactor
except ModuleNotFoundError:  # python -I removes both cwd and the script directory.
    refactor_path = Path(__file__).resolve().with_name("refactor.py")
    refactor_spec = importlib.util.spec_from_file_location("refactor", refactor_path)
    if refactor_spec is None or refactor_spec.loader is None:
        raise RuntimeError(f"cannot load refactor module from {refactor_path}")
    refactor = importlib.util.module_from_spec(refactor_spec)
    sys.modules[refactor_spec.name] = refactor
    refactor_spec.loader.exec_module(refactor)


ITERATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
WARNING_CATEGORY_PATTERN = re.compile(r"[A-Z0-9_]+")
EXPECTED_ARTIFACT_SUFFIXES = (
    "/log/compile.log",
    "/obj_dir/Vsimu_top.mk",
    "/obj_dir/Vsimu_top__ALL.a",
    "/run_prog/output",
    "/obj/main.elf",
    "/obj/rom.vlog",
    "/simu_trace.txt",
    "/uart_output.txt",
    "/uart_output.txt.real",
)
EXPECTED_COMMAND_LOG_NAMES = ("01-configure.log", "02-build.log", "03-simulation.log")
SMOKE_ALLOWED_KEYS = frozenset(
    {
        "schema_version",
        "command",
        "generated_at",
        "status",
        "gate_result",
        "gate_eligible",
        "mode",
        "functional_status",
        "verilator_compile_status",
        "build_integrity_status",
        "simulation_eligible",
        "rtl_static_gate",
        "iteration_id",
        "run_id",
        "chiplab_commit",
        "dut_source",
        "provenance_mode",
        "gate_kind",
        "golden_candidate_commit",
        "candidate_locked",
        "base_candidate_locked",
        "baseline_exact",
        "component_replacement",
        "selection_sha256",
        "observed_result",
        "requested_case",
        "actual_case",
        "configure_valid",
        "removed_generated_paths",
        "compile_log_fresh",
        "build_artifacts_fresh",
        "build_artifacts",
        "build_errors",
        "output_contract_ok",
        "output_evidence",
        "post_run_dut_verification",
        "environment",
        "environment_sha256",
        "result_file_policy",
        "overlay_report_sha256",
        "doctor_report_sha256",
        "evaluator_sha256",
        "commands",
        "counts",
        "functional_counts",
        "verilator_compile_counts",
        "parser",
        "verilator_warnings",
        "compile_warning_policy",
        "lock_policy",
        "artifacts",
        "raw_dir",
    }
)
EXCLUDED_FIELDS = [
    "Vsimu_top__ALL.a",
    "simulator output binary",
    "compile and simulation log bytes",
    "cwd and absolute artifact paths",
    "run_id, timestamps, and elapsed time",
    "whole manifest/report hashes and cross-run selection hashes",
    "Verilator warning message text and absolute source locations",
    "non-semantic environment and raw-log byte differences",
]
CLAIM_SCOPE = (
    "The locked and mixed runs used the same manifest-bound DUT/test-input projection "
    "and produced the same selected rtl-smoke observations for one case. This is not "
    "CPU correctness, RTL formal equivalence, build-byte reproducibility, or a gate PASS."
)


class IdentityCompareError(RuntimeError):
    pass


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IdentityCompareError(f"{context} must be an object")
    return value


def _list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise IdentityCompareError(f"{context} must be a list")
    return value


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise IdentityCompareError(f"{context} must be a non-empty string")
    return value


def _sha256(value: Any, context: str) -> str:
    value = _string(value, context)
    if SHA256_PATTERN.fullmatch(value) is None:
        raise IdentityCompareError(f"{context} must be a lowercase SHA-256 digest")
    return value


def _git_sha(value: Any, context: str) -> str:
    value = _string(value, context)
    if GIT_SHA_PATTERN.fullmatch(value) is None:
        raise IdentityCompareError(f"{context} must be a lowercase 40-character Git SHA")
    return value


def _boolean(value: Any, context: str) -> bool:
    if type(value) is not bool:
        raise IdentityCompareError(f"{context} must be a JSON boolean")
    return value


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise IdentityCompareError(f"{context} must be an integer >= {minimum}")
    return value


def _nonnegative_number(value: Any, context: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise IdentityCompareError(f"{context} must be a nonnegative number")
    return float(value)


def _schema(value: dict[str, Any], context: str, *, command: str | None = None) -> None:
    if value.get("schema_version") != 1 or type(value.get("schema_version")) is not int:
        raise IdentityCompareError(f"{context} must use schema_version=1")
    if command is not None and value.get("command") != command:
        raise IdentityCompareError(f"{context} must report command={command}")


def _require_plain_path(path: Path, root: Path, context: str) -> Path:
    absolute = path.absolute()
    try:
        refactor.reject_link_or_reparse_path(absolute, context)
    except refactor.RefactorError as error:
        raise IdentityCompareError(str(error)) from error
    resolved = absolute.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise IdentityCompareError(f"{context} escapes its locked root: {path}") from error
    return resolved


def _read_json(path: Path, context: str, *, root: Path | None = None) -> tuple[dict[str, Any], str]:
    if root is not None:
        path = _require_plain_path(path, root, context)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise IdentityCompareError(f"cannot open {context} {path}: {error}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise IdentityCompareError(f"{context} must be a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as error:
        raise IdentityCompareError(f"cannot read {context} {path}: {error}") from error
    finally:
        os.close(descriptor)
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise IdentityCompareError(f"{context} changed while it was being read: {path}")
    payload = b"".join(chunks)
    try:
        text = payload.decode("utf-8")
        value = refactor.strict_json_loads(text, str(path))
    except (UnicodeError, refactor.RefactorError) as error:
        raise IdentityCompareError(f"cannot parse {context} {path}: {error}") from error
    digest = refactor.sha256_bytes(payload)
    return _object(value, context), digest


def _read_plain_bytes(path: Path, root: Path, context: str) -> bytes:
    path = _require_plain_path(path, root, context)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise IdentityCompareError(f"cannot open {context} {path}: {error}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise IdentityCompareError(f"{context} must be a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as error:
        raise IdentityCompareError(f"cannot read {context} {path}: {error}") from error
    finally:
        os.close(descriptor)
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise IdentityCompareError(f"{context} changed while it was being read: {path}")
    return b"".join(chunks)


def _canonical_paths(out_dir: Path, iteration_id: str) -> dict[str, Path]:
    if ITERATION_ID_PATTERN.fullmatch(iteration_id) is None:
        raise IdentityCompareError(f"invalid iteration id: {iteration_id!r}")
    root = out_dir / "reports" / "iterations" / iteration_id
    return {
        "overlay": root / "chiplab-overlay.json",
        "manifest": root / "chiplab-overlay-manifest.json",
        "smoke": root / "rtl-smoke.json",
    }


def _add_mismatch(mismatches: list[str], condition: bool, message: str) -> None:
    if not condition:
        mismatches.append(message)


def _critical_overlay_shape(
    report: dict[str, Any],
    manifest: dict[str, Any],
    *,
    mixed: bool,
    expected_iteration_id: str,
    mismatches: list[str],
) -> None:
    label = "mixed" if mixed else "locked"
    _schema(report, f"{label} overlay report", command="chiplab-overlay")
    _schema(manifest, f"{label} overlay manifest")
    expected = (
        {
            "dut_source": "mixed",
            "provenance_mode": "mixed_candidate",
            "gate_kind": "component_replacement",
            "mode": "diagnostic",
            "candidate_locked": False,
            "base_candidate_locked": True,
            "baseline_exact": False,
            "gate_eligible": False,
        }
        if mixed
        else {
            "dut_source": "candidate",
            "provenance_mode": "locked_candidate",
            "gate_kind": "baseline_candidate",
            "mode": "baseline",
            "candidate_locked": True,
            "base_candidate_locked": True,
            "baseline_exact": True,
            "gate_eligible": True,
        }
    )
    if report.get("iteration_id") != expected_iteration_id or manifest.get(
        "iteration_id"
    ) != expected_iteration_id:
        raise IdentityCompareError(
            f"{label} embedded iteration id does not match {expected_iteration_id}"
        )
    expected_status = "diagnostic" if mixed else "pass"
    if report.get("status") != expected_status:
        raise IdentityCompareError(f"{label} overlay status must be {expected_status}")
    for key, expected_value in expected.items():
        if isinstance(expected_value, bool):
            _boolean(report.get(key), f"{label} overlay report {key}")
            _boolean(manifest.get(key), f"{label} overlay manifest {key}")
        else:
            _string(report.get(key), f"{label} overlay report {key}")
            _string(manifest.get(key), f"{label} overlay manifest {key}")
        _add_mismatch(
            mismatches,
            report.get(key) == expected_value and manifest.get(key) == expected_value,
            f"{label} {key} does not have the required {expected_value!r} shape",
        )
    for key in (
        "iteration_id",
        "selection_sha256",
        "golden_candidate_commit",
        "component_replacement",
    ):
        _add_mismatch(
            mismatches,
            report.get(key) == manifest.get(key),
            f"{label} overlay report/manifest disagree on {key}",
        )
    _sha256(report.get("selection_sha256"), f"{label} overlay selection_sha256")
    _sha256(manifest.get("selection_sha256"), f"{label} manifest selection_sha256")
    _git_sha(
        report.get("golden_candidate_commit"), f"{label} overlay golden candidate"
    )
    _git_sha(
        manifest.get("golden_candidate_commit"), f"{label} manifest golden candidate"
    )
    files = _list(manifest.get("files"), f"{label} manifest files")
    file_count = _integer(report.get("file_count"), f"{label} report file_count", minimum=1)
    if file_count != len(files):
        raise IdentityCompareError(f"{label} report file_count does not match manifest files")
    replacement_count = _integer(
        report.get("replacement_count"), f"{label} replacement_count"
    )
    if (mixed and replacement_count < 1) or (not mixed and replacement_count != 0):
        raise IdentityCompareError(f"{label} replacement_count has an invalid value")
    if mixed:
        _object(report.get("component_replacement"), "mixed report component_replacement")
        _object(manifest.get("component_replacement"), "mixed manifest component_replacement")
    elif report.get("component_replacement") is not None or manifest.get(
        "component_replacement"
    ) is not None:
        raise IdentityCompareError("locked overlay must not contain a component replacement")


def _check_hash_chain(
    label: str,
    overlay: dict[str, Any],
    overlay_sha: str,
    manifest: dict[str, Any],
    manifest_sha: str,
    smoke: dict[str, Any],
    mismatches: list[str],
) -> None:
    _schema(smoke, f"{label} smoke", command="rtl-smoke")
    for key in (
        "iteration_id",
        "dut_source",
        "provenance_mode",
        "gate_kind",
        "mode",
        "candidate_locked",
        "base_candidate_locked",
        "baseline_exact",
        "gate_eligible",
        "golden_candidate_commit",
        "component_replacement",
    ):
        if key in {"candidate_locked", "base_candidate_locked", "baseline_exact", "gate_eligible"}:
            _boolean(smoke.get(key), f"{label} smoke {key}")
        _add_mismatch(
            mismatches,
            smoke.get(key) == overlay.get(key),
            f"{label} smoke/overlay disagree on {key}",
        )
    post_run = _object(smoke.get("post_run_dut_verification"), f"{label} post-run verification")
    overlay_manifest_digest = _sha256(
        overlay.get("overlay_manifest_sha256"), f"{label} overlay manifest SHA"
    )
    smoke_overlay_digest = _sha256(
        smoke.get("overlay_report_sha256"), f"{label} smoke overlay report SHA"
    )
    post_overlay_digest = _sha256(
        post_run.get("overlay_report_sha256"), f"{label} post-run overlay report SHA"
    )
    post_manifest_digest = _sha256(
        post_run.get("overlay_manifest_sha256"), f"{label} post-run manifest SHA"
    )
    _sha256(post_run.get("work_marker_sha256"), f"{label} post-run marker SHA")
    _sha256(overlay.get("work_marker_sha256"), f"{label} overlay marker SHA")
    _add_mismatch(
        mismatches,
        overlay_manifest_digest == manifest_sha,
        f"{label} overlay report is not bound to its manifest file",
    )
    _add_mismatch(
        mismatches,
        smoke_overlay_digest == overlay_sha,
        f"{label} smoke is not bound to its overlay report file",
    )
    _add_mismatch(
        mismatches,
        post_overlay_digest == overlay_sha,
        f"{label} post-run verification is not bound to its overlay report file",
    )
    _add_mismatch(
        mismatches,
        post_manifest_digest == manifest_sha,
        f"{label} post-run verification is not bound to its overlay manifest file",
    )
    _add_mismatch(
        mismatches,
        post_run.get("work_marker_sha256") == overlay.get("work_marker_sha256"),
        f"{label} post-run marker SHA differs from the overlay marker",
    )
    _add_mismatch(
        mismatches,
        post_run.get("status") == "pass",
        f"{label} post-run DUT verification did not pass",
    )
    post_workspace = _object(
        post_run.get("official_workspace_fingerprint"),
        f"{label} post-run official workspace fingerprint",
    )
    _sha256(
        post_workspace.get("sha256"),
        f"{label} post-run official workspace fingerprint SHA",
    )
    _integer(
        post_workspace.get("entry_count"),
        f"{label} post-run official workspace entry_count",
        minimum=1,
    )
    _add_mismatch(
        mismatches,
        post_workspace == manifest.get("post_smoke_official_workspace_fingerprint"),
        f"{label} post-run workspace fingerprint differs from its overlay manifest",
    )
    exclusions = _list(
        post_run.get("generated_path_exclusions"),
        f"{label} post-run generated path exclusions",
    )
    if exclusions != sorted(refactor.smoke_generated_relative_paths(refactor.LOCKED_SMOKE_CASE)):
        raise IdentityCompareError(f"{label} post-run generated path exclusions changed")
    selection = _sha256(manifest.get("selection_sha256"), f"{label} selection SHA")
    _sha256(overlay.get("selection_sha256"), f"{label} overlay selection SHA")
    _sha256(smoke.get("selection_sha256"), f"{label} smoke selection SHA")
    _sha256(post_run.get("selection_sha256"), f"{label} post-run selection SHA")
    _add_mismatch(
        mismatches,
        isinstance(selection, str)
        and overlay.get("selection_sha256") == selection
        and smoke.get("selection_sha256") == selection
        and post_run.get("selection_sha256") == selection,
        f"{label} selection SHA chain is inconsistent",
    )
    for key in ("doctor_report_sha256", "evaluator_sha256", "chiplab_commit"):
        if key.endswith("sha256"):
            _sha256(smoke.get(key), f"{label} smoke {key}")
            _sha256(manifest.get(key), f"{label} manifest {key}")
        else:
            _git_sha(smoke.get(key), f"{label} smoke {key}")
            _git_sha(manifest.get(key), f"{label} manifest {key}")
        _add_mismatch(
            mismatches,
            smoke.get(key) == manifest.get(key),
            f"{label} smoke/manifest disagree on {key}",
        )


def _file_projection(
    manifest: dict[str, Any], label: str, expected_paths: list[str]
) -> dict[str, dict[str, Any]]:
    projection: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_list(manifest.get("files"), f"{label} manifest files")):
        entry = _object(raw, f"{label} manifest files[{index}]")
        logical_path = _string(entry.get("logical_path"), f"{label} logical_path")
        if logical_path not in expected_paths:
            raise IdentityCompareError(f"{label} manifest has an unapproved DUT path {logical_path}")
        if logical_path in projection:
            raise IdentityCompareError(f"{label} manifest repeats logical_path {logical_path}")
        basename = Path(logical_path).name
        path = _string(entry.get("path"), f"{label} {logical_path} path")
        overlay_path = _string(
            entry.get("overlay_path"), f"{label} {logical_path} overlay_path"
        )
        digest = _sha256(entry.get("sha256"), f"{label} {logical_path} sha256")
        overlay_digest = _sha256(
            entry.get("overlay_sha256"), f"{label} {logical_path} overlay_sha256"
        )
        size = _integer(entry.get("size"), f"{label} {logical_path} size", minimum=1)
        base_mode = _string(entry.get("base_mode"), f"{label} {logical_path} base_mode")
        source_kind = _string(
            entry.get("source_kind"), f"{label} {logical_path} source_kind"
        )
        if path != basename or overlay_path != f"IP/myCPU/{basename}":
            raise IdentityCompareError(f"{label} manifest has a noncanonical target for {logical_path}")
        if digest != overlay_digest:
            raise IdentityCompareError(f"{label} installed/overlay SHA differ for {logical_path}")
        if base_mode not in {"100644", "100755"}:
            raise IdentityCompareError(f"{label} has invalid Git mode for {logical_path}")
        if source_kind not in {"golden", "replacement"}:
            raise IdentityCompareError(
                f"{label} has invalid source_kind for {logical_path}: {source_kind!r}"
            )
        projection[logical_path] = {
            "path": path,
            "overlay_path": overlay_path,
            "sha256": digest,
            "overlay_sha256": overlay_digest,
            "size": size,
            "base_mode": base_mode,
            "source_kind": source_kind,
        }
    if set(projection) != set(expected_paths) or len(projection) != len(expected_paths):
        raise IdentityCompareError(f"{label} manifest differs from the locked DUT allowlist")
    return projection


def _support_projection(manifest: dict[str, Any], label: str) -> list[dict[str, Any]]:
    support: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(
        _list(manifest.get("support_files"), f"{label} manifest support_files")
    ):
        entry = _object(raw, f"{label} support_files[{index}]")
        path = _string(entry.get("path"), f"{label} support path")
        if path in seen:
            raise IdentityCompareError(f"{label} repeats support file {path}")
        seen.add(path)
        support.append(
            {
                "path": path,
                "source": _string(entry.get("source"), f"{label} {path} source"),
                "sha256": _sha256(entry.get("sha256"), f"{label} {path} sha256"),
                "size": _integer(entry.get("size"), f"{label} {path} size", minimum=1),
            }
        )
    if seen != {"IP/myCPU/mycpu.h", "IP/myCPU/LICENSE"}:
        raise IdentityCompareError(f"{label} support files differ from the locked pair")
    return sorted(support, key=lambda item: str(item["path"]))


def _tool_projection(manifest: dict[str, Any], label: str) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(
        _list(manifest.get("tool_fingerprints"), f"{label} manifest tool_fingerprints")
    ):
        entry = _object(raw, f"{label} tool_fingerprints[{index}]")
        name = _string(entry.get("name"), f"{label} tool name")
        if name in seen:
            raise IdentityCompareError(f"{label} repeats tool fingerprint {name}")
        seen.add(name)
        actual = _sha256(entry.get("actual_sha256"), f"{label} {name} actual_sha256")
        expected = _sha256(entry.get("expected_sha256"), f"{label} {name} expected_sha256")
        if actual != expected:
            raise IdentityCompareError(f"{label} tool fingerprint {name} does not match its lock")
        tools.append(
            {
                "name": name,
                "manifest_key": _string(
                    entry.get("manifest_key"), f"{label} {name} manifest_key"
                ),
                "actual_sha256": actual,
                "expected_sha256": expected,
                "size": _integer(entry.get("size"), f"{label} {name} size", minimum=1),
            }
        )
    if not tools:
        raise IdentityCompareError(f"{label} manifest has no tool fingerprints")
    return sorted(tools, key=lambda item: item["name"])


def _common_manifest_projection(manifest: dict[str, Any], label: str) -> dict[str, Any]:
    official = _object(
        manifest.get("official_workspace_fingerprint"),
        f"{label} official workspace fingerprint",
    )
    if set(official) != {"entry_count", "sha256"}:
        raise IdentityCompareError(
            f"{label} official workspace fingerprint has an invalid schema"
        )
    official_projection = {
        "entry_count": _integer(
            official.get("entry_count"),
            f"{label} official workspace entry_count",
            minimum=1,
        ),
        "sha256": _sha256(
            official.get("sha256"), f"{label} official workspace sha256"
        ),
    }
    post_official = _object(
        manifest.get("post_smoke_official_workspace_fingerprint"),
        f"{label} post-smoke official workspace fingerprint",
    )
    if set(post_official) != {"entry_count", "sha256"}:
        raise IdentityCompareError(
            f"{label} post-smoke official workspace fingerprint has an invalid schema"
        )
    post_official_projection = {
        "entry_count": _integer(
            post_official.get("entry_count"),
            f"{label} post-smoke official workspace entry_count",
            minimum=1,
        ),
        "sha256": _sha256(
            post_official.get("sha256"),
            f"{label} post-smoke official workspace sha256",
        ),
    }
    tool_links = _object(manifest.get("tool_links"), f"{label} tool_links")
    if set(tool_links) != {"gcc", "nemu", "picolibc"}:
        raise IdentityCompareError(f"{label} tool_links has an invalid schema")
    return {
        "chiplab_commit": _git_sha(
            manifest.get("chiplab_commit"), f"{label} chiplab_commit"
        ),
        "chiplab_tree": _git_sha(
            manifest.get("chiplab_tree"), f"{label} chiplab_tree"
        ),
        "mycpu_reference_commit": _git_sha(
            manifest.get("mycpu_reference_commit"),
            f"{label} mycpu_reference_commit",
        ),
        "golden_candidate_commit": _git_sha(
            manifest.get("golden_candidate_commit"),
            f"{label} golden_candidate_commit",
        ),
        "manifest_sha256": _sha256(
            manifest.get("manifest_sha256"), f"{label} manifest_sha256"
        ),
        "golden_files_lock_sha256": _sha256(
            manifest.get("golden_files_lock_sha256"),
            f"{label} golden_files_lock_sha256",
        ),
        "doctor_report_sha256": _sha256(
            manifest.get("doctor_report_sha256"),
            f"{label} doctor_report_sha256",
        ),
        "evaluator_sha256": _sha256(
            manifest.get("evaluator_sha256"), f"{label} evaluator_sha256"
        ),
        "chiplab_reference": _string(
            manifest.get("chiplab_reference"), f"{label} chiplab_reference"
        ),
        "work_filesystem": _string(
            manifest.get("work_filesystem"), f"{label} work_filesystem"
        ),
        "official_workspace_fingerprint": official_projection,
        "post_smoke_official_workspace_fingerprint": post_official_projection,
        "tool_links": {
            name: _string(tool_links.get(name), f"{label} tool_links.{name}")
            for name in ("gcc", "nemu", "picolibc")
        },
    }


def _artifact_by_suffix(
    smoke: dict[str, Any], suffix: str, label: str
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for index, raw in enumerate(_list(smoke.get("artifacts"), f"{label} smoke artifacts")):
        artifact = _object(raw, f"{label} smoke artifacts[{index}]")
        path = _string(artifact.get("path"), f"{label} artifact path")
        if path.replace("\\", "/").endswith(suffix):
            matches.append(artifact)
    if len(matches) != 1:
        raise IdentityCompareError(
            f"{label} smoke must contain exactly one artifact ending with {suffix!r}"
        )
    artifact = matches[0]
    return {
        "sha256": _sha256(artifact.get("sha256"), f"{label} {suffix} sha256"),
        "size": _integer(artifact.get("size"), f"{label} {suffix} size", minimum=1),
    }


def _output_evidence_projection(smoke: dict[str, Any], label: str) -> dict[str, Any]:
    output = _object(smoke.get("output_evidence"), f"{label} output_evidence")
    projection: dict[str, Any] = {}
    for role in ("simu_trace", "uart", "uart_real"):
        entry = _object(output.get(role), f"{label} output_evidence.{role}")
        exists = _boolean(entry.get("exists"), f"{label} {role} exists")
        fresh = _boolean(entry.get("fresh"), f"{label} {role} fresh")
        if not exists or not fresh:
            raise IdentityCompareError(f"{label} {role} is missing or stale")
        _string(entry.get("path"), f"{label} {role} path")
        oracle_role = _string(
            entry.get("oracle_role"), f"{label} {role} oracle_role"
        )
        expected_oracle_role = (
            "trace_artifact"
            if role == "simu_trace"
            else "not_applicable_for_func_lab19"
        )
        if oracle_role != expected_oracle_role:
            raise IdentityCompareError(f"{label} {role} oracle role changed")
        projection[role] = {
            "exists": exists,
            "fresh": fresh,
            "oracle_role": oracle_role,
            "sha256": _sha256(entry.get("sha256"), f"{label} {role} sha256"),
            "size": _integer(
                entry.get("size"),
                f"{label} {role} size",
                minimum=1 if role == "simu_trace" else 0,
            ),
        }
    return projection


def _environment_projection(smoke: dict[str, Any], label: str) -> dict[str, str]:
    environment = _object(smoke.get("environment"), f"{label} environment")
    expected_keys = {"HOME", "PATH", "LANG", "LC_ALL", "TZ", "CHIPLAB_HOME"}
    if set(environment) != expected_keys:
        raise IdentityCompareError(f"{label} smoke environment has an invalid schema")
    validated = {
        key: _string(environment.get(key), f"{label} environment.{key}")
        for key in sorted(expected_keys)
    }
    for key, expected in {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC"}.items():
        if validated[key] != expected:
            raise IdentityCompareError(f"{label} environment.{key} changed")
    digest = refactor.sha256_bytes(
        json.dumps(validated, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    if digest != _sha256(
        smoke.get("environment_sha256"), f"{label} environment_sha256"
    ):
        raise IdentityCompareError(f"{label} environment hash does not match its report")
    return {
        key: value for key, value in validated.items() if key != "CHIPLAB_HOME"
    }


def _command_projection(smoke: dict[str, Any], label: str) -> list[list[str]]:
    commands: list[list[str]] = []
    for index, raw in enumerate(_list(smoke.get("commands"), f"{label} smoke commands")):
        command = _object(raw, f"{label} smoke commands[{index}]")
        argv = command.get("command")
        if not isinstance(argv, list) or not argv or any(
            not isinstance(item, str) or not item for item in argv
        ):
            raise IdentityCompareError(f"{label} smoke command[{index}] has invalid argv")
        _integer(command.get("exit_code"), f"{label} smoke command[{index}] exit_code")
        _boolean(command.get("timed_out"), f"{label} smoke command[{index}] timed_out")
        _nonnegative_number(
            command.get("elapsed_seconds"),
            f"{label} smoke command[{index}] elapsed_seconds",
        )
        _string(command.get("cwd"), f"{label} smoke command[{index}] cwd")
        _string(command.get("log_path"), f"{label} smoke command[{index}] log_path")
        _sha256(command.get("log_sha256"), f"{label} smoke command[{index}] log_sha256")
        if command.get("exit_code") != 0 or command.get("timed_out") is not False:
            raise IdentityCompareError(f"{label} smoke command[{index}] failed or timed out")
        commands.append(argv)
    expected = [
        ["./configure.sh", "--run", refactor.LOCKED_SMOKE_CASE],
        ["make", "verilator", "testbench", "soft_compile"],
        ["make", "simulation_run_prog"],
    ]
    if commands != expected:
        raise IdentityCompareError(f"{label} smoke did not execute the locked command sequence")
    return commands


def _warning_projection(smoke: dict[str, Any], label: str) -> dict[str, Any]:
    by_scope: collections.Counter[str] = collections.Counter(
        {"dut": 0, "official_environment": 0}
    )
    by_scope_category: collections.Counter[tuple[str, str]] = collections.Counter()
    for index, raw in enumerate(
        _list(smoke.get("verilator_warnings"), f"{label} verilator_warnings")
    ):
        warning = _object(raw, f"{label} verilator_warnings[{index}]")
        scope = _string(warning.get("scope"), f"{label} warning scope")
        category = _string(warning.get("category"), f"{label} warning category")
        _string(warning.get("line"), f"{label} warning line")
        if scope not in {"dut", "official_environment"}:
            raise IdentityCompareError(f"{label} warning has an invalid scope {scope!r}")
        if WARNING_CATEGORY_PATTERN.fullmatch(category) is None:
            raise IdentityCompareError(f"{label} warning has an invalid category {category!r}")
        by_scope[scope] += 1
        by_scope_category[(scope, category)] += 1
    return {
        "total": sum(by_scope.values()),
        "by_scope": dict(sorted(by_scope.items())),
        "by_scope_category": [
            {"scope": scope, "category": category, "count": count}
            for (scope, category), count in sorted(by_scope_category.items())
        ],
    }


def _validate_counts(value: Any, context: str) -> dict[str, int]:
    counts = _object(value, context)
    result = {
        key: _integer(counts.get(key), f"{context}.{key}")
        for key in ("planned", "executed", "passed", "failed", "skipped")
    }
    if result["planned"] != 1:
        raise IdentityCompareError(f"{context}.planned must equal the single locked case")
    if result["executed"] != result["passed"] + result["failed"]:
        raise IdentityCompareError(f"{context} executed/pass/fail counts are inconsistent")
    if result["planned"] != result["executed"] + result["skipped"]:
        raise IdentityCompareError(f"{context} planned/executed/skipped counts are inconsistent")
    if result["executed"] != result["planned"] or result["skipped"] != 0:
        raise IdentityCompareError(f"{context} contains unexecuted or skipped work")
    return result


def _validate_parser(value: Any, label: str) -> dict[str, Any]:
    parser = _object(value, f"{label} parser")
    status = _string(parser.get("status"), f"{label} parser status")
    if status not in {"pass", "fail"}:
        raise IdentityCompareError(f"{label} parser has an invalid status")
    _integer(parser.get("instructions"), f"{label} parser instructions", minimum=1)
    _integer(parser.get("clocks"), f"{label} parser clocks", minimum=1)
    failures = _list(parser.get("failures"), f"{label} parser failures")
    if any(not isinstance(item, str) or not item for item in failures):
        raise IdentityCompareError(f"{label} parser failures are malformed")
    excerpt = _list(parser.get("failure_excerpt"), f"{label} parser failure_excerpt")
    if any(not isinstance(item, str) or not item for item in excerpt):
        raise IdentityCompareError(f"{label} parser failure excerpt is malformed")
    first_mismatch = parser.get("first_mismatch")
    if status == "fail":
        _string(first_mismatch, f"{label} parser first_mismatch")
        if not failures or not excerpt:
            raise IdentityCompareError(f"{label} failing parser lacks diagnostics")
    elif first_mismatch is not None:
        raise IdentityCompareError(f"{label} passing parser reports a mismatch")
    markers = _object(parser.get("markers"), f"{label} parser markers")
    expected_markers = {
        "difftest_library_loaded",
        "difftest_enabled",
        "good_trap",
        "end_by_syscall",
        "reached_test_end",
        "nonzero_instructions",
        "nonzero_clocks",
    }
    if set(markers) != expected_markers:
        raise IdentityCompareError(f"{label} parser marker set is incomplete")
    for name in expected_markers:
        _boolean(markers.get(name), f"{label} parser marker {name}")
    if not markers["difftest_library_loaded"] or not markers["difftest_enabled"]:
        raise IdentityCompareError(f"{label} parser did not observe active DiffTest")
    if not markers["nonzero_instructions"] or not markers["nonzero_clocks"]:
        raise IdentityCompareError(f"{label} parser did not observe nonzero execution")
    return parser


def _validate_smoke_contract(smoke: dict[str, Any], label: str) -> dict[str, Any]:
    unknown_keys = set(smoke) - SMOKE_ALLOWED_KEYS
    if unknown_keys:
        raise IdentityCompareError(
            f"{label} smoke contains unknown fields: {sorted(unknown_keys)}"
        )
    requested = _string(smoke.get("requested_case"), f"{label} requested_case")
    actual = _string(smoke.get("actual_case"), f"{label} actual_case")
    if requested != refactor.LOCKED_SMOKE_CASE or actual != requested:
        raise IdentityCompareError(f"{label} did not run the locked smoke case")
    required_true = (
        "configure_valid",
        "compile_log_fresh",
        "build_artifacts_fresh",
        "output_contract_ok",
        "simulation_eligible",
    )
    for key in required_true:
        if not _boolean(smoke.get(key), f"{label} smoke {key}"):
            raise IdentityCompareError(f"{label} smoke {key} is false")
    if _list(smoke.get("build_errors"), f"{label} build_errors"):
        raise IdentityCompareError(f"{label} smoke reports build errors")
    if smoke.get("build_integrity_status") != "pass":
        raise IdentityCompareError(f"{label} build integrity did not pass")
    compile_status = _string(
        smoke.get("verilator_compile_status"), f"{label} verilator_compile_status"
    )
    if compile_status not in {"pass", "warning"}:
        raise IdentityCompareError(f"{label} Verilator compile status is invalid")
    gate_result = _string(smoke.get("gate_result"), f"{label} gate_result")
    functional_status = _string(
        smoke.get("functional_status"), f"{label} functional_status"
    )
    if gate_result not in {"pass", "fail"} or functional_status not in {"pass", "fail"}:
        raise IdentityCompareError(f"{label} smoke has invalid result status")
    report_status = _string(smoke.get("status"), f"{label} report status")
    expected_status = "diagnostic" if label == "mixed" else gate_result
    if report_status != expected_status:
        raise IdentityCompareError(f"{label} smoke report status contradicts its mode/result")
    observed_result = smoke.get("observed_result")
    if (label == "mixed" and observed_result != gate_result) or (
        label == "locked" and observed_result is not None
    ):
        raise IdentityCompareError(f"{label} observed_result has an invalid shape")
    run_id = _string(smoke.get("run_id"), f"{label} run_id")
    if ITERATION_ID_PATTERN.fullmatch(run_id) is None:
        raise IdentityCompareError(f"{label} run_id is not canonical")
    parser = _validate_parser(smoke.get("parser"), label)
    if parser["status"] != functional_status:
        raise IdentityCompareError(f"{label} parser and functional status disagree")
    counts = _validate_counts(smoke.get("counts"), f"{label} counts")
    functional_counts = _validate_counts(
        smoke.get("functional_counts"), f"{label} functional_counts"
    )
    compile_counts = _validate_counts(
        smoke.get("verilator_compile_counts"), f"{label} verilator_compile_counts"
    )
    if (functional_status == "pass") != (functional_counts["passed"] == 1):
        raise IdentityCompareError(f"{label} functional counts contradict status")
    if (gate_result == "pass") != (counts["passed"] == 1):
        raise IdentityCompareError(f"{label} gate counts contradict gate_result")
    if (compile_status == "pass") != (compile_counts["passed"] == 1):
        raise IdentityCompareError(f"{label} compile counts contradict compile status")
    warning_policy = _object(
        smoke.get("compile_warning_policy"), f"{label} compile_warning_policy"
    )
    policy_status = _string(
        warning_policy.get("status"), f"{label} compile warning policy status"
    )
    if policy_status not in {"pass", "fail"}:
        raise IdentityCompareError(f"{label} warning policy status is invalid")
    warning_rule = _string(
        warning_policy.get("rule"), f"{label} compile warning policy rule"
    )
    scope_counts = _object(
        warning_policy.get("counts_by_scope"), f"{label} warning counts_by_scope"
    )
    for scope in ("dut", "official_environment"):
        _integer(scope_counts.get(scope), f"{label} warning scope {scope}")
    rtl_static_gate = _string(smoke.get("rtl_static_gate"), f"{label} rtl_static_gate")
    if rtl_static_gate != "not_executed_by_rtl_smoke":
        raise IdentityCompareError(f"{label} rtl-static disclosure changed")
    commands = _command_projection(smoke, label)
    output = _output_evidence_projection(smoke, label)
    environment = _environment_projection(smoke, label)
    warnings = _warning_projection(smoke, label)
    if warnings["by_scope"] != scope_counts:
        raise IdentityCompareError(f"{label} warning list/count projection disagrees")
    if (warnings["total"] == 0) != (policy_status == "pass"):
        raise IdentityCompareError(f"{label} warning policy contradicts warning list")
    expected_compile_status = "pass" if warnings["total"] == 0 else "warning"
    if compile_status != expected_compile_status:
        raise IdentityCompareError(
            f"{label} compile status contradicts the locked warning policy"
        )
    expected_gate_result = (
        "pass"
        if functional_status == "pass" and compile_status == "pass"
        else "fail"
    )
    if gate_result != expected_gate_result:
        raise IdentityCompareError(
            f"{label} gate result contradicts functional/compile status"
        )
    result_policy = _object(smoke.get("result_file_policy"), f"{label} result_file_policy")
    if set(result_policy) != {"status", "functional_oracle"}:
        raise IdentityCompareError(f"{label} result-file policy has an invalid schema")
    result_policy_projection = {
        "status": _string(result_policy.get("status"), f"{label} result policy status"),
        "functional_oracle": _string(
            result_policy.get("functional_oracle"),
            f"{label} result policy functional_oracle",
        ),
    }
    if result_policy_projection != {
        "status": "not_provided_by_locked_func_lab19",
        "functional_oracle": (
            "NEMU DPI DiffTest markers and simulator termination output"
        ),
    }:
        raise IdentityCompareError(f"{label} result-file policy changed")
    return {
        "run_id": run_id,
        "case": actual,
        "commands": commands,
        "counts": counts,
        "functional_counts": functional_counts,
        "compile_counts": compile_counts,
        "parser": parser,
        "gate_result": gate_result,
        "functional_status": functional_status,
        "compile_status": compile_status,
        "warning_policy_status": policy_status,
        "warning_policy_rule": warning_rule,
        "rtl_static_gate": rtl_static_gate,
        "environment": environment,
        "result_file_policy": result_policy_projection,
        "output": output,
        "warnings": warnings,
    }


def _verify_physical_smoke_artifacts(
    smoke: dict[str, Any],
    *,
    label: str,
    out_dir: Path,
    work_root: Path,
    iteration_id: str,
) -> None:
    work = _require_plain_path(work_root / iteration_id, work_root, f"{label} worktree")
    if not work.is_dir():
        raise IdentityCompareError(f"{label} worktree is missing: {work}")
    expected_run_dir = _require_plain_path(
        work / "sims" / "verilator" / "run_prog",
        work,
        f"{label} run directory",
    )
    if not expected_run_dir.is_dir():
        raise IdentityCompareError(f"{label} run directory is missing: {expected_run_dir}")
    expected_artifact_paths = {
        "/log/compile.log": expected_run_dir / "log" / "compile.log",
        "/obj_dir/Vsimu_top.mk": expected_run_dir / "obj_dir" / "Vsimu_top.mk",
        "/obj_dir/Vsimu_top__ALL.a": expected_run_dir
        / "obj_dir"
        / "Vsimu_top__ALL.a",
        "/run_prog/output": expected_run_dir / "output",
        "/obj/main.elf": expected_run_dir
        / "obj"
        / f"{refactor.LOCKED_SMOKE_CASE}_obj"
        / "obj"
        / "main.elf",
        "/obj/rom.vlog": expected_run_dir
        / "obj"
        / f"{refactor.LOCKED_SMOKE_CASE}_obj"
        / "obj"
        / "rom.vlog",
        "/simu_trace.txt": expected_run_dir
        / "log"
        / f"{refactor.LOCKED_SMOKE_CASE}_log"
        / "simu_trace.txt",
        "/uart_output.txt": expected_run_dir
        / "log"
        / f"{refactor.LOCKED_SMOKE_CASE}_log"
        / "uart_output.txt",
        "/uart_output.txt.real": expected_run_dir
        / "log"
        / f"{refactor.LOCKED_SMOKE_CASE}_log"
        / "uart_output.txt.real",
    }
    artifacts = _list(smoke.get("artifacts"), f"{label} artifacts")
    if len(artifacts) != 9:
        raise IdentityCompareError(f"{label} smoke must bind exactly nine artifacts")
    physical: dict[Path, dict[str, Any]] = {}
    artifact_roles: dict[str, Path] = {}
    for index, raw in enumerate(artifacts):
        artifact = _object(raw, f"{label} artifacts[{index}]")
        declared_path = Path(_string(artifact.get("path"), f"{label} artifact path"))
        path = _require_plain_path(declared_path, work, f"{label} artifact")
        if path in physical:
            raise IdentityCompareError(f"{label} repeats artifact path {path}")
        payload = _read_plain_bytes(path, work, f"{label} artifact")
        digest = _sha256(artifact.get("sha256"), f"{label} artifact sha256")
        size = _integer(artifact.get("size"), f"{label} artifact size")
        if digest != refactor.sha256_bytes(payload) or size != len(payload):
            raise IdentityCompareError(f"{label} artifact content differs from its report: {path}")
        normalized = str(path).replace("\\", "/")
        matches = [
            suffix for suffix in EXPECTED_ARTIFACT_SUFFIXES if normalized.endswith(suffix)
        ]
        if len(matches) != 1 or matches[0] in artifact_roles:
            raise IdentityCompareError(
                f"{label} artifact is not a unique member of the locked artifact set: {path}"
            )
        expected_path = _require_plain_path(
            expected_artifact_paths[matches[0]],
            work,
            f"{label} canonical artifact",
        )
        if path != expected_path:
            raise IdentityCompareError(f"{label} artifact path is not canonical: {path}")
        artifact_roles[matches[0]] = path
        physical[path] = {"sha256": digest, "size": size}
    if set(artifact_roles) != set(EXPECTED_ARTIFACT_SUFFIXES):
        raise IdentityCompareError(f"{label} physical artifact role set is incomplete")

    build_artifacts = _list(smoke.get("build_artifacts"), f"{label} build_artifacts")
    if len(build_artifacts) != 6:
        raise IdentityCompareError(f"{label} smoke must bind exactly six build artifacts")
    build_roles: set[str] = set()
    for index, raw in enumerate(build_artifacts):
        entry = _object(raw, f"{label} build_artifacts[{index}]")
        if not _boolean(entry.get("exists"), f"{label} build artifact exists") or not _boolean(
            entry.get("fresh"), f"{label} build artifact fresh"
        ):
            raise IdentityCompareError(f"{label} build artifact is missing or stale")
        path = _require_plain_path(
            Path(_string(entry.get("path"), f"{label} build artifact path")),
            work,
            f"{label} build artifact",
        )
        normalized = str(path).replace("\\", "/")
        matches = [
            suffix for suffix in EXPECTED_ARTIFACT_SUFFIXES[:6] if normalized.endswith(suffix)
        ]
        if len(matches) != 1 or matches[0] in build_roles or path not in physical:
            raise IdentityCompareError(f"{label} build artifact role set is invalid")
        build_roles.add(matches[0])
        if (
            entry.get("sha256") != physical[path]["sha256"]
            or entry.get("size") != physical[path]["size"]
        ):
            raise IdentityCompareError(
                f"{label} build artifact disagrees with the physical artifact manifest"
            )
    if build_roles != set(EXPECTED_ARTIFACT_SUFFIXES[:6]):
        raise IdentityCompareError(f"{label} build artifact role set is incomplete")

    output = _object(smoke.get("output_evidence"), f"{label} output_evidence")
    for role in ("simu_trace", "uart", "uart_real"):
        entry = _object(output.get(role), f"{label} output_evidence.{role}")
        path = _require_plain_path(
            Path(_string(entry.get("path"), f"{label} {role} path")),
            work,
            f"{label} {role}",
        )
        if path not in physical:
            raise IdentityCompareError(f"{label} {role} is not in the artifact manifest")
        if (
            physical[path]["sha256"] != entry.get("sha256")
            or physical[path]["size"] != entry.get("size")
        ):
            raise IdentityCompareError(f"{label} {role} disagrees with its artifact entry")

    commands = _list(smoke.get("commands"), f"{label} commands")
    if len(commands) != 3:
        raise IdentityCompareError(f"{label} command log set is incomplete")
    command_logs: list[bytes] = []
    seen_logs: set[Path] = set()
    environment = _object(smoke.get("environment"), f"{label} environment")
    if Path(_string(environment.get("CHIPLAB_HOME"), f"{label} CHIPLAB_HOME")).resolve() != work:
        raise IdentityCompareError(f"{label} CHIPLAB_HOME differs from the verified worktree")
    raw_root = out_dir / "raw" / "iterations" / iteration_id / "rtl-smoke"
    raw_dir = _require_plain_path(
        Path(_string(smoke.get("raw_dir"), f"{label} raw_dir")),
        raw_root,
        f"{label} raw directory",
    )
    run_id = _string(smoke.get("run_id"), f"{label} run_id")
    if (
        not raw_dir.is_dir()
        or raw_dir.parent != raw_root.resolve()
        or raw_dir.name != run_id
    ):
        raise IdentityCompareError(f"{label} raw directory is not a canonical run directory")
    for index, raw in enumerate(commands):
        command = _object(raw, f"{label} commands[{index}]")
        cwd = _require_plain_path(
            Path(_string(command.get("cwd"), f"{label} command cwd")),
            work,
            f"{label} command cwd",
        )
        if cwd != expected_run_dir:
            raise IdentityCompareError(f"{label} command cwd differs from run_prog")
        log_path = _require_plain_path(
            Path(_string(command.get("log_path"), f"{label} command log path")),
            out_dir,
            f"{label} command log",
        )
        if log_path in seen_logs:
            raise IdentityCompareError(f"{label} repeats command log {log_path}")
        if log_path.parent != raw_dir or log_path.name != EXPECTED_COMMAND_LOG_NAMES[index]:
            raise IdentityCompareError(
                f"{label} command log is not in the canonical raw run directory"
            )
        seen_logs.add(log_path)
        payload = _read_plain_bytes(log_path, out_dir, f"{label} command log")
        if refactor.sha256_bytes(payload) != command.get("log_sha256"):
            raise IdentityCompareError(f"{label} command log SHA mismatch: {log_path}")
        command_logs.append(payload)
    try:
        raw_build_text = command_logs[1].decode("utf-8")
        simulation_text = command_logs[2].decode("utf-8")
        compile_text = _read_plain_bytes(
            artifact_roles["/log/compile.log"],
            work,
            f"{label} physical compile log",
        ).decode("utf-8")
    except UnicodeError as error:
        raise IdentityCompareError(f"{label} compile/simulation log is not UTF-8") from error
    if refactor.parse_verilator_warnings(compile_text) != smoke.get("verilator_warnings"):
        raise IdentityCompareError(f"{label} warning report differs from compile.log")
    combined_build_text = compile_text + "\n" + raw_build_text
    if refactor.parse_build_errors(combined_build_text) != smoke.get("build_errors"):
        raise IdentityCompareError(
            f"{label} build error report differs from compile/raw build logs"
        )
    if refactor.parse_simulation_log(simulation_text) != smoke.get("parser"):
        raise IdentityCompareError(f"{label} parser report differs from the simulation log")


def _runtime_anchors(
    out_dir: Path, chiplab_ref: Path, tool_root: Path
) -> dict[str, Any]:
    try:
        doctor_path, doctor, doctor_sha = refactor.require_passing_chiplab_doctor(
            out_dir, chiplab_ref, tool_root, 86400
        )
        head = refactor.git_text(["rev-parse", "HEAD"])
        source_state = refactor.require_clean_source_head(head)
        manifest = refactor.parse_lock(refactor.MANIFEST_PATH)
        manifest_sha = refactor.sha256_file(refactor.MANIFEST_PATH)
        golden_files = refactor.read_golden_files()
        golden_files_sha = refactor.sha256_file(refactor.GOLDEN_FILES_PATH)
        refactor_sha = refactor.sha256_file(Path(refactor.__file__))
        comparator_sha = refactor.sha256_file(Path(__file__))
    except (OSError, refactor.RefactorError) as error:
        raise IdentityCompareError(f"runtime provenance check failed: {error}") from error
    return {
        "doctor_path": doctor_path,
        "doctor": _object(doctor, "current chiplab doctor"),
        "doctor_sha256": doctor_sha,
        "manifest": manifest,
        "manifest_sha256": manifest_sha,
        "golden_files": golden_files,
        "golden_files_sha256": golden_files_sha,
        "refactor_sha256": refactor_sha,
        "comparator_sha256": comparator_sha,
        "head_sha": head,
        "source_state": source_state,
        "chiplab_reference": str(chiplab_ref.resolve()),
        "tool_root": str(tool_root.resolve()),
    }


def _runtime_anchor_projection(anchors: dict[str, Any]) -> dict[str, Any]:
    source_state = _object(anchors.get("source_state"), "runtime source state")
    head = _git_sha(anchors.get("head_sha"), "runtime HEAD")
    if _git_sha(source_state.get("head"), "runtime source-state HEAD") != head:
        raise IdentityCompareError("runtime source-state HEAD disagrees with current HEAD")
    if not _boolean(source_state.get("semantic_clean"), "runtime semantic clean"):
        raise IdentityCompareError("runtime source tree is not semantically clean")
    return {
        "head_sha": head,
        "source_tree": _git_sha(source_state.get("tree"), "runtime source tree"),
        "source_branch": _string(source_state.get("branch"), "runtime source branch"),
        "source_porcelain_clean": _boolean(
            source_state.get("porcelain_clean"), "runtime source porcelain clean"
        ),
        "source_semantic_clean": True,
        "source_eol_normalization_only": _boolean(
            source_state.get("eol_normalization_only"),
            "runtime source EOL normalization",
        ),
        "source_status_entry_count": _integer(
            source_state.get("status_entry_count"), "runtime source status entry count"
        ),
        "doctor_sha256": _sha256(
            anchors.get("doctor_sha256"), "runtime doctor SHA"
        ),
        "manifest_sha256": _sha256(
            anchors.get("manifest_sha256"), "runtime manifest SHA"
        ),
        "golden_files_sha256": _sha256(
            anchors.get("golden_files_sha256"), "runtime golden allowlist SHA"
        ),
        "evaluator_sha256": _sha256(
            anchors.get("refactor_sha256"), "runtime evaluator SHA"
        ),
        "comparator_sha256": _sha256(
            anchors.get("comparator_sha256"), "runtime comparator SHA"
        ),
        "chiplab_reference": _string(
            anchors.get("chiplab_reference"), "runtime chiplab reference"
        ),
        "tool_root": _string(anchors.get("tool_root"), "runtime tool root"),
    }


def _validate_runtime_bindings(
    *,
    locked_overlay: dict[str, Any],
    locked_manifest: dict[str, Any],
    locked_smoke: dict[str, Any],
    mixed_overlay: dict[str, Any],
    mixed_manifest: dict[str, Any],
    mixed_smoke: dict[str, Any],
    anchors: dict[str, Any],
    work_root: Path,
    out_dir: Path,
    chiplab_ref: Path,
    tool_root: Path,
    locked_iteration_id: str,
    mixed_iteration_id: str,
) -> None:
    manifest_lock = _object(anchors.get("manifest"), "runtime manifest lock")
    doctor = _object(anchors.get("doctor"), "runtime chiplab doctor")
    runtime = _runtime_anchor_projection(anchors)
    expected = {
        "chiplab_commit": _git_sha(
            manifest_lock.get("chiplab_commit"), "manifest.lock chiplab_commit"
        ),
        "mycpu_reference_commit": _git_sha(
            manifest_lock.get("chiplab_mycpu_gitlink"), "manifest.lock myCPU gitlink"
        ),
        "golden_candidate_commit": _git_sha(
            manifest_lock.get("team_golden_candidate"), "manifest.lock golden candidate"
        ),
        "manifest_sha256": _sha256(
            anchors.get("manifest_sha256"), "current manifest.lock SHA"
        ),
        "golden_files_lock_sha256": _sha256(
            anchors.get("golden_files_sha256"), "current golden allowlist SHA"
        ),
        "doctor_report_sha256": _sha256(
            anchors.get("doctor_sha256"), "current chiplab doctor SHA"
        ),
        "evaluator_sha256": _sha256(
            anchors.get("refactor_sha256"), "current RTL evaluator SHA"
        ),
    }
    for label, overlay, overlay_manifest, smoke in (
        ("locked", locked_overlay, locked_manifest, locked_smoke),
        ("mixed", mixed_overlay, mixed_manifest, mixed_smoke),
    ):
        for key, expected_value in expected.items():
            if overlay_manifest.get(key) != expected_value:
                raise IdentityCompareError(f"{label} manifest is not anchored to current {key}")
        if overlay.get("doctor_report_sha256") != expected["doctor_report_sha256"]:
            raise IdentityCompareError(f"{label} overlay is not bound to the current doctor")
        for key in ("doctor_report_sha256", "evaluator_sha256", "chiplab_commit"):
            if smoke.get(key) != expected[key]:
                raise IdentityCompareError(f"{label} smoke is not anchored to current {key}")
        if overlay_manifest.get("chiplab_reference") != runtime["chiplab_reference"]:
            raise IdentityCompareError(
                f"{label} manifest is not bound to the requested chiplab reference"
            )
        if overlay_manifest.get("tool_fingerprints") != doctor.get("tool_fingerprints"):
            raise IdentityCompareError(
                f"{label} manifest tool fingerprints differ from current doctor"
            )
    if runtime["chiplab_reference"] != str(chiplab_ref.resolve()):
        raise IdentityCompareError("runtime chiplab reference argument changed")
    if mixed_manifest.get("component_replacement", {}).get("source_head") != anchors.get(
        "head_sha"
    ):
        raise IdentityCompareError("mixed replacement source is not current HEAD")
    try:
        for label, iteration_id, diagnostic, report, overlay_manifest, smoke in (
            (
                "locked",
                locked_iteration_id,
                False,
                locked_overlay,
                locked_manifest,
                locked_smoke,
            ),
            (
                "mixed",
                mixed_iteration_id,
                True,
                mixed_overlay,
                mixed_manifest,
                mixed_smoke,
            ),
        ):
            canonical_manifest = _canonical_paths(out_dir, iteration_id)["manifest"].absolute()
            declared_manifest = Path(
                _string(report.get("overlay_manifest"), f"{label} overlay_manifest path")
            ).absolute()
            if declared_manifest != canonical_manifest:
                raise IdentityCompareError(
                    f"{label} overlay report does not name the canonical manifest"
                )
            verified_work, verified_manifest, verified_report, doctor_sha, _ = (
                refactor.verify_overlay_integrity(
                    out_dir=out_dir,
                    iteration_id=iteration_id,
                    tool_root=tool_root,
                    work_root=work_root,
                    diagnostic=diagnostic,
                    doctor_max_age_seconds=86400,
                    post_smoke=True,
                )
            )
            if verified_work != (work_root / iteration_id).resolve():
                raise IdentityCompareError(f"{label} verified worktree path changed")
            if verified_manifest != overlay_manifest or verified_report != report:
                raise IdentityCompareError(
                    f"{label} canonical report differs from the verified work marker"
                )
            if doctor_sha != expected["doctor_report_sha256"]:
                raise IdentityCompareError(f"{label} verifier used a different doctor")
            refactor.verify_dut_source_bindings(
                verified_work, verified_manifest, manifest_lock
            )
            if smoke.get("environment") != refactor.smoke_environment(
                verified_work, tool_root
            ):
                raise IdentityCompareError(
                    f"{label} smoke environment differs from the current locked environment"
                )
    except (OSError, refactor.RefactorError) as error:
        raise IdentityCompareError(f"physical DUT/source binding failed: {error}") from error


def _identity_replacements(
    locked_files: dict[str, dict[str, Any]],
    mixed_manifest: dict[str, Any],
    mixed_files: dict[str, dict[str, Any]],
) -> tuple[bool, str | None, list[dict[str, Any]]]:
    metadata = _object(
        mixed_manifest.get("component_replacement"), "mixed component_replacement"
    )
    _schema(metadata, "mixed component_replacement")
    source_head = _git_sha(metadata.get("source_head"), "mixed replacement source_head")
    source_branch = _string(metadata.get("source_branch"), "mixed replacement source_branch")
    if not source_branch.startswith("refactor/"):
        raise IdentityCompareError("mixed replacement source branch is not a refactor branch")
    if metadata.get("replacement_payload_source") != "committed_git_blobs":
        raise IdentityCompareError("mixed replacement payload is not bound to committed Git blobs")
    porcelain_clean = _boolean(
        metadata.get("worktree_porcelain_clean"), "mixed worktree_porcelain_clean"
    )
    if _boolean(metadata.get("worktree_clean"), "mixed worktree_clean") is not porcelain_clean:
        raise IdentityCompareError("mixed worktree clean fields disagree")
    if not _boolean(metadata.get("worktree_semantic_clean"), "mixed worktree_semantic_clean"):
        raise IdentityCompareError("mixed replacement source is not semantically clean")
    eol_only = _boolean(
        metadata.get("worktree_eol_normalization_only"),
        "mixed worktree_eol_normalization_only",
    )
    raw_status_count = _integer(
        metadata.get("worktree_raw_status_entry_count"),
        "mixed worktree_raw_status_entry_count",
    )
    if eol_only != (not porcelain_clean) or (raw_status_count == 0) != porcelain_clean:
        raise IdentityCompareError("mixed worktree EOL/status metadata is inconsistent")
    if metadata.get("worktree_semantic_diff_policy") != "ignore-cr-at-eol-only":
        raise IdentityCompareError("mixed source used an unapproved semantic diff policy")
    replacements = _list(metadata.get("replacements"), "mixed replacements")
    if not replacements:
        raise IdentityCompareError("mixed component replacement list is empty")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    identity = True
    for index, raw in enumerate(replacements):
        replacement = _object(raw, f"mixed replacements[{index}]")
        target = _string(replacement.get("target"), f"mixed replacements[{index}].target")
        if target in seen:
            raise IdentityCompareError(f"mixed replacement target is duplicated: {target}")
        seen.add(target)
        if target not in locked_files or target not in mixed_files:
            raise IdentityCompareError(f"mixed replacement target is not in the DUT union: {target}")
        base_sha = _sha256(
            replacement.get("base_sha256"), f"mixed replacements[{index}].base_sha256"
        )
        replacement_sha = _sha256(
            replacement.get("replacement_sha256"),
            f"mixed replacements[{index}].replacement_sha256",
        )
        installed_sha = _sha256(
            mixed_files[target].get("sha256"), f"mixed installed SHA for {target}"
        )
        size = _integer(
            replacement.get("size"), f"mixed replacements[{index}].size", minimum=1
        )
        source = _string(replacement.get("source"), f"mixed replacements[{index}].source")
        source_mode = _string(
            replacement.get("source_mode"), f"mixed replacements[{index}].source_mode"
        )
        _git_sha(replacement.get("source_oid"), f"mixed replacements[{index}].source_oid")
        target_identity = (
            base_sha == replacement_sha == installed_sha == locked_files[target].get("sha256")
            and size == mixed_files[target].get("size")
            and mixed_files[target].get("base_mode") == locked_files[target].get("base_mode")
            and source_mode == locked_files[target].get("base_mode")
        )
        identity = identity and target_identity
        result.append(
            {
                "target": target,
                "source": source,
                "base_sha256": base_sha,
                "replacement_sha256": replacement_sha,
                "installed_sha256": installed_sha,
                "identity": target_identity,
            }
        )
    replacement_sources = {
        entry.get("logical_path")
        for entry in _list(mixed_manifest.get("files"), "mixed manifest files")
        if isinstance(entry, dict) and entry.get("source_kind") == "replacement"
    }
    if replacement_sources != seen:
        raise IdentityCompareError(
            "mixed source_kind=replacement set does not match component replacement targets"
        )
    return identity, source_head, result


def compare_identity_overlay(
    *,
    locked_overlay_path: Path,
    locked_manifest_path: Path,
    locked_smoke_path: Path,
    mixed_overlay_path: Path,
    mixed_manifest_path: Path,
    mixed_smoke_path: Path,
    out_dir: Path,
    work_root: Path,
    locked_iteration_id: str,
    mixed_iteration_id: str,
    anchors: dict[str, Any],
) -> dict[str, Any]:
    locked_overlay, locked_overlay_sha = _read_json(
        locked_overlay_path, "locked overlay", root=out_dir
    )
    locked_manifest, locked_manifest_sha = _read_json(
        locked_manifest_path, "locked manifest", root=out_dir
    )
    locked_smoke, locked_smoke_sha = _read_json(
        locked_smoke_path, "locked smoke", root=out_dir
    )
    mixed_overlay, mixed_overlay_sha = _read_json(
        mixed_overlay_path, "mixed overlay", root=out_dir
    )
    mixed_manifest, mixed_manifest_sha = _read_json(
        mixed_manifest_path, "mixed manifest", root=out_dir
    )
    mixed_smoke, mixed_smoke_sha = _read_json(
        mixed_smoke_path, "mixed smoke", root=out_dir
    )

    published_inputs = (
        (
            locked_overlay_path,
            locked_overlay,
            locked_overlay_sha,
            "chiplab-overlay",
            locked_iteration_id,
        ),
        (
            locked_smoke_path,
            locked_smoke,
            locked_smoke_sha,
            "rtl-smoke",
            locked_iteration_id,
        ),
        (
            mixed_overlay_path,
            mixed_overlay,
            mixed_overlay_sha,
            "chiplab-overlay",
            mixed_iteration_id,
        ),
        (
            mixed_smoke_path,
            mixed_smoke,
            mixed_smoke_sha,
            "rtl-smoke",
            mixed_iteration_id,
        ),
    )
    for path, report, report_sha, operation, expected_iteration in published_inputs:
        try:
            refactor.require_report_publication(
                path,
                report,
                report_sha,
                command=operation,
                iteration_id=expected_iteration,
                publication_id=_string(
                    report.get("run_id"), f"{operation} publication id"
                ),
                publisher_sha256=_sha256(
                    report.get("evaluator_sha256"), f"{operation} publisher SHA"
                ),
            )
        except (OSError, refactor.RefactorError) as error:
            raise IdentityCompareError(
                f"published input verification failed for {path}: {error}"
            ) from error

    mismatches: list[str] = []
    _critical_overlay_shape(
        locked_overlay,
        locked_manifest,
        mixed=False,
        expected_iteration_id=locked_iteration_id,
        mismatches=mismatches,
    )
    _critical_overlay_shape(
        mixed_overlay,
        mixed_manifest,
        mixed=True,
        expected_iteration_id=mixed_iteration_id,
        mismatches=mismatches,
    )
    _check_hash_chain(
        "locked",
        locked_overlay,
        locked_overlay_sha,
        locked_manifest,
        locked_manifest_sha,
        locked_smoke,
        mismatches,
    )
    _check_hash_chain(
        "mixed",
        mixed_overlay,
        mixed_overlay_sha,
        mixed_manifest,
        mixed_manifest_sha,
        mixed_smoke,
        mismatches,
    )

    _validate_runtime_bindings(
        locked_overlay=locked_overlay,
        locked_manifest=locked_manifest,
        locked_smoke=locked_smoke,
        mixed_overlay=mixed_overlay,
        mixed_manifest=mixed_manifest,
        mixed_smoke=mixed_smoke,
        anchors=anchors,
        work_root=work_root,
        out_dir=out_dir,
        chiplab_ref=Path(_string(anchors.get("chiplab_reference"), "runtime chiplab reference")),
        tool_root=Path(_string(anchors.get("tool_root"), "runtime tool root")),
        locked_iteration_id=locked_iteration_id,
        mixed_iteration_id=mixed_iteration_id,
    )
    locked_smoke_projection = _validate_smoke_contract(locked_smoke, "locked")
    mixed_smoke_projection = _validate_smoke_contract(mixed_smoke, "mixed")
    _verify_physical_smoke_artifacts(
        locked_smoke,
        label="locked",
        out_dir=out_dir,
        work_root=work_root,
        iteration_id=locked_iteration_id,
    )
    _verify_physical_smoke_artifacts(
        mixed_smoke,
        label="mixed",
        out_dir=out_dir,
        work_root=work_root,
        iteration_id=mixed_iteration_id,
    )

    expected_paths = _list(anchors.get("golden_files"), "runtime golden file allowlist")
    if (
        not expected_paths
        or len(expected_paths) != len(set(expected_paths))
        or any(not isinstance(path, str) or not path for path in expected_paths)
    ):
        raise IdentityCompareError("runtime golden file allowlist is malformed")
    locked_files = _file_projection(locked_manifest, "locked", expected_paths)
    mixed_files = _file_projection(mixed_manifest, "mixed", expected_paths)
    if any(entry["source_kind"] != "golden" for entry in locked_files.values()):
        raise IdentityCompareError("locked manifest contains a non-golden DUT source")
    locked_file_content = {
        path: {key: value for key, value in entry.items() if key != "source_kind"}
        for path, entry in locked_files.items()
    }
    mixed_file_content = {
        path: {key: value for key, value in entry.items() if key != "source_kind"}
        for path, entry in mixed_files.items()
    }
    file_union_equal = locked_file_content == mixed_file_content
    _add_mismatch(mismatches, file_union_equal, "locked and mixed DUT file projections differ")
    identity_replacement, source_head, replacements = _identity_replacements(
        locked_files, mixed_manifest, mixed_files
    )
    _add_mismatch(mismatches, identity_replacement, "mixed replacement is not byte-identical")

    locked_common = _common_manifest_projection(locked_manifest, "locked")
    mixed_common = _common_manifest_projection(mixed_manifest, "mixed")
    _add_mismatch(
        mismatches,
        locked_common == mixed_common,
        "locked and mixed common manifest provenance differs",
    )

    locked_tools = _tool_projection(locked_manifest, "locked")
    mixed_tools = _tool_projection(mixed_manifest, "mixed")
    _add_mismatch(mismatches, locked_tools == mixed_tools, "tool fingerprints differ")
    locked_support = _support_projection(locked_manifest, "locked")
    mixed_support = _support_projection(mixed_manifest, "mixed")
    _add_mismatch(mismatches, locked_support == mixed_support, "support files differ")

    comparison_fields = {
        "case": "locked and mixed smoke cases differ",
        "commands": "smoke command argv differ",
        "counts": "overall gate counts differ",
        "functional_counts": "functional counts differ",
        "compile_counts": "Verilator compile counts differ",
        "parser": "locked and mixed parser observations differ",
        "gate_result": "locked and mixed gate results differ",
        "functional_status": "locked and mixed functional status differs",
        "compile_status": "locked and mixed compile status differs",
        "warning_policy_status": "warning policy status differs",
        "warning_policy_rule": "warning policy rule differs",
        "rtl_static_gate": "rtl-static disclosure differs",
        "environment": "locked runtime environment projection differs",
        "result_file_policy": "functional result-file policy differs",
        "output": "trace/UART evidence differs",
        "warnings": "Verilator warning counts differ",
    }
    for key, message in comparison_fields.items():
        _add_mismatch(
            mismatches,
            locked_smoke_projection[key] == mixed_smoke_projection[key],
            message,
        )

    locked_elf = _artifact_by_suffix(locked_smoke, "/main.elf", "locked")
    mixed_elf = _artifact_by_suffix(mixed_smoke, "/main.elf", "mixed")
    locked_rom = _artifact_by_suffix(locked_smoke, "/rom.vlog", "locked")
    mixed_rom = _artifact_by_suffix(mixed_smoke, "/rom.vlog", "mixed")
    _add_mismatch(mismatches, locked_elf == mixed_elf, "main.elf evidence differs")
    _add_mismatch(mismatches, locked_rom == mixed_rom, "rom.vlog evidence differs")

    locked_output = locked_smoke_projection["output"]
    mixed_output = mixed_smoke_projection["output"]
    locked_warnings = locked_smoke_projection["warnings"]
    mixed_warnings = mixed_smoke_projection["warnings"]
    parser_equal = locked_smoke_projection["parser"] == mixed_smoke_projection["parser"]
    warning_counts_equal = locked_warnings == mixed_warnings
    runtime = _runtime_anchor_projection(anchors)
    status = "pass" if not mismatches else "fail"
    return {
        "schema_version": 1,
        "command": "identity-compare",
        "generated_at": refactor.now_iso(),
        "status": status,
        "gate_eligible": False,
        "claim_scope": CLAIM_SCOPE,
        "excluded_fields": EXCLUDED_FIELDS,
        "locked_iteration": locked_overlay.get("iteration_id"),
        "mixed_iteration": mixed_overlay.get("iteration_id"),
        "source_head": source_head,
        "runtime": runtime,
        "physical_evidence_verified": True,
        "input_snapshot_verified": False,
        "inputs": {
            "locked_overlay": {"path": str(locked_overlay_path), "sha256": locked_overlay_sha},
            "locked_manifest": {"path": str(locked_manifest_path), "sha256": locked_manifest_sha},
            "locked_smoke": {"path": str(locked_smoke_path), "sha256": locked_smoke_sha},
            "mixed_overlay": {"path": str(mixed_overlay_path), "sha256": mixed_overlay_sha},
            "mixed_manifest": {"path": str(mixed_manifest_path), "sha256": mixed_manifest_sha},
            "mixed_smoke": {"path": str(mixed_smoke_path), "sha256": mixed_smoke_sha},
        },
        "checks": {
            "identity_replacement": identity_replacement,
            "rtl_file_union_equal": file_union_equal,
            "parser_equal": parser_equal,
            "trace_uart_equal": locked_output == mixed_output,
            "rom_equal": locked_rom == mixed_rom,
            "elf_equal": locked_elf == mixed_elf,
            "warning_counts_equal": warning_counts_equal,
            "post_run_verified": (
                _object(
                    locked_smoke.get("post_run_dut_verification"),
                    "locked post-run verification",
                ).get("status")
                == "pass"
                and _object(
                    mixed_smoke.get("post_run_dut_verification"),
                    "mixed post-run verification",
                ).get("status")
                == "pass"
            ),
            "runtime_provenance_verified": True,
            "physical_evidence_verified": True,
        },
        "replacements": replacements,
        "observed": {
            "case": locked_smoke_projection["case"],
            "locked_gate_result": locked_smoke_projection["gate_result"],
            "mixed_observed_result": mixed_smoke_projection["gate_result"],
            "functional_status": locked_smoke_projection["functional_status"],
            "parser": locked_smoke_projection["parser"],
            "warning_counts": locked_warnings,
        },
        "mismatches": mismatches,
    }


def _verify_input_snapshot(report: dict[str, Any], out_dir: Path) -> None:
    inputs = _object(report.get("inputs"), "identity comparison inputs")
    expected_names = {
        "locked_overlay",
        "locked_manifest",
        "locked_smoke",
        "mixed_overlay",
        "mixed_manifest",
        "mixed_smoke",
    }
    if set(inputs) != expected_names:
        raise IdentityCompareError("identity comparison input snapshot is incomplete")
    for name in sorted(expected_names):
        entry = _object(inputs.get(name), f"identity comparison input {name}")
        if set(entry) != {"path", "sha256"}:
            raise IdentityCompareError(f"identity comparison input {name} has an invalid schema")
        path = Path(_string(entry.get("path"), f"identity comparison input {name} path"))
        expected_sha = _sha256(
            entry.get("sha256"), f"identity comparison input {name} sha256"
        )
        _, current_sha = _read_json(path, f"identity comparison input {name}", root=out_dir)
        if current_sha != expected_sha:
            raise IdentityCompareError(
                f"identity comparison input changed before publication: {name}"
            )


def _acquire_comparison_locks(
    out_dir: Path,
    work_root: Path,
    iteration_ids: list[str],
    run_id: str,
) -> list[refactor.ValidationLock]:
    locks: list[refactor.ValidationLock] = []
    try:
        for root in (out_dir, work_root):
            for iteration_id in sorted(iteration_ids):
                locks.append(
                    refactor.acquire_iteration_lock(
                        root, iteration_id, "identity-compare", run_id
                    )
                )
    except BaseException as acquisition_error:
        try:
            refactor.release_validation_locks(locks)
        except BaseException as release_error:
            if not isinstance(acquisition_error, Exception):
                raise acquisition_error
            raise IdentityCompareError(
                f"identity comparison lock acquisition rollback failed: {release_error}"
            ) from acquisition_error
        raise
    return locks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--chiplab-ref", required=True)
    parser.add_argument("--tool-root", required=True)
    parser.add_argument("--locked-iteration-id", required=True)
    parser.add_argument("--mixed-iteration-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    locks: list[refactor.ValidationLock] = []
    output: Path | None = None
    output_sha256: str | None = None
    report: dict[str, Any] | None = None
    publication_armed = False
    release_error: BaseException | None = None
    result_code = 2
    try:
        out_dir = refactor.checked_out_dir(args.out_dir)
        work_requested = Path(args.work_root).absolute()
        refactor.reject_link_or_reparse_path(work_requested, "CHIPLAB_WORK_ROOT")
        work_root = work_requested.resolve()
        chiplab_ref = Path(args.chiplab_ref).resolve()
        tool_root = Path(args.tool_root).resolve()
        refactor.require_nonoverlapping_validation_roots(out_dir, work_root)
        locked = _canonical_paths(out_dir, args.locked_iteration_id)
        mixed = _canonical_paths(out_dir, args.mixed_iteration_id)
        output = (
            out_dir
            / "reports"
            / "iterations"
            / args.mixed_iteration_id
            / "identity-comparison.json"
        )
        if args.locked_iteration_id == args.mixed_iteration_id:
            raise IdentityCompareError("locked and mixed iteration ids must be distinct")
        run_id = f"identity-compare-{time.time_ns()}-{os.getpid()}"
        locks = _acquire_comparison_locks(
            out_dir,
            work_root,
            [args.locked_iteration_id, args.mixed_iteration_id],
            run_id,
        )
        refactor.remove_stale_report_publication(output)
        publication_armed = True
        anchors = _runtime_anchors(out_dir, chiplab_ref, tool_root)
        report = compare_identity_overlay(
            locked_overlay_path=locked["overlay"],
            locked_manifest_path=locked["manifest"],
            locked_smoke_path=locked["smoke"],
            mixed_overlay_path=mixed["overlay"],
            mixed_manifest_path=mixed["manifest"],
            mixed_smoke_path=mixed["smoke"],
            out_dir=out_dir,
            work_root=work_root,
            locked_iteration_id=args.locked_iteration_id,
            mixed_iteration_id=args.mixed_iteration_id,
            anchors=anchors,
        )
        final_anchors = _runtime_anchors(out_dir, chiplab_ref, tool_root)
        if (
            _runtime_anchor_projection(final_anchors)
            != _runtime_anchor_projection(anchors)
            or final_anchors.get("manifest") != anchors.get("manifest")
            or final_anchors.get("golden_files") != anchors.get("golden_files")
            or final_anchors.get("doctor") != anchors.get("doctor")
        ):
            raise IdentityCompareError("runtime provenance changed during comparison")
        _verify_input_snapshot(report, out_dir)
        report["input_snapshot_verified"] = True
        _object(report.get("checks"), "identity comparison checks")[
            "input_snapshot_verified"
        ] = True
        report["run_id"] = run_id
        refactor.write_json(output, report)
        output_sha256 = refactor.json_sha256(report)
        if refactor.sha256_file(output) != output_sha256:
            raise IdentityCompareError(
                "identity comparison output changed during publication"
            )
        runtime = _object(report.get("runtime"), "identity comparison runtime")
        refactor.write_publication_marker(
            output,
            report,
            command="identity-compare",
            iteration_id=args.mixed_iteration_id,
            publication_id=run_id,
            publisher_sha256=_sha256(
                runtime.get("comparator_sha256"), "identity comparator publisher SHA"
            ),
        )
        result_code = 0 if report["status"] == "pass" else 1
    except (OSError, IdentityCompareError, refactor.RefactorError) as error:
        print(f"identity-compare input error: {error}", file=sys.stderr)
        result_code = 2
        if publication_armed and output is not None:
            try:
                refactor.remove_stale_report_publication(output)
            except (OSError, refactor.RefactorError) as cleanup_error:
                print(
                    f"identity-compare locked cleanup error: {cleanup_error}",
                    file=sys.stderr,
                )
    finally:
        try:
            refactor.release_validation_locks(locks)
        except BaseException as error:
            release_error = error
            print(f"identity-compare lock release error: {error}", file=sys.stderr)
            result_code = 2
    if result_code in {0, 1} and report is not None and output is not None:
        try:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        except Exception as error:
            print(f"identity-compare output error: {error}", file=sys.stderr)
            result_code = 2
    if release_error is not None and not isinstance(release_error, Exception):
        raise release_error
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
