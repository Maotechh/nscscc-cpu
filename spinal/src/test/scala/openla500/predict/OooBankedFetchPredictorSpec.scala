package openla500.predict

import java.nio.file.Paths
import openla500.core.OooCoreConfig
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

class OooBankedFetchPredictorSpec extends AnyFunSuite {
  private val WordMask = (BigInt(1) << 32) - 1
  private val Conditional = 0
  private val Ret = 3

  private def workspace: String = {
    val root = sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-predict-banked")
    Paths.get(root, "predictor").toString
  }

  test(
    "BTB invalidation edge: lookups suppressed during clearing and updates are dropped, then training resumes"
  ) {
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
      .compile(new OooBankedFetchPredictor(OooCoreConfig.FourIssueThreeCommit))
      .doSim("banked-invalidation", 0x1dac8c) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        def clearInputs(): Unit = {
          dut.io.lookupValid #= false
          dut.io.lookupPc #= 0
          dut.io.btbUpdateValid #= false
          dut.io.btbUpdatePc #= 0
          dut.io.btbUpdateTarget #= 0
          dut.io.btbUpdateType #= 0
          dut.io.btbUpdateDirectionTrained #= false
          dut.io.phtUpdateValid #= false
          dut.io.phtUpdatePc #= 0
          dut.io.phtUpdateIndex #= 0
          dut.io.phtUpdateOldState #= 0
          dut.io.phtUpdateOldValid #= false
          dut.io.phtUpdateTaken #= false
          dut.io.speculativeHistoryValid #= false
          dut.io.speculativeHistoryTaken #= false
          dut.io.speculativeRasPush #= false
          dut.io.speculativeRasPop #= false
          dut.io.speculativeReturnAddress #= 0
          dut.io.commitRasPush #= false
          dut.io.commitRasPop #= false
          dut.io.commitReturnAddress #= 0
          dut.io.flush #= false
        }

        def resetState(): Unit = {
          clearInputs()
          dut.clockDomain.assertReset()
          dut.clockDomain.waitSampling(2)
          dut.clockDomain.deassertReset()
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        final case class BankPrediction(
            responseValid: Boolean,
            hit: Boolean,
            phtValid: Boolean,
            branchType: Int,
            phtState: Int,
            phtIndex: Int,
            target: BigInt,
            fallbackTaken: Boolean
        )

        def lookup(pc: BigInt, bank: Int = 0): BankPrediction = {
          dut.io.lookupPc #= pc & WordMask
          dut.io.lookupValid #= true
          dut.clockDomain.waitSampling()
          dut.io.lookupValid #= false
          dut.clockDomain.waitSampling()
          val result = BankPrediction(
            dut.io.responseValid.toBoolean,
            dut.io.prediction(bank).hit.toBoolean,
            dut.io.prediction(bank).phtValid.toBoolean,
            dut.io.prediction(bank).branchType.toInt,
            dut.io.prediction(bank).phtState.toInt,
            dut.io.prediction(bank).phtIndex.toInt,
            dut.io.prediction(bank).target.toBigInt,
            dut.io.prediction(bank).fallbackTaken.toBoolean
          )
          dut.clockDomain.waitSampling()
          assert(
            !dut.io.responseValid.toBoolean,
            "a lookup response lasted more than one cycle"
          )
          result
        }

        def btbUpdate(
            pc: BigInt,
            target: BigInt,
            branchType: Int = Conditional,
            directionTrained: Boolean = false
        ): Unit = {
          dut.io.btbUpdateValid #= true
          dut.io.btbUpdatePc #= pc & WordMask
          dut.io.btbUpdateTarget #= target & WordMask
          dut.io.btbUpdateType #= branchType
          dut.io.btbUpdateDirectionTrained #= directionTrained
          dut.clockDomain.waitSampling()
          dut.io.btbUpdateValid #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        val branchPc = BigInt("1c000000", 16)
        val branchTarget = BigInt("1c001000", 16)

        resetState()
        // While invalidating, a continuous lookup must never produce a response.
        dut.io.lookupPc #= branchPc
        dut.io.lookupValid #= true
        for (_ <- 0 until 3) {
          dut.clockDomain.waitSampling()
          assert(!dut.io.responseValid.toBoolean, "lookup fired during BTB invalidation")
        }
        dut.io.lookupValid #= false

        // An update applied during invalidation is dropped, not stored.
        btbUpdate(branchPc, branchTarget)
        dut.clockDomain.waitSampling(132)
        sleep(1)

        val dropped = lookup(branchPc)
        assert(!dropped.hit, "BTB entry trained during invalidation must be dropped")

        btbUpdate(branchPc, branchTarget)
        val trained = lookup(branchPc)
        assert(trained.hit, "trained BTB entry must hit")
        assert(trained.target == branchTarget, "trained BTB target mismatch")
        assert(trained.branchType == Conditional, "trained BTB type mismatch")
        assert(!trained.phtValid, "direction-untrained entry must report phtValid=false")

        val untrained = lookup(BigInt("1c000020", 16))
        assert(!untrained.hit, "untrained row must miss")
      }
  }

  test(
    "back-to-back same-index updates serialize correctly through the staged bimodal counter"
  ) {
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
      .compile(new OooBankedFetchPredictor(OooCoreConfig.FourIssueThreeCommit))
      .doSim("banked-back-to-back", 0x1dac8c) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        def clearInputs(): Unit = {
          dut.io.lookupValid #= false
          dut.io.lookupPc #= 0
          dut.io.btbUpdateValid #= false
          dut.io.btbUpdatePc #= 0
          dut.io.btbUpdateTarget #= 0
          dut.io.btbUpdateType #= 0
          dut.io.btbUpdateDirectionTrained #= false
          dut.io.phtUpdateValid #= false
          dut.io.phtUpdatePc #= 0
          dut.io.phtUpdateIndex #= 0
          dut.io.phtUpdateOldState #= 0
          dut.io.phtUpdateOldValid #= false
          dut.io.phtUpdateTaken #= false
          dut.io.speculativeHistoryValid #= false
          dut.io.speculativeHistoryTaken #= false
          dut.io.speculativeRasPush #= false
          dut.io.speculativeRasPop #= false
          dut.io.speculativeReturnAddress #= 0
          dut.io.commitRasPush #= false
          dut.io.commitRasPop #= false
          dut.io.commitReturnAddress #= 0
          dut.io.flush #= false
        }

        def resetState(): Unit = {
          clearInputs()
          dut.clockDomain.assertReset()
          dut.clockDomain.waitSampling(2)
          dut.clockDomain.deassertReset()
          dut.clockDomain.waitSampling(132)
          sleep(1)
        }

        final case class BankPrediction(
            responseValid: Boolean,
            hit: Boolean,
            phtValid: Boolean,
            branchType: Int,
            phtState: Int,
            phtIndex: Int,
            target: BigInt,
            fallbackTaken: Boolean
        )

        def lookup(pc: BigInt, bank: Int = 0): BankPrediction = {
          dut.io.lookupPc #= pc & WordMask
          dut.io.lookupValid #= true
          dut.clockDomain.waitSampling()
          dut.io.lookupValid #= false
          dut.clockDomain.waitSampling()
          val result = BankPrediction(
            dut.io.responseValid.toBoolean,
            dut.io.prediction(bank).hit.toBoolean,
            dut.io.prediction(bank).phtValid.toBoolean,
            dut.io.prediction(bank).branchType.toInt,
            dut.io.prediction(bank).phtState.toInt,
            dut.io.prediction(bank).phtIndex.toInt,
            dut.io.prediction(bank).target.toBigInt,
            dut.io.prediction(bank).fallbackTaken.toBoolean
          )
          dut.clockDomain.waitSampling()
          assert(
            !dut.io.responseValid.toBoolean,
            "a lookup response lasted more than one cycle"
          )
          result
        }

        def btbUpdate(
            pc: BigInt,
            target: BigInt,
            branchType: Int = Conditional,
            directionTrained: Boolean = false
        ): Unit = {
          dut.io.btbUpdateValid #= true
          dut.io.btbUpdatePc #= pc & WordMask
          dut.io.btbUpdateTarget #= target & WordMask
          dut.io.btbUpdateType #= branchType
          dut.io.btbUpdateDirectionTrained #= directionTrained
          dut.clockDomain.waitSampling()
          dut.io.btbUpdateValid #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        def phtUpdate(
            pc: BigInt,
            taken: Boolean,
            index: Int,
            oldState: Int = 0,
            oldValid: Boolean = false
        ): Unit = {
          dut.io.phtUpdateValid #= true
          dut.io.phtUpdatePc #= pc & WordMask
          dut.io.phtUpdateTaken #= taken
          dut.io.phtUpdateIndex #= index
          dut.io.phtUpdateOldState #= oldState
          dut.io.phtUpdateOldValid #= oldValid
          dut.clockDomain.waitSampling()
          dut.io.phtUpdateValid #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        val branchPc = BigInt("1c000000", 16)
        val branchTarget = BigInt("1c001000", 16)

        resetState()
        // Same row (bits 10:4) and same bimodal index (bits 7:2) as branchPc.
        btbUpdate(branchPc, branchTarget)

        phtUpdate(branchPc, taken = true, index = 0)
        val once = lookup(branchPc)
        assert(once.hit, "single trained update must still hit")
        assert(!once.phtValid, "bimodal fallback only applies while phtValid=false")
        assert(!once.fallbackTaken, "bimodal counter 0->1 must still be not-taken")

        phtUpdate(branchPc, taken = true, index = 0)
        phtUpdate(branchPc, taken = true, index = 0)
        val twice = lookup(branchPc)
        assert(twice.hit)
        assert(!twice.phtValid)
        assert(twice.fallbackTaken, "bimodal counter 1->2 must cross the taken threshold")

        phtUpdate(branchPc, taken = false, index = 0)
        phtUpdate(branchPc, taken = false, index = 0)
        val drained = lookup(branchPc)
        assert(drained.hit)
        assert(!drained.phtValid)
        assert(!drained.fallbackTaken, "bimodal counter 2->1->0 must fall back to not-taken")
      }
  }

  test(
    "flush coincident with a commit restores history that already folds the committed direction"
  ) {
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
      .compile(new OooBankedFetchPredictor(OooCoreConfig.FourIssueThreeCommit))
      .doSim("banked-flush-commit", 0x1dac8c) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        def clearInputs(): Unit = {
          dut.io.lookupValid #= false
          dut.io.lookupPc #= 0
          dut.io.btbUpdateValid #= false
          dut.io.btbUpdatePc #= 0
          dut.io.btbUpdateTarget #= 0
          dut.io.btbUpdateType #= 0
          dut.io.btbUpdateDirectionTrained #= false
          dut.io.phtUpdateValid #= false
          dut.io.phtUpdatePc #= 0
          dut.io.phtUpdateIndex #= 0
          dut.io.phtUpdateOldState #= 0
          dut.io.phtUpdateOldValid #= false
          dut.io.phtUpdateTaken #= false
          dut.io.speculativeHistoryValid #= false
          dut.io.speculativeHistoryTaken #= false
          dut.io.speculativeRasPush #= false
          dut.io.speculativeRasPop #= false
          dut.io.speculativeReturnAddress #= 0
          dut.io.commitRasPush #= false
          dut.io.commitRasPop #= false
          dut.io.commitReturnAddress #= 0
          dut.io.flush #= false
        }

        def resetState(): Unit = {
          clearInputs()
          dut.clockDomain.assertReset()
          dut.clockDomain.waitSampling(2)
          dut.clockDomain.deassertReset()
          dut.clockDomain.waitSampling(132)
          sleep(1)
        }

        final case class BankPrediction(
            responseValid: Boolean,
            hit: Boolean,
            phtValid: Boolean,
            branchType: Int,
            phtState: Int,
            phtIndex: Int,
            target: BigInt,
            fallbackTaken: Boolean
        )

        def lookup(pc: BigInt, bank: Int = 0): BankPrediction = {
          dut.io.lookupPc #= pc & WordMask
          dut.io.lookupValid #= true
          dut.clockDomain.waitSampling()
          dut.io.lookupValid #= false
          dut.clockDomain.waitSampling()
          val result = BankPrediction(
            dut.io.responseValid.toBoolean,
            dut.io.prediction(bank).hit.toBoolean,
            dut.io.prediction(bank).phtValid.toBoolean,
            dut.io.prediction(bank).branchType.toInt,
            dut.io.prediction(bank).phtState.toInt,
            dut.io.prediction(bank).phtIndex.toInt,
            dut.io.prediction(bank).target.toBigInt,
            dut.io.prediction(bank).fallbackTaken.toBoolean
          )
          dut.clockDomain.waitSampling()
          assert(
            !dut.io.responseValid.toBoolean,
            "a lookup response lasted more than one cycle"
          )
          result
        }

        def phtUpdate(
            pc: BigInt,
            taken: Boolean,
            index: Int,
            oldState: Int = 0,
            oldValid: Boolean = false
        ): Unit = {
          dut.io.phtUpdateValid #= true
          dut.io.phtUpdatePc #= pc & WordMask
          dut.io.phtUpdateTaken #= taken
          dut.io.phtUpdateIndex #= index
          dut.io.phtUpdateOldState #= oldState
          dut.io.phtUpdateOldValid #= oldValid
          dut.clockDomain.waitSampling()
          dut.io.phtUpdateValid #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        def speculativeHistory(taken: Boolean): Unit = {
          dut.io.speculativeHistoryValid #= true
          dut.io.speculativeHistoryTaken #= taken
          dut.clockDomain.waitSampling()
          dut.io.speculativeHistoryValid #= false
          sleep(1)
        }

        def flushWithCommit(taken: Boolean, index: Int = 0): Unit = {
          dut.io.flush #= true
          dut.io.phtUpdateValid #= true
          dut.io.phtUpdatePc #= BigInt("1c000000", 16)
          dut.io.phtUpdateTaken #= taken
          dut.io.phtUpdateIndex #= index
          dut.io.phtUpdateOldState #= 0
          dut.io.phtUpdateOldValid #= false
          dut.clockDomain.waitSampling()
          dut.io.flush #= false
          dut.io.phtUpdateValid #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        val branchPc = BigInt("1c000000", 16)
        // phtIndex = {ghr(4:0), pc(8:4)}; with pc(8:4)=0 the lower five bits are the folded GHR.
        assert((branchPc >> 4 & 0x1f) == 0, "test PC must keep pc(8:4) clear")

        resetState()
        // Architectural history: taken, taken -> GHR = 0b11 = 3.
        phtUpdate(branchPc, taken = true, index = 0)
        phtUpdate(branchPc, taken = true, index = 0)
        // Speculative GHR mirrors architecture: two takens fold to 0b11.
        speculativeHistory(taken = true)
        speculativeHistory(taken = true)
        val beforeFlush = lookup(branchPc)
        assert(
          beforeFlush.phtIndex == 3 * 32,
          s"expected speculative GHR 0b11 folded into phtIndex, got ${beforeFlush.phtIndex}"
        )

        // Flush coincident with an architectural commit (not-taken) folds the new direction in.
        flushWithCommit(taken = false)
        val afterFlush = lookup(branchPc)
        // arch GHR 0b11 shifted right by the new taken bit gives 0b110 = 6.
        assert(
          afterFlush.phtIndex == 6 * 32,
          s"expected flushed GHR 0b110 folded into phtIndex, got ${afterFlush.phtIndex}"
        )
      }
  }

  test(
    "RAS push/pop staging survives flush recovery and ret prediction falls back to BTB on empty stack"
  ) {
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
      .compile(new OooBankedFetchPredictor(OooCoreConfig.FourIssueThreeCommit))
      .doSim("banked-ras-recovery", 0x1dac8c) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        def clearInputs(): Unit = {
          dut.io.lookupValid #= false
          dut.io.lookupPc #= 0
          dut.io.btbUpdateValid #= false
          dut.io.btbUpdatePc #= 0
          dut.io.btbUpdateTarget #= 0
          dut.io.btbUpdateType #= 0
          dut.io.btbUpdateDirectionTrained #= false
          dut.io.phtUpdateValid #= false
          dut.io.phtUpdatePc #= 0
          dut.io.phtUpdateIndex #= 0
          dut.io.phtUpdateOldState #= 0
          dut.io.phtUpdateOldValid #= false
          dut.io.phtUpdateTaken #= false
          dut.io.speculativeHistoryValid #= false
          dut.io.speculativeHistoryTaken #= false
          dut.io.speculativeRasPush #= false
          dut.io.speculativeRasPop #= false
          dut.io.speculativeReturnAddress #= 0
          dut.io.commitRasPush #= false
          dut.io.commitRasPop #= false
          dut.io.commitReturnAddress #= 0
          dut.io.flush #= false
        }

        def resetState(): Unit = {
          clearInputs()
          dut.clockDomain.assertReset()
          dut.clockDomain.waitSampling(2)
          dut.clockDomain.deassertReset()
          dut.clockDomain.waitSampling(132)
          sleep(1)
        }

        final case class BankPrediction(
            responseValid: Boolean,
            hit: Boolean,
            phtValid: Boolean,
            branchType: Int,
            phtState: Int,
            phtIndex: Int,
            target: BigInt,
            fallbackTaken: Boolean
        )

        def lookup(pc: BigInt, bank: Int = 0): BankPrediction = {
          dut.io.lookupPc #= pc & WordMask
          dut.io.lookupValid #= true
          dut.clockDomain.waitSampling()
          dut.io.lookupValid #= false
          dut.clockDomain.waitSampling()
          val result = BankPrediction(
            dut.io.responseValid.toBoolean,
            dut.io.prediction(bank).hit.toBoolean,
            dut.io.prediction(bank).phtValid.toBoolean,
            dut.io.prediction(bank).branchType.toInt,
            dut.io.prediction(bank).phtState.toInt,
            dut.io.prediction(bank).phtIndex.toInt,
            dut.io.prediction(bank).target.toBigInt,
            dut.io.prediction(bank).fallbackTaken.toBoolean
          )
          dut.clockDomain.waitSampling()
          assert(
            !dut.io.responseValid.toBoolean,
            "a lookup response lasted more than one cycle"
          )
          result
        }

        def btbUpdate(
            pc: BigInt,
            target: BigInt,
            branchType: Int = Conditional,
            directionTrained: Boolean = false
        ): Unit = {
          dut.io.btbUpdateValid #= true
          dut.io.btbUpdatePc #= pc & WordMask
          dut.io.btbUpdateTarget #= target & WordMask
          dut.io.btbUpdateType #= branchType
          dut.io.btbUpdateDirectionTrained #= directionTrained
          dut.clockDomain.waitSampling()
          dut.io.btbUpdateValid #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        def commitRas(push: Boolean, pop: Boolean, address: BigInt): Unit = {
          dut.io.commitRasPush #= push
          dut.io.commitRasPop #= pop
          dut.io.commitReturnAddress #= address & WordMask
          dut.clockDomain.waitSampling()
          dut.io.commitRasPush #= false
          dut.io.commitRasPop #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        def speculativeRas(push: Boolean, pop: Boolean, address: BigInt): Unit = {
          dut.io.speculativeRasPush #= push
          dut.io.speculativeRasPop #= pop
          dut.io.speculativeReturnAddress #= address & WordMask
          dut.clockDomain.waitSampling()
          dut.io.speculativeRasPush #= false
          dut.io.speculativeRasPop #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        def flush(): Unit = {
          dut.io.flush #= true
          dut.clockDomain.waitSampling()
          dut.io.flush #= false
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        val retPc = BigInt("1c000000", 16)
        val fallbackTarget = BigInt("1c0fff00", 16)
        val commitAddress = BigInt("1c001000", 16)
        val speculativeAddress = BigInt("1c002000", 16)
        val secondAddress = BigInt("1c003000", 16)

        resetState()
        btbUpdate(retPc, fallbackTarget, branchType = Ret)

        // Empty speculative stack (matching architectural) falls back to the BTB target.
        val empty = lookup(retPc)
        assert(empty.hit)
        assert(empty.branchType == Ret)
        assert(empty.target == fallbackTarget, "empty RAS must fall back to the BTB target")

        // Architectural push is staged; speculative push tracks on top of it.
        commitRas(push = true, pop = false, address = commitAddress)
        speculativeRas(push = true, pop = false, address = speculativeAddress)
        val onTop = lookup(retPc)
        assert(onTop.hit)
        assert(onTop.target == speculativeAddress, "speculative RAS top must override the BTB target")

        // Speculative pop exposes the architectural entry beneath it.
        speculativeRas(push = false, pop = true, address = 0)
        val afterPop = lookup(retPc)
        assert(afterPop.target == commitAddress, "pop must expose the entry below the speculative top")

        // Flush discards the speculative push and restores the architectural stack.
        speculativeRas(push = true, pop = false, address = secondAddress)
        flush()
        val afterFlush = lookup(retPc)
        assert(
          afterFlush.target == commitAddress,
          "flush must restore the architectural RAS top, not the speculative entry"
        )

        // A ret is predicted and committed: the speculative pop runs ahead of the
        // architectural pop, draining the remaining entry from both stacks.
        speculativeRas(push = false, pop = true, address = 0)
        commitRas(push = false, pop = true, address = 0)
        val drained = lookup(retPc)
        assert(
          drained.target == fallbackTarget,
          "drained architectural stack must fall back to the BTB target"
        )
      }
  }
}
