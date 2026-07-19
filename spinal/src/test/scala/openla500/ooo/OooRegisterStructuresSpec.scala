package openla500.ooo

import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooRegisterMapProbe(config: OooCoreConfig) extends Component {
  val io = new Bundle {
    val renameValid = in Bits (config.renameWidth bits)
    val renameSource1 = in Vec (UInt(config.archRegIndexWidth bits), config.renameWidth)
    val renameSource2 = in Vec (UInt(config.archRegIndexWidth bits), config.renameWidth)
    val renameDestination = in Vec (UInt(config.archRegIndexWidth bits), config.renameWidth)
    val renamePdst = in Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)
    val renamePsrc1 = out Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)
    val renamePsrc2 = out Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)
    val renameSource1Ready = out Bits (config.renameWidth bits)
    val renameSource2Ready = out Bits (config.renameWidth bits)
    val renameOldPdst = out Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)
    val writebackValid = in Bits (config.writebackWidth bits)
    val writebackPdst = in Vec (UInt(config.physicalRegIndexWidth bits), config.writebackWidth)
    val commitValid = in Bits (config.commitWidth bits)
    val commitArch = in Vec (UInt(config.archRegIndexWidth bits), config.commitWidth)
    val commitPdst = in Vec (UInt(config.physicalRegIndexWidth bits), config.commitWidth)
    val commitPreviousPdst = out Vec (UInt(config.physicalRegIndexWidth bits), config.commitWidth)
    val flush = in Bool ()
  }
  noIoPrefix()

  val registerMap = new OooRegisterMap(config)
  registerMap.io.renameValid := io.renameValid
  registerMap.io.renameSource1 := io.renameSource1
  registerMap.io.renameSource2 := io.renameSource2
  registerMap.io.renameDestination := io.renameDestination
  registerMap.io.renamePdst := io.renamePdst
  registerMap.io.writebackValid := io.writebackValid
  registerMap.io.writebackPdst := io.writebackPdst
  registerMap.io.commitValid := io.commitValid
  registerMap.io.commitArch := io.commitArch
  registerMap.io.commitPdst := io.commitPdst
  registerMap.io.flush := io.flush

  io.renamePsrc1 := registerMap.io.renamePsrc1
  io.renamePsrc2 := registerMap.io.renamePsrc2
  io.renameSource1Ready := registerMap.io.renameSource1Ready
  io.renameSource2Ready := registerMap.io.renameSource2Ready
  io.renameOldPdst := registerMap.io.renameOldPdst
  io.commitPreviousPdst := registerMap.io.commitPreviousPdst
}

class OooRegisterStructuresSpec extends AnyFunSuite {
  private def clearInputs(dut: OooRegisterMapProbe, config: OooCoreConfig): Unit = {
    dut.io.renameValid #= 0
    dut.io.writebackValid #= 0
    dut.io.commitValid #= 0
    dut.io.flush #= false
    for (lane <- 0 until config.renameWidth) {
      dut.io.renameSource1(lane) #= 0
      dut.io.renameSource2(lane) #= 0
      dut.io.renameDestination(lane) #= 0
      dut.io.renamePdst(lane) #= 0
    }
    for (lane <- 0 until config.writebackWidth) {
      dut.io.writebackPdst(lane) #= 0
    }
    for (lane <- 0 until config.commitWidth) {
      dut.io.commitArch(lane) #= 0
      dut.io.commitPdst(lane) #= 0
    }
  }

  private def sample(dut: OooRegisterMapProbe): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  test("rename handles same-cycle RAW and WAW in lane order") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-registers")
      .compile(new OooRegisterMapProbe(config))
      .doSim("ooo-register-same-cycle-dependencies", 0x5241) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.renameValid #= 3
        dut.io.renameDestination(0) #= 5
        dut.io.renameDestination(1) #= 5
        dut.io.renameSource1(1) #= 5
        dut.io.renamePdst(0) #= 10
        dut.io.renamePdst(1) #= 11
        sleep(1)

        assert(dut.io.renamePsrc1(0).toBigInt == 0)
        assert((dut.io.renameSource1Ready.toBigInt & 1) == 1)
        assert(dut.io.renamePsrc1(1).toBigInt == 10)
        assert((dut.io.renameSource1Ready.toBigInt & 2) == 0)
        assert(dut.io.renameOldPdst(0).toBigInt == 0)
        assert(dut.io.renameOldPdst(1).toBigInt == 10)
      }
  }

  test("writeback wakes the current physical source and commit history is ordered") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-registers")
      .compile(new OooRegisterMapProbe(config))
      .doSim("ooo-register-wakeup-and-commit-history", 0x5242) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.renameValid #= 1
        dut.io.renameDestination(0) #= 7
        dut.io.renamePdst(0) #= 12
        sample(dut)

        dut.io.renameValid #= 0
        dut.io.renameSource1(0) #= 7
        dut.io.writebackValid #= 1
        dut.io.writebackPdst(0) #= 12
        sleep(1)
        assert(dut.io.renamePsrc1(0).toBigInt == 12)
        assert((dut.io.renameSource1Ready.toBigInt & 1) == 1)

        dut.io.writebackValid #= 0
        dut.io.commitValid #= 3
        dut.io.commitArch(0) #= 7
        dut.io.commitArch(1) #= 7
        dut.io.commitPdst(0) #= 12
        dut.io.commitPdst(1) #= 13
        sleep(1)
        assert(dut.io.commitPreviousPdst(0).toBigInt == 0)
        assert(dut.io.commitPreviousPdst(1).toBigInt == 12)
        sample(dut)

        dut.io.commitValid #= 0
        dut.io.flush #= true
        sample(dut)
        assert(dut.io.renamePsrc1(0).toBigInt == 13)
      }
  }
}
