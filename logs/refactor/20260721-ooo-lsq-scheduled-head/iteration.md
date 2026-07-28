# LSQ scheduled-head timing iteration

Date: 2026-07-21

## Objective

Remove the full load-queue ROB-age comparison from the completion path while
retaining physical slot wrap-around and precise load/store ordering.

## Design

The LSQ now tracks `loadBase`, which advances by the retired-load count and
resets at a recovery flush.  A rotated pending bitmap selects the oldest live
slot in circular allocation order.  On the first allocation group of an epoch,
up to three new ROB pointers are compared once to initialize the base; this
keeps direct LSQ probes and recycled-slot states deterministic.  The selected
index then passes through a registered `scheduledLoadValid/loadHead` boundary,
matching the ysyx LoadQueue's registered uop output.  Cache request ownership,
translation ownership, and completion generation consume that registered
selection.

## Experiments

| Candidate | LUT | FF | WNS | TNS | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Previous commit `ff89be8` | 71,539 | 34,524 | -4.368 ns | -33865.806 ns | baseline |
| Rotated bitmap without scheduled register | 71,143 | 34,524 | -4.985 ns | -40353.963 ns | rejected |
| Rotated bitmap plus registered scheduled head | 71,071 | 34,529 | -3.484 ns | -1132.243 ns | kept |

The rejected version reduced LUT but made timing worse because Vivado still
folded the selection network into the completion enable.  The kept register is
an architectural state boundary rather than a synthesis attribute; it moves
the critical path to ROB serializing metadata feeding CSR TLBIDX control.

## Evidence

Generated RTL SHA-256:
`a8967e8fdeaee20dfacce57ed1a89ecb408a416454aeb1ac1ad4604e9fbcca4e`.

| Check | Result |
| --- | --- |
| Scala/Spinal tests | 35 suites, 81/81 passed |
| Python repository gates | 362/362 passed |
| LSQ directed tests | 10/10 passed, including base initialization and post-commit wrap |
| package, port, lint, Yosys, publish gates | passed; lint 728 exact signatures |
| Chiplab `func/func_lab19` with NEMU DiffTest | syscall end; 126,136 instructions; 776,232 clocks; IPC 0.162498 |
| Vivado 2023.2 synthesis | 0 synthesis errors; 0 critical synthesis warnings |

Vivado target: `xc7a200tfbg676-2`, standalone 100 MHz synthesis.  The worst
path is `ROB entries_23.uop.decoded.serializing` to CSR `logic_tlbidx` CE,
with 13.139 ns data delay.  Timing is improved but not closed.

## Compliance and limits

Only Scala/SpinalHDL and directed Scala test sources changed.  No handwritten
Verilog, timing exception, simulator shortcut, or workload-specific behavior
was added.  The remote FPGA evaluation skill is unavailable, so no board
speedup claim is made and the required three real-board runs remain pending.
