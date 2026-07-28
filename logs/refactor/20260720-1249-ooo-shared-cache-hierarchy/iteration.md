# 20260720-1249 OoO Shared Cache Hierarchy

## Scope

Add the four-slot L1 instruction path and make the existing 64-byte L2 genuinely
shared by L1I and L1D without introducing a second backend integration path.
The official scalar `core_top` remains unchanged.

## Implementation

- Added `OooL1InstructionCache`, a two-way 8-KiB read-only L1I returning four
  32-bit instructions from a 16-byte fetch group.
- Added redirect kill semantics: stale fetch responses are suppressed while an
  accepted refill still installs its line.
- Added `OooSharedCacheHierarchy` with dirty L1D writeback priority, alternating
  I/D read arbitration, and read-owner locking across all eight return beats.
- Evolved the existing `OooBackendWithDataCache` wrapper to instantiate the
  shared hierarchy and expose instruction request/response/kill ports. No second
  backend datapath or wrapper is retained.
- Edge-captured invalidates in L1I, L1D, and L2 so a one-cycle request during a
  miss is deferred rather than lost and a held request starts only one pass.
- Added deterministic generators, a Vivado synthesis Tcl entry point, directed
  simulations, and elaboration contracts.

## ysyx reference

The `ysyx-workbench` `la32r-linux` sources use four-wide fetch, 64-byte lines,
2x64-set L1I/L1D, 2x512-set L2, four MSHRs, and a cache-id bit that distinguishes
instruction and data refill clients. This round adopts the geometry and identity
routing. Multiple outstanding misses remain the next round because the current
Spinal L2 controller is blocking.

## Behavioral verification

Final WSL2 run after the shared hierarchy replaced the data-only wrapper:

```text
sbt -batch test
63 tests, 31 suites, 63 passed, 0 failed
```

The simultaneous same-line I/D test accepts both L1 requests, services one
external 64-byte refill, returns the data word to its ROB/pdst, returns the four
instruction words to the fetch client, and observes no second memory read.

## Vivado 2023.2

Configuration:

- device `xc7a200tfbg676-2`;
- clock `ooo_clk`, 10.000 ns;
- `synth_design -flatten_hierarchy rebuilt`;
- 0 errors and 0 critical warnings in both completed runs.

| Metric | Shared cache | Backend + shared cache |
| --- | ---: | ---: |
| LUT | 5,048 | 61,809 |
| FF | 4,850 | 27,593 |
| RAMB36 | 42 | 42 |
| RAMB18 | 12 | 12 |
| DSP48E1 | 0 | 4 |
| WNS | +2.787 ns | -0.998 ns |
| TNS | 0.000 ns | -142.976 ns |
| Failing endpoints | 0 | 1,043 |

The integrated worst path is unchanged: FreeList `freeBits_15` to RegisterMap
`ready_23`, 10.847 ns data delay with 9.081 ns routing. The shared-cache-only
top meets 100 MHz; the backend-integrated top still does not.

Artifact hashes:

- shared RTL `683C0D306CE3A5F79D83F71BFB3350A6A6756DEDC8DE234EBF056709FF9AD56E`;
- shared DCP `64A9D09B9F0C68226D2F0104B096F78386146741DE759ACA6F46121CA5D1F51C`;
- integrated RTL `EB4904B1F5AC21E0E14CFCC3454B6019EFD2290C3FF96F3F808A036EA126691D`;
- integrated DCP `78CD12494D24439D4937DD69B894A86EB65B4418282374AAAC5D3266C5B59263`.

## Assessment

This round is accepted as an architectural performance milestone: instruction
and data misses now share the synthesized L2, an L1I hit supplies four slots,
and integration preserves the improved backend timing. It is not an official
program-speedup claim because frontend/MMU/AXI/SoC integration and board tests
remain open.

## Compliance and limits

- All design RTL originates from Scala/SpinalHDL.
- Generated Verilog and Vivado products remain ignored build artifacts.
- No hand-written Verilog was added.
- The remote FPGA evaluation skill is unavailable in this tool set, so no board
  result is claimed.
