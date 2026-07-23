package openla500.memory

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

class OpenLa500ICacheLineSpec extends AnyFunSuite {
  private val SetCount = 1024
  private val Address = BigInt("1c123048", 16)
  private val Words = Vector(
    BigInt("02800421", 16),
    BigInt("02800842", 16),
    BigInt("02800c63", 16),
    BigInt("02801084", 16)
  )

  private def packedLine(words: Seq[BigInt]): BigInt =
    words.zipWithIndex.foldLeft(BigInt(0)) { case (line, (word, index)) =>
      line | ((word & BigInt("ffffffff", 16)) << (index * 32))
    }

  test("active I-cache returns all hit words and includes the final refill beat") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-icache-line")
    val workspace = Paths.get(workspaceRoot, "whole-line-response").toString

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
      .compile(
        new OpenLa500ICache(
          setCount = SetCount,
          scrubOnReset = true,
          exposeLineResponse = true
        )
      )
      .doSim("icache-whole-line", 0x158aa8) { dut =>
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

        def driveAddress(address: BigInt): Unit = {
          dut.io.tag #= (address >> 12) & ((BigInt(1) << 20) - 1)
          dut.io.speculativeColor #= (address >> 12) & 3
          dut.io.index #= (address >> 4) & 0xff
          dut.io.offset #= address & 0xf
        }

        dut.io.reset #= false
        for (_ <- 0 until SetCount) risingEdge()
        sleep(1)
        assert(dut.io.icache_unbusy.toBoolean)

        driveAddress(Address)
        dut.io.valid #= true
        sleep(1)
        assert(dut.io.addr_ok.toBoolean)
        risingEdge()
        dut.io.valid #= false
        risingEdge()
        sleep(1)
        assert(dut.io.rd_req.toBoolean)
        assert(dut.io.rd_addr.toBigInt == (Address & ~BigInt(0xf)))
        risingEdge()

        for (beat <- Words.indices) {
          dut.io.ret_valid #= true
          dut.io.ret_last #= beat == Words.size - 1
          dut.io.ret_data #= Words(beat)
          sleep(1)
          assert(
            !dut.io.data_ok.toBoolean,
            s"wide cacheable refill emitted a scalar response on beat $beat"
          )
          if (beat == Words.size - 1) {
            assert(dut.io.line_valid.toBoolean)
            assert(dut.io.line_data.toBigInt == packedLine(Words))
          } else {
            assert(!dut.io.line_valid.toBoolean)
          }
          risingEdge()
        }
        dut.io.ret_valid #= false
        dut.io.ret_last #= false
        sleep(1)
        assert(dut.io.icache_unbusy.toBoolean)

        driveAddress(Address)
        dut.io.valid #= true
        sleep(1)
        assert(dut.io.addr_ok.toBoolean)
        risingEdge()
        dut.io.valid #= false
        sleep(1)
        assert(dut.io.data_ok.toBoolean)
        assert(dut.io.rdata.toBigInt == Words(2))
        assert(dut.io.line_valid.toBoolean)
        assert(dut.io.line_data.toBigInt == packedLine(Words))
      }
  }
}
