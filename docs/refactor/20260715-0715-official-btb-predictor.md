# 20260715 official BTB predictor correction

## Goal and base

Correct the default predictor profile to the official detached aa3bde1
behavioral source. The historical a158aa8 candidate changed the nominal BTB
parameter to 64 while the official btb.v remains 32 entries. The active
Spinal predictor now uses the official 32-entry geometry and the 5-bit
operate_index for target/counter updates.

- ECHO base commit: c5e4e6d53d368fa148342e3e82305153052c07fa
- official source commit: aa3bde1f3e720e71c2c78d6b81930d797b810149
- official btb.v Git blob SHA-1: e2f6e340c1f4f98ce93493192030c32943935229
- official btb.v SHA-256: 6d540a983075e8ed3a9bd1f791bc4ec14e3b08ff04c4c8f13ae1c0fa8a081bfb
- historical diagnostic source remains a158aa8

## Changes

- CoreConfig and the machine-readable contract now use btbEntries=32.
- OpenLa500Predictor uses a 32-entry BTB, 5-bit replacement/index logic,
  official add/replacement behavior, and index-selected target/counter
  updates.
- The active predictor no longer implements the historical delete enhancement
  or same-PC add reuse. Decode/legacy contracts retain the dead official
  delete_entry port for compatibility.
- Backend wiring now sends DecodeBtbUpdate.index to the predictor.
- Predictor tests cover all 32 entries, index-directed updates, replacement,
  RAS, and non-overlapping 16-entry return-site fill.
- Current predictor/core contract prose explicitly distinguishes aa3 from the
  historical 64-entry a158 candidate.

## Commands and exits

| command | exit | result |
| --- | --- | --- |
| python3 -m json.tool reference/core-contracts.json | 0 | contract JSON valid |
| python3 -I tests/test_core_contract_manifest.py -v | 0 | 8 official-source contract tests passed |
| local SBT scalafmtAll | 0 | formatted predictor sources/tests |
| SBT with local Verilator compatibility flag, first run | 1 | initial standalone delete input warning; no RTL warning waiver added |
| SBT predictor run before test correction | cancelled/1 | mid-test reset path did not converge; JVM stack showed native Verilator eval at the second reset |
| SBT run without SPINAL_VERILATOR_FLAGS | 1 | known Spinal 1.14.2/Verilator 5.051 WData wrapper compile failure |
| SBT with SPINAL_VERILATOR_FLAGS=-CFLAGS -DWData=EData after test correction | 1 | real matcher assertion exposed overlapping duplicate return-site fill |
| final SBT local profile with 240s timeout and compatibility flag | 0 | compile, 2 CoreConfig tests, predictor Verilator test passed; simulation 37.677 ms |
| make test-local LOCAL_TMP_ROOT=/tmp | 0 | 371 Python automation tests passed in 8.481 s |
| canonical SBT GenerateCoreTopCompat into /tmp generate | 0 | raw RTL generated; Spinal reported 111 pruned signals |
| core_top_gate.py package on /tmp raw RTL | 0 | 49-port package passed |
| core_top_gate.py lint --environment-profile local | 1 | fail-closed 73-warning inventory |
| make cpu-stage CPU_WORK_ROOT=/tmp/... LOCAL_TMP_ROOT=/tmp | 0 | root Makefile staged one candidate source file outside official chiplab |
| python warning-name inventory on local lint summary | 0 | decode_io_btb_index removed; decode_io_btb_deleteEntry is the expected dead official input |

## Artifacts and hashes

- raw generated core_top.v SHA-256:
  b32e877299330ae93656555b7783b4b13826ca146567dfadef52818b4e0a5919
- packaged mycpu_top.v SHA-256:
- root Makefile staged mycpu_top.v SHA-256:
  ded57a4a2b494e5342481a2d87e5b286ebb703bedde8e79df3fe299894dc4cad
  ded57a4a2b494e5342481a2d87e5b286ebb703bedde8e79df3fe299894dc4cad
- local Verilator log SHA-256:
  5057261058e9a2416ab850d760cd939170bbbd5ae6051769d349874b255add40
- local lint summary SHA-256:
  3b75115efb754b4a143c3bc35fa6594e8e2aa610d16d902be8c6bcea7809bf88
- warning categories: 71 UNUSEDSIGNAL, one DECLFILENAME, one
  UNUSEDPARAM
- package contract: 49 ports, 17 inputs, 32 outputs, TLBNUM=32,
  legacy backend absent

## Claim and residual risk

Qualified evidence: the default active predictor is now bound to the official
aa3 BTB geometry and index update contract, and its directed local simulation
passes. The complete generated core_top still has 73 strict local lint
warnings; AXI response handling, cache/TLB reserved fields, DiffTest shell,
CSR/debug observations, and whole-chip functional behavior remain open.

This boundary does not claim official behavioral equivalence, complete
predictor cycle lockstep, functional/random/performance/system/Vivado pass, or
release readiness. The local tool run is not a locked-manifest gate.

Rollback: revert this ECHO predictor commit. Do not modify the nested official
checkout, chiplab source baseline, or user-owned chiplab dirty files.
