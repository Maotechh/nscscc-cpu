package openla500.predict

import java.nio.file.Paths
import openla500.config.CoreConfig
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

class OpenLa500PredictorSpec extends AnyFunSuite {
  private val WordMask = (BigInt(1) << 32) - 1

  test(
    "official 32-entry BTB, saturating counters and return prediction obey the active contract"
  ) {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-contracts")
    val workspace = Paths.get(workspaceRoot, "predictor").toString

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
      .compile(new OpenLa500Predictor(CoreConfig.Locked))
      .doSim("predictor-directed", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        def clearInputs(): Unit = {
          dut.io.lookup.valid #= false
          dut.io.lookup.payload.pc #= 0
          dut.io.update.valid #= false
          dut.io.update.payload.popReturnStack #= false
          dut.io.update.payload.pushReturnStack #= false
          dut.io.update.payload.addEntry #= false
          dut.io.update.payload.predictionError #= false
          dut.io.update.payload.predictionRight #= false
          dut.io.update.payload.targetError #= false
          dut.io.update.payload.actualTaken #= false
          dut.io.update.payload.actualTarget #= 0
          dut.io.update.payload.pc #= 0
          dut.io.update.payload.legacyIndex #= 0
          dut.io.update.payload.direction.phtIndex #= 0
          dut.io.update.payload.direction.baseTaken #= false
          dut.io.update.payload.direction.localTaken #= false
        }

        def resetState(): Unit = {
          clearInputs()
          dut.clockDomain.assertReset()
          dut.clockDomain.waitSampling(2)
          dut.clockDomain.deassertReset()
          dut.clockDomain.waitSampling()
          sleep(1)
        }

        def update(
            pc: BigInt,
            target: BigInt = 0,
            pop: Boolean = false,
            push: Boolean = false,
            add: Boolean = false,
            error: Boolean = false,
            right: Boolean = false,
            targetError: Boolean = false,
            actualTaken: Boolean = false,
            legacyIndex: Int = 0,
            phtIndex: Int = 0,
            baseTaken: Boolean = false,
            localTaken: Boolean = false
        ): Unit = {
          dut.io.update.payload.pc #= pc & WordMask
          dut.io.update.payload.actualTarget #= target & WordMask
          dut.io.update.payload.popReturnStack #= pop
          dut.io.update.payload.pushReturnStack #= push
          dut.io.update.payload.addEntry #= add
          dut.io.update.payload.predictionError #= error
          dut.io.update.payload.predictionRight #= right
          dut.io.update.payload.targetError #= targetError
          dut.io.update.payload.actualTaken #= actualTaken
          dut.io.update.payload.legacyIndex #= legacyIndex
          dut.io.update.payload.direction.phtIndex #= phtIndex
          dut.io.update.payload.direction.baseTaken #= baseTaken
          dut.io.update.payload.direction.localTaken #= localTaken
          dut.io.update.valid #= true
          dut.clockDomain.waitSampling()
          dut.io.update.valid #= false
          clearInputs()
          sleep(1)
        }

        final case class Prediction(valid: Boolean, taken: Boolean, target: BigInt, index: Int)

        def lookup(pc: BigInt): Prediction = {
          dut.io.lookup.payload.pc #= pc & WordMask
          dut.io.lookup.valid #= true
          dut.clockDomain.waitSampling()
          dut.io.lookup.valid #= false
          sleep(1)
          val result = Prediction(
            dut.io.prediction.valid.toBoolean,
            dut.io.prediction.payload.taken.toBoolean,
            dut.io.prediction.payload.target.toBigInt,
            dut.io.prediction.payload.legacyIndex.toInt
          )
          dut.clockDomain.waitSampling()
          sleep(1)
          assert(!dut.io.prediction.valid.toBoolean, "a lookup response lasted more than one cycle")
          assert(!dut.io.prediction.payload.taken.toBoolean)
          assert(dut.io.prediction.payload.target.toBigInt == 0)
          assert(dut.io.prediction.payload.legacyIndex.toInt == 0)
          result
        }

        def expectHit(
            pc: BigInt,
            target: BigInt,
            taken: Boolean = true,
            index: Option[Int] = None
        ): Unit = {
          val result = lookup(pc)
          assert(result.valid, f"expected hit for PC 0x$pc%08x")
          assert(result.taken == taken, f"wrong direction for PC 0x$pc%08x")
          assert(result.target == (target & WordMask), f"wrong target for PC 0x$pc%08x")
          index.foreach(expected => assert(result.index == expected))
        }

        def expectMiss(pc: BigInt): Unit = {
          val result = lookup(pc)
          assert(!result.valid, f"unexpected hit for PC 0x$pc%08x")
          assert(!result.taken)
          assert(result.target == 0)
          assert(result.index == 0)
        }

        resetState()
        expectMiss(BigInt("1c000000", 16))

        val counterPc = BigInt("1c001000", 16)
        val counterTarget = BigInt("1c002000", 16)
        update(counterPc, counterTarget, add = true, actualTaken = true)
        expectHit(counterPc, counterTarget, index = Some(0))
        update(counterPc, right = true, actualTaken = false)
        expectHit(counterPc, counterTarget, taken = false)
        update(counterPc, error = true, actualTaken = false)
        expectHit(counterPc, counterTarget, taken = false)
        update(counterPc, error = true, actualTaken = false)
        expectHit(counterPc, counterTarget, taken = false)
        update(counterPc, error = true, actualTaken = true)
        expectHit(counterPc, counterTarget, taken = false)
        update(counterPc, error = true, actualTaken = true)
        expectHit(counterPc, counterTarget)
        update(counterPc, right = true, actualTaken = true)
        update(counterPc, right = true, actualTaken = true)
        expectHit(counterPc, counterTarget)

        val correctedTarget = BigInt("1c003000", 16)
        update(BigInt("1c101000", 16), correctedTarget, targetError = true, legacyIndex = 0)
        expectHit(counterPc, correctedTarget)

        val fillBase = BigInt("1d000000", 16)
        val targetBase = BigInt("1e000000", 16)
        for (entry <- 0 until 31) {
          update(fillBase + entry * 4, targetBase + entry * 4, add = true, actualTaken = true)
        }
        expectHit(fillBase, targetBase, index = Some(1))
        expectHit(fillBase + 15 * 4, targetBase + 15 * 4, index = Some(16))
        expectHit(fillBase + 30 * 4, targetBase + 30 * 4, index = Some(31))

        val weakPc = fillBase + 11 * 4
        update(weakPc, error = true, actualTaken = false, legacyIndex = 12)
        update(weakPc, error = true, actualTaken = false, legacyIndex = 12)
        val replacementPc = BigInt("1d100000", 16)
        val replacementTarget = BigInt("1e100000", 16)
        update(replacementPc, replacementTarget, add = true, actualTaken = true)
        expectMiss(weakPc)
        expectHit(replacementPc, replacementTarget)
        expectHit(fillBase + 10 * 4, targetBase + 10 * 4)

        val randomReplacementPc = BigInt("1d200000", 16)
        val randomReplacementTarget = BigInt("1e200000", 16)
        update(randomReplacementPc, randomReplacementTarget, add = true, actualTaken = true)
        expectHit(randomReplacementPc, randomReplacementTarget)
        val oldMisses = (0 until 31).count { entry =>
          !lookup(fillBase + entry * 4).valid
        }
        val replacementWasEvicted = !lookup(replacementPc).valid
        val originalMisses = oldMisses + (if (!lookup(counterPc).valid) 1 else 0)
        assert(
          originalMisses + (if (replacementWasEvicted) 1 else 0) == 2,
          "the strongly-untaken replacement plus one LFSR replacement must be observable"
        )

        val returnPc = BigInt("1c004000", 16)
        val call0 = BigInt("1c005000", 16)
        update(returnPc, pop = true, add = true)
        expectMiss(returnPc)
        update(call0, push = true)
        expectHit(returnPc, call0 + 4)

        val call1 = BigInt("1c006000", 16)
        update(call1, push = true)
        expectHit(returnPc, call1 + 4)
        update(returnPc, pop = true)
        expectHit(returnPc, call0 + 4)
        update(returnPc, pop = true)
        expectMiss(returnPc)
        update(returnPc, pop = true)
        expectMiss(returnPc)

        for (depth <- 0 until 8) update(BigInt("1c010000", 16) + depth * 4, push = true)
        expectHit(returnPc, BigInt("1c010000", 16) + 7 * 4 + 4)
        update(BigInt("1c020000", 16), push = true)
        expectHit(returnPc, BigInt("1c010000", 16) + 7 * 4 + 4)
        update(BigInt("1c030000", 16), pop = true, push = true)
        expectHit(returnPc, BigInt("1c010000", 16) + 6 * 4 + 4)
        update(BigInt("1c040000", 16), pop = true, push = true)
        expectHit(returnPc, BigInt("1c040000", 16) + 4)

        for (_ <- 0 until 8) update(returnPc, pop = true)
        expectMiss(returnPc)
        val matcherBase = BigInt("1c100000", 16)
        for (entry <- 0 until 15) update(matcherBase + entry * 4, pop = true, add = true)
        val matcherReplacement = BigInt("1c110000", 16)
        update(matcherReplacement, pop = true, add = true)
        update(call0, push = true)
        expectHit(matcherReplacement, call0 + 4)
        val matcherMisses =
          (0 until 15).count(entry => !lookup(matcherBase + entry * 4).valid) +
            (if (!lookup(returnPc).valid) 1 else 0)
        assert(matcherMisses == 1, s"expected one replaced return-site matcher, got $matcherMisses")

        val collisionPc = BigInt("1c200000", 16)
        val branchTarget = BigInt("1c210000", 16)
        val returnTargetSource = BigInt("1c220000", 16)
        update(collisionPc, branchTarget, add = true, actualTaken = true)
        update(collisionPc, pop = true, add = true)
        update(returnTargetSource, push = true)
        expectHit(collisionPc, returnTargetSource + 4)
      }
  }

  test("local-history tournament learns a repeating direction pattern with exact update metadata") {
    val workspaceRoot =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-contracts")
    val workspace = Paths.get(workspaceRoot, "predictor-local-history").toString

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
      .compile(new OpenLa500Predictor(CoreConfig.Locked, localHistoryEnabled = true))
      .doSim("predictor-local-history-directed", 0x158aa8) { dut =>
        dut.clockDomain.forkStimulus(period = 10)

        def clearInputs(): Unit = {
          dut.io.lookup.valid #= false
          dut.io.lookup.payload.pc #= 0
          dut.io.update.valid #= false
          dut.io.update.payload.popReturnStack #= false
          dut.io.update.payload.pushReturnStack #= false
          dut.io.update.payload.addEntry #= false
          dut.io.update.payload.predictionError #= false
          dut.io.update.payload.predictionRight #= false
          dut.io.update.payload.targetError #= false
          dut.io.update.payload.actualTaken #= false
          dut.io.update.payload.actualTarget #= 0
          dut.io.update.payload.pc #= 0
          dut.io.update.payload.legacyIndex #= 0
          dut.io.update.payload.direction.phtIndex #= 0
          dut.io.update.payload.direction.baseTaken #= false
          dut.io.update.payload.direction.localTaken #= false
        }

        final case class Prediction(
            taken: Boolean,
            target: BigInt,
            legacyIndex: Int,
            phtIndex: Int,
            baseTaken: Boolean,
            localTaken: Boolean
        )

        def lookup(pc: BigInt): Prediction = {
          dut.io.lookup.payload.pc #= pc & WordMask
          dut.io.lookup.valid #= true
          dut.clockDomain.waitSampling()
          dut.io.lookup.valid #= false
          sleep(1)
          assert(dut.io.prediction.valid.toBoolean)
          val prediction = Prediction(
            dut.io.prediction.payload.taken.toBoolean,
            dut.io.prediction.payload.target.toBigInt,
            dut.io.prediction.payload.legacyIndex.toInt,
            dut.io.prediction.payload.direction.phtIndex.toInt,
            dut.io.prediction.payload.direction.baseTaken.toBoolean,
            dut.io.prediction.payload.direction.localTaken.toBoolean
          )
          dut.clockDomain.waitSampling()
          sleep(1)
          assert(!dut.io.prediction.valid.toBoolean)
          prediction
        }

        def train(pc: BigInt, prediction: Prediction, actualTaken: Boolean): Unit = {
          dut.io.update.payload.pc #= pc & WordMask
          dut.io.update.payload.actualTarget #= BigInt("1c301000", 16)
          dut.io.update.payload.actualTaken #= actualTaken
          dut.io.update.payload.legacyIndex #= prediction.legacyIndex
          dut.io.update.payload.predictionError #= prediction.taken != actualTaken
          dut.io.update.payload.predictionRight #= prediction.taken == actualTaken
          dut.io.update.payload.direction.phtIndex #= prediction.phtIndex
          dut.io.update.payload.direction.baseTaken #= prediction.baseTaken
          dut.io.update.payload.direction.localTaken #= prediction.localTaken
          dut.io.update.valid #= true
          dut.clockDomain.waitSampling()
          clearInputs()
          sleep(1)
        }

        clearInputs()
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        dut.clockDomain.waitSampling()

        val pc = BigInt("1c300120", 16)
        val target = BigInt("1c301000", 16)
        dut.io.update.payload.pc #= pc
        dut.io.update.payload.actualTarget #= target
        dut.io.update.payload.actualTaken #= true
        dut.io.update.payload.addEntry #= true
        dut.io.update.valid #= true
        dut.clockDomain.waitSampling()
        clearInputs()

        var history = 1
        var correctAfterWarmup = 0
        for (iteration <- 0 until 28) {
          val actualTaken = (iteration & 1) == 1
          val prediction = lookup(pc)
          val expectedIndex = history ^ ((pc >> 2) & 0xff).toInt
          assert(prediction.target == target)
          assert(prediction.legacyIndex == 0)
          assert(prediction.phtIndex == expectedIndex)
          if (iteration >= 16 && prediction.taken == actualTaken) correctAfterWarmup += 1
          train(pc, prediction, actualTaken)
          history = ((history << 1) | (if (actualTaken) 1 else 0)) & 0xff
        }
        assert(correctAfterWarmup >= 11, s"local predictor only got $correctAfterWarmup/12 correct")

        // Target repair shares the update cycle with direction training and must preserve both the
        // learned direction state and the exact prediction-time PHT index contract.
        val prediction = lookup(pc)
        val correctedTarget = BigInt("1c302000", 16)
        dut.io.update.payload.pc #= pc
        dut.io.update.payload.actualTarget #= correctedTarget
        dut.io.update.payload.actualTaken #= prediction.taken
        dut.io.update.payload.legacyIndex #= prediction.legacyIndex
        dut.io.update.payload.predictionRight #= true
        dut.io.update.payload.targetError #= true
        dut.io.update.payload.direction.phtIndex #= prediction.phtIndex
        dut.io.update.payload.direction.baseTaken #= prediction.baseTaken
        dut.io.update.payload.direction.localTaken #= prediction.localTaken
        dut.io.update.valid #= true
        dut.clockDomain.waitSampling()
        clearInputs()
        val repaired = lookup(pc)
        assert(repaired.target == correctedTarget)
      }
  }
}
