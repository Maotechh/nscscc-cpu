# 20260715 core_top exact lint waiver closure

## Goal and base

Introduce a fail-closed whole-core lint policy for the default ECHO
OpenLA500 profile. The policy must audit the complete Verilator warning set
before applying any suppression, and it must bind the reviewed set to the
packaged SpinalHDL RTL hash, the local environment profile, and a canonical
warning-signature hash.

- ECHO source head during this iteration: bb05067b1af649bf105e5d57e06690258a329622
- official behavioral source: aa3bde1f3e720e71c2c78d6b81930d797b810149
- packaged RTL input: ded57a4a2b494e5342481a2d87e5b286ebb703bedde8e79df3fe299894dc4cad
- environment profile: local (Java/Verilator/Python policy; not a locked gate)
- nested official checkout and chiplab source baseline were not modified

## Changes

- Added reference/core-top-lint-waivers.json.
- Added strict warning parsing and canonical category/message hashing to
  tools/core_top_gate.py.
- The lint gate now runs an unsuppressed -Wall audit first. It accepts the
  warning-induced Verilator exit only when the complete warning set matches
  the waiver count, approved categories, and signature hash.
- A second lint run is then executed with exactly
  -Wno-DECLFILENAME, -Wno-UNUSEDPARAM, and -Wno-UNUSEDSIGNAL.
  Closure requires return code zero, no warning, no skip marker, and no error.
- Any warning drift, RTL hash drift, malformed waiver, unexpected error, or
  failed closure remains a failure and prevents suppression.
- Existing CPU make lint TARGET=core_top now accepts explicit
  CORE_TOP_LINT_PROFILE, CORE_TOP_VERILATOR, and
  CORE_TOP_LINT_WAIVERS variables while retaining the locked profile and
  no-waiver defaults.
- Added focused tests for exact two-pass ordering, warning drift rejection,
  and Makefile opt-in behavior.

## Reviewed warning scope

The unsuppressed package produced 73 warnings:

- 71 UNUSEDSIGNAL: official AXI response/ID compatibility fields, cache and
  TLB reserved fields, CSR/debug observation shell signals, DiffTest-disabled
  observation ports, and official dead pipeline compatibility ports.
- one DECLFILENAME: generated package filename core_top versus the Spinal
  backend module name.
- one UNUSEDPARAM: the contract-preserved TLBNUM top parameter.

The full 73-entry category/message set is represented by
warning_signature_sha256; warning paths and line numbers are intentionally
excluded from the canonical signature so temporary directories do not change
the identity. The waiver is only valid for the exact packaged RTL SHA and
local profile.
## Commands and exits

| command | exit | result |
| --- | --- | --- |
| python3 -m py_compile tools/core_top_gate.py tests/test_core_top_gate.py | 0 | syntax check |
| python3 -m unittest tests.test_core_top_gate | 0 | 32 focused tests passed |
| make test-local LOCAL_TMP_ROOT=/tmp | 0 | 374 Python automation tests passed in 8.433 s |
| make lint TARGET=core_top OUT_DIR=/tmp/nscscc-echo-lint-make-bb05067-02 CORE_TOP_RTL=... CORE_TOP_LINT_PROFILE=local CORE_TOP_LINT_WAIVERS=reference/core-top-lint-waivers.json CORE_TOP_VERILATOR=/usr/local/bin/verilator | 0 | unsuppressed audit matched 73 warnings; closure had zero warnings/errors/skips |
| direct local lint without --waivers | 1 | negative control remained fail-closed on 73 warnings |
| Yosys availability check | 1/not installed | hierarchy/check gate remains environment-blocked |

## Artifacts and hashes

- generated/package input RTL SHA-256:
  ded57a4a2b494e5342481a2d87e5b286ebb703bedde8e79df3fe299894dc4cad
- waiver JSON SHA-256:
  2a4582bf61d12a2e2462d5ddb1283c09b54aa6e46f0b233d64d50f8363f35038
- canonical warning signature SHA-256:
  6cb7110012904a4b0a7648d89815dd23599646f92fa1027255e5b3a352995d37
- Makefile gate summary SHA-256:
  ac96fe7086231c47c63fc84474f1a166eb0c7d99a55391c7c7749c4694dac450
- unsuppressed Verilator log SHA-256:
  1c6163c7092e2356e97bdc2ad51fdefc24745d859affbf734d8a5782f1e74892
- zero-warning closure log SHA-256:
  2d5faf1fe38fcc84b617af81e1d7a7aad305b3c266b8cbef7244e908f3707bf0
- strict negative-control summary SHA-256:
  2e9ab37922f7915d2f1ebeb987fc065fb628bb91b16a66281cd7734067ead127
- evaluator SHA-256 during evidence:
  de3b69dce99ea8a78c4ac0e15f3835ed8d31f861cc2119618a907b3a5eba2a51
## Claim and residual risk

Qualified evidence: the complete packaged default core_top has a reproducible,
exactly reviewed local warning inventory and a zero-warning second-pass closure.
The 49-port contract, TLBNUM=32, package identity, and generated RTL stability
were rechecked by the lint gate.

This does not claim that the warnings are architecturally harmless, nor does
it claim official cycle equivalence, complete functional/random/performance or
Linux/RT-Thread behavior, Yosys hierarchy cleanliness, Vivado timing, or
release readiness. The warning waiver is a bounded compatibility-shell
exception, not a global warning disable. The local profile is not a locked
manifest gate.

## Rollback

Revert the iteration commit on refactor/ECHO and remove only the new waiver
and gate changes. Do not modify the detached official checkout, chiplab
source baseline, kernel, other branches, or existing chiplab dirty files.
