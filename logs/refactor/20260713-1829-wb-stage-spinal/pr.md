# PR draft: SpinalHDL writeback stage

- Branch: `refactor/20260713-1829-wb-stage-spinal`
- Base: `a6788aaf36cea5a90512d60194c9e41a5c127860`
- Head: `4d03454359c73854ffecf25a529d820b89fa285e`
- Scope: typed WB stage, legacy port adapter, CommitEvent observation and differential gates.
- Evidence: `logs/refactor/20260713-1829-wb-stage-spinal/`.
- Verified: Scala 4/4, ports 52/64, lint/Yosys both profiles, 8238-cycle lockstep and negative control.
- Not claimed: official func, random NEMU, performance, Linux, Vivado, full-core equivalence.
- Known blockers: WB not in active overlay; baseline `func_lab19` mismatch at `0x1c07c79c`; Claude review unavailable.
- Rollback: revert commits `4d03454359c73854ffecf25a529d820b89fa285e` and `2cfc0c9d0defefad0da8dcb7ddd775637e8ca47c`.
- Merge policy: draft/awaiting review; no automatic merge.
