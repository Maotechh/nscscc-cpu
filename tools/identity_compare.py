#!/usr/bin/env python3
"""Compare a locked chiplab smoke run with an identity mixed overlay run."""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import re
import sys
import tempfile
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
EXCLUDED_FIELDS = [
    "Vsimu_top__ALL.a",
    "simulator output binary",
    "compile and simulation log bytes",
    "cwd and absolute artifact paths",
    "run_id, timestamps, and elapsed time",
    "whole manifest/report hashes and cross-run selection hashes",
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


def _read_json(path: Path, context: str) -> tuple[dict[str, Any], str]:
    try:
        value, digest = refactor.read_json_file_with_sha256(path)
    except (OSError, UnicodeError, refactor.RefactorError) as error:
        raise IdentityCompareError(f"cannot read {context} {path}: {error}") from error
    return _object(value, context), digest


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


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
    report: dict[str, Any], manifest: dict[str, Any], *, mixed: bool, mismatches: list[str]
) -> None:
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
    label = "mixed" if mixed else "locked"
    for key, expected_value in expected.items():
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


def _check_hash_chain(
    label: str,
    overlay: dict[str, Any],
    overlay_sha: str,
    manifest: dict[str, Any],
    manifest_sha: str,
    smoke: dict[str, Any],
    mismatches: list[str],
) -> None:
    for key in (
        "iteration_id",
        "dut_source",
        "provenance_mode",
        "gate_kind",
        "candidate_locked",
        "base_candidate_locked",
        "baseline_exact",
        "gate_eligible",
        "golden_candidate_commit",
        "component_replacement",
    ):
        _add_mismatch(
            mismatches,
            smoke.get(key) == overlay.get(key),
            f"{label} smoke/overlay disagree on {key}",
        )
    post_run = _object(smoke.get("post_run_dut_verification"), f"{label} post-run verification")
    _add_mismatch(
        mismatches,
        overlay.get("overlay_manifest_sha256") == manifest_sha,
        f"{label} overlay report is not bound to its manifest file",
    )
    _add_mismatch(
        mismatches,
        smoke.get("overlay_report_sha256") == overlay_sha,
        f"{label} smoke is not bound to its overlay report file",
    )
    _add_mismatch(
        mismatches,
        post_run.get("overlay_report_sha256") == overlay_sha,
        f"{label} post-run verification is not bound to its overlay report file",
    )
    _add_mismatch(
        mismatches,
        post_run.get("overlay_manifest_sha256") == manifest_sha,
        f"{label} post-run verification is not bound to its overlay manifest file",
    )
    _add_mismatch(
        mismatches,
        post_run.get("status") == "pass",
        f"{label} post-run DUT verification did not pass",
    )
    selection = manifest.get("selection_sha256")
    _add_mismatch(
        mismatches,
        isinstance(selection, str)
        and overlay.get("selection_sha256") == selection
        and smoke.get("selection_sha256") == selection
        and post_run.get("selection_sha256") == selection,
        f"{label} selection SHA chain is inconsistent",
    )


def _file_projection(manifest: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    projection: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_list(manifest.get("files"), f"{label} manifest files")):
        entry = _object(raw, f"{label} manifest files[{index}]")
        logical_path = _string(entry.get("logical_path"), f"{label} logical_path")
        if logical_path in projection:
            raise IdentityCompareError(f"{label} manifest repeats logical_path {logical_path}")
        projection[logical_path] = {
            "path": entry.get("path"),
            "overlay_path": entry.get("overlay_path"),
            "sha256": entry.get("sha256"),
            "overlay_sha256": entry.get("overlay_sha256"),
            "size": entry.get("size"),
            "base_mode": entry.get("base_mode"),
        }
    if not projection:
        raise IdentityCompareError(f"{label} manifest has no DUT files")
    return projection


def _support_projection(manifest: dict[str, Any], label: str) -> list[dict[str, Any]]:
    support: list[dict[str, Any]] = []
    for index, raw in enumerate(
        _list(manifest.get("support_files"), f"{label} manifest support_files")
    ):
        entry = _object(raw, f"{label} support_files[{index}]")
        support.append(
            {
                "path": entry.get("path"),
                "source": entry.get("source"),
                "sha256": entry.get("sha256"),
                "size": entry.get("size"),
            }
        )
    if not support:
        raise IdentityCompareError(f"{label} manifest has no support-file bindings")
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
                "manifest_key": entry.get("manifest_key"),
                "actual_sha256": actual,
                "expected_sha256": expected,
                "size": entry.get("size"),
            }
        )
    if not tools:
        raise IdentityCompareError(f"{label} manifest has no tool fingerprints")
    return sorted(tools, key=lambda item: item["name"])


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
    return {"sha256": artifact.get("sha256"), "size": artifact.get("size")}


def _output_evidence_projection(smoke: dict[str, Any], label: str) -> dict[str, Any]:
    output = _object(smoke.get("output_evidence"), f"{label} output_evidence")
    projection: dict[str, Any] = {}
    for role in ("simu_trace", "uart", "uart_real"):
        entry = _object(output.get(role), f"{label} output_evidence.{role}")
        projection[role] = {
            "exists": entry.get("exists"),
            "fresh": entry.get("fresh"),
            "oracle_role": entry.get("oracle_role"),
            "sha256": entry.get("sha256"),
            "size": entry.get("size"),
        }
    return projection


def _command_projection(smoke: dict[str, Any], label: str) -> list[list[str]]:
    commands: list[list[str]] = []
    for index, raw in enumerate(_list(smoke.get("commands"), f"{label} smoke commands")):
        command = _object(raw, f"{label} smoke commands[{index}]")
        argv = command.get("command")
        if not isinstance(argv, list) or not argv or any(
            not isinstance(item, str) or not item for item in argv
        ):
            raise IdentityCompareError(f"{label} smoke command[{index}] has invalid argv")
        if command.get("exit_code") != 0 or command.get("timed_out") is not False:
            raise IdentityCompareError(f"{label} smoke command[{index}] failed or timed out")
        commands.append(argv)
    return commands


def _warning_projection(smoke: dict[str, Any], label: str) -> dict[str, Any]:
    by_scope: collections.Counter[str] = collections.Counter()
    by_scope_category: collections.Counter[str] = collections.Counter()
    for index, raw in enumerate(
        _list(smoke.get("verilator_warnings"), f"{label} verilator_warnings")
    ):
        warning = _object(raw, f"{label} verilator_warnings[{index}]")
        scope = _string(warning.get("scope"), f"{label} warning scope")
        category = _string(warning.get("category"), f"{label} warning category")
        by_scope[scope] += 1
        by_scope_category[f"{scope}:{category}"] += 1
    return {
        "total": sum(by_scope.values()),
        "by_scope": dict(sorted(by_scope.items())),
        "by_scope_category": dict(sorted(by_scope_category.items())),
    }


def _identity_replacements(
    locked_files: dict[str, dict[str, Any]],
    mixed_manifest: dict[str, Any],
    mixed_files: dict[str, dict[str, Any]],
) -> tuple[bool, str | None, list[dict[str, Any]]]:
    metadata = _object(
        mixed_manifest.get("component_replacement"), "mixed component_replacement"
    )
    source_head = _string(metadata.get("source_head"), "mixed replacement source_head")
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
        base_sha = replacement.get("base_sha256")
        replacement_sha = replacement.get("replacement_sha256")
        installed_sha = mixed_files[target].get("sha256")
        target_identity = (
            base_sha == replacement_sha == installed_sha == locked_files[target].get("sha256")
            and replacement.get("size") == mixed_files[target].get("size")
            and mixed_files[target].get("base_mode") == locked_files[target].get("base_mode")
        )
        identity = identity and target_identity
        result.append(
            {
                "target": target,
                "source": replacement.get("source"),
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
) -> dict[str, Any]:
    locked_overlay, locked_overlay_sha = _read_json(locked_overlay_path, "locked overlay")
    locked_manifest, locked_manifest_sha = _read_json(locked_manifest_path, "locked manifest")
    locked_smoke, locked_smoke_sha = _read_json(locked_smoke_path, "locked smoke")
    mixed_overlay, mixed_overlay_sha = _read_json(mixed_overlay_path, "mixed overlay")
    mixed_manifest, mixed_manifest_sha = _read_json(mixed_manifest_path, "mixed manifest")
    mixed_smoke, mixed_smoke_sha = _read_json(mixed_smoke_path, "mixed smoke")

    mismatches: list[str] = []
    _critical_overlay_shape(locked_overlay, locked_manifest, mixed=False, mismatches=mismatches)
    _critical_overlay_shape(mixed_overlay, mixed_manifest, mixed=True, mismatches=mismatches)
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

    locked_files = _file_projection(locked_manifest, "locked")
    mixed_files = _file_projection(mixed_manifest, "mixed")
    file_union_equal = locked_files == mixed_files
    _add_mismatch(mismatches, file_union_equal, "locked and mixed DUT file projections differ")
    identity_replacement, source_head, replacements = _identity_replacements(
        locked_files, mixed_manifest, mixed_files
    )
    _add_mismatch(mismatches, identity_replacement, "mixed replacement is not byte-identical")

    for key in (
        "chiplab_commit",
        "chiplab_tree",
        "mycpu_reference_commit",
        "golden_candidate_commit",
        "golden_files_lock_sha256",
        "doctor_report_sha256",
        "evaluator_sha256",
        "official_workspace_fingerprint",
        "tool_links",
    ):
        _add_mismatch(
            mismatches,
            locked_manifest.get(key) == mixed_manifest.get(key),
            f"locked and mixed manifests differ on {key}",
        )

    locked_tools = _tool_projection(locked_manifest, "locked")
    mixed_tools = _tool_projection(mixed_manifest, "mixed")
    _add_mismatch(mismatches, locked_tools == mixed_tools, "tool fingerprints differ")
    locked_support = _support_projection(locked_manifest, "locked")
    mixed_support = _support_projection(mixed_manifest, "mixed")
    _add_mismatch(mismatches, locked_support == mixed_support, "support files differ")

    locked_commands = _command_projection(locked_smoke, "locked")
    mixed_commands = _command_projection(mixed_smoke, "mixed")
    _add_mismatch(mismatches, locked_commands == mixed_commands, "smoke command argv differ")
    for label, smoke in (("locked", locked_smoke), ("mixed", mixed_smoke)):
        counts = _object(smoke.get("counts"), f"{label} counts")
        if counts.get("skipped") != 0:
            raise IdentityCompareError(f"{label} smoke contains skipped work")
        _add_mismatch(
            mismatches,
            smoke.get("requested_case") == smoke.get("actual_case"),
            f"{label} requested and actual smoke cases differ",
        )
    _add_mismatch(
        mismatches,
        locked_smoke.get("actual_case") == mixed_smoke.get("actual_case"),
        "locked and mixed smoke cases differ",
    )

    locked_elf = _artifact_by_suffix(locked_smoke, "/main.elf", "locked")
    mixed_elf = _artifact_by_suffix(mixed_smoke, "/main.elf", "mixed")
    locked_rom = _artifact_by_suffix(locked_smoke, "/rom.vlog", "locked")
    mixed_rom = _artifact_by_suffix(mixed_smoke, "/rom.vlog", "mixed")
    _add_mismatch(mismatches, locked_elf == mixed_elf, "main.elf evidence differs")
    _add_mismatch(mismatches, locked_rom == mixed_rom, "rom.vlog evidence differs")

    locked_output = _output_evidence_projection(locked_smoke, "locked")
    mixed_output = _output_evidence_projection(mixed_smoke, "mixed")
    _add_mismatch(mismatches, locked_output == mixed_output, "trace/UART evidence differs")
    locked_warnings = _warning_projection(locked_smoke, "locked")
    mixed_warnings = _warning_projection(mixed_smoke, "mixed")
    _add_mismatch(mismatches, locked_warnings == mixed_warnings, "Verilator warning counts differ")
    for key in (
        "parser",
        "gate_result",
        "functional_status",
        "functional_counts",
        "verilator_compile_counts",
    ):
        _add_mismatch(
            mismatches,
            locked_smoke.get(key) == mixed_smoke.get(key),
            f"locked and mixed smoke reports differ on {key}",
        )

    parser_equal = locked_smoke.get("parser") == mixed_smoke.get("parser")
    warning_counts_equal = locked_warnings == mixed_warnings
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
                locked_smoke.get("post_run_dut_verification", {}).get("status") == "pass"
                and mixed_smoke.get("post_run_dut_verification", {}).get("status") == "pass"
            ),
        },
        "replacements": replacements,
        "observed": {
            "case": locked_smoke.get("actual_case"),
            "locked_gate_result": locked_smoke.get("gate_result"),
            "mixed_observed_result": mixed_smoke.get("gate_result"),
            "functional_status": locked_smoke.get("functional_status"),
            "parser": locked_smoke.get("parser"),
            "warning_counts": locked_warnings,
        },
        "mismatches": mismatches,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--locked-iteration-id", required=True)
    parser.add_argument("--mixed-iteration-id", required=True)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    try:
        locked = _canonical_paths(out_dir, args.locked_iteration_id)
        mixed = _canonical_paths(out_dir, args.mixed_iteration_id)
    except IdentityCompareError as error:
        print(f"identity-compare input error: {error}", file=sys.stderr)
        return 2
    output = (
        Path(args.output).resolve()
        if args.output
        else (
            out_dir
            / "reports"
            / "iterations"
            / args.mixed_iteration_id
            / "identity-comparison.json"
        ).resolve()
    )
    try:
        output.relative_to(out_dir)
    except ValueError:
        print("identity-compare output must remain inside OUT_DIR", file=sys.stderr)
        return 2
    input_paths = {path.resolve() for path in (*locked.values(), *mixed.values())}
    if output in input_paths:
        print("identity-compare output must not replace an input report", file=sys.stderr)
        return 2
    try:
        output.unlink(missing_ok=True)
    except OSError as error:
        print(f"identity-compare cannot remove stale output: {error}", file=sys.stderr)
        return 2
    try:
        report = compare_identity_overlay(
            locked_overlay_path=locked["overlay"],
            locked_manifest_path=locked["manifest"],
            locked_smoke_path=locked["smoke"],
            mixed_overlay_path=mixed["overlay"],
            mixed_manifest_path=mixed["manifest"],
            mixed_smoke_path=mixed["smoke"],
        )
    except IdentityCompareError as error:
        print(f"identity-compare input error: {error}", file=sys.stderr)
        return 2
    _atomic_write_json(output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
