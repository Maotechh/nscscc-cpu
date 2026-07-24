package openla500.execute

import openla500.backend._
import openla500.core._
import openla500.frontend._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooExecutionClusterProbe(config: OooCoreConfig) extends Component {
  private val loadStorePort =
    config.executionPorts.indexWhere(_.capabilities.contains(OooFuKind.LoadStore))

  val io = new Bundle {
    val instruction = in Bits (32 bits)
    val issueValid = in Bool ()
    val aguReady = in Bool ()
    val loadStoreCompletionValid = in Bool ()
    val issueReady = out Bool ()
    val aguValid = out Bool ()
    val completionValid = out Bool ()
    val systemOperation = out UInt (OooSystemOp.Width bits)
    val isLoad = out Bool ()
    val isStore = out Bool ()
  }
  noIoPrefix()

  val decoder = new OooLa32rDecoder(config)
  decoder.io.pc := U(config.resetVector, config.xlen bits)
  decoder.io.instruction := io.instruction
  decoder.io.fetchSlot := 0
  decoder.io.predictedTaken := False
  decoder.io.predictedTarget := U(config.resetVector + 4, config.xlen bits)
  decoder.io.predictorMetadata := 0
  decoder.io.fetchException.assignFromBits(B(0, decoder.io.fetchException.getBitsWidth bits))
  decoder.io.privilege := 0
  decoder.io.interruptPending := False

  val execution = new OooExecutionCluster(config)
  execution.io.issueValid := 0
  execution.io.issueValid(loadStorePort) := io.issueValid
  for (port <- 0 until config.executionWidth) {
    if (port == loadStorePort) {
      execution.io.issue(port).decoded := decoder.io.decoded
      execution.io.issue(port).pdst := 0
      execution.io.issue(port).oldPdst := 0
      execution.io.issue(port).psrc1 := 0
      execution.io.issue(port).psrc2 := 0
      execution.io.issue(port).source1Ready := True
      execution.io.issue(port).source2Ready := True
      execution.io.issue(port).robPointer := 3
      execution.io.issue(port).loadQueueIndex := 1
      execution.io.issue(port).storeQueueIndex := 2
    } else {
      execution.io.issue(port).assignFromBits(B(0, execution.io.issue(port).getBitsWidth bits))
    }
    execution.io.source1(port) := 0
    execution.io.source2(port) := 0
  }
  execution.io.flush := False
  execution.io.systemReadData := 0
  execution.io.timer := 0
  execution.io.timerId := 0
  execution.io.aguReady := io.aguReady
  execution.io.loadStoreCompletionValid := io.loadStoreCompletionValid
  execution.io.loadStoreCompletion.assignFromBits(
    B(0, execution.io.loadStoreCompletion.getBitsWidth bits)
  )
  execution.io.olderStorePending := False
  execution.io.cacheTranslationRequest.ready := True
  execution.io.cacheTranslationResponse.valid := False
  execution.io.cacheTranslationResponse.payload.assignFromBits(
    B(0, execution.io.cacheTranslationResponse.payload.getBitsWidth bits)
  )

  io.issueReady := execution.io.issueReady(loadStorePort)
  io.aguValid := execution.io.aguValid
  io.completionValid := execution.io.completionValid(loadStorePort)
  io.systemOperation := decoder.io.decoded.systemOperation
  io.isLoad := decoder.io.decoded.isLoad
  io.isStore := decoder.io.decoded.isStore
}

private final class OooDivideCompletionCollisionProbe(config: OooCoreConfig) extends Component {
  private val dividePort =
    config.executionPorts.indexWhere(_.capabilities.contains(OooFuKind.Divide))

  val io = new Bundle {
    val instruction = in Bits (32 bits)
    val issueValid = in Bool ()
    val source1 = in Bits (config.xlen bits)
    val source2 = in Bits (config.xlen bits)
    val robPointer = in UInt (config.robPointerWidth bits)
    val pdst = in UInt (config.physicalRegIndexWidth bits)
    val issueReady = out Bool ()
    val completionValid = out Bool ()
    val completionRobPointer = out UInt (config.robPointerWidth bits)
  }
  noIoPrefix()

  val decoder = new OooLa32rDecoder(config)
  decoder.io.pc := U(config.resetVector, config.xlen bits)
  decoder.io.instruction := io.instruction
  decoder.io.fetchSlot := 0
  decoder.io.predictedTaken := False
  decoder.io.predictedTarget := U(config.resetVector + 4, config.xlen bits)
  decoder.io.predictorMetadata := 0
  decoder.io.fetchException.assignFromBits(B(0, decoder.io.fetchException.getBitsWidth bits))
  decoder.io.privilege := 0
  decoder.io.interruptPending := False

  val execution = new OooExecutionCluster(config)
  execution.io.issueValid := 0
  execution.io.issueValid(dividePort) := io.issueValid
  for (port <- 0 until config.executionWidth) {
    if (port == dividePort) {
      execution.io.issue(port).decoded := decoder.io.decoded
      execution.io.issue(port).pdst := io.pdst
      execution.io.issue(port).oldPdst := 0
      execution.io.issue(port).psrc1 := 0
      execution.io.issue(port).psrc2 := 0
      execution.io.issue(port).source1Ready := True
      execution.io.issue(port).source2Ready := True
      execution.io.issue(port).robPointer := io.robPointer
      execution.io.issue(port).loadQueueIndex := 0
      execution.io.issue(port).storeQueueIndex := 0
      execution.io.source1(port) := io.source1
      execution.io.source2(port) := io.source2
    } else {
      execution.io.issue(port).assignFromBits(B(0, execution.io.issue(port).getBitsWidth bits))
      execution.io.source1(port) := 0
      execution.io.source2(port) := 0
    }
  }
  execution.io.flush := False
  execution.io.systemReadData := 0
  execution.io.timer := 0
  execution.io.timerId := 0
  execution.io.aguReady := True
  execution.io.loadStoreCompletionValid := False
  execution.io.loadStoreCompletion.assignFromBits(
    B(0, execution.io.loadStoreCompletion.getBitsWidth bits)
  )
  execution.io.olderStorePending := False
  execution.io.cacheTranslationRequest.ready := True
  execution.io.cacheTranslationResponse.valid := False
  execution.io.cacheTranslationResponse.payload.assignFromBits(
    B(0, execution.io.cacheTranslationResponse.payload.getBitsWidth bits)
  )

  io.issueReady := execution.io.issueReady(dividePort)
  io.completionValid := execution.io.completionValid(dividePort)
  io.completionRobPointer := execution.io.completion(dividePort).robPointer
}

class OooExecutionClusterSpec extends AnyFunSuite {
  private val config = OooCoreConfig.FourIssueThreeCommit

  test("CACOP and PRELD complete without allocating an LSQ entry") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-execution-cluster")
      .compile(new OooExecutionClusterProbe(config))
      .doSim("ooo-execution-cluster-cache-hints", 0x4c67) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.issueValid #= false
        dut.io.aguReady #= false
        dut.io.loadStoreCompletionValid #= false

        for (
          (instruction, operation) <- Seq(
            BigInt("06000000", 16) -> 17,
            BigInt("2ac00000", 16) -> 18
          )
        ) {
          dut.io.instruction #= instruction
          dut.io.issueValid #= true
          sleep(1)
          assert(dut.io.systemOperation.toBigInt == operation)
          assert(!dut.io.isLoad.toBoolean)
          assert(!dut.io.isStore.toBoolean)
          assert(dut.io.issueReady.toBoolean)
          assert(!dut.io.aguValid.toBoolean)
          assert(dut.io.completionValid.toBoolean)
          dut.clockDomain.waitSampling()
          dut.io.issueValid #= false
        }

        dut.io.instruction #= BigInt("28800000", 16)
        dut.io.issueValid #= true
        sleep(1)
        assert(dut.io.isLoad.toBoolean)
        assert(!dut.io.issueReady.toBoolean)
        assert(!dut.io.aguValid.toBoolean)
        assert(!dut.io.completionValid.toBoolean)

        dut.io.aguReady #= true
        sleep(1)
        assert(dut.io.issueReady.toBoolean)
        assert(dut.io.aguValid.toBoolean)
        assert(!dut.io.completionValid.toBoolean)

        dut.io.instruction #= BigInt("06000000", 16)
        dut.io.aguReady #= false
        dut.io.loadStoreCompletionValid #= true
        sleep(1)
        assert(!dut.io.issueReady.toBoolean)
        assert(dut.io.completionValid.toBoolean)
        assert(!dut.io.aguValid.toBoolean)
      }
  }

  test("a divider return backpressures a direct ALU sharing its writeback lane") {
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-execution-cluster")
      .compile(new OooDivideCompletionCollisionProbe(config))
      .doSim("ooo-execution-cluster-divider-return-arbitration", 0x4c68) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.issueValid #= false
        dut.io.instruction #= 0
        dut.io.source1 #= 0
        dut.io.source2 #= 0
        dut.io.robPointer #= 0
        dut.io.pdst #= 0
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        // div.w r15, r12, r13
        dut.io.instruction #= BigInt("0020b58f", 16)
        dut.io.source1 #= 100
        dut.io.source2 #= 3
        dut.io.robPointer #= 5
        dut.io.pdst #= 10
        dut.io.issueValid #= true
        sleep(1)
        assert(dut.io.issueReady.toBoolean)
        dut.clockDomain.waitSampling()
        dut.io.issueValid #= false

        var completionWait = 0
        while (!dut.io.completionValid.toBoolean && completionWait < 40) {
          dut.clockDomain.waitSampling()
          sleep(1)
          completionWait += 1
        }
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completionRobPointer.toBigInt == 5)

        // ori r12, r12, imm would otherwise be accepted and overwritten by
        // the divider result on this exact cycle.
        dut.io.instruction #= BigInt("039b658c", 16)
        dut.io.robPointer #= 6
        dut.io.pdst #= 11
        dut.io.issueValid #= true
        sleep(1)
        assert(!dut.io.issueReady.toBoolean)
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completionRobPointer.toBigInt == 5)

        dut.clockDomain.waitSampling()
        sleep(1)
        assert(dut.io.issueReady.toBoolean)
        assert(dut.io.completionValid.toBoolean)
        assert(dut.io.completionRobPointer.toBigInt == 6)
      }
  }
}
