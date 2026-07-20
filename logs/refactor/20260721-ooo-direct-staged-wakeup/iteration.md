# Direct wakeup from the ROB accepted-completion stage

Date: 2026-07-21

## Objective

Close the final standalone 100 MHz setup violation without adding another
wakeup cycle or changing architectural execution time.

## Design

The preceding `a94a289` baseline registered accepted ROB completion targets and
the payload needed for retirement.  The backend still independently registered
five complete `OooCompletion` bundles, with its valid input driven by the
current-cycle ROB acceptance network.  That duplicated storage and extended
the LSQ completion path to `wakeupCompletionValid`.

This round adds `pdst` and `writesPdst` to the existing ROB accepted stage and
exports only staged `valid`, `pdst`, and `data` to the backend.  IQ wakeup, PRF
write, and ready-map writeback now consume those registered outputs directly.
They remain visible in the same cycle as before because the removed backend
register and the ROB accepted register occupied the same pipeline boundary.
Flush gates staged wakeup and clears accepted one-hot targets.

The obsolete current-cycle `completionAccepted` output was removed after it
lost its final production consumer.  Directed tests observe the staged
wakeup/commit behavior instead of retaining a test-only port.

## Results

| Metric | Previous `a94a289` | Candidate | Delta |
| --- | ---: | ---: | ---: |
| LUT | 69,566 | 69,560 | -6 |
| FF | 35,862 | 35,607 | -255 |
| WNS | -0.290 ns | +0.419 ns | +0.709 ns |
| TNS | -0.290 ns | 0.000 ns | +0.290 ns |
| Failing endpoints | 1 | 0 | -1 |
| Verilator lint warnings | 738 | 668 | -70 |
| RAMB36 / RAMB18 / DSP | 42 / 12 / 4 | 42 / 12 / 4 | unchanged |

Generated RTL SHA-256:
`239872bf2a4768e534b2b700b47be640aca55422f094e20f80474626c57e7701`.

All standalone 100 MHz timing constraints are met.  The new worst path is
backend `issueOperandUop_2_decoded_mulDivSigned` to multiplier `result[29]`,
with 9.460 ns data delay.

## Evidence

| Check | Result |
| --- | --- |
| Scala/Spinal tests | 35 suites, 84/84 passed |
| Python repository gates | 362/362 passed |
| package, port, lint, Yosys, publish gates | passed; lint 668 exact signatures and clean closure |
| Chiplab `func/func_lab19` with NEMU DiffTest | syscall end; 126,136 instructions; 776,232 clocks; IPC 0.162498 |
| Vivado 2023.2 synthesis/timing | 0 synthesis errors; WNS +0.419 ns; TNS 0; 0 failing endpoints; DCP/reports generated |

The official simulation cycle count is unchanged.  This round is retained for
measured timing closure and lower storage/lint complexity, not claimed as an
IPC improvement.

## Compliance and limits

Only Scala/SpinalHDL source and Scala tests changed.  Generated Verilog remains
ignored and reproducible from the locked generator.  No handwritten Verilog,
timing exception, simulator shortcut, or workload-specific behavior was added.
Standalone synthesis lacks the board XDC and therefore still reports NSTD-1
and UCIO-1.  The remote FPGA evaluation skill is unavailable, so no real-board
speedup claim is made and the required three board runs remain pending.
