package openla500.frontend

import openla500.backend._
import openla500.core._
import openla500.memory._
import openla500.predict._
import openla500.privileged._
import spinal.core._
import spinal.lib._

final case class OooFrontendSlot(config: OooCoreConfig) extends Bundle {
  val pc = UInt(config.xlen bits)
  val instruction = Bits(32 bits)
  val exception = OooExceptionMeta()
  val predictedTaken = Bool()
  val predictedTarget = UInt(config.xlen bits)
  val predictorMetadata = Bits(16 bits)
}

/** Four-slot fetch frontend with an eight-entry fetch-to-decode buffer.
  *
  * The cache returns one aligned 16-byte group. Slots preceding an unaligned redirect target are
  * discarded, and the remaining stream is compacted into the fixed three-wide decoder. Translated
  * memory attributes are carried to the hierarchy so uncached fetches bypass every cache level.
  */
final class OooFrontend(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private val pointerWidth = log2Up(config.instructionBufferEntries)
  private val countWidth = log2Up(config.instructionBufferEntries + 1)
  private val enqueueCountWidth = log2Up(config.fetchWidth + 1)
  private val fetchGroupBytes = config.fetchWidth * 4
  private val fetchGroupOffsetWidth = log2Up(fetchGroupBytes)
  require(fetchGroupBytes == 16)

  val io = new Bundle {
    val translationRequest = master(Stream(OooTranslationRequest(config)))
    val translationResponse = slave(Stream(OooTranslationResponse(config)))

    val cacheRequestValid = out Bool ()
    val cacheUncachedRequestValid = out Bool ()
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
    val predictorUpdateType = in UInt (OooPredictedBranchType.Width bits)
    val predictorUpdateMetadata = in Bits (16 bits)
    val predictorUpdateIsCall = in Bool ()
    val predictorUpdateIsReturn = in Bool ()
    val privilege = in Bits (2 bits)
    val interruptPending = in Bool ()

    val fetchPc = out UInt (config.xlen bits)
    val occupancy = out UInt (countWidth bits)
    val predictorDebugTaken = out Bool ()
    val predictorDebugHit = out Bool ()
    val predictorDebugType = out UInt (OooPredictedBranchType.Width bits)
    val predictorDebugPhtState = out UInt (2 bits)
  }

  val entries = Vec.fill(config.instructionBufferEntries)(Reg(OooFrontendSlot(config)))
  for (entry <- entries) {
    entry.pc.addAttribute("extract_reset", "no")
    entry.instruction.addAttribute("extract_reset", "no")
    entry.exception.valid.addAttribute("extract_reset", "no")
    entry.exception.ecode.addAttribute("extract_reset", "no")
    entry.exception.esubcode.addAttribute("extract_reset", "no")
    entry.exception.badVAddrValid.addAttribute("extract_reset", "no")
    entry.exception.badVAddr.addAttribute("extract_reset", "no")
    entry.exception.tlbRefill.addAttribute("extract_reset", "no")
    entry.predictedTaken.addAttribute("extract_reset", "no")
    entry.predictedTarget.addAttribute("extract_reset", "no")
    entry.predictorMetadata.addAttribute("extract_reset", "no")
  }
  val head = Reg(UInt(pointerWidth bits)) init (0)
  val tail = Reg(UInt(pointerWidth bits)) init (0)
  val count = Reg(UInt(countWidth bits)) init (0)
  val nextFetchPc = Reg(UInt(config.xlen bits)) init (U(config.resetVector, config.xlen bits))
  val translationOutstanding = RegInit(False)
  val translationDropPending = RegInit(False)
  val translatedRequestValid = RegInit(False)
  val translatedPhysicalAddress = Reg(UInt(config.xlen bits))
  val translatedUncached = Reg(Bool())
  val translatedExceptionValid = RegInit(False)
  val translatedException = Reg(OooExceptionMeta())
  val cacheOutstanding = RegInit(False)
  val cacheDropPending = RegInit(False)
  val predictionCorrectionFlushPending = RegInit(False)
  val translationPc = Reg(UInt(config.xlen bits)) init (U(config.resetVector, config.xlen bits))
  val cachePc = Reg(UInt(config.xlen bits)) init (U(config.resetVector, config.xlen bits))
  val predictionPendingValid = RegInit(False)
  val pendingPrediction = Vec.fill(config.fetchWidth)(Reg(OooBankedFetchPrediction(config)))
  val translatedPrediction = Vec.fill(config.fetchWidth)(Reg(OooBankedFetchPrediction(config)))
  val cachePrediction = Vec.fill(config.fetchWidth)(Reg(OooBankedFetchPrediction(config)))
  for (lane <- 0 until config.fetchWidth) {
    pendingPrediction(lane).hit.init(False)
    pendingPrediction(lane).phtValid.init(False)
    pendingPrediction(lane).branchType.init(OooPredictedBranchType.conditional)
    pendingPrediction(lane).phtState.init(1)
    pendingPrediction(lane).phtIndex.init(0)
    pendingPrediction(lane).target.init(0)
    translatedPrediction(lane).hit.init(False)
    translatedPrediction(lane).phtValid.init(False)
    translatedPrediction(lane).branchType.init(OooPredictedBranchType.conditional)
    translatedPrediction(lane).phtState.init(1)
    translatedPrediction(lane).phtIndex.init(0)
    translatedPrediction(lane).target.init(0)
    cachePrediction(lane).hit.init(False)
    cachePrediction(lane).phtValid.init(False)
    cachePrediction(lane).branchType.init(OooPredictedBranchType.conditional)
    cachePrediction(lane).phtState.init(1)
    cachePrediction(lane).phtIndex.init(0)
    cachePrediction(lane).target.init(0)
  }
  val cachePredictedTaken = RegInit(False)
  val cachePredictedLane = Reg(UInt(config.fetchSlotWidth bits)) init (0)
  val cachePredictedTarget =
    Reg(UInt(config.xlen bits)) init (U(config.resetVector, config.xlen bits))
  io.predictorDebugTaken := cachePredictedTaken
  io.predictorDebugHit := cachePrediction(0).hit
  io.predictorDebugType := cachePrediction(0).branchType
  io.predictorDebugPhtState := cachePrediction(0).phtState

  val targetPredictor = new OooBankedFetchPredictor(config)
  val targetPredictorLookupPc = UInt(config.xlen bits)
  targetPredictor.io.lookupPc := targetPredictorLookupPc

  val predictionForTranslation = Vec(OooBankedFetchPrediction(config), config.fetchWidth)
  for (lane <- 0 until config.fetchWidth) {
    predictionForTranslation(lane) := pendingPrediction(lane)
    when(!predictionPendingValid) {
      predictionForTranslation(lane).hit := False
      predictionForTranslation(lane).phtValid := False
      predictionForTranslation(lane).branchType := OooPredictedBranchType.conditional
      predictionForTranslation(lane).phtState := 1
      predictionForTranslation(lane).phtIndex := 0
      predictionForTranslation(lane).target := 0
    }
    when(targetPredictor.io.responseValid) {
      predictionForTranslation(lane) := targetPredictor.io.prediction(lane)
    }
  }

  io.translationResponse.ready := !translatedRequestValid && !translatedExceptionValid &&
    (translationOutstanding || translationDropPending)
  val translationResponseFire = io.translationResponse.valid && io.translationResponse.ready
  // A delayed response must belong to the request currently held by the frontend.  This
  // protects the virtual-PC tag from being paired with a physical address from a stale request
  // after a redirect or a translator response race.
  val translationResponseMatches =
    io.translationResponse.virtualAddress === translationPc
  val translationResponseBypassValid = if (config.enableFrontendTranslationResponseBypass) {
    translationResponseFire && translationOutstanding && translationResponseMatches &&
      !io.translationResponse.cancelled && !io.translationResponse.exception.valid &&
      !io.redirectValid
  } else {
    False
  }
  val requestTranslationPc = Mux(
    translationResponseBypassValid,
    io.translationResponse.virtualAddress,
    translationPc
  )
  val requestPrediction = Vec(OooBankedFetchPrediction(config), config.fetchWidth)
  for (lane <- 0 until config.fetchWidth) {
    requestPrediction(lane) := translatedPrediction(lane)
    when(translationResponseBypassValid) {
      requestPrediction(lane) := predictionForTranslation(lane)
    }
  }

  val translatedGroupBase = requestTranslationPc &
    U(((BigInt(1) << config.xlen) - 1) ^ (fetchGroupBytes - 1), config.xlen bits)
  val translatedFirstSlot = requestTranslationPc(fetchGroupOffsetWidth - 1 downto 2)
  val translatedPredictionTaken = Vec(Bool(), config.fetchWidth)
  val translatedConditionalSeen = Vec(Bool(), config.fetchWidth)
  val earlierTranslatedPredictionTaken = Vec(Bool(), config.fetchWidth + 1)
  earlierTranslatedPredictionTaken(0) := False
  for (lane <- 0 until config.fetchWidth) {
    val lanePc = translatedGroupBase + U(lane * 4, config.xlen bits)
    val coldConditionalTaken = requestPrediction(lane).target < lanePc
    val laneTaken = requestPrediction(lane).branchType =/=
      OooPredictedBranchType.conditional || Mux(
        requestPrediction(lane).phtValid,
        requestPrediction(lane).phtState(1),
        coldConditionalTaken
      )
    translatedPredictionTaken(lane) := requestPrediction(lane).hit &&
      laneTaken &&
      U(lane, config.fetchSlotWidth bits) >= translatedFirstSlot &&
      !earlierTranslatedPredictionTaken(lane)
    translatedConditionalSeen(lane) := requestPrediction(lane).hit &&
      requestPrediction(lane).branchType === OooPredictedBranchType.conditional &&
      U(lane, config.fetchSlotWidth bits) >= translatedFirstSlot &&
      !earlierTranslatedPredictionTaken(lane)
    earlierTranslatedPredictionTaken(lane + 1) :=
      earlierTranslatedPredictionTaken(lane) || translatedPredictionTaken(lane)
  }
  val requestPredictedTaken = earlierTranslatedPredictionTaken(config.fetchWidth)
  val requestPredictedPc = UInt(config.xlen bits)
  val requestPredictedTarget = UInt(config.xlen bits)
  val requestPredictedType = UInt(OooPredictedBranchType.Width bits)
  requestPredictedPc := translatedGroupBase
  requestPredictedTarget := translatedGroupBase + fetchGroupBytes
  requestPredictedType := OooPredictedBranchType.conditional
  for (lane <- (0 until config.fetchWidth).reverse) {
    when(translatedPredictionTaken(lane)) {
      requestPredictedPc := translatedGroupBase + lane * 4
      requestPredictedTarget := requestPrediction(lane).target
      requestPredictedType := requestPrediction(lane).branchType
    }
  }
  val requestHistoryValid = translatedConditionalSeen.asBits.orR

  // A straight-line or non-RAS direct transfer does not change speculative GHR/RAS state.  Such
  // a group can launch the next translation while its own response is bypassed to L1I.  Branches
  // that would update history remain on the registered path so the next lookup observes the same
  // predictor state as the non-turnover implementation.
  val requestPredictedNextPc = UInt(config.xlen bits)
  requestPredictedNextPc := Mux(
    requestPredictedTaken,
    requestPredictedTarget,
    translatedGroupBase + fetchGroupBytes
  )
  val translationTurnoverEligible = if (config.enableFrontendTranslationTurnover) {
    translationResponseBypassValid && !requestHistoryValid &&
      requestPredictedType =/= OooPredictedBranchType.call &&
      requestPredictedType =/= OooPredictedBranchType.ret
  } else {
    False
  }

  val freeSlots = U(config.instructionBufferEntries, countWidth bits) - count
  val translationExceptionFire = translationResponseFire && translationOutstanding &&
    !io.redirectValid && translationResponseMatches && !io.translationResponse.cancelled &&
    io.translationResponse.exception.valid
  val predictionCorrectionOnResponse = Bool()
  val cacheRequestCapacityAvailable = Bool()
  // Cached requests can be killed at the L1 boundary, but an already accepted uncached AXI burst
  // still completes.  Do not let that stale response satisfy a newer request after redirect.
  val cacheResponseMatches = io.cacheResponse.virtualAddress === cachePc
  val responseFire = io.cacheResponseValid && cacheOutstanding && !cacheDropPending &&
    !io.redirectValid && cacheResponseMatches
  val droppedResponseFire = io.cacheResponseValid && cacheOutstanding && cacheDropPending &&
    !io.redirectValid && cacheResponseMatches

  val cacheRequestBaseValid = (translatedRequestValid || translationResponseBypassValid) &&
    (!cacheOutstanding || responseFire || droppedResponseFire) && !io.redirectValid &&
    cacheRequestCapacityAvailable
  val requestUncached = Mux(
    translationResponseBypassValid,
    io.translationResponse.uncached,
    translatedUncached
  )
  io.cacheRequestValid := cacheRequestBaseValid && !requestUncached
  io.cacheUncachedRequestValid := cacheRequestBaseValid && requestUncached
  io.cacheRequest.virtualAddress := requestTranslationPc
  io.cacheRequest.physicalAddress := Mux(
    translationResponseBypassValid,
    io.translationResponse.physicalAddress,
    translatedPhysicalAddress
  )
  io.cacheRequest.uncached := requestUncached
  val cachedRequestFire = io.cacheRequestValid && io.cacheRequestReady
  val uncachedRequestFire = io.cacheUncachedRequestValid && io.cacheRequestReady
  val requestFire = cachedRequestFire || uncachedRequestFire
  // The next translation may replace the current owner only when the translated group actually
  // enters L1I on this edge.  Merely buffering the old translation response would otherwise
  // overwrite the single translation context with two live groups.
  val translationRequestCanTurnover = translationTurnoverEligible &&
    !translationDropPending && requestFire
  io.translationRequest.valid := (!translationOutstanding || translationRequestCanTurnover) &&
    !translatedRequestValid && !translatedExceptionValid && !io.redirectValid &&
    !predictionCorrectionFlushPending && freeSlots >= config.fetchWidth
  val translationRequestPc = Mux(translationRequestCanTurnover, requestPredictedNextPc, nextFetchPc)
  io.translationRequest.virtualAddress := translationRequestPc
  io.translationRequest.isWrite := False
  val translationRequestFire = io.translationRequest.valid && io.translationRequest.ready
  targetPredictorLookupPc := translationRequestPc
  targetPredictor.io.lookupValid := translationRequestFire
  val correctionKillsCachedRequest = predictionCorrectionOnResponse && cachedRequestFire
  // The cache-array lookup is synchronous, so canceling the just-accepted wrong-path request on
  // the following cycle still prevents both a hit response and a miss allocation.  Registering
  // this pulse also keeps response predecode out of the L1I response-register enable cone.
  val cachedCorrectionKillPending = RegNext(correctionKillsCachedRequest) init (False)
  io.cacheKill := (io.redirectValid && cacheOutstanding) || cachedCorrectionKillPending
  val predictorSpeculativeUpdateValid =
    RegNext(requestFire && !predictionCorrectionOnResponse) init (False)
  val predictorSpeculativeHistoryValid = Reg(Bool()) init (False)
  val predictorSpeculativeHistoryTaken = Reg(Bool()) init (False)
  val predictorSpeculativeRasPush = Reg(Bool()) init (False)
  val predictorSpeculativeRasPop = Reg(Bool()) init (False)
  val predictorSpeculativeReturnAddress = Reg(UInt(config.xlen bits)) init (0)
  when(requestFire) {
    predictorSpeculativeHistoryValid := requestHistoryValid
    predictorSpeculativeHistoryTaken := requestPredictedTaken &&
      requestPredictedType === OooPredictedBranchType.conditional
    predictorSpeculativeRasPush := requestPredictedTaken &&
      requestPredictedType === OooPredictedBranchType.call
    predictorSpeculativeRasPop := requestPredictedTaken &&
      requestPredictedType === OooPredictedBranchType.ret
    predictorSpeculativeReturnAddress := requestPredictedPc + 4
  }
  targetPredictor.io.speculativeHistoryValid := predictorSpeculativeUpdateValid &&
    predictorSpeculativeHistoryValid
  targetPredictor.io.speculativeHistoryTaken := predictorSpeculativeHistoryTaken
  targetPredictor.io.speculativeRasPush := predictorSpeculativeUpdateValid &&
    predictorSpeculativeRasPush
  targetPredictor.io.speculativeRasPop := predictorSpeculativeUpdateValid &&
    predictorSpeculativeRasPop
  targetPredictor.io.speculativeReturnAddress := predictorSpeculativeReturnAddress
  // FixBranch correction is response-predecode work.  Delay only its predictor-state restore,
  // matching ysyx's registered FixBranch redirect, so the wide RAS/GHR recovery enables do not
  // sit in the cache-response timing cone.  Hold lookup for that restore cycle; the corrected PC
  // is already installed, and the following lookup therefore observes recovered history.
  targetPredictor.io.flush := io.redirectValid || predictionCorrectionFlushPending

  val groupBase = cachePc &
    U(((BigInt(1) << config.xlen) - 1) ^ (fetchGroupBytes - 1), config.xlen bits)
  val firstSlot = cachePc(fetchGroupOffsetWidth - 1 downto 2)
  val responseSlotValid = Vec(Bool(), config.fetchWidth)
  val responsePredictionTaken = Vec(Bool(), config.fetchWidth)
  val responseDynamicPredictionHit = Vec(Bool(), config.fetchWidth)
  val responseControlTransfer = Vec(Bool(), config.fetchWidth)
  val responseActualType = Vec(UInt(OooPredictedBranchType.Width bits), config.fetchWidth)
  val responseActualTarget = Vec(UInt(config.xlen bits), config.fetchWidth)
  val responsePredictorMetadata = Vec(Bits(16 bits), config.fetchWidth)
  val earlierResponsePredictionTaken = Vec(Bool(), config.fetchWidth + 1)
  val responsePredictionTarget = Vec(UInt(config.xlen bits), config.fetchWidth)
  val responsePrefix = Vec(UInt(enqueueCountWidth bits), config.fetchWidth + 1)
  earlierResponsePredictionTaken(0) := False
  responsePrefix(0) := 0
  for (lane <- 0 until config.fetchWidth) {
    val predecode = io.cacheResponse.predecode(lane)
    responseControlTransfer(lane) := predecode.valid
    responseActualType(lane) := predecode.branchType
    responseActualTarget(lane) := predecode.target
    val targetMatches = predecode.indirect ||
      cachePrediction(lane).target === responseActualTarget(lane)
    val dynamicPredictionHit = cachePrediction(lane).hit && predecode.valid &&
      cachePrediction(lane).branchType === predecode.branchType && targetMatches
    responseDynamicPredictionHit(lane) := dynamicPredictionHit
    // A cold BTB miss does not identify a stable branch location yet. Preserve BTFNT for that
    // first encounter; the carried PHT state is trained at commit and becomes active with the BTB.
    val fallbackTaken = predecode.staticTaken
    val dynamicTaken = predecode.branchType =/= OooPredictedBranchType.conditional || Mux(
      cachePrediction(lane).phtValid,
      cachePrediction(lane).phtState(1),
      fallbackTaken
    )
    val lanePredictionTaken = Mux(
      dynamicPredictionHit,
      dynamicTaken,
      fallbackTaken
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
      cachePrediction(lane).target,
      predecode.target
    )
    responsePredictorMetadata(lane) := 0
    responsePredictorMetadata(lane)(9 downto 0) := cachePrediction(lane).phtIndex.asBits
    responsePredictorMetadata(lane)(11 downto 10) := cachePrediction(lane).phtState.asBits
    responsePredictorMetadata(lane)(12) := cachePrediction(lane).phtValid
    responsePredictorMetadata(lane)(15 downto 13) := predecode.branchType.asBits
    responsePrefix(lane + 1) := responsePrefix(lane) + responseSlotValid(lane).asUInt
  }
  val enqueueCount = responsePrefix(config.fetchWidth)
  val overlapRequiredSlots = U(config.fetchWidth * 2, countWidth bits)
  // Reserve both the current response and the next in-flight group without feeding response decode
  // into the L1I request-ready path.
  cacheRequestCapacityAvailable := Mux(
    responseFire,
    freeSlots >= overlapRequiredSlots,
    freeSlots >= config.fetchWidth
  )
  val responsePredictedTaken = earlierResponsePredictionTaken(config.fetchWidth)
  val responsePredictedTarget = UInt(config.xlen bits)
  responsePredictedTarget := groupBase + fetchGroupBytes
  for (lane <- (0 until config.fetchWidth).reverse) {
    when(responsePredictionTaken(lane)) {
      responsePredictedTarget := responsePredictionTarget(lane)
    }
  }
  val earlyLanePredictionTaken = responsePredictionTaken(cachePredictedLane)
  val earlyLanePredictionTarget = responsePredictionTarget(cachePredictedLane)
  val responsePredictionMatchesRequest = Mux(
    cachePredictedTaken,
    earlyLanePredictionTaken && cachePredictedTarget === earlyLanePredictionTarget,
    !responsePredictedTaken
  )
  predictionCorrectionOnResponse := responseFire && !responsePredictionMatchesRequest
  predictionCorrectionFlushPending := predictionCorrectionOnResponse

  val responseLearnMask = Bits(config.fetchWidth bits)
  for (lane <- 0 until config.fetchWidth) {
    responseLearnMask(lane) := responseSlotValid(lane) && !io.cacheResponse.error &&
      responseControlTransfer(lane) && !responseDynamicPredictionHit(lane) &&
      !io.cacheResponse.predecode(lane).indirect
  }
  val responseLearnPc = UInt(config.xlen bits)
  val responseLearnTarget = UInt(config.xlen bits)
  val responseLearnType = UInt(OooPredictedBranchType.Width bits)
  responseLearnPc := groupBase
  responseLearnTarget := groupBase + fetchGroupBytes
  responseLearnType := OooPredictedBranchType.direct
  for (lane <- (0 until config.fetchWidth).reverse) {
    when(responseLearnMask(lane)) {
      responseLearnPc := groupBase + lane * 4
      responseLearnTarget := responseActualTarget(lane)
      responseLearnType := responseActualType(lane)
    }
  }
  val responseLearnPending = RegNext(responseLearnMask.orR) init (False)
  val responseLearnPcReg = RegNextWhen(responseLearnPc, responseFire) init (0)
  val responseLearnTargetReg = RegNextWhen(responseLearnTarget, responseFire) init (0)
  val responseLearnTypeReg = RegNextWhen(responseLearnType, responseFire) init (
    OooPredictedBranchType.direct
  )
  val preciseBtbUpdate = io.predictorUpdateValid && io.predictorUpdateTaken
  targetPredictor.io.btbUpdateValid := preciseBtbUpdate || responseLearnPending
  targetPredictor.io.btbUpdatePc := responseLearnPcReg
  targetPredictor.io.btbUpdateTarget := responseLearnTargetReg
  targetPredictor.io.btbUpdateType := responseLearnTypeReg
  targetPredictor.io.btbUpdateDirectionTrained := False
  when(preciseBtbUpdate) {
    targetPredictor.io.btbUpdatePc := io.predictorUpdatePc
    targetPredictor.io.btbUpdateTarget := io.predictorUpdateTarget
    targetPredictor.io.btbUpdateType := io.predictorUpdateType
    targetPredictor.io.btbUpdateDirectionTrained := True
  }
  targetPredictor.io.phtUpdateValid := io.predictorUpdateValid &&
    io.predictorUpdateType === OooPredictedBranchType.conditional
  targetPredictor.io.phtUpdatePc := io.predictorUpdatePc
  targetPredictor.io.phtUpdateIndex := io.predictorUpdateMetadata(9 downto 0).asUInt
  targetPredictor.io.phtUpdateOldState := io.predictorUpdateMetadata(11 downto 10).asUInt
  targetPredictor.io.phtUpdateOldValid := io.predictorUpdateMetadata(12)
  targetPredictor.io.phtUpdateTaken := io.predictorUpdateTaken
  targetPredictor.io.commitRasPush := io.predictorUpdateValid && io.predictorUpdateIsCall
  targetPredictor.io.commitRasPop := io.predictorUpdateValid && io.predictorUpdateIsReturn
  targetPredictor.io.commitReturnAddress := io.predictorUpdatePc + 4
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
    wideDecode.io.predictorMetadata(lane) := Mux(
      decodeInputValid(lane),
      entries(decodeSource).predictorMetadata,
      B(0, 16 bits)
    )
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
    translatedExceptionValid := False
    cacheOutstanding := False
    cacheDropPending := False
    predictionPendingValid := False
  }.otherwise {
    when(translationRequestFire) {
      translationOutstanding := True
      translationPc := translationRequestPc
      predictionPendingValid := False
    }
    when(targetPredictor.io.responseValid) {
      predictionPendingValid := True
      for (lane <- 0 until config.fetchWidth) {
        pendingPrediction(lane) := targetPredictor.io.prediction(lane)
      }
    }
    when(translationResponseFire) {
      predictionPendingValid := False
      when(translationDropPending) {
        translationDropPending := False
      }.elsewhen(translationOutstanding) {
        translationOutstanding := translationRequestFire
        when(io.translationResponse.cancelled) {
          translatedRequestValid := False
          translatedExceptionValid := False
        }.elsewhen(translationResponseMatches && !io.translationResponse.exception.valid) {
          translatedRequestValid := True
          translatedPhysicalAddress := io.translationResponse.physicalAddress
          translatedUncached := io.translationResponse.uncached
          for (lane <- 0 until config.fetchWidth) {
            translatedPrediction(lane) := predictionForTranslation(lane)
          }
        }.elsewhen(translationResponseMatches) {
          // Preserve the original immediate exception path when no older cache request exists.
          // A speculative next-group fault waits behind the older instruction group.
          when(cacheOutstanding) {
            translatedExceptionValid := True
            translatedException := io.translationResponse.exception
          }
        }
      }
    }
    when(requestFire) {
      translatedRequestValid := False
      cacheOutstanding := True
      cacheDropPending := False
      cachePc := requestTranslationPc
      cachePredictedTaken := requestPredictedTaken
      cachePredictedLane := requestPredictedPc(fetchGroupOffsetWidth - 1 downto 2)
      cachePredictedTarget := requestPredictedTarget
      for (lane <- 0 until config.fetchWidth) {
        cachePrediction(lane) := requestPrediction(lane)
      }
      nextFetchPc := Mux(
        requestPredictedTaken,
        requestPredictedTarget,
        translatedGroupBase + fetchGroupBytes
      )
    }
    when(responseFire) {
      // A cached wrong-path handoff is accepted to keep response decode out of the L1I lookup
      // enable, then canceled at the L1 boundary.  Uncached AXI requests cannot be canceled and
      // therefore retain the response-drain protocol.
      cacheOutstanding := requestFire && !correctionKillsCachedRequest
      cacheDropPending := predictionCorrectionOnResponse && uncachedRequestFire
      when(predictionCorrectionOnResponse) {
        nextFetchPc := Mux(
          responsePredictedTaken,
          responsePredictedTarget,
          groupBase + fetchGroupBytes
        )
        translatedRequestValid := False
        translatedExceptionValid := False
        translationOutstanding := False
        translationDropPending :=
          (translationOutstanding || translationDropPending || translationRequestFire) &&
            !translationResponseFire
        predictionPendingValid := False
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
          entries(destination).predictorMetadata := responsePredictorMetadata(lane)
        }
      }
      tail := tail + enqueueCount
    }
    when(droppedResponseFire) {
      cacheOutstanding := requestFire
      cacheDropPending := False
    }
    val translationExceptionCommit = !cacheOutstanding && !translatedRequestValid &&
      !io.redirectValid && freeSlots =/= 0 &&
      (translatedExceptionValid || translationExceptionFire)
    when(translationExceptionCommit) {
      entries(tail).pc := translationPc
      entries(tail).instruction := B(0, 32 bits)
      entries(tail).exception := Mux(
        translationExceptionFire,
        io.translationResponse.exception,
        translatedException
      )
      entries(tail).predictedTaken := False
      entries(tail).predictedTarget := translationPc + 4
      entries(tail).predictorMetadata := B(0, 16 bits)
      tail := tail + 1
      nextFetchPc := translationPc + 4
      translatedExceptionValid := False
    }
    head := head + dequeueCount
    val acceptedCount = Mux(
      responseFire,
      enqueueCount,
      Mux(translationExceptionCommit, U(1, enqueueCountWidth bits), U(0, enqueueCountWidth bits))
    )
    count := count + acceptedCount - dequeueCount
  }

  io.fetchPc := nextFetchPc
  io.occupancy := count
}
