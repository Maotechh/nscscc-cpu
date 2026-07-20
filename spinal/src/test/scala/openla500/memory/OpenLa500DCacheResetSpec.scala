package openla500.memory

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

class OpenLa500DCacheResetSpec extends AnyFunSuite {
  private val SetCount = 1024
  private val Address = BigInt("1c123040", 16)
  private val OtherColorAddress = Address ^ BigInt("00001000", 16)
  private val LineBase = BigInt("a5000000", 16)
  private val OtherLineBase = BigInt("5a000000", 16)

  test("active 32 KiB profile scrubs stale tags before accepting a post-reset request") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-dcache-reset")
    val workspace = Paths.get(workspaceRoot, "dcache-reset-scrub").toString

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
      .compile(new OpenLa500DCache(setCount = SetCount, scrubOnReset = true))
      .doSim("dcache-reset-scrub", 0x158aa8) { dut =>
        dut.io.clk #= false
        dut.io.reset #= true
        dut.io.valid #= false
        dut.io.op #= false
        dut.io.size #= 2
        dut.io.index #= 0
        dut.io.tag #= 0
        dut.io.speculativeColor #= 0
        dut.io.offset #= 0
        dut.io.wstrb #= 0
        dut.io.wdata #= 0
        dut.io.uncache_en #= false
        dut.io.dcacop_op_en #= false
        dut.io.cacop_op_mode #= 0
        dut.io.preld_hint #= 0
        dut.io.preld_en #= false
        dut.io.tlb_excp_cancel_req #= false
        dut.io.sc_cancel_req #= false
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

        def driveAddress(address: BigInt): Unit = {
          dut.io.tag #= (address >> 12) & ((BigInt(1) << 20) - 1)
          dut.io.speculativeColor #= (address >> 12) & 0x3
          dut.io.index #= (address >> 4) & 0xff
          dut.io.offset #= address & 0xf
        }

        def waitForScrub(): Unit = {
          for (cycle <- 0 until SetCount) {
            sleep(1)
            assert(!dut.io.addr_ok.toBoolean, s"accepted a request during scrub cycle $cycle")
            assert(!dut.io.dcache_empty.toBoolean, s"reported empty during scrub cycle $cycle")
            risingEdge()
          }
          sleep(1)
          assert(dut.io.addr_ok.toBoolean, "did not accept requests after the final scrub write")
          assert(dut.io.dcache_empty.toBoolean, "did not return to empty after scrub")
        }

        def acceptLoad(address: BigInt): Unit = {
          driveAddress(address)
          dut.io.valid #= true
          sleep(1)
          assert(dut.io.addr_ok.toBoolean, f"load 0x$address%08x was not accepted")
          risingEdge()
          dut.io.valid #= false
          sleep(1)
        }

        risingEdge()
        risingEdge()
        dut.io.reset #= false
        driveAddress(Address)
        dut.io.valid #= true
        waitForScrub()

        // The held request is accepted only after all stale tag-valid and dirty entries are clear.
        risingEdge()
        dut.io.valid #= false
        sleep(1)
        assert(!dut.io.data_ok.toBoolean, "cold request incorrectly hit after initial scrub")
        risingEdge()
        sleep(1)
        assert(dut.io.rd_req.toBoolean, "cold request did not issue a line refill")
        assert(
          dut.io.rd_addr.toBigInt == (Address & ~BigInt(0xf)),
          f"wrong refill address 0x${dut.io.rd_addr.toBigInt}%08x"
        )
        risingEdge()

        for (beat <- 0 until 4) {
          val value = LineBase + beat
          dut.io.ret_valid #= true
          dut.io.ret_last #= beat == 3
          dut.io.ret_data #= value
          sleep(1)
          if (beat == 0) {
            assert(dut.io.data_ok.toBoolean, "critical refill word did not respond")
            assert(dut.io.rdata.toBigInt == value, "critical refill word was corrupted")
          }
          risingEdge()
        }
        dut.io.ret_valid #= false
        dut.io.ret_last #= false
        sleep(1)

        acceptLoad(Address)
        assert(dut.io.data_ok.toBoolean, "refilled line did not hit")
        assert(dut.io.rdata.toBigInt == LineBase, "cache-hit data was corrupted")
        assert(!dut.io.rd_req.toBoolean, "cache hit incorrectly issued a refill")
        risingEdge()

        // The real core receives the physical tag one cycle after accepting the virtual index.
        // These two addresses have the same stored tag and virtual index but different physical
        // colors, so failing to replay would falsely return Address's cached line here.
        driveAddress(OtherColorAddress)
        dut.io.tag #= (Address >> 12) & ((BigInt(1) << 20) - 1)
        dut.io.speculativeColor #= (Address >> 12) & 0x3
        dut.io.valid #= true
        sleep(1)
        assert(dut.io.addr_ok.toBoolean, "late-tag request was not accepted speculatively")
        risingEdge()
        dut.io.valid #= false
        dut.io.tag #= (OtherColorAddress >> 12) & ((BigInt(1) << 20) - 1)
        sleep(1)
        assert(!dut.io.data_ok.toBoolean, "wrong-color SRAM output escaped during replay")
        assert(!dut.io.addr_ok.toBoolean, "accepted another request during set replay")
        risingEdge()
        sleep(1)
        assert(!dut.io.data_ok.toBoolean, "cold corrected set incorrectly hit")
        risingEdge()
        sleep(1)
        assert(dut.io.rd_req.toBoolean, "corrected set did not issue a refill")
        assert(
          dut.io.rd_addr.toBigInt == (OtherColorAddress & ~BigInt(0xf)),
          f"wrong replay refill address 0x${dut.io.rd_addr.toBigInt}%08x"
        )
        risingEdge()

        for (beat <- 0 until 4) {
          dut.io.ret_valid #= true
          dut.io.ret_last #= beat == 3
          dut.io.ret_data #= OtherLineBase + beat
          risingEdge()
        }
        dut.io.ret_valid #= false
        dut.io.ret_last #= false
        sleep(1)

        acceptLoad(OtherColorAddress)
        assert(dut.io.data_ok.toBoolean, "replayed line did not hit after refill")
        assert(dut.io.rdata.toBigInt == OtherLineBase, "replayed line data was corrupted")
        risingEdge()

        acceptLoad(Address)
        assert(dut.io.data_ok.toBoolean, "first physical color was displaced by the second")
        assert(dut.io.rdata.toBigInt == LineBase, "physical colors aliased after replay")
        risingEdge()

        // A new benchmark reset must invalidate the populated line before the CPU can continue.
        dut.io.reset #= true
        risingEdge()
        dut.io.reset #= false
        dut.io.valid #= false
        waitForScrub()

        acceptLoad(Address)
        assert(!dut.io.data_ok.toBoolean, "stale pre-reset line survived the scrub")
        risingEdge()
        sleep(1)
        assert(dut.io.rd_req.toBoolean, "post-reset access did not miss after scrub")
      }
  }
}
