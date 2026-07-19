# OoO 64-Byte Data Cache Hierarchy

The OoO memory path now contains a two-way 8-KiB L1 data cache and a two-way
64-KiB L2 cache. Both levels use 64-byte lines and connect through eight 64-bit
refill beats, matching the line geometry used by the `la32r-linux` ysyx design.

## Structure

- `OooL1DataCache`: blocking, write-back, write-allocate L1D controller.
- `OooL2Cache`: blocking, write-back, write-allocate L2 controller.
- `OooDataCacheHierarchy`: connects L1D refill/writeback traffic to L2.
- `OooBackendWithDataCache`: connects the ordered LSQ cache boundary to L1D/L2.
- `OooCacheArray`: synchronous tag/data storage inferred as FPGA block RAM.

The external memory contract carries one aligned 64-byte request and eight
64-bit response beats. L1 miss responses retain the original ROB pointer and
physical destination register. A branch recovery does not cancel an accepted
cache transaction; the LSQ rejects the resulting stale response by full ROB
pointer, while stores cannot enter the cache before ordered commit.

## Current invariants

- A dirty L1D victim is accepted by L2 before the replacement refill starts.
- A dirty L2 victim is accepted by external memory before replacement install.
- Line read and write requests remain stable while the receiver applies
  backpressure.
- Refill beats may arrive in any order; installation occurs after all eight
  beat indices have been observed.
- Byte-masked CPU stores merge into the selected 32-bit word and mark the line
  dirty.
- L2 preserves the originating L1 MSHR id on returned beats.
- Cache arrays invalidate every set after reset before reporting idle.

## Measured standalone synthesis

Vivado 2023.2, `xc7a200tfbg676-2`, 10.000 ns clock:

The clean-snapshot reproduction commands, reports, and artifact hashes are
recorded in `docs/ooo-vivado-baseline-eb34990.md`.

| Top | LUT | FF | RAMB36 | RAMB18 | DSP | WNS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `ooo_data_cache_hierarchy` | 4,315 | 3,975 | 28 | 8 | 0 | +3.002 ns |
| `ooo_backend_with_data_cache` | 57,964 | 24,069 | 28 | 8 | 4 | -1.891 ns |

The combined critical path remains the backend IQ enqueue-ready to source-ready
wakeup path. Connecting the cache hierarchy did not worsen WNS or TNS relative
to the preceding standalone backend result.

## Deliberate next steps

This is not yet the final competition memory system. The following work remains:

1. Replace the one-miss blocking controller with the existing four-entry MSHR
   contract and support merged misses.
2. Add L1I and arbitration between L1I/L1D and the shared L2.
3. Connect address translation, uncached accesses, CACOP, LL/SC, and bus errors.
4. Bridge the line interface to the SoC AXI3 master and validate burst ordering.
5. Integrate frontend, CSR/TLB, official top-level IO, and full functional tests.

Only Scala/SpinalHDL sources generate the RTL; no hand-written Verilog is added
by this hierarchy.
