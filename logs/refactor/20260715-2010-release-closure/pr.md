# Draft PR: publish the canonical pure-active-Spinal CPU candidate

Status: **Draft only**. Functional diagnostics pass; strict and release gates do not. Do not merge automatically.

## Iteration

- Iteration: `20260715-2010-release-closure`
- Branch: `refactor/20260715-2010-release-closure`
- Base: `56d74f4b92d85e6403689cbbe4f7b4b460e8f63a`
- Reviewed implementation: `9a29409242bf29436bf553e584b87018fb3f6fa6`
- Log: `logs/refactor/20260715-2010-release-closure/`

## Change and contract

Publish the reproducible self-contained `core_top` at `rtl/mycpu_top.v`, the path consumed by the locked FPGA overlay. Remove the obsolete `CPUCoreFlat` RTL and inactive simplified Scala drafts. Bind the publication specs, tests, and generated-package checks to the canonical path. The public 49-port/reset contract and locked source/tool versions are unchanged; the committed CPU package changes from a nonfunctional flat draft to the pure-active-Spinal candidate. The locked openLA500 support license/header contract is unchanged.

## Verification

- Locked Scala: 4/4 PASS; generation: 2/2 reproducible.
- Port, publication, Yosys hierarchy/check, candidate closure, typed AXI, and replacement reachability: PASS.
- Clean Linux automation: 390/390 PASS, zero skip.
- func58: 58/58 functional PASS, live DiffTest, no mismatch; strict gate FAIL on 405 compile warnings.
- func81: score 81, live DiffTest, no mismatch; strict gate FAIL on the same 40 DUT and 365 official-environment warnings.
- Required lint: FAIL. The exact 73-warning aggregate suppression closes diagnostically but does not satisfy the repository's individual waiver policy.
- External Claude review: unavailable because `GEEKPIE_CLAUDE_API_KEY` is absent; local fallback has open blockers.

## Missing release evidence

Random DiffTest is blocked by an empty locked vector set. perf20, U-Boot, Linux, Vivado 2023.2 implementation/timing/resource/bitstream, FPGA hardware, and the LACC-on release matrix are not executed. The active official 32-entry predictor also conflicts with the completion contract's historical 64-entry target.

## Risk, resource impact, and rollback

No Fmax/LUT/FF/BRAM delta is available. Six warning-backed compatibility/behavior debts remain documented. Revert the implementation and evidence commits to restore the prior reference-only publication layout; the original dirty worktrees and stable branch remain untouched.
