# Registered accepted-completion boundary at the ROB

Date: 2026-07-21

## Objective

Remove the synthesized LSQ-completion-to-ROB-entry clock-enable critical path
without changing completion acceptance, PRF writeback, dependency wakeup, or
architectural behavior.

## Design

The ROB still checks completion valid, entry validity, entry generation
pointer, and incomplete state in the arrival cycle.  Its
`completionAccepted` response therefore preserves the existing PRF and wakeup
acceptance timing.  For each of the five writeback lanes, the ROB now registers
the accepted one-hot entry target and only the payload fields consumed by the
ROB: result, side-effect data, exception metadata, branch-resolved state,
branch-mispredict state, and branch target.  The selected entry is completed on
the following cycle.

Flush clears all staged one-hot targets.  Already-complete entries reject
duplicate completions, and generation-pointer comparison still rejects stale
completions after entry reuse.  Higher-numbered completion lanes retain the
previous priority if malformed inputs target the same entry.

An initial implementation registered the complete `OooCompletion` bundle and
raised lint from 738 to 743 warnings.  It was narrowed before acceptance;
unused `robPointer`, `pdst`, `writesPdst`, and `branchTaken` fields are not
stored.  Final lint is exactly the previous 738-warning signature.

## Results

| Metric | Previous `87f23ae` | Candidate | Delta |
| --- | ---: | ---: | ---: |
| LUT | 69,787 | 69,566 | -221 (-0.32%) |
| FF | 34,978 | 35,862 | +884 (+2.53%) |
| WNS | -0.737 ns | -0.290 ns | +0.447 ns |
| TNS | -819.826 ns | -0.290 ns | +819.536 ns |
| Failing endpoints | 2,457 | 1 | -2,456 |
| RAMB36 / RAMB18 / DSP | 42 / 12 / 4 | 42 / 12 / 4 | unchanged |

Generated RTL SHA-256:
`1cc5e65b5140d25d062b315adade540008dfd0c9596f08dea751be7e1344c1f6`.

The former LSQ-to-ROB-entry path is absent from the reported worst paths.  The
only remaining setup violation is LSQ `loads_7_virtualAddress` to backend
`wakeupCompletionValid[3]`, with 10.139 ns data delay.  Standalone 100 MHz
timing remains open by 0.290 ns.

## Evidence

| Check | Result |
| --- | --- |
| Scala/Spinal tests | 35 suites, 83/83 passed |
| Python repository gates | 362/362 passed |
| package, port, lint, Yosys, publish gates | passed; lint 738 exact signatures and clean closure |
| Chiplab `func/func_lab19` with NEMU DiffTest | syscall end; 126,136 instructions; 776,232 clocks; IPC 0.162498 |
| Vivado 2023.2 synthesis | 0 synthesis errors; 0 critical synthesis warnings; DCP/reports generated |

The official simulation cycle count is unchanged.  This round is retained for
the measured synthesis timing improvement, not claimed as a workload IPC
improvement.

## Compliance and limits

Only Scala/SpinalHDL source and Scala tests changed.  Generated Verilog remains
ignored and reproducible from the locked generator.  No handwritten Verilog,
timing exception, simulator shortcut, or workload-specific behavior was added.
The remote FPGA evaluation skill is unavailable, so no real-board speedup claim
is made and the required three board runs remain pending.
