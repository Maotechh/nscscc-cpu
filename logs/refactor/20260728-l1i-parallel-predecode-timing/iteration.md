# L1I parallel predecode and TLBSRCH timing cut

## Motivation

The complete 100 MHz `perf20` build for parent commit
`d82be71df28125dbc22f1e9b33407e6da96571a6` improved routed timing from WNS
`-0.380378 ns` to `-0.047113 ns`, but still had three setup failures. Two path families
remained:

- L1I tag BRAM -> tag compare -> way selection -> branch predecode -> response target register;
- committed CSR write/address forwarding -> management TLB search -> TLBIDX register.

The parent package was evaluated once to separate functional behavior from timing closure:

- package SHA-256: `a86085a475ce757bb7faa07386da19932b1a680d693d3e054b12b7477bd2afbd`;
- Job ID: `20260728-112440-86fe59d9`;
- verdict: `passed`, all 20 `perf20` rows passed;
- total `soc_count`: `74,445,839` (`0.74445839 s` at 100 MHz);
- WNS/TNS: `-0.047113/-0.073832 ns`, `timing_met=0`, advisory warning present;
- hash-verified evidence: `D:\fpga-agent-client\results\20260728-112440-86fe59d9`.

This is about 0.84% slower than the validated `724b808` performance baseline
(`73,826,502` cycles), so the parent is timing progress rather than a performance win.

## Change

- Expose all L1I cache-array way data internally. Decode the selected fetch group and branch facts
  for each way in parallel with tag comparison, then use the hit way only to select an already
  decoded response. The existing response-register edge and hit latency are unchanged.
- Snapshot `csr.io.vppn_out` on the same edge as the existing registered TLBSRCH valid signal.
  Management search therefore receives aligned registered valid/payload without adding an
  architectural cycle.
- Extend the L1I simulation with two same-set cache lines so a hit in the second way must return
  the correct direct-branch instruction, type, target and static prediction facts.

No handwritten Verilog was added. `rtl/mycpu_top.v` is regenerated from the Scala sources and is
locked by the publication and lint metadata.

## Local gates

- Scala: 37 suites, 133/133 tests passed.
- Python: 362/362 tests passed.
- Generated RTL SHA-256: `14874c00bf2a4632ac9792da2234286d4f1ac05140df03b7db90b784d00074f0`.
- Port contract: passed.
- Yosys structural closure: passed.
- Verilator exact lint: passed; 849 reviewed warnings, only `CMPCONST` and `UNUSEDSIGNAL`.
- Publication consistency: passed.
- Standalone Vivado 2023.2 at 100 MHz: WNS `+0.419 ns`, TNS `0`, 0 failing endpoints.

Targeted synthesized paths confirm that the intended boundaries remain after optimization:

- L1I tag BRAM -> response predecode target: worst slack `+2.943 ns`, 8 logic levels,
  `CARRY4=2`;
- registered TLBSRCH VPPN -> TLBIDX: worst relevant index-bit slack `+5.120 ns`, 7 logic levels.

Standalone synthesis does not establish complete-SoC timing closure. The next decisive gate is an
exact committed `perf20@100MHz` Vivado implementation with numeric routed WNS, complete
implementation and zero DRC errors. Board evaluation is allowed only after routed WNS is
nonnegative for this timing-closure iteration.
