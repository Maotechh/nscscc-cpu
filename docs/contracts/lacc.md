# openLA500 LACC cycle contract

## Scope and oracle

- Golden candidate: `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`.
- Behavioral sources: `rtl/lacc_core.v` and `rtl/lacc_demo.v` at that commit.
- Candidate generator: `openla500.execute.GenerateOpenLa500LaccCore`.
- Generated top definition: `lacc_core`.

This contract covers the active demo accelerator only. Passing it does not prove execute-stage,
cache, whole-core, DiffTest, or chiplab integration.

## Legacy port contract

| Port | Direction | Width | Meaning |
|---|---|---:|---|
| `clk` | input | 1 | Rising-edge state clock |
| `reset` | input | 1 | Synchronous active-high partial reset |
| `lacc_flush` | input | 1 | Synchronous active-high abort |
| `lacc_req_valid` | input | 1 | Level request, held until response |
| `lacc_req_command` | input | 2 | `0`: lmadd, `1`: configure |
| `lacc_req_imm` | input | 7 | Architecturally unused by the golden demo |
| `lacc_req_rj` | input | 32 | Configure count or lmadd source-1 address |
| `lacc_req_rk` | input | 32 | Configure destination or lmadd source-2 address |
| `lacc_rsp_valid` | output | 1 | Level response for the current request |
| `lacc_rsp_rdat` | output | 32 | Sum of all read responses in the lmadd operation |
| `lacc_data_valid` | output | 1 | Memory request valid |
| `lacc_data_ready` | input | 1 | Memory request ready |
| `lacc_data_addr` | output | 32 | Read or write byte address |
| `lacc_data_read` | output | 1 | `1`: read, `0`: write |
| `lacc_data_wdata` | output | 32 | Sum written for one source pair |
| `lacc_data_size` | output | 2 | Constant `2'b10` word access |
| `lacc_drsp_valid` | input | 1 | Ordered read-response valid |
| `lacc_drsp_rdata` | input | 32 | Read-response data |

No implicit clock/reset or extra public port is permitted.

## Command and cycle behavior

1. Configure (`command == 1`) captures `rj[6:0]` as the element count and `rk` as the
   destination address on the rising edge. Its response is combinationally valid while the request
   is valid in Idle and it never issues memory traffic.
2. Zero-count lmadd (`command == 0`) responds immediately in Idle and issues no memory request.
3. Nonzero lmadd captures `rj` and `rk` as source addresses, clears the result accumulator, and
   issues one source-1 read followed by one source-2 read for each element.
4. A memory request advances only on `lacc_data_valid && lacc_data_ready`. While stalled, valid,
   address, read/write, size, and write data remain stable.
5. Ordered read responses are accepted without backpressure. The first response is buffered; the
   second response produces a 32-bit wrapping sum and a write request to the current destination.
6. After each pair, both source addresses and the destination address advance by four bytes. The
   seven-bit count decrements after the source-2 request handshake.
7. The final `lacc_rsp_valid` is asserted in the same cycle as the final write handshake. The
   response data is the 32-bit wrapping sum of every read response in the operation.
8. Commands `2` and `3` produce neither response nor memory request while Idle.

The memory environment must return exactly one ordered response for every accepted read and no
response for writes. A response is not consumed through a ready signal because the golden interface
has none.

## Reset and flush

`reset` and `lacc_flush` are synchronous. They return the FSM to Idle and clear only the five
golden-reset registers: element count, FSM state, read-request valid, first-response buffered valid,
and write-data valid. Source/destination addresses, response accumulator, buffered data, and delayed
write-valid history intentionally retain the golden partial-reset behavior. A flush aborts the
active transaction and does not create an architectural response.

Values on invalid response and unused memory payload cycles are not architectural behavior and must
not be used as an oracle. In particular, `lacc_req_imm` does not affect any valid response or memory
transaction.

## Required evidence

- Scala compilation and elaboration with locked Scala, sbt, SpinalHDL, and JDK versions.
- Verilator simulation with strict warning flags.
- Directed coverage of configure, zero count, one and multiple elements, read/write backpressure,
  address progression, wrapping accumulation, final write/response alignment, flush, reset, and
  unsupported commands.
- Exact generated legacy module and port check.
- Before active replacement, a golden/candidate cycle differential under legal memory-response
  ordering and a mixed whole-core overlay regression are still required.
