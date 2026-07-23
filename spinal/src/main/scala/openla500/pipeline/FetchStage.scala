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
final class FetchStage(
    config: CoreConfig = CoreConfig.Locked,
    fetchPacketEnabled: Boolean = false
) extends Component {
  val io = new Bundle {
    val downstream =
      if (!fetchPacketEnabled) master(Stream(FetchPayload())) else null
    val downstreamPacket =
      if (fetchPacketEnabled) master(Stream(FetchPacket())) else null
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
    val instructionLineValid = if (fetchPacketEnabled) in(Bool()) else null
    val instructionLineData = if (fetchPacketEnabled) in(Bits(128 bits)) else null
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
    val directionPrediction =
      if (!fetchPacketEnabled) out(PredictorDirectionMetadata()) else null

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
  val instructionLineBuffer =
    if (fetchPacketEnabled) Reg(Bits(128 bits)) else null
  val instructionLineBufferValid =
    if (fetchPacketEnabled) Reg(Bool()) init (False) else null
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
  val liveLineValid = if (fetchPacketEnabled) io.instructionLineValid else False
  val bufferedLineValid =
    if (fetchPacketEnabled) instructionLineBufferValid else False
  val responseIsLine = liveLineValid || bufferedLineValid
  val responseLineData =
    if (fetchPacketEnabled)
      Mux(
        instructionLineBufferValid,
        instructionLineBuffer,
        io.instructionLineData
      )
    else null
  val responseValid =
    io.instructionDataValid || instructionBufferValid || responseIsLine

  val lineWords =
    if (fetchPacketEnabled) {
      val words = Vec(Bits(32 bits), FetchPacket.Width)
      for (bank <- 0 until FetchPacket.Width) {
        words(bank) := responseLineData(bank * 32 + 31 downto bank * 32)
      }
      words
    } else null
  val lineStartWord = if (fetchPacketEnabled) fsPc(3 downto 2) else null
  val firstInstruction =
    if (fetchPacketEnabled)
      Mux(
        responseIsLine,
        lineWords(lineStartWord),
        Mux(instructionBufferValid, instructionBuffer, io.instructionData)
      )
    else Mux(instructionBufferValid, instructionBuffer, io.instructionData)

  val packetInstructions =
    if (fetchPacketEnabled) {
      val instructions = Vec(Bits(32 bits), FetchPacket.Width)
      for (lane <- 0 until FetchPacket.Width) {
        val wrappedBank = (lineStartWord + U(lane, 2 bits)).resized
        instructions(lane) := lineWords(wrappedBank)
      }
      instructions
    } else null
  val packetInLine =
    if (fetchPacketEnabled) {
      val inLine = Vec(Bool(), FetchPacket.Width)
      for (lane <- 0 until FetchPacket.Width) {
        val bank = lineStartWord.resize(3) + U(lane, 3 bits)
        inLine(lane) := bank < U(FetchPacket.Width, 3 bits)
      }
      inLine
    } else null
  val packetControl =
    if (fetchPacketEnabled) {
      val control = Vec(Bool(), FetchPacket.Width)
      for (lane <- 0 until FetchPacket.Width) {
        val majorOpcode = packetInstructions(lane)(31 downto 26).asUInt
        control(lane) := majorOpcode >= U(0x13, 6 bits) && majorOpcode <= U(0x1b, 6 bits)
      }
      control
    } else null

  val sequencePc =
    if (fetchPacketEnabled) {
      val lineSequencePc = UInt(32 bits)
      lineSequencePc := (fsPc | U(0x0f, 32 bits)) + 1
      for (lane <- (1 until FetchPacket.Width).reverse) {
        when(packetInLine(lane) && packetControl(lane)) {
          lineSequencePc := fsPc + U(lane * 4, 32 bits)
        }
      }
      when(packetControl(0)) {
        lineSequencePc := fsPc + 4
      }
      Mux(responseIsLine, lineSequencePc, fsPc + 4)
    } else {
      fsPc + 4
    }
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
  val fsReady = responseValid || fsExceptionAny
  val downstreamReady =
    if (fetchPacketEnabled) io.downstreamPacket.ready else io.downstream.ready
  val fsAllow = !fsValid || (fsReady && downstreamReady)
  val instructionRequest =
    ((fsAllow && !prefetchAlignmentException && !tlbLockPc) || flush || io.branchRepair) &&
      !(io.idleFlush || idleLock)
  val prefetchReady =
    (instructionRequest || prefetchAlignmentException) && io.instructionAddressAccepted
  val toFsValid = prefetchReady
  // When a complete line retires without a replacement request, retain the next packet address as
  // the request cursor. If a replacement was accepted, the normal fsPc update must instead bind the
  // outstanding response to that accepted address.
  val lineResponseConsumedWithoutReplacement =
    if (fetchPacketEnabled)
      responseIsLine && fsValid && downstreamReady && !flush && !toFsValid
    else False
  // A coincident sequential request can already be the authoritative redirect target. Remembering
  // that target in branchWaitTarget would issue it twice and duplicate its first instruction.
  val branchTargetAccepted =
    io.branchRepair && instructionRequest && io.instructionAddressAccepted && nextPc === io.branchTarget

  val scalarPayload = FetchPayload()
  scalarPayload.pc := fsPc
  scalarPayload.instruction := firstInstruction
  scalarPayload.exceptionCode :=
    tlbPrivilege.asBits ## tlbInvalid.asBits ## tlbRefill.asBits ## fsExceptionNumber.asBits
  scalarPayload.hasException := fsExceptionAny
  scalarPayload.instructionCacheMiss := io.instructionMiss
  scalarPayload.btbEnabled := btbEnabledLocked
  scalarPayload.btbTaken := btbTakenLocked
  scalarPayload.btbIndex := btbIndexLocked
  scalarPayload.btbTarget := btbTargetLocked

  if (fetchPacketEnabled) {
    io.downstreamPacket.valid := fsValid && fsReady
    io.downstreamPacket.payload.slotValid := 0
    var blockedByLaterControl: Bool = False
    for (lane <- 0 until FetchPacket.Width) {
      val validLineSlot =
        if (lane == 0) responseIsLine && packetInLine(lane)
        else
          responseIsLine && packetInLine(lane) && !fetchBtbTarget &&
          !blockedByLaterControl && !packetControl(lane)
      val validScalarSlot = if (lane == 0) !responseIsLine else False
      io.downstreamPacket.payload.slotValid(lane) := validLineSlot || validScalarSlot
      io.downstreamPacket.payload.slots(lane).fetch.pc :=
        (if (lane == 0) scalarPayload.pc else fsPc + U(lane * 4, 32 bits))
      io.downstreamPacket.payload.slots(lane).fetch.instruction := Mux(
        responseIsLine,
        packetInstructions(lane),
        (if (lane == 0) scalarPayload.instruction else firstInstruction)
      )
      io.downstreamPacket.payload.slots(lane).fetch.exceptionCode :=
        (if (lane == 0) scalarPayload.exceptionCode else B(0, 4 bits))
      io.downstreamPacket.payload.slots(lane).fetch.hasException :=
        (if (lane == 0) scalarPayload.hasException else False)
      io.downstreamPacket.payload.slots(lane).fetch.instructionCacheMiss :=
        (if (lane == 0) scalarPayload.instructionCacheMiss else False)
      io.downstreamPacket.payload.slots(lane).fetch.btbEnabled :=
        (if (lane == 0) scalarPayload.btbEnabled else False)
      io.downstreamPacket.payload.slots(lane).fetch.btbTaken :=
        (if (lane == 0) scalarPayload.btbTaken else False)
      io.downstreamPacket.payload.slots(lane).fetch.btbIndex :=
        (if (lane == 0) scalarPayload.btbIndex else U(0, 5 bits))
      io.downstreamPacket.payload.slots(lane).fetch.btbTarget :=
        (if (lane == 0) scalarPayload.btbTarget else U(0, 32 bits))
      if (lane == 0) {
        io.downstreamPacket.payload.slots(lane).direction := btbDirectionLocked
      } else {
        io.downstreamPacket.payload.slots(lane).direction.phtIndex := 0
        io.downstreamPacket.payload.slots(lane).direction.baseTaken := False
        io.downstreamPacket.payload.slots(lane).direction.localTaken := False
      }
      blockedByLaterControl = blockedByLaterControl || packetControl(lane)
    }
  } else {
    io.downstream.valid := fsValid && fsReady
    io.downstream.payload := scalarPayload
    io.directionPrediction := btbDirectionLocked
  }

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

  when((fsReady && downstreamReady) || flush) {
    instructionBufferValid := False
    if (fetchPacketEnabled) {
      instructionLineBufferValid := False
    }
  }.elsewhen(
    (if (fetchPacketEnabled) responseValid else io.instructionDataValid) && !downstreamReady
  ) {
    if (fetchPacketEnabled) {
      when(liveLineValid) {
        instructionLineBuffer := io.instructionLineData
        instructionLineBufferValid := True
        instructionBufferValid := False
      }.elsewhen(io.instructionDataValid) {
        instructionLineBufferValid := False
        instructionBuffer := io.instructionData
        instructionBufferValid := True
      }
    } else {
      instructionBuffer := io.instructionData
      instructionBufferValid := True
    }
  }

  when(flushDelay) {
    fsValid := False
  }.elsewhen(fsAllow) {
    fsValid := toFsValid
  }
  when(lineResponseConsumedWithoutReplacement) {
    // fsPc is the accepted-request PC. With no request in flight, keep it one word behind the next
    // packet address so the normal fsPc + 4 request expression retries that exact address.
    fsPc := (nextPc - U(4, 32 bits)).resized
    fsException := False
    fsExceptionNumber := False
  }.elsewhen(toFsValid && (fsAllow || flushDirty)) {
    fsPc := nextPc
    fsException := prefetchAlignmentException
    fsExceptionNumber := prefetchAlignmentException
  }
}
