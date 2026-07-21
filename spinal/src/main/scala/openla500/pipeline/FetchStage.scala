package openla500.pipeline

import openla500.config.CoreConfig
import openla500.predict.PredictorDirectionMetadata
import spinal.core._
import spinal.lib._

/** Typed fetch stage translated from the active a158aa8 IF control.
  *
  * The output Stream holds its payload while decode applies backpressure. Flushes cancel younger
  * state; instruction address and data acknowledgements retain the historical split handshake.
  */
final class FetchStage(config: CoreConfig = CoreConfig.Locked) extends Component {
  val io = new Bundle {
    val downstream = master(Stream(FetchPayload()))
    val branchRepair = in Bool ()
    val branchTarget = in UInt (32 bits)
    val exceptionFlush = in Bool ()
    val ertnFlush = in Bool ()
    val refetchFlush = in Bool ()
    val instructionCacheFlush = in Bool ()
    val idleFlush = in Bool ()
    val writebackPc = in UInt (32 bits)
    val exceptionEntry = in UInt (32 bits)
    val exceptionEra = in UInt (32 bits)
    val exceptionTlbRefill = in Bool ()
    val tlbRefillEntry = in UInt (32 bits)
    val interrupt = in Bool ()

    val instructionAddressAccepted = in Bool ()
    val instructionDataValid = in Bool ()
    val instructionData = in Bits (32 bits)
    val instructionMiss = in Bool ()
    val instructionRequest = out Bool ()
    val instructionAddress = out UInt (32 bits)
    val instructionUncached = out Bool ()
    val tlbCancel = out Bool ()

    val paging = in Bool ()
    val directAddress = in Bool ()
    val dmw0 = in Bits (32 bits)
    val dmw1 = in Bits (32 bits)
    val currentPlv = in UInt (2 bits)
    val directFetchMat = in Bits (2 bits)
    val disableCache = in Bool ()

    val btbTarget = in UInt (32 bits)
    val btbTaken = in Bool ()
    val btbEnabled = in Bool ()
    val btbIndex = in UInt (5 bits)
    val btbDirection = in(PredictorDirectionMetadata())
    val directionPrediction = out(PredictorDirectionMetadata())

    val addressTranslation = out Bool ()
    val dmw0Enabled = out Bool ()
    val dmw1Enabled = out Bool ()
    val tlbFound = in Bool ()
    val tlbValid = in Bool ()
    val tlbMat = in Bits (2 bits)
    val tlbPlv = in UInt (2 bits)

    val fetchPc = out UInt (32 bits)
    val fetchEnable = out Bool ()
  }

  val fsValid = Reg(Bool()) init (False)
  val fsPc = Reg(UInt(32 bits)) init (U(config.resetVector - 4, 32 bits))
  val fsException = Reg(Bool()) init (False)
  val fsExceptionNumber = Reg(Bool()) init (False)
  val instructionBuffer = Reg(Bits(32 bits))
  val instructionBufferValid = Reg(Bool()) init (False)
  val idleLock = Reg(Bool()) init (False)
  val btbLock = Reg(Bits(38 bits))
  val btbDirectionLock = Reg(PredictorDirectionMetadata())
  val btbLockValid = Reg(Bool()) init (False)
  val flushRequestPc = Reg(UInt(32 bits))
  val flushRequestPending = Reg(Bool()) init (False)
  val branchRequestPc = Reg(UInt(32 bits))
  val branchRequestState = Reg(UInt(3 bits)) init (U(1, 3 bits))

  val branchEmpty = U(1, 3 bits)
  val branchWaitSlot = U(2, 3 bits)
  val branchWaitTarget = U(4, 3 bits)
  val flush =
    io.ertnFlush || io.exceptionFlush || io.refetchFlush || io.instructionCacheFlush || io.idleFlush
  val flushDelay = (flush && !io.instructionAddressAccepted) || io.idleFlush
  val flushDirty = flush && io.instructionAddressAccepted && !io.idleFlush

  // Preserve the golden bitwise-OR merge, including current BTB bits while the lock is active.
  val btbTargetLocked = Mux(btbLockValid, btbLock(31 downto 0).asUInt, U(0, 32 bits)) | io.btbTarget
  val btbIndexLocked = Mux(btbLockValid, btbLock(36 downto 32).asUInt, U(0, 5 bits)) | io.btbIndex
  val btbTakenLocked = (btbLockValid && btbLock(37)) || io.btbTaken
  val btbEnabledLocked = btbLockValid || io.btbEnabled
  val btbDirectionLocked = PredictorDirectionMetadata()
  btbDirectionLocked := io.btbDirection
  when(btbLockValid) {
    btbDirectionLocked := btbDirectionLock
  }
  val fetchBtbTarget = (io.btbTaken && io.btbEnabled) || (btbLockValid && btbLock(37))
  val sequencePc = fsPc + 4
  val architecturalExceptionEntry = Mux(io.exceptionTlbRefill, io.tlbRefillEntry, io.exceptionEntry)
  val instructionFlushPc = Mux(io.ertnFlush, io.exceptionEra, io.writebackPc + 4)

  val nextPc = UInt(32 bits)
  nextPc := sequencePc
  when(flushRequestPending) {
    nextPc := flushRequestPc
  }.elsewhen(io.exceptionFlush) {
    nextPc := architecturalExceptionEntry
  }.elsewhen(io.ertnFlush || io.refetchFlush || io.instructionCacheFlush || io.idleFlush) {
    nextPc := instructionFlushPc
  }.elsewhen(branchRequestState === branchWaitTarget) {
    nextPc := branchRequestPc
  }.elsewhen(io.branchRepair && fsValid) {
    nextPc := io.branchTarget
  }.elsewhen(fetchBtbTarget) {
    nextPc := btbTargetLocked
  }

  val directMode = io.directAddress && !io.paging
  val pagingMode = io.paging && !io.directAddress
  val dmw0Enabled = (((io.dmw0(0) && io.currentPlv === 0) || (io.dmw0(3) && io.currentPlv === 3)) &&
    fsPc(31 downto 29) === io.dmw0(31 downto 29).asUInt && pagingMode)
  val dmw1Enabled = (((io.dmw1(0) && io.currentPlv === 0) || (io.dmw1(3) && io.currentPlv === 3)) &&
    fsPc(31 downto 29) === io.dmw1(31 downto 29).asUInt && pagingMode)
  val addressTranslation = pagingMode && !dmw0Enabled && !dmw1Enabled
  val tlbRefill = !io.tlbFound && addressTranslation
  val tlbInvalid = !io.tlbValid && addressTranslation
  val tlbPrivilege = io.currentPlv > io.tlbPlv && addressTranslation
  val tlbCancel = tlbRefill || tlbInvalid || tlbPrivilege
  val tlbLockPc = tlbCancel && branchRequestState =/= branchWaitTarget && !flushRequestPending
  val prefetchAlignmentException = nextPc(1 downto 0) =/= 0

  val fsExceptionAny = fsException || tlbRefill || tlbInvalid || tlbPrivilege
  val fsReady = io.instructionDataValid || instructionBufferValid || fsExceptionAny
  val fsAllow = !fsValid || (fsReady && io.downstream.ready)
  val instructionRequest =
    ((fsAllow && !prefetchAlignmentException && !tlbLockPc) || flush || io.branchRepair) &&
      !(io.idleFlush || idleLock)
  val prefetchReady =
    (instructionRequest || prefetchAlignmentException) && io.instructionAddressAccepted
  val toFsValid = prefetchReady
  // A coincident sequential request can already be the authoritative redirect target. Remembering
  // that target in branchWaitTarget would issue it twice and duplicate its first instruction.
  val branchTargetAccepted =
    io.branchRepair && instructionRequest && io.instructionAddressAccepted && nextPc === io.branchTarget

  io.downstream.valid := fsValid && fsReady
  io.downstream.payload.pc := fsPc
  io.downstream.payload.instruction := Mux(
    instructionBufferValid,
    instructionBuffer,
    io.instructionData
  )
  io.downstream.payload.exceptionCode := tlbPrivilege.asBits ## tlbInvalid.asBits ## tlbRefill.asBits ## fsExceptionNumber.asBits
  io.downstream.payload.hasException := fsExceptionAny
  io.downstream.payload.instructionCacheMiss := io.instructionMiss
  io.downstream.payload.btbEnabled := btbEnabledLocked
  io.downstream.payload.btbTaken := btbTakenLocked
  io.downstream.payload.btbIndex := btbIndexLocked
  io.downstream.payload.btbTarget := btbTargetLocked
  io.directionPrediction := btbDirectionLocked

  io.instructionRequest := instructionRequest
  io.instructionAddress := nextPc
  io.instructionUncached := (directMode && io.directFetchMat === B"00") ||
    (dmw0Enabled && io.dmw0(5 downto 4) === B"00") ||
    (dmw1Enabled && io.dmw1(5 downto 4) === B"00") ||
    (addressTranslation && io.tlbMat === B"00") || io.disableCache
  io.tlbCancel := tlbCancel
  io.addressTranslation := addressTranslation
  io.dmw0Enabled := dmw0Enabled
  io.dmw1Enabled := dmw1Enabled
  io.fetchPc := nextPc
  io.fetchEnable := instructionRequest && io.instructionAddressAccepted

  when(!flushRequestPending) {
    when(flushDelay) {
      flushRequestPc := nextPc
      flushRequestPending := True
    }
  }.otherwise {
    when(prefetchReady) {
      flushRequestPending := False
    }.elsewhen(flush) {
      flushRequestPc := nextPc
    }
  }

  when(io.idleFlush && !io.interrupt) {
    idleLock := True
  }.elsewhen(io.interrupt) {
    idleLock := False
  }

  switch(branchRequestState) {
    is(branchEmpty) {
      when(flush) {
        branchRequestState := branchEmpty
      }.elsewhen(io.branchRepair && !fsValid && !io.instructionAddressAccepted) {
        branchRequestState := branchWaitSlot
        branchRequestPc := io.branchTarget
      }.elsewhen(
        (io.branchRepair && !io.instructionAddressAccepted && fsValid) ||
          (io.branchRepair && io.instructionAddressAccepted && !fsValid && !branchTargetAccepted)
      ) {
        branchRequestState := branchWaitTarget
        branchRequestPc := io.branchTarget
      }
    }
    is(branchWaitSlot) {
      when(flush) {
        branchRequestState := branchEmpty
      }.elsewhen(prefetchReady) {
        branchRequestState := branchWaitTarget
      }
    }
    is(branchWaitTarget) {
      when(prefetchReady || flush) { branchRequestState := branchEmpty }
    }
    default { branchRequestState := branchEmpty }
  }

  when(flush || io.fetchEnable) {
    btbLockValid := False
  }.elsewhen(io.btbEnabled && !prefetchReady) {
    btbLockValid := True
    btbLock := io.btbTaken.asBits ## io.btbIndex.asBits ## io.btbTarget.asBits
    btbDirectionLock := io.btbDirection
  }

  when((fsReady && io.downstream.ready) || flush) {
    instructionBufferValid := False
  }.elsewhen(io.instructionDataValid && !io.downstream.ready) {
    instructionBuffer := io.instructionData
    instructionBufferValid := True
  }

  when(flushDelay) {
    fsValid := False
  }.elsewhen(fsAllow) {
    fsValid := toFsValid
  }
  when(toFsValid && (fsAllow || flushDirty)) {
    fsPc := nextPc
    fsException := prefetchAlignmentException
    fsExceptionNumber := prefetchAlignmentException
  }
}
