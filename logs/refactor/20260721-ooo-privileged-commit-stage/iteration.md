# Privileged commit side-effect stage

Date: 2026-07-21

## Objective

Cut the ROB serializing-to-CSR/TLB critical path without changing precise
exception behavior or adding a timing exception.

## Design

`OooCoreSystem` now captures the state-changing payloads for CSR writes, ERTN,
TLB search/read/write/fill/invalidate, cache maintenance, and LL/SC reservation
updates at the architectural commit boundary.  The existing privileged redirect
request and pending-flush timing remains unchanged; the captured payload is
applied on the same clock edge as that flush.  This follows the ysyx design
pattern of staging serialized privileged effects after ordered commit instead
of driving architectural state directly through ROB metadata.

## Results

| Metric | Previous `a09e6a6` | Candidate | Delta |
| --- | ---: | ---: | ---: |
| LUT | 71,071 | 71,071 | 0 |
| FF | 34,529 | 34,620 | +91 |
| WNS | -3.484 ns | -1.202 ns | +2.282 ns |
| TNS | -1132.243 ns | -906.053 ns | +226.190 ns |
| Failing endpoints | 3,054 | 2,644 | -410 |

Generated RTL SHA-256:
`0a79277e8c3ef80c2f9d65c21e176df5d43802e5e88eb9fed3581dd0b09dae17`.

The new worst path is FreeList `freeBits[15]` to RegisterMap `ready[10]`, with
11.051 ns data delay.  Standalone 100 MHz timing is improved but not closed.

## Evidence

| Check | Result |
| --- | --- |
| Scala/Spinal tests | 35 suites, 81/81 passed |
| Python repository gates | 362/362 passed |
| package, port, lint, Yosys, publish gates | passed; lint 728 exact signatures and clean closure |
| Chiplab `func/func_lab19` with NEMU DiffTest | syscall end; 126,136 instructions; 776,232 clocks; IPC 0.162498 |
| Vivado 2023.2 synthesis | 0 synthesis errors; 0 critical synthesis warnings; DCP/reports generated |

## Compliance and limits

Only Scala/SpinalHDL source and generated-artifact contracts changed.  No
handwritten Verilog, timing exception, simulator shortcut, or workload-specific
behavior was added.  The remote FPGA evaluation skill is unavailable, so no
real-board speedup claim is made and the required three board runs remain
pending.
