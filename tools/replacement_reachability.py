#!/usr/bin/env python3
"""Check that the aggregate replacement set follows the locked Verilog closure.

This is a structural check only.  It does not prove behavior or that a mixed
chiplab run is gate-eligible.  It intentionally reports deferred reachable
implementation files separately from the replacements selected by an
iteration.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


MODULE_BLOCK_RE = re.compile(
    r"\bmodule\s+([A-Za-z_$][\w$]*)\b(.*?)\bendmodule\b", re.DOTALL
)


def git_show(repo: Path, commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise RuntimeError(f"git show failed for {commit}:{path}: {result.stderr.strip()}")
    return result.stdout


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def preprocess(text: str, defined_macros: set[str]) -> str:
    output: list[str] = []
    stack: list[tuple[bool, bool]] = []
    active = True
    directive = re.compile(r"`(ifdef|ifndef|else|endif)\b\s*([A-Za-z_$][\w$]*)?")
    for line in text.splitlines(keepends=True):
        cursor = 0
        for match in directive.finditer(line):
            if active:
                output.append(line[cursor : match.start()])
            kind, macro = match.groups()
            if kind in {"ifdef", "ifndef"}:
                condition = macro in defined_macros
                if kind == "ifndef":
                    condition = not condition
                stack.append((active, condition))
                active = active and condition
            elif kind == "else":
                if not stack:
                    raise ValueError("unmatched `else in golden Verilog")
                parent, condition = stack[-1]
                stack[-1] = (parent, not condition)
                active = parent and not condition
            else:
                if not stack:
                    raise ValueError("unmatched `endif in golden Verilog")
                parent, _ = stack.pop()
                active = parent
            cursor = match.end()
        if active:
            output.append(line[cursor:])
    if stack:
        raise ValueError("unterminated conditional in golden Verilog")
    return "".join(output)


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda match: "\n" * match.group(0).count("\n"), text, flags=re.DOTALL)
    return re.sub(r"//[^\r\n]*", "", text)


def build_graph(
    repo: Path, commit: str, paths: list[str], defined_macros: set[str]
) -> tuple[dict[str, str], dict[str, set[str]]]:
    module_file: dict[str, str] = {}
    module_body: dict[str, str] = {}
    for path in paths:
        text = strip_comments(preprocess(git_show(repo, commit, path), defined_macros))
        for match in MODULE_BLOCK_RE.finditer(text):
            module, body = match.groups()
            if module in module_file:
                raise ValueError(f"duplicate module definition in golden closure: {module}")
            module_file[module] = path
            module_body[module] = body
    known = set(module_file)
    graph: dict[str, set[str]] = {module: set() for module in known}
    for module, body in module_body.items():
        for child in known:
            instance_re = re.compile(
                rf"(?m)^[ \t]*{re.escape(child)}\b[ \t]*"
                rf"(?:#\s*\([^;]*?\)[ \t]*)?([A-Za-z_$][\w$]*)\s*\("
            )
            if instance_re.search(body):
                graph[module].add(child)
    return module_file, graph


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--golden-commit")
    parser.add_argument("--manifest", default="reference/manifest.lock")
    parser.add_argument("--golden-files", default="reference/golden-rtl-files.lock")
    parser.add_argument("--spec", default="reference/component-replacements/active-reachable.json")
    parser.add_argument("--metadata", default="reference/component-replacements/active-reachable.meta.json")
    parser.add_argument("--out-dir", default="build/replacement-reachability")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    golden_commit = args.golden_commit
    if not golden_commit:
        lock = (repo / args.manifest).read_text(encoding="utf-8").splitlines()
        values = {
            line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip()
            for line in lock
            if "=" in line and not line.lstrip().startswith("#")
        }
        golden_commit = values.get("team_golden_candidate")
    if not golden_commit:
        raise ValueError("team_golden_candidate is missing from manifest.lock")
    golden_files = [
        line.strip()
        for line in (repo / args.golden_files).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and line.strip().endswith(".v")
    ]
    spec = read_json(repo / args.spec)
    metadata = read_json(repo / args.metadata)
    replacements = spec.get("replacements")
    selected = [item.get("target") for item in replacements] if isinstance(replacements, list) else []
    selected_set = set(selected)
    if len(selected) != len(selected_set):
        raise ValueError("replacement spec contains duplicate targets")
    expected = metadata.get("selected_replacements")
    if not isinstance(expected, list) or set(expected) != selected_set:
        raise ValueError("metadata selected_replacements differs from aggregate replacement spec")

    defined_macros = metadata.get("defined_macros", [])
    undefined_macros = metadata.get("undefined_macros", [])
    if not isinstance(defined_macros, list) or not all(isinstance(item, str) for item in defined_macros):
        raise ValueError("defined_macros must be a string list")
    if not isinstance(undefined_macros, list) or not all(isinstance(item, str) for item in undefined_macros):
        raise ValueError("undefined_macros must be a string list")
    if set(defined_macros) & set(undefined_macros):
        raise ValueError("macro cannot be both defined and undefined")
    module_file, graph = build_graph(repo, golden_commit, golden_files, set(defined_macros))
    root = str(metadata.get("root_module", ""))
    if root not in graph:
        raise ValueError(f"root module is not present in golden files: {root}")
    reachable: set[str] = set()
    pending = [root]
    while pending:
        module = pending.pop()
        if module in reachable:
            continue
        reachable.add(module)
        pending.extend(sorted(graph.get(module, set()) - reachable))

    target_modules: dict[str, str] = {}
    for target in selected:
        if not isinstance(target, str) or target not in golden_files:
            raise ValueError(f"selected target is not in golden file lock: {target!r}")
        basename = Path(target).stem
        module = "core_top" if basename == "mycpu_top" else basename
        target_modules[target] = module
    missing = sorted(target for target, module in target_modules.items() if module not in reachable)
    forbidden = sorted(set(selected) & {"rtl/alu.v", "rtl/tlb_entry.v"})
    if missing:
        raise ValueError(f"selected replacement is unreachable: {missing}")
    if forbidden:
        raise ValueError(f"deferred implementation must not be duplicated in aggregate spec: {forbidden}")

    deferred = metadata.get("deferred_reachable", {})
    deferred_paths = sorted(deferred) if isinstance(deferred, dict) else []
    deferred_modules = {
        path: ("core_top" if Path(path).stem == "mycpu_top" else Path(path).stem)
        for path in deferred_paths
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "pass",
        "root_module": root,
        "profile": metadata.get("profile"),
        "defined_macros": defined_macros,
        "undefined_macros": undefined_macros,
        "golden_commit": golden_commit,
        "golden_file_count": len(golden_files),
        "reachable_modules": sorted(reachable),
        "selected_replacements": selected,
        "selected_target_modules": target_modules,
        "deferred_reachable": {
            path: {"module": module, "reachable": module in reachable, "reason": deferred[path]}
            for path, module in deferred_modules.items()
        },
        "selected_count": len(selected),
        "deferred_count": len(deferred_modules),
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "reachability.json").write_text(
        json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"replacement-reachability: ERROR: {error}")
        raise SystemExit(2)
