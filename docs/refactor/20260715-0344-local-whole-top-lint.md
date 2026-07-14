# 20260715 local whole-top lint baseline

## Goal and inputs

Add an explicit local Verilator profile without weakening the locked manifest
gate, then record the complete generated `core_top` warning baseline. This is a
diagnostic result and is not a lint pass or whole-core acceptance claim.

- ECHO base: `fe8bd50a8a55889f80cd303c2e6bffc52b83fc04`
- official source: `aa3bde1f3e720e71c2c78d6b81930d797b810149`
- generated package: `.work/echo/fe8bd50.../package/rtl/mycpu_top.v`
- environment profile: `local`; the locked tool identity was not asserted
- Verilator: `5.051 devel rev v5.050-45-gf316ec0d6`
- temporary root: `/tmp`

## Commands and exits

| command | exit | result |
| --- | --- | --- |
| `python3 -I tests/test_core_top_gate.py -v` | 1 | first added negative-test run exposed a test-fixture escaping error; corrected before final run |
| `python3 -I tests/test_core_top_gate.py -v` | 0 | 29 focused gate tests passed |
| `python3 -I tools/core_top_gate.py lint ... --environment-profile local` | 1 | fail-closed summary written; 73 warnings |
| `sha256sum .../verilator.log .../summary.json .../mycpu_top.v` | 0 | artifact hashes recorded below |
| `make test-local LOCAL_TMP_ROOT=/tmp` | 2 | first full run exposed the same test-fixture error; no production failure |
| `make test-local LOCAL_TMP_ROOT=/tmp` | 0 | 371 tests passed in 8.634 s |
| nested official Git status check in the Codex sandbox | 101 | environment failure: `bubblewrap` unavailable; no write attempted |

The local profile resolves the requested Verilator and records its binary hash
and version. It deliberately skips only the locked manifest's version and
binary-hash assertions. Nonzero exit status, timeout, every warning, and every
skip marker continue to fail the gate. Failed runs now write `summary.json`
before raising so the warning evidence is not lost.

## Outputs and hashes

- complete packaged RTL SHA-256:
  `ac6a631e696d3bc75f41604b1f7191ad62655834b9f9ed37abcab030c6e706f1`
- Verilator log SHA-256:
  `56d0c93365107f82db3d21492c4e7333ac25dbdc33d2e8f8b76d8042d61adda2`
- lint summary SHA-256:
  `6ac7e833cda40c1beabf73e3086193847f4aa2f98c374ca0928b70b88b1008fd`
- warning categories: 71 `UNUSEDSIGNAL`, one `DECLFILENAME`, one
  `UNUSEDPARAM`
- lint result: `status=fail`, `returncode=1`, `timed_out=false`, no skip
  markers

The large final `UNUSEDSIGNAL` group is the inline chiplab DiffTest observation
shell when `DIFFTEST_EN` is absent. Other warnings include AXI response fields,
instruction-write inputs, pipeline observation signals, cache preload state,
CSR/TLB bit slices, the integration `TLBNUM` parameter, and the one-file module
name mismatch. They remain unresolved; no global warning suppression or waiver
was added.

## Claim, risk, and rollback

Qualified diagnostic: the local Verilator can evaluate the complete 49-port
Spinal package and produces a durable, fail-closed warning inventory. The
locked gate remains separate and unchanged. This does not establish warning
closure, functional correctness, DiffTest correctness, synthesis validity, or
release readiness.

Residual risk is the full 73-warning inventory plus the previously documented
functional, random, performance, system, and Vivado blockers. Warning cleanup
must distinguish integration-only observations from incomplete active logic;
none may be hidden by a broad waiver.

Rollback: revert this ECHO commit. Generated evidence under the root `.work`
tree is disposable; do not modify or clean chiplab or the nested official
checkout.
