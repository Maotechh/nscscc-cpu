# H03/F01 timing localization diagnostic

Date: 2026-08-05

## Scope

This iteration retains the IPC-oriented frontend/cache work while reducing the
100 MHz full-SoC critical-path cost.  The evaluated source commit is
`88657fd26e73a2dd717c0ce23ec53cc99b8cfc30`; its published generated RTL has
SHA-256
`da0bb088cad7a56e40a68cc4d20951de431384404dd729b4bd5435a93555b268`.

The timing changes are intentionally local:

- disable the low-return W01/E02 shortcuts;
- register the L1I confirmed-hit response boundary;
- register straight-line translation turnover;
- remove the production LSU port's unnecessary completion-valid dependency and
  route PRELD through the ALU path;
- consume the registered LSQ epoch qualification in the backend;
- remove the redundant FreeList allocation-ready term under the fixed
  63-physical-register/32-ROB-entry invariant;
- store the BTB static direction bit at update time instead of comparing the
  full target and PC on the read path.

No platform interface or handwritten Verilog was added.  The generated RTL was
published from the SpinalHDL source.

## Local verification

`make cpu-check` passed before implementation:

- Scala/Spinal tests: 198/198;
- Python and locked contracts: 364/364;
- focused predictor, frontend, execution, backend, LSQ, and ROB suites all
  passed;
- generated-RTL port, lint, Yosys, and publication checks passed.

These gates establish the tested RTL semantics; they do not compensate for a
negative routed setup result.

## Complete-SoC implementation

The locked Chiplab input is
`c398d274812f164d387146fa7d8f612a4a1296d9`, using Vivado 2023.2 and the
`xc7a200tfbg676-2` performance SoC at an actual 100.000000 MHz CPU clock.

- implementation and bitstream generation: complete;
- routed setup WNS/TNS: `-0.168585/-15.878564 ns`;
- routed hold WHS/THS: `+0.052/0.000 ns`;
- routed DRC: 0 Errors;
- LUT/FF/BRAM/DSP: 88,595 / 45,710 / 54 / 8;
- bitstream SHA-256:
  `a73f708bc6d2ce273eb70a8eccb827ff8e911678fc883227441b80bb6c0c7717`.

The setup violation makes this a diagnostic implementation, not timing closure
or a release candidate.

## Team-board diagnostic

LabAgent package
`b21d3e631a2ca2b01c3fc8343586477d2c5546e6312ed36784c95115e480873e`
was evaluated as job `20260805-070709-5f1728a1`.  The production
`nscscc-system-reset-v1` protocol programmed the board successfully, observed
DDR ready, and ran both repetitions of all 20 performance programs.  The
terminal verdict was `failed`:

| Index | Program | Result |
| ---: | --- | --- |
| 8 | `sha` | both repetitions timed out |
| 17 | `lookup_table` | both repetitions timed out |

The other 18 selected rows passed.  Against the previously passed
`758181a01c5bb53156157bc7946bc37d6057f3ec` board job
`20260804-182327-8f1c8193`, their matched CPU-count sum changed from
63,852,061 to 45,595,375 cycles (`-28.592164%`).  This strongly motivates
preserving the performance work for repair, but it is not a valid complete
perf20 result: the two timeouts prevent a total-cycle/score comparison, and the
single board experiment cannot distinguish an RTL defect from the known setup
violation.  `stringsearch` also regressed by 37.808458% among the passing rows
and needs separate attribution.

Hash-verified local evidence is retained outside the repository at
`build/board-jobs/cpu_88657fd26e73_perf20/`, including both-run CSV data,
programming and board summaries, the exact Vivado metrics, package, and terminal
result.

## Disposition

Keep the source history as a high-value but unaccepted candidate.  The next
iteration must recover nonnegative setup slack and reproduce 20/20 on the board
before promotion.  Core renaming remains deferred until a candidate has timing
closure, complete board correctness, and finalized evidence.
