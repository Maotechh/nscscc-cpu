package openla500.ooo

import spinal.core._
import spinal.lib._

object OooL1DataCacheState extends SpinalEnum {
  val idle, lookup, writeback, refillRequest, refillData, install = newElement()
}

/** Blocking reference controller for the 64-byte L1D data/tag arrays.
  *
  * The line interface already carries an MSHR id and accepts out-of-order refill beats. The first
  * integration uses id zero and one outstanding miss; the protocol can be widened to the four-entry
  * MSHR table without changing the cache-line geometry or refill/writeback payloads.
  */
final class OooL1DataCache(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private val geometry = config.dataCache
  private val wayWidth = log2Up(geometry.ways)
  private val indexWidth = geometry.indexWidth
  private val offsetWidth = geometry.offsetWidth
  private val tagWidth = geometry.tagWidth

  require(geometry.lineBytes == OooCacheContract.LineBytes)
  require(OooCacheContract.BeatsPerLine == 8)

  private def lineAddress(address: UInt): UInt = {
    address & U(((BigInt(1) << config.xlen) - 1) ^ (geometry.lineBytes - 1), config.xlen bits)
  }

  private def indexOf(address: UInt): UInt =
    address(offsetWidth + indexWidth - 1 downto offsetWidth)

  private def tagOf(address: UInt): UInt =
    address(config.xlen - 1 downto offsetWidth + indexWidth)

  private def wordShift(address: UInt): UInt =
    (address(offsetWidth - 1 downto 2) ## U(0, 5 bits)).asUInt

  private def selectWord(line: Bits, address: UInt): Bits =
    (line |>> wordShift(address))(config.xlen - 1 downto 0)

  private def mergeStore(line: Bits, request: OooCacheRequest): Bits = {
    val wordMask = Bits(config.xlen bits)
    for (byte <- 0 until config.xlen / 8) {
      wordMask(byte * 8 + 7 downto byte * 8) := B(0xff, 8 bits).andMask(request.byteMask(byte))
    }
    val shift = wordShift(request.physicalAddress)
    val lineMask = wordMask.resize(OooCacheContract.LineBits) |<< shift
    val lineData = request.writeData.resize(OooCacheContract.LineBits) |<< shift
    (line & ~lineMask) | (lineData & lineMask)
  }

  val io = new Bundle {
    val requestValid = in Bool ()
    val request = in(OooCacheRequest(config))
    val requestReady = out Bool ()
    val responseValid = out Bool ()
    val response = out(OooCacheResponse(config))

    val lineReadValid = out Bool ()
    val lineRead = out(OooLineReadRequest(config))
    val lineReadReady = in Bool ()
    val lineReadBeatValid = in Bool ()
    val lineReadBeat = in(OooLineReadBeat(config))
    val lineReadBeatReady = out Bool ()

    val lineWriteValid = out Bool ()
    val lineWrite = out(OooLineWriteRequest(config))
    val lineWriteReady = in Bool ()

    val invalidate = in Bool ()
    val invalidateBusy = out Bool ()
  }

  val cacheArray = new OooCacheArray(geometry)
  val state = RegInit(OooL1DataCacheState.idle)
  val request = Reg(OooCacheRequest(config))
  val victimWay = Reg(UInt(wayWidth bits))
  val victimAddress = Reg(UInt(config.xlen bits))
  val victimData = Reg(Bits(OooCacheContract.LineBits bits))
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
  val installedLine = mergeStore(refillLine, request)
  val hitStoreLine = mergeStore(cacheArray.io.hitData, request)

  val responseValid = RegInit(False)
  val response = Reg(OooCacheResponse(config))
  responseValid := False
  io.responseValid := responseValid
  io.response := response

  cacheArray.io.lookupValid := False
  cacheArray.io.lookupAddress := io.request.physicalAddress
  cacheArray.io.writeValid := False
  cacheArray.io.writeIndex := indexOf(request.physicalAddress)
  cacheArray.io.writeWay := victimWay
  cacheArray.io.writeTag := tagOf(request.physicalAddress)
  cacheArray.io.writeData := installedLine
  cacheArray.io.writeDirty := request.isWrite
  cacheArray.io.invalidate := io.invalidate && state === OooL1DataCacheState.idle

  io.requestReady := state === OooL1DataCacheState.idle && cacheArray.io.lookupReady &&
    !io.invalidate && !io.request.uncached
  val requestFire = io.requestValid && io.requestReady
  when(requestFire) {
    request := io.request
    cacheArray.io.lookupValid := True
    cacheArray.io.lookupAddress := io.request.physicalAddress
    state := OooL1DataCacheState.lookup
  }

  io.lineReadValid := state === OooL1DataCacheState.refillRequest
  io.lineRead.lineAddress := lineAddress(request.physicalAddress)
  io.lineRead.mshrId := 0
  io.lineReadBeatReady := state === OooL1DataCacheState.refillData &&
    io.lineReadBeat.mshrId === 0
  io.lineWriteValid := state === OooL1DataCacheState.writeback
  io.lineWrite.lineAddress := victimAddress
  io.lineWrite.data := victimData
  io.lineWrite.byteMask := B((BigInt(1) << OooCacheContract.LineBytes) - 1,
    OooCacheContract.LineBytes bits)
  io.lineWrite.mshrId := 0

  when(state === OooL1DataCacheState.lookup && cacheArray.io.responseValid) {
    when(cacheArray.io.hit) {
      when(request.isWrite) {
        cacheArray.io.writeValid := True
        cacheArray.io.writeWay := cacheArray.io.hitWay
        cacheArray.io.writeData := hitStoreLine
        cacheArray.io.writeDirty := True
      }.otherwise {
        responseValid := True
        response.robPointer := request.robPointer
        response.pdst := request.pdst
        response.data := selectWord(cacheArray.io.hitData, request.physicalAddress)
        response.error := False
      }
      state := OooL1DataCacheState.idle
    }.otherwise {
      victimWay := cacheArray.io.victimWay
      victimAddress := cacheArray.io.victimAddress
      victimData := cacheArray.io.victimData
      when(cacheArray.io.victimValid && cacheArray.io.victimDirty) {
        state := OooL1DataCacheState.writeback
      }.otherwise {
        state := OooL1DataCacheState.refillRequest
      }
    }
  }

  when(state === OooL1DataCacheState.writeback && io.lineWriteReady) {
    state := OooL1DataCacheState.refillRequest
  }

  when(state === OooL1DataCacheState.refillRequest && io.lineReadReady) {
    refillMask := 0
    refillError := False
    state := OooL1DataCacheState.refillData
  }

  val refillBeatFire = io.lineReadBeatValid && io.lineReadBeatReady
  when(refillBeatFire) {
    refillBeats(io.lineReadBeat.beat) := io.lineReadBeat.data
    refillError := refillError || io.lineReadBeat.error
    val nextMask = refillMask | UIntToOh(
      io.lineReadBeat.beat,
      OooCacheContract.BeatsPerLine
    )
    refillMask := nextMask
    when(nextMask.andR) { state := OooL1DataCacheState.install }
  }

  when(state === OooL1DataCacheState.install) {
    cacheArray.io.writeValid := True
    cacheArray.io.writeWay := victimWay
    cacheArray.io.writeData := Mux(request.isWrite, installedLine, refillLine)
    cacheArray.io.writeDirty := request.isWrite
    when(!request.isWrite) {
      responseValid := True
      response.robPointer := request.robPointer
      response.pdst := request.pdst
      response.data := selectWord(refillLine, request.physicalAddress)
      response.error := refillError
    }
    state := OooL1DataCacheState.idle
  }

  io.invalidateBusy := cacheArray.io.invalidateBusy ||
    (io.invalidate && state =/= OooL1DataCacheState.idle)
}
