# DBAR/IBAR Linux semantics closure

## Candidate identity

- Active branch: `dev/ECHO`
- Base commit: `d9bab16ef46540eb3348b0781afc4d0949f28adc`
- Source commit: `2301dde1ee0622e27b2bbaaf609942b56ca5f764`
- Pre-documentation source status SHA-256: `6b0e07dac5b3e3c21be32d8da7ce6c9aada9e8f26380670ecca075f7bd36b0e9`
- Generated `rtl/mycpu_top.v` SHA-256: `d667c7e3740a95e54863b3758c8343daf932905f5e2aa4e1877dade44d2a60bc`
- Chiplab commit: `68c20a539e2be8a05300e714296f5fda8373ee80`
- Chiplab `IP/myCPU` gitlink: `aa3bde1f3e720e71c2c78d6b81930d797b810149`

## Implementation

The backend now maintains 8-bit speculative and committed memory epochs. Loads and stores after an accepted DBAR/IBAR receive the next epoch, and the LSQ only issues entries in the committed epoch. Flush restores the speculative epoch to the committed value, including a barrier that retires on the flush edge.

DBAR and IBAR use a variable-latency ROB-head execution token. DBAR waits for older stores and registered L1D/MSHR/L2/AXI quiescence in two consecutive cycles. IBAR then performs L1D writeback-invalidate, L2 writeback-invalidate, L1I invalidate, waits for final AXI drain, and completes with a single `PC+4` refetch.

The candidate also removes flush from internal candidate handshake paths, simplifies micro-TLB field selection, and registers uncached AXI arbitration state. These timing changes preserve flush-priority state clearing and were covered by the queue/dispatch tests.

## Local verification

- Scala/SpinalHDL: 37 suites, 140 tests, all passed with Verilator 5.020.
- Python tooling: 364 tests, all passed.
- Locked generated-RTL gates: 49-port contract, Verilator lint, Yosys, and publication consistency passed.
- Reviewed lint signature: 880 warnings, exactly `CMPCONST` and `UNUSEDSIGNAL`; signature `8160bbbba0794492b5d1a358b12bdea70d5ad48bac5ad5c0787eac188cef461b`.
- `func_advance` with AXI seeds `5570815`, `1`, and `20260802`: 18,047 / 18,018 / 17,976 cycles; each reached end PC, exited by syscall, and had no DiffTest error.
- `func_lab19`, AXI seed `5570815`: 565,868 cycles; reached end PC, exited by syscall, and had no DiffTest error.

## Linux Verilator milestone

The 5,000,000 ns limited run completed 2,499,995 cycles and 1,224,741 instructions. UART reached Linux 5.14 early console, identified the 32-bit Loongson processor, and printed `start_pfn=0x0, end_pfn=0x8000`. The last committed PC was `0xa07a9b58`. UART SHA-256: `d7687f23400a842fbf393e1400ea154b56fedd98abc834a6545d4688735cf405`.

This is early-boot evidence only. It does not establish U-Boot/PMON, user mode, an interactive shell, or the complete Linux contract.

## Vivado 2023.2 complete SoC

- Device: `xc7a200tfbg676-2`
- Clocks: CPU 100 MHz, system 100 MHz, DDR 200 MHz
- WNS/TNS: `+0.026 ns / 0.000 ns`
- WHS/THS: `+0.051 ns / 0.000 ns`
- Worst setup path: `stagedPdst_1_reg[3]` to issue queue 3 predicted-target register, 9.448 ns data path (1.635 ns logic, 7.813 ns routing), 11 logic levels
- DRC: 0 Error, 26 Warning
- Bitstream: generated successfully, SHA-256 `5e21422e2a9a74e15158e0a84ef6f3c2630bbdc4b34f0bd59f2f878614f240be`
- Probes: SHA-256 `3e36db904e602bae47d72e9f8b54a553903de4ccf5ff72ce88942c87280dfcdb`
- Utilization: 88,286 LUTs, 53,193 registers, 68.5 BRAM tiles, 8 DSPs

## Remaining gates

The current candidate is fixed at `2301dde1ee0622e27b2bbaaf609942b56ca5f764`; no board package or job has been created yet. Existing perf20 jobs belong to the old `da71fd3` baseline and are not evidence for this RTL. Run current-candidate `func58`, Linux boot progress, and three serialized `perf20` evaluations; perf20 must remain 20/20 and no more than 0.2% slower than 74,446,699 cycles.

Subsequent Linux work remains CACOP address/mode semantics, CPUCFG generation from real cache geometry, LL/SC platform limits and external invalidation, then the shell-level Linux acceptance path.
