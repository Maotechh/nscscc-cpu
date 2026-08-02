# Iteration 008 WIP Handoff: L1D Early Restart

## Status

This branch preserves the incomplete working tree that was active when the
OpenCode campaign was stopped on 2026-08-02. It is based on the accepted
`234ea8c596fc53ba4532640f58168bca6457ad85` predictor snapshot.

This is a WIP branch, not an accepted performance iteration. It has no campaign
receipt, Vivado result, FPGA functional result, or `perf20` measurement.

## Hypothesis and Implementation

The experiment reduces load-miss latency by restarting a load as soon as the
64-bit refill beat containing its requested word arrives, instead of waiting
for all eight beats of the 64-byte line to be installed.

The current implementation also permits a following load to the same line to
be accepted while refill is active. If that load's beat has already arrived it
is replayed immediately; otherwise it receives an early response when the beat
arrives. Stores and loads to other lines remain blocked until installation.

Tracked changes in this snapshot:

- `spinal/src/main/scala/openla500/memory/OooL1DataCache.scala`;
- L1D and hierarchy simulation specifications;
- regenerated `rtl/mycpu_top.v`;
- updated lint-waiver and component-replacement hashes.

No generated build tree, OpenCode state, or temporary Chiplab directory is
included in the commit.

## Evidence Collected Before Stop

| Lane | Result |
| --- | --- |
| `OooL1DataCacheSpec` | 6/6 passed |
| Memory/cache Scala suite | 22/22 passed |
| Port check | Passed |
| RTL lint | Passed |
| Yosys check | Passed |
| Publish consistency | Passed |
| Generated RTL SHA-256 | `beed4a3f029b3e758c4f2d676a613006f9d1ce07a90607b31733c274cf5da11c` |
| Full Python suite | Failed: 14 failures out of 362, matching the existing host/tooling failure class |

An initial hierarchy test failed because the test sampled the response after
the new early pulse. The test was corrected to capture the pulse during refill;
the rerun passed 3/3, and the subsequent memory suite passed 22/22.

The final 30 ms Chiplab/Verilator simulation was still running when the operator
stopped the campaign. It was terminated together with the detached simulation
process group and produced no terminal pass/fail verdict. Diagnostic NEMU
messages in the partial log are therefore not an acceptance result.

## Required Work Before Acceptance

1. Review the refill-response and replay arbitration for simultaneous request,
   beat, install, error, invalidate, and backpressure cases.
2. Re-run a bounded functional lane with an absolute or board-backed oracle.
3. Run Vivado synthesis and inspect timing/resource changes.
4. Pass FPGA `func58`, then run three serialized `perf20` measurements.
5. Write an iteration receipt and accept or reject the experiment from the
   measured result.

Until those steps are complete, use
`auto-iteration/cpu-accepted-20260802` as the release-quality campaign result.
