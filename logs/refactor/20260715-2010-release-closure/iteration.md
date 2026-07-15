# 20260715-2010-release-closure

- Status: implementation_ready_for_commit
- Branch / Base SHA / Head SHA: `refactor/20260715-2010-release-closure` / `56d74f4b92d85e6403689cbbe4f7b4b460e8f63a` / `56d74f4b92d85e6403689cbbe4f7b4b460e8f63a`
- Owner / Agent: Codex `/root`
- Selected boundary and selection reason: release-closure audit of the committed pure-Spinal `core_top`; this is the narrowest boundary that can determine which repository completion gates are real, missing, or failing before any further implementation.
- Golden reference and locked tool versions: `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`; versions are locked by `reference/manifest.lock`.
- Behavior contract: `AGENTS.md` completion definition, `docs/contracts/candidate-closure.md`, and `docs/contracts/core-top-compat.md`.
- Files changed: publish the reproducible package at `rtl/mycpu_top.v`; remove the obsolete `CPUCoreFlat` RTL and 15 inactive draft Scala sources; bind the publication specs and exact lint waiver to the canonical path; update affected tests and documentation.
- Attempts and failures: Windows `scala-check` incorrectly mapped `/opt` to `D:/opt`; the locked WSL run passed. A focused Python command used package-style test names although `tests/` is not a package; direct scripts and discovery passed. A WSL discovery run inherited linked-worktree `GIT_DIR` into temporary fixture repositories and therefore failed four Git-fixture tests; this is a harness invocation error, and the final zero-skip run remains required from a clean Linux clone. Two tests initially retained the old generated-RTL path and were fixed.
- Commands and gate results: doctor PASS; locked Scala 4/4 PASS; reproducible generation 2/2 PASS; official 49-port contract, publish consistency, port, Yosys, candidate closure, typed AXI, and reachability PASS; locked exact-waiver lint PASS after an unsuppressed exact 73-warning audit and zero-warning closure; Windows automation 390 PASS with 10 platform skips, not accepted as the final Linux gate.
- Functional/performance/resource delta: not measured.
- Residual risks: the source is not strict-zero clean. The exact waiver includes 67 compatibility/profile warnings and six explicit debts: fixed-only `TLBNUM`, unused BTB delete, unused PRELD hint, ignored AXI `rresp/bresp`, and write-only BRK state. Full func58/func81, random, performance, system, FPGA, and independent claim review remain unverified.
- Rollback: revert this iteration's commits; the consolidated branch and original dirty worktree remain untouched.
- PR URL or awaiting state: awaiting implementation commit and push.
- Next unblocked candidates: clean-clone Linux automation; diagnostic func58/func81; FPGA client package build after the commit is available remotely.
