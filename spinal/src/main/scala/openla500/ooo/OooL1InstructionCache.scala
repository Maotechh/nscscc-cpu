package openla500.ooo

import spinal.core._
import spinal.lib._

object OooL1InstructionCacheState extends SpinalEnum {
  val idle, lookup, refillRequest, refillData, install = newElement()
}

/** Blocking two-way 8-KiB L1 instruction cache with 64-byte lines.
  *
  * A killed request is allowed to finish its refill so a redirect back to the same line can hit,
  * but no response is emitted for the stale fetch group.
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

  val refillLine = Bits(OooCacheContract.LineBits bits)
  for (beat <- 0 until OooCacheContract.BeatsPerLine) {
    refillLine(beat * OooCacheContract.BeatBits + OooCacheContract.BeatBits - 1 downto
      beat * OooCacheContract.BeatBits) := refillBeats(beat)
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
  cacheArray.io.writeDirty := False
  cacheArray.io.invalidate := startInvalidate

  io.requestReady := state === OooL1InstructionCacheState.idle &&
    cacheArray.io.lookupReady && !invalidateRequest && !io.kill
  val requestFire = io.requestValid && io.requestReady
  when(requestFire) {
    request := io.request
    requestKilled := False
    cacheArray.io.lookupValid := True
    cacheArray.io.lookupAddress := io.request.physicalAddress
    state := OooL1InstructionCacheState.lookup
  }
  when((io.kill || newInvalidate) && state =/= OooL1InstructionCacheState.idle) {
    requestKilled := True
  }

  io.lineReadValid := state === OooL1InstructionCacheState.refillRequest
  io.lineRead.lineAddress := lineAddress(request.physicalAddress)
  io.lineRead.mshrId := 0
  io.lineReadBeatReady := state === OooL1InstructionCacheState.refillData &&
    io.lineReadBeat.mshrId === 0

  when(state === OooL1InstructionCacheState.lookup && cacheArray.io.responseValid) {
    when(cacheArray.io.hit) {
      when(!requestKilled && !io.kill) {
        responseValid := True
        response.virtualAddress := request.virtualAddress
        response.physicalAddress := request.physicalAddress
        response.instructions := selectFetchGroup(cacheArray.io.hitData, request.physicalAddress)
        response.error := False
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
    state := OooL1InstructionCacheState.refillData
  }

  val refillBeatFire = io.lineReadBeatValid && io.lineReadBeatReady
  when(refillBeatFire) {
    refillBeats(io.lineReadBeat.beat) := io.lineReadBeat.data
    refillError := refillError || io.lineReadBeat.error
    val nextMask = refillMask | UIntToOh(io.lineReadBeat.beat, OooCacheContract.BeatsPerLine)
    refillMask := nextMask
    when(nextMask.andR) { state := OooL1InstructionCacheState.install }
  }

  when(state === OooL1InstructionCacheState.install) {
    cacheArray.io.writeValid := True
    cacheArray.io.writeWay := victimWay
    cacheArray.io.writeData := refillLine
    cacheArray.io.writeDirty := False
    when(!requestKilled && !io.kill) {
      responseValid := True
      response.virtualAddress := request.virtualAddress
      response.physicalAddress := request.physicalAddress
      response.instructions := selectFetchGroup(refillLine, request.physicalAddress)
      response.error := refillError
    }
    state := OooL1InstructionCacheState.idle
  }

  io.invalidateBusy := cacheArray.io.invalidateBusy || invalidateRequest
}
