package openla500.compat

import java.nio.file.Paths
import openla500.memory.OpenLa500ICache
import openla500.pipeline.{FetchPacket, FetchStage}
import openla500.privileged.OpenLa500AddrTrans
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

/** Integration harness for the cycle boundary between fetch, translation and the active I-cache. */
private final class InstructionFrontendIntegrationHarness extends Component {
  val io = new Bundle {
    val clk = in Bool ()
    val reset = in Bool ()
    val directFetchMat = in Bits (2 bits)

    val readReady = in Bool ()
    val returnValid = in Bool ()
    val returnLast = in Bool ()
    val returnData = in Bits (32 bits)

    val readRequest = out Bool ()
    val readType = out Bits (3 bits)
    val readAddress = out Bits (32 bits)
    val scalarResponse = out Bool ()
    val lineResponse = out Bool ()
    val packetValid = out Bool ()
    val packetMask = out Bits (FetchPacket.Width bits)
    val packetPc = out UInt (32 bits)
    val packetInstructions = out(Vec(Bits(32 bits), FetchPacket.Width))
    val keepAlive = out Bits (2048 bits)
  }
  noIoPrefix()

  private val domain = ClockDomain(
    clock = io.clk,
    reset = io.reset,
    config = ClockDomainConfig(
      clockEdge = RISING,
      resetKind = SYNC,
      resetActiveLevel = HIGH
    )
  )

  private val logic = new ClockingArea(domain) {
    val fetch = new FetchStage(fetchPacketEnabled = true)
    val translation = new OpenLa500AddrTrans
    val cache = new OpenLa500ICache(
      setCount = 1024,
      scrubOnReset = true,
      exposeLineResponse = true
    )

    // The direct-address scenario ties off several child ports. Mark those boundaries explicitly,
    // while keepAlive below keeps every produced value and the state feeding it observable.
    Seq(fetch, translation, cache).foreach(
      _.walkComponents(_.getAllIo.foreach(_.allowPruning()))
    )

    fetch.io.downstreamPacket.ready := True
    fetch.io.branchRepair := False
    fetch.io.branchTarget := 0
    fetch.io.exceptionFlush := False
    fetch.io.ertnFlush := False
    fetch.io.refetchFlush := False
    fetch.io.instructionCacheFlush := False
    fetch.io.idleFlush := False
    fetch.io.writebackPc := 0
    fetch.io.exceptionEntry := 0
    fetch.io.exceptionEra := 0
    fetch.io.exceptionTlbRefill := False
    fetch.io.tlbRefillEntry := 0
    fetch.io.interrupt := False
    fetch.io.instructionAddressAccepted := cache.io.addr_ok
    fetch.io.instructionDataValid := cache.io.data_ok && !cache.io.line_valid
    fetch.io.instructionData := cache.io.rdata
    fetch.io.instructionLineValid := cache.io.line_valid
    fetch.io.instructionLineData := cache.io.line_data
    fetch.io.instructionMiss := cache.io.cache_miss
    fetch.io.paging := False
    fetch.io.directAddress := True
    fetch.io.dmw0 := 0
    fetch.io.dmw1 := 0
    fetch.io.currentPlv := 0
    fetch.io.directFetchMat := io.directFetchMat
    fetch.io.disableCache := False
    fetch.io.btbTarget := 0
    fetch.io.btbTaken := False
    fetch.io.btbEnabled := False
    fetch.io.btbIndex := 0
    fetch.io.btbDirection.phtIndex := 0
    fetch.io.btbDirection.baseTaken := False
    fetch.io.btbDirection.localTaken := False
    fetch.io.tlbFound := True
    fetch.io.tlbValid := True
    fetch.io.tlbMat := B"2'b01"
    fetch.io.tlbPlv := 0

    translation.io.clk := io.clk
    translation.io.asid := 0
    translation.io.inst_addr_trans_en := fetch.io.addressTranslation
    translation.io.inst_fetch := fetch.io.fetchEnable
    translation.io.inst_vaddr := fetch.io.instructionAddress.asBits
    translation.io.inst_dmw0_en := fetch.io.dmw0Enabled
    translation.io.inst_dmw1_en := fetch.io.dmw1Enabled
    translation.io.data_addr_trans_en := False
    translation.io.data_fetch := False
    translation.io.data_vaddr := 0
    translation.io.data_dmw0_en := False
    translation.io.data_dmw1_en := False
    translation.io.cacop_op_mode_di := False
    translation.io.tlbfill_en := False
    translation.io.tlbwr_en := False
    translation.io.rand_index := 0
    translation.io.tlbehi_in := 0
    translation.io.tlbelo0_in := 0
    translation.io.tlbelo1_in := 0
    translation.io.tlbidx_in := 0
    translation.io.ecode_in := 0
    translation.io.invtlb_en := False
    translation.io.invtlb_asid := 0
    translation.io.invtlb_vpn := 0
    translation.io.invtlb_op := 0
    translation.io.csr_dmw0 := 0
    translation.io.csr_dmw1 := 0
    translation.io.csr_da := True
    translation.io.csr_pg := False

    cache.io.clk := io.clk
    cache.io.reset := io.reset
    cache.io.valid := fetch.io.instructionRequest
    cache.io.op := False
    cache.io.index := translation.io.inst_index
    cache.io.tag := translation.io.inst_tag
    cache.io.speculativeColor := fetch.io.instructionAddress(13 downto 12).asBits
    cache.io.offset := translation.io.inst_offset
    cache.io.wstrb := 0
    cache.io.wdata := 0
    cache.io.uncache_en := fetch.io.instructionUncached
    cache.io.icacop_op_en := False
    cache.io.cacop_op_mode := 0
    cache.io.cacop_op_addr_index := 0
    cache.io.cacop_op_addr_tag := 0
    cache.io.cacop_op_addr_offset := 0
    cache.io.tlb_excp_cancel_req := fetch.io.tlbCancel
    cache.io.rd_rdy := io.readReady
    cache.io.ret_valid := io.returnValid
    cache.io.ret_last := io.returnLast
    cache.io.ret_data := io.returnData
    cache.io.wr_rdy := True
  }

  io.readRequest := logic.cache.io.rd_req
  io.readType := logic.cache.io.rd_type
  io.readAddress := logic.cache.io.rd_addr
  io.scalarResponse := logic.cache.io.data_ok
  io.lineResponse := logic.cache.io.line_valid
  io.packetValid := logic.fetch.io.downstreamPacket.valid
  io.packetMask := logic.fetch.io.downstreamPacket.payload.slotValid
  io.packetPc := logic.fetch.io.downstreamPacket.payload.slots(0).fetch.pc
  for (lane <- 0 until FetchPacket.Width) {
    io.packetInstructions(lane) :=
      logic.fetch.io.downstreamPacket.payload.slots(lane).fetch.instruction
  }
  io.keepAlive := (
    logic.fetch.io.downstreamPacket.payload.asBits ##
      logic.fetch.io.fetchPc.asBits ##
      logic.translation.io.inst_tlb_found.asBits ##
      logic.translation.io.inst_tlb_v.asBits ##
      logic.translation.io.inst_tlb_d.asBits ##
      logic.translation.io.inst_tlb_mat ##
      logic.translation.io.inst_tlb_plv ##
      logic.translation.io.data_index ##
      logic.translation.io.data_tag ##
      logic.translation.io.data_offset ##
      logic.translation.io.data_tlb_found.asBits ##
      logic.translation.io.data_tlb_index ##
      logic.translation.io.data_tlb_v.asBits ##
      logic.translation.io.data_tlb_d.asBits ##
      logic.translation.io.data_tlb_mat ##
      logic.translation.io.data_tlb_plv ##
      logic.translation.io.tlbehi_out ##
      logic.translation.io.tlbelo0_out ##
      logic.translation.io.tlbelo1_out ##
      logic.translation.io.tlbidx_out ##
      logic.translation.io.asid_out ##
      logic.cache.io.icache_unbusy.asBits ##
      logic.cache.io.cache_miss.asBits ##
      logic.cache.io.wr_req.asBits ##
      logic.cache.io.wr_type ##
      logic.cache.io.wr_addr ##
      logic.cache.io.wr_wstrb ##
      logic.cache.io.wr_data
  ).resize(2048)
}

class InstructionFrontendIntegrationSpec extends AnyFunSuite {
  private val ResetVector = BigInt("1c000000", 16)
  private val Words = Vector(
    BigInt("02800421", 16),
    BigInt("02800842", 16),
    BigInt("02800c63", 16),
    BigInt("02801084", 16)
  )

  private def simulationConfig(workspace: String) =
    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true, removePruned = false))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .addSimulatorFlag("-Wno-UNUSEDSIGNAL")
      .disableCache
      .workspacePath(workspace)

  private def initialize(dut: InstructionFrontendIntegrationHarness, mat: Int): Unit = {
    dut.io.clk #= false
    dut.io.reset #= true
    dut.io.directFetchMat #= mat
    dut.io.readReady #= false
    dut.io.returnValid #= false
    dut.io.returnLast #= false
    dut.io.returnData #= 0
  }

  private def risingEdge(dut: InstructionFrontendIntegrationHarness): Unit = {
    dut.io.clk #= false
    sleep(2)
    dut.io.clk #= true
    sleep(2)
    dut.io.clk #= false
    sleep(2)
  }

  private def waitForFirstRead(dut: InstructionFrontendIntegrationHarness): Unit = {
    risingEdge(dut)
    risingEdge(dut)
    dut.io.reset #= false
    var cycles = 0
    while (!dut.io.readRequest.toBoolean && cycles < 1040) {
      risingEdge(dut)
      cycles += 1
    }
    assert(dut.io.readRequest.toBoolean, "frontend did not issue its first post-scrub read")
  }

  test("uncached reset-vector fetch uses the translated request address") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-frontend-integration")
    val workspace = Paths.get(workspaceRoot, "uncached-reset-vector").toString
    val compiled = simulationConfig(workspace).compile(new InstructionFrontendIntegrationHarness)

    compiled.doSim("uncached-reset-vector", 0x158aa8) { dut =>
      initialize(dut, mat = 0)
      waitForFirstRead(dut)
      assert(dut.io.readType.toInt == 2, "reset-vector fetch was not scalar/uncached")
      assert(
        dut.io.readAddress.toBigInt == ResetVector,
        f"first fetch used stale translated address 0x${dut.io.readAddress.toBigInt}%08x"
      )

      dut.io.readReady #= true
      risingEdge(dut)
      dut.io.returnValid #= true
      dut.io.returnLast #= true
      dut.io.returnData #= Words.head
      sleep(1)
      assert(dut.io.scalarResponse.toBoolean)
      assert(!dut.io.lineResponse.toBoolean)
      assert(dut.io.packetValid.toBoolean)
      assert(dut.io.packetMask.toInt == 1)
      assert(dut.io.packetPc.toBigInt == ResetVector)
      assert(dut.io.packetInstructions(0).toBigInt == Words.head)

      risingEdge(dut)
      dut.io.returnValid #= false
      dut.io.returnLast #= false
      sleep(1)
      assert(!dut.io.packetValid.toBoolean, "uncached response was consumed more than once")
    }
  }

  test("cacheable refill emits one complete packet and no critical-word packet") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-frontend-integration")
    val workspace = Paths.get(workspaceRoot, "cacheable-single-response").toString
    val compiled = simulationConfig(workspace).compile(new InstructionFrontendIntegrationHarness)

    compiled.doSim("cacheable-single-response", 0x158aa9) { dut =>
      initialize(dut, mat = 1)
      waitForFirstRead(dut)
      assert(dut.io.readType.toInt == 4, "cacheable fetch did not request a cache line")
      assert(dut.io.readAddress.toBigInt == ResetVector)

      dut.io.readReady #= true
      risingEdge(dut)
      for (beat <- Words.indices) {
        dut.io.returnValid #= true
        dut.io.returnLast #= beat == Words.size - 1
        dut.io.returnData #= Words(beat)
        sleep(1)
        assert(
          !dut.io.scalarResponse.toBoolean,
          s"cacheable refill emitted a scalar response on beat $beat"
        )
        if (beat == Words.size - 1) {
          assert(dut.io.lineResponse.toBoolean)
          assert(dut.io.packetValid.toBoolean)
          assert(dut.io.packetMask.toInt == 0xf)
          assert(dut.io.packetPc.toBigInt == ResetVector)
          for (lane <- Words.indices) {
            assert(dut.io.packetInstructions(lane).toBigInt == Words(lane))
          }
        } else {
          assert(!dut.io.lineResponse.toBoolean)
          assert(!dut.io.packetValid.toBoolean, s"partial line escaped on beat $beat")
        }
        risingEdge(dut)
      }

      dut.io.returnValid #= false
      dut.io.returnLast #= false
      sleep(1)
      assert(!dut.io.packetValid.toBoolean, "completed line response was consumed more than once")
    }
  }
}
