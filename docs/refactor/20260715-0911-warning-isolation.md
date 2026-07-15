# 20260715 warning-isolation diagnostic

## Goal and base

Attempt a controlled current-ECHO func_lab19 run with trace comparison and
simulator trace output disabled, to distinguish official environment warnings
from trace-only build noise. This is diagnostic only and does not alter the
default profile or add warning waivers.

- ECHO source: 9d33ef09360632debf7cac38eebac8f143a1a3d1
- root Makefile: 8f29ea2
- package source: ded57a4a2b494e5342481a2d87e5b286ebb703bedde8e79df3fe299894dc4cad
- command used DUMP_WAVEFORM=1 and
  --disable-trace-comp --disable-simu-trace --disable-clk-time --dump-fst
- all generated work was under /tmp or chiplab run_prog/tmp
## Commands and exits

| command | exit | result |
| --- | --- | --- |
| controlled root make sim with trace disabled and FST enabled | 130 | aborted after approximately 7 minutes and 8.3 GB FST growth; no complete summary |
| explicit process interrupt | 130 | stopped only the diagnostic process |
| removal of run_prog/tmp | 0 | removed only files timestamped by this run; no user source/config/Git metadata touched |
| chiplab status after cleanup | 0 | existing config dirty fields and three Vivado journals preserved |

The prior no-waveform current-ECHO run remains the usable smoke evidence:
parser pass with END by Syscall, Reached test end PC, 174059 instructions,
609660 clocks, first_mismatch=null, and a fail-closed 429-warning gate.

## Claim and residual risk

Resource-blocked diagnostic only. This attempt provides no new functional,
warning-reduction, or performance claim. The compile warning gate remains
unclosed at 40 DUT and 389 official-environment warnings. No global warning
suppression was added, and no waveform artifact from the aborted run is kept.

## Rollback

Revert this documentation-only ECHO commit if needed. Chiplab was not
committed or pushed; its pre-existing dirty files remain intentionally
untouched.
