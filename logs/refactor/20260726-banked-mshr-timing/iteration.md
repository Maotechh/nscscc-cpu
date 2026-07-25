# Banked MSHR timing refinement

Date: 2026-07-26

## Objective

Reduce the register, LUT, and routing cost of the four-entry L1D/L2 MSHR
implementation without giving up four independent miss identities, same-line
merge, hit-under-miss, interleaved refill, or the 64-byte line contract. Keep the
fresh Chiplab `func_lab19` cycle count unchanged and recover positive standalone
100 MHz timing before complete-SoC evaluation.

## Starting point

Commit `d7c484b4263f86371da06859d6aeecfc5f744ebb` implemented the first complete
nonblocking path. It passed 110 Scala/Spinal/Verilator tests, 362 Python gates,
fresh NEMU DiffTest, and standalone 100 MHz synthesis. That implementation used
one 512-bit refill/victim register structure per MSHR and required 88,514 LUT /
49,150 FF in the standalone `core_top`.

A complete-SoC implementation of that committed revision reached WNS
`-2.344203 ns`, TNS `-14887.989 ns`, 98,148 slice LUT, and 61,718 registers.
This result established that standalone closure did not carry through the
official SoC placement and routing. Two remote functional jobs reached the lab
but ended as infrastructure errors with `There is no current hw_target`; they
provide no CPU functional or performance verdict.

## Final structure

Both L1D and L2 replace per-MSHR 512-bit line registers with eight shallow
64-bit memories indexed by the four MSHR identities. Metadata remains in the
MSHR records. Clean misses retain four-way concurrency; dirty victims share one
global line buffer and therefore serialize only the writeback portion.

L2 cache hits first enter a registered full-line capture. The following cycle
writes the eight shallow banks, and a one-entry output register returns the hit
beats with consume-and-replace behavior. External AXI refill beats remain on the
direct streamed response path, so critical-word-first memory traffic does not
gain another stage.

L1D uses a one-entry elastic merged-store buffer containing MSHR identity,
6-bit line offset, byte mask, and 32-bit data. It can consume the old entry and
capture a new store in the same cycle. The buffer breaks the LSQ request to
refill-bank path and handles the final-refill/store race by delaying install
until the buffered update has been applied.

## Timing exploration

| Candidate | LUT / FF | 100 MHz WNS | Result |
| --- | ---: | ---: | --- |
| Shallow L1D/L2 banks, no response isolation | 78,885 / 41,985 | `-1.972 ns` | Area target met, BRAM/cache response path too long |
| L1D refill stage plus fully elastic L2 output | 79,026 / 42,051 | `-2.037 ns` | `func_lab19` regressed to 544,850 cycles; rejected |
| L2 hit-only output stage without registered capture | 78,821 / 42,042 | `-2.455 ns` | Tag BRAM still drove the downstream refill path |
| Registered L2 hit capture | 79,146 / 42,573 | `-0.893 ns` | L2 path improved; LSQ merged-store path became critical |
| L2 full output register | 79,002 / 42,114 | `+0.137 ns` | Timing passed but added an avoidable external-refill stage |
| Final hit capture plus L1D merged-store buffer | 78,776 / 42,609 | `+0.137 ns` | Kept direct external refill and recovered the original cycle count |

The final candidate's worst setup path is no longer in either MSHR line bank.
It ends in the existing LSQ store data/reset network, with 0 failing endpoints
and TNS `0 ns` under the standalone 10 ns clock.

## Validation

| Check | Result |
| --- | --- |
| Scala/Spinal/Verilator full regression | 35 suites, 110/110 passed |
| Python repository gates | 362/362 passed |
| Directed memory regression | 13/13 passed |
| package/port/lint/Yosys/publish | passed; 49 ports; generated RTL SHA-256 `81b771cff7d57a6bb6b24126f867050f58e53cc08382ddf96155074fb0ba511f` |
| Exact complete-top lint | 770 warnings, only `UNUSEDSIGNAL`/`CMPCONST`; signature `3a42df142f0dc26d89f9571af572ad8d64cedc718352326113faea6650510b7e` |
| Fresh Chiplab `func_lab19` | NEMU DiffTest, syscall, and end PC passed; 139,654 instructions / 538,555 cycles / IPC 0.259312 |
| Standalone Vivado 2023.2 | 100 MHz WNS `+0.137 ns`; TNS `0 ns`; 78,776 LUT / 42,609 FF |

Standalone evidence SHA-256 values are:

- timing: `44d71585fb277ce68039c551e6dc221511ce2158f86b660a40a1b4136697eb0`
- utilization: `7f86db4b071ee1e9f14a674edb71eabfec1233a16d8aabb713f62a287abe8cef`
- DRC: `a80c624178c27e55acf006b50accee53015663f4819e2793b13d0691856ab28d`
- DCP: `1ae1e9885e8db186fe7368ed39ff97b142cf6a247c2d931f4435ed60ceb1d41b`

The standalone DRC contains only unconstrained-top I/O/configuration warnings,
DSP pipeline advisories, and I/O reset-sharing warnings. It has no RTL or
synthesis error. This remains CPU-top evidence, not complete-SoC timing closure.

## Decision and next gate

The refinement preserves all four MSHR identities and the exact 538,555-cycle
local result while reducing the standalone top by 9,738 LUT and 6,541 FF versus
the committed MSHR version. It is therefore retained for complete-SoC synthesis.
Promotion to a board-performance baseline still requires a full committed build,
remote `func58`, and three `perf20` evaluations. Only after that evidence is
available should work proceed to ALU/MUL zero-cycle forwarding and decoupled
store address/data handling.

## Committed complete-SoC evidence

The banked MSHR implementation was committed as
`40a3b53f10918878e135bff8087b2b3ebd0540da` and pushed to
`origin/dev-OoOE`. Its locked `func58` package has SHA-256
`6872fa8c9dbbed8612ee3074b253b51c835da8f34a4b062786685041ef8d3fd4`.
Vivado 2023.2 completed synthesis, placement, routing, bitstream generation,
and DRC with zero errors at the requested 100 MHz. Routed timing did not close:
WNS was `-0.977163 ns` and TNS was `-1228.851318 ns`. This is substantially
better than the first nonblocking MSHR result (`-2.344203 ns` /
`-14887.989258 ns`), but remains a timing failure under the advisory policy.

The routed worst path started at `loadHead_reg[0]` in the LSQ and ended at the
clock enable for `stores_2_byteMask_reg[2]`. It crossed store ordering and
forwarding selection, completion arbitration, `aguReady`, and store-entry
write qualification. The 10.516 ns data path had 14 logic levels and was about
75% routing delay. This identified a control dependency outside the banked
MSHR arrays as the next timing target.

Remote job `20260725-190713-92986670` progressed through preparing and
programming, then ended as `infra_error` with
`ERROR: [Labtoolstcl 44-469] There is no current hw_target.` There is no
programming summary, VIO result, or DUT verdict. It is neither a functional
failure nor a functional pass, and no `perf20` claim can be made from it.

## LSQ exceptional-completion isolation

Normal aligned AGU traffic previously inherited the entire current load and
translation completion arbitration cone through `aguReady`, even though only
a misaligned AGU request needs to emit an immediate completion. A one-entry
narrow exception-completion buffer now captures the ROB pointer, recovery
epoch, destination tag, SC flag, store data, and bad virtual address for ALE.
Aligned AGU requests no longer depend on the completion port. A misaligned
access waits only when this single exceptional entry is occupied; its precise
exception completion is delayed by one cycle and remains ordered with cache and
translation completions.

A directed LSQ collision test presents a cache response and a misaligned store
AGU in the same cycle. It proves that the AGU is accepted, the older load
completion is emitted first, the buffered ALE completion follows with ecode 9
and the original bad address, and no memory request is issued for the invalid
store.

Final local evidence after narrowing the buffer is:

| Check | Result |
| --- | --- |
| Scala/Spinal/Verilator full regression | 35 suites, 111/111 passed |
| Python repository gates | 362/362 passed |
| package/port/lint/Yosys/publish | passed; 49 ports; RTL SHA-256 `0bcecbd36496b0f47faae2a84b4961526c3025c63570cee0315d436d327d68df` |
| Exact complete-top lint | 776 warnings, only `UNUSEDSIGNAL`/`CMPCONST`; signature `55638bf7f6cd6c52948c51210fd291062d62f259aea2b8758d462e59d11dc591` |
| Fresh Chiplab `func_lab19` | NEMU DiffTest, syscall, and end PC passed; 139,654 instructions / 538,555 cycles / IPC 0.259312 |
| Standalone Vivado 2023.2 | 8-thread policy; 100 MHz WNS `+0.359 ns`; TNS `0 ns`; 78,735 LUT / 42,699 FF |

Standalone evidence SHA-256 values are:

- timing: `d09d24394d38a2e603011066d681f3f3330ad98bf944c8482c78e0d1eab8afb5`
- utilization: `d95c3e0b4895e3137d208dbea22fa661ba9cf35071075e00339bf2dced8a1832`
- DRC: `478c71863d693c24c90b07d24fe8327e78f18ba1701fad3c796fcd43c01fe65e`
- DCP: `bb0b2b70330cbf7ad5ddd9c7bd518a634e8e83253fff54794552e8fce0afd743`

The standalone worst path moved to L1I response predecode driving a data-array
enable. The former LSQ path is absent from the top 20 timing paths. The change
adds 90 FF while removing 41 LUT relative to the committed banked MSHR top and
does not change the official local cycle count. A fresh committed complete-SoC
implementation is still required before claiming routed 100 MHz closure.

Vivado host scheduling is restored to the agreed policy:
`general.maxThreads=8`, with `launch_runs -jobs 4` supplied when the caller does
not specify a job count.

## LSQ-isolation complete-SoC result

The LSQ exceptional-completion isolation was committed and pushed as
`7ada9ba51e7e69b5e6c95a45dcf1984a4114a022`. Its locked 100 MHz `func58`
package is `team-7ada9ba-func58-100mhz.fpgajob`, SHA-256
`a02b2b72ba0d3ab53a4cc80f6a1baf6d2328684b2796e467b45329572070101b`.
Vivado 2023.2 completed bitstream generation with zero routed DRC errors. The
final advisory timing metrics are WNS `-0.535200 ns`, TNS `-95.344513 ns`,
90,110 slice LUT, and 55,281 registers. This improves the committed banked MSHR
result by 0.441963 ns WNS and reduces the TNS magnitude by 92.4%, but it is not
100 MHz timing closure.

Every packaged artifact was independently streamed through SHA-256 and matched
the manifest:

- `design.bit`: `4c14380493da8e4f5684d254b14758a6d0c3c495deef69fe37e21681d64b2588`
- `program.bin`: `04e79fe1dcfac195b546cfab52959e03e530d08ba96deedab49cbae65b52501a`
- `probes.ltx`: `cbb0799a601e9c9a69cc594e74faf4c08fe028f1374760137317c037c2f395b8`
- `timing_summary.rpt`: `3da22dc29a6b52fc4637378554165650ce23ffd360453e7621e36d3436501aca`
- `utilization.rpt`: `77fe0b3a91c4875f5fe3468058ef944be6a661980f8957767aad635ca5533310`
- `drc.rpt`: `bce9af260be595c43f36fb11a87ff4fd752ac1356e45302e2eac9941a6a1a9a6`

The routed worst CPU path now starts at `recoveryEpoch_reg[1]`, passes through
ROB completion-wakeup qualification and the port-1 IQ oldest-ready selection,
and ends at `issueAddressUop_1_decoded_immediate_reg[4]`. Its 10.386 ns data
path has 11 logic levels and 8.779 ns (84.5%) routing delay. The former LSQ
`loadHead -> aguReady` path is no longer critical.

Remote `func58` job `20260725-210149-13a43932` used the package hash above and
progressed from queued to programming. It ended as `infra_error` because the
worker again reported `There is no current hw_target`; programming evidence,
VIO output, and a DUT verdict are absent. No `perf20` job was submitted.

## Registered completion-epoch qualification

The completion payload was already registered before ROB validation, but the
comparison between its staged recovery epoch and `currentEpoch` remained
combinational on the next-cycle IQ wakeup path. The comparison result is now a
per-writeback-lane register captured in the same edge as the completion payload.
Thus stale-epoch suppression is preserved and wakeup still appears on the same
next cycle, while `currentEpoch` terminates at this narrow register bank instead
of traversing the IQ selector.

A directed ROB test drives an invalid epoch completion followed by a valid one
without allocating a ROB entry. The invalid completion produces no wakeup
candidate; the valid completion appears exactly one cycle after its input, and
clears on the following cycle. Existing flush, pointer-generation, physical
write, dispatch, and full-core regressions continue to pass.

Current local evidence is:

| Check | Result |
| --- | --- |
| Scala/Spinal/Verilator full regression | 35 suites, 112/112 passed |
| Python repository gates | 362/362 passed |
| package/port/lint/Yosys/publish | passed; 49 ports; RTL SHA-256 `83d1c1ad988a38d7cd27a7194a8dc9f91f2bcd170ba669ceedfbfbd68211711b` |
| Exact complete-top lint | 781 warnings, only `UNUSEDSIGNAL`/`CMPCONST`; signature `5e4fbab6ffdbd2d1438847a3fc27143fa67d35fa3fa2bc09affddedfffc319fb` |
| Fresh Chiplab `func_lab19` | NEMU DiffTest, syscall, and end PC passed; 139,654 instructions / 538,555 cycles / IPC 0.259312 |
| Standalone Vivado 2023.2 | 8-thread policy; 100 MHz WNS `+0.292 ns`; TNS `0 ns`; 78,640 LUT / 42,665 FF |

Standalone evidence SHA-256 values are:

- timing: `7ac5cfcd7e8692f6c11801898705af5b63d2e164b654d15b23c0e6e5ed46af6f`
- utilization: `7bfd331d2e211c68f7d29308b9b4885e2f53cd973535284a910bf227a8bfb40b`
- DRC: `f9eb920e372d8fad611f84029828f8766a1060c05fff3a5e175ff7cc3a4e4164`
- DCP: `48339457e98dd346ba4968ca03a050d1cee5c0c9050fcb1f6d3eb7b5da0201f3`

The targeted recovery-to-IQ path is absent from the standalone top 20. The
new worst path runs from a ROB serializing bit to predictor PHT enables. The
change reduces standalone synthesis by 95 LUT and 34 FF relative to `7ada9ba`
despite the five explicit epoch-valid bits. A committed full-SoC route is the
next decisive timing gate.
