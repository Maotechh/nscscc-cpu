package openla500.pipeline

import spinal.core._
import spinal.lib._

final case class MemoryFlush() extends Bundle {
  val exception = Bool()
  val ertn = Bool()
  val refetch = Bool()
  val instructionCacheOperation = Bool()
  val idle = Bool()
  def any: Bool = exception || ertn || refetch || instructionCacheOperation || idle
}

final case class MemoryForward() extends Bundle {
  val valid = Bool()
  val dependencyNeedsStall = Bool()
  val writeEnabled = Bool()
  val destination = UInt(5 bits)
  val result = Bits(32 bits)
}

/** Typed one-entry memory stage. The legacy adapter owns only port packing and clock polarity. */
final class MemoryStage extends Component {
  val io = new Bundle {
    val input = slave(Stream(ExecutePayload()))
    val output = master(Stream(MemoryPayload()))
    val divResult = in Bits (32 bits)
    val modResult = in Bits (32 bits)
    val mulResult = in Bits (64 bits)
    val flush = in(MemoryFlush())
    val dataDataOk = in Bool ()
    val dcacheMiss = in Bool ()
    val dataReadData = in Bits (32 bits)
    val dataUncached = out Bool ()
    val tlbExceptionCancel = out Bool ()
    val scCancel = out Bool ()
    val csrPage = in Bool ()
    val csrDirectAddress = in Bool ()
    val csrDmw0Plv0 = in Bool ()
    val csrDmw0Plv3 = in Bool ()
    val csrDmw0VirtualSegment = in Bits (3 bits)
    val csrDmw0MemoryAttribute = in Bits (2 bits)
    val csrDmw1Plv0 = in Bool ()
    val csrDmw1Plv3 = in Bool ()
    val csrDmw1VirtualSegment = in Bits (3 bits)
    val csrDmw1MemoryAttribute = in Bits (2 bits)
    val csrPlv = in Bits (2 bits)
    val csrDatm = in Bits (2 bits)
    val disableCache = in Bool ()
    val llAddress = in Bits (28 bits)
    val dataIndexDiff = in Bits (8 bits)
    val dataTagDiff = in Bits (20 bits)
    val dataOffsetDiff = in Bits (4 bits)
    val dataAddressTranslationEnable = out Bool ()
    val dmw0Enable = out Bool ()
    val dmw1Enable = out Bool ()
    val cacopModeDi = out Bool ()
    val dataTlbFound = in Bool ()
    val dataTlbIndex = in UInt (5 bits)
    val dataTlbValid = in Bool ()
    val dataTlbDirty = in Bool ()
    val dataTlbMat = in Bits (2 bits)
    val dataTlbPlv = in Bits (2 bits)
    val dataTlbPpn = in Bits (20 bits)
    val tlbInstructionStall = out Bool ()
    val writeTlbEntryHigh = out Bool ()
    val stageFlush = out Bool ()
    val forward = out(MemoryForward())
  }

  val valid = RegInit(False)
  val payload = Reg(ExecutePayload())
  val dataBuffer = Reg(Bits(32 bits)) init (0)
  val dataBufferEnable = Reg(Bool()) init (False)
  val dataIndex = Reg(Bits(8 bits))
  val dataOffset = Reg(Bits(4 bits))

  val accessMemory = payload.isLoad || payload.isStore
  val pgMode = !io.csrDirectAddress && io.csrPage
  val daMode = io.csrDirectAddress && !io.csrPage
  val cacopMode = payload.destination(4 downto 3)
  io.dmw0Enable := (((io.csrDmw0Plv0 && io.csrPlv === 0) ||
    (io.csrDmw0Plv3 && io.csrPlv === 3)) &&
    payload.errorVirtualAddress(31 downto 29).asBits === io.csrDmw0VirtualSegment && pgMode)
  io.dmw1Enable := (((io.csrDmw1Plv0 && io.csrPlv === 0) ||
    (io.csrDmw1Plv3 && io.csrPlv === 3)) &&
    payload.errorVirtualAddress(31 downto 29).asBits === io.csrDmw1VirtualSegment && pgMode)
  io.cacopModeDi := payload.cacheOperation && (cacopMode === 0 || cacopMode === 1)
  io.dataAddressTranslationEnable := pgMode && !io.dmw0Enable && !io.dmw1Enable && !io.cacopModeDi

  val physicalAddress = Bits(32 bits)
  physicalAddress := io.dataTlbPpn ## payload.errorVirtualAddress(11 downto 0)
  val uncache = (daMode && io.csrDatm === 0) ||
    (io.dmw0Enable && io.csrDmw0MemoryAttribute === 0) ||
    (io.dmw1Enable && io.csrDmw1MemoryAttribute === 0) ||
    (io.dataAddressTranslationEnable && io.dataTlbMat === 0) || io.disableCache
  io.dataUncached := uncache

  val tlbr =
    (accessMemory || payload.cacheOperation) && !io.dataTlbFound && io.dataAddressTranslationEnable
  val pil =
    (payload.isLoad || payload.cacheOperation) && !io.dataTlbValid && io.dataAddressTranslationEnable
  val pis = payload.isStore && !io.dataTlbValid && io.dataAddressTranslationEnable
  val ppi =
    accessMemory && io.dataTlbValid && io.csrPlv.asUInt > io.dataTlbPlv.asUInt && io.dataAddressTranslationEnable
  val pme =
    payload.isStore && io.dataTlbValid && io.csrPlv.asUInt <= io.dataTlbPlv.asUInt && !io.dataTlbDirty && io.dataAddressTranslationEnable
  val exception = tlbr || pil || pis || ppi || pme || payload.hasException
  val exceptionCode = Bits(16 bits)
  exceptionCode := pil.asBits ## pis.asBits ## ppi.asBits ## pme.asBits ## tlbr.asBits ##
    False.asBits ## payload.exceptionCode

  val readData = Mux(dataBufferEnable, dataBuffer, io.dataReadData)
  val byteData = Bits(8 bits)
  byteData := readData(7 downto 0)
  switch(payload.executeResult(1 downto 0)) {
    is(1) { byteData := readData(15 downto 8) }
    is(2) { byteData := readData(23 downto 16) }
    is(3) { byteData := readData(31 downto 24) }
  }
  val halfData = Bits(16 bits)
  halfData := 0
  when(payload.executeResult(1 downto 0) === 0) { halfData := readData(15 downto 0) }
  when(payload.executeResult(1 downto 0) === 2) { halfData := readData(31 downto 16) }
  val loadResult = Bits(32 bits)
  val extendedByte = Mux(
    payload.memorySignExtend,
    byteData.asSInt.resize(32).asBits,
    byteData.resize(32)
  )
  val extendedHalf = Mux(
    payload.memorySignExtend,
    halfData.asSInt.resize(32).asBits,
    halfData.resize(32)
  )
  loadResult := Mux(payload.memorySize(0), extendedByte, B(0, 32 bits)) |
    Mux(payload.memorySize(1), extendedHalf, B(0, 32 bits)) |
    Mux(!payload.memorySize.orR, readData, B(0, 32 bits))

  val scAddressEqual = io.llAddress === physicalAddress(31 downto 4)
  val scCancel = (!scAddressEqual || uncache) && payload.isSc && accessMemory
  io.scCancel := scCancel
  io.tlbExceptionCancel := tlbr || pil || pis || ppi || pme
  val finalResult = Bits(32 bits)
  finalResult := Mux(payload.isLoad, loadResult, B(0, 32 bits)) |
    Mux(payload.mulDivOperation(0), io.mulResult(31 downto 0), B(0, 32 bits)) |
    Mux(payload.mulDivOperation(1), io.mulResult(63 downto 32), B(0, 32 bits)) |
    Mux(payload.mulDivOperation(2), io.divResult, B(0, 32 bits)) |
    Mux(payload.mulDivOperation(3), io.modResult, B(0, 32 bits)) |
    Mux(
      !payload.mulDivOperation.orR && !payload.isLoad && !scCancel,
      payload.executeResult,
      B(0, 32 bits)
    )

  val readyGo = (io.dataDataOk || dataBufferEnable) || !accessMemory || exception || scCancel
  io.input.ready := !valid || (readyGo && io.output.ready)
  io.output.valid := valid && readyGo
  io.output.payload.pc := payload.pc
  io.output.payload.finalResult := finalResult
  io.output.payload.destination := payload.destination
  io.output.payload.gprWrite := payload.gprWrite
  io.output.payload.hasException := exception
  io.output.payload.isErtn := payload.isErtn
  io.output.payload.csrResult := payload.csrResult
  io.output.payload.csrAddress := payload.csrAddress
  io.output.payload.csrWrite := payload.csrWrite
  io.output.payload.exceptionCode := exceptionCode
  io.output.payload.isLl := payload.isLl
  io.output.payload.isSc := payload.isSc
  io.output.payload.errorVirtualAddress := payload.errorVirtualAddress
  io.output.payload.tlbSearch := payload.tlbSearch
  io.output.payload.tlbFound := io.dataTlbFound
  io.output.payload.tlbIndex := io.dataTlbIndex
  io.output.payload.tlbWrite := payload.tlbWrite
  io.output.payload.tlbFill := payload.tlbFill
  io.output.payload.refetch := payload.refetch
  io.output.payload.tlbRead := payload.tlbRead
  io.output.payload.invalidateTlb := payload.invalidateTlb
  io.output.payload.invalidateTlbAsid := payload.invalidateTlbAsid
  io.output.payload.invalidateTlbVpn := payload.invalidateTlbVpn
  io.output.payload.instructionCacheOperation := payload.instructionCacheOperation
  io.output.payload.isBranch := payload.isBranch
  io.output.payload.instructionCacheMiss := payload.instructionCacheMiss
  io.output.payload.accessesMemory := accessMemory
  io.output.payload.dataCacheMiss := io.dcacheMiss
  io.output.payload.isPredictableBranch := payload.isPredictableBranch
  io.output.payload.predictionError := payload.predictionError
  io.output.payload.idle := payload.idle
  io.output.payload.physicalAddress := physicalAddress.asUInt
  io.output.payload.dataUncached := uncache
  io.output.payload.instruction := payload.instruction
  io.output.payload.timer := payload.timer
  io.output.payload.isCounterInstruction := payload.isCounterInstruction
  io.output.payload.loadEvent := payload.loadEvent
  io.output.payload.memoryPhysicalAddress := (io.dataTagDiff ## dataIndex ## dataOffset).asUInt
  io.output.payload.memoryVirtualAddress := payload.memoryVirtualAddress
  io.output.payload.storeEvent := payload.storeEvent
  io.output.payload.storeData := payload.storeData
  io.output.payload.csrRstatEvent := payload.csrRstatEvent
  io.output.payload.csrData := payload.csrData

  io.forward.valid := valid
  io.forward.dependencyNeedsStall := payload.isLoad && !io.output.valid
  io.forward.writeEnabled := payload.gprWrite && payload.destination =/= 0 && valid
  io.forward.destination := payload.destination
  io.forward.result := finalResult
  io.tlbInstructionStall := (payload.tlbSearch || payload.tlbRead) && valid
  io.writeTlbEntryHigh := payload.csrWrite && payload.csrAddress === 0x11 && valid
  io.stageFlush := (exception || payload.isErtn || payload.csrWrite ||
    ((payload.isLl || payload.isSc) && !exception) || payload.refetch || payload.idle) && valid

  when(io.flush.any || (readyGo && io.output.ready)) {
    valid := False
    dataBufferEnable := False
    dataBuffer := 0
  } elsewhen (io.dataDataOk && !io.output.ready) {
    dataBuffer := io.dataReadData
    dataBufferEnable := True
  }
  when(io.input.fire) {
    valid := True
    payload := io.input.payload
  }
  when(io.flush.any) { valid := False }
  dataIndex := io.dataIndexDiff
  dataOffset := io.dataOffsetDiff
}
