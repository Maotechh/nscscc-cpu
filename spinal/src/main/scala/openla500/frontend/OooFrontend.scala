package openla500.frontend

import openla500.backend._
import openla500.core._
import openla500.memory._
import openla500.privileged._
import spinal.core._
import spinal.lib._

final case class OooFrontendSlot(config: OooCoreConfig) extends Bundle {
  val pc = UInt(config.xlen bits)
  val instruction = Bits(32 bits)
  val exception = OooExceptionMeta()
  val predictedTaken = Bool()
  val predictedTarget = UInt(config.xlen bits)
}

/** Four-slot fetch frontend with an eight-entry fetch-to-decode buffer.
  *
  * The cache returns one aligned 16-byte group. Slots preceding an unaligned redirect target are
  * discarded, and the remaining stream is compacted into the fixed three-wide decoder. Translated
  * memory attributes are carried to the hierarchy so uncached fetches bypass every cache level.
  */
final class OooFrontend(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private def opcode(instruction: Bits): UInt = instruction(31 downto 26).asUInt

  private def isDirectUnconditionalBranch(instruction: Bits): Bool = {
    val op = opcode(instruction)
    op === U(0x14, 6 bits) || op === U(0x15, 6 bits)
  }

  private def isConditionalBranch(instruction: Bits): Bool = {
    val op = opcode(instruction)
    op >= U(0x16, 6 bits) && op <= U(0x1b, 6 bits)
  }

  // BTFNT is deliberately stateless: it removes the common loop back-edge penalty without
  // adding a predictor table or a new recovery protocol to this first OoO frontend.
  private def staticallyPredictedTaken(instruction: Bits): Bool =
    isDirectUnconditionalBranch(instruction) ||
      (isConditionalBranch(instruction) && instruction(25))

  private def staticDirectTarget(pc: UInt, instruction: Bits): UInt = {
    val directOffset =
      (instruction(9 downto 0) ## instruction(25 downto 10) ## B(0, 2 bits))
        .asSInt
        .resize(config.xlen)
        .asUInt
    val conditionalOffset =
      (instruction(25 downto 10) ## B(0, 2 bits))
        .asSInt
        .resize(config.xlen)
        .asUInt
    pc + Mux(isDirectUnconditionalBranch(instruction), directOffset, conditionalOffset)
  }

  private val pointerWidth = log2Up(config.instructionBufferEntries)
  private val countWidth = log2Up(config.instructionBufferEntries + 1)
  private val enqueueCountWidth = log2Up(config.fetchWidth + 1)
  private val fetchGroupBytes = config.fetchWidth * 4
  private val fetchGroupOffsetWidth = log2Up(fetchGroupBytes)
  private val predictorEntries = 32
  private val predictorIndexWidth = log2Up(predictorEntries)
  private val predictorTagWidth = config.xlen - predictorIndexWidth - 2

  require(fetchGroupBytes == 16)

  val io = new Bundle {
    val translationRequest = master(Stream(OooTranslationRequest(config)))
    val translationResponse = slave(Stream(OooTranslationResponse(config)))

    val cacheRequestValid = out Bool ()
    val cacheRequest = out(OooInstructionCacheRequest(config))
    val cacheRequestReady = in Bool ()
    val cacheResponseValid = in Bool ()
    val cacheResponse = in(OooInstructionCacheResponse(config))
    val cacheKill = out Bool ()

    val decodeValid = out Bits (config.decodeWidth bits)
    val decoded = out Vec (OooDecodedUop(config), config.decodeWidth)
    val decodeReady = in Bits (config.decodeWidth bits)

    val redirectValid = in Bool ()
    val redirectTarget = in UInt (config.xlen bits)
    val predictorUpdateValid = in Bool ()
    val predictorUpdatePc = in UInt (config.xlen bits)
    val predictorUpdateTaken = in Bool ()
    val predictorUpdateTarget = in UInt (config.xlen bits)
    val privilege = in Bits (2 bits)
    val interruptPending = in Bool ()

    val fetchPc = out UInt (config.xlen bits)
    val occupancy = out UInt (countWidth bits)
  }

  val entries = Vec.fill(config.instructionBufferEntries)(Reg(OooFrontendSlot(config)))
  val head = Reg(UInt(pointerWidth bits)) init (0)
  val tail = Reg(UInt(pointerWidth bits)) init (0)
  val count = Reg(UInt(countWidth bits)) init (0)
  val nextFetchPc = Reg(UInt(config.xlen bits)) init (U(config.resetVector, config.xlen bits))
  val translationOutstanding = RegInit(False)
  val translationDropPending = RegInit(False)
  val translatedRequestValid = RegInit(False)
  val translatedPhysicalAddress = Reg(UInt(config.xlen bits))
  val translatedUncached = Reg(Bool())
  val cacheOutstanding = RegInit(False)
  val outstandingPc = Reg(UInt(config.xlen bits)) init (U(config.resetVector, config.xlen bits))
  // A compact recovery-trained table handles JIRL and branches that disagree with BTFNT.
  // It is intentionally updated only by a precise ROB recovery, so squashed speculation cannot
  // corrupt the architectural prediction history.
  val predictorValid = Vec.fill(predictorEntries)(RegInit(False))
  val predictorTaken = Vec.fill(predictorEntries)(Reg(Bool()) init (False))
  val predictorTag = Vec.fill(predictorEntries)(Reg(Bits(predictorTagWidth bits)) init (0))
  val predictorTarget = Vec.fill(predictorEntries)(Reg(UInt(config.xlen bits)) init (0))
  when(io.predictorUpdateValid) {
    val updateIndex = io.predictorUpdatePc(predictorIndexWidth + 1 downto 2)
    predictorValid(updateIndex) := True
    predictorTaken(updateIndex) := io.predictorUpdateTaken
    predictorTag(updateIndex) :=
      io.predictorUpdatePc(config.xlen - 1 downto predictorIndexWidth + 2).asBits
    predictorTarget(updateIndex) := io.predictorUpdateTarget
  }

  val freeSlots = U(config.instructionBufferEntries, countWidth bits) - count
  io.translationRequest.valid := !translationOutstanding && !translationDropPending &&
    !translatedRequestValid && !cacheOutstanding && !io.redirectValid &&
    freeSlots >= config.fetchWidth
  io.translationRequest.virtualAddress := nextFetchPc
  io.translationRequest.isWrite := False
  val translationRequestFire = io.translationRequest.valid && io.translationRequest.ready
  io.translationResponse.ready := !translatedRequestValid &&
    (translationOutstanding || translationDropPending)
  val translationResponseFire = io.translationResponse.valid && io.translationResponse.ready
  // A delayed response must belong to the request currently held by the frontend.  This
  // protects the virtual-PC tag from being paired with a physical address from a stale request
  // after a redirect or a translator response race.
  val translationResponseMatches =
    io.translationResponse.virtualAddress === outstandingPc
  val translationResponseUseful = translationResponseFire && translationOutstanding &&
    !io.redirectValid && translationResponseMatches
  val translationExceptionFire = translationResponseUseful &&
    io.translationResponse.exception.valid

  io.cacheRequestValid := translatedRequestValid && !io.redirectValid
  io.cacheRequest.virtualAddress := outstandingPc
  io.cacheRequest.physicalAddress := translatedPhysicalAddress
  io.cacheRequest.uncached := translatedUncached
  val requestFire = io.cacheRequestValid && io.cacheRequestReady
  io.cacheKill := io.redirectValid && cacheOutstanding

  // Cached requests can be killed at the L1 boundary, but an already accepted uncached AXI burst
  // still completes.  Do not let that stale response satisfy a newer request after redirect.
  val cacheResponseMatches = io.cacheResponse.virtualAddress === outstandingPc
  val responseFire = io.cacheResponseValid && cacheOutstanding && !io.redirectValid &&
    cacheResponseMatches
  val groupBase = outstandingPc &
    U(((BigInt(1) << config.xlen) - 1) ^ (fetchGroupBytes - 1), config.xlen bits)
  val firstSlot = outstandingPc(fetchGroupOffsetWidth - 1 downto 2)
  val responseSlotValid = Vec(Bool(), config.fetchWidth)
  val responsePredictionTaken = Vec(Bool(), config.fetchWidth)
  val earlierResponsePredictionTaken = Vec(Bool(), config.fetchWidth + 1)
  val responsePredictionTarget = Vec(UInt(config.xlen bits), config.fetchWidth)
  val responsePrefix = Vec(UInt(enqueueCountWidth bits), config.fetchWidth + 1)
  earlierResponsePredictionTaken(0) := False
  responsePrefix(0) := 0
  for (lane <- 0 until config.fetchWidth) {
    val lanePc = groupBase + U(lane * 4, config.xlen bits)
    val laneIndex = lanePc(predictorIndexWidth + 1 downto 2)
    val laneTag = lanePc(config.xlen - 1 downto predictorIndexWidth + 2).asBits
    val dynamicPredictionHit = predictorValid(laneIndex) && predictorTag(laneIndex) === laneTag
    val lanePredictionTaken = Mux(
      dynamicPredictionHit,
      predictorTaken(laneIndex),
      staticallyPredictedTaken(io.cacheResponse.instructions(lane))
    )
    responseSlotValid(lane) := responseFire &&
      U(lane, config.fetchSlotWidth bits) >= firstSlot &&
      !earlierResponsePredictionTaken(lane)
    responsePredictionTaken(lane) := responseSlotValid(lane) &&
      !io.cacheResponse.error && lanePredictionTaken
    earlierResponsePredictionTaken(lane + 1) :=
      earlierResponsePredictionTaken(lane) || responsePredictionTaken(lane)
    responsePredictionTarget(lane) := Mux(
      dynamicPredictionHit,
      predictorTarget(laneIndex),
      staticDirectTarget(lanePc, io.cacheResponse.instructions(lane))
    )
    responsePrefix(lane + 1) := responsePrefix(lane) + responseSlotValid(lane).asUInt
  }
  val enqueueCount = responsePrefix(config.fetchWidth)

  val decodeInputValid = Bits(config.fetchWidth bits)
  val decodePc = Vec(UInt(config.xlen bits), config.fetchWidth)
  val decodeInstruction = Vec(Bits(32 bits), config.fetchWidth)
  val decodeException = Vec(OooExceptionMeta(), config.fetchWidth)
  for (lane <- 0 until config.fetchWidth) {
    if (lane < config.decodeWidth) {
      val source = (head + U(lane, pointerWidth bits)).resized
      decodeInputValid(lane) := count > U(lane, countWidth bits)
      decodePc(lane) := entries(source).pc
      decodeInstruction(lane) := entries(source).instruction
      decodeException(lane) := entries(source).exception
    } else {
      decodeInputValid(lane) := False
      decodePc(lane) := 0
      decodeInstruction(lane) := 0
      decodeException(lane).valid := False
      decodeException(lane).ecode := 0
      decodeException(lane).esubcode := 0
      decodeException(lane).badVAddrValid := False
      decodeException(lane).badVAddr := 0
      decodeException(lane).tlbRefill := False
    }
  }

  val wideDecode = new OooWideDecode(config)
  wideDecode.io.inputValid := decodeInputValid
  wideDecode.io.pc := decodePc
  wideDecode.io.instruction := decodeInstruction
  wideDecode.io.predictedTaken := 0
  for (lane <- 0 until config.fetchWidth) {
    val decodeSource = (head + U(lane, pointerWidth bits)).resized
    val decodePredictionTaken = decodeInputValid(lane) && !decodeException(lane).valid &&
      entries(decodeSource).predictedTaken
    wideDecode.io.predictedTaken(lane) := decodePredictionTaken
    wideDecode.io.predictedTarget(lane) := Mux(
      decodePredictionTaken,
      entries(decodeSource).predictedTarget,
      decodePc(lane) + 4
    )
    wideDecode.io.predictorMetadata(lane) := 0
    wideDecode.io.fetchException(lane) := decodeException(lane)
  }
  wideDecode.io.privilege := io.privilege
  wideDecode.io.interruptPending := io.interruptPending
  io.decodeValid := wideDecode.io.outputValid
  io.decoded := wideDecode.io.decoded

  val dequeueFire = Bits(config.decodeWidth bits)
  val dequeueAccepted = Vec(Bool(), config.decodeWidth + 1)
  dequeueAccepted(0) := True
  for (lane <- 0 until config.decodeWidth) {
    dequeueAccepted(lane + 1) :=
      dequeueAccepted(lane) && io.decodeValid(lane) && io.decodeReady(lane)
    dequeueFire(lane) := dequeueAccepted(lane + 1)
  }
  val dequeueCount = CountOne(dequeueFire)

  when(io.redirectValid) {
    head := 0
    tail := 0
    count := 0
    nextFetchPc := io.redirectTarget
    translationOutstanding := False
    translationDropPending :=
      (translationOutstanding || translationDropPending) && !translationResponseFire
    translatedRequestValid := False
    cacheOutstanding := False
  }.otherwise {
    when(translationRequestFire) {
      translationOutstanding := True
      outstandingPc := nextFetchPc
    }
    when(translationResponseFire) {
      when(translationDropPending) {
        translationDropPending := False
      }.elsewhen(translationOutstanding) {
        translationOutstanding := False
        when(translationResponseMatches && !io.translationResponse.exception.valid) {
          translatedRequestValid := True
          translatedPhysicalAddress := io.translationResponse.physicalAddress
          translatedUncached := io.translationResponse.uncached
        }
      }
    }
    when(requestFire) {
      translatedRequestValid := False
      cacheOutstanding := True
    }
    when(responseFire) {
      cacheOutstanding := False
      nextFetchPc := groupBase + fetchGroupBytes
      when(earlierResponsePredictionTaken(config.fetchWidth)) {
        when(responsePredictionTaken(0)) {
          nextFetchPc := responsePredictionTarget(0)
        }.otherwise {
          for (lane <- 1 until config.fetchWidth) {
            when(responsePredictionTaken(lane)) {
              nextFetchPc := responsePredictionTarget(lane)
            }
          }
        }
      }
      for (lane <- 0 until config.fetchWidth) {
        when(responseSlotValid(lane)) {
          val destination = (tail + responsePrefix(lane)).resized
          entries(destination).pc := groupBase + lane * 4
          entries(destination).instruction := io.cacheResponse.instructions(lane)
          entries(destination).exception.valid := io.cacheResponse.error
          entries(destination).exception.ecode := U(8, 6 bits)
          entries(destination).exception.esubcode := U(0, 9 bits)
          entries(destination).exception.badVAddrValid := io.cacheResponse.error
          entries(destination).exception.badVAddr := groupBase + lane * 4
          entries(destination).exception.tlbRefill := False
          entries(destination).predictedTaken := responsePredictionTaken(lane)
          entries(destination).predictedTarget := responsePredictionTarget(lane)
        }
      }
      tail := tail + enqueueCount
    }
    when(translationExceptionFire) {
      entries(tail).pc := outstandingPc
      entries(tail).instruction := B(0, 32 bits)
      entries(tail).exception := io.translationResponse.exception
      entries(tail).predictedTaken := False
      entries(tail).predictedTarget := outstandingPc + 4
      tail := tail + 1
      nextFetchPc := outstandingPc + 4
    }
    head := head + dequeueCount
    val acceptedCount = Mux(
      responseFire,
      enqueueCount,
      Mux(translationExceptionFire, U(1, enqueueCountWidth bits), U(0, enqueueCountWidth bits))
    )
    count := count + acceptedCount - dequeueCount
  }

  io.fetchPc := nextFetchPc
  io.occupancy := count
}
