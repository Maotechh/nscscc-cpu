# Draft PR: publish the canonical pure-Spinal CPU overlay

Status: implementation gates pass; full release gates remain pending.

## Change

Publish the reproducible self-contained `core_top` at `rtl/mycpu_top.v`, the path consumed by the locked FPGA client. Remove the obsolete `CPUCoreFlat` RTL and inactive draft Scala implementation. Bind overlay specs, publication checks, tests, and the locked exact-warning waiver to the canonical path.

## Verification

Locked Scala 4/4, reproducible generation 2/2, official 49-port contract, publish consistency, port/Yosys, candidate closure, typed AXI, and replacement reachability pass. Locked lint passes through an exact 73-signature audit followed by a zero-warning closure; it is not a strict-zero source claim. Windows automation passes 390 tests with 10 platform skips; a clean Linux zero-skip run remains required after commit.

## Risk and rollback

Full func58/func81, random, performance, Linux, and FPGA evidence is not yet available, so this PR remains draft. Six warning-backed debts remain explicit in the iteration log. Revert this iteration commit to restore the prior reference-only publication layout; do not merge automatically.
