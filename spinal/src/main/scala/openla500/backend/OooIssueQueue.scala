package openla500.backend

import openla500.core._
import spinal.core._
import spinal.lib._

final class OooIssueQueue(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit,
    portIndex: Int = 0
) extends Component {
  require(portIndex >= 0 && portIndex < config.executionWidth)

  private def selectLowest(mask: Bits): UInt = {
    val selected = UInt(log2Up(config.issueQueueEntriesPerPort) bits)
    selected := 0
    for (index <- (0 until config.issueQueueEntriesPerPort).reverse) {
      when(mask(index)) { selected := U(index, selected.getWidth bits) }
    }
    selected
  }

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

  // Keep resident uops compacted in age order, as the ysyx issue queue does.
  // Wakeup-to-select therefore crosses one payload lookup instead of an age
  // lookup followed by a second physical-slot lookup.
  val queue = Vec.fill(config.issueQueueEntriesPerPort)(Reg(OooRenamedUop(config)))
  val count = Reg(UInt(log2Up(config.issueQueueEntriesPerPort + 1) bits)) init (0)

  val wakeupEntry1 = Bits(config.issueQueueEntriesPerPort bits)
  val wakeupEntry2 = Bits(config.issueQueueEntriesPerPort bits)
  for (entry <- 0 until config.issueQueueEntriesPerPort) {
    wakeupEntry1(entry) := False
    wakeupEntry2(entry) := False
    for (write <- 0 until config.writebackWidth) {
      when(io.wakeupValid(write) && io.wakeupPdst(write) === queue(entry).psrc1) {
        wakeupEntry1(entry) := True
      }
      when(io.wakeupValid(write) && io.wakeupPdst(write) === queue(entry).psrc2) {
        wakeupEntry2(entry) := True
      }
    }
  }

  val readyMap = Bits(config.issueQueueEntriesPerPort bits)
  for (entry <- 0 until config.issueQueueEntriesPerPort) {
    val storeDataIsDecoupled =
      if (config.executionPorts(portIndex).capabilities.contains(OooFuKind.LoadStore)) {
        queue(entry).decoded.isStore
      } else {
        False
      }
    readyMap(entry) := U(entry, count.getWidth bits) < count &&
      (queue(entry).source1Ready || wakeupEntry1(entry)) &&
      (storeDataIsDecoupled || queue(entry).source2Ready || wakeupEntry2(entry)) &&
      (!queue(entry).decoded.serializing || queue(entry).robPointer === io.robHeadPointer)
  }

  val issueIndex = selectLowest(readyMap)
  val issueIndexWide = UInt(count.getWidth bits)
  issueIndexWide := issueIndex.resize(count.getWidth)
  val selectedUop = OooRenamedUop(config)
  selectedUop := queue(issueIndex)
  val queueDequeue = Bool()

  if (config.executionPorts(portIndex).registeredIssueOutput) {
    val outputSlots = Vec.fill(2)(Reg(OooRenamedUop(config)))
    val outputReadPointer = RegInit(False)
    val outputWritePointer = RegInit(False)
    val outputCount = Reg(UInt(2 bits)) init (0)
    val outputEnqueueReady = RegInit(True)

    val outputHead = OooRenamedUop(config)
    outputHead := outputSlots(0)
    when(outputReadPointer) { outputHead := outputSlots(1) }
    io.issueValid := outputCount =/= 0
    io.issue := outputHead

    val outputDequeue = io.issueValid && io.issueReady
    queueDequeue := outputEnqueueReady && readyMap.orR
    val nextOutputCount = UInt(outputCount.getWidth bits)
    nextOutputCount := outputCount + queueDequeue.asUInt - outputDequeue.asUInt

    when(io.flush) {
      outputCount := 0
      outputReadPointer := False
      outputWritePointer := False
      outputEnqueueReady := True
    }.otherwise {
      outputCount := nextOutputCount
      outputEnqueueReady := nextOutputCount < 2
      when(queueDequeue) { outputWritePointer := !outputWritePointer }
      when(outputDequeue) { outputReadPointer := !outputReadPointer }
    }
    // outputCount alone defines visibility.  Let an invalid slot absorb the
    // flush-edge payload write so redirect does not drive every payload CE.
    when(queueDequeue) {
      when(outputWritePointer) {
        outputSlots(1) := selectedUop
      }.otherwise {
        outputSlots(0) := selectedUop
      }
    }

    io.occupancy := (count + outputCount).resized
  } else {
    io.issueValid := readyMap.orR
    io.issue := selectedUop
    queueDequeue := io.issueValid && io.issueReady
    io.occupancy := count
  }

  // Register the backpressure boundary. Reserve one slot because the ready
  // value describes the previous cycle's count; one enqueue per cycle per IQ
  // cannot overrun the remaining slot.
  val enqueueReadyReg = Reg(Bool()) init (True)
  enqueueReadyReg := count < U(config.issueQueueEntriesPerPort - 1, count.getWidth bits)
  // Ready/valid are candidate handshakes during recovery.  The sequential
  // flush branches below have priority over every enqueue/dequeue update.
  io.enqueueReady := enqueueReadyReg
  val enqueueFire = io.enqueueValid && io.enqueueReady
  val enqueueIndex = UInt(log2Up(config.issueQueueEntriesPerPort) bits)
  enqueueIndex := count.resized
  when(queueDequeue) { enqueueIndex := (count - 1).resized }

  val enqueueWakeup1 = io.wakeupValid.asBools
    .zip(io.wakeupPdst)
    .map { case (wakeValid, pdst) => wakeValid && pdst === io.enqueue.psrc1 }
    .reduce(_ || _)
  val enqueueWakeup2 = io.wakeupValid.asBools
    .zip(io.wakeupPdst)
    .map { case (wakeValid, pdst) => wakeValid && pdst === io.enqueue.psrc2 }
    .reduce(_ || _)
  val enqueued = OooRenamedUop(config)
  enqueued.decoded := io.enqueue.decoded
  enqueued.pdst := io.enqueue.pdst
  enqueued.oldPdst := io.enqueue.oldPdst
  enqueued.psrc1 := io.enqueue.psrc1
  enqueued.psrc2 := io.enqueue.psrc2
  enqueued.source1Ready := io.enqueue.source1Ready || enqueueWakeup1
  enqueued.source2Ready := io.enqueue.source2Ready || enqueueWakeup2
  enqueued.robPointer := io.enqueue.robPointer
  enqueued.recoveryEpoch := io.enqueue.recoveryEpoch
  enqueued.loadQueueIndex := io.enqueue.loadQueueIndex
  enqueued.storeQueueIndex := io.enqueue.storeQueueIndex

  when(io.flush) {
    count := 0
  }.otherwise {
    count := count + enqueueFire.asUInt - queueDequeue.asUInt
  }
  // count alone defines resident entries.  Payload mutation on a flush edge
  // is harmless and keeps the redirect net out of every wide queue CE.
  for (entry <- 0 until config.issueQueueEntriesPerPort) {
    val entryEnqueue = enqueueFire &&
      enqueueIndex === U(entry, log2Up(config.issueQueueEntriesPerPort) bits)
    if (entry < config.issueQueueEntriesPerPort - 1) {
      val entryShift = queueDequeue &&
        U(entry, count.getWidth bits) >= issueIndexWide &&
        U(entry + 1, count.getWidth bits) < count
      when(entryEnqueue) {
        queue(entry) := enqueued
      }.elsewhen(entryShift) {
        queue(entry).decoded := queue(entry + 1).decoded
        queue(entry).pdst := queue(entry + 1).pdst
        queue(entry).oldPdst := queue(entry + 1).oldPdst
        queue(entry).psrc1 := queue(entry + 1).psrc1
        queue(entry).psrc2 := queue(entry + 1).psrc2
        queue(entry).source1Ready :=
          queue(entry + 1).source1Ready || wakeupEntry1(entry + 1)
        queue(entry).source2Ready :=
          queue(entry + 1).source2Ready || wakeupEntry2(entry + 1)
        queue(entry).robPointer := queue(entry + 1).robPointer
        queue(entry).recoveryEpoch := queue(entry + 1).recoveryEpoch
        queue(entry).loadQueueIndex := queue(entry + 1).loadQueueIndex
        queue(entry).storeQueueIndex := queue(entry + 1).storeQueueIndex
      }.otherwise {
        when(wakeupEntry1(entry)) { queue(entry).source1Ready := True }
        when(wakeupEntry2(entry)) { queue(entry).source2Ready := True }
      }
    } else {
      when(entryEnqueue) {
        queue(entry) := enqueued
      }.otherwise {
        when(wakeupEntry1(entry)) { queue(entry).source1Ready := True }
        when(wakeupEntry2(entry)) { queue(entry).source2Ready := True }
      }
    }
  }
}

final class OooDispatchRouter(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private def accepts(port: OooExecPortConfig, uop: OooRenamedUop): Bool = {
    val acceptedKinds = port.capabilities.toVector.map {
      case OooFuKind.Alu       => uop.decoded.fuType === OooFuType.alu
      case OooFuKind.Branch    => uop.decoded.fuType === OooFuType.branch
      case OooFuKind.Multiply  => uop.decoded.fuType === OooFuType.multiply
      case OooFuKind.Divide    => uop.decoded.fuType === OooFuType.divide
      case OooFuKind.Csr       => uop.decoded.fuType === OooFuType.csr
      case OooFuKind.Serial    =>
        uop.decoded.fuType === OooFuType.serial || OooFuType.isBarrier(uop.decoded.fuType)
      case OooFuKind.LoadStore => uop.decoded.fuType === OooFuType.loadStore
    }
    acceptedKinds.reduce(_ || _)
  }

  private def selectLowest(mask: Bits): UInt = {
    val selected = UInt(log2Up(config.executionWidth) bits)
    selected := 0
    for (index <- (0 until config.executionWidth).reverse) {
      when(mask(index)) { selected := U(index, selected.getWidth bits) }
    }
    selected
  }

  val io = new Bundle {
    val inputValid = in Bits (config.dispatchWidth bits)
    val input = in Vec (OooRenamedUop(config), config.dispatchWidth)
    val inputReady = out Bits (config.dispatchWidth bits)
    val portReady = in Bits (config.executionWidth bits)
    val portValid = out Bits (config.executionWidth bits)
    val portInput = out Vec (OooRenamedUop(config), config.executionWidth)
  }

  val portUsed = Vec(Bits(config.executionWidth bits), config.dispatchWidth + 1)
  portUsed(0) := 0
  val laneOpen = Vec(Bool(), config.dispatchWidth + 1)
  laneOpen(0) := True
  val choices = Vec(Bits(config.executionWidth bits), config.dispatchWidth)
  for (lane <- 0 until config.dispatchWidth) {
    val capable = Bits(config.executionWidth bits)
    for (port <- 0 until config.executionWidth) {
      capable(port) := io.inputValid(lane) && io.portReady(port) &&
        accepts(config.executionPorts(port), io.input(lane))
    }
    val available = capable & ~portUsed(lane)
    choices(lane) := B(0, config.executionWidth bits)
    when(laneOpen(lane) && available.orR) {
      choices(lane) := UIntToOh(selectLowest(available), config.executionWidth)
    }
    portUsed(lane + 1) := portUsed(lane) | choices(lane)
    io.inputReady(lane) := laneOpen(lane) && available.orR
    laneOpen(lane + 1) := laneOpen(lane) && (!io.inputValid(lane) || available.orR)
  }

  for (port <- 0 until config.executionWidth) {
    io.portValid(port) := choices.map(_(port)).reduce(_ || _)
    io.portInput(port) := io.input(0)
    for (lane <- (0 until config.dispatchWidth).reverse) {
      when(choices(lane)(port)) { io.portInput(port) := io.input(lane) }
    }
  }
}
