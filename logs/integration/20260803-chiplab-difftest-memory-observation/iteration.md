# Chiplab DiffTest memory observation closure

## Scope

This record covers the CPU-side observation path required by Chiplab c398's
NEMU DiffTest adapter for retiring loads and stores. It is separate from the
architectural DBAR/IBAR work in
`logs/refactor/20260803-dbar-ibar-linux-semantics/`: these signals do not change
load/store execution, cache ordering, or synthesized board behavior. They let
the simulation harness reconcile MMIO loads and observe committed stores.

## Failure and root cause

With CPU `8594150feb652bd3ef137995858cb9eb5f884580`, Chiplab
`c398d274812f164d387146fa7d8f612a4a1296d9`, Linux, and AXI seed `5570815`,
NEMU DiffTest stopped after 654 cycles and 16 instructions at PC `0x1c00003c`.
The instruction was a signed byte load from UART LSR address `0x1fe001e5`.
The DUT correctly observed `0x60`, while NEMU retained zero because the CPU
hardwired `DifftestLoadEvent` and `DifftestStoreEvent` to zero.

Chiplab uses a valid peripheral load event to synchronize the reference model
with device data. The official event masks are:

- load: `{2'b0, ll_w, ld_w, ld_hu, ld_h, ld_bu, ld_b}`;
- store: `{4'b0, successful_sc_w, st_w, st_h, st_b}`.

The failure was therefore a CPU simulation-observation defect. It was not
evidence of a Chiplab platform bug and did not establish a hardware load error.
No Chiplab simulator source was modified.

## Implementation

Commit `79c0045923e2a1cc9da2cf07fc5478f9f622e69b` adds an observation-only
bundle from the LSQ through the backend and core to `OooCoreSystem`.

For each commit lane, the LSQ requires a valid queue entry whose ROB pointer
and queue index match the retiring record. Flushes, exceptions, non-retiring
records, and recycled entries suppress the event. Loads report the official
instruction mask plus physical and virtual address. Stores additionally report
aligned write data and byte mask; SC is reported only when it succeeds.

The public `core_top` interface remains 49 ports. The generated RTL SHA-256 is
`8938858750255431d0bd24f90d314332a57ebdc4c64fa3b0c0220c087fe132fc`.

## Verification

- The focused LSQ test checks the UART signed-byte load, address propagation,
  exception/flush/ROB-pointer suppression, and byte-store data/mask encoding.
- The complete LSQ suite passed 18/18 tests.
- The complete Scala test set and 364/364 Python tests passed before the final
  static-mask rewrite; the focused test was rerun after that mechanically
  equivalent rewrite.
- Locked generated-RTL metadata, 49-port, lint, Yosys, and publication gates
  all passed after the final rewrite. No lint waiver was added; the final
  warning count is 877, limited to existing `CMPCONST` and `UNUSEDSIGNAL`
  classes.
- c398 `func/func_lab19`, seed `5570815`, still passed by test-end PC and
  syscall with live NEMU DiffTest: 565,868 cycles, 139,658 instructions, IPC
  0.246803. This is unchanged from the pre-fix result.
- The Linux rerun with the same seed reached its 5,000,004 ns time limit with
  no DiffTest mismatch: 2,499,995 cycles, 1,224,741 instructions, IPC 0.489897.
  UART reached Linux CPU probing and early physical-memory initialization; the
  final sampled DUT PC was `0xa07a9b58`.

The captured pre-fix and post-fix terminal logs are retained under ignored root
`build/logs/`. The post-fix result proves that the original 16-instruction
DiffTest failure is closed and supplies a much deeper Linux simulation
milestone. It does not prove Linux reaches an interactive shell, complete the
DBAR/IBAR architectural acceptance, or replace complete-SoC and board evidence.
