package openla500.pipeline

import openla500.observe._
import spinal.core._
import spinal.lib._

/** Flush requests produced by the architectural writeback boundary. */
final case class WritebackFlush() extends Bundle {
  val exception = Bool()
  val ertn = Bool()
  val refetch = Bool()
  val instructionCacheOperation = Bool()
  val idle = Bool()

  def any: Bool = exception || ertn || refetch || instructionCacheOperation || idle
}

/** TLB operations which become visible at writeback. */
final case class WritebackTlbControl() extends Bundle {
  val instructionStall = Bool()
  val search = Bool()
  val searchFound = Bool()
  val searchIndex = UInt(5 bits)
  val fill = Bool()
  val write = Bool()
  val read = Bool()
  val invalidate = Bool()
  val invalidateAsid = Bits(10 bits)
  val invalidateVpn = Bits(19 bits)
  val invalidateOperation = Bits(5 bits)
}

/** LL/SC state updates performed at writeback. */
final case class WritebackReservation() extends Bundle {
  val bitSet = Bool()
  val bitValue = Bool()
  val addressSet = Bool()
  val lineAddress = UInt(28 bits)
}

/** Performance events qualified by normal retirement. */
final case class WritebackPerfEvent() extends Bundle {
  val retired = Bool()
  val branch = Bool()
  val instructionCacheMiss = Bool()
  val dataCacheMiss = Bool()
  val memoryAccess = Bool()
  val predictedBranch = Bool()
  val predictionError = Bool()
}

/** Debug outputs retained by the locked chiplab interface. */
final case class WritebackDebug() extends Bundle {
  val stageValid = Bool()
  val pc = UInt(32 bits)
  val gprWriteMask = Bits(4 bits)
  val gprIndex = UInt(5 bits)
  val gprData = Bits(32 bits)
  val instruction = Bits(32 bits)
}

/** Registered state consumed by the optional legacy DiffTest adapter. */
final case class WritebackObservation() extends Bundle {
  val isCounterInstruction = Bool()
  val timer = Bits(64 bits)
  val loadEvent = Bits(8 bits)
  val memoryPhysicalAddress = UInt(32 bits)
  val memoryVirtualAddress = UInt(32 bits)
  val storeEvent = Bits(8 bits)
  val storeData = Bits(32 bits)
  val csrRstatEvent = Bool()
  val csrData = Bits(32 bits)
}

/** Architectural writeback stage for the locked single-issue pipeline.
  *
  * The input is retained while `debugBreakPoint` applies backpressure. Flush has priority over a
  * simultaneous input transfer. The legacy level outputs intentionally remain asserted while the
  * stage is breakpoint-stalled; the typed CommitEvent is ready-qualified and therefore emits each
  * architectural event once.
  */
final class WritebackStage(emitCommit: Boolean = true, exposeObservation: Boolean = false)
    extends Component {
  val io = new Bundle {
    val input = slave(Stream(MemoryPayload()))
    val debugBreakPoint = in Bool ()
    val tlbFillIndex = in UInt (5 bits)

    val stageValid = out Bool ()
    val realValid = out Bool ()
    val registerWrite = out(GprWrite())
    val csrWrite = out(CsrWrite())
    val flush = out(WritebackFlush())
    val exception = out(ExceptionEvent())
    val tlb = out(WritebackTlbControl())
    val reservation = out(WritebackReservation())
    val perf = out(WritebackPerfEvent())
    val debug = out(WritebackDebug())
    val commit = emitCommit generate master(Flow(CommitEvent()))
    val observation = exposeObservation generate out(WritebackObservation())
  }

  val valid = Reg(Bool()) init (False)
  val payload = Reg(MemoryPayload())
  val readyGo = !io.debugBreakPoint
  io.input.ready := !valid || readyGo

  val realValid = valid && !payload.hasException
  val registerWriteValid = payload.gprWrite && realValid

  io.stageValid := valid
  io.realValid := realValid

  io.registerWrite.valid := registerWriteValid
  io.registerWrite.index := payload.destination
  io.registerWrite.data := payload.finalResult

  io.csrWrite.valid := payload.csrWrite && realValid
  io.csrWrite.address := payload.csrAddress
  io.csrWrite.data := payload.csrResult

  io.flush.exception := payload.hasException && valid
  io.flush.ertn := payload.isErtn && realValid
  io.flush.refetch :=
    (payload.csrWrite || ((payload.isLl || payload.isSc) && !payload.hasException) ||
      payload.refetch) && valid
  io.flush.instructionCacheOperation := payload.instructionCacheOperation && valid
  io.flush.idle := payload.idle && realValid

  io.exception.valid := io.flush.exception
  io.exception.ecode := 0
  io.exception.esubcode := 0
  io.exception.badVAddrValid := False
  io.exception.badVAddr := 0
  io.exception.tlbRefill := False
  io.exception.tlbException := False
  io.exception.tlbVppn := 0

  when(payload.exceptionCode(0)) {
    io.exception.ecode := 0x00
  }.elsewhen(payload.exceptionCode(1)) {
    io.exception.ecode := 0x08
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.pc
  }.elsewhen(payload.exceptionCode(2)) {
    io.exception.ecode := 0x3f
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.pc
    io.exception.tlbRefill := valid
    io.exception.tlbException := valid
    io.exception.tlbVppn := payload.pc(31 downto 13)
  }.elsewhen(payload.exceptionCode(3)) {
    io.exception.ecode := 0x03
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.pc
    io.exception.tlbException := valid
    io.exception.tlbVppn := payload.pc(31 downto 13)
  }.elsewhen(payload.exceptionCode(4)) {
    io.exception.ecode := 0x07
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.pc
    io.exception.tlbException := valid
    io.exception.tlbVppn := payload.pc(31 downto 13)
  }.elsewhen(payload.exceptionCode(5)) {
    io.exception.ecode := 0x0b
  }.elsewhen(payload.exceptionCode(6)) {
    io.exception.ecode := 0x0c
  }.elsewhen(payload.exceptionCode(7)) {
    io.exception.ecode := 0x0d
  }.elsewhen(payload.exceptionCode(8)) {
    io.exception.ecode := 0x0e
  }.elsewhen(payload.exceptionCode(9)) {
    io.exception.ecode := 0x09
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.errorVirtualAddress
  }.elsewhen(payload.exceptionCode(11)) {
    io.exception.ecode := 0x3f
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.errorVirtualAddress
    io.exception.tlbRefill := valid
    io.exception.tlbException := valid
    io.exception.tlbVppn := payload.errorVirtualAddress(31 downto 13)
  }.elsewhen(payload.exceptionCode(12)) {
    io.exception.ecode := 0x04
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.errorVirtualAddress
    io.exception.tlbException := valid
    io.exception.tlbVppn := payload.errorVirtualAddress(31 downto 13)
  }.elsewhen(payload.exceptionCode(13)) {
    io.exception.ecode := 0x07
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.errorVirtualAddress
    io.exception.tlbException := valid
    io.exception.tlbVppn := payload.errorVirtualAddress(31 downto 13)
  }.elsewhen(payload.exceptionCode(14)) {
    io.exception.ecode := 0x02
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.errorVirtualAddress
    io.exception.tlbException := valid
    io.exception.tlbVppn := payload.errorVirtualAddress(31 downto 13)
  }.elsewhen(payload.exceptionCode(15)) {
    io.exception.ecode := 0x01
    io.exception.badVAddrValid := valid
    io.exception.badVAddr := payload.errorVirtualAddress
    io.exception.tlbException := valid
    io.exception.tlbVppn := payload.errorVirtualAddress(31 downto 13)
  }

  io.tlb.instructionStall := (payload.tlbSearch || payload.tlbRead) && valid
  io.tlb.search := payload.tlbSearch && realValid
  io.tlb.searchFound := payload.tlbFound
  io.tlb.searchIndex := payload.tlbIndex
  io.tlb.fill := payload.tlbFill && realValid
  io.tlb.write := payload.tlbWrite && realValid
  io.tlb.read := payload.tlbRead && realValid
  io.tlb.invalidate := payload.invalidateTlb && realValid
  io.tlb.invalidateAsid := payload.invalidateTlbAsid
  io.tlb.invalidateVpn := payload.invalidateTlbVpn
  io.tlb.invalidateOperation := payload.destination.asBits

  io.reservation.bitSet := (payload.isLl || payload.isSc) && realValid
  io.reservation.bitValue := payload.isLl && !payload.dataUncached
  io.reservation.addressSet := payload.isLl && !payload.dataUncached && realValid
  io.reservation.lineAddress := payload.physicalAddress(31 downto 4)

  io.perf.retired := realValid
  io.perf.branch := payload.isBranch && realValid
  io.perf.instructionCacheMiss := payload.instructionCacheMiss && realValid
  io.perf.dataCacheMiss := payload.dataCacheMiss && realValid
  io.perf.memoryAccess := payload.accessesMemory && realValid
  io.perf.predictedBranch := payload.isPredictableBranch && realValid
  io.perf.predictionError := payload.predictionError && realValid

  io.debug.stageValid := valid
  io.debug.pc := payload.pc
  io.debug.gprWriteMask := Mux(registerWriteValid, B"4'xF", B"4'x0")
  io.debug.gprIndex := payload.destination
  io.debug.gprData := payload.finalResult
  io.debug.instruction := payload.instruction

  if (exposeObservation) {
    io.observation.isCounterInstruction := payload.isCounterInstruction
    io.observation.timer := payload.timer
    io.observation.loadEvent := payload.loadEvent
    io.observation.memoryPhysicalAddress := payload.memoryPhysicalAddress
    io.observation.memoryVirtualAddress := payload.memoryVirtualAddress
    io.observation.storeEvent := payload.storeEvent
    io.observation.storeData := payload.storeData
    io.observation.csrRstatEvent := payload.csrRstatEvent
    io.observation.csrData := payload.csrData
  }

  if (emitCommit) {
    val storeByteMask = Bits(4 bits)
    storeByteMask := 0
    when(payload.storeEvent(0)) {
      switch(payload.memoryVirtualAddress(1 downto 0)) {
        is(0) { storeByteMask := B"0001" }
        is(1) { storeByteMask := B"0010" }
        is(2) { storeByteMask := B"0100" }
        default { storeByteMask := B"1000" }
      }
    }.elsewhen(payload.storeEvent(1)) {
      storeByteMask := Mux(payload.memoryVirtualAddress(1), B"1100", B"0011")
    }.elsewhen(payload.storeEvent(2) || payload.storeEvent(3)) {
      storeByteMask := B"1111"
    }

    io.commit.valid := valid && readyGo
    io.commit.payload.pc := payload.pc
    io.commit.payload.instruction := payload.instruction
    io.commit.payload.retired := realValid
    io.commit.payload.ertn := payload.isErtn && realValid
    io.commit.payload.isCounterInstruction := payload.isCounterInstruction
    io.commit.payload.csrRstat := payload.csrRstatEvent
    io.commit.payload.csrReadData := payload.csrData
    io.commit.payload.gprWrite := io.registerWrite
    io.commit.payload.csrWrite := io.csrWrite
    io.commit.payload.exception := io.exception
    io.commit.payload.timer := payload.timer.asUInt
    io.commit.payload.load.instructionMask := payload.loadEvent
    io.commit.payload.load.pAddr := payload.memoryPhysicalAddress
    io.commit.payload.load.vAddr := payload.memoryVirtualAddress
    io.commit.payload.store.instructionMask := payload.storeEvent
    io.commit.payload.store.pAddr := payload.memoryPhysicalAddress
    io.commit.payload.store.vAddr := payload.memoryVirtualAddress
    io.commit.payload.store.data := payload.storeData
    io.commit.payload.store.byteMask := storeByteMask
    io.commit.payload.tlbFill.valid := io.tlb.fill
    io.commit.payload.tlbFill.index := io.tlbFillIndex
  }

  when(io.flush.any) {
    valid := False
  }.elsewhen(io.input.ready) {
    valid := io.input.valid
  }
  when(io.input.fire) {
    payload := io.input.payload
  }
}
