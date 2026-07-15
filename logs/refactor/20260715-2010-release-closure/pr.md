# Draft PR: close pure-Spinal warnings and validate func58 on FPGA

Status: **Draft only**. The requested pure-Spinal warning cleanup, repository HDL cleanup, Vivado build, programming, and one func58 hardware job pass. Do not merge automatically because broader release gates remain incomplete.

## Implementation

- Branch: `refactor/20260715-2010-release-closure`
- Base: `56d74f4b92d85e6403689cbbe4f7b4b460e8f63a`
- Implementation: `088d8d4cc9038488a03c27dcbf3a0751b1f76ad9`
- Canonical CPU RTL: `rtl/mycpu_top.v`, SHA256 `cccb159952f10337566c2341eccafdab1fa3fa8882ff4db7565119b8e2e451d2`

The active CPU is generated from SpinalHDL and packaged as one committed `core_top` file. Historical leaf replacement RTL and obsolete SoC Verilog were removed. Repository purity checks allow only this generated file as CPU synthesis HDL; the remaining `.sv` files are simulation-only testbenches.

## Verification

- Locked Scala: 4/4 PASS; 30 Scala tests PASS.
- Reproducible generation: 2/2 PASS.
- Strict Verilator 5.020 lint: 0 warning, 0 error, 0 skip, no external waiver file.
- Port, publication, Yosys, candidate closure, typed AXI, reachability, and repository purity: PASS.
- Clean Linux automation: 398/398 PASS, zero skip.
- func58: 58/58 functional PASS, live DiffTest, no mismatch, DUT warnings 0.
- func81: 81/81 functional PASS, live DiffTest, no mismatch, DUT warnings 0.
- Whole-environment strict wrappers: FAIL because the locked official Verilator compile log emits 365 environment warnings; this is kept separate from DUT warning closure.
- Vivado 2023.2: bitstream PASS, WNS `+0.977809 ns`, TNS `0`, part `xc7a200tfbg676-2`.
- FPGA job `20260715-174319-8a924804`: PASS. VIO is `3A00003A`, LED `1/1` at 100/200/300 ms; package and result artifact hashes all match.

## Remaining Scope

Random DiffTest has no locked vectors. perf20, U-Boot/Linux system validation, the LACC-on release matrix, and a fresh external claim review remain open. The Vivado SoC build also retains 45 DRC warnings and external I/O delay-check warnings despite passing timing and hardware. The active 32-entry predictor still conflicts with the historical 64-entry completion target.

## Rollback

Revert the implementation commits and this evidence-only commit. The FPGA evidence is bound to `088d8d4`; it must not be reused for another commit or profile.
