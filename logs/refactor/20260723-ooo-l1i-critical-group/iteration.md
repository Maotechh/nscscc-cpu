# L1I critical-group early response

Date: 2026-07-23

## Objective

Reduce instruction-cache miss latency without changing line fill ownership,
cache installation ordering, flush cancellation, or the 4-issue/3-commit
architectural interface.

## Design

`OooL1InstructionCache` now tracks whether the requested 16-byte fetch group
has arrived.  On the accepting refill beat, it builds a combinational view of
the refill line including that beat and returns the requested group immediately.
The later `install` state still installs the complete 64-byte line, while
`refillResponseSent` prevents a duplicate response.  Error accumulation and
kill/flush gates remain active for both early and install responses.

`OooFrontend` now marks a sequential translation request accepted on the same
edge as a predicted redirect as a dropped response owner.  The later response
is drained and the frontend can issue the redirected translation instead of
deadlocking the translation port.

## Results

| Metric | Previous `8c96eb7` | Candidate | Delta |
| --- | ---: | ---: | ---: |
| `func_lab19` committed instructions | 132,916 | 132,917 | +1 |
| `func_lab19` clocks | 599,313 | 586,915 | -12,398 (-2.069%) |
| IPC | 0.221781 | 0.226467 | +2.11% |
| LUT | 72,015 | 72,637 | +622 |
| FF | 39,676 | 39,673 | -3 |
| WNS / TNS / failing endpoints | +0.419 / 0 / 0 | +0.419 / 0 / 0 | unchanged |
| RAMB36 / RAMB18 / DSP | 42 / 12 / 4 | 42 / 12 / 4 | unchanged |

## Evidence

- Scala/Spinal/Verilator: 35 suites, 91/91 tests passed.
- Python repository gates: 362/362 tests passed.
- Complete-top package, 49-port contract, lint, Yosys and publish checks:
  passed; lint has 665 exact locked warnings and zero closure errors.
- Chiplab `func/func_lab19`, NEMU DiffTest, bus-delay seed `5570815`:
  `END by Syscall`, reached end PC, 132,917 instructions, 586,915 clocks,
  IPC 0.226467, no mismatch.
- Vivado 2023.2 standalone synthesis on `xc7a200tfbg676-2`: 0 synthesis
  errors, 0 critical synthesis warnings, WNS `+0.419 ns`, TNS `0`, 0 failing
  endpoints. Standalone DRC retains the expected NSTD/UCIO/CFGBVS top-level
  warnings plus DSP pipelining advisories.

## Compliance and limits

Only Scala/SpinalHDL source and Scala tests implement the optimization;
`rtl/mycpu_top.v` is regenerated and hash-checked.  No handwritten CPU
Verilog, timing exception, simulator shortcut, or workload-specific behavior
was added.  The remote `perf20` package and three real-board runs are still
pending; local cycle reduction is not yet an FPGA performance claim.
