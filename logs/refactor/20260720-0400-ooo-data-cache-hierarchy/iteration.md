# 20260720-0400 OoO Data Cache Hierarchy

## Scope

Connect a write-back 64-byte L1D to a shared-level 64-byte L2, attach the
hierarchy to the ordered OoO LSQ boundary, and establish behavioral and Vivado
synthesis evidence. The official scalar SoC top is unchanged.

## Implementation

- Added `OooL1DataCache`, a two-way 8-KiB blocking L1D controller.
- Added `OooL2Cache`, a two-way 64-KiB blocking L2 controller.
- Added `OooDataCacheHierarchy` and `OooBackendWithDataCache` integration tops.
- Added deterministic generators and batch synthesis scripts for both tops.
- Added directed tests for refill, hit, byte-store merge, request backpressure,
  dirty L1 writeback, dirty L2 writeback, and integrated L1D/L2 behavior.

The integrated test fills four lines mapping to one L1 set, dirties the first,
forces its eviction into L2, then reloads it. The returned word is `deadbeef`
and no external memory read occurs, proving that the dirty line reached L2.

## Verification

Environment:

- Ubuntu WSL2
- OpenJDK 17.0.19
- sbt 1.10.11
- Verilator 5.020
- Vivado 2023.2 build 4029153
- Device `xc7a200tfbg676-2`

Final full Scala/Verilator run after the wrapper and cache hierarchy additions:

```text
sbt -batch test
58 tests, 27 suites, 58 passed, 0 failed
```

The backend/cache wrapper elaboration test is included in the 58-test result.

## Vivado results

`ooo_data_cache_hierarchy`, 10.000 ns:

- 4,315 LUT
- 3,975 FF
- 28 RAMB36 and 8 RAMB18
- 0 DSP
- WNS `+3.002 ns`, TNS `0.000 ns`, 0 failing endpoints
- Worst data path `6.342 ns`, 7 logic levels
- RTL SHA-256 `4CBEE93AE883E18467B0FC418A19CD560C0866751182BE6FA1A74282BAE24F35`
- DCP SHA-256 `BC64D527FB2A6AF8F63EC0F36017C09AA383D7A3A16B42E0A0811600A4571C8A`

`ooo_backend_with_data_cache`, 10.000 ns:

- 57,964 LUT
- 24,069 FF
- 28 RAMB36 and 8 RAMB18
- 4 DSP48E1
- WNS `-1.891 ns`, TNS `-527.483 ns`, 599 failing endpoints
- Worst data path `11.740 ns`, 29 logic levels
- RTL SHA-256 `573A741AF70E29B87337001AD6EE6DF8E4F64B2B4150040979C5DF734C3C030F`
- DCP SHA-256 `525C95749099D4F73BE0737F5F8A7E65AAFFA41B86A0FA83BDCE163611B5A439`

Both runs completed with 0 errors and 0 critical warnings. The combined critical
path is unchanged from the preceding backend baseline:
`issueQueues_3/enqueueReadyReg` to `issueQueues_0/payloadSlots_0_source2Ready`.

## Assessment

The round is accepted as an architectural performance milestone: the backend
now has a synthesizable two-level data hierarchy, cache hits avoid external
memory, and the added hierarchy does not worsen the existing backend critical
path. This is not an official speedup claim because frontend, AXI, MMU/TLB,
official functional workloads, implementation, and board measurements remain
unconnected.

The remote FPGA evaluation skill is not available in the current tool set, so no
board result is claimed. The next timing iteration should pipeline the IQ
dispatch/wakeup feedback path before L1I and shared-L2 arbitration expand the
top further.

## Compliance

- Design sources are Scala/SpinalHDL.
- Generated Verilog remains under ignored `spinal/target/` paths.
- No hand-written Verilog is introduced.
- The standalone evidence is not substituted for official functional or FPGA
  scoring.
