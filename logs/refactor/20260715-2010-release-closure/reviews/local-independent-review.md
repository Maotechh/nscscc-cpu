# Independent read-only release review

Reviewed target: `9a29409242bf29436bf553e584b87018fb3f6fa6`.

## Blocking findings

1. The committed iteration metadata did not pass `make evidence-check`: its status was not in the allowed schema, its head was stale, command records were malformed, and the required Claude-attempt files were absent. This follow-up evidence change addresses the schema issues but cannot replace an unavailable external review.
2. The 73-warning core-top suppression is aggregate and hash-locked, but it is not represented as individual `lint-waivers.yml` records with rule, file, line, owner, and expiry. Treat required static lint as failed; the aggregate closure is diagnostic only.
3. Both official functional suites pass their software/DiffTest checks but fail the strict warning gate: func58 has 58/58 functional points and func81 reaches score 81, while each compile reports 40 DUT and 365 official-environment warnings.
4. Random DiffTest, perf20, U-Boot, Linux, Vivado implementation/timing/bitstream, and FPGA hardware are not complete. The locked random result directory contains no cases, so an upstream zero exit would not be evidence.
5. The active predictor is the official 32-entry profile, while the repository completion contract still names the historical a158 64-entry BTB. The authority and target behavior must be reconciled before a completion claim.
6. The canonical package is LACC-off. A LACC-on generator exists, but no release-equivalent functional/performance/FPGA matrix is archived for both profiles.

## Supported narrow findings

- `rtl/mycpu_top.v` is a reproducible self-contained generated `core_top`; the active hierarchy contains no historical CPU Verilog instance.
- The only Scala `BlackBox` is the conditional simulator-owned DiffTest DPI shell, not CPU implementation logic.
- The official 49-port contract, publication consistency, Yosys hierarchy/check, candidate closure, typed AXI boundary, and replacement reachability pass at the reviewed source content.
- The branch may be pushed and opened only as a Draft PR. It is not merge-ready or release-ready.

## Claim disposition

- Pure active Spinal candidate: accepted with the active-path and candidate qualifiers.
- Strict-zero lint clean: rejected.
- func58/func81 strict PASS: rejected; functional diagnostic PASS only.
- Fully refactored/release-ready: rejected.

This is a local independent review fallback, not a Claude review.
