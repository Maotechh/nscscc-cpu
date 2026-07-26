package openla500.memory

import openla500.core._
import openla500.predict._
import spinal.core._
import spinal.lib._

object OooL1InstructionCacheState extends SpinalEnum {
  val idle, lookup, refillRequest, refillData, install = newElement()
}

/** Two-way 8-KiB L1 instruction cache with 64-byte lines.
  *
  * A killed request is allowed to finish its refill so a redirect back to the same line can hit,
  * but no response is emitted for the stale fetch group. Once the requested 16-byte group has
  * returned, another request to the line being refilled may take ownership without waiting for
  * installation; requests to a different line remain blocked.
  */
final class OooL1InstructionCache(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit
) extends Component {
  private val geometry = config.instructionCache
  private val wayWidth = log2Up(geometry.ways)
  private val indexWidth = geometry.indexWidth
  private val offsetWidth = geometry.offsetWidth
  private val fetchGroupBits = config.fetchWidth * 32
  private val fetchGroupBytes = fetchGroupBits / 8
  private val fetchGroupOffsetWidth = log2Up(fetchGroupBytes)

  require(geometry.capacityBytes == 8 * 1024)
  require(geometry.lineBytes == OooCacheContract.LineBytes)
  require(fetchGroupBytes == 16)
  require(geometry.lineBytes % fetchGroupBytes == 0)

  private def lineAddress(address: UInt): UInt =
    address & U(((BigInt(1) << config.xlen) - 1) ^ (geometry.lineBytes - 1), config.xlen bits)

  private def indexOf(address: UInt): UInt =
    address(offsetWidth + indexWidth - 1 downto offsetWidth)

  private def tagOf(address: UInt): UInt =
    address(config.xlen - 1 downto offsetWidth + indexWidth)

  private def selectFetchGroup(line: Bits, address: UInt): Vec[Bits] = {
    val group = Vec(Bits(32 bits), config.fetchWidth)
    val shift = (address(offsetWidth - 1 downto fetchGroupOffsetWidth) ##
      U(0, log2Up(fetchGroupBits) bits)).asUInt
    val selected = line |>> shift
    for (lane <- 0 until config.fetchWidth) {
      group(lane) := selected(lane * 32 + 31 downto lane * 32)
    }
    group
  }

  private def writeResponse(
      context: OooInstructionCacheRequest,
      group: Vec[Bits],
      error: Bool
  ): Unit = {
    val groupBase = context.virtualAddress &
      U(((BigInt(1) << config.xlen) - 1) ^ (fetchGroupBytes - 1), config.xlen bits)
    response.virtualAddress := context.virtualAddress
    response.physicalAddress := context.physicalAddress
    response.error := error
    for (lane <- 0 until config.fetchWidth) {
      response.instructions(lane) := group(lane)
      OooFetchPredecoder.drive(
        response.predecode(lane),
        config,
        groupBase + U(lane * 4, config.xlen bits),
        group(lane)
      )
    }
  }

  val io = new Bundle {
    val requestValid = in Bool ()
    val request = in(OooInstructionCacheRequest(config))
    val requestReady = out Bool ()
    val responseValid = out Bool ()
    val response = out(OooInstructionCacheResponse(config))
    val kill = in Bool ()

    val lineReadValid = out Bool ()
    val lineRead = out(OooLineReadRequest(config))
    val lineReadReady = in Bool ()
    val lineReadBeatValid = in Bool ()
    val lineReadBeat = in(OooLineReadBeat(config))
    val lineReadBeatReady = out Bool ()

    val invalidate = in Bool ()
    val invalidateBusy = out Bool ()
  }

  val cacheArray = new OooCacheArray(geometry)
  val state = RegInit(OooL1InstructionCacheState.idle)
  val invalidateSeen = RegInit(False)
  val invalidatePending = RegInit(False)
  val request = Reg(OooInstructionCacheRequest(config))
  val requestKilled = RegInit(False)
  val victimWay = Reg(UInt(wayWidth bits))
  val refillBeats = Vec.fill(OooCacheContract.BeatsPerLine)(
    Reg(Bits(OooCacheContract.BeatBits bits))
  )
  val refillMask = Reg(Bits(OooCacheContract.BeatsPerLine bits)) init (0)
  val refillError = RegInit(False)
  val refillResponseSent = RegInit(False)
  val refillReplayPending = RegInit(False)

  val refillLine = Bits(OooCacheContract.LineBits bits)
  for (beat <- 0 until OooCacheContract.BeatsPerLine) {
    refillLine(
      beat * OooCacheContract.BeatBits + OooCacheContract.BeatBits - 1 downto
        beat * OooCacheContract.BeatBits
    ) := refillBeats(beat)
  }

  val responseValid = RegInit(False)
  val response = Reg(OooInstructionCacheResponse(config))
  responseValid := False
  io.responseValid := responseValid
  io.response := response

  val newInvalidate = io.invalidate && !invalidateSeen
  when(io.invalidate) { invalidateSeen := True }.otherwise { invalidateSeen := False }
  val invalidateRequest = invalidatePending || newInvalidate
  val startInvalidate = invalidateRequest && state === OooL1InstructionCacheState.idle &&
    !cacheArray.io.invalidateBusy
  when(newInvalidate) { invalidatePending := True }
  when(startInvalidate) { invalidatePending := False }

  cacheArray.io.lookupValid := False
  cacheArray.io.lookupAddress := io.request.physicalAddress
  cacheArray.io.writeValid := False
  cacheArray.io.writeIndex := indexOf(request.physicalAddress)
  cacheArray.io.writeWay := victimWay
  cacheArray.io.writeTag := tagOf(request.physicalAddress)
  cacheArray.io.writeData := refillLine
  cacheArray.io.writeEntryValid := True
  cacheArray.io.writeDirty := False
  cacheArray.io.invalidate := startInvalidate
  cacheArray.io.maintenanceReadValid := False
  cacheArray.io.maintenanceReadIndex := 0
  cacheArray.io.maintenanceReadWay := 0

  val idleRequestReady = state === OooL1InstructionCacheState.idle &&
    cacheArray.io.lookupReady
  val refillSameLineReady = state === OooL1InstructionCacheState.refillData &&
    refillResponseSent && !refillReplayPending && !requestKilled && !io.request.uncached &&
    lineAddress(io.request.physicalAddress) === lineAddress(request.physicalAddress)
  io.requestReady := (idleRequestReady || refillSameLineReady) &&
    !invalidateRequest && !io.kill
  val requestFire = io.requestValid && io.requestReady
  val refillRequestFire = requestFire && refillSameLineReady
  when(requestFire) {
    request := io.request
    requestKilled := False
    when(refillRequestFire) {
      refillResponseSent := False
    }.otherwise {
      cacheArray.io.lookupValid := True
      cacheArray.io.lookupAddress := io.request.physicalAddress
      state := OooL1InstructionCacheState.lookup
    }
  }
  when((io.kill || newInvalidate) && state =/= OooL1InstructionCacheState.idle) {
    requestKilled := True
  }

  io.lineReadValid := state === OooL1InstructionCacheState.refillRequest
  io.lineRead.lineAddress := lineAddress(request.physicalAddress)
  io.lineRead.mshrId := 0
  io.lineRead.criticalBeat := U(0, OooCacheContract.BeatIndexWidth bits)
  io.lineReadBeatReady := state === OooL1InstructionCacheState.refillData &&
    io.lineReadBeat.mshrId === 0

  when(state === OooL1InstructionCacheState.lookup && cacheArray.io.responseValid) {
    when(cacheArray.io.hit) {
      when(!requestKilled && !io.kill) {
        responseValid := True
        writeResponse(
          request,
          selectFetchGroup(cacheArray.io.hitData, request.physicalAddress),
          False
        )
      }
      state := OooL1InstructionCacheState.idle
    }.otherwise {
      victimWay := cacheArray.io.victimWay
      state := OooL1InstructionCacheState.refillRequest
    }
  }

  when(state === OooL1InstructionCacheState.refillRequest && io.lineReadReady) {
    refillMask := 0
    refillError := False
    refillResponseSent := False
    state := OooL1InstructionCacheState.refillData
  }

  val refillBeatFire = io.lineReadBeatValid && io.lineReadBeatReady
  val refillLineWithAcceptedBeat = Bits(OooCacheContract.LineBits bits)
  for (beat <- 0 until OooCacheContract.BeatsPerLine) {
    refillLineWithAcceptedBeat(
      beat * OooCacheContract.BeatBits + OooCacheContract.BeatBits - 1 downto
        beat * OooCacheContract.BeatBits
    ) := Mux(
      refillBeatFire && io.lineReadBeat.beat === beat,
      io.lineReadBeat.data,
      refillBeats(beat)
    )
  }
  val requestedGroup = request.physicalAddress(offsetWidth - 1 downto fetchGroupOffsetWidth)
  val requestedBeatBase = (requestedGroup ## U(0, 1 bits)).asUInt
  val requestedBeatMask = (B(3, OooCacheContract.BeatsPerLine bits) |<< requestedBeatBase).resized
  val acceptedBeatMask = Mux(
    refillBeatFire,
    UIntToOh(io.lineReadBeat.beat, OooCacheContract.BeatsPerLine),
    B(0, OooCacheContract.BeatsPerLine bits)
  )
  val refillMaskWithAcceptedBeat = refillMask | acceptedBeatMask
  val refillRequestGroup =
    io.request.physicalAddress(offsetWidth - 1 downto fetchGroupOffsetWidth)
  val refillRequestBeatBase = (refillRequestGroup ## U(0, 1 bits)).asUInt
  val refillRequestBeatMask =
    (B(3, OooCacheContract.BeatsPerLine bits) |<< refillRequestBeatBase).resized
  val refillRequestGroupReady =
    (refillMaskWithAcceptedBeat & refillRequestBeatMask) === refillRequestBeatMask
  when(refillReplayPending) {
    refillReplayPending := False
    when(!requestKilled && !io.kill) {
      responseValid := True
      writeResponse(request, selectFetchGroup(refillLine, request.physicalAddress), refillError)
      refillResponseSent := True
    }
  }
  when(refillBeatFire) {
    refillBeats(io.lineReadBeat.beat) := io.lineReadBeat.data
    refillError := refillError || io.lineReadBeat.error
    refillMask := refillMaskWithAcceptedBeat
    val requestedGroupReady =
      (refillMaskWithAcceptedBeat & requestedBeatMask) === requestedBeatMask
    when(requestedGroupReady && !refillResponseSent && !requestKilled && !io.kill) {
      responseValid := True
      writeResponse(
        request,
        selectFetchGroup(refillLineWithAcceptedBeat, request.physicalAddress),
        refillError || io.lineReadBeat.error
      )
      refillResponseSent := True
    }
    when(refillMaskWithAcceptedBeat.andR) { state := OooL1InstructionCacheState.install }
  }
  when(refillRequestFire && refillRequestGroupReady) {
    refillReplayPending := True
    refillResponseSent := True
  }

  when(state === OooL1InstructionCacheState.install) {
    cacheArray.io.writeValid := True
    cacheArray.io.writeWay := victimWay
    cacheArray.io.writeData := refillLine
    cacheArray.io.writeEntryValid := True
    cacheArray.io.writeDirty := False
    when(!refillResponseSent && !requestKilled && !io.kill) {
      responseValid := True
      writeResponse(request, selectFetchGroup(refillLine, request.physicalAddress), refillError)
    }
    state := OooL1InstructionCacheState.idle
  }

  io.invalidateBusy := cacheArray.io.invalidateBusy || invalidateRequest
}
