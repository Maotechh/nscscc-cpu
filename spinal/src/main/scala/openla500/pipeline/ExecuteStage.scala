package openla500.pipeline

import openla500.config.CoreConfig
import openla500.execute.OpenLa500Alu
import spinal.core._
import spinal.lib._

/** Forwarding observation produced by EXE. The valid member reports stage occupancy. */
final case class ExecuteForward() extends Bundle {
  val valid = Bool()
  val dependencyNeedsStall = Bool()
  val writeEnabled = Bool()
  val destination = UInt(5 bits)
  val result = Bits(32 bits)
}

/** Level request consumed by the existing OpenLa500Div/OpenLa500Mul integration at top level. */
final case class ExecuteMulDivRequest() extends Bundle {
  val divideEnable = Bool()
  val signed = Bool()
  val operandJ = Bits(32 bits)
  val operandKOrD = Bits(32 bits)
}

/** EXE-to-memory request before address translation and cacheability selection. */
final case class ExecuteMemoryRequest() extends Bundle {
  val valid = Bool()
  val isWrite = Bool()
  val size = Bits(3 bits)
  val byteMask = Bits(4 bits)
  val writeData = Bits(32 bits)
  val virtualAddress = UInt(32 bits)
}

final case class ExecuteCacheControl() extends Bundle {
  val instructionOperationEnable = Bool()
  val dataOperationEnable = Bool()
  val operationMode = Bits(2 bits)
  val preloadEnable = Bool()
  val preloadHint = Bits(5 bits)
}

final case class ExecuteFlush() extends Bundle {
  val exception = Bool()
  val ertn = Bool()
  val refetch = Bool()
  val instructionCacheOperation = Bool()
  val idle = Bool()

  def any: Bool = exception || ertn || refetch || instructionCacheOperation || idle
}

/** LACC boundary retained while the optional accelerator remains outside the stage migration. */
final case class ExecuteLaccInput() extends Bundle {
  val requestReady = Bool()
  val dataValid = Bool()
  val dataRead = Bool()
  val dataAddress = UInt(32 bits)
  val dataWriteData = Bits(32 bits)
  val dataSize = Bits(2 bits)
  val responseValid = Bool()
  val responseData = Bits(32 bits)
  val dataAccepted = Bool()
}

final case class ExecuteLaccOutput() extends Bundle {
  val request = Bool()
  val command = Bits(2 bits)
  val immediate = Bits(7 bits)
  val flush = Bool()
  val dataResponseValid = Bool()
}

/** Typed, one-entry execute stage matching `a158aa8:rtl/exe_stage.v`.
  *
  * The input and output Streams own the historical DS/ES and ES/MS valid/allow contracts. The stage
  * preserves the golden ready-qualified memory request and exposes the legacy top-level divider
  * handshake through ExecuteMulDivRequest. A global flush clears occupancy synchronously;
  * `memoryFlush` suppresses a new memory side effect without clearing this stage register.
  */
final class ExecuteStage(
    config: CoreConfig = CoreConfig.Locked,
    delayedBranchResolutionEnabled: Boolean = false
) extends Component {
  val io = new Bundle {
    val input = slave(Stream(DecodePayload(config)))
    val output = master(Stream(ExecutePayload()))
    val forward = out(ExecuteForward())
    val lateForwardJ = in Bool ()
    val lateForwardKOrD = in Bool ()
    val lateForwardDestination = in UInt (5 bits)
    val memoryForward = in(MemoryForward())
    val mulDiv = out(ExecuteMulDivRequest())
    val divideComplete = in Bool ()
    val flush = in(ExecuteFlush())
    val memoryFlush = in Bool ()
    val memoryWritesTlbEntryHigh = in Bool ()
    val instructionCacheUnbusy = in Bool ()
    val memoryAddressAccepted = in Bool ()
    val csrVirtualPageNumber = in UInt (19 bits)
    val memory = out(ExecuteMemoryRequest())
    val cache = out(ExecuteCacheControl())
    val tlbInstructionStall = out Bool ()
    val dataFetch = out Bool ()
    val delayedBranch = delayedBranchResolutionEnabled generate in(DelayedBranchPrediction())
    val branchRepair = delayedBranchResolutionEnabled generate out(RedirectRequest())
    val btb = delayedBranchResolutionEnabled generate out(DelayedBranchBtbUpdate())
    val laccInput = config.laccEnabled generate in(ExecuteLaccInput())
    val laccOutput = config.laccEnabled generate out(ExecuteLaccOutput())
  }

  val occupied = RegInit(False)
  val payload = Reg(DecodePayload(config))
  val lateForwardJ = Reg(Bool())
  val lateForwardKOrD = Reg(Bool())
  val lateForwardDestination = Reg(UInt(5 bits))
  val delayedBranch =
    delayedBranchResolutionEnabled generate Reg(DelayedBranchPrediction())

  val lateForwardRequested = lateForwardJ || lateForwardKOrD
  val lateForwardMatch =
    io.memoryForward.valid && io.memoryForward.writeEnabled &&
      !io.memoryForward.dependencyNeedsStall &&
      io.memoryForward.destination === lateForwardDestination
  val lateForwardReady =
    !lateForwardRequested || lateForwardMatch
  val effectiveRegisterDataJ =
    Mux(lateForwardJ, io.memoryForward.result, payload.registerDataJ)
  val effectiveRegisterDataKOrD =
    Mux(lateForwardKOrD, io.memoryForward.result, payload.registerDataKOrD)
  val delayedBranchPredictionError = Bool()

  val alu = new OpenLa500Alu
  alu.io.alu_op := payload.aluOperation
  alu.io.alu_src1 := Mux(payload.source1IsPc, payload.pc.asBits, effectiveRegisterDataJ)
  alu.io.alu_src2 := Mux(
    payload.source2IsImmediate,
    payload.immediate,
    Mux(payload.source2IsFour, B(4, 32 bits), effectiveRegisterDataKOrD)
  )

  val laccRequest = Bool()
  val laccResponseValid = Bool()
  val laccDataValid = Bool()
  val laccDataRead = Bool()
  val laccDataAddress = UInt(32 bits)
  val laccDataWriteData = Bits(32 bits)
  val laccDataSize = Bits(2 bits)
  if (config.laccEnabled) {
    laccRequest := payload.laccRequest && occupied && lateForwardReady
    laccResponseValid := io.laccInput.responseValid
    laccDataValid := io.laccInput.dataValid
    laccDataRead := io.laccInput.dataRead
    laccDataAddress := io.laccInput.dataAddress
    laccDataWriteData := io.laccInput.dataWriteData
    laccDataSize := io.laccInput.dataSize
  } else {
    laccRequest := False
    laccResponseValid := False
    laccDataValid := False
    laccDataRead := False
    laccDataAddress := U(0, 32 bits)
    laccDataWriteData := B(0, 32 bits)
    laccDataSize := B(0, 2 bits)
  }

  val executeResult = Bits(32 bits)
  executeResult := Mux(payload.resultFromCsr, payload.csrReadData, alu.io.alu_result)
  if (config.laccEnabled) {
    when(laccRequest) {
      executeResult := io.laccInput.responseData
    }
  }

  val accessMemory = payload.isLoad || payload.isStore
  val addressLow = alu.io.alu_result(1 downto 0)
  val alignmentException =
    accessMemory &&
      ((payload.memorySize(1) && addressLow(0)) ||
        (!payload.memorySize.orR && addressLow.orR))
  val hasException = payload.hasException || alignmentException
  val exceptionCode = alignmentException.asBits ## payload.exceptionCode

  val divideEnable =
    (payload.mulDivOperation(2) || payload.mulDivOperation(3)) && occupied && lateForwardReady
  val multiplyEnable = payload.mulDivOperation(0) || payload.mulDivOperation(1)
  val divideStall = divideEnable && !io.divideComplete

  val sideEffectEnable =
    occupied && lateForwardReady && !hasException && io.output.ready && !io.flush.any &&
      !io.memoryFlush
  val cacheOperation = payload.destination
  val instructionCacheOperation = payload.cacheOperation && cacheOperation(2 downto 0) === 0
  val dataCacheOperation = payload.cacheOperation && cacheOperation(2 downto 0) === 1
  val preloadInstruction =
    payload.preload && (payload.destination === 0 || payload.destination === 8)

  val instructionCacheStall =
    instructionCacheOperation && sideEffectEnable && !io.instructionCacheUnbusy
  val tlbSearchStall = payload.tlbSearch && io.memoryWritesTlbEntryHigh
  val laccStall = laccRequest && !laccResponseValid

  val waitsForAddress = accessMemory || dataCacheOperation || preloadInstruction
  val addressReady = sideEffectEnable && io.memoryAddressAccepted
  val readyGo =
    (lateForwardReady && !divideStall && !laccStall &&
      ((addressReady || !waitsForAddress) && !tlbSearchStall && !instructionCacheStall)) ||
      payload.hasException || (alignmentException && lateForwardReady)

  if (delayedBranchResolutionEnabled) {
    val opcode = payload.instruction(31 downto 26).asUInt
    val isJirl = opcode === U(0x13, 6 bits)
    val isBeq = opcode === U(0x16, 6 bits)
    val isBne = opcode === U(0x17, 6 bits)
    val isBlt = opcode === U(0x18, 6 bits)
    val isBge = opcode === U(0x19, 6 bits)
    val isBltu = opcode === U(0x1a, 6 bits)
    val isBgeu = opcode === U(0x1b, 6 bits)
    val operandsEqual = effectiveRegisterDataJ === effectiveRegisterDataKOrD
    val lessSigned = effectiveRegisterDataJ.asSInt < effectiveRegisterDataKOrD.asSInt
    val lessUnsigned = effectiveRegisterDataJ.asUInt < effectiveRegisterDataKOrD.asUInt
    val branchTaken =
      isJirl || (isBeq && operandsEqual) || (isBne && !operandsEqual) ||
        (isBlt && lessSigned) || (isBge && !lessSigned) ||
        (isBltu && lessUnsigned) || (isBgeu && !lessUnsigned)
    val branchTarget = Mux(
      isJirl,
      effectiveRegisterDataJ.asUInt + payload.immediate.asUInt,
      payload.pc + payload.immediate.asUInt
    )
    val addEntry = !delayedBranch.btbEnabled && branchTaken
    val predictionError =
      delayedBranch.btbEnabled && (delayedBranch.btbTaken ^ branchTaken)
    val targetError =
      delayedBranch.btbEnabled && delayedBranch.btbTaken && branchTaken &&
        delayedBranch.btbTarget =/= branchTarget
    val repair = addEntry || predictionError || targetError
    val resolutionFire =
      io.output.fire && delayedBranch.valid && !payload.hasException && !io.flush.any &&
        !io.memoryFlush

    delayedBranchPredictionError := repair
    io.branchRepair.active := resolutionFire && repair
    io.branchRepair.target := Mux(branchTaken, branchTarget, payload.pc + 4)
    io.btb.enable := resolutionFire
    io.btb.popReturnStack := isJirl
    io.btb.pushReturnStack := False
    io.btb.addEntry := addEntry
    io.btb.predictionError := predictionError
    io.btb.predictionRight :=
      delayedBranch.btbEnabled && !(delayedBranch.btbTaken ^ branchTaken)
    io.btb.targetError := targetError
    io.btb.actualTaken := branchTaken
    io.btb.actualTarget := branchTarget
    io.btb.pc := payload.pc
    io.btb.index := delayedBranch.btbIndex
    io.btb.direction := delayedBranch.direction
  } else {
    delayedBranchPredictionError := False
  }

  io.input.ready := !occupied || (readyGo && io.output.ready)
  io.output.valid := occupied && readyGo

  when(io.flush.any) {
    occupied := False
  }.elsewhen(io.input.ready) {
    occupied := io.input.valid
  }
  when(io.input.valid && io.input.ready) {
    payload := io.input.payload
    lateForwardJ := io.lateForwardJ
    lateForwardKOrD := io.lateForwardKOrD
    lateForwardDestination := io.lateForwardDestination
    if (delayedBranchResolutionEnabled) {
      delayedBranch := io.delayedBranch
    }
  }.elsewhen(occupied && lateForwardMatch) {
    when(lateForwardJ) {
      payload.registerDataJ := io.memoryForward.result
    }
    when(lateForwardKOrD) {
      payload.registerDataKOrD := io.memoryForward.result
    }
    lateForwardJ := False
    lateForwardKOrD := False
  }

  val byteMask = (B(1, 4 bits) |<< addressLow.asUInt).resize(4)
  val halfMask = Bits(4 bits)
  halfMask(0) := addressLow === 0
  halfMask(1) := addressLow === 0
  halfMask(2) := addressLow === 2
  halfMask(3) := addressLow === 2

  val byteSizeTerm = Mux(payload.memorySize(0), byteMask ## B(0, 3 bits), B(0, 7 bits))
  val halfSizeTerm = Mux(payload.memorySize(1), halfMask ## B(1, 3 bits), B(0, 7 bits))
  val wordSizeTerm = Mux(!payload.memorySize.orR, B(0xf, 4 bits) ## B(2, 3 bits), B(0, 7 bits))
  val maskAndSize = byteSizeTerm | halfSizeTerm | wordSizeTerm

  val byteContent = Bits(32 bits)
  for (lane <- 0 until 4) {
    byteContent(lane * 8 + 7 downto lane * 8) :=
      Mux(byteMask(lane), effectiveRegisterDataKOrD(7 downto 0), B(0, 8 bits))
  }
  val halfContent = Bits(32 bits)
  halfContent(15 downto 0) :=
    Mux(halfMask(0), effectiveRegisterDataKOrD(15 downto 0), B(0, 16 bits))
  halfContent(31 downto 16) :=
    Mux(halfMask(3), effectiveRegisterDataKOrD(15 downto 0), B(0, 16 bits))
  val storeData =
    Mux(payload.memorySize(0), byteContent, B(0, 32 bits)) |
      Mux(payload.memorySize(1), halfContent, B(0, 32 bits)) |
      Mux(!payload.memorySize.orR, effectiveRegisterDataKOrD, B(0, 32 bits))

  val laccByteMask = (B(1, 4 bits) |<< laccDataAddress(1 downto 0)).resize(4)
  val laccHalfMask = Bits(4 bits)
  laccHalfMask(0) := !laccDataAddress.orR
  laccHalfMask(1) := !laccDataAddress(1)
  laccHalfMask(2) := laccDataAddress.xorR
  laccHalfMask(3) := laccDataAddress(1)
  val selectedLaccMask = Mux(
    laccDataSize === 0,
    laccByteMask,
    Mux(laccDataSize === 1, laccHalfMask, B(0xf, 4 bits))
  )

  io.memory.valid := (accessMemory && sideEffectEnable) || laccDataValid
  io.memory.isWrite := Mux(
    laccDataValid,
    !laccDataRead,
    payload.isStore && !payload.cacheOperation && !payload.preload
  )
  io.memory.size := Mux(laccDataValid, laccDataSize.resize(3), maskAndSize(2 downto 0))
  io.memory.byteMask := Mux(laccDataValid, selectedLaccMask, maskAndSize(6 downto 3))
  io.memory.writeData := Mux(laccDataValid, laccDataWriteData, storeData)
  io.memory.virtualAddress := Mux(
    laccDataValid,
    laccDataAddress,
    Mux(
      payload.tlbSearch,
      (io.csrVirtualPageNumber.asBits ## B(0, 13 bits)).asUInt,
      alu.io.alu_result.asUInt
    )
  )

  io.cache.instructionOperationEnable := instructionCacheOperation && sideEffectEnable
  io.cache.dataOperationEnable := dataCacheOperation && sideEffectEnable
  io.cache.operationMode := cacheOperation(4 downto 3).asBits
  io.cache.preloadHint := payload.destination.asBits
  io.cache.preloadEnable := preloadInstruction && sideEffectEnable

  io.dataFetch :=
    ((io.memory.valid || dataCacheOperation || io.cache.preloadEnable) &&
      io.memoryAddressAccepted) ||
      ((instructionCacheOperation || payload.tlbSearch) && readyGo && io.output.ready) ||
      laccDataValid

  io.tlbInstructionStall := (payload.tlbSearch || payload.tlbRead) && occupied

  io.mulDiv.divideEnable := divideEnable
  io.mulDiv.signed := payload.mulDivSigned
  io.mulDiv.operandJ := payload.registerDataJ
  io.mulDiv.operandKOrD := payload.registerDataKOrD

  io.forward.valid := occupied
  io.forward.dependencyNeedsStall := payload.isLoad || divideEnable || multiplyEnable
  io.forward.writeEnabled := payload.gprWrite && payload.destination =/= 0 && occupied
  io.forward.destination := payload.destination
  io.forward.result := executeResult

  if (config.laccEnabled) {
    io.laccOutput.request := laccRequest
    io.laccOutput.command := payload.laccCommand
    io.laccOutput.immediate := payload.immediate(11 downto 5)
    io.laccOutput.flush := False
    io.laccOutput.dataResponseValid := laccRequest && io.laccInput.dataAccepted
  }

  val csrMaskResult =
    (effectiveRegisterDataJ & effectiveRegisterDataKOrD) |
      (~effectiveRegisterDataJ & payload.csrReadData)

  io.output.payload.pc := payload.pc
  io.output.payload.executeResult := executeResult
  io.output.payload.destination := payload.destination
  io.output.payload.gprWrite := payload.gprWrite
  io.output.payload.isLoad := payload.isLoad
  io.output.payload.mulDivOperation := payload.mulDivOperation
  io.output.payload.memorySize := payload.memorySize
  io.output.payload.hasException := hasException
  io.output.payload.isErtn := payload.isErtn
  io.output.payload.csrResult :=
    Mux(payload.csrMask, csrMaskResult, effectiveRegisterDataKOrD)
  io.output.payload.csrAddress := payload.csrAddress
  io.output.payload.csrWrite := payload.csrWrite
  io.output.payload.exceptionCode := exceptionCode
  io.output.payload.isLl := payload.isLl
  io.output.payload.isSc := payload.isSc
  io.output.payload.isStore := payload.isStore
  io.output.payload.tlbSearch := payload.tlbSearch
  io.output.payload.tlbWrite := payload.tlbWrite
  io.output.payload.tlbFill := payload.tlbFill
  io.output.payload.refetch := payload.refetch
  io.output.payload.tlbRead := payload.tlbRead
  io.output.payload.invalidateTlb := payload.invalidateTlb
  io.output.payload.invalidateTlbAsid := effectiveRegisterDataJ(9 downto 0)
  io.output.payload.invalidateTlbVpn := effectiveRegisterDataKOrD(31 downto 13)
  io.output.payload.memorySignExtend := payload.memorySignExtend
  io.output.payload.instructionCacheOperation := io.cache.instructionOperationEnable
  io.output.payload.isBranch := payload.isBranch
  io.output.payload.instructionCacheMiss := payload.instructionCacheMiss
  io.output.payload.isPredictableBranch := payload.isPredictableBranch
  if (delayedBranchResolutionEnabled) {
    io.output.payload.predictionError :=
      Mux(delayedBranch.valid, delayedBranchPredictionError, payload.predictionError)
  } else {
    io.output.payload.predictionError := payload.predictionError
  }
  io.output.payload.preload := preloadInstruction
  io.output.payload.cacheOperation := payload.cacheOperation
  io.output.payload.idle := payload.idle
  io.output.payload.errorVirtualAddress := alu.io.alu_result.asUInt
  io.output.payload.instruction := payload.instruction
  io.output.payload.timer := payload.timer
  io.output.payload.isCounterInstruction := payload.isCounterInstruction
  io.output.payload.loadEvent := payload.loadEvent
  io.output.payload.memoryVirtualAddress := io.memory.virtualAddress
  io.output.payload.storeEvent := payload.storeEvent
  io.output.payload.storeData := io.memory.writeData
  io.output.payload.csrRstatEvent := payload.csrRstatEvent
  io.output.payload.csrData := payload.csrReadData
}
