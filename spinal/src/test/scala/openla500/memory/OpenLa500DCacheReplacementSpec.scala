package openla500.memory

import java.nio.file.Paths
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OpenLa500DCacheReplacementTop extends Component {
  val io = new Bundle {
    val coreClk = in Bool ()
    val coreReset = in Bool ()
    val valid = in Bool ()
    val address = in UInt (32 bits)
    val op = in Bool ()
    val size = in Bits (3 bits)
    val writeStrobe = in Bits (4 bits)
    val writeData = in Bits (32 bits)
    val uncacheEnable = in Bool ()
    val cacopEnable = in Bool ()
    val cacopMode = in Bits (2 bits)
    val preldHint = in Bits (5 bits)
    val preldEnable = in Bool ()
    val tlbCancel = in Bool ()
    val scCancel = in Bool ()
    val addrOk = out Bool ()
    val dataOk = out Bool ()
    val readData = out Bits (32 bits)
    val cacheEmpty = out Bool ()
    val readRequest = out Bool ()
    val readType = out Bits (3 bits)
    val readAddress = out Bits (32 bits)
    val readReady = in Bool ()
    val returnValid = in Bool ()
    val returnLast = in Bool ()
    val returnData = in Bits (32 bits)
    val writeRequest = out Bool ()
    val writeType = out Bits (3 bits)
    val writeAddress = out Bits (32 bits)
    val busWriteStrobe = out Bits (4 bits)
    val busWriteData = out Bits (128 bits)
    val writeReady = in Bool ()
    val cacheMiss = out Bool ()
  }

  private val cache = new OpenLa500DCache
  cache.io.clk := io.coreClk
  cache.io.reset := io.coreReset
  cache.io.valid := io.valid
  cache.io.op := io.op
  cache.io.size := io.size
  cache.io.index := io.address(11 downto 4).asBits
  cache.io.tag := io.address(31 downto 12).asBits
  cache.io.offset := io.address(3 downto 0).asBits
  cache.io.wstrb := io.writeStrobe
  cache.io.wdata := io.writeData
  cache.io.uncache_en := io.uncacheEnable
  cache.io.dcacop_op_en := io.cacopEnable
  cache.io.cacop_op_mode := io.cacopMode
  cache.io.preld_hint := io.preldHint
  cache.io.preld_hint.allowPruning()
  cache.io.preld_en := io.preldEnable
  cache.io.tlb_excp_cancel_req := io.tlbCancel
  cache.io.sc_cancel_req := io.scCancel
  cache.io.rd_rdy := io.readReady
  cache.io.ret_valid := io.returnValid
  cache.io.ret_last := io.returnLast
  cache.io.ret_data := io.returnData
  cache.io.wr_rdy := io.writeReady

  io.addrOk := cache.io.addr_ok
  io.dataOk := cache.io.data_ok
  io.readData := cache.io.rdata
  io.cacheEmpty := cache.io.dcache_empty
  io.readRequest := cache.io.rd_req
  io.readType := cache.io.rd_type
  io.readAddress := cache.io.rd_addr
  io.writeRequest := cache.io.wr_req
  io.writeType := cache.io.wr_type
  io.writeAddress := cache.io.wr_addr
  io.busWriteStrobe := cache.io.wr_wstrb
  io.busWriteData := cache.io.wr_data
  io.cacheMiss := cache.io.cache_miss
}

class OpenLa500DCacheReplacementSpec extends AnyFunSuite {
  test("per-set pseudo-LRU retains the re-accessed way") {
    val workspaceRoot = sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace")
    val workspace = Paths.get(workspaceRoot, "dcache-pseudo-lru").toString

    val compiled = SimConfig
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
      .compile(new OpenLa500DCacheReplacementTop)
    compiled.doSim("dcache-pseudo-lru", 0x158aa8) { dut =>
      dut.io.coreClk #= false
      dut.io.coreReset #= true
      dut.io.valid #= false
      dut.io.address #= 0
      dut.io.op #= false
      dut.io.size #= 2
      dut.io.writeStrobe #= 0
      dut.io.writeData #= 0
      dut.io.uncacheEnable #= false
      dut.io.cacopEnable #= false
      dut.io.cacopMode #= 0
      dut.io.preldHint #= 0
      dut.io.preldEnable #= false
      dut.io.tlbCancel #= false
      dut.io.scCancel #= false
      dut.io.readReady #= false
      dut.io.returnValid #= false
      dut.io.returnLast #= false
      dut.io.returnData #= 0
      dut.io.writeReady #= true

      def coreRisingEdge(): Unit = {
        dut.io.coreClk #= false
        sleep(2)
        dut.io.coreClk #= true
        sleep(2)
        dut.io.coreClk #= false
        sleep(2)
      }

      coreRisingEdge()
      coreRisingEdge()
      dut.io.coreReset #= false
      coreRisingEdge()

      def accept(address: BigInt): Unit = {
        dut.io.address #= address
        dut.io.valid #= true
        var cycles = 0
        while (!dut.io.addrOk.toBoolean && cycles < 16) {
          coreRisingEdge()
          cycles += 1
        }
        assert(dut.io.addrOk.toBoolean, f"request 0x$address%08x was not accepted")
        coreRisingEdge()
        dut.io.valid #= false
      }

      def outcome(): Boolean = {
        var cycles = 0
        while (!dut.io.dataOk.toBoolean && !dut.io.readRequest.toBoolean && cycles < 16) {
          coreRisingEdge()
          cycles += 1
        }
        assert(
          dut.io.dataOk.toBoolean || dut.io.readRequest.toBoolean,
          "cache request produced neither a hit nor a refill"
        )
        dut.io.dataOk.toBoolean
      }

      def refill(lineAddress: BigInt, seed: Int): Unit = {
        assert(dut.io.readRequest.toBoolean, "refill requested without rd_req")
        assert(
          dut.io.readAddress.toBigInt == lineAddress,
          f"unexpected refill address 0x${dut.io.readAddress.toBigInt}%08x"
        )
        dut.io.readReady #= true
        coreRisingEdge()
        dut.io.readReady #= false
        for (word <- 0 until 4) {
          dut.io.returnValid #= true
          dut.io.returnLast #= word == 3
          dut.io.returnData #= seed + word
          coreRisingEdge()
        }
        dut.io.returnValid #= false
        dut.io.returnLast #= false
        coreRisingEdge()
      }

      def expectMiss(address: BigInt, seed: Int): Unit = {
        accept(address)
        assert(!outcome(), f"expected miss at 0x$address%08x")
        refill(address & ~BigInt(0xf), seed)
      }

      def expectHit(address: BigInt): Unit = {
        accept(address)
        assert(outcome(), f"expected hit at 0x$address%08x")
        coreRisingEdge()
      }

      val lineA = BigInt("00001000", 16)
      val lineB = BigInt("00002000", 16)
      val lineC = BigInt("00003000", 16)

      expectMiss(lineA, 0x10)
      expectMiss(lineB, 0x20)
      expectHit(lineA)
      expectMiss(lineC, 0x30)
      expectHit(lineA)
      expectMiss(lineB, 0x40)
    }
  }
}
