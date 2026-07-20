package openla500.frontend

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core.sim._

import scala.language.reflectiveCalls

class OooFrontendSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def sample(dut: OooFrontend): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  private def clearInputs(dut: OooFrontend): Unit = {
    dut.io.translationRequest.ready #= false
    dut.io.translationResponse.valid #= false
    dut.io.translationResponse.virtualAddress #= 0
    dut.io.translationResponse.physicalAddress #= 0
    dut.io.translationResponse.uncached #= false
    dut.io.translationResponse.exception.valid #= false
    dut.io.translationResponse.exception.ecode #= 0
    dut.io.translationResponse.exception.esubcode #= 0
    dut.io.translationResponse.exception.badVAddrValid #= false
    dut.io.translationResponse.exception.badVAddr #= 0
    dut.io.translationResponse.exception.tlbRefill #= false
    dut.io.cacheRequestReady #= false
    dut.io.cacheResponseValid #= false
    dut.io.cacheResponse.virtualAddress #= 0
    dut.io.cacheResponse.physicalAddress #= 0
    for (lane <- 0 until config.fetchWidth) {
      dut.io.cacheResponse.instructions(lane) #= 0
    }
    dut.io.cacheResponse.error #= false
    dut.io.decodeReady #= 0
    dut.io.redirectValid #= false
    dut.io.redirectTarget #= 0
    dut.io.privilege #= 0
    dut.io.interruptPending #= false
  }

  private def acceptFetch(dut: OooFrontend, expectedAddress: BigInt): Unit = {
    var translationCycles = 0
    while (!dut.io.translationRequest.valid.toBoolean && translationCycles < 8) {
      sample(dut)
      translationCycles += 1
    }
    assert(dut.io.translationRequest.valid.toBoolean)
    assert(dut.io.translationRequest.virtualAddress.toBigInt == expectedAddress)
    dut.io.translationRequest.ready #= true
    sample(dut)
    dut.io.translationRequest.ready #= false

    dut.io.translationResponse.valid #= true
    dut.io.translationResponse.virtualAddress #= expectedAddress
    dut.io.translationResponse.physicalAddress #= expectedAddress
    dut.io.translationResponse.uncached #= false
    sleep(1)
    assert(dut.io.translationResponse.ready.toBoolean)
    sample(dut)
    dut.io.translationResponse.valid #= false

    var cycles = 0
    while (!dut.io.cacheRequestValid.toBoolean && cycles < 8) {
      sample(dut)
      cycles += 1
    }
    assert(dut.io.cacheRequestValid.toBoolean)
    assert(dut.io.cacheRequest.virtualAddress.toBigInt == expectedAddress)
    assert(dut.io.cacheRequest.physicalAddress.toBigInt == expectedAddress)
    dut.io.cacheRequestReady #= true
    sample(dut)
    dut.io.cacheRequestReady #= false
  }

  private def returnGroup(dut: OooFrontend, address: BigInt, firstRd: Int): Unit = {
    dut.io.cacheResponseValid #= true
    dut.io.cacheResponse.virtualAddress #= address
    dut.io.cacheResponse.physicalAddress #= address
    for (lane <- 0 until config.fetchWidth) {
      dut.io.cacheResponse.instructions(lane) #= (BigInt("00100000", 16) | (firstRd + lane))
    }
    dut.io.cacheResponse.error #= false
    sample(dut)
    dut.io.cacheResponseValid #= false
  }

  private def expectDecode(dut: OooFrontend, pcs: Seq[BigInt], rds: Seq[Int]): Unit = {
    assert(dut.io.decodeValid.toBigInt == ((BigInt(1) << pcs.size) - 1))
    pcs.indices.foreach { lane =>
      assert(dut.io.decoded(lane).pc.toBigInt == pcs(lane))
      assert(dut.io.decoded(lane).instruction.toBigInt ==
        (BigInt("00100000", 16) | rds(lane)))
    }
  }

  test("fetch4 groups compact across decode3 and redirects discard stale responses") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-frontend")
      .compile(new OooFrontend(config))
      .doSim("ooo-frontend-fetch4-decode3", 0x4c62) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        val resetPc = config.resetVector
        acceptFetch(dut, resetPc)
        returnGroup(dut, resetPc, firstRd = 1)
        assert(dut.io.occupancy.toBigInt == 4)
        expectDecode(dut, Seq(resetPc, resetPc + 4, resetPc + 8), Seq(1, 2, 3))

        dut.io.decodeReady #= 7
        sample(dut)
        dut.io.decodeReady #= 0
        assert(dut.io.occupancy.toBigInt == 1)
        expectDecode(dut, Seq(resetPc + 12), Seq(4))

        acceptFetch(dut, resetPc + 16)
        returnGroup(dut, resetPc + 16, firstRd = 5)
        assert(dut.io.occupancy.toBigInt == 5)
        expectDecode(dut, Seq(resetPc + 12, resetPc + 16, resetPc + 20), Seq(4, 5, 6))

        dut.io.decodeReady #= 7
        sample(dut)
        dut.io.decodeReady #= 0
        assert(dut.io.occupancy.toBigInt == 2)

        acceptFetch(dut, resetPc + 32)
        dut.io.redirectTarget #= resetPc + 0x124
        dut.io.redirectValid #= true
        sleep(1)
        assert(dut.io.cacheKill.toBoolean)
        sample(dut)
        dut.io.redirectValid #= false
        assert(dut.io.occupancy.toBigInt == 0)
        assert(dut.io.fetchPc.toBigInt == resetPc + 0x124)

        dut.io.cacheResponseValid #= true
        for (lane <- 0 until config.fetchWidth) {
          dut.io.cacheResponse.instructions(lane) #= (BigInt("00100000", 16) | (9 + lane))
        }
        sample(dut)
        dut.io.cacheResponseValid #= false
        assert(dut.io.occupancy.toBigInt == 0)

        acceptFetch(dut, resetPc + 0x124)
        returnGroup(dut, resetPc + 0x124, firstRd = 13)
        assert(dut.io.occupancy.toBigInt == 3)
        expectDecode(
          dut,
          Seq(resetPc + 0x124, resetPc + 0x128, resetPc + 0x12c),
          Seq(14, 15, 16)
        )
      }
  }

  test("a misaligned fetch keeps ADEF metadata ahead of placeholder decode errors") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-frontend")
      .compile(new OooFrontend(config))
      .doSim("ooo-frontend-fetch-adef-priority", 0x4c63) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        val badPc = BigInt("227f9789", 16)
        dut.io.redirectValid #= true
        dut.io.redirectTarget #= badPc
        sample(dut)
        dut.io.redirectValid #= false

        var requestWait = 0
        while (!dut.io.translationRequest.valid.toBoolean && requestWait < 8) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.translationRequest.valid.toBoolean)
        assert(dut.io.translationRequest.virtualAddress.toBigInt == badPc)
        dut.io.translationRequest.ready #= true
        sample(dut)
        dut.io.translationRequest.ready #= false

        dut.io.translationResponse.valid #= true
        dut.io.translationResponse.virtualAddress #= badPc
        dut.io.translationResponse.exception.valid #= true
        dut.io.translationResponse.exception.ecode #= 8
        dut.io.translationResponse.exception.badVAddrValid #= true
        dut.io.translationResponse.exception.badVAddr #= badPc
        sleep(1)
        assert(dut.io.translationResponse.ready.toBoolean)
        sample(dut)
        dut.io.translationResponse.valid #= false

        assert(dut.io.decodeValid.toBigInt == 1)
        assert(dut.io.decoded(0).pc.toBigInt == badPc)
        assert(dut.io.decoded(0).exception.valid.toBoolean)
        assert(dut.io.decoded(0).exception.ecode.toBigInt == 8)
        assert(dut.io.decoded(0).exception.badVAddr.toBigInt == badPc)
      }
  }

  test("a stale translation response is drained and the original PC is retried") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-frontend")
      .compile(new OooFrontend(config))
      .doSim("ooo-frontend-translation-response-match", 0x4c65) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        val resetPc = config.resetVector
        var requestWait = 0
        while (!dut.io.translationRequest.valid.toBoolean && requestWait < 8) {
          sample(dut)
          requestWait += 1
        }
        assert(dut.io.translationRequest.valid.toBoolean)
        assert(dut.io.translationRequest.virtualAddress.toBigInt == resetPc)
        dut.io.translationRequest.ready #= true
        sample(dut)
        dut.io.translationRequest.ready #= false

        // Consume a response belonging to a later request without allowing its physical address
        // to be paired with resetPc.
        dut.io.translationResponse.virtualAddress #= resetPc + 16
        dut.io.translationResponse.physicalAddress #= resetPc + 16
        dut.io.translationResponse.valid #= true
        sleep(1)
        assert(dut.io.translationResponse.ready.toBoolean)
        sample(dut)
        dut.io.translationResponse.valid #= false
        assert(!dut.io.cacheRequestValid.toBoolean)

        var retryWait = 0
        while (!dut.io.translationRequest.valid.toBoolean && retryWait < 8) {
          sample(dut)
          retryWait += 1
        }
        assert(dut.io.translationRequest.valid.toBoolean)
        assert(dut.io.translationRequest.virtualAddress.toBigInt == resetPc)
      }
  }

  test("a stale cache response cannot satisfy the post-redirect request") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-frontend")
      .compile(new OooFrontend(config))
      .doSim("ooo-frontend-cache-response-match", 0x4c66) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        val oldPc = config.resetVector
        val redirectPc = config.resetVector + 0x108
        acceptFetch(dut, oldPc)

        dut.io.redirectTarget #= redirectPc
        dut.io.redirectValid #= true
        sample(dut)
        dut.io.redirectValid #= false
        assert(dut.io.occupancy.toBigInt == 0)

        acceptFetch(dut, redirectPc)

        dut.io.cacheResponseValid #= true
        dut.io.cacheResponse.virtualAddress #= oldPc
        dut.io.cacheResponse.physicalAddress #= oldPc
        for (lane <- 0 until config.fetchWidth) {
          dut.io.cacheResponse.instructions(lane) #= (BigInt("00100000", 16) | lane + 1)
        }
        sample(dut)
        dut.io.cacheResponseValid #= false
        assert(dut.io.occupancy.toBigInt == 0)
        assert(dut.io.fetchPc.toBigInt == redirectPc)

        returnGroup(dut, redirectPc, firstRd = 9)
        assert(dut.io.occupancy.toBigInt == 2)
        expectDecode(dut, Seq(redirectPc, redirectPc + 4), Seq(11, 12))
      }
  }
}
