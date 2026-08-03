# Chiplab c398 CPU compatibility closure

## Scope

This record owns the CPU/integration work required by the production Chiplab
migration from the historical `68c20a5...` line to
`c398d274812f164d387146fa7d8f612a4a1296d9`. It is intentionally separate from
`logs/refactor/20260803-dbar-ibar-linux-semantics/`, which owns memory epochs,
barrier quiescence, cache maintenance, and the Linux barrier milestone.

The latest tested CPU contains both lines of development. Therefore its board
and simulation results prove the combined candidate is compatible with c398;
they do not attribute the result to DBAR/IBAR and are not an A/B isolation of
the timer reset change.

## Platform identity and static impact

- Production CI template: `6915882af5c8d3a0c856f570cb914920a3e5ff99`.
- Required Chiplab: `c398d274812f164d387146fa7d8f612a4a1296d9`, branch
  `nscscc2026`.
- Student CPU gitlink expected by c398:
  `aa3bde1f3e720e71c2c78d6b81930d797b810149`.
- The public CPU interface and `IP/myCPU` contents are not changed by the
  `68c20a5...` to c398 platform diff.
- Relevant platform differences are complete-system versus CPU/confreg-local
  reset, AXI-delay LFSR seed/reload behavior, the VIO run protocol, timing
  policy, and one performance workload image. They can expose CPU reset and AXI
  assumptions but do not redefine architectural state.

The old local 68c worktree was removed after its reusable LA32 GCC 8.3, NEMU,
QEMU, and picolibc snapshot was copied into the ignored official-manual path
`chiplab/toolchains/`. The c398 checkout is now an independent clean clone named
`chiplab/`; no tracked platform source, Tcl, XCI, or simulator source was
carried from 68c. The old 100 MHz `clk_pll.xci` edit is replaced by the root
parameterized Vivado flow rather than copied across platform revisions.

## CPU reset compatibility fix

The pre-fix candidate `2301dde1ee0622e27b2bbaaf609942b56ca5f764` had a real
architectural reset defect: `ESTAT.IS[11]`, most of `TCFG`, and `TVAL` were not
reset. Commit `1c331323e77bd927c61390f07d629efe098da1dd` resets the complete
timer interrupt state and adds CSR-level plus ROB/front-end acceptance tests.
This is an unconditional correctness fix, not a c398-specific workaround or a
performance trade-off.

The observed board value `0x30000030` is the function-suite progress marker
after n48 and before completion of n49, the timer-interrupt exception test; it
is not a CPU PC. The earlier observation used a performance-mode bitstream with
a function image, so it remains a cross-mode diagnostic rather than clean
function A/B evidence.

## Evidence

The main CPU `d9bab16ef46540eb3348b0781afc4d0949f28adc` already established
baseline c398 compatibility in official CI pipelines 590 and 1421: both passed
func58 58/58 and perf20 20/20. The two submissions had identical RTL and
implementation payloads; their score variation is runtime noise, not an RTL
change.

For the repaired latest line, behavioral source commit
`8594150feb652bd3ef137995858cb9eb5f884580` generated RTL SHA-256
`434a16ea967b4af20c57ca91f6ed407218ccce1bbeeb4440a37e54af2567a924`.
Local c398 `func_lab19` with AXI seed `5570815` passed with live NEMU DiffTest:
it reached the test-end PC, ended by syscall, executed 139,658 instructions in
565,868 cycles, and reported no DiffTest mismatch. The captured terminal log is
`build/logs/chiplab-c398-func_lab19-seed5570815.log`, SHA-256
`2aa7d282ddfe4679647999d23b39d8c18909301ee692a9e76702eb3174357fc6`.

The clean c398 function package then passed team-board LabAgent job
`20260803-132008-97f48faa`. Seeds `F0`, `FF`, and `A5` each reached
`3A00003A` with both indicators asserted. The package SHA-256 is
`93378d04f3fa8519ecc03c63de168f556e1366403185a4547f9a8c191bad2b6d`;
the downloaded `result.json` SHA-256 is
`9374523af22d43d54f3c8353b1abd1c170668b1cce75c3fcf3c14ebef7a00cdb`.
This closes the earlier n49 symptom for this repaired candidate at the function
build's actual 32.726797 MHz clock.

## Remaining boundaries

- The current c398 100 MHz performance implementation has setup WNS
  `-0.225 ns`; it is diagnostic and must not be programmed or scored as a
  timing-closed perf candidate.
- The func pass is not 100 MHz evidence and does not prove Linux boot.
- Linux UART/shell closure remains owned by the DBAR/IBAR and subsequent
  CACOP/CPUCFG/LL-SC work.
- Any future Chiplab or CI-template revision requires a new compatibility
  record; evidence from 68c and c398 must not be merged.
