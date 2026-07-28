# Ysyx-style circular physical-register FreeList

Date: 2026-07-21

## Objective

Shorten the FreeList-to-RegisterMap rename path and remove dead bitmap-facing
interface fields while preserving four-issue, three-commit rename/flush behavior.

## Design

The bitmap priority encoder was replaced with a 63-entry circular queue of
physical-register numbers, following the ysyx `FreeList` organization.  The
queue tracks three independent pointers:

- `headPtr`: speculative rename consumption;
- `architecturalHeadPtr`: committed allocation frontier used by flush;
- `tailPtr`: recycled old physical registers written at commit.

`freeCount` and `architecturalFreeCount` keep speculative and committed queue
occupancy separate.  Flush restores only `headPtr/freeCount` to the committed
frontier.  Commit confirms architectural allocations and appends non-zero old
physical registers.  Release writes are explicitly disabled during flush so a
same-cycle stale commit cannot mutate the recycled queue.  The backend also
filters `rd == 0` before confirming a physical destination.

The former `freeCount` output had no consumer and was removed.  The FreeList's
`architecturalMappings` input is no longer required because flush restores the
architectural head instead of reconstructing a bitmap.  The architectural
mapping output of `OooRegisterMap` remains because the PRF debug path still
consumes it.

## Results

| Metric | Previous `1483ef0` | Candidate | Delta |
| --- | ---: | ---: | ---: |
| LUT | 71,071 | 69,787 | -1,284 (-1.81%) |
| FF | 34,620 | 34,978 | +358 |
| WNS | -1.202 ns | -0.737 ns | +0.465 ns |
| TNS | -906.053 ns | -819.826 ns | +86.227 ns |
| Failing endpoints | 2,644 | 2,457 | -187 |
| RAMB36 / RAMB18 / DSP | 42 / 12 / 4 | 42 / 12 / 4 | unchanged |

Generated RTL SHA-256:
`54dea2310d5e04cf4628558526cc14004ca7b0f628320e4d7780c3efb25c61a3`.

The worst path is now LSQ `loads_7_virtualAddress` to ROB
`exception_badVAddrValid` CE, with 10.392 ns data delay.  Standalone 100 MHz
timing remains open.

## Evidence

| Check | Result |
| --- | --- |
| Scala/Spinal tests | 35 suites, 83/83 passed |
| Python repository gates | 362/362 passed |
| package, port, lint, Yosys, publish gates | passed; lint 738 exact signatures and clean closure |
| Chiplab `func/func_lab19` with NEMU DiffTest | syscall end; 126,136 instructions; 776,232 clocks; IPC 0.162498 |
| Vivado 2023.2 synthesis | 0 synthesis errors; 0 critical synthesis warnings; DCP/reports generated |

## Compliance and limits

Only Scala/SpinalHDL source and Scala tests changed.  No handwritten Verilog,
timing exception, simulator shortcut, or workload-specific behavior was added.
The remote FPGA evaluation skill is unavailable, so no real-board speedup claim
is made and the required three board runs remain pending.
