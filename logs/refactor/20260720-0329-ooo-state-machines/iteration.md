# OoO state-machine closure and timing boundaries

## Scope

This iteration closes the first behavioral-verification gap in the standalone
four-issue, three-commit backend. It does not switch the official SoC top to the
OoO core and does not claim an official functional or FPGA performance result.

## Correctness changes

- ROB occupancy now advances only when allocation is accepted.
- ROB flush keeps the next-free pointer as the new empty-window base, preventing
  immediate aliasing with delayed completions from the discarded window.
- IQ order tags compact from the selected issue position instead of always
  removing the oldest position.
- Register rename forms the correct `oldPdst` chain for same-cycle WAW groups.
- LSQ ROB-age comparison has an explicit pointer width and no unresolved
  `.resized` expression; older-store forwarding and blocking now synthesize as
  real logic instead of being folded to false.
- External rename ready is gated by ROB, FreeList, and LSQ allocation capacity.
- Non-branch completions no longer rewrite ROB branch recovery fields.

## Timing changes

- LSQ completion is registered before entering the shared completion/ROB path.
  The pipeline accepts one generated LSU completion every cycle and flush clears
  the pending valid bit.
- IQ enqueue ready is registered. One entry is reserved so the one-cycle-old
  ready value cannot overflow the eight-entry queue; immediate flush gating is
  retained.

## Verification

WSL Ubuntu, OpenJDK 17, SpinalHDL 1.14.2, and Verilator 5.020:

```text
sbt -batch test
```

Result: 51 tests in 23 suites, 51 passed, 0 failed.

New directed simulations cover:

- accepted versus merely-ready ROB allocation;
- stale completion rejection after flush and three-wide ordered commit;
- younger-ready IQ issue, selective order compaction, serial-at-head, and the
  registered full boundary;
- same-cycle RAW/WAW rename and ordered commit history;
- store commit isolation, request stability under backpressure, store-to-load
  forwarding, unknown older-store blocking, and stale cache responses.

Vivado 2023.2 standalone synthesis used `xc7a200tfbg676-2`, hierarchy rebuilding,
and a 10.000 ns clock constraint.

| Metric | Baseline `937b4dd` | This iteration | Change |
| --- | ---: | ---: | ---: |
| LUT | 56,785 | 53,239 | -3,546 (-6.24%) |
| FF | 19,976 | 20,115 | +139 (+0.70%) |
| DSP48E1 | 4 | 4 | 0 |
| WNS | -2.301 ns | -1.891 ns | +0.410 ns |
| TNS | -1175.875 ns | -527.483 ns | +648.392 ns |
| Failing endpoints | 2,614 | 599 | -2,015 |

Synthesis completed with 0 errors and 0 critical warnings. Timing is still not
met at 100 MHz. The new worst path starts at an IQ `enqueueReadyReg` and ends at
another IQ payload source-ready register; the previous direct IQ count feedback
and LSQ-to-ROB completion paths are no longer the worst paths.

Artifacts are Git-ignored under:

```text
spinal/target/ooo-vivado/iter-iq-ready-pipe/
```

- RTL SHA-256: `3B0935609C1DA4C5349073D24C69A951F00C60597BC5BBF6E4A507A277B473B7`
- DCP SHA-256: `EEC5599E0CFE3A147E5762F435EB07191B30CA796FA63B26F37B8806B121784C`

## Remaining work

The official scalar top is unchanged. The next implementation step is the 64-byte
L1D controller and refill/writeback path, followed by L2, L1I/fetch4, MMU/TLB,
LL/SC, cache operations, SoC integration, full functional tests, and three FPGA
measurements.
