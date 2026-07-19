# OoO Vivado Baseline (eb34990)

This record is tied to the design snapshot
`eb34990e3144d005fec3ec41d29130440ebbee76`. The record-only commit amendment
does not change Scala design sources or generated RTL.

This is a synthesis baseline for the standalone four-issue, three-commit OoO
backend and the backend with the 64-byte L1D/L2 hierarchy. It is not an
official SoC functional or FPGA performance result.

## Tool and design

- Vivado: 2023.2 (build 4029153)
- Device: `xc7a200tfbg676-2`, speed grade `-2`
- Clock constraint: `ooo_clk`, 10.000 ns (100 MHz)
- Run date: 2026-07-20
- Source worktree: detached, clean `eb34990`
- Generated reports: `spinal/target/ooo-vivado/regenerated-eb34990/`

RTL generation:

```text
sbt -batch "runMain openla500.ooo.GenerateOooBackend --out-dir target/ooo-vivado/regenerated-eb34990/backend/rtl"
sbt -batch "runMain openla500.ooo.GenerateOooBackendWithDataCache --out-dir target/ooo-vivado/regenerated-eb34990/backend-with-data-cache/rtl"
```

Vivado synthesis:

```text
vivado -mode batch -source tools/ooo_backend_synth.tcl -tclargs \
  spinal/target/ooo-vivado/regenerated-eb34990/backend/rtl/ooo_backend_with_execution.v \
  spinal/target/ooo-vivado/regenerated-eb34990/backend/synth

vivado -mode batch -source tools/ooo_backend_with_data_cache_synth.tcl -tclargs \
  spinal/target/ooo-vivado/regenerated-eb34990/backend-with-data-cache/rtl/ooo_backend_with_data_cache.v \
  spinal/target/ooo-vivado/regenerated-eb34990/backend-with-data-cache/synth
```

## Results

Both runs completed with 0 errors and 0 critical warnings. Neither top meets
the 100 MHz constraint, so these results are a comparison baseline rather than
a timing-closure claim.

| Top | LUT | FF | RAMB36 | RAMB18 | DSP | WNS | TNS | Failing endpoints |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ooo_backend_with_execution` | 53,239 | 20,115 | 0 | 0 | 4 | -1.891 ns | -527.483 ns | 599 / 40,504 |
| `ooo_backend_with_data_cache` | 57,964 | 24,069 | 28 | 8 | 4 | -1.891 ns | -527.483 ns | 599 / 50,302 |

The shared worst path has 11.740 ns data delay and 29 logic levels. It starts
at `backend/issueQueues_3/enqueueReadyReg_reg/C` and ends at
`backend/issueQueues_0/payloadSlots_0_source2Ready_reg/D`. The data path is
4.430 ns logic and 7.310 ns routing.

The standalone synthesis engine reported 3,993 warnings and the combined top
reported 4,045, primarily from pruning unused state in these diagnostic tops.
Each final Vivado session summary contained 202 warnings.

## Artifact identity

| Artifact | SHA-256 |
| --- | --- |
| Standalone RTL | `3B0935609C1DA4C5349073D24C69A951F00C60597BC5BBF6E4A507A277B473B7` |
| Standalone DCP | `F449AEB6A618DE630BC1A7A0E1FB2B6446D7656D9922C29C513371ADD8240BDA` |
| Backend/cache RTL | `573A741AF70E29B87337001AD6EE6DF8E4F64B2B4150040979C5DF734C3C030F` |
| Backend/cache DCP | `79A6CB3D593031786225D0BDC967E7E2700B709EBD3615C26E37D3D553D9C5F6` |

Both RTL hashes exactly match the earlier generated artifacts for this design.
The resource and timing values also reproduce the preceding reports. DCP files
are identified by the hashes from this run because Vivado regenerated them with
new run metadata.

The official scalar CPU board measurements remain in the root `baseline.txt`.
This synthesis baseline must not be used as an official competition score until
frontend, MMU/TLB, SoC integration, full functional tests, implementation, and
board evaluation are complete.
