package openla500.backend

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooRobProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val allocateValid = in Bits (config.renameWidth bits)
    val allocateAccept = in Bool ()
    val flush = in Bool ()
    val allocatePc = in Vec (UInt(config.xlen bits), config.renameWidth)
    val allocateSerializing = in Bits (config.renameWidth bits)
    val allocateIsBranch = in Bits (config.renameWidth bits)
    val allocateSystemOperation =
      in Vec (UInt(OooSystemOp.Width bits), config.renameWidth)
    val allocateReady = out Bool ()
    val allocatedPointer = out Vec (UInt(config.robPointerWidth bits), config.renameWidth)
    val completionValid = in Bits (config.writebackWidth bits)
    val completionWritesPdst = in Bits (config.writebackWidth bits)
    val completionRobPointer = in Vec (UInt(config.robPointerWidth bits), config.writebackWidth)
    val completionRecoveryEpoch =
      in Vec (UInt(config.recoveryEpochWidth bits), config.writebackWidth)
    val completionExceptionValid = in Bits (config.writebackWidth bits)
    val completionBranchResolved = in Bits (config.writebackWidth bits)
    val currentEpoch = in UInt (config.recoveryEpochWidth bits)
    val completionWakeupValid = out Bits (config.writebackWidth bits)
    val completionWakeupCandidateValid = out Bits (config.writebackWidth bits)
    val commitValid = out Bits (config.commitWidth bits)
    val commitPc = out Vec (UInt(config.xlen bits), config.commitWidth)
    val commitResult = out Vec (Bits(config.xlen bits), config.commitWidth)
    val occupancy = out UInt (log2Up(config.robEntries + 1) bits)
    val empty = out Bool ()
    val headPointer = out UInt (config.robPointerWidth bits)
  }
  noIoPrefix()

  val rob = new OooRob(config)
  for (lane <- 0 until config.renameWidth) {
    rob.io.allocate(lane).assignFromBits(B(0, rob.io.allocate(lane).getBitsWidth bits))
    rob.io.allocate(lane).uop.decoded.pc.allowOverride()
    rob.io.allocate(lane).uop.decoded.pc := io.allocatePc(lane)
    rob.io.allocate(lane).uop.decoded.serializing.allowOverride()
    rob.io.allocate(lane).uop.decoded.serializing := io.allocateSerializing(lane)
    rob.io.allocate(lane).uop.decoded.isBranch.allowOverride()
    rob.io.allocate(lane).uop.decoded.isBranch := io.allocateIsBranch(lane)
    rob.io.allocate(lane).uop.decoded.systemOperation.allowOverride()
    rob.io.allocate(lane).uop.decoded.systemOperation := io.allocateSystemOperation(lane)
  }
  rob.io.currentEpoch := io.currentEpoch
  rob.io.completionValid := io.completionValid
  for (lane <- 0 until config.writebackWidth) {
    val completion = rob.io.completion(lane)
    completion.robPointer := io.completionRobPointer(lane)
    completion.recoveryEpoch := io.completionRecoveryEpoch(lane)
    completion.pdst := U(lane + 1, config.physicalRegIndexWidth bits)
    completion.writesPdst := io.completionWritesPdst(lane)
    completion.data := B(0x100 + lane, config.xlen bits)
    completion.sideEffectData := 0
    completion.exception.valid := io.completionExceptionValid(lane)
    completion.exception.ecode := 0
    completion.exception.esubcode := 0
    completion.exception.badVAddrValid := False
    completion.exception.badVAddr := 0
    completion.exception.tlbRefill := False
    completion.branchResolved := io.completionBranchResolved(lane)
    completion.branchTaken := False
    completion.branchTarget := 0
    completion.branchMispredict := False
  }
  rob.io.allocateValid := io.allocateValid
  rob.io.allocateAccept := io.allocateAccept
  rob.io.flush := io.flush

  io.allocateReady := rob.io.allocateReady
  io.allocatedPointer := rob.io.allocatedPointer
  io.completionWakeupValid := rob.io.completionWakeupValid
  io.completionWakeupCandidateValid := rob.io.completionWakeupCandidateValid
  io.commitValid := rob.io.commitValid
  for (lane <- 0 until config.commitWidth) {
    io.commitPc(lane) := rob.io.commit(lane).pc
    io.commitResult(lane) := rob.io.commit(lane).result
  }
  io.occupancy := rob.io.occupancy
  io.empty := rob.io.empty
  io.headPointer := rob.io.headPointer
}

class OooRobSpec extends AnyFunSuite {
  private def initialize(dut: OooRobProbe, config: OooCoreConfig): Unit = {
    dut.io.allocateValid #= 0
    dut.io.allocateAccept #= false
    dut.io.flush #= false
    dut.io.completionValid #= 0
    dut.io.completionWritesPdst #= 0
    dut.io.completionExceptionValid #= 0
    dut.io.completionBranchResolved #= 0
    dut.io.currentEpoch #= 0
    dut.io.allocateSerializing #= 0
    dut.io.allocateIsBranch #= 0
    for (lane <- 0 until config.writebackWidth) {
      dut.io.completionRobPointer(lane) #= 0
      dut.io.completionRecoveryEpoch(lane) #= 0
    }
    for (lane <- 0 until config.renameWidth) {
      dut.io.allocatePc(lane) #= 0
      dut.io.allocateSystemOperation(lane) #= 0
    }
  }

  test("ROB occupancy follows accepted allocation, not ready speculation") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob")
      .compile(new OooRobProbe(config))
      .doSim("ooo-rob-allocation-handshake", 0x4f4f45) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)

        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()
        assert(dut.io.empty.toBoolean)
        assert(dut.io.occupancy.toBigInt == 0)

        dut.io.allocateValid #= 1
        sleep(1)
        assert(dut.io.allocateReady.toBoolean)
        dut.io.allocateAccept #= false
        sample()
        assert(dut.io.occupancy.toBigInt == 0)
        assert(dut.io.empty.toBoolean)

        dut.io.allocateAccept #= true
        sample()
        assert(dut.io.occupancy.toBigInt == 1)
        assert(!dut.io.empty.toBoolean)

        dut.io.allocateValid #= 0
        dut.io.allocateAccept #= false
        dut.io.flush #= true
        sample()
        assert(dut.io.occupancy.toBigInt == 0)
        assert(dut.io.empty.toBoolean)
      }
  }

  test("ROB flush does not immediately alias stale completion pointers") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob")
      .compile(new OooRobProbe(config))
      .doSim("ooo-rob-flush-pointer-generation", 0x4f4f46) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()

        dut.io.allocateValid #= 1
        dut.io.allocateAccept #= true
        sleep(1)
        val stalePointer = dut.io.allocatedPointer(0).toBigInt
        sample()
        assert(dut.io.occupancy.toBigInt == 1)

        dut.io.allocateValid #= 0
        dut.io.allocateAccept #= false
        dut.io.flush #= true
        sample()
        assert(dut.io.occupancy.toBigInt == 0)

        dut.io.flush #= false
        dut.io.currentEpoch #= 1
        dut.io.allocateValid #= 1
        dut.io.allocateAccept #= true
        sleep(1)
        val newPointer = dut.io.allocatedPointer(0).toBigInt
        assert(newPointer != stalePointer)
        sample()
        assert(dut.io.occupancy.toBigInt == 1)

        dut.io.allocateValid #= 0
        dut.io.allocateAccept #= false
        dut.io.completionRobPointer(0) #= stalePointer
        dut.io.completionValid #= 1
        sleep(1)
        sample()
        assert(dut.io.completionWakeupValid.toBigInt == 0)
        assert(dut.io.commitValid.toBigInt == 0)

        dut.io.completionRobPointer(0) #= newPointer
        dut.io.completionRecoveryEpoch(0) #= 1
        sleep(1)
        sample()
        assert(dut.io.completionWakeupValid.toBigInt == 0)
        assert((dut.io.commitValid.toBigInt & 1) == 1)

        dut.io.completionValid #= 0
        sample()
        assert(dut.io.occupancy.toBigInt == 0)
        assert(dut.io.empty.toBoolean)
      }
  }

  test("ROB commits three completed entries in order") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob")
      .compile(new OooRobProbe(config))
      .doSim("ooo-rob-three-commit", 0x4f4f47) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()

        dut.io.allocatePc(0) #= 0
        dut.io.allocatePc(1) #= 1
        dut.io.allocatePc(2) #= 2
        dut.io.allocateValid #= 7
        dut.io.allocateAccept #= true
        sleep(1)
        assert(dut.io.allocatedPointer(0).toBigInt == 0)
        assert(dut.io.allocatedPointer(1).toBigInt == 1)
        assert(dut.io.allocatedPointer(2).toBigInt == 2)
        sample()
        assert(dut.io.occupancy.toBigInt == 3)

        dut.io.allocateValid #= 0
        dut.io.allocateAccept #= false
        dut.io.completionRobPointer(2) #= 2
        dut.io.completionValid #= 4
        sleep(1)
        assert(dut.io.commitValid.toBigInt == 0)
        sample()
        assert(dut.io.commitValid.toBigInt == 0)

        dut.io.completionRobPointer(0) #= 0
        dut.io.completionRobPointer(1) #= 1
        dut.io.completionValid #= 3
        sleep(1)
        assert(dut.io.commitValid.toBigInt == 0)
        sample()
        assert(dut.io.commitValid.toBigInt == 1)
        assert(dut.io.commitPc(0).toBigInt == 0)
        dut.io.completionValid #= 0
        sample()
        assert(dut.io.commitValid.toBigInt == 3)
        assert(dut.io.commitPc(0).toBigInt == 1)
        assert(dut.io.commitPc(1).toBigInt == 2)

        sample()
        assert(dut.io.occupancy.toBigInt == 0)
        assert(dut.io.empty.toBoolean)
      }
  }

  test("banked ROB payload remains ordered across the physical index wrap") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob")
      .compile(new OooRobProbe(config))
      .doSim("ooo-rob-payload-bank-wrap", 0x4f4f4b) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()

        for (index <- 0 until config.robEntries - 1) {
          dut.io.allocateValid #= 1
          dut.io.allocateAccept #= true
          dut.io.allocatePc(0) #= index
          sleep(1)
          val pointer = dut.io.allocatedPointer(0).toBigInt
          sample()

          dut.io.allocateValid #= 0
          dut.io.allocateAccept #= false
          dut.io.completionRobPointer(0) #= pointer
          dut.io.completionValid #= 1
          sample()
          assert(dut.io.commitValid.toBigInt == 1)
          assert(dut.io.commitPc(0).toBigInt == index)
          dut.io.completionValid #= 0
          sample()
          assert(dut.io.occupancy.toBigInt == 0)
        }

        dut.io.allocatePc(0) #= 0x31
        dut.io.allocatePc(1) #= 0x32
        dut.io.allocatePc(2) #= 0x33
        dut.io.allocateValid #= 7
        dut.io.allocateAccept #= true
        sleep(1)
        val pointers = (0 until config.renameWidth).map { lane =>
          dut.io.allocatedPointer(lane).toBigInt
        }
        assert(pointers.map(_ & (config.robEntries - 1)) == Seq(31, 0, 1))
        sample()

        dut.io.allocateValid #= 0
        dut.io.allocateAccept #= false
        for (lane <- 0 until config.commitWidth) {
          dut.io.completionRobPointer(lane) #= pointers(lane)
        }
        dut.io.completionValid #= 7
        sample()
        assert(dut.io.commitValid.toBigInt == 1)
        assert(dut.io.commitPc(0).toBigInt == 0x31)
        dut.io.completionValid #= 0
        sample()
        assert(dut.io.commitValid.toBigInt == 3)
        assert(
          (0 until 2).map(lane => dut.io.commitPc(lane).toBigInt) == Seq(0x32, 0x33)
        )
        sample()
        assert(dut.io.occupancy.toBigInt == 0)
      }
  }

  test("ROB exposes accepted physical writes from the registered completion stage") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob")
      .compile(new OooRobProbe(config))
      .doSim("ooo-rob-registered-wakeup", 0x4f4f48) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()

        dut.io.allocateValid #= 1
        dut.io.allocateAccept #= true
        sleep(1)
        val pointer = dut.io.allocatedPointer(0).toBigInt
        sample()

        dut.io.allocateValid #= 0
        dut.io.allocateAccept #= false
        dut.io.completionRobPointer(0) #= pointer
        dut.io.completionWritesPdst #= 1
        dut.io.completionValid #= 1
        sleep(1)
        assert(dut.io.completionWakeupValid.toBigInt == 0)

        sample()
        assert(dut.io.completionWakeupValid.toBigInt == 1)
        assert(dut.io.completionWakeupCandidateValid.toBigInt == 1)
        assert(dut.io.commitValid.toBigInt == 1)

        dut.io.completionValid #= 0
        sample()
        assert(dut.io.completionWakeupValid.toBigInt == 0)
        assert(dut.io.occupancy.toBigInt == 0)
      }
  }

  test("ordinary head completion may commit from the staged exact-pointer match") {
    for ((bypass, name, seed) <- Seq(
        (false, "legacy", 0x4f4f51),
        (true, "bypass", 0x4f4f52)
      )) {
      val config = OooCoreConfig.FourIssueThreeCommit.copy(
        enableHeadCompletionCommitBypass = bypass
      )
      SimConfig.withVerilator
        .workspacePath(s"target/sim-workspace-ooo-rob-head-completion-$name")
        .compile(new OooRobProbe(config))
        .doSim(s"ooo-rob-head-completion-$name", seed) { dut =>
          def sample(): Unit = {
            dut.clockDomain.waitSampling()
            sleep(1)
          }

          dut.clockDomain.forkStimulus(period = 10)
          initialize(dut, config)
          dut.clockDomain.assertReset()
          dut.clockDomain.waitSampling(2)
          dut.clockDomain.deassertReset()
          sample()

          dut.io.allocateValid #= 1
          dut.io.allocateAccept #= true
          dut.io.allocatePc(0) #= BigInt("1c000000", 16)
          sleep(1)
          val pointer = dut.io.allocatedPointer(0).toBigInt
          sample()

          dut.io.allocateValid #= 0
          dut.io.allocateAccept #= false
          dut.io.completionRobPointer(0) #= pointer
          dut.io.completionRecoveryEpoch(0) #= 0
          dut.io.completionValid #= 1
          sample()
          assert(dut.io.completionWakeupValid.toBigInt == 0)
          assert(((dut.io.commitValid.toBigInt & 1) != 0) == bypass)
          if (bypass) {
            assert(dut.io.commitResult(0).toBigInt == 0x100)
          }

          dut.io.completionValid #= 0
          sample()
          if (bypass) {
            assert(dut.io.occupancy.toBigInt == 0)
            assert(dut.io.commitValid.toBigInt == 0)
          } else {
            assert((dut.io.commitValid.toBigInt & 1) == 1)
            sample()
            assert(dut.io.occupancy.toBigInt == 0)
          }
        }
    }
  }

  test("head completion bypass preserves precise retirement boundaries") {
    val config = OooCoreConfig.FourIssueThreeCommit.copy(
      enableHeadCompletionCommitBypass = true
    )
    val compiled = SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob-head-completion-boundaries")
      .compile(new OooRobProbe(config))
    val cases = Seq(
      ("completion-exception", false, false, 0, true, false),
      ("resolved-branch", false, false, 0, false, true),
      ("serializing-uop", true, false, 0, false, false),
      ("system-operation", false, false, 1, false, false),
      ("branch-payload", false, true, 0, false, false)
    )
    for (((name, serializing, isBranch, systemOperation, completionException,
          branchResolved), index) <- cases.zipWithIndex) {
      compiled.doSim(s"ooo-rob-head-completion-$name", 0x4f4f53 + index) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()

        dut.io.allocateValid #= 1
        dut.io.allocateAccept #= true
        dut.io.allocatePc(0) #= BigInt("1c000100", 16)
        dut.io.allocateSerializing #= (if (serializing) 1 else 0)
        dut.io.allocateIsBranch #= (if (isBranch) 1 else 0)
        dut.io.allocateSystemOperation(0) #= systemOperation
        sleep(1)
        val pointer = dut.io.allocatedPointer(0).toBigInt
        sample()

        dut.io.allocateValid #= 0
        dut.io.allocateAccept #= false
        dut.io.completionRobPointer(0) #= pointer
        dut.io.completionExceptionValid #= (if (completionException) 1 else 0)
        dut.io.completionBranchResolved #= (if (branchResolved) 1 else 0)
        dut.io.completionValid #= 1
        sample()
        withClue(s"$name must not retire from the bypass stage: ") {
          assert(dut.io.commitValid.toBigInt == 0)
        }

        dut.io.completionValid #= 0
        dut.io.completionExceptionValid #= 0
        dut.io.completionBranchResolved #= 0
        sample()
        withClue(s"$name must retain normal registered completion: ") {
          assert((dut.io.commitValid.toBigInt & 1) == 1)
          assert(dut.io.commitPc(0).toBigInt == BigInt("1c000100", 16))
          assert(dut.io.commitResult(0).toBigInt == 0x100)
        }
        sample()
        assert(dut.io.occupancy.toBigInt == 0)
      }
    }
  }

  test("ROB registers epoch qualification without adding wakeup latency") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob")
      .compile(new OooRobProbe(config))
      .doSim("ooo-rob-registered-epoch-qualification", 0x4f4f4a) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()

        dut.io.currentEpoch #= 2
        dut.io.completionWritesPdst #= 1
        dut.io.completionValid #= 1
        dut.io.completionRecoveryEpoch(0) #= 1
        sample()
        assert(dut.io.completionWakeupCandidateValid.toBigInt == 0)

        dut.io.completionRecoveryEpoch(0) #= 2
        sample()
        assert(dut.io.completionWakeupCandidateValid.toBigInt == 1)
        assert(dut.io.completionWakeupValid.toBigInt == 1)

        dut.io.completionValid #= 0
        sample()
        assert(dut.io.completionWakeupCandidateValid.toBigInt == 0)
      }
  }

  test("ROB flush suppresses architectural wakeup without extending the IQ candidate path") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob")
      .compile(new OooRobProbe(config))
      .doSim("ooo-rob-flush-wakeup-candidate", 0x4f4f49) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()

        dut.io.allocateValid #= 1
        dut.io.allocateAccept #= true
        sleep(1)
        val pointer = dut.io.allocatedPointer(0).toBigInt
        sample()

        dut.io.allocateValid #= 0
        dut.io.allocateAccept #= false
        dut.io.completionRobPointer(0) #= pointer
        dut.io.completionWritesPdst #= 1
        dut.io.completionValid #= 1
        sample()
        assert(dut.io.completionWakeupValid.toBigInt == 1)
        assert(dut.io.completionWakeupCandidateValid.toBigInt == 1)

        dut.io.flush #= true
        sleep(1)
        assert(dut.io.completionWakeupValid.toBigInt == 0)
        assert(dut.io.completionWakeupCandidateValid.toBigInt == 1)
        sample()
        assert(dut.io.completionWakeupCandidateValid.toBigInt == 0)
        assert(dut.io.empty.toBoolean)
      }
  }

  test("ROB rejects an old-epoch completion after the full pointer identity wraps") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-rob")
      .compile(new OooRobProbe(config))
      .doSim("ooo-rob-full-pointer-wrap-epoch-qualification", 0x4f4f4c) { dut =>
        def sample(): Unit = {
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        def allocateOne(expectedPointer: Int, pc: Int): Unit = {
          dut.io.allocatePc(0) #= pc
          dut.io.allocateValid #= 1
          dut.io.allocateAccept #= true
          sleep(1)
          assert(dut.io.allocateReady.toBoolean)
          assert(dut.io.allocatedPointer(0).toBigInt == expectedPointer)
          sample()
          dut.io.allocateValid #= 0
          dut.io.allocateAccept #= false
          assert(dut.io.occupancy.toBigInt == 1)
        }

        def completeAndCommit(pointer: Int, epoch: Int): Unit = {
          dut.io.completionRobPointer(0) #= pointer
          dut.io.completionRecoveryEpoch(0) #= epoch
          dut.io.completionValid #= 1
          sample()
          assert((dut.io.commitValid.toBigInt & 1) == 1)
          assert(dut.io.commitPc(0).toBigInt == pointer)
          dut.io.completionValid #= 0
          sample()
          assert(dut.io.occupancy.toBigInt == 0)
        }

        dut.clockDomain.forkStimulus(period = 10)
        initialize(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample()

        // Preserve pointer 0 as an old-epoch completion identity, then flush it.
        allocateOne(expectedPointer = 0, pc = 0)
        dut.io.flush #= true
        sample()
        dut.io.flush #= false
        assert(dut.io.empty.toBoolean)

        // Retire pointers 1..63 so both index and generation return to pointer 0.
        dut.io.currentEpoch #= 1
        for (pointer <- 1 until (1 << config.robPointerWidth)) {
          allocateOne(expectedPointer = pointer, pc = pointer)
          completeAndCommit(pointer = pointer, epoch = 1)
        }

        allocateOne(expectedPointer = 0, pc = 0x100)
        dut.io.completionRobPointer(0) #= 0
        dut.io.completionRecoveryEpoch(0) #= 0
        dut.io.completionWritesPdst #= 1
        dut.io.completionValid #= 1
        sample()
        dut.io.completionValid #= 0
        assert(dut.io.completionWakeupCandidateValid.toBigInt == 0)
        assert(dut.io.completionWakeupValid.toBigInt == 0)

        for (_ <- 0 until 4) {
          sample()
          assert(dut.io.completionWakeupCandidateValid.toBigInt == 0)
          assert(dut.io.completionWakeupValid.toBigInt == 0)
          assert(dut.io.commitValid.toBigInt == 0)
          assert(dut.io.occupancy.toBigInt == 1)
        }

        dut.io.completionRecoveryEpoch(0) #= 1
        dut.io.completionWritesPdst #= 0
        dut.io.completionValid #= 1
        sample()
        assert((dut.io.commitValid.toBigInt & 1) == 1)
        assert(dut.io.commitPc(0).toBigInt == 0x100)
        dut.io.completionValid #= 0
        sample()
        assert(dut.io.occupancy.toBigInt == 0)
      }
  }
}
