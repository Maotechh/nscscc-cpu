# 20260715-0205 ECHO bootstrap and local environment

## 状态

本 iteration 记录 ECHO 在重启后的同步、工作区边界和 local profile 诊断。它不声明
official baseline、整机功能、locked toolchain 或 release 通过。

- CPU branch: `refactor/ECHO`
- CPU head after rebase: `923eb73b20507234d5b109fec8b82ca3850967f1`
- consolidated remote: `refs/remotes/origin/refactor/20260714-1650-consolidated-spinal`
- official nested myCPU: detached `aa3bde1f3e720e71c2c78d6b81930d797b810149`
- remote ECHO: not present at the time of this record
- root AGENTS.md: local uncommitted governance edit; root has no remote
- Codex approvals: `.codex/rules/default.rules` is local and ignored

## Preflight commands

| command | result |
| --- | --- |
| `git status --short --branch` in nscscc-cpu | clean on `refactor/ECHO` |
| `git fetch origin <consolidated-refspec>` | exit 0 |
| `git rebase refs/remotes/origin/refactor/20260714-1650-consolidated-spinal` | exit 0; updated to `923eb73b` |
| `git status --short --branch` in chiplab | existing `vivado*.jou` files preserved |
| `git status --short --branch` in nscscc-linux-kernel | clean on `main` |
| process preflight | no build, simulation, fetch, rebase, or push process |

## Local profile

`make local-doctor OUT_DIR=build/local-bootstrap` passed after direct toolchain
fallbacks were added. The report is `build/local-bootstrap/local-env/summary.json`.
The profile records local evidence only; it does not assert `reference/manifest.lock`.

- Java: 21.0.11, `/usr/lib/jvm/java-21-openjdk-amd64/bin/java`
- Verilator: 5.051 devel, `/usr/local/bin/verilator`
- Python: 3.10.12, `/usr/bin/python3.10`
- SBT runner: `/home/toss-a-coin/.local/share/coursier/bin/sbt`
- GNU Make: 4.3
- LoongArch GCC: chiplab toolchain, 8.3.0 LA32 v2.0
- QEMU: chiplab `qemu-system-loongarch32`, 6.2.50
- NEMU: chiplab shared object recorded as an artifact, not an executable command
- Yosys: unavailable in the local PATH; future static checks must report this explicitly
- TEMP/TMP: `/mnt/c/Users/admin/AppData/Local/Temp`; host use is temporary-files-only

The first local doctor run failed because non-interactive PATH omitted chiplab GCC/QEMU.
The diagnostic now resolves those binaries from `CHIPLAB_HOME` or the workspace chiplab
toolchain paths. This was an environment-discovery fix, not a CPU behavior change.

## Files introduced in this iteration

- `tools/local_env.py`: local tool/repository evidence writer with SHA256 records.
- `Makefile`: local-doctor, local-scala and test-local targets.
- this Markdown record.

Root Makefile canonical `core_top` staging and root AGENTS cleanup remain the next
milestone. No chiplab commit or push was performed.

## Claims and residual risks

Allowed: ECHO is synchronized to the current consolidated tip; the official nested
source commit is present; the local tool profile is captured; the local doctor passes.

Not allowed: official functional PASS, full SpinalHDL completion, locked reproducibility,
full functional/random/performance/system PASS, Vivado timing PASS, or release readiness.

Rollback: revert this iteration's CPU commit if the local diagnostic interface proves
incompatible; do not delete official source, golden references, or chiplab user files.

## Automated and Scala checks

| command | exit | evidence |
| --- | --- | --- |
| `python3 -I -m py_compile tools/local_env.py tests/test_local_env.py` | 0 | local diagnostic syntax valid |
| `make test-local LOCAL_TMP_ROOT=/tmp` | 0 | 362 tests, 8.572 s, `OK` |
| `make test-local` with inherited host `TEMP/TMP` | 2 before test fix | DrvFS parent-swap safety test reports `ENXIO/EOPNOTSUPP`; use `/tmp` for WSL evidence |
| `make local-scala LOCAL_TMP_ROOT=/tmp` | 2 | scalafmt, Compile and Test/compile pass; 27/31 suites pass with `-CFLAGS -DWData=EData`; four wide `VlWide<N>` wrapper casts fail under Verilator 5.051 |
| `make local-doctor OUT_DIR=build/local-bootstrap` | 0 | report SHA256 `fe9eb755cc35c95a47df8994ef5162eefb1ffcf132d045bfdf678ab4701794b4` |

The Scala result is `environment-blocked`, not a CPU pass claim. The temporary
`WData` compatibility macro is passed through `SPINAL_VERILATOR_FLAGS`; no generated
RTL or host installation was modified. The remaining failures are the old Spinal
wrapper's casts of Verilator 5.051 `VlWide<N>` objects to `WData*` in wide-signal
suites. A compatible simulator/tool version or an audited Spinal backend update is
required before the full Scala simulation gate can pass.
