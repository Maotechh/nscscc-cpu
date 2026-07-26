package openla500.backend

import openla500.core._
import openla500.execute.OooAguRequest
import openla500.memory._
import openla500.privileged._
import spinal.core._
import spinal.lib._

final case class OooStoreQueueEntry(config: OooCoreConfig) extends Bundle {
  val valid = Bool()
  val addressReady = Bool()
  val dataReady = Bool()
  val completed = Bool()
  val committed = Bool()
  val robPointer = UInt(config.robPointerWidth bits)
  val recoveryEpoch = UInt(config.recoveryEpochWidth bits)
  val virtualAddress = UInt(config.xlen bits)
  val physicalAddress = UInt(config.xlen bits)
  val translationDone = Bool()
  val uncached = Bool()
  val pdst = UInt(config.physicalRegIndexWidth bits)
  val writesPdst = Bool()
  val isSc = Bool()
  val scSuccess = Bool()
  val size = Bits(3 bits)
  val byteMask = Bits(4 bits)
  val writeData = Bits(config.xlen bits)
}

final case class OooLoadQueueEntry(config: OooCoreConfig) extends Bundle {
  val valid = Bool()
  val addressReady = Bool()
  val requestSent = Bool()
  val completed = Bool()
  val robPointer = UInt(config.robPointerWidth bits)
  val recoveryEpoch = UInt(config.recoveryEpochWidth bits)
  val pdst = UInt(config.physicalRegIndexWidth bits)
  val writesPdst = Bool()
  val virtualAddress = UInt(config.xlen bits)
  val physicalAddress = UInt(config.xlen bits)
  val translationDone = Bool()
  val uncached = Bool()
  val size = Bits(3 bits)
  val byteMask = Bits(4 bits)
  val signExtend = Bool()
  val isLl = Bool()
}

// Payload consumed after load selection.  Volatile queue state such as
// requestSent/translationDone stays in the indexed entry, while the wide
// immutable fields cross the selection boundary once and remain registered.
final case class OooScheduledLoad(config: OooCoreConfig) extends Bundle {
  val robPointer = UInt(config.robPointerWidth bits)
  val recoveryEpoch = UInt(config.recoveryEpochWidth bits)
  val pdst = UInt(config.physicalRegIndexWidth bits)
  val writesPdst = Bool()
  val virtualAddress = UInt(config.xlen bits)
  val size = Bits(3 bits)
  val byteMask = Bits(4 bits)
  val signExtend = Bool()
  val isLl = Bool()
}

final class OooLoadStoreQueue(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private def isOlder(older: UInt, younger: UInt): Bool = {
    val distance = (younger - older).resize(config.robPointerWidth)
    (distance =/= U(0, config.robPointerWidth bits)) && !distance.msb
  }

  private def formatLoad(word: Bits, address: UInt, size: Bits, signExtend: Bool): Bits = {
    val shift = (address(1 downto 0) ## U(0, 3 bits)).asUInt
    val shifted = word |>> shift
    val byteUpper = Bits(24 bits)
    val halfUpper = Bits(16 bits)
    byteUpper := B(0, 24 bits)
    halfUpper := B(0, 16 bits)
    when(signExtend && shifted(7)) { byteUpper := B((BigInt(1) << 24) - 1, 24 bits) }
    when(signExtend && shifted(15)) { halfUpper := B((BigInt(1) << 16) - 1, 16 bits) }
    val result = Bits(config.xlen bits)
    result := shifted(config.xlen - 1 downto 0)
    when(size === B(0, 3 bits)) {
      result := byteUpper ## shifted(7 downto 0)
    }.elsewhen(size === B(1, 3 bits)) {
      result := halfUpper ## shifted(15 downto 0)
    }
    result
  }

  private def formatStore(data: Bits, address: UInt, size: Bits): Bits = {
    val shifted = Bits(config.xlen bits)
    shifted := data
    when(size === B(0, 3 bits)) {
      switch(address(1 downto 0)) {
        is(U(0, 2 bits)) { shifted := B(0, 24 bits) ## data(7 downto 0) }
        is(U(1, 2 bits)) {
          shifted := B(0, 16 bits) ## data(7 downto 0) ## B(0, 8 bits)
        }
        is(U(2, 2 bits)) {
          shifted := B(0, 8 bits) ## data(7 downto 0) ## B(0, 16 bits)
        }
        default { shifted := data(7 downto 0) ## B(0, 24 bits) }
      }
    }.elsewhen(size === B(1, 3 bits)) {
      shifted := Mux(
        address(1),
        data(15 downto 0) ## B(0, 16 bits),
        B(0, 16 bits) ## data(15 downto 0)
      )
    }
    shifted
  }

  private def clearCompletion(completion: OooCompletion): Unit = {
    completion.robPointer := U(0, config.robPointerWidth bits)
    completion.recoveryEpoch := U(0, config.recoveryEpochWidth bits)
    completion.pdst := U(0, config.physicalRegIndexWidth bits)
    completion.writesPdst := False
    completion.data := B(0, config.xlen bits)
    completion.sideEffectData := B(0, config.xlen bits)
    completion.exception.valid := False
    completion.exception.ecode := U(0, 6 bits)
    completion.exception.esubcode := U(0, 9 bits)
    completion.exception.badVAddrValid := False
    completion.exception.badVAddr := U(0, config.xlen bits)
    completion.exception.tlbRefill := False
    completion.branchResolved := False
    completion.branchTaken := False
    completion.branchTarget := U(0, config.xlen bits)
    completion.branchMispredict := False
  }

  val io = new Bundle {
    val allocateValid = in Bits (config.renameWidth bits)
    val allocate = in Vec (OooLsqAllocate(config), config.renameWidth)
    val storeDataValid = in Bool ()
    val storeDataRobPointer = in UInt (config.robPointerWidth bits)
    val storeDataStoreQueueIndex = in UInt (config.storeQueueIndexWidth bits)
    val storeData = in Bits (config.xlen bits)
    val storeDataReady = out Bool ()
    val aguValid = in Bool ()
    val agu = in(OooAguRequest(config))
    val aguReady = out Bool ()
    val commitValid = in Bits (config.commitWidth bits)
    val commit = in Vec (OooCommitRecord(config), config.commitWidth)
    val translationRequest = master(Stream(OooTranslationRequest(config)))
    val translationResponse = slave(Stream(OooTranslationResponse(config)))
    val reservationValid = in Bool ()
    val reservationLineAddress = in Bits (28 bits)
    val dataRequestValid = out Bool ()
    val dataRequest = out(OooCacheRequest(config))
    val dataRequestReady = in Bool ()
    val dataResponseValid = in Bool ()
    val dataResponse = in(OooCacheResponse(config))
    val completionValid = out Bool ()
    val completion = out(OooCompletion(config))
    val releaseLoadValid = out Bits (config.commitWidth bits)
    val releaseStoreValid = out Bits (config.commitWidth bits)
    val storeDrainBusy = out Bool ()
    val orderingRobPointer = in UInt (config.robPointerWidth bits)
    val olderStorePending = out Bool ()
    val flush = in Bool ()
  }

  val loadReleaseValid = Bits(config.commitWidth bits)
  val storeReleaseValid = Bits(config.commitWidth bits)
  val aguMisaligned = (io.agu.size === B(2, 3 bits) && io.agu.virtualAddress(1 downto 0) =/= 0) ||
    (io.agu.size === B(1, 3 bits) && io.agu.virtualAddress(0))
  val aguFire = Bool()

  val stores = Vec.fill(config.storeQueueEntries)(Reg(OooStoreQueueEntry(config)))
  val loads = Vec.fill(config.loadQueueEntries)(Reg(OooLoadQueueEntry(config)))
  for (entry <- stores) {
    entry.valid.init(False)
    entry.addressReady.init(False)
    entry.dataReady.init(False)
    entry.completed.init(False)
    entry.committed.init(False)
    entry.translationDone.init(False)
  }
  for (entry <- loads) {
    entry.valid.init(False)
    entry.addressReady.init(False)
    entry.requestSent.init(False)
    entry.completed.init(False)
    entry.translationDone.init(False)
  }
  val storeHead = Reg(UInt(config.storeQueueIndexWidth bits)) init (0)
  // The allocator releases load slots in retirement order.  Keeping the
  // oldest live slot explicitly lets the scheduler rotate a small pending
  // bitmap instead of comparing every load ROB pointer against every other
  // load on every cycle.
  val loadBase = Reg(UInt(config.loadQueueIndexWidth bits)) init (0)
  val drainAfterFlush = RegInit(False)
  val committedStorePresent = stores
    .map(entry => entry.valid && entry.committed)
    .reduce(_ || _)
  io.storeDrainBusy := drainAfterFlush
  io.olderStorePending := stores
    .map(entry => entry.valid && isOlder(entry.robPointer, io.orderingRobPointer))
    .reduce(_ || _)

  // Completed loads remain allocated until commit.  The allocator therefore
  // advances the base only on commit, and a rotated priority select preserves
  // program order across physical slot wrap-around.
  val pendingLoads = Bits(config.loadQueueEntries bits)
  for (entry <- 0 until config.loadQueueEntries) {
    pendingLoads(entry) := loads(entry).valid && !loads(entry).requestSent &&
      !loads(entry).completed
  }
  val rotatedPending = ((pendingLoads ## pendingLoads) |>> loadBase)
    .resize(config.loadQueueEntries)
  val loadHeadOffset = OHToUInt(OHMasking.first(rotatedPending))
  val selectedLoadHead = (loadBase + loadHeadOffset).resized
  val selectedLoadValid = pendingLoads.orR
  // Match the registered uop boundary used by the reference LoadQueue.  The
  // selected index and immutable payload are state: translation, forwarding,
  // and cache request ownership no longer re-read wide queue fields through a
  // second asynchronous loadHead mux.
  val scheduledLoadValid = RegInit(False)
  val loadHead = Reg(UInt(config.loadQueueIndexWidth bits)) init (0)
  val scheduledLoad = Reg(OooScheduledLoad(config))
  when(io.flush) {
    scheduledLoadValid := False
  }.otherwise {
    scheduledLoadValid := selectedLoadValid
    when(selectedLoadValid) {
      loadHead := selectedLoadHead
      val selectedLoad = loads(selectedLoadHead)
      scheduledLoad.robPointer := selectedLoad.robPointer
      scheduledLoad.recoveryEpoch := selectedLoad.recoveryEpoch
      scheduledLoad.pdst := selectedLoad.pdst
      scheduledLoad.writesPdst := selectedLoad.writesPdst
      scheduledLoad.virtualAddress := selectedLoad.virtualAddress
      scheduledLoad.size := selectedLoad.size
      scheduledLoad.byteMask := selectedLoad.byteMask
      scheduledLoad.signExtend := selectedLoad.signExtend
      scheduledLoad.isLl := selectedLoad.isLl

      // AGU and scheduler can target the same newly-ready entry on one edge.
      // Bypass that write into the registered payload so this timing cut does
      // not add a cycle to the normal address-to-translation path.
      when(
        aguFire && !io.agu.isWrite && !aguMisaligned &&
          io.agu.uop.loadQueueIndex === selectedLoadHead &&
          selectedLoad.valid && selectedLoad.robPointer === io.agu.uop.robPointer
      ) {
        scheduledLoad.robPointer := io.agu.uop.robPointer
        scheduledLoad.recoveryEpoch := io.agu.uop.recoveryEpoch
        scheduledLoad.pdst := io.agu.uop.pdst
        scheduledLoad.writesPdst := io.agu.uop.pdst =/= 0
        scheduledLoad.virtualAddress := io.agu.virtualAddress
        scheduledLoad.size := io.agu.size
        scheduledLoad.byteMask := io.agu.byteMask
        scheduledLoad.signExtend := io.agu.uop.decoded.memorySignExtend
        scheduledLoad.isLl := io.agu.uop.decoded.isLl
      }
    }
  }

  // A direct LSQ probe can present a recycled slot without the allocator's
  // preceding history.  Initialize the base from the first allocation group
  // once, then keep it purely pointer-driven during normal execution.  The
  // age comparisons here terminate at the loadBase register and are not in
  // the completion-to-ROB path.
  val allocationLoads = Bits(config.renameWidth bits)
  for (lane <- 0 until config.renameWidth) {
    allocationLoads(lane) := io.allocateValid(lane) && io.allocate(lane).isLoad
  }
  val initialOldest = Bits(config.renameWidth bits)
  for (lane <- 0 until config.renameWidth) {
    val olderCandidate = Bits(config.renameWidth bits)
    olderCandidate := B(0, config.renameWidth bits)
    for (other <- 0 until config.renameWidth if other != lane) {
      olderCandidate(other) := allocationLoads(other) &&
        isOlder(io.allocate(other).robPointer, io.allocate(lane).robPointer)
    }
    initialOldest(lane) := allocationLoads(lane) && !olderCandidate.orR
  }
  val initialLoadSelect = Mux(
    initialOldest.orR,
    OHMasking.first(initialOldest),
    OHMasking.first(allocationLoads)
  )
  val initialLoadIndex = OHToUInt(initialLoadSelect)
  val liveLoads = loads.map(_.valid).reduce(_ || _)
  when(io.flush) {
    loadBase := U(0, config.loadQueueIndexWidth bits)
  }.otherwise {
    when(!liveLoads && allocationLoads.orR) {
      loadBase := io.allocate(initialLoadIndex).loadQueueIndex
    }.elsewhen(loadReleaseValid.orR) {
      loadBase := (loadBase + CountOne(loadReleaseValid)).resized
    }
  }

  val headStore = stores(storeHead)
  val headLoadState = loads(loadHead)
  val loadHeadReady = scheduledLoadValid && headLoadState.valid &&
    headLoadState.robPointer === scheduledLoad.robPointer && headLoadState.addressReady &&
    !headLoadState.requestSent && !headLoadState.completed

  val unknownOlderStore = Bits(config.storeQueueEntries bits)
  val partialOverlapStore = Bits(config.storeQueueEntries bits)
  val pendingDataStore = Bits(config.storeQueueEntries bits)
  val forwardingStore = Bits(config.storeQueueEntries bits)
  for (entry <- 0 until config.storeQueueEntries) {
    val store = stores(entry)
    val older = store.valid && isOlder(store.robPointer, scheduledLoad.robPointer)
    val sameWord = store.virtualAddress(config.xlen - 1 downto 2) ===
      scheduledLoad.virtualAddress(config.xlen - 1 downto 2)
    val overlap = (store.byteMask & scheduledLoad.byteMask).orR
    val covers = (store.byteMask & scheduledLoad.byteMask) === scheduledLoad.byteMask
    unknownOlderStore(entry) := older && !store.addressReady
    partialOverlapStore(entry) := older && store.addressReady && sameWord && overlap && !covers
    pendingDataStore(entry) := older && store.addressReady && sameWord && overlap &&
      !store.dataReady
    forwardingStore(entry) := older && store.addressReady && store.dataReady && sameWord && covers
  }

  val forwardingCount = CountOne(forwardingStore)
  val forwardingId = OHToUInt(OHMasking.first(forwardingStore))
  val loadOrderClear = !unknownOlderStore.orR && !partialOverlapStore.orR &&
    !pendingDataStore.orR
  val forwardCandidate = loadHeadReady && !scheduledLoad.isLl && loadOrderClear &&
    forwardingCount === 1
  val cacheLoadBase = loadHeadReady && loadOrderClear && forwardingCount === 0
  val cacheLoadCandidate = cacheLoadBase && headLoadState.translationDone
  val storeRequest = headStore.valid && headStore.addressReady && headStore.dataReady &&
    headStore.translationDone && headStore.completed && headStore.committed &&
    (!headStore.isSc || headStore.scSuccess)
  val failedScRelease = headStore.valid && headStore.addressReady &&
    headStore.translationDone && headStore.completed && headStore.committed &&
    headStore.isSc && !headStore.scSuccess

  val translationActive = RegInit(False)
  // A redirect can invalidate the LSQ owner after a translation request has
  // fired, while the translator still owes one response. Keep consuming that
  // response as a cancelled transaction so the shared translator cannot be
  // left permanently backpressured.
  val translationCancelPending = RegInit(False)
  val translationOwnerStore = RegInit(False)
  val translationOwnerRobPointer = Reg(UInt(config.robPointerWidth bits))
  val translationOwnerRecoveryEpoch = Reg(UInt(config.recoveryEpochWidth bits))
  val translationOwnerLoadIndex = Reg(UInt(config.loadQueueIndexWidth bits))
  val translationOwnerStoreIndex = Reg(UInt(config.storeQueueIndexWidth bits))
  val storeNeedsTranslation = headStore.valid && headStore.addressReady &&
    !headStore.translationDone
  // Translation has no memory side effect, so overlap it with the unresolved-store window.
  // Store ordering and forwarding are still checked before a translated load reaches D-cache.
  val loadNeedsTranslation = loadHeadReady && !headLoadState.translationDone
  val selectStoreTranslation = storeNeedsTranslation
  io.translationRequest.valid := !io.flush && !translationActive && !translationCancelPending &&
    (storeNeedsTranslation || loadNeedsTranslation)
  io.translationRequest.virtualAddress := Mux(
    selectStoreTranslation,
    headStore.virtualAddress,
    scheduledLoad.virtualAddress
  )
  io.translationRequest.isWrite := selectStoreTranslation
  val translationRequestFire = io.translationRequest.valid && io.translationRequest.ready
  when(translationRequestFire) {
    translationActive := True
    translationOwnerStore := selectStoreTranslation
    translationOwnerRobPointer := Mux(
      selectStoreTranslation,
      headStore.robPointer,
      scheduledLoad.robPointer
    )
    translationOwnerRecoveryEpoch := Mux(
      selectStoreTranslation,
      headStore.recoveryEpoch,
      scheduledLoad.recoveryEpoch
    )
    translationOwnerLoadIndex := loadHead
    translationOwnerStoreIndex := storeHead
  }

  val requestCandidate = OooCacheRequest(config)
  requestCandidate.virtualAddress := scheduledLoad.virtualAddress
  requestCandidate.physicalAddress := headLoadState.physicalAddress
  requestCandidate.isWrite := False
  requestCandidate.size := scheduledLoad.size
  requestCandidate.byteMask := scheduledLoad.byteMask
  requestCandidate.writeData := B(0, config.xlen bits)
  requestCandidate.uncached := headLoadState.uncached
  requestCandidate.robPointer := scheduledLoad.robPointer
  requestCandidate.pdst := scheduledLoad.pdst
  when(storeRequest) {
    requestCandidate.virtualAddress := headStore.virtualAddress
    requestCandidate.physicalAddress := headStore.physicalAddress
    requestCandidate.isWrite := True
    requestCandidate.size := headStore.size
    requestCandidate.byteMask := headStore.byteMask
    requestCandidate.writeData := formatStore(
      headStore.writeData,
      headStore.virtualAddress,
      headStore.size
    )
    requestCandidate.uncached := headStore.uncached
    requestCandidate.robPointer := headStore.robPointer
    requestCandidate.pdst := U(0, config.physicalRegIndexWidth bits)
  }

  // Cut the oldest-load/store-ordering cone before cache and AXI backpressure.  A buffered
  // committed store remains represented in the SQ until the hierarchy accepts it, so CACOP
  // ordering and recovery still observe that store as pending.
  val requestBufferValid = RegInit(False)
  val requestBuffer = Reg(OooCacheRequest(config))
  val requestBufferLoadIndex = Reg(UInt(config.loadQueueIndexWidth bits))
  val requestBufferStoreIndex = Reg(UInt(config.storeQueueIndexWidth bits))
  val requestCapture = !io.flush && !requestBufferValid &&
    (storeRequest || cacheLoadCandidate)
  io.dataRequestValid := requestBufferValid && !io.flush
  io.dataRequest := requestBuffer
  val dataRequestFire = io.dataRequestValid && io.dataRequestReady
  val storeRequestFire = dataRequestFire && requestBuffer.isWrite
  val loadRequestFire = dataRequestFire && !requestBuffer.isWrite

  val responseLoadMatch = Bits(config.loadQueueEntries bits)
  for (entry <- 0 until config.loadQueueEntries) {
    responseLoadMatch(entry) := loads(entry).valid && loads(entry).requestSent &&
      !loads(entry).completed && io.dataResponse.robPointer === loads(entry).robPointer
  }
  val responseLoadValid = responseLoadMatch.orR
  val responseLoadIndex = OHToUInt(OHMasking.first(responseLoadMatch))
  val responseLoadRobPointer = loads(responseLoadIndex).robPointer
  val responseLoadRecoveryEpoch = loads(responseLoadIndex).recoveryEpoch
  val responseLoadPdst = loads(responseLoadIndex).pdst
  val responseLoadWritesPdst = loads(responseLoadIndex).writesPdst
  val responseLoadVirtualAddress = loads(responseLoadIndex).virtualAddress
  val responseLoadSize = loads(responseLoadIndex).size
  val responseLoadSignExtend = loads(responseLoadIndex).signExtend
  val responseLoadIsLl = loads(responseLoadIndex).isLl
  val responseLoadPhysicalAddress = loads(responseLoadIndex).physicalAddress
  val responseLoadUncached = loads(responseLoadIndex).uncached
  val responseAccepted = io.dataResponseValid && responseLoadValid
  val forwardFire = !io.dataResponseValid && forwardCandidate

  val aguTargetAvailable = Mux(
    io.agu.isWrite,
    stores(io.agu.uop.storeQueueIndex).valid &&
      stores(io.agu.uop.storeQueueIndex).robPointer === io.agu.uop.robPointer &&
      !stores(io.agu.uop.storeQueueIndex).addressReady,
    loads(io.agu.uop.loadQueueIndex).valid &&
      loads(io.agu.uop.loadQueueIndex).robPointer === io.agu.uop.robPointer &&
      !loads(io.agu.uop.loadQueueIndex).addressReady
  )
  val storeDataTarget = stores(io.storeDataStoreQueueIndex)
  io.storeDataReady := !io.flush && storeDataTarget.valid &&
    storeDataTarget.robPointer === io.storeDataRobPointer && !storeDataTarget.dataReady
  val storeDataFire = io.storeDataValid && io.storeDataReady
  val translatedScSuccess = !io.translationResponse.exception.valid &&
    !io.translationResponse.uncached && io.reservationValid &&
    io.reservationLineAddress === io.translationResponse.physicalAddress(31 downto 4).asBits
  val translationResponseCandidate = io.translationResponse.valid && translationActive
  val translationStore = stores(translationOwnerStoreIndex)
  val translationStoreCanComplete = translationStore.dataReady ||
    (translationStore.isSc && !translatedScSuccess)
  val translationProducesCompletion = io.translationResponse.exception.valid ||
    (translationOwnerStore && translationStoreCanComplete)
  val storeCompletionCandidate = headStore.valid && headStore.addressReady &&
    headStore.translationDone && !headStore.completed &&
    (headStore.dataReady || (headStore.isSc && !headStore.scSuccess))
  val baseCompletionBusy = io.dataResponseValid || forwardCandidate ||
    storeCompletionCandidate
  io.translationResponse.ready := translationCancelPending ||
    (translationActive && (!translationProducesCompletion || !baseCompletionBusy))
  val translationResponseFire = io.translationResponse.valid && io.translationResponse.ready
  val translationCompletionFire = translationResponseFire && !io.flush &&
    translationActive && translationProducesCompletion
  val translationCompletionCandidate = translationResponseCandidate && translationProducesCompletion
  // Misaligned accesses are rare and already terminal exceptions. Buffer that
  // completion instead of feeding the current load/translation arbitration
  // back into aguReady. This keeps an older load's forwarding cone out of the
  // store-entry write enable while preserving every exceptional completion.
  val aguExceptionCompletionValid = RegInit(False)
  val aguExceptionRobPointer = Reg(UInt(config.robPointerWidth bits))
  val aguExceptionRecoveryEpoch = Reg(UInt(config.recoveryEpochWidth bits))
  val aguExceptionPdst = Reg(UInt(config.physicalRegIndexWidth bits))
  val aguExceptionIsSc = Reg(Bool())
  val aguExceptionBadVAddr = Reg(UInt(config.xlen bits))
  val aguExceptionCompletionReady = aguExceptionCompletionValid &&
    !baseCompletionBusy && !translationCompletionCandidate
  io.aguReady := !io.flush && aguTargetAvailable &&
    (!aguMisaligned || !aguExceptionCompletionValid)
  aguFire := io.aguValid && io.aguReady
  val aguExceptionCapture = aguFire && aguMisaligned

  val generatedCompletionValid = responseAccepted || forwardFire ||
    storeCompletionCandidate || translationCompletionFire || aguExceptionCompletionReady
  val generatedCompletion = OooCompletion(config)
  clearCompletion(generatedCompletion)
  when(responseAccepted) {
    generatedCompletion.robPointer := responseLoadRobPointer
    generatedCompletion.recoveryEpoch := responseLoadRecoveryEpoch
    generatedCompletion.pdst := responseLoadPdst
    generatedCompletion.writesPdst := responseLoadWritesPdst
    generatedCompletion.data := formatLoad(
      io.dataResponse.data,
      responseLoadVirtualAddress,
      responseLoadSize,
      responseLoadSignExtend
    )
    when(io.dataResponse.error) {
      generatedCompletion.exception.valid := True
      generatedCompletion.exception.ecode := U(8, 6 bits)
      generatedCompletion.exception.badVAddrValid := True
      generatedCompletion.exception.badVAddr := responseLoadVirtualAddress
    }
  }.elsewhen(forwardFire) {
    generatedCompletion.robPointer := scheduledLoad.robPointer
    generatedCompletion.recoveryEpoch := scheduledLoad.recoveryEpoch
    generatedCompletion.pdst := scheduledLoad.pdst
    generatedCompletion.writesPdst := scheduledLoad.writesPdst
    generatedCompletion.data := formatLoad(
      formatStore(
        stores(forwardingId).writeData,
        stores(forwardingId).virtualAddress,
        stores(forwardingId).size
      ),
      scheduledLoad.virtualAddress,
      scheduledLoad.size,
      scheduledLoad.signExtend
    )
  }.elsewhen(storeCompletionCandidate) {
    generatedCompletion.robPointer := headStore.robPointer
    generatedCompletion.recoveryEpoch := headStore.recoveryEpoch
    generatedCompletion.pdst := headStore.pdst
    generatedCompletion.writesPdst := headStore.writesPdst
    generatedCompletion.data := Mux(
      headStore.isSc,
      headStore.scSuccess.asBits.resize(config.xlen),
      B(0, config.xlen bits)
    )
  }.elsewhen(translationCompletionFire) {
    val store = stores(translationOwnerStoreIndex)
    val load = loads(translationOwnerLoadIndex)
    generatedCompletion.robPointer := translationOwnerRobPointer
    generatedCompletion.recoveryEpoch := translationOwnerRecoveryEpoch
    generatedCompletion.pdst := Mux(
      translationOwnerStore,
      store.pdst,
      load.pdst
    )
    generatedCompletion.writesPdst := Mux(
      translationOwnerStore,
      store.writesPdst,
      load.writesPdst
    )
    generatedCompletion.data := Mux(
      translationOwnerStore && store.isSc,
      translatedScSuccess.asBits.resize(config.xlen),
      B(0, config.xlen bits)
    )
    generatedCompletion.exception := io.translationResponse.exception
  }.elsewhen(aguExceptionCompletionReady) {
    generatedCompletion.robPointer := aguExceptionRobPointer
    generatedCompletion.recoveryEpoch := aguExceptionRecoveryEpoch
    generatedCompletion.pdst := aguExceptionPdst
    generatedCompletion.writesPdst := aguExceptionPdst =/= 0
    generatedCompletion.data := Mux(
      aguExceptionIsSc,
      B(1, config.xlen bits),
      B(0, config.xlen bits)
    )
    generatedCompletion.exception.valid := True
    generatedCompletion.exception.ecode := U(9, 6 bits)
    generatedCompletion.exception.esubcode := U(0, 9 bits)
    generatedCompletion.exception.badVAddrValid := True
    generatedCompletion.exception.badVAddr := aguExceptionBadVAddr
    generatedCompletion.exception.tlbRefill := False
  }
  // Only LL consumes the LSQ side-effect sidecar at retirement. Keep it out of
  // the store-forwarding/completion-arbitration cone so ordinary completions do
  // not turn the entire 32-bit field into a timing-critical conditional clear.
  when(responseAccepted && responseLoadIsLl) {
    generatedCompletion.sideEffectData :=
      responseLoadPhysicalAddress(31 downto 1).asBits ## responseLoadUncached.asBits
  }

  val completionValid = RegInit(False)
  val completion = Reg(OooCompletion(config))
  when(io.flush) {
    aguExceptionCompletionValid := False
    when(requestBufferValid && !requestBuffer.isWrite) {
      requestBufferValid := False
    }
    completionValid := False
  }.otherwise {
    when(aguExceptionCompletionReady) {
      aguExceptionCompletionValid := False
    }
    when(aguExceptionCapture) {
      aguExceptionCompletionValid := True
      aguExceptionRobPointer := io.agu.uop.robPointer
      aguExceptionRecoveryEpoch := io.agu.uop.recoveryEpoch
      aguExceptionPdst := io.agu.uop.pdst
      aguExceptionIsSc := io.agu.uop.decoded.isSc
      aguExceptionBadVAddr := io.agu.virtualAddress
    }
    when(requestCapture) {
      requestBufferValid := True
      requestBuffer := requestCandidate
      requestBufferLoadIndex := loadHead
      requestBufferStoreIndex := storeHead
    }
    when(dataRequestFire) {
      requestBufferValid := False
    }
    completionValid := generatedCompletionValid
    // Validity, not payload clock-enables, defines whether this register is
    // observable. Sampling every cycle prevents the deep forwarding predicate
    // from being replicated onto every completion payload register.
    completion := generatedCompletion
  }
  io.completionValid := completionValid
  io.completion := completion

  loadReleaseValid := B(0, config.commitWidth bits)
  storeReleaseValid := B(0, config.commitWidth bits)
  for (lane <- 0 until config.commitWidth) {
    val loadCommitMatch = io.commitValid(lane) && io.commit(lane).isLoad &&
      loads(io.commit(lane).loadQueueIndex).valid &&
      loads(io.commit(lane).loadQueueIndex).robPointer === io.commit(lane).robPointer
    loadReleaseValid(lane) := !io.flush && loadCommitMatch
  }
  storeReleaseValid(0) := !io.flush && (storeRequestFire || failedScRelease)
  io.releaseLoadValid := loadReleaseValid
  io.releaseStoreValid := storeReleaseValid

  when(io.flush) {
    // Preserve a cancellation token until the translator's outstanding
    // response is consumed. A response consumed on the flush edge itself does
    // not need a token.
    translationCancelPending :=
      (translationActive || translationCancelPending) && !translationResponseFire
    translationActive := False
    // Retired stores are architectural state.  Preserve the committed prefix
    // across recovery and drain it before admitting the new speculative epoch.
    drainAfterFlush := committedStorePresent
    when(!committedStorePresent) {
      storeHead := 0
    }
    for (entry <- stores) {
      when(!entry.committed) {
        entry.valid := False
        entry.addressReady := False
        entry.dataReady := False
        entry.completed := False
        entry.committed := False
        entry.translationDone := False
      }
    }
    for (entry <- loads) {
      entry.valid := False
      entry.addressReady := False
      entry.requestSent := False
      entry.completed := False
      entry.translationDone := False
    }
  }.otherwise {
    when(translationCancelPending && translationResponseFire) {
      translationCancelPending := False
    }
    when(drainAfterFlush && !committedStorePresent) {
      drainAfterFlush := False
      storeHead := 0
    }
    for (lane <- 0 until config.renameWidth) {
      when(io.allocateValid(lane) && io.allocate(lane).isStore) {
        val index = io.allocate(lane).storeQueueIndex
        stores(index).valid := True
        stores(index).addressReady := False
        stores(index).dataReady := False
        stores(index).completed := False
        stores(index).committed := False
        stores(index).translationDone := False
        stores(index).scSuccess := False
        stores(index).robPointer := io.allocate(lane).robPointer
        stores(index).recoveryEpoch := io.allocate(lane).recoveryEpoch
      }
      when(io.allocateValid(lane) && io.allocate(lane).isLoad) {
        val index = io.allocate(lane).loadQueueIndex
        loads(index).valid := True
        loads(index).addressReady := False
        loads(index).requestSent := False
        loads(index).completed := False
        loads(index).translationDone := False
        loads(index).robPointer := io.allocate(lane).robPointer
        loads(index).recoveryEpoch := io.allocate(lane).recoveryEpoch
      }
    }

    when(aguFire && io.agu.isWrite) {
      val index = io.agu.uop.storeQueueIndex
      stores(index).virtualAddress := io.agu.virtualAddress
      stores(index).pdst := io.agu.uop.pdst
      stores(index).writesPdst := io.agu.uop.pdst =/= 0
      stores(index).isSc := io.agu.uop.decoded.isSc
      stores(index).size := io.agu.size
      stores(index).byteMask := io.agu.byteMask
      stores(index).addressReady := !aguMisaligned
      stores(index).translationDone := False
    }
    when(storeDataFire) {
      val index = io.storeDataStoreQueueIndex
      stores(index).writeData := io.storeData
      stores(index).dataReady := True
    }
    when(aguFire && !io.agu.isWrite) {
      val index = io.agu.uop.loadQueueIndex
      loads(index).pdst := io.agu.uop.pdst
      loads(index).writesPdst := io.agu.uop.pdst =/= 0
      loads(index).virtualAddress := io.agu.virtualAddress
      loads(index).size := io.agu.size
      loads(index).byteMask := io.agu.byteMask
      loads(index).signExtend := io.agu.uop.decoded.memorySignExtend
      loads(index).isLl := io.agu.uop.decoded.isLl
      loads(index).addressReady := !aguMisaligned
      loads(index).completed := aguMisaligned
      loads(index).translationDone := False
    }

    when(translationResponseFire && translationActive) {
      translationActive := False
      when(translationOwnerStore) {
        val entry = stores(translationOwnerStoreIndex)
        when(entry.valid && entry.robPointer === translationOwnerRobPointer) {
          entry.physicalAddress := io.translationResponse.physicalAddress
          entry.uncached := io.translationResponse.uncached
          entry.translationDone := True
          when(entry.isSc) { entry.scSuccess := translatedScSuccess }
          when(translationCompletionFire) { entry.completed := True }
        }
      }.otherwise {
        val entry = loads(translationOwnerLoadIndex)
        when(entry.valid && entry.robPointer === translationOwnerRobPointer) {
          entry.physicalAddress := io.translationResponse.physicalAddress
          entry.uncached := io.translationResponse.uncached
          entry.translationDone := True
          when(io.translationResponse.exception.valid) { entry.completed := True }
        }
      }
    }
    when(storeCompletionCandidate) {
      stores(storeHead).completed := True
    }

    for (lane <- 0 until config.commitWidth) {
      when(io.releaseLoadValid(lane)) {
        loads(io.commit(lane).loadQueueIndex).valid := False
      }
      when(
        io.commitValid(lane) && io.commit(lane).isStore &&
          !io.commit(lane).exception.valid &&
          stores(io.commit(lane).storeQueueIndex).valid &&
          stores(io.commit(lane).storeQueueIndex).robPointer === io.commit(lane).robPointer
      ) {
        stores(io.commit(lane).storeQueueIndex).committed := True
      }
    }

    when(loadRequestFire) {
      val entry = loads(requestBufferLoadIndex)
      when(entry.valid && entry.robPointer === requestBuffer.robPointer) {
        entry.requestSent := True
      }
    }
    when(responseAccepted) {
      loads(responseLoadIndex).completed := True
    }
    when(forwardFire) {
      loads(loadHead).completed := True
    }
    when(storeRequestFire || failedScRelease) {
      val releaseIndex = Mux(
        storeRequestFire,
        requestBufferStoreIndex,
        storeHead
      )
      stores(releaseIndex).valid := False
      stores(releaseIndex).addressReady := False
      stores(releaseIndex).dataReady := False
      stores(releaseIndex).completed := False
      stores(releaseIndex).committed := False
      stores(releaseIndex).translationDone := False
      storeHead := storeHead + 1
    }
  }
}
