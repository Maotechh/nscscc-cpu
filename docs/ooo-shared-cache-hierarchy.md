# OoO Shared L1I/L1D/L2 Hierarchy

The active OoO backend wrapper contains a two-way 8-KiB L1 instruction cache, a
two-way 8-KiB L1 data cache, and one shared two-way 64-KiB L2. Every level uses
64-byte lines and eight 64-bit refill beats.

## Reference alignment

The `ysyx-workbench` `la32r-linux` reference uses the same core geometry:

- four-instruction fetch groups;
- two-way, 64-set L1I and L1D caches;
- two-way, 512-set L2 cache;
- 64-byte cache lines;
- four MSHRs carrying a one-bit I-cache/D-cache identity.

This implementation preserves the I/D identity at the current blocking L2
boundary by locking a read owner when L2 accepts a line request and holding it
through the final return beat. The next memory-system iteration will replace
that transaction lock with the existing four-entry MSHR contract.

## L1I contract

`OooL1InstructionCache` returns the 16-byte fetch group containing the requested
physical address as four little-endian 32-bit instructions. The original virtual
and physical addresses are returned with the group so a future instruction
aligner can mask slots preceding an unaligned branch target.

A redirect asserts `instructionKill`. A killed miss continues refilling and
installs the line, but its stale response is suppressed. Redirecting back to the
same line can therefore hit without consuming an old fetch group.

## Shared arbitration

- Dirty L1D writebacks have priority over new reads.
- Simultaneous L1I/L1D read misses alternate using a one-bit preference state.
- The selected source is latched until all eight L2 return beats are consumed.
- L1-local MSHR id zero cannot cross-route between instruction and data clients.
- A same-line simultaneous I/D miss reads external memory once; the second L1
  request hits the newly installed shared L2 line.

## Invalidation

L1I, L1D, and L2 edge-capture invalidate requests. An invalidate arriving while
a controller is busy remains pending, blocks new requests once the controller
becomes idle, and starts exactly one full-array invalidation pass. L1I also kills
the in-flight fetch response. This prevents both lost one-cycle invalidates and
restarting set zero when a request is held high.

The current invalidation operation clears cache contents; dirty data writeback
for architectural data-cache maintenance remains part of CACOP integration.

## Verification

Final WSL2 regression:

```text
sbt -batch test
63 tests, 31 suites, 63 passed, 0 failed
```

Directed tests cover L1I refill/hit/fetch-group selection, redirect kill,
deferred invalidate, and simultaneous same-line I/D misses with response-owner
routing.

Vivado 2023.2 synthesis on `xc7a200tfbg676-2` at 10.000 ns:

| Top | LUT | FF | RAMB36 | RAMB18 | DSP | WNS | TNS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ooo_shared_cache_hierarchy` | 5,048 | 4,850 | 42 | 12 | 0 | +2.787 ns | 0.000 ns |
| `ooo_backend_with_data_cache` | 61,809 | 27,593 | 42 | 12 | 4 | -0.998 ns | -142.976 ns |

Both runs completed with zero errors and zero critical warnings. The integrated
critical path remains the backend FreeList-to-RegisterMap ready path; adding
L1I and shared-L2 arbitration did not worsen WNS or TNS.

Artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| Shared-cache RTL | `683C0D306CE3A5F79D83F71BFB3350A6A6756DEDC8DE234EBF056709FF9AD56E` |
| Shared-cache DCP | `64A9D09B9F0C68226D2F0104B096F78386146741DE759ACA6F46121CA5D1F51C` |
| Backend/shared-cache RTL | `EB4904B1F5AC21E0E14CFCC3454B6019EFD2290C3FF96F3F808A036EA126691D` |
| Backend/shared-cache DCP | `78CD12494D24439D4937DD69B894A86EB65B4418282374AAAC5D3266C5B59263` |

## Remaining integration

The instruction port is exposed at `OooBackendWithDataCache`, but the official
frontend, address translation, AXI3 bridge, and `core_top` do not use it yet.
This hierarchy is therefore synthesis and protocol evidence, not an official
functional or board-performance result.
