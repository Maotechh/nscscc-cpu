package openla500.ooo

import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooLoadStoreQueueProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val allocateValid = in Bits (config.renameWidth bits)
    val allocate = in Vec (OooLsqAllocate(config), config.renameWidth)
    val aguValid = in Bool ()
    val agu = in(OooAguRequest(config))
    val aguReady = out Bool ()
    val commitValid = in Bits (config.commitWidth bits)
    val commit = in Vec (OooCommitRecord(config), config.commitWidth)
    val dataRequestValid = out Bool ()
    val dataRequest = out(OooCacheRequest(config))
    val dataRequestReady = in Bool ()
    val dataResponseValid = in Bool ()
    val dataResponse = in(OooCacheResponse(config))
    val completionValid = out Bool ()
    val completion = out(OooCompletion(config))
    val releaseLoadValid = out Bits (config.commitWidth bits)
    val releaseStoreValid = out Bits (config.commitWidth bits)
    val flush = in Bool ()
  }
  noIoPrefix()

  val lsq = new OooLoadStoreQueue(config)
  lsq.io.allocateValid := io.allocateValid
  lsq.io.allocate := io.allocate
  lsq.io.aguValid := io.aguValid
  lsq.io.agu := io.agu
  lsq.io.commitValid := io.commitValid
  lsq.io.commit := io.commit
  lsq.io.dataRequestReady := io.dataRequestReady
  lsq.io.dataResponseValid := io.dataResponseValid
  lsq.io.dataResponse := io.dataResponse
  lsq.io.flush := io.flush

  io.aguReady := lsq.io.aguReady
  io.dataRequestValid := lsq.io.dataRequestValid
  io.dataRequest := lsq.io.dataRequest
  io.completionValid := lsq.io.completionValid
  io.completion := lsq.io.completion
  io.releaseLoadValid := lsq.io.releaseLoadValid
  io.releaseStoreValid := lsq.io.releaseStoreValid
}

class OooLoadStoreQueueSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def clearInputs(dut: OooLoadStoreQueueProbe): Unit = {
    dut.io.allocateValid #= 0
    dut.io.aguValid #= false
    dut.io.commitValid #= 0
    dut.io.dataRequestReady #= false
    dut.io.dataResponseValid #= false
    dut.io.flush #= false
    for (lane <- 0 until config.renameWidth) {
      dut.io.allocate(lane).robPointer #= 0
      dut.io.allocate(lane).isLoad #= false
      dut.io.allocate(lane).isStore #= false
      dut.io.allocate(lane).loadQueueIndex #= 0
      dut.io.allocate(lane).storeQueueIndex #= 0
    }
    dut.io.agu.isWrite #= false
    dut.io.agu.virtualAddress #= 0
    dut.io.agu.size #= 2
    dut.io.agu.byteMask #= 0xf
    dut.io.agu.writeData #= 0
    dut.io.agu.uop.robPointer #= 0
    dut.io.agu.uop.pdst #= 0
    dut.io.agu.uop.loadQueueIndex #= 0
    dut.io.agu.uop.storeQueueIndex #= 0
    dut.io.agu.uop.decoded.isSc #= false
    dut.io.agu.uop.decoded.isLoad #= false
    dut.io.agu.uop.decoded.isStore #= false
    dut.io.agu.uop.decoded.writesGpr #= false
    dut.io.agu.uop.decoded.memorySignExtend #= false
    dut.io.agu.uop.decoded.exception.valid #= false
    for (lane <- 0 until config.commitWidth) {
      dut.io.commit(lane).robPointer #= 0
      dut.io.commit(lane).isLoad #= false
      dut.io.commit(lane).isStore #= false
      dut.io.commit(lane).loadQueueIndex #= 0
      dut.io.commit(lane).storeQueueIndex #= 0
      dut.io.commit(lane).exception.valid #= false
    }
    dut.io.dataResponse.robPointer #= 0
    dut.io.dataResponse.pdst #= 0
    dut.io.dataResponse.data #= 0
    dut.io.dataResponse.error #= false
  }

  private def sample(dut: OooLoadStoreQueueProbe): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def setStoreAgu(
      dut: OooLoadStoreQueueProbe,
      pointer: BigInt,
      address: BigInt,
      data: BigInt
  ): Unit = {
    dut.io.aguValid #= true
    dut.io.agu.isWrite #= true
    dut.io.agu.virtualAddress #= address
    dut.io.agu.size #= 2
    dut.io.agu.byteMask #= 0xf
    dut.io.agu.writeData #= data
    dut.io.agu.uop.robPointer #= pointer
    dut.io.agu.uop.storeQueueIndex #= 0
    dut.io.agu.uop.decoded.isStore #= true
  }

  private def setLoadAgu(dut: OooLoadStoreQueueProbe, pointer: BigInt, address: BigInt): Unit = {
    dut.io.aguValid #= true
    dut.io.agu.isWrite #= false
    dut.io.agu.virtualAddress #= address
    dut.io.agu.size #= 2
    dut.io.agu.byteMask #= 0xf
    dut.io.agu.uop.robPointer #= pointer
    dut.io.agu.uop.pdst #= 7
    dut.io.agu.uop.loadQueueIndex #= 0
    dut.io.agu.uop.decoded.isLoad #= true
    dut.io.agu.uop.decoded.writesGpr #= true
  }

  test("store waits for commit and holds a stable request under backpressure") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-store-commit-boundary", 0x4c51) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.allocateValid #= 1
        dut.io.allocate(0).robPointer #= 0
        dut.io.allocate(0).isStore #= true
        dut.io.allocate(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0

        setStoreAgu(dut, 0, 0x100, BigInt("deadbeef", 16))
        sleep(1)
        assert(dut.io.aguReady.toBoolean)
        sample(dut)
        dut.io.aguValid #= false
        assert(!dut.io.dataRequestValid.toBoolean)

        dut.io.commitValid #= 1
        dut.io.commit(0).robPointer #= 0
        dut.io.commit(0).isStore #= true
        dut.io.commit(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.commitValid #= 0
        assert(dut.io.dataRequestValid.toBoolean)
        assert(dut.io.dataRequest.isWrite.toBoolean)
        assert(dut.io.dataRequest.virtualAddress.toBigInt == 0x100)
        assert(dut.io.dataRequest.writeData.toBigInt == BigInt("deadbeef", 16))

        val heldAddress = dut.io.dataRequest.virtualAddress.toBigInt
        val heldData = dut.io.dataRequest.writeData.toBigInt
        sample(dut)
        assert(dut.io.dataRequestValid.toBoolean)
        assert(dut.io.dataRequest.virtualAddress.toBigInt == heldAddress)
        assert(dut.io.dataRequest.writeData.toBigInt == heldData)

        dut.io.dataRequestReady #= true
        sleep(1)
        assert(dut.io.releaseStoreValid.toBigInt == 1)
        sample(dut)
        assert(!dut.io.dataRequestValid.toBoolean)
      }
  }

  test("a single older covering store forwards to a younger load") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-store-forwarding", 0x4c52) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.allocateValid #= 3
        dut.io.allocate(0).robPointer #= 0
        dut.io.allocate(0).isStore #= true
        dut.io.allocate(0).storeQueueIndex #= 0
        dut.io.allocate(1).robPointer #= 1
        dut.io.allocate(1).isLoad #= true
        dut.io.allocate(1).loadQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0

        setStoreAgu(dut, 0, 0x200, BigInt("12345678", 16))
        sleep(1)
        sample(dut)
        dut.io.aguValid #= false

        setLoadAgu(dut, 1, 0x200)
        sleep(1)
        assert(dut.io.aguReady.toBoolean)
        sample(dut)
        sample(dut)
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 1)
        assert(dut.io.completion.pdst.toBigInt == 7)
        assert(dut.io.completion.data.toBigInt == BigInt("12345678", 16))
        assert(!dut.io.dataRequestValid.toBoolean)
        dut.io.aguValid #= false
      }
  }

  test("unknown older stores block loads and stale cache responses are rejected") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-ordering-and-stale-response", 0x4c53) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.allocateValid #= 3
        dut.io.allocate(0).robPointer #= 0
        dut.io.allocate(0).isStore #= true
        dut.io.allocate(0).storeQueueIndex #= 0
        dut.io.allocate(1).robPointer #= 1
        dut.io.allocate(1).isLoad #= true
        dut.io.allocate(1).loadQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0

        setLoadAgu(dut, 1, 0x300)
        sleep(1)
        assert(dut.io.aguReady.toBoolean)
        sample(dut)
        dut.io.aguValid #= false
        sleep(1)
        assert(!dut.io.completionValid.toBoolean)
        assert(!dut.io.dataRequestValid.toBoolean)

        setStoreAgu(dut, 0, 0x400, BigInt("a5a5a5a5", 16))
        sleep(1)
        assert(dut.io.aguReady.toBoolean)
        sample(dut)
        dut.io.aguValid #= false
        sleep(1)
        assert(dut.io.dataRequestValid.toBoolean)
        assert(!dut.io.dataRequest.isWrite.toBoolean)
        assert(dut.io.dataRequest.robPointer.toBigInt == 1)
        assert(dut.io.dataRequest.virtualAddress.toBigInt == 0x300)

        dut.io.dataRequestReady #= true
        sample(dut)
        dut.io.dataRequestReady #= false
        assert(!dut.io.dataRequestValid.toBoolean)

        dut.io.dataResponseValid #= true
        dut.io.dataResponse.robPointer #= 0
        dut.io.dataResponse.data #= BigInt("89abcdef", 16)
        sleep(1)
        assert(!dut.io.completionValid.toBoolean)
        sample(dut)

        dut.io.dataResponse.robPointer #= 1
        sample(dut)
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 1)
        assert(dut.io.completion.data.toBigInt == BigInt("89abcdef", 16))
      }
  }
}
