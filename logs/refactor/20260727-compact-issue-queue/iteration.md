# Compact age-ordered issue queue

Date: 2026-07-27

## Objective

Shorten the complete-SoC path from registered ROB wakeup tags through issue-queue wakeup,
oldest-ready selection, and payload selection. Keep the existing four issue ports, eight entries per
port, five writeback tags, and zero additional issue latency.

## Starting evidence

Commit `2965219e09a823244284ddc26b9fd77b382d0b9f` removed the raw divider completion path and
completed the locked Vivado 2023.2 implementation at 100 MHz. The bitstream and DRC completed,
but timing still did not close: WNS was `-0.729440 ns`, TNS was `-183.101868 ns`, and minimum
hold slack was `+0.015 ns`. The new worst path started at ROB `stagedPdst` and ended in the LSU
issue selection network. Thus the divider cut worked, but the physical-slot IQ's two-stage
age-to-slot lookup remained a routed critical path.

## ysyx comparison and discarded design

The ysyx `la32r-linux` reference at `8baa79a24989e2a5b7ebee76b1abcd2be1b10c7a`
keeps its eight IQ entries compact in age order. Wakeup compares tags directly with those entries,
priority encoding selects an age index, and one indexed payload read feeds issue; dequeue shifts
younger entries toward the head.

Our first candidate retained stable physical payload slots and shifted only an age-order index.
That removed the reverse O(8 x 8) readiness mapping, passed all local functional gates, and used
less IQ logic, but standalone Vivado exposed a new 13-level path from ROB `stagedPdst` through an
age lookup and a second physical-slot lookup to `issueAddressUop`. WNS was `-0.044 ns`, so that
candidate was discarded without being committed.

## Retained design

- Each per-port IQ is one eight-entry register vector compacted in program age order.
- Wakeup tags compare directly with the compact entries; the ready bitmap is already age ordered.
- The selected age index performs exactly one payload read.
- A middle dequeue shifts every younger payload down one slot. Same-cycle wake bits are folded
  into the shifted `source1Ready` and `source2Ready` fields, so a one-cycle pulse cannot be lost.
- Simultaneous dequeue and enqueue writes the new uop at `count - 1`; enqueue has priority at the
  destination slot.
- LSU store-data decoupling, serial-at-ROB-head gating, registered LSU issue output, and the
  existing registered enqueue backpressure boundary are unchanged.

A new directed test covers head dequeue, survivor compaction, younger wakeup, persistent ready
state, and later wakeup of the older survivor. All CPU implementation remains Scala/SpinalHDL;
the published Verilog was regenerated and was not edited manually.

## Local evidence

| Check | Result |
| --- | --- |
| Scala/Spinal/Verilator | 36 suites, 126/126 passed |
| Python repository gates | 362/362 passed |
| package/port/lint/Yosys/publish | all passed; 49 ports |
| exact generated-top lint | 844 warnings, only `UNUSEDSIGNAL`/`CMPCONST`; signature `3cc89716969f5559058cde99455e7b51aa92eb336be94b2cf7ead1235a0c8484` |
| generated RTL | SHA-256 `4f3964af34fdb67b26193420f4d48e584e42fc3c9f2579a504c7b54176d90886` |
| locked Chiplab `func_lab19` | DiffTest, syscall, and end PC passed; 139,671 instructions / 534,497 cycles / IPC 0.261313 |
| standalone Vivado 2023.2 | WNS `+0.359 ns`, TNS `0`; 72,088 LUT / 39,349 FF / 58 RAMB36 / 16 RAMB18 / 4 DSP |

Compared with the physical-slot candidate, compact age order improves standalone WNS by
`0.403 ns`. Compared with committed `2965219`, it keeps the same local cycle count and WNS,
adds 999 LUT (1.41%), and removes 121 FF. The standalone worst path returns to the pre-existing
L1I predecode-to-cache-enable path; ROB `stagedPdst` to IQ is absent from the top 20 paths.

Standalone report SHA-256 values:

- timing: `ff66ff258d40661ac49679bc60729e3cf83c8f9de2016a0ff5596e034fb080e5`
- utilization: `8a3c22d49c576f0ca8d88199bf1c5a49604949ed5d6faaf4f72f3bc83584089f`
- DRC: `09069a591112966e828a59b71aa3b11d8a542638e383669776c0719c6a0b273b`
- DCP: `efb03e334fd555c5fd40cb721d6eed2495a124fe91d06581893e8691aea1feaa`

## Promotion boundary

Standalone synthesis does not prove complete-SoC timing. The next gate is a locked build of this
exact committed revision with the official SoC and board constraints at 100 MHz. It must achieve
non-negative routed WNS and pass remote `func58` before three real `perf20` runs can decide whether
the candidate becomes the performance baseline.

## Rule audit

The change only restructures the CPU issue queues, preserves architectural ordering and the
official 49-port top, and adds no accelerator, test-specific answer, simulation dependency, or
handwritten Verilog. Generated RTL identity is locked by the replacement and lint manifests.
