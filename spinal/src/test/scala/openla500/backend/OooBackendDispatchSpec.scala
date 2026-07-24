package openla500.backend

import openla500.core._
import openla500.frontend._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

import scala.collection.mutable.ArrayBuffer

private final class OooBackendDispatchProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val inputValid = in Bits (config.renameWidth bits)
    val pc = in Vec (UInt(config.xlen bits), config.renameWidth)
    val instruction = in Vec (Bits(32 bits), config.renameWidth)
    val renameReady = out Bits (config.renameWidth bits)
    val issueValid = out Bits (config.executionWidth bits)
    val issuePc = out Vec (UInt(config.xlen bits), config.executionWidth)
    val issuePdst = out Vec (UInt(config.physicalRegIndexWidth bits), config.executionWidth)
    val issueRobPointer = out Vec (UInt(config.robPointerWidth bits), config.executionWidth)
    val issueSource1 = out Vec (Bits(config.xlen bits), config.executionWidth)
    val issueSource2 = out Vec (Bits(config.xlen bits), config.executionWidth)
    val issueReady = in Bits (config.executionWidth bits)
    val completionValid = in Bits (config.writebackWidth bits)
    val completionRobPointer = in UInt (config.robPointerWidth bits)
    val completionPdst = in UInt (config.physicalRegIndexWidth bits)
    val completionWritesPdst = in Bool ()
    val completionData = in Bits (config.xlen bits)
    val flush = in Bool ()
  }
  noIoPrefix()

  val backend = new OooBackend(config)
  val decoders = Array.tabulate(config.renameWidth)(_ => new OooLa32rDecoder(config))

  backend.io.renameValid := io.inputValid
  for (lane <- 0 until config.renameWidth) {
    val decoder = decoders(lane)
    decoder.io.pc := io.pc(lane)
    decoder.io.instruction := io.instruction(lane)
    decoder.io.fetchSlot := U(lane, config.fetchSlotWidth bits)
    decoder.io.predictedTaken := False
    decoder.io.predictedTarget := U(0, config.xlen bits)
    decoder.io.predictorMetadata := B(0, 16 bits)
    decoder.io.fetchException.valid := False
    decoder.io.fetchException.ecode := U(0, 6 bits)
    decoder.io.fetchException.esubcode := U(0, 9 bits)
    decoder.io.fetchException.badVAddrValid := False
    decoder.io.fetchException.badVAddr := U(0, config.xlen bits)
    decoder.io.fetchException.tlbRefill := False
    decoder.io.privilege := B(0, 2 bits)
    decoder.io.interruptPending := False
    backend.io.rename(lane) := decoder.io.decoded
  }

  backend.io.issueReady := io.issueReady
  backend.io.completionValid := io.completionValid
  for (lane <- 1 until config.writebackWidth) {
    backend.io
      .completion(lane)
      .assignFromBits(
        B(0, backend.io.completion(lane).getBitsWidth bits)
      )
  }
  backend.io.completion(0).robPointer := io.completionRobPointer
  backend.io.completion(0).pdst := io.completionPdst
  backend.io.completion(0).writesPdst := io.completionWritesPdst
  backend.io.completion(0).data := io.completionData
  backend.io.completion(0).sideEffectData := 0
  backend.io.completion(0).exception.valid := False
  backend.io.completion(0).exception.ecode := 0
  backend.io.completion(0).exception.esubcode := 0
  backend.io.completion(0).exception.badVAddrValid := False
  backend.io.completion(0).exception.badVAddr := 0
  backend.io.completion(0).exception.tlbRefill := False
  backend.io.completion(0).branchResolved := False
  backend.io.completion(0).branchTaken := False
  backend.io.completion(0).branchTarget := 0
  backend.io.completion(0).branchMispredict := False
  backend.io.releaseLoadValid := B(0, config.commitWidth bits)
  backend.io.releaseStoreValid := B(0, config.commitWidth bits)
  backend.io.debugReadAddress := 0
  backend.io.flush := io.flush

  io.renameReady := backend.io.renameReady
  io.issueValid := backend.io.issueValid
  for (port <- 0 until config.executionWidth) {
    io.issuePc(port) := backend.io.issue(port).decoded.pc
    io.issuePdst(port) := backend.io.issue(port).pdst
    io.issueRobPointer(port) := backend.io.issue(port).robPointer
    io.issueSource1(port) := backend.io.issueSource1(port)
    io.issueSource2(port) := backend.io.issueSource2(port)
  }
}

class OooBackendDispatchSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  private def clearControl(dut: OooBackendDispatchProbe): Unit = {
    dut.io.inputValid #= 0
    dut.io.issueReady #= 0
    dut.io.completionValid #= 0
    dut.io.completionRobPointer #= 0
    dut.io.completionPdst #= 0
    dut.io.completionWritesPdst #= false
    dut.io.completionData #= 0
    dut.io.flush #= false
    for (lane <- 0 until config.renameWidth) {
      dut.io.pc(lane) #= 0
      dut.io.instruction(lane) #= 0
    }
  }

  test("rename dispatch queue sustains three independent ALU issues without loss") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-backend-dispatch")
      .compile(new OooBackendDispatchProbe(config))
      .doSim("ooo-backend-dispatch-throughput", 0x4c42) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearControl(dut)
        dut.io.issueReady #= 0xf
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()

        val observedPc = ArrayBuffer.empty[BigInt]
        val observedRob = ArrayBuffer.empty[BigInt]
        var threeIssueCycles = 0

        def sampleAndCapture(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
          var issuedThisCycle = 0
          val issueMask = dut.io.issueValid.toBigInt
          for (port <- 0 until config.executionWidth) {
            if ((issueMask & (BigInt(1) << port)) != 0) {
              observedPc += dut.io.issuePc(port).toBigInt
              observedRob += dut.io.issueRobPointer(port).toBigInt
              assert(dut.io.issueSource1(port).toBigInt == 0)
              assert(dut.io.issueSource2(port).toBigInt == 0)
              issuedThisCycle += 1
            }
          }
          if (issuedThisCycle == 3) threeIssueCycles += 1
        }

        sampleAndCapture()
        val basePc = BigInt("1c000000", 16)
        val expectedPc = (0 until 9).map(index => basePc + index * 4)
        for (group <- 0 until 3) {
          dut.io.inputValid #= 7
          for (lane <- 0 until config.renameWidth) {
            val index = group * config.renameWidth + lane
            dut.io.pc(lane) #= expectedPc(index)
            dut.io.instruction(lane) #= (BigInt("00100000", 16) | (index + 1))
          }
          sleep(1)
          assert(dut.io.renameReady.toBigInt == 7)
          sampleAndCapture()
        }
        dut.io.inputValid #= 0

        var drainCycles = 0
        while (observedPc.size < expectedPc.size && drainCycles < 20) {
          sampleAndCapture()
          drainCycles += 1
        }

        assert(observedPc.size == expectedPc.size)
        assert(observedPc.distinct.size == expectedPc.size)
        assert(observedPc.toSet == expectedPc.toSet)
        assert(observedRob.toSet == (0 until 9).map(BigInt(_)).toSet)
        assert(threeIssueCycles >= 2)
      }
  }

  test("a completion without a physical write cannot wake a reused destination tag") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-backend-dispatch")
      .compile(new OooBackendDispatchProbe(config))
      .doSim("ooo-backend-ignore-non-writing-completion", 0x4c43) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearControl(dut)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val basePc = BigInt("1c000000", 16)
        // addi.w r13,r0,1; addi.w r14,r13,1; b 0
        dut.io.inputValid #= 7
        dut.io.pc(0) #= basePc
        dut.io.instruction(0) #= BigInt("0280040d", 16)
        dut.io.pc(1) #= basePc + 4
        dut.io.instruction(1) #= BigInt("028005ae", 16)
        dut.io.pc(2) #= basePc + 8
        dut.io.instruction(2) #= BigInt("50000000", 16)
        dut.clockDomain.waitSampling()
        dut.io.inputValid #= 0

        // Complete the non-writing branch while claiming the producer's physical tag p1.
        dut.io.completionValid #= 1
        dut.io.completionRobPointer #= 2
        dut.io.completionPdst #= 1
        dut.io.completionWritesPdst #= false
        dut.clockDomain.waitSampling()
        dut.io.completionValid #= 0
        dut.clockDomain.waitSampling(2)

        dut.io.issueReady #= 0xf
        var dependentIssued = false
        for (_ <- 0 until 8) {
          dut.clockDomain.waitSampling()
          sleep(1)
          val issueMask = dut.io.issueValid.toBigInt
          for (port <- 0 until config.executionWidth) {
            if (
              (issueMask & (BigInt(1) << port)) != 0 &&
              dut.io.issuePc(port).toBigInt == basePc + 4
            ) {
              dependentIssued = true
            }
          }
        }
        assert(!dependentIssued)
      }
  }

  test("an r0 write cannot borrow the next allocated physical destination") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-backend-dispatch")
      .compile(new OooBackendDispatchProbe(config))
      .doSim("ooo-backend-r0-has-no-physical-destination", 0x4c44) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearControl(dut)
        dut.io.issueReady #= 0xf
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val basePc = BigInt("1c000000", 16)
        // add.w r0,r0,r0 must not claim p1; addi.w r13,r0,1 owns p1.
        dut.io.inputValid #= 3
        dut.io.pc(0) #= basePc
        dut.io.instruction(0) #= BigInt("00100000", 16)
        dut.io.pc(1) #= basePc + 4
        dut.io.instruction(1) #= BigInt("0280040d", 16)
        dut.clockDomain.waitSampling()
        dut.io.inputValid #= 0

        val observedPdst = scala.collection.mutable.Map.empty[BigInt, BigInt]
        var cycles = 0
        while (observedPdst.size < 2 && cycles < 12) {
          dut.clockDomain.waitSampling()
          sleep(1)
          val issueMask = dut.io.issueValid.toBigInt
          for (port <- 0 until config.executionWidth) {
            if ((issueMask & (BigInt(1) << port)) != 0) {
              observedPdst(dut.io.issuePc(port).toBigInt) = dut.io.issuePdst(port).toBigInt
            }
          }
          cycles += 1
        }

        assert(observedPdst(basePc) == 0)
        assert(observedPdst(basePc + 4) == 1)
      }
  }
}
