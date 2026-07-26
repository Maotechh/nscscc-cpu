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

  val slotValid = Vec.fill(config.issueQueueEntriesPerPort)(Reg(Bool()) init (False))
  val payloadSlots = Vec.fill(config.issueQueueEntriesPerPort)(Reg(OooRenamedUop(config)))
  val order = Vec.fill(config.issueQueueEntriesPerPort)(
    Reg(UInt(log2Up(config.issueQueueEntriesPerPort) bits)) init (0)
  )
  val count = Reg(UInt(log2Up(config.issueQueueEntriesPerPort + 1) bits)) init (0)

  val wakeupReady1 = Bits(config.issueQueueEntriesPerPort bits)
  val wakeupReady2 = Bits(config.issueQueueEntriesPerPort bits)
  for (entry <- 0 until config.issueQueueEntriesPerPort) {
    wakeupReady1(entry) := False
    wakeupReady2(entry) := False
    for (write <- 0 until config.writebackWidth) {
      when(io.wakeupValid(write) && io.wakeupPdst(write) === payloadSlots(order(entry)).psrc1) {
        wakeupReady1(entry) := True
      }
      when(io.wakeupValid(write) && io.wakeupPdst(write) === payloadSlots(order(entry)).psrc2) {
        wakeupReady2(entry) := True
      }
    }
  }

  val readyMap = Bits(config.issueQueueEntriesPerPort bits)
  for (entry <- 0 until config.issueQueueEntriesPerPort) {
    readyMap(entry) := U(entry, count.getWidth bits) < count &&
      (payloadSlots(order(entry)).source1Ready || wakeupReady1(entry)) &&
      (payloadSlots(order(entry)).source2Ready || wakeupReady2(entry)) &&
      (!payloadSlots(order(entry)).decoded.serializing ||
        payloadSlots(order(entry)).robPointer === io.robHeadPointer)
  }

  val issueIndex = selectLowest(readyMap)
  val issueIndexWide = UInt(count.getWidth bits)
  issueIndexWide := issueIndex.resize(count.getWidth)
  val issueSlot = order(issueIndex)
  io.issueValid := readyMap.orR
  io.issue := payloadSlots(issueSlot)
  val issueFire = io.issueValid && io.issueReady

  // Register the backpressure boundary. Reserve one slot because the ready
  // value describes the previous cycle's count; one enqueue per cycle per IQ
  // cannot overrun the remaining slot.
  val enqueueReadyReg = Reg(Bool()) init (True)
  enqueueReadyReg := count < U(config.issueQueueEntriesPerPort - 1, count.getWidth bits)
  io.enqueueReady := !io.flush && enqueueReadyReg
  val enqueueFire = io.enqueueValid && io.enqueueReady
  io.occupancy := count
  val enqueueSlot = selectLowest(~slotValid.asBits)

  val wakeupSlot1 = Bits(config.issueQueueEntriesPerPort bits)
  val wakeupSlot2 = Bits(config.issueQueueEntriesPerPort bits)
  for (slot <- 0 until config.issueQueueEntriesPerPort) {
    wakeupSlot1(slot) := False
    wakeupSlot2(slot) := False
    for (entry <- 0 until config.issueQueueEntriesPerPort) {
      when(
        U(entry, count.getWidth bits) < count &&
          order(entry) === U(slot, log2Up(config.issueQueueEntriesPerPort) bits) &&
          wakeupReady1(entry)
      ) {
        wakeupSlot1(slot) := True
      }
      when(
        U(entry, count.getWidth bits) < count &&
          order(entry) === U(slot, log2Up(config.issueQueueEntriesPerPort) bits) &&
          wakeupReady2(entry)
      ) {
        wakeupSlot2(slot) := True
      }
    }
  }

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
  enqueued.loadQueueIndex := io.enqueue.loadQueueIndex
  enqueued.storeQueueIndex := io.enqueue.storeQueueIndex

  when(io.flush) {
    count := 0
    for (slot <- 0 until config.issueQueueEntriesPerPort) { slotValid(slot) := False }
  }.otherwise {
    for (slot <- 0 until config.issueQueueEntriesPerPort) {
      val slotEnqueue = enqueueFire &&
        enqueueSlot === U(slot, log2Up(config.issueQueueEntriesPerPort) bits)
      val slotIssue = issueFire &&
        issueSlot === U(slot, log2Up(config.issueQueueEntriesPerPort) bits)
      when(slotEnqueue) {
        slotValid(slot) := True
      }.elsewhen(slotIssue) {
        slotValid(slot) := False
      }

      // Issuing invalidates the narrow slot-valid bit at the clock edge, so
      // payload wakeups in that same cycle are unobservable.  Keep slotIssue
      // out of the wide source-ready update cone to shorten LSU-to-IQ routing.
      when(slotEnqueue) {
        payloadSlots(slot) := enqueued
      }.otherwise {
        when(wakeupSlot1(slot)) { payloadSlots(slot).source1Ready := True }
        when(wakeupSlot2(slot)) { payloadSlots(slot).source2Ready := True }
      }
    }

    when(issueFire) {
      for (entry <- 0 until config.issueQueueEntriesPerPort - 1) {
        when(
          U(entry, count.getWidth bits) >= issueIndexWide &&
            U(entry + 1, count.getWidth bits) < count
        ) {
          order(entry) := order(entry + 1)
        }
      }
      when(enqueueFire) {
        val destination = (count - U(1, count.getWidth bits)).resized
        order(destination(log2Up(config.issueQueueEntriesPerPort) - 1 downto 0)) := enqueueSlot
      }
    }.elsewhen(enqueueFire) {
      order(count(log2Up(config.issueQueueEntriesPerPort) - 1 downto 0)) := enqueueSlot
    }
    count := count + enqueueFire.asUInt - issueFire.asUInt
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
      case OooFuKind.Serial    => uop.decoded.fuType === OooFuType.serial
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
    val flush = in Bool ()
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
    when(!io.flush && laneOpen(lane) && available.orR) {
      choices(lane) := UIntToOh(selectLowest(available), config.executionWidth)
    }
    portUsed(lane + 1) := portUsed(lane) | choices(lane)
    io.inputReady(lane) := !io.flush && laneOpen(lane) && available.orR
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
