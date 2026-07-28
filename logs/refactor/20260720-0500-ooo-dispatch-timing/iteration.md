# 20260720-0500 OoO Dispatch and Issue Timing

## Scope

Reduce the standalone OoO backend critical path without changing the fixed
four-execution-port, three-rename, three-commit configuration. The official
scalar SoC top remains unchanged.

## Accepted implementation

- Added an eight-entry circular dispatch FIFO between rename allocation and
  execution-port routing. Rename can allocate ROB, physical register, and LSQ
  state without waiting on current IQ port availability.
- Kept dispatch consumption strictly prefix ordered. The FIFO compacts valid
  rename lanes on write and supports up to three enqueues and three dequeues per
  cycle.
- Recomputed source readiness from the physical-register scoreboard at dispatch
  time. IQ enqueue still observes same-cycle completion wakeups.
- Replaced each monolithic 64-bit FreeList lowest-one selection with an 8x8
  hierarchical selector.
- Split issue readout into an address/uop elastic stage and an operand/uop
  elastic stage. PRF reads sit between the stages; steady-state throughput is
  unchanged while issue latency increases by one cycle.

## Explored alternatives

| Candidate | WNS at 10 ns | Decision |
| --- | ---: | --- |
| Previous backend baseline | -1.891 ns | Comparison point |
| One-entry post-router elastic buffer | -2.451 ns | Rejected; worsened the critical path |
| Rename/dispatch FIFO | -1.700 ns | Kept as the architectural boundary |
| FIFO plus hierarchical FreeList selector | -1.554 ns | Kept |
| Dynamic-index ready/free updates | -1.991 ns | Rejected; reverted |
| FIFO, hierarchical selector, two-stage issue read | -0.998 ns | Accepted |

The final RTL is byte-identical to the accepted standalone synthesis input:

- RTL SHA-256:
  `508526BD4984C81612B0C03C6B6C66384A88C6280E6A11F74BF0B60E3A6FDD2B`
- DCP SHA-256:
  `AF67FC1D8FA592AEB9F515B778ACC1E7A9934DB52446BD14C6EE36684CA32D10`

## Verification

WSL2 environment:

- OpenJDK 17.0.19
- sbt 1.10.11
- SpinalHDL 1.14.2
- Verilator 5.020

Final full regression:

```text
sbt -batch test
60 tests, 29 suites, 60 passed, 0 failed
```

New directed coverage includes dispatch FIFO wrap/full/flush behavior and a
backend sequence of nine independent `add.w` uops. All ROB pointers `0..8` are
observed exactly once, and at least two cycles issue three uops.

## Vivado synthesis

Environment:

- Vivado 2023.2 build 4029153
- Device `xc7a200tfbg676-2`
- Clock `ooo_clk`, 10.000 ns
- `synth_design -flatten_hierarchy rebuilt`

Standalone backend comparison:

| Metric | Previous | Accepted | Change |
| --- | ---: | ---: | ---: |
| LUT | 53,239 | 56,421 | +3,182 (+5.98%) |
| FF | 20,115 | 22,770 | +2,655 (+13.20%) |
| DSP48E1 | 4 | 4 | 0 |
| WNS | -1.891 ns | -0.998 ns | +0.893 ns |
| TNS | -527.483 ns | -142.976 ns | +384.507 ns |
| Failing endpoints | 599 | 1,043 | +444 |

Backend plus 64-byte L1D/L2 comparison:

| Metric | Previous | Accepted | Change |
| --- | ---: | ---: | ---: |
| LUT | 57,964 | 61,153 | +3,189 (+5.50%) |
| FF | 24,069 | 26,725 | +2,656 (+11.03%) |
| RAMB36 / RAMB18 | 28 / 8 | 28 / 8 | 0 / 0 |
| DSP48E1 | 4 | 4 | 0 |
| WNS | -1.891 ns | -0.998 ns | +0.893 ns |
| TNS | -527.483 ns | -142.976 ns | +384.507 ns |
| Failing endpoints | 599 | 1,043 | +444 |

Combined-top artifacts:

- RTL SHA-256:
  `C89B3B65E4DA4242D5EE0463BE8BD3796BBB33AE04A1BC7074226AC01C5EB4F6`
- DCP SHA-256:
  `CFB5D886C774F008B2FF03C7D2E68072DE8D9691497C86629D9768179B55EBD6`

Both accepted synthesis runs completed with 0 errors and 0 critical warnings.
The cache hierarchy does not alter the backend critical path.

## Assessment

The worst path is now FreeList `freeBits_15` to RegisterMap `ready_23`:

- data path delay: 10.847 ns
- logic delay: 1.766 ns
- route delay: 9.081 ns
- logic levels: 12

The WNS and aggregate negative slack improved substantially, but 100 MHz still
fails and the number of failing endpoints increased. This round is accepted as
a backend timing improvement, not as timing closure or an official program
speedup. The next timing round should register or localize FreeList-to-ready
updates without restoring the rejected dynamic-index implementation.

## Compliance and limits

- All design changes are Scala/SpinalHDL; no hand-written Verilog is added.
- Generated RTL and Vivado products remain under ignored `spinal/target/`
  directories.
- No frontend, MMU/TLB, AXI, official SoC functional test, implementation, or
  board result is claimed.
- The remote FPGA evaluation skill is not available in the current tool set, so
  the required three board runs could not be performed.
