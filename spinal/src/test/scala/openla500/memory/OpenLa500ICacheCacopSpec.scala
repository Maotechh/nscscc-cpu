package openla500.memory

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

class OpenLa500ICacheCacopSpec extends AnyFunSuite {
  private val SetCount = 1024
  private val TargetAddress = BigInt("1c123040", 16)
  private val OtherColorAddress = TargetAddress ^ BigInt("00001000", 16)
  private val OtherAddress = TargetAddress ^ BigInt("00005000", 16)

  test("active 32 KiB profile mode2 CACOP invalidates a line outside the previous request set") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-icache-cacop")
    val workspace = Paths.get(workspaceRoot, "icache-mode2-hit-invalidate").toString

    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .addSimulatorFlag("-Wno-UNUSEDSIGNAL")
      .disableCache
      .workspacePath(workspace)
      .compile(new OpenLa500ICache(setCount = SetCount, scrubOnReset = true))
      .doSim("icache-mode2-hit-invalidate", 0x158aa8) { dut =>
        dut.io.clk #= false
        dut.io.reset #= true
        dut.io.valid #= false
        dut.io.op #= false
        dut.io.index #= 0
        dut.io.tag #= 0
        dut.io.speculativeColor #= 0
        dut.io.offset #= 0
        dut.io.wstrb #= 0
        dut.io.wdata #= 0
        dut.io.uncache_en #= false
        dut.io.icacop_op_en #= false
        dut.io.cacop_op_mode #= 0
        dut.io.cacop_op_addr_index #= 0
        dut.io.cacop_op_addr_tag #= 0
        dut.io.cacop_op_addr_offset #= 0
        dut.io.tlb_excp_cancel_req #= false
        dut.io.rd_rdy #= true
        dut.io.ret_valid #= false
        dut.io.ret_last #= false
        dut.io.ret_data #= 0
        dut.io.wr_rdy #= true

        def risingEdge(): Unit = {
          dut.io.clk #= false
          sleep(2)
          dut.io.clk #= true
          sleep(2)
          dut.io.clk #= false
          sleep(2)
        }

        def driveFetchAddress(address: BigInt): Unit = {
          dut.io.tag #= (address >> 12) & ((BigInt(1) << 20) - 1)
          dut.io.speculativeColor #= (address >> 12) & 0x3
          dut.io.index #= (address >> 4) & 0xff
          dut.io.offset #= address & 0xf
        }

        def waitForScrub(): Unit = {
          for (cycle <- 0 until SetCount) {
            sleep(1)
            assert(!dut.io.addr_ok.toBoolean, s"accepted a request during scrub cycle $cycle")
            assert(!dut.io.icache_unbusy.toBoolean, s"reported idle during scrub cycle $cycle")
            risingEdge()
          }
          sleep(1)
          assert(dut.io.addr_ok.toBoolean, "did not accept requests after the final scrub write")
          assert(dut.io.icache_unbusy.toBoolean, "did not return idle after scrub")
        }

        def fillLine(address: BigInt, lineBase: BigInt): Unit = {
          driveFetchAddress(address)
          dut.io.valid #= true
          sleep(1)
          assert(dut.io.addr_ok.toBoolean, f"fetch 0x$address%08x was not accepted")
          risingEdge()
          dut.io.valid #= false
          sleep(1)
          assert(!dut.io.data_ok.toBoolean, f"cold fetch 0x$address%08x unexpectedly hit")
          risingEdge()
          sleep(1)
          assert(dut.io.rd_req.toBoolean, f"cold fetch 0x$address%08x did not request a refill")
          assert(
            dut.io.rd_addr.toBigInt == (address & ~BigInt(0xf)),
            f"wrong refill address 0x${dut.io.rd_addr.toBigInt}%08x"
          )
          risingEdge()

          for (beat <- 0 until 4) {
            dut.io.ret_valid #= true
            dut.io.ret_last #= beat == 3
            dut.io.ret_data #= lineBase + beat
            sleep(1)
            if (beat == 0) {
              assert(dut.io.data_ok.toBoolean, "critical refill word did not respond")
            }
            risingEdge()
          }
          dut.io.ret_valid #= false
          dut.io.ret_last #= false
          sleep(1)
          assert(dut.io.icache_unbusy.toBoolean, "cache did not return idle after refill")
        }

        def expectHit(address: BigInt, expected: BigInt): Unit = {
          driveFetchAddress(address)
          dut.io.valid #= true
          sleep(1)
          assert(dut.io.addr_ok.toBoolean, f"fetch 0x$address%08x was not accepted")
          risingEdge()
          dut.io.valid #= false
          sleep(1)
          assert(dut.io.data_ok.toBoolean, f"fetch 0x$address%08x did not hit")
          assert(dut.io.rdata.toBigInt == expected, f"fetch 0x$address%08x returned stale data")
          risingEdge()
          sleep(1)
        }

        risingEdge()
        risingEdge()
        dut.io.reset #= false
        waitForScrub()

        fillLine(TargetAddress, BigInt("a5000000", 16))
        fillLine(OtherAddress, BigInt("5a000000", 16))
        expectHit(TargetAddress, BigInt("a5000000", 16))

        // The SRAM probe uses a virtual color before the translated tag arrives. Point that
        // speculative probe at TargetAddress, then reveal a different physical color one cycle
        // later. The old line must not escape as a hit; the corrected set is replayed instead.
        driveFetchAddress(OtherColorAddress)
        dut.io.tag #= (TargetAddress >> 12) & ((BigInt(1) << 20) - 1)
        dut.io.speculativeColor #= (TargetAddress >> 12) & 0x3
        dut.io.valid #= true
        sleep(1)
        assert(dut.io.addr_ok.toBoolean, "wrong-color request was not accepted speculatively")
        risingEdge()
        dut.io.valid #= false
        dut.io.tag #= (OtherColorAddress >> 12) & ((BigInt(1) << 20) - 1)
        sleep(1)
        assert(!dut.io.data_ok.toBoolean, "wrong-color SRAM output escaped during replay")
        assert(!dut.io.addr_ok.toBoolean, "accepted another fetch during set replay")
        risingEdge()
        sleep(1)
        assert(!dut.io.data_ok.toBoolean, "cold corrected I-cache set unexpectedly hit")
        risingEdge()
        sleep(1)
        assert(dut.io.rd_req.toBoolean, "corrected I-cache set did not request a refill")
        assert(
          dut.io.rd_addr.toBigInt == (OtherColorAddress & ~BigInt(0xf)),
          f"wrong replay refill address 0x${dut.io.rd_addr.toBigInt}%08x"
        )
        risingEdge()

        for (beat <- 0 until 4) {
          dut.io.ret_valid #= true
          dut.io.ret_last #= beat == 3
          dut.io.ret_data #= BigInt("c3000000", 16) + beat
          risingEdge()
        }
        dut.io.ret_valid #= false
        dut.io.ret_last #= false
        sleep(1)

        expectHit(OtherColorAddress, BigInt("c3000000", 16))
        expectHit(TargetAddress, BigInt("a5000000", 16))
        expectHit(OtherAddress, BigInt("5a000000", 16))

        // Leave requestSet at OtherAddress, then invalidate TargetAddress. The CACOP request must
        // select its own physical set for the synchronous tag read instead of reusing requestSet.
        dut.io.cacop_op_mode #= 2
        dut.io.cacop_op_addr_tag #= (TargetAddress >> 12) & ((BigInt(1) << 20) - 1)
        dut.io.cacop_op_addr_index #= (TargetAddress >> 4) & 0xff
        dut.io.cacop_op_addr_offset #= TargetAddress & 0xf
        dut.io.icacop_op_en #= true
        sleep(1)
        assert(!dut.io.addr_ok.toBoolean, "CACOP was exposed as a normal fetch acceptance")
        risingEdge()
        dut.io.icacop_op_en #= false

        var completionCycles = 0
        while (!dut.io.icache_unbusy.toBoolean && completionCycles < 8) {
          risingEdge()
          completionCycles += 1
        }
        assert(dut.io.icache_unbusy.toBoolean, "mode2 CACOP did not complete")
        assert(!dut.io.rd_req.toBoolean, "mode2 hit-invalidate incorrectly issued a refill")

        driveFetchAddress(TargetAddress)
        dut.io.valid #= true
        sleep(1)
        assert(dut.io.addr_ok.toBoolean, "post-CACOP target fetch was not accepted")
        risingEdge()
        dut.io.valid #= false
        sleep(1)
        assert(!dut.io.data_ok.toBoolean, "mode2 CACOP left the target line valid")
        risingEdge()
        sleep(1)
        assert(dut.io.rd_req.toBoolean, "invalidated target did not request a new refill")
      }
  }
}
