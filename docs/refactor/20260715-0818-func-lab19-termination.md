# 20260715 func_lab19 termination contract

## Goal and base

Resolve the ambiguous good_trap=false observation for the locked
func/func_lab19 smoke case and make its completion oracle case-specific.
A null first_mismatch is never sufficient: the run must prove active
DiffTest, nonzero execution, the expected syscall termination, the simulator
test-end PC, no failure marker, fresh output artifacts, and the existing
compile warning policy.

- ECHO base: 950e7253d5d71acf22880c331426c2e13de84615
- locked chiplab source: a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31
- official CPU source remains detached aa3bde1f3e720e71c2c78d6b81930d797b810149
- no chiplab source, configuration, log, or Git metadata was modified

## Source audit

The locked functional test deliberately does not execute the NEMU trap word.
Its test_finish sequence writes zero to UART_ADDR and later executes
syscall 0x11. DiffManage reports END by Syscall when the NEMU proxy observes
completion, and CpuTestbench separately reports Reached test end PC.

- software/examples/func/func_src/start.S
  - Git blob SHA-1: f31b32d4bac31f0d51ea9068f1bd49f6baea34a7
  - SHA-256: 323a6095e6ae4e2d18f732232232263d418bc68a33f9d1a1905be753973d5cfa
- sims/verilator/testbench/diff_manage.cpp
  - Git blob SHA-1: f106d7ebb397cbb50db57cc80507a3436a5db17c
  - SHA-256: 2094904b431179f10ae36baff561903980e8d5d7bf42da912ffbe0ba493f1c9f
- sims/verilator/testbench/testbench.cpp
  - Git blob SHA-1: 038d3e933e03759d61132825f39567954b52978c
  - SHA-256: bc8f9bb4aa218554be4bf9d9f59871e25f745f21c5632ab1bc125d776e92e78e

UART is part of the exit stimulus for this case, not its pass oracle. Empty or
nonempty UART files cannot replace the DiffTest/syscall/end-PC contract. The
current mutable chiplab func_lab19 trace and uart_output.txt.real are both
stale zero-byte files and were explicitly excluded from evidence.

## Changes

- parse_simulation_log now records termination_expectation,
  termination_mode, and termination_valid.
- Generic callers remain compatible with either HIT GOOD TRAP or
  END by Syscall.
- The locked func_lab19 smoke path explicitly requires end_by_syscall.
  A good-trap-only transcript now fails this case-specific contract.
- A missing or wrong termination marker adds termination_marker to failures
  and a diagnostic excerpt.
- identity_compare requires the syscall termination fields and recomputes the
  parser from the immutable raw simulation command log using the same
  expectation.
- sim_result accepts an explicit case and applies the same syscall expectation
  for func/func_lab19.
- The existing root make sim target forwards TEST through --case; no new Make
  target or automatic-approval rule was added.
- Regression tests cover the good-trap-only negative control and the valid

  syscall completion path.
## Historical diagnostic interpretation

The committed 20260714-1907-lacc-spinal official-smoke summary is a historical
diagnostic, not a result for the current ECHO head. It records 174069
instructions, 609803 clocks, good_trap=false, end_by_syscall=true,
reached_test_end=true, and first_mismatch=null. Its overall gate remained
FAIL because 244 DUT and 364 official-environment warnings had no reviewed
waiver. This confirms that good_trap=false was not the failure cause and that
warning policy is independent of functional completion.

Historical official-smoke JSON SHA-256:
10f1a9a05bfc66e91920308403e3e3e99adef612f4af9c99d79e5dd44f4351a8

## Commands and exits

| command | exit | result |
| --- | --- | --- |
| exact fetch of consolidated ref | 0 | remote remained 923eb73 and was already an ECHO ancestor |
| locked Git blob/hash audit for start.S, diff_manage.cpp, and testbench.cpp | 0 | syscall, UART write, END by Syscall, and test-end PC provenance recorded |
| first py_compile/focused test attempt | 1 | fallback edit preserved literal newline escapes in two fixture lines |
| second focused test attempt | 1 | fixture helper had lost the raw simulation-log write; identity SHA check failed closed |
| final py_compile | 0 | refactor, identity comparator, sim_result, and three test modules valid |
| focused SimulationResultTests, SimulationParserTests, and IdentityCompareTests | 0 | 35 tests passed in 52.820 s |
| make test-local LOCAL_TMP_ROOT=/tmp | 0 | 376 tests passed in 8.565 s |
| root make -n sim dry run | 2 | recursive Make execution under -n lacked dry-run artifacts; exposed and corrected a PIPESTATUS escaping regression; no simulation result claimed |
| fresh current-ECHO func_lab19 simulation | not run | this iteration changes and verifies the oracle contract only |

## Artifact hashes

- tools/refactor.py:
  7663c95687c5d7e467db364d951f6e9aa974e860f9f8bc4f710ddc14829b0342
- tools/identity_compare.py:
  6819f4bde5e996b0db847699568f6eaceb9e985aca6f4333415986afa9020a4e
- tests/test_refactor.py:
  01a7c1b0c96fa50c4e144b548acc1feb86b19ae3f69326516012da760152d210
- tests/test_identity_compare.py:
  3ea5327f302d88904cdeb42061115db475eacb7705148c5f522d87db4ac6d564
- tools/sim_result.py:
  ab38e751ad730654b930d352082612aafa6b110cc41e242f584ee1f3e79edd8f
- tests/test_sim_result.py:
  88a26b43d2357d428541bc31dd8a2e8793236180dcc9bcda7b0692342ce3a0d4
- root Makefile during evidence:
  db7c2b256a8126388890671095df31687fe25f3e467cc534a891a029c2c41d60
## Claim and residual risk

Qualified evidence: the completion oracle now matches the locked func_lab19
software and chiplab termination implementation. good_trap=false is expected
when END by Syscall and Reached test end PC are present. A null mismatch,
zero process exit, UART content, or good-trap text alone cannot pass the
locked smoke contract.

This does not claim a current-ECHO func_lab19 functional pass. A fresh staged
simulation must still bind the generated RTL, fresh compile/simulation logs,
active DiffTest markers, syscall termination, test-end PC, nonzero counts,
and the compile warning policy. The 58/81 functional collection, random
DiffTest, performance, Linux, RT-Thread, Yosys, and Vivado gates remain open.

## Rollback

Revert this ECHO iteration commit. Do not alter the locked chiplab source,
official nested myCPU, kernel, other branches, or existing mutable chiplab
files.
