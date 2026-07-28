# ROB completion local-decode iteration

Date: 2026-07-21

## Objective

Reduce the area and critical-path cost of writing five completion lanes into a
32-entry ROB without changing the fixed four-issue, five-writeback,
three-commit protocol.

## Kept change

`OooRob` now compares every valid entry with every completion pointer locally
and performs the field update at that entry.  This replaces dynamic `Vec`
index writes, whose generated decoder and per-field priority mux were large.
The highest-numbered matching completion lane still wins if malformed input
duplicates a ROB pointer, so the previous assignment priority is preserved.

The generated RTL is no longer tracked.  `make generate-core` packages the
authoritative file at `build/core_top/package/rtl/mycpu_top.v` and mirrors it
to the ignored `rtl/mycpu_top.v` path for existing consumers.

## Rejected experiment

Adding `DONT_TOUCH` boundaries to LSQ completion registers was synthesized and
rejected.  It increased area and changed WNS from `-4.368 ns` to `-4.403 ns`.
No attribute from that experiment remains in the source.

## Evidence

Generated RTL SHA-256:
`72766abf6aaa5765c56ab93d1e4a55cda8ddc9c69f3f775885f84c3622ae0b06`.

| Check | Result |
| --- | --- |
| Scala/Spinal tests | 35 suites, 81/81 passed |
| Python repository gates | 362/362 passed |
| package, port, lint, Yosys, publish gates | passed |
| Chiplab `func/func_lab19` with NEMU DiffTest | syscall end; 126,136 instructions; 776,232 clocks; IPC 0.162498 |
| Vivado 2023.2 synthesis | 0 synthesis errors; 0 critical synthesis warnings |

Vivado target: `xc7a200tfbg676-2`, 100 MHz standalone synthesis.

| Metric | Previous commit | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Total LUT | 73,905 | 71,539 | -2,366 (-3.2%) |
| FF | 34,504 | 34,524 | +20 |
| RAMB36 / RAMB18 / DSP | 42 / 12 / 4 | 42 / 12 / 4 | unchanged |
| WNS | -4.428 ns | -4.368 ns | +0.060 ns |
| TNS | -30393.850 ns | -33865.806 ns | -3471.956 ns |

The worst path still begins at
`loadStoreQueue/loads_7_robPointer_reg` and ends at a ROB exception-field
clock enable.  Timing is not closed.  The local synthesis result demonstrates
an area improvement, not an FPGA execution-time claim.  The remote FPGA
evaluation skill was unavailable, so the required three board runs remain
outstanding.

## Rule audit

The hardware change is Scala/SpinalHDL source only.  No handwritten Verilog,
simulation shortcut, timing exception, or workload-specific data was added.
The official 49-port top contract and `TLBNUM=32` guard remain unchanged.
