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
    val allocateReady = out Bool ()
    val allocatedPointer = out Vec (UInt(config.robPointerWidth bits), config.renameWidth)
    val completionValid = in Bits (config.writebackWidth bits)
    val completionRobPointer = in Vec (UInt(config.robPointerWidth bits), config.writebackWidth)
    val completionAccepted = out Bits (config.writebackWidth bits)
    val commitValid = out Bits (config.commitWidth bits)
    val occupancy = out UInt (log2Up(config.robEntries + 1) bits)
    val empty = out Bool ()
    val headPointer = out UInt (config.robPointerWidth bits)
  }
  noIoPrefix()

  val rob = new OooRob(config)
  for (lane <- 0 until config.renameWidth) {
    rob.io.allocate(lane).assignFromBits(B(0, rob.io.allocate(lane).getBitsWidth bits))
  }
  rob.io.completionValid := io.completionValid
  for (lane <- 0 until config.writebackWidth) {
    val completion = rob.io.completion(lane)
    completion.robPointer := io.completionRobPointer(lane)
    completion.pdst := 0
    completion.writesPdst := False
    completion.data := 0
    completion.sideEffectData := 0
    completion.exception.valid := False
    completion.exception.ecode := 0
    completion.exception.esubcode := 0
    completion.exception.badVAddrValid := False
    completion.exception.badVAddr := 0
    completion.exception.tlbRefill := False
    completion.branchResolved := False
    completion.branchTaken := False
    completion.branchTarget := 0
    completion.branchMispredict := False
  }
  rob.io.allocateValid := io.allocateValid
  rob.io.allocateAccept := io.allocateAccept
  rob.io.flush := io.flush

  io.allocateReady := rob.io.allocateReady
  io.allocatedPointer := rob.io.allocatedPointer
  io.completionAccepted := rob.io.completionAccepted
  io.commitValid := rob.io.commitValid
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
    for (lane <- 0 until config.writebackWidth) {
      dut.io.completionRobPointer(lane) #= 0
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
        assert(dut.io.completionAccepted.toBigInt == 0)
        sample()
        assert(dut.io.commitValid.toBigInt == 0)

        dut.io.completionRobPointer(0) #= newPointer
        sleep(1)
        assert(dut.io.completionAccepted.toBigInt == 1)
        sample()
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
        assert(dut.io.completionAccepted.toBigInt == 4)
        assert(dut.io.commitValid.toBigInt == 0)
        sample()
        assert(dut.io.commitValid.toBigInt == 0)

        dut.io.completionRobPointer(0) #= 0
        dut.io.completionRobPointer(1) #= 1
        dut.io.completionValid #= 3
        sleep(1)
        assert(dut.io.completionAccepted.toBigInt == 3)
        assert(dut.io.commitValid.toBigInt == 0)
        sample()
        assert(dut.io.commitValid.toBigInt == 7)

        dut.io.completionValid #= 0
        sample()
        assert(dut.io.occupancy.toBigInt == 0)
        assert(dut.io.empty.toBoolean)
      }
  }
}
