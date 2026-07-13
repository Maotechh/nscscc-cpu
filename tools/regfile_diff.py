from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_bytes(*arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--verilator", default="verilator")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    contract = json.loads((ROOT / "reference/component-contracts/regfile.json").read_text("utf-8"))
    golden = git_bytes("cat-file", "blob", contract["golden_blob_sha1"])
    if len(golden) != contract["golden_size"] or hashlib.sha256(golden).hexdigest() != contract["golden_sha256"]:
        raise SystemExit("locked golden regfile blob does not match contract")

    candidate_files = [args.candidate_dir / "regfile.v"]
    missing = [str(path) for path in candidate_files if not path.is_file()]
    if missing:
        raise SystemExit(f"missing generated candidate files: {missing}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="openla500-regfile-diff-") as temporary:
        workspace = Path(temporary)
        renamed, count = re.subn(rb"\bmodule\s+regfile\s*\(", b"module regfile_golden(", golden, count=1)
        if count != 1:
            raise SystemExit("golden module rename did not match exactly once")
        golden_path = workspace / "regfile_golden.v"
        golden_path.write_bytes(b"`timescale 1ns/1ps\n" + renamed)
        executable = workspace / "regfile_diff"
        command = [
            args.verilator,
            "--binary",
            "--timing",
            "-Wall",
            "-DDIFFTEST_EN",
            "--top-module",
            "regfile_diff_tb",
            "-o",
            str(executable),
            str(ROOT / "tests/regfile_diff_tb.sv"),
            str(golden_path),
            *(str(path.resolve()) for path in candidate_files),
        ]
        compile_result = subprocess.run(command, text=True, capture_output=True, timeout=args.timeout)
        run_result = None
        if compile_result.returncode == 0:
            run_result = subprocess.run(
                [str(executable)], text=True, capture_output=True, timeout=args.timeout
            )

    passed = (
        compile_result.returncode == 0
        and run_result is not None
        and run_result.returncode == 0
        and "REGFILE_DIFF_PASS vectors=4096" in run_result.stdout
    )
    report = {
        "schema_version": 1,
        "gate": "regfile-cycle-diff",
        "status": "pass" if passed else "fail",
        "golden_blob_sha1": contract["golden_blob_sha1"],
        "golden_sha256": contract["golden_sha256"],
        "candidate": [
            {"path": str(path), "sha256": sha256(path), "size": path.stat().st_size}
            for path in candidate_files
        ],
        "vectors": 4096 if passed else 0,
        "compile_returncode": compile_result.returncode,
        "run_returncode": None if run_result is None else run_result.returncode,
        "compile_tail": (compile_result.stdout + compile_result.stderr)[-4000:],
        "run_tail": None if run_result is None else (run_result.stdout + run_result.stderr)[-4000:],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    (args.out_dir / "regfile-diff.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
