# OoO Vivado Baseline

This record is tied to commit `937b4ddfe0b1fd9b0e8330253d389d698fd2cbee`.
It is a standalone synthesis baseline for the four-issue, three-commit OoO
backend; it is not the official SoC functional/performance baseline.

## Tool and design

- Vivado: 2023.2 (build 4029153)
- Device: `xc7a200tfbg676-2`, speed grade `-2`
- Clock constraint: `ooo_clk`, 10.000 ns (100 MHz)
- Top: `ooo_backend_with_execution`
- RTL: `spinal/target/ooo-vivado/baseline-937b4dd/rtl/ooo_backend_with_execution.v`
- Reports: `spinal/target/ooo-vivado/baseline-937b4dd/synth/`

RTL was generated with:

```text
sbt -batch "runMain openla500.ooo.GenerateOooBackend --out-dir target/ooo-vivado/baseline-937b4dd/rtl"
```

Vivado was run with `tools/ooo_backend_synth.tcl` and the arguments above.

## Result

Synthesis completed successfully with 0 errors and 0 critical warnings. The
synthesis engine reported 3,998 warnings, primarily unused sequential signals
from the generated standalone backend; the final Vivado session summary reported
202 warnings.

| Resource | Used | Notes |
| --- | ---: | --- |
| LUT | 56,785 | 56,785 logic LUTs; 0 LUTRAM; 0 SRL |
| FF | 19,976 | |
| RAMB36 | 0 | Cache arrays are not integrated in this standalone top |
| RAMB18 | 0 | Cache arrays are not integrated in this standalone top |
| DSP48E1 | 4 | Used by `OooMultiplyPipe` |

Timing is not met at 100 MHz in this standalone configuration:

- WNS: `-2.301 ns`
- TNS: `-1175.875 ns`
- Failing endpoints: `2614 / 40804`
- Worst data path: `12.150 ns` (logic `4.455 ns`, route `7.695 ns`)
- Worst path source: `backend/issueQueues_2/count_reg[3]/C`
- Worst path destination: `backend/issueQueues_0/payloadSlots_0_source2Ready_reg/D`
- Logic depth: 32 levels (`CARRY4=16`, `LUT2=3`, `LUT5=3`, `LUT6=10`)

Artifact hashes:

- RTL SHA-256: `386DD7826286D37D718AF2C722F790E38E4F2DCA579B5721802A713FDD060F57`
- DCP SHA-256: `07A1A3C05950125B90146E647905037482B1B4EF0F1661D03A6CF03C46B70B4E`

The official scalar CPU results remain in the root `baseline.txt`. This OoO
record must not be compared with that file as an official functional score until
frontend, cache, MMU/TLB, SoC integration, and the required test workload are
connected and validated.
