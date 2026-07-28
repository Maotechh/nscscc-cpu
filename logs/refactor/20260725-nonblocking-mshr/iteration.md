# Nonblocking MSHR iteration

Date: 2026-07-25

## Objective

Turn the existing four-ID cache protocol into four real concurrent miss slots.
Allow the LSQ to keep issuing independent safe loads, merge requests to an
in-flight data-cache line, route interleaved refills by MSHR identity, and keep
cache hits progressing while misses wait below L1. Preserve precise exceptions,
store ordering, maintenance, uncached ordering, and the 64-byte line contract.

## Baseline diagnosis

Commit `7b237f0f7b19f9a29f679b0838da53fed3801aee` carried a two-bit `mshrId`,
and `OooSharedReadMshrRouter` could allocate four global identities and route
interleaved return beats. Useful concurrency stopped at that boundary:

- L1I and L1D hard-wired local ID zero and each used one blocking request FSM.
- L2 hard-wired external ID zero and held one pending request/refill.
- The AXI line bridge held one global cached-read context.
- The LSQ retained the oldest issued load as `loadHead` until its response.

The ysyx `la32r-linux` reference uses explicit MSHR records, tagged AXI returns,
same-location conflict checks, and load waiters attached to an in-flight line.
This iteration adopts those boundaries while retaining the local Spinal bundles
and precise ROB response tags.

## Implemented structure

### LSQ issue and completion identity

The load scheduler excludes only entries whose request has already been accepted.
It may therefore select another safe load while older cache requests are pending.
Responses no longer target the current load head: all eight live load entries
compare the full ROB pointer, and only the matching generation may complete. Store
age, partial-overlap, forwarding, committed-store drain, and flush cancellation
rules are unchanged.

### L1 data cache

`OooL1DataCache` owns four `OooL1DataMshr` records and eight compact load waiters.
Each MSHR carries the line/victim identity, dirty victim data, eight refill beats,
refill/error state, and a 64-bit store-byte overlay mask. The refill buffer itself
holds store bytes, avoiding a second 512-bit store-data array per MSHR.

- Loads and stores to an active line merge into that MSHR.
- A same-set, different-line lookup waits until the conflicting install completes.
- Other sets and cache hits continue while misses are active.
- Dirty victims write back before the refill request.
- Interleaved refill beats select their MSHR by returned local ID.
- A load response is selected from the waiter table after the line is installed.
- A store accepted on the same cycle as its refill beat wins for masked bytes.

Maintenance begins only after lookup, response, writeback, and all MSHR/waiter
state drain. No speculative store becomes externally visible before ROB commit.

### Shared router and L2

`OooSharedReadMshrRouter` remains the sole owner of the four global line-read IDs.
It records instruction/data ownership and the client's local ID, rejects unknown
return IDs, and restores the local ID on every response beat.

`OooL2Cache` now uses the restored global ID as one of four `OooL2Mshr` slots.
Different-set lookups and installed-line hits may proceed under a miss; same-set
conflicts serialize. Refill beats stream to the requesting L1 before installation,
and can be arbitrarily interleaved across the four IDs. The independent write path
retains dirty-victim and write-through ordering.

### AXI bridge

Cached line reads use AXI IDs 4 through 7 (`01 ## mshrId`). The bridge keeps active,
half-word, low-word/error, and beat-index state per ID, allowing four outstanding
16-word AXI bursts and interleaved R-channel returns. IDs 2 and 3 remain reserved
for uncached instruction and data reads.

The AR channel has one staging register. A cached high 32-bit word is accepted only
when the 64-bit output register is empty; a low word may arrive while the previous
output drains. This removes downstream cache ready from AXI `rready` without adding
a bubble to the normal low/high burst sequence.

## Area refinement

The first correct version stored a 512-bit store payload and a 512-bit expanded
bit mask in every L1D MSHR. The accepted refinement stores write bytes directly in
the refill buffer and tracks only one bit per line byte. Compared with the preceding
nonblocking version, standalone use changes as follows:

| Hierarchy | Before | Final |
| --- | ---: | ---: |
| Complete `core_top` | 92,477 LUT / 53,009 FF | 88,514 LUT / 49,150 FF |
| L1D | 16,427 LUT / 9,376 FF | 12,792 LUT / 5,529 FF |
| L2 | 6,232 LUT / 6,601 FF | 6,230 LUT / 6,600 FF |

The refinement saves 3,963 LUT and 3,859 FF at the top while preserving the
standalone 100 MHz WNS of `+0.137 ns`.

## Validation

| Check | Result |
| --- | --- |
| Directed MSHR/LSQ/L1D/L2/AXI tests | 4 suites, 27/27 passed |
| Scala/Spinal/Verilator full regression | 35 suites, 110/110 passed |
| Python repository gates | 362/362 passed |
| package/port/lint/Yosys/publish | passed; RTL SHA-256 `f389b02b36a2cdb9e64beb7d5558c26e9ad5ffd954915278a9592bf5625fe77a` |
| Exact complete-top lint | 769 warnings, only `UNUSEDSIGNAL`/`CMPCONST`; signature `f096fdbe49def41936bea8ce6523a0a49e332e06f24b9b0c916e688413093f5c` |
| Fresh locked Chiplab `func_lab19` | NEMU DiffTest, syscall, and end PC passed; 139,647 instructions / 538,555 cycles / IPC 0.259299 |
| Standalone Vivado 2023.2 | synthesis completed; 100 MHz WNS `+0.137 ns`; 88,514 LUT / 49,150 FF |

The Chiplab build deleted `obj_dir/output`, copied the final generated RTL, and
rebuilt Verilator and the testbench. Its copied RTL hash exactly matched the
published hash above. Relative to the committed baseline's 538,742 cycles, this
workload improves by 187 cycles (`0.0347%`). It demonstrates functional progress,
not a decisive FPGA performance gain.

Standalone report SHA-256 values are:

- timing: `5c5604c2d1a44e5d03ab8091fc20cfd7bd3a69276ffc02d4bc2815f2395edabd`
- utilization: `42c02636a5a45f27759fb54dae926371a6dc813251a2e610ee19cdef773591cc`
- DRC: `8b5207f747b6ac59ef03c33999d28f9d0324a27a54c7bf272289bcf429e86b76`
- DCP: `28ae8819fd09a81d113347f704e91a66dac31c63c22cd0249c150048307315c1`

The standalone DRC has only the expected unconstrained-top I/O and DSP pipeline
advisories. This synthesis does not include the official SoC placement, board XDC,
or routing congestion. The candidate is not a 100 MHz timing baseline until a
locked complete-SoC implementation reports non-negative WNS.

## Residual limits and next step

L1I still has one local miss context, although its request uses the shared global
ID pool and can coexist with multiple L1D/L2 misses. L1D accepts one lookup and
returns one load per cycle; L2 has one lookup port and one streamed output beat.
Same-set conflicts intentionally serialize to avoid multi-writer cache-array
hazards. Uncached traffic and line writes remain globally ordered in the AXI bridge.

The local benchmark contains too little independent miss overlap to expose a large
cycle gain. A committed, locked `func58` and three `perf20` board evaluations are
required before promotion. After this MSHR round, the planned performance order is
ALU/MUL zero-cycle forwarding, then decoupled store address/data handling.
