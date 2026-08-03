# Seeded CPU-only reset AXI recovery

## Failure

The `nscscc-seeded-reset-v1` board protocol keeps DDR, the system clock domain and the AXI
crossbar running between functional seeds and performance cases. It resets only the CPU and
`confreg` through `btn_step_vio[0]`. The previous evaluation flow reset the complete platform, so
the behavior below was not observable.

Chiplab's `Axi_CDC` resets its CPU-to-system request FIFOs from `cpu_resetn`, but resets its
system-to-CPU R/B response FIFOs from `sys_resetn`. A request that has already reached the system
side may therefore complete while only the CPU is held in reset. The old bridge cleared its local
outstanding state and deasserted `RREADY/BREADY`; the response remained in the CDC FIFO and could
later be mistaken for a new request that reused the same four-bit AXI ID.

This matches the observed board failures at parent commit
`d9bab16ef46540eb3348b0781afc4d0949f28adc`:

- `func58` job `20260802-212323-3a88d7bd` timed out under
  `nscscc-seeded-reset-v1`;
- `perf20` job `20260802-212934-428d5aa4` passed its first two cases and then failed subsequent
  CPU-only-reset cases;
- locked OpenLA500 positive control job `20260802-210107-85705dce` passed on the same service.

## Change

`OooAxiLineBridge` enters a response-drain state after reset. While active it:

- accepts and discards AXI R and B responses;
- blocks new AR, AW and W traffic and all upstream request acceptance;
- leaves the drain state only after 256 consecutive CPU cycles without an R or B response;
- restarts the 256-cycle quiet window whenever another old response appears.

No handwritten Verilog is added. `rtl/mycpu_top.v` must be regenerated from the Scala source
before publication.

## Directed evidence

`OooAxiLineBridgeSpec` covers stale cached read responses, stale uncached read and write responses,
reuse of the same AXI ID, and a response arriving immediately before the quiet window would end.
The existing core interrupt test also verifies that an interrupt pending in a self-branch loop
reaches precise exception recovery.

The apparent `func58` timer failure from an earlier EPYC2 simulation was caused by reusing a
hardware ELF built with `RUN_SIMU=0`. Rebuilding `func_lab9` with the locked LA32R GCC 8.3 and
`RUN_SIMU=1` produced terminal `num_data=0x3A00003A`; no timer RTL change is part of this iteration.

## Candidate gates

The generated `rtl/mycpu_top.v` is byte-identical to
`build/core_top/package/rtl/mycpu_top.v` and has SHA256
`9623ba8b21746539bdc366f8b1d2073b58efcc3992490134887017f91a3a2daa`.

- Scala compilation passed; 37 suites and 137 tests passed.
- Python gates passed; 362 tests passed with `TMPDIR` resolved under `/private/tmp` on macOS.
- The locked port contract passed with Yosys 0.33.
- Locked Verilator 5.020 lint passed with the previously reviewed 849-warning signature. The
  categories remain exactly `CMPCONST` and `UNUSEDSIGNAL`, and the warning-signature SHA256 remains
  `218a2d03db8147e7b83823d25583764bff818dda6e06b638804a35b50af15f88`.
- The locked Yosys structural gate and publication-consistency gate passed.

The locked Verilator and Yosys binaries were run in an Ubuntu 24.04 container because the EPYC2
host uses Ubuntu 22.04 and cannot satisfy their GLIBC 2.38 requirement. The checked binary hashes
remain those recorded in `reference/manifest.lock`; only runtime libraries, Python and Git came
from the container image.

## Required completion evidence

This iteration is incomplete until the repository gates pass, generated RTL is committed with the
Scala source, a complete Vivado 2023.2 implementation is produced from that commit, and both
`func58` and `perf20` pass under Chiplab commit
`68c20a539e2be8a05300e714296f5fda8373ee80` with downloaded artifact hashes verified.
