# OoO Vivado Baseline (2f7271f)

This record is tied to the design snapshot
`2f7271fb73d4df3e71e5c4bcd8048d2ea0aaf6f0`. The subsequent record-only
commit amendment does not change any Scala or generated RTL design source.

This is a standalone synthesis baseline for the four-issue, three-commit OoO
backend. It is not the official SoC functional or FPGA performance baseline.

## Tool and design

- Vivado: 2023.2 (build 4029153)
- Device: `xc7a200tfbg676-2`, speed grade `-2`
- Clock constraint: `ooo_clk`, 10.000 ns (100 MHz)
- Top: `ooo_backend_with_execution`
- Generated RTL: `spinal/target/ooo-vivado/baseline-2f7271f/rtl/ooo_backend_with_execution.v`
- Reports: `spinal/target/ooo-vivado/baseline-2f7271f/synth/`
- Run date: 2026-07-20

RTL generation:

```text
sbt -batch "runMain openla500.ooo.GenerateOooBackend --out-dir target/ooo-vivado/baseline-2f7271f/rtl"
```

Synthesis:

```text
vivado -mode batch -source tools/ooo_backend_synth.tcl -tclargs \
  spinal/target/ooo-vivado/baseline-2f7271f/rtl/ooo_backend_with_execution.v \
  spinal/target/ooo-vivado/baseline-2f7271f/synth
```

## Result

Vivado completed synthesis with 0 errors and 0 critical warnings. The synthesis
engine reported 3,993 warnings, primarily removal of unused sequential state in
the standalone backend; the final Vivado session summary reported 202 warnings.

| Resource | Used | Notes |
| --- | ---: | --- |
| LUT | 53,239 | 53,239 logic LUTs; 0 LUTRAM; 0 SRL |
| FF | 20,115 | |
| RAMB36 | 0 | Cache arrays are not integrated in this top |
| RAMB18 | 0 | Cache arrays are not integrated in this top |
| DSP48E1 | 4 | Used by `OooMultiplyPipe` |

Timing is not met at 100 MHz in this standalone configuration:

- WNS: `-1.891 ns`
- TNS: `-527.483 ns`
- Failing endpoints: `599 / 40504`
- Worst data path: `11.740 ns` (logic `4.430 ns`, route `7.310 ns`)
- Worst path source: `backend/issueQueues_3/enqueueReadyReg_reg/C`
- Worst path destination: `backend/issueQueues_0/payloadSlots_0_source2Ready_reg/D`
- Logic depth: 29 levels
  (`CARRY4=12`, `LUT2=3`, `LUT4=1`, `LUT5=2`, `LUT6=10`, `MUXF7=1`)

Artifact hashes for this run:

- RTL SHA-256: `3B0935609C1DA4C5349073D24C69A951F00C60597BC5BBF6E4A507A277B473B7`
- DCP SHA-256: `C97AC24C4A3FE62E3F688E98F87C5BEE8BF28FC0E5078702B003D41B627C474F`

Compared with the earlier standalone snapshot `937b4dd`:

| Metric | 937b4dd | 2f7271f | Change |
| --- | ---: | ---: | ---: |
| LUT | 56,785 | 53,239 | -3,546 (-6.24%) |
| FF | 19,976 | 20,115 | +139 (+0.70%) |
| WNS | -2.301 ns | -1.891 ns | +0.410 ns |
| TNS | -1175.875 ns | -527.483 ns | +648.392 ns |
| Failing endpoints | 2,614 | 599 | -2,015 |

The official scalar CPU result remains in the root `baseline.txt`. This result
must not be treated as an official competition score until frontend, cache,
MMU/TLB, SoC integration, full functional tests, implementation, and board runs
are complete.
