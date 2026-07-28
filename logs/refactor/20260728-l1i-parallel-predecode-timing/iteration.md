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
- hash-verified evidence: `${FPGA_CLIENT_HOME}/results/20260728-112440-86fe59d9`.

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

## Complete-SoC timing and board evidence

Exact evaluated commit: `da71fd32e0db3d13f1964895bbafeb5d2e5af412`.

- locked build workspace: `${FPGA_WORK_ROOT}/job-3019588010`;
- package: `${FPGA_ARTIFACT_ROOT}/da71fd3-perf20-l1i-parallel-predecode-100mhz-v1.fpgajob`;
- package SHA-256: `bfe51c269e939588698f1f1de52f73bfa74f0d34904c7cdaa594296e243f99fa`;
- Vivado 2023.2 implementation and `write_bitstream`: complete;
- target/actual CPU clock: `100/100.000000 MHz`;
- routed WNS/TNS: `+0.036678/0.000000 ns`, `timing_met=1`;
- routed hold WHS/THS: `+0.049/0.000 ns`;
- DRC: 0 Errors, 26 Warnings.

Three strictly serialized real `perf20` evaluations used the same package:

| Run | Job ID | Result | `soc_count` | Time at 100 MHz |
| --- | --- | --- | ---: | ---: |
| 1 | `20260728-125651-a8fa17a8` | 20/20 passed | 74,446,749 | 0.74446749 s |
| 2 | `20260728-130020-6b290214` | 20/20 passed | 74,467,075 | 0.74467075 s |
| 3 | `20260728-130312-ddaf3a7a` | 20/20 passed | 74,446,699 | 0.74446699 s |

All runs passed programming and board/VIO testing. For every run, all eight returned artifacts
were downloaded and matched `artifacts_sha256`; evidence is under
`${FPGA_CLIENT_HOME}/results/<Job ID>`. `FPGA_CLIENT_HOME`, `FPGA_WORK_ROOT` and
`FPGA_ARTIFACT_ROOT` are local storage roots and may point anywhere after migration. The decisive
minimum is 74,446,699 cycles. This is
620,197 cycles (0.84%) slower than the `724b808` minimum of 73,826,502, so the change establishes
100 MHz timing closure and functional correctness but is not a performance improvement. The next
iteration must recover the scheduler-window cycle cost while preserving this timing margin.
