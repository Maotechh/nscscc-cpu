package openla500.memory

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

/** Directed protocol checks for the optional write-back/read overlap mode. */
class OpenLa500AxiBridgeOverlapSpec extends AnyFunSuite {
  private def init(dut: OpenLa500AxiBridge): Unit = {
    dut.io.clk #= false
    dut.io.reset #= true
    dut.io.arready #= false
    dut.io.rid #= 0
    dut.io.rdata #= 0
    dut.io.rresp #= 0
    dut.io.rlast #= false
    dut.io.rvalid #= false
    dut.io.awready #= false
    dut.io.wready #= false
    dut.io.bid #= 0
    dut.io.bresp #= 0
    dut.io.bvalid #= false
    dut.io.inst_rd_req #= false
    dut.io.inst_rd_type #= 2
    dut.io.inst_rd_addr #= 0
    dut.io.inst_wr_req #= false
    dut.io.inst_wr_type #= 2
    dut.io.inst_wr_addr #= 0
    dut.io.inst_wr_wstrb #= 0
    dut.io.inst_wr_data #= 0
    dut.io.data_rd_req #= false
    dut.io.data_rd_type #= 2
    dut.io.data_rd_addr #= 0
    dut.io.data_wr_req #= false
    dut.io.data_wr_type #= 2
    dut.io.data_wr_addr #= 0
    dut.io.data_wr_wstrb #= 0xf
    dut.io.data_wr_data #= BigInt("00112233445566778899aabbccddeeff", 16)
  }

  private def edge(dut: OpenLa500AxiBridge): Unit = {
    dut.io.clk #= false
    sleep(1)
    dut.io.clk #= true
    sleep(1)
    dut.io.clk #= false
    sleep(1)
  }

  private def startCacheLineWrite(dut: OpenLa500AxiBridge): Unit = {
    dut.io.data_wr_type #= 4
    dut.io.data_wr_req #= true
    sleep(1)
    assert(dut.io.data_wr_rdy.toBoolean)
    edge(dut)
    dut.io.data_wr_req #= false
    sleep(1)
    assert(dut.io.awvalid.toBoolean)
  }

  private def startScalarWrite(dut: OpenLa500AxiBridge): Unit = {
    dut.io.data_wr_type #= 2
    dut.io.data_wr_req #= true
    sleep(1)
    assert(dut.io.data_wr_rdy.toBoolean)
    edge(dut)
    dut.io.data_wr_req #= false
    sleep(1)
  }

  private def runCase(allowOverlap: Boolean, workspaceName: String): Unit = {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-axi-bridge-overlap")
    val workspace = Paths.get(workspaceRoot, workspaceName).toString
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
      .compile(new OpenLa500AxiBridge(allowCacheLineReadOverlap = allowOverlap))
      .doSim(s"axi-bridge-overlap-$workspaceName", 0x158aa8) { dut =>
        init(dut)
        edge(dut)
        dut.io.reset #= false
        edge(dut)

        startCacheLineWrite(dut)
        sleep(1)
        assert(
          dut.io.data_rd_rdy.toBoolean == allowOverlap,
          s"cache-line overlap mismatch while AW is pending for allowOverlap=$allowOverlap"
        )
        dut.io.awready #= true
        edge(dut)
        dut.io.awready #= false
        sleep(1)
        assert(
          dut.io.data_rd_rdy.toBoolean == allowOverlap,
          s"cache-line overlap mismatch while W is active for allowOverlap=$allowOverlap"
        )
        assert(!dut.io.write_buffer_empty.toBoolean, "writeback became empty before W completed")

        dut.io.wready #= true
        for (_ <- 0 until 4) {
          assert(
            dut.io.data_rd_rdy.toBoolean == allowOverlap,
            s"cache-line overlap mismatch between W beats for allowOverlap=$allowOverlap"
          )
          edge(dut)
        }
        dut.io.wready #= false
        sleep(1)
        assert(
          dut.io.data_rd_rdy.toBoolean == allowOverlap,
          s"cache-line overlap mismatch while B is pending for allowOverlap=$allowOverlap"
        )
        assert(!dut.io.write_buffer_empty.toBoolean, "writeback became empty before B completed")

        dut.io.data_rd_req #= true
        dut.io.data_rd_addr #= BigInt("10000100", 16)
        dut.io.data_rd_type #= 4
        sleep(1)
        if (allowOverlap) {
          edge(dut)
          dut.io.data_rd_req #= false
          sleep(1)
          assert(dut.io.arvalid.toBoolean, "read address was not captured during line writeback")
          assert(dut.io.arid.toBigInt == 1, "data read lost its AXI routing id")
          dut.io.arready #= true
          edge(dut)
          dut.io.arready #= false
        } else {
          dut.io.data_rd_req #= false
          edge(dut)
          assert(!dut.io.arvalid.toBoolean, "legacy bridge issued a read during line writeback")
        }

        dut.io.bvalid #= true
        edge(dut)
        dut.io.bvalid #= false
        edge(dut)
        assert(dut.io.write_buffer_empty.toBoolean, "completed writeback did not become empty")

        // A scalar/uncached store must remain ordered even in the active overlap profile.
        startScalarWrite(dut)
        dut.io.inst_rd_req #= true
        dut.io.inst_rd_addr #= BigInt("20000200", 16)
        sleep(1)
        assert(
          !dut.io.inst_rd_rdy.toBoolean,
          "scalar write incorrectly allowed a read while AW was pending"
        )
        dut.io.awready #= true
        edge(dut)
        dut.io.awready #= false
        assert(
          !dut.io.inst_rd_rdy.toBoolean,
          "scalar write incorrectly allowed a read while W was active"
        )
        dut.io.wready #= true
        edge(dut)
        dut.io.wready #= false
        assert(
          !dut.io.inst_rd_rdy.toBoolean,
          "scalar write incorrectly allowed a read while B was pending"
        )
        assert(!dut.io.write_buffer_empty.toBoolean, "scalar write became empty before B completed")
        dut.io.inst_rd_req #= false
        dut.io.bvalid #= true
        edge(dut)
        dut.io.bvalid #= false
        edge(dut)
        assert(dut.io.write_buffer_empty.toBoolean, "completed scalar write did not become empty")
      }
  }

  test("cache-line writeback overlap is explicit and scalar writes remain ordered") {
    runCase(allowOverlap = false, "legacy")
    runCase(allowOverlap = true, "active")
  }
}
