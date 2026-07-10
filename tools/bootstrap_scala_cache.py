#!/usr/bin/env python3
"""Populate a new fixed Scala cache and emit its deterministic dependency lock."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile

from tools import scala_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--spinal-dir", type=Path, required=True)
    parser.add_argument("--tool-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--lock-out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    if os.name != "posix":
        raise SystemExit("bootstrap_scala_cache.py must run in WSL/Linux")

    manifest_path = args.manifest.resolve()
    spinal_dir = args.spinal_dir.resolve()
    tool_root = args.tool_root.resolve()
    cache_root = args.cache_root.resolve()
    lock_out = args.lock_out.resolve()
    if cache_root.exists():
        raise SystemExit(f"refusing to reuse or delete an existing cache root: {cache_root}")
    cache_root.mkdir(parents=True)

    lock = scala_gate.parse_lock(manifest_path)
    sbt = scala_gate.resolve_executable(
        str(tool_root / f"sbt-{lock['sbt']}" / "bin" / "sbt")
    )
    java = scala_gate.java_binary(None)
    verilator = scala_gate.resolve_executable("verilator")
    sbt_launch_jar = sbt.parent / "sbt-launch.jar"
    if scala_gate.sha256(sbt_launch_jar) != lock["sbt_launch_jar_sha256"]:
        raise SystemExit("SBT launch JAR differs from manifest.lock")

    with tempfile.TemporaryDirectory(prefix="nscscc-scala-cache-bootstrap-") as temporary:
        workspace_root = Path(temporary) / "workspace"
        build_spinal, _ = scala_gate.copy_source_snapshot(
            spinal_dir, manifest_path, workspace_root
        )
        environment = scala_gate.clean_environment(
            [java.parent, verilator.parent, sbt.parent],
            {
                "JAVA_HOME": str(java.parent.parent),
                "SPINAL_SIM_WORKSPACE": str(workspace_root / "sim-workspace"),
                "COURSIER_CACHE": str(cache_root / "coursier" / "v1"),
            },
            home=workspace_root / "home",
        )
        common = [
            str(java),
            f"-Dsbt.global.base={workspace_root / 'sbt-global'}",
            f"-Dsbt.boot.directory={cache_root / 'sbt-boot'}",
            f"-Dsbt.ivy.home={cache_root / 'ivy2'}",
            "-Dsbt.supershell=false",
            "-Dsbt.log.noformat=true",
            "-jar",
            str(sbt_launch_jar),
        ]
        for task in ("clean", *(item[1] for item in scala_gate.TASKS)):
            result = scala_gate.run_capture(
                [*common, task], build_spinal, environment, args.timeout
            )
            print(f"[{result.returncode}] {task}")
            if result.returncode != 0:
                print("\n".join(result.stdout.splitlines()[-40:]))
                raise SystemExit(f"Scala cache bootstrap task failed: {task}")

    scala_gate.write_json(lock_out, scala_gate.dependency_cache_manifest(cache_root))
    print(f"Scala dependency lock: {lock_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
