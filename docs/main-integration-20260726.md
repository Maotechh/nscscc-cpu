# Main integration readiness (2026-07-26)

## Integration basis

- Integration branch: `integration/main-ready-20260726`
- Upstream implementation base: `origin/dev-OoOE@d126f579971eb4331e1c918dfc291a3924bd7036`
- Current main dependency base:
  `main` and `origin/main` at `ad6551afe009652b5562f200bd0d76f641d56a76`
- Legacy development tip: `dev@f60ea3813aad4c16ab3bf395d83e8ecd60e48644`

`dev` and `origin/dev-OoOE` share the current main commit as their merge base, but have
diverged by 13 and 33 commits respectively. A direct merge reports conflicts across the backend,
frontend, memory system, tests, generated RTL, gates, and historical logs. More importantly, it
would reintroduce the deleted legacy `pipeline` implementation and place the older
`openla500.ooo` tree beside the reorganized `backend`, `core`, `frontend`, and `memory` packages.
The integration therefore uses the newer OoO tree as the source of truth and ports only missing
behavior.

## Legacy development disposition

| Legacy work | Disposition on the integration branch |
| --- | --- |
| Main reset and overlay synchronization | Already in the common main base |
| Active three-wide checkpoint and cache-contract refactor | Superseded by the reorganized four-issue/three-commit tree |
| Register-writing wakeup qualification | Already implemented in the registered ROB completion path |
| Committed-store recovery ordering | Already implemented, including a flush/drain regression |
| Fetch exception preservation and decode priority | Already implemented, including misaligned-fetch ADEF coverage |
| Fetch-side TLB exception classification | Already implemented; PIF ECODE 3 participates in the TLB exception set |
| Serial issue/CSR timing closure | Serial issue ordering was missing and has been ported semantically |
| Cross-cache self-modifying-code maintenance | Dirty cacheable data ordering was incomplete and has been ported semantically |
| Iteration archives and the old package layout | Deliberately not imported into the active source tree |
| USB/PS2 audit | Preserved as `docs/usb-ps2-audit.md`; no peripheral implementation change in this integration |

## Resolved behavior

### Serial instructions

The backend records the first accepted serial instruction as a ROB fence. It stops later rename
groups, prevents younger IQ entries from issuing, and holds any defensively blocked operand-stage
entry until the fence commits. Older work remains eligible, so a serial instruction cannot
deadlock behind an older dependency. Flush clears the fence.

The IQ wakeup cleanup also compares writeback tags directly against physical slots instead of
mapping logical order entries to slots and back again.

### Instruction-cache maintenance

Instruction maintenance now executes in this order:

1. L1D writeback and invalidate;
2. L2 writeback and invalidate;
3. L1I invalidate.

This preserves dirty instruction bytes produced by a cacheable self-modifying-code store before
removing stale instruction copies. The regression dirties a shared line through L1D, proves that
the updated word reaches external memory, proves that L1D no longer supplies a stale hit, and then
refills L1I through the refreshed hierarchy.

### Repository cleanup

Local DSE output, raw review evidence, simulator traces, UART captures, and Python cache files are
ignored. Condensed reports remain eligible for version control.

## Verification

- `scalafmtCheckAll`, main compile, and test compile: pass.
- Full Scala/SpinalHDL suite: 35 suites, 114 tests, all pass.
- Focused serial-IQ/backend suite: 11 tests, all pass.
- Focused shared-cache suite: 2 tests, all pass.
- Python unit suite: 362 tests, all pass.
- Generated top package: pass; SHA-256
  `92b91e43cdc5bf949557d732fb8f43dbce87341a0ed810969b95adb18e118c0f`.
- Locked top port check: pass.
- Yosys complete-top check: pass, no warning or skip marker.
- Verilator locked lint: pass; the existing 781-warning exact signature remains unchanged and
  closes to zero after its exact waiver.
- Publication consistency: pass; tracked RTL, generated package, and replacement ledger match.

Vivado synthesis and frequency exploration were intentionally not run for this integration.

## Merge policy

Do not merge `dev` directly into `main` or the integration branch. Review and merge
`integration/main-ready-20260726` instead. Before merging, refresh `origin/main`; if it has advanced
past the dependency base above, merge that new `origin/main` into the integration branch and rerun
the same gates before updating `main`.
