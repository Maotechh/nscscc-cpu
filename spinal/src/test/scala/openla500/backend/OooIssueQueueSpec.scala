package openla500.backend

import openla500.core._
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

private final class OooIssueQueueProbe(config: OooCoreConfig, portIndex: Int = 0)
    extends Component {
  val io = new Bundle {
    val enqueueValid = in Bool ()
    val enqueue = in(OooRenamedUop(config))
    val enqueueReady = out Bool ()
    val wakeupValid = in Bits (config.writebackWidth bits)
    val wakeupPdst = in Vec (UInt(config.physicalRegIndexWidth bits), config.writebackWidth)
    val issueValid = out Bool ()
    val issue = out(OooRenamedUop(config))
    val issueReady = in Bool ()
    val robHeadPointer = in UInt (config.robPointerWidth bits)
    val flush = in Bool ()
    val occupancy = out UInt (log2Up(config.issueQueueEntriesPerPort + 1) bits)
  }
  noIoPrefix()

  val queue = new OooIssueQueue(config, portIndex)
  queue.io.enqueueValid := io.enqueueValid
  queue.io.enqueue := io.enqueue
  queue.io.wakeupValid := io.wakeupValid
  queue.io.wakeupPdst := io.wakeupPdst
  queue.io.issueReady := io.issueReady
  queue.io.robHeadPointer := io.robHeadPointer
  queue.io.flush := io.flush

  io.enqueueReady := queue.io.enqueueReady
  io.issueValid := queue.io.issueValid
  io.issue := queue.io.issue
  io.occupancy := queue.io.occupancy
}

class OooIssueQueueSpec extends AnyFunSuite {
  private def clearInputs(dut: OooIssueQueueProbe, config: OooCoreConfig): Unit = {
    dut.io.enqueueValid #= false
    dut.io.enqueue.decoded.serializing #= false
    dut.io.enqueue.decoded.isStore #= false
    dut.io.enqueue.pdst #= 0
    dut.io.enqueue.oldPdst #= 0
    dut.io.enqueue.psrc1 #= 0
    dut.io.enqueue.psrc2 #= 0
    dut.io.enqueue.source1Ready #= false
    dut.io.enqueue.source2Ready #= false
    dut.io.enqueue.robPointer #= 0
    dut.io.enqueue.recoveryEpoch #= 0
    dut.io.enqueue.loadQueueIndex #= 0
    dut.io.enqueue.storeQueueIndex #= 0
    dut.io.wakeupValid #= 0
    for (lane <- 0 until config.writebackWidth) {
      dut.io.wakeupPdst(lane) #= 0
    }
    dut.io.issueReady #= false
    dut.io.robHeadPointer #= 0
    dut.io.flush #= false
  }

  private def sample(dut: OooIssueQueueProbe): Unit = {
    dut.clockDomain.waitSampling()
    sleep(1)
  }

  test("IQ removes the selected younger ready entry without duplicating it") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-iq")
      .compile(new OooIssueQueueProbe(config))
      .doSim("ooo-iq-selective-compaction", 0x4951) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 0
        dut.io.enqueue.psrc1 #= 5
        dut.io.enqueue.psrc2 #= 0
        dut.io.enqueue.source1Ready #= false
        dut.io.enqueue.source2Ready #= true
        assert(dut.io.enqueueReady.toBoolean)
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 1)

        dut.io.enqueue.robPointer #= 1
        dut.io.enqueue.psrc1 #= 0
        dut.io.enqueue.source1Ready #= true
        dut.io.enqueue.source2Ready #= true
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 2)
        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 1)

        dut.io.enqueueValid #= false
        dut.io.issueReady #= true
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 1)
        assert(!dut.io.issueValid.toBoolean)

        dut.io.wakeupValid #= 1
        dut.io.wakeupPdst(0) #= 5
        dut.io.issueReady #= false
        sleep(1)
        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 0)
      }
  }

  test("IQ wakeup follows compacted age order after an older dequeue") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-iq")
      .compile(new OooIssueQueueProbe(config))
      .doSim("ooo-iq-compacted-wakeup", 0x4956) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        // Put a ready oldest entry at the queue head.
        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 0
        dut.io.enqueue.source1Ready #= true
        dut.io.enqueue.source2Ready #= true
        sample(dut)

        // Issue the head while enqueuing a blocked entry behind it.
        dut.io.issueReady #= true
        dut.io.enqueue.robPointer #= 1
        dut.io.enqueue.psrc1 #= 5
        dut.io.enqueue.source1Ready #= false
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 1)
        assert(!dut.io.issueValid.toBoolean)

        // Enqueue a younger blocked entry after the survivor was compacted to
        // the head. Waking the younger entry must not corrupt the older tag.
        dut.io.issueReady #= false
        dut.io.enqueue.robPointer #= 2
        dut.io.enqueue.psrc1 #= 6
        sample(dut)
        dut.io.enqueueValid #= false
        assert(dut.io.occupancy.toBigInt == 2)

        dut.io.wakeupValid #= 1
        dut.io.wakeupPdst(0) #= 6
        sleep(1)
        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 2)

        // Capture the wake pulse, then prove that the stored ready bit holds
        // after the tag disappears.
        sample(dut)
        dut.io.wakeupValid #= 0
        sleep(1)
        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 2)

        dut.io.issueReady #= true
        sample(dut)
        dut.io.issueReady #= false
        assert(dut.io.occupancy.toBigInt == 1)
        assert(!dut.io.issueValid.toBoolean)

        dut.io.wakeupValid #= 1
        dut.io.wakeupPdst(0) #= 5
        sleep(1)
        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 1)
      }
  }

  test("serial IQ entries wait for the matching ROB head") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-iq")
      .compile(new OooIssueQueueProbe(config))
      .doSim("ooo-iq-serial-head", 0x4952) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 3
        dut.io.enqueue.decoded.serializing #= true
        dut.io.enqueue.source1Ready #= true
        dut.io.enqueue.source2Ready #= true
        dut.io.robHeadPointer #= 2
        sample(dut)
        assert(!dut.io.issueValid.toBoolean)

        dut.io.enqueueValid #= false
        dut.io.robHeadPointer #= 3
        sleep(1)
        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 3)
      }
  }

  test("registered IQ backpressure uses the reserved slot without overflowing") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-iq")
      .compile(new OooIssueQueueProbe(config))
      .doSim("ooo-iq-registered-full-boundary", 0x4953) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.enqueueValid #= true
        dut.io.enqueue.psrc1 #= 5
        dut.io.enqueue.psrc2 #= 6
        dut.io.enqueue.source1Ready #= false
        dut.io.enqueue.source2Ready #= false
        for (entry <- 0 until config.issueQueueEntriesPerPort) {
          dut.io.enqueue.robPointer #= entry
          sleep(1)
          assert(dut.io.enqueueReady.toBoolean)
          sample(dut)
        }

        assert(dut.io.occupancy.toBigInt == config.issueQueueEntriesPerPort)
        assert(!dut.io.enqueueReady.toBoolean)
        dut.io.enqueue.robPointer #= config.issueQueueEntriesPerPort
        sample(dut)
        assert(dut.io.occupancy.toBigInt == config.issueQueueEntriesPerPort)

        dut.io.enqueueValid #= false
        dut.io.flush #= true
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 0)
        dut.io.flush #= false
        sample(dut)
        assert(dut.io.enqueueReady.toBoolean)
      }
  }

  test("LSU IQ registered output holds backpressure and sustains one issue per cycle") {
    val config = OooCoreConfig.FourIssueThreeCommit
    val loadStorePort =
      config.executionPorts.indexWhere(_.capabilities.contains(OooFuKind.LoadStore))
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-iq")
      .compile(new OooIssueQueueProbe(config, loadStorePort))
      .doSim("ooo-iq-lsu-registered-output", 0x4954) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.enqueueValid #= true
        dut.io.enqueue.source1Ready #= true
        dut.io.enqueue.source2Ready #= true
        for (entry <- 0 until 3) {
          dut.io.enqueue.robPointer #= entry
          sample(dut)
        }
        dut.io.enqueueValid #= false

        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 0)
        assert(dut.io.occupancy.toBigInt == 3)

        dut.io.issueReady #= true
        for (entry <- 0 until 3) {
          sleep(1)
          assert(dut.io.issueValid.toBoolean)
          assert(dut.io.issue.robPointer.toBigInt == entry)
          sample(dut)
        }
        assert(!dut.io.issueValid.toBoolean)
        assert(dut.io.occupancy.toBigInt == 0)

        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 4
        dut.io.issueReady #= false
        sample(dut)
        dut.io.enqueueValid #= false
        sample(dut)
        assert(dut.io.issueValid.toBoolean)
        dut.io.flush #= true
        sample(dut)
        assert(!dut.io.issueValid.toBoolean)
        assert(dut.io.occupancy.toBigInt == 0)
      }
  }

  test("LSU IQ schedules a Store address without waiting for Store data") {
    val config = OooCoreConfig.FourIssueThreeCommit
    val loadStorePort =
      config.executionPorts.indexWhere(_.capabilities.contains(OooFuKind.LoadStore))
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-iq")
      .compile(new OooIssueQueueProbe(config, loadStorePort))
      .doSim("ooo-iq-store-address-data-decoupling", 0x4955) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.enqueueValid #= true
        dut.io.enqueue.decoded.isStore #= true
        dut.io.enqueue.source1Ready #= true
        dut.io.enqueue.source2Ready #= false
        dut.io.enqueue.psrc2 #= 7
        sample(dut)
        dut.io.enqueueValid #= false
        sample(dut)
        assert(dut.io.issueValid.toBoolean)

        dut.io.flush #= true
        sample(dut)
        dut.io.flush #= false
        dut.io.enqueueValid #= true
        dut.io.enqueue.decoded.isStore #= false
        dut.io.enqueue.source1Ready #= true
        dut.io.enqueue.source2Ready #= false
        sample(dut)
        dut.io.enqueueValid #= false
        sample(dut)
        assert(!dut.io.issueValid.toBoolean)
      }
  }

  test("flush hides simultaneous compact-queue payload mutations") {
    val config = OooCoreConfig.FourIssueThreeCommit
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-iq")
      .compile(new OooIssueQueueProbe(config))
      .doSim("ooo-iq-flush-payload-collision", 0x4957) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 1
        dut.io.enqueue.source1Ready #= true
        dut.io.enqueue.source2Ready #= true
        sample(dut)
        assert(dut.io.issueValid.toBoolean)

        dut.io.flush #= true
        dut.io.issueReady #= true
        dut.io.enqueue.robPointer #= 2
        dut.io.wakeupValid #= 1
        dut.io.wakeupPdst(0) #= 0
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 0)
        assert(!dut.io.issueValid.toBoolean)

        dut.io.flush #= false
        dut.io.issueReady #= false
        dut.io.enqueueValid #= false
        dut.io.wakeupValid #= 0
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 0)
        assert(!dut.io.issueValid.toBoolean)

        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 3
        sample(dut)
        dut.io.enqueueValid #= false
        sleep(1)
        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 3)
      }
  }

  test("flush hides simultaneous registered LSU output mutations") {
    val config = OooCoreConfig.FourIssueThreeCommit
    val loadStorePort =
      config.executionPorts.indexWhere(_.capabilities.contains(OooFuKind.LoadStore))
    SimConfig.withVerilator
      .workspacePath("target/sim-workspace-ooo-iq")
      .compile(new OooIssueQueueProbe(config, loadStorePort))
      .doSim("ooo-iq-lsu-flush-output-collision", 0x4958) { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        clearInputs(dut, config)
        dut.clockDomain.assertReset()
        dut.clockDomain.waitSampling(2)
        dut.clockDomain.deassertReset()
        sample(dut)

        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 4
        dut.io.enqueue.source1Ready #= true
        dut.io.enqueue.source2Ready #= true
        sample(dut)
        dut.io.enqueueValid #= false
        sample(dut)
        assert(dut.io.issueValid.toBoolean)

        dut.io.flush #= true
        dut.io.issueReady #= true
        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 5
        dut.io.wakeupValid #= 1
        dut.io.wakeupPdst(0) #= 0
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 0)
        assert(!dut.io.issueValid.toBoolean)

        dut.io.flush #= false
        dut.io.issueReady #= false
        dut.io.enqueueValid #= false
        dut.io.wakeupValid #= 0
        sample(dut)
        assert(dut.io.occupancy.toBigInt == 0)
        assert(!dut.io.issueValid.toBoolean)

        dut.io.enqueueValid #= true
        dut.io.enqueue.robPointer #= 6
        sample(dut)
        dut.io.enqueueValid #= false
        sample(dut)
        assert(dut.io.issueValid.toBoolean)
        assert(dut.io.issue.robPointer.toBigInt == 6)
      }
  }
}
