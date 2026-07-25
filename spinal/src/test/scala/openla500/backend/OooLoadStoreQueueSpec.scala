package openla500.backend

import openla500.core._
import openla500.execute._
import openla500.memory._
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
    val translationFault = in Bool ()
    val translationEcode = in UInt (6 bits)
    val translationResponseEnable = in Bool ()
    val translationRequestValid = out Bool ()
    val reservationValid = in Bool ()
    val reservationLineAddress = in Bits (28 bits)
    val completionValid = out Bool ()
    val completion = out(OooCompletion(config))
    val releaseLoadValid = out Bits (config.commitWidth bits)
    val releaseStoreValid = out Bits (config.commitWidth bits)
    val storeDrainBusy = out Bool ()
    val flush = in Bool ()
  }
  noIoPrefix()

  val lsq = new OooLoadStoreQueue(config)
  val translationValid = RegInit(False)
  val translationAddress = Reg(UInt(config.xlen bits))
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
  lsq.io.translationRequest.ready := !translationValid ||
    (lsq.io.translationResponse.valid && lsq.io.translationResponse.ready)
  io.translationRequestValid := lsq.io.translationRequest.valid
  val translationRequestFire =
    lsq.io.translationRequest.valid && lsq.io.translationRequest.ready
  when(lsq.io.translationResponse.valid && lsq.io.translationResponse.ready) {
    translationValid := False
  }
  when(translationRequestFire) {
    translationValid := True
    translationAddress := lsq.io.translationRequest.virtualAddress
  }
  lsq.io.translationResponse.valid := translationValid && io.translationResponseEnable
  lsq.io.translationResponse.virtualAddress := translationAddress
  lsq.io.translationResponse.physicalAddress := translationAddress
  lsq.io.translationResponse.uncached := False
  lsq.io.translationResponse.exception.valid := io.translationFault
  lsq.io.translationResponse.exception.ecode := io.translationEcode
  lsq.io.translationResponse.exception.esubcode := 0
  lsq.io.translationResponse.exception.badVAddrValid := io.translationFault
  lsq.io.translationResponse.exception.badVAddr := translationAddress
  lsq.io.translationResponse.exception.tlbRefill := False
  lsq.io.reservationValid := io.reservationValid
  lsq.io.reservationLineAddress := io.reservationLineAddress
  lsq.io.orderingRobPointer := 0

  io.aguReady := lsq.io.aguReady
  io.dataRequestValid := lsq.io.dataRequestValid
  io.dataRequest := lsq.io.dataRequest
  io.completionValid := lsq.io.completionValid
  io.completion := lsq.io.completion
  io.releaseLoadValid := lsq.io.releaseLoadValid
  io.releaseStoreValid := lsq.io.releaseStoreValid
  io.storeDrainBusy := lsq.io.storeDrainBusy
}

class OooLoadStoreQueueSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def clearInputs(dut: OooLoadStoreQueueProbe): Unit = {
    dut.io.allocateValid #= 0
    dut.io.aguValid #= false
    dut.io.commitValid #= 0
    dut.io.dataRequestReady #= false
    dut.io.dataResponseValid #= false
    dut.io.translationFault #= false
    dut.io.translationEcode #= 0
    dut.io.translationResponseEnable #= true
    dut.io.reservationValid #= false
    dut.io.reservationLineAddress #= 0
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
    dut.io.agu.uop.decoded.isLl #= false
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
      data: BigInt,
      storeIndex: Int = 0,
      isSc: Boolean = false,
      pdst: Int = 0
  ): Unit = {
    dut.io.aguValid #= true
    dut.io.agu.isWrite #= true
    dut.io.agu.virtualAddress #= address
    dut.io.agu.size #= 2
    dut.io.agu.byteMask #= 0xf
    dut.io.agu.writeData #= data
    dut.io.agu.uop.robPointer #= pointer
    dut.io.agu.uop.pdst #= pdst
    dut.io.agu.uop.storeQueueIndex #= storeIndex
    dut.io.agu.uop.decoded.isStore #= true
    dut.io.agu.uop.decoded.isSc #= isSc
    dut.io.agu.uop.decoded.writesGpr #= isSc
  }

  private def setLoadAgu(
      dut: OooLoadStoreQueueProbe,
      pointer: BigInt,
      address: BigInt,
      isLl: Boolean = false,
      loadIndex: Int = 0,
      pdst: Int = 7
  ): Unit = {
    dut.io.aguValid #= true
    dut.io.agu.isWrite #= false
    dut.io.agu.virtualAddress #= address
    dut.io.agu.size #= 2
    dut.io.agu.byteMask #= 0xf
    dut.io.agu.uop.robPointer #= pointer
    dut.io.agu.uop.pdst #= pdst
    dut.io.agu.uop.loadQueueIndex #= loadIndex
    dut.io.agu.uop.decoded.isLoad #= true
    dut.io.agu.uop.decoded.isLl #= isLl
    dut.io.agu.uop.decoded.writesGpr #= true
  }

  test("recycled load slots initialize and advance the circular scheduling base") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-recycled-slot-age", 0x4c58) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        // This is the state reached when commit-time slot reuse laps the old
        // execution pointer: the older load occupies a numerically later slot.
        dut.io.allocateValid #= 3
        dut.io.allocate(0).robPointer #= 34
        dut.io.allocate(0).isLoad #= true
        dut.io.allocate(0).loadQueueIndex #= 0
        dut.io.allocate(1).robPointer #= 18
        dut.io.allocate(1).isLoad #= true
        dut.io.allocate(1).loadQueueIndex #= 4
        sample(dut)
        dut.io.allocateValid #= 0

        setLoadAgu(dut, pointer = 34, address = 0x340, loadIndex = 0, pdst = 9)
        sample(dut)
        dut.io.aguValid #= false
        setLoadAgu(dut, pointer = 18, address = 0x180, loadIndex = 4, pdst = 8)
        sample(dut)
        dut.io.aguValid #= false

        var requestWait = 0
        while (!dut.io.dataRequestValid.toBoolean && requestWait < 12) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.dataRequestValid.toBoolean)
        assert(dut.io.dataRequest.robPointer.toBigInt == 18)
        assert(dut.io.dataRequest.virtualAddress.toBigInt == 0x180)

        dut.io.dataRequestReady #= true
        sample(dut)
        dut.io.dataRequestReady #= false
        dut.io.dataResponseValid #= true
        dut.io.dataResponse.robPointer #= 18
        dut.io.dataResponse.data #= BigInt("18181818", 16)
        sample(dut)
        dut.io.dataResponseValid #= false
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 18)

        dut.io.commitValid #= 1
        dut.io.commit(0).robPointer #= 18
        dut.io.commit(0).isLoad #= true
        dut.io.commit(0).loadQueueIndex #= 4
        sample(dut)
        dut.io.commitValid #= 0

        requestWait = 0
        while (!dut.io.dataRequestValid.toBoolean && requestWait < 12) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.dataRequestValid.toBoolean)
        assert(dut.io.dataRequest.robPointer.toBigInt == 34)
        assert(dut.io.dataRequest.virtualAddress.toBigInt == 0x340)
      }
  }

  test("independent loads issue before the first response and complete by ROB tag") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-multiple-outstanding-loads", 0x4c5b) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.allocateValid #= 3
        dut.io.allocate(0).robPointer #= 0
        dut.io.allocate(0).isLoad #= true
        dut.io.allocate(0).loadQueueIndex #= 0
        dut.io.allocate(1).robPointer #= 1
        dut.io.allocate(1).isLoad #= true
        dut.io.allocate(1).loadQueueIndex #= 1
        sample(dut)
        dut.io.allocateValid #= 0

        setLoadAgu(dut, pointer = 0, address = 0x100, loadIndex = 0, pdst = 8)
        sample(dut)
        setLoadAgu(dut, pointer = 1, address = 0x180, loadIndex = 1, pdst = 9)
        sample(dut)
        dut.io.aguValid #= false
        dut.io.dataRequestReady #= true

        val requests = scala.collection.mutable.ArrayBuffer.empty[BigInt]
        var requestWait = 0
        while (requests.size < 2 && requestWait < 24) {
          if (dut.io.dataRequestValid.toBoolean) {
            requests += dut.io.dataRequest.robPointer.toBigInt
          }
          sample(dut)
          requestWait += 1
        }
        assert(requests.toSeq == Seq(BigInt(0), BigInt(1)))
        dut.io.dataRequestReady #= false

        dut.io.dataResponseValid #= true
        dut.io.dataResponse.robPointer #= 1
        dut.io.dataResponse.data #= BigInt("11111111", 16)
        sample(dut)
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 1)
        assert(dut.io.completion.pdst.toBigInt == 9)

        dut.io.dataResponse.robPointer #= 0
        dut.io.dataResponse.data #= BigInt("01010101", 16)
        sample(dut)
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 0)
        assert(dut.io.completion.pdst.toBigInt == 8)
      }
  }

  test("a committed store survives a recovery flush and drains before restart") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-committed-store-flush-drain", 0x4c59) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.allocateValid #= 1
        dut.io.allocate(0).robPointer #= 9
        dut.io.allocate(0).isStore #= true
        dut.io.allocate(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0

        setStoreAgu(dut, 9, 0x1d0000, 0xf)
        sample(dut)
        dut.io.aguValid #= false
        var completionWait = 0
        while (!dut.io.completionValid.toBoolean && completionWait < 8) {
          sample(dut)
          completionWait += 1
        }
        assert(dut.io.completionValid.toBoolean)

        dut.io.commitValid #= 1
        dut.io.commit(0).robPointer #= 9
        dut.io.commit(0).isStore #= true
        dut.io.commit(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.commitValid #= 0

        dut.io.flush #= true
        sample(dut)
        dut.io.flush #= false
        sleep(1)
        assert(dut.io.storeDrainBusy.toBoolean)
        var requestWait = 0
        while (!dut.io.dataRequestValid.toBoolean && requestWait < 4) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.dataRequestValid.toBoolean)
        assert(dut.io.dataRequest.isWrite.toBoolean)
        assert(dut.io.dataRequest.virtualAddress.toBigInt == 0x1d0000)
        assert(dut.io.dataRequest.writeData.toBigInt == 0xf)

        dut.io.dataRequestReady #= true
        sample(dut)
        dut.io.dataRequestReady #= false
        var drainWait = 0
        while (dut.io.storeDrainBusy.toBoolean && drainWait < 4) {
          sample(dut)
          drainWait += 1
        }
        assert(!dut.io.storeDrainBusy.toBoolean)

        dut.io.allocateValid #= 1
        dut.io.allocate(0).robPointer #= 10
        dut.io.allocate(0).isStore #= true
        dut.io.allocate(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0
        setStoreAgu(dut, 10, 0x1d0004, 0x10)
        sample(dut)
        dut.io.aguValid #= false
        var reusedCompletionWait = 0
        while (!dut.io.completionValid.toBoolean && reusedCompletionWait < 8) {
          sample(dut)
          reusedCompletionWait += 1
        }
        assert(dut.io.completionValid.toBoolean)
      }
  }

  test("a translation response invalidated by flush is drained before slot reuse") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-translation-flush-cancel", 0x4c5a) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.allocateValid #= 1
        dut.io.allocate(0).robPointer #= 9
        dut.io.allocate(0).isStore #= true
        dut.io.allocate(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0

        setStoreAgu(dut, 9, 0x1d0000, 0xf)
        sample(dut)
        dut.io.aguValid #= false
        dut.io.translationResponseEnable #= false
        sample(dut)

        // Redirect after the request handshake but before its response. The
        // response belongs to the discarded epoch and must only be consumed.
        dut.io.flush #= true
        sample(dut)
        dut.io.flush #= false
        dut.io.translationResponseEnable #= true
        sample(dut)
        assert(!dut.io.completionValid.toBoolean)

        dut.io.allocateValid #= 1
        dut.io.allocate(0).robPointer #= 10
        dut.io.allocate(0).isStore #= true
        dut.io.allocate(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0
        setStoreAgu(dut, 10, 0x1d0004, 0x10)
        sample(dut)
        dut.io.aguValid #= false

        var completionWait = 0
        while (!dut.io.completionValid.toBoolean && completionWait < 8) {
          sample(dut)
          completionWait += 1
        }
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 10)
      }
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

        var storeCompletionWait = 0
        while (!dut.io.completionValid.toBoolean && storeCompletionWait < 8) {
          sample(dut)
          storeCompletionWait += 1
        }
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 0)
        assert(!dut.io.completion.exception.valid.toBoolean)

        dut.io.commitValid #= 1
        dut.io.commit(0).robPointer #= 0
        dut.io.commit(0).isStore #= true
        dut.io.commit(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.commitValid #= 0
        var storeRequestWait = 0
        while (!dut.io.dataRequestValid.toBoolean && storeRequestWait < 8) {
          sample(dut)
          storeRequestWait += 1
        }
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
        var translationWait = 0
        while (!dut.io.translationRequestValid.toBoolean && translationWait < 4) {
          sample(dut)
          translationWait += 1
        }
        assert(dut.io.translationRequestValid.toBoolean)
        assert(!dut.io.completionValid.toBoolean)
        assert(!dut.io.dataRequestValid.toBoolean)

        setStoreAgu(dut, 0, 0x400, BigInt("a5a5a5a5", 16))
        sleep(1)
        assert(dut.io.aguReady.toBoolean)
        sample(dut)
        dut.io.aguValid #= false
        var storeTranslationWait = 0
        while (!dut.io.completionValid.toBoolean && storeTranslationWait < 4) {
          sample(dut)
          storeTranslationWait += 1
        }
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 0)
        sample(dut)
        var loadRequestWait = 0
        while (!dut.io.dataRequestValid.toBoolean && loadRequestWait < 12) {
          sample(dut)
          loadRequestWait += 1
        }
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

  test("a misaligned AGU completion is buffered behind a cache response") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-misaligned-completion-buffer", 0x4c5c) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.allocateValid #= 3
        dut.io.allocate(0).robPointer #= 0
        dut.io.allocate(0).isLoad #= true
        dut.io.allocate(0).loadQueueIndex #= 0
        dut.io.allocate(1).robPointer #= 1
        dut.io.allocate(1).isStore #= true
        dut.io.allocate(1).storeQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0

        setLoadAgu(dut, 0, 0x180)
        sample(dut)
        dut.io.aguValid #= false
        var requestWait = 0
        while (!dut.io.dataRequestValid.toBoolean && requestWait < 10) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.dataRequestValid.toBoolean)
        dut.io.dataRequestReady #= true
        sample(dut)
        dut.io.dataRequestReady #= false

        dut.io.dataResponseValid #= true
        dut.io.dataResponse.robPointer #= 0
        dut.io.dataResponse.data #= BigInt("12345678", 16)
        setStoreAgu(dut, 1, 0x201, BigInt("89abcdef", 16))
        sleep(1)
        assert(dut.io.aguReady.toBoolean)
        sample(dut)
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 0)
        assert(dut.io.completion.data.toBigInt == BigInt("12345678", 16))

        dut.io.dataResponseValid #= false
        dut.io.aguValid #= false
        sample(dut)
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 1)
        assert(dut.io.completion.exception.valid.toBoolean)
        assert(dut.io.completion.exception.ecode.toBigInt == 9)
        assert(dut.io.completion.exception.badVAddrValid.toBoolean)
        assert(dut.io.completion.exception.badVAddr.toBigInt == 0x201)
        assert(!dut.io.dataRequestValid.toBoolean)
      }
  }

  test("a store translation exception completes without issuing a memory request") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-store-translation-exception", 0x4c54) { dut =>
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

        dut.io.translationFault #= true
        dut.io.translationEcode #= 3
        setStoreAgu(dut, 0, 0x12345678L, BigInt("cafebabe", 16))
        sleep(1)
        assert(dut.io.aguReady.toBoolean)
        sample(dut)
        dut.io.aguValid #= false

        var completionWait = 0
        while (!dut.io.completionValid.toBoolean && completionWait < 8) {
          sample(dut)
          completionWait += 1
        }
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.robPointer.toBigInt == 0)
        assert(dut.io.completion.exception.valid.toBoolean)
        assert(dut.io.completion.exception.ecode.toBigInt == 3)
        assert(dut.io.completion.exception.badVAddrValid.toBoolean)
        assert(dut.io.completion.exception.badVAddr.toBigInt == BigInt("12345678", 16))
        assert(!dut.io.dataRequestValid.toBoolean)

        dut.io.commitValid #= 1
        dut.io.commit(0).robPointer #= 0
        dut.io.commit(0).isStore #= true
        dut.io.commit(0).storeQueueIndex #= 0
        dut.io.commit(0).exception.valid #= true
        dut.io.dataRequestReady #= true
        for (_ <- 0 until 3) sample(dut)
        assert(!dut.io.dataRequestValid.toBoolean)
      }
  }

  test("load-linked completion carries its physical reservation line") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-load-linked-reservation", 0x4c55) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.allocateValid #= 1
        dut.io.allocate(0).robPointer #= 0
        dut.io.allocate(0).isLoad #= true
        dut.io.allocate(0).loadQueueIndex #= 0
        sample(dut)
        dut.io.allocateValid #= 0
        setLoadAgu(dut, 0, 0x2340, isLl = true)
        sample(dut)
        dut.io.aguValid #= false

        var requestWait = 0
        while (!dut.io.dataRequestValid.toBoolean && requestWait < 10) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.dataRequestValid.toBoolean)
        dut.io.dataRequestReady #= true
        sample(dut)
        dut.io.dataRequestReady #= false
        dut.io.dataResponseValid #= true
        dut.io.dataResponse.robPointer #= 0
        dut.io.dataResponse.pdst #= 7
        dut.io.dataResponse.data #= BigInt("76543210", 16)
        sample(dut)
        dut.io.dataResponseValid #= false
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.data.toBigInt == BigInt("76543210", 16))
        assert(dut.io.completion.sideEffectData.toBigInt == 0x2340)
      }
  }

  test("a failed store-conditional writes zero and never reaches memory") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-store-conditional-failure", 0x4c56) { dut =>
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
        dut.io.reservationValid #= true
        dut.io.reservationLineAddress #= 0x99
        setStoreAgu(dut, 0, 0x200, BigInt("11223344", 16), isSc = true, pdst = 11)
        sample(dut)
        dut.io.aguValid #= false

        var completionWait = 0
        while (!dut.io.completionValid.toBoolean && completionWait < 8) {
          sample(dut)
          completionWait += 1
        }
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.pdst.toBigInt == 11)
        assert(dut.io.completion.writesPdst.toBoolean)
        assert(dut.io.completion.data.toBigInt == 0)
        assert(!dut.io.dataRequestValid.toBoolean)

        dut.io.commitValid #= 1
        dut.io.commit(0).robPointer #= 0
        dut.io.commit(0).isStore #= true
        dut.io.commit(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.commitValid #= 0
        sleep(1)
        assert(dut.io.releaseStoreValid.toBigInt == 1)
        assert(!dut.io.dataRequestValid.toBoolean)
        sample(dut)
        assert(!dut.io.dataRequestValid.toBoolean)
      }
  }

  test("a matching store-conditional writes one and issues the store after commit") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-lsq")
      .compile(new OooLoadStoreQueueProbe(config))
      .doSim("ooo-lsq-store-conditional-success", 0x4c57) { dut =>
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
        dut.io.reservationValid #= true
        dut.io.reservationLineAddress #= 0x20
        setStoreAgu(dut, 0, 0x200, BigInt("55667788", 16), isSc = true, pdst = 12)
        sample(dut)
        dut.io.aguValid #= false

        var completionWait = 0
        while (!dut.io.completionValid.toBoolean && completionWait < 8) {
          sample(dut)
          completionWait += 1
        }
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completion.data.toBigInt == 1)
        dut.io.commitValid #= 1
        dut.io.commit(0).robPointer #= 0
        dut.io.commit(0).isStore #= true
        dut.io.commit(0).storeQueueIndex #= 0
        sample(dut)
        dut.io.commitValid #= 0

        var requestWait = 0
        while (!dut.io.dataRequestValid.toBoolean && requestWait < 5) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.dataRequestValid.toBoolean)
        assert(dut.io.dataRequest.isWrite.toBoolean)
        assert(dut.io.dataRequest.writeData.toBigInt == BigInt("55667788", 16))
      }
  }
}
