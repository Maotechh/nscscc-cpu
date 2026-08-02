# OpenCode Auto-Iteration Handoff (2026-08-02)

## Scope

This branch preserves the accepted result of the `cpu-continuous` OpenCode
campaign. The campaign started from `1eb45e6ba5b9ab6911b932d7b47f4dc6ff6f5643`
and its accepted head is `234ea8c596fc53ba4532640f58168bca6457ad85`.
It has not been merged into `main` or `dev`.

The accepted source change pipelines the bimodal PHT commit-update path, aligns
fallback direction metadata at the response boundary, and adds directed tests
for update collisions, redirect recovery, RAS recovery, and untrained fallback.
`rtl/mycpu_top.v` is generated from the Scala/SpinalHDL source; no handwritten
Verilog was introduced.

## Iteration History

| Iteration | Result | Disposition |
| --- | --- | --- |
| 001 | Pipeline BTB/PHT commit training | Retained |
| 002 | Add a 64-entry bimodal cold-miss predictor | Retained |
| 003 | Double ROB/IQ/LSQ/MSHR capacity | Rejected and reverted |
| 004 | Restore the no-scale configuration and close local gates | Retained |
| 005 | Stage bimodal updates and align response fallback metadata | Accepted |
| 006 | FPGA `func58` at a 92 MHz target | Passed |
| 007 | Three FPGA `perf20` runs | Accepted, decisive 2.1367x speedup |

## Verification

Local evidence at the accepted snapshot:

- directed predictor specification: 4/4 passed;
- Scala and generated-RTL flow passed;
- port, lint, Yosys, and publish-consistency gates passed;
- corrected `func_lab19` A/B showed no candidate stall or divergence;
- FPGA `func58` passed at 92.310533 MHz actual frequency.

Three independent FPGA `perf20` runs all passed 20/20 benchmarks:

| Job | Total `soc_count` | Execution time | Speedup |
| --- | ---: | ---: | ---: |
| `20260801-220157-75375597` | 95,850,432 | 958.504 ms | 2.1586x |
| `20260802-072457-73e9a69a` | 95,269,488 | 952.695 ms | 2.1718x |
| `20260802-072458-4b980736` | 96,833,006 | 968.330 ms | 2.1367x |

The comparison baseline is 206,902,887 `soc_count` (2.069029 s). Per the
campaign policy, the lowest measured improvement is decisive, so this branch
records a 2.1367x board-measured speedup.

The perf build reported advisory WNS `-0.676437 ns`. The board measurements
were stable, but this is not a strict timing-closure claim.

## Branch and Integration

The single `opencode-auto-iteration-20260802` branch preserves the complete
iteration history. The large-window commits are evidence for a rejected
experiment and were subsequently reverted; they must not be treated as a
release candidate. Commit `234ea8c` is the accepted campaign handoff point.

The accepted history was based on `main`, while the repository's `dev` history
has diverged. Integration into either branch requires an explicit review or
cherry-pick; no automatic merge was performed.

The branch head also preserves the incomplete iteration 008 L1D early-restart
experiment. It is explicitly documented as WIP in
`docs/iteration-008-wip-20260802.md` and does not change the accepted-point
designation above.
