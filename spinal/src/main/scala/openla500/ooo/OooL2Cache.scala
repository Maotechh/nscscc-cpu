package openla500.ooo

import spinal.core._
import spinal.lib._

object OooL2CacheState extends SpinalEnum {
  val idle, lookup, writeback, refillRequest, refillData, installRead, installWrite, returnData =
    newElement()
}

/** Blocking 64-KiB L2 controller used to establish the complete 64-byte line hierarchy.
  *
  * Requests carry their L1 MSHR id through hit and refill paths. The downstream memory side uses
  * id zero until arbitration is widened for concurrent L1I/L1D misses.
  */
final class OooL2Cache(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private val geometry = config.level2Cache
  private val wayWidth = log2Up(geometry.ways)
  private val indexWidth = geometry.indexWidth
  private val offsetWidth = geometry.offsetWidth

  require(geometry.capacityBytes == 64 * 1024)
  require(geometry.lineBytes == OooCacheContract.LineBytes)

  private def lineAddress(address: UInt): UInt =
    address & U(((BigInt(1) << config.xlen) - 1) ^ (geometry.lineBytes - 1), config.xlen bits)

  private def indexOf(address: UInt): UInt =
    address(offsetWidth + indexWidth - 1 downto offsetWidth)

  private def tagOf(address: UInt): UInt =
    address(config.xlen - 1 downto offsetWidth + indexWidth)

  val io = new Bundle {
    val readValid = in Bool ()
    val read = in(OooLineReadRequest(config))
    val readReady = out Bool ()
    val readBeatValid = out Bool ()
    val readBeat = out(OooLineReadBeat(config))
    val readBeatReady = in Bool ()

    val writeValid = in Bool ()
    val write = in(OooLineWriteRequest(config))
    val writeReady = out Bool ()

    val memoryReadValid = out Bool ()
    val memoryRead = out(OooLineReadRequest(config))
    val memoryReadReady = in Bool ()
    val memoryReadBeatValid = in Bool ()
    val memoryReadBeat = in(OooLineReadBeat(config))
    val memoryReadBeatReady = out Bool ()

    val memoryWriteValid = out Bool ()
    val memoryWrite = out(OooLineWriteRequest(config))
    val memoryWriteReady = in Bool ()

    val invalidate = in Bool ()
    val invalidateBusy = out Bool ()
  }

  val cacheArray = new OooCacheArray(geometry)
  val state = RegInit(OooL2CacheState.idle)
  val pendingAddress = Reg(UInt(config.xlen bits))
  val pendingMshrId = Reg(UInt(log2Up(config.mshrEntries) bits))
  val pendingIsWrite = RegInit(False)
  val pendingWriteData = Reg(Bits(OooCacheContract.LineBits bits))
  val victimWay = Reg(UInt(wayWidth bits))
  val victimAddress = Reg(UInt(config.xlen bits))
  val victimData = Reg(Bits(OooCacheContract.LineBits bits))
  val refillBeats = Vec.fill(OooCacheContract.BeatsPerLine)(
    Reg(Bits(OooCacheContract.BeatBits bits))
  )
  val refillMask = Reg(Bits(OooCacheContract.BeatsPerLine bits)) init (0)
  val refillError = RegInit(False)
  val returnLine = Reg(Bits(OooCacheContract.LineBits bits))
  val returnError = RegInit(False)
  val returnBeat = Reg(UInt(OooCacheContract.BeatIndexWidth bits)) init (0)

  val refillLine = Bits(OooCacheContract.LineBits bits)
  for (beat <- 0 until OooCacheContract.BeatsPerLine) {
    refillLine(beat * OooCacheContract.BeatBits + OooCacheContract.BeatBits - 1 downto
      beat * OooCacheContract.BeatBits) := refillBeats(beat)
  }

  cacheArray.io.lookupValid := False
  cacheArray.io.lookupAddress := pendingAddress
  cacheArray.io.writeValid := False
  cacheArray.io.writeIndex := indexOf(pendingAddress)
  cacheArray.io.writeWay := victimWay
  cacheArray.io.writeTag := tagOf(pendingAddress)
  cacheArray.io.writeData := refillLine
  cacheArray.io.writeDirty := False
  cacheArray.io.invalidate := io.invalidate && state === OooL2CacheState.idle

  io.readReady := state === OooL2CacheState.idle && cacheArray.io.lookupReady &&
    !io.invalidate
  io.writeReady := state === OooL2CacheState.idle && cacheArray.io.lookupReady &&
    !io.invalidate && !io.readValid && io.write.byteMask.andR
  val readFire = io.readValid && io.readReady
  val writeFire = io.writeValid && io.writeReady
  when(readFire) {
    pendingAddress := lineAddress(io.read.lineAddress)
    pendingMshrId := io.read.mshrId
    pendingIsWrite := False
    cacheArray.io.lookupValid := True
    cacheArray.io.lookupAddress := io.read.lineAddress
    state := OooL2CacheState.lookup
  }.elsewhen(writeFire) {
    pendingAddress := lineAddress(io.write.lineAddress)
    pendingMshrId := io.write.mshrId
    pendingIsWrite := True
    pendingWriteData := io.write.data
    cacheArray.io.lookupValid := True
    cacheArray.io.lookupAddress := io.write.lineAddress
    state := OooL2CacheState.lookup
  }

  io.memoryWriteValid := state === OooL2CacheState.writeback
  io.memoryWrite.lineAddress := victimAddress
  io.memoryWrite.data := victimData
  io.memoryWrite.byteMask := B((BigInt(1) << OooCacheContract.LineBytes) - 1,
    OooCacheContract.LineBytes bits)
  io.memoryWrite.mshrId := 0
  io.memoryReadValid := state === OooL2CacheState.refillRequest
  io.memoryRead.lineAddress := pendingAddress
  io.memoryRead.mshrId := 0
  io.memoryReadBeatReady := state === OooL2CacheState.refillData &&
    io.memoryReadBeat.mshrId === 0

  io.readBeatValid := state === OooL2CacheState.returnData
  io.readBeat.mshrId := pendingMshrId
  io.readBeat.beat := returnBeat
  val returnShift = (returnBeat ## U(0, 6 bits)).asUInt
  io.readBeat.data := (returnLine |>> returnShift)(OooCacheContract.BeatBits - 1 downto 0)
  io.readBeat.last := returnBeat === OooCacheContract.BeatsPerLine - 1
  io.readBeat.error := returnError

  when(state === OooL2CacheState.lookup && cacheArray.io.responseValid) {
    when(cacheArray.io.hit) {
      when(pendingIsWrite) {
        cacheArray.io.writeValid := True
        cacheArray.io.writeWay := cacheArray.io.hitWay
        cacheArray.io.writeData := pendingWriteData
        cacheArray.io.writeDirty := True
        state := OooL2CacheState.idle
      }.otherwise {
        returnLine := cacheArray.io.hitData
        returnError := False
        returnBeat := 0
        state := OooL2CacheState.returnData
      }
    }.otherwise {
      victimWay := cacheArray.io.victimWay
      victimAddress := cacheArray.io.victimAddress
      victimData := cacheArray.io.victimData
      when(cacheArray.io.victimValid && cacheArray.io.victimDirty) {
        state := OooL2CacheState.writeback
      }.elsewhen(pendingIsWrite) {
        state := OooL2CacheState.installWrite
      }.otherwise {
        state := OooL2CacheState.refillRequest
      }
    }
  }

  when(state === OooL2CacheState.writeback && io.memoryWriteReady) {
    state := Mux(
      pendingIsWrite,
      OooL2CacheState.installWrite,
      OooL2CacheState.refillRequest
    )
  }

  when(state === OooL2CacheState.refillRequest && io.memoryReadReady) {
    refillMask := 0
    refillError := False
    state := OooL2CacheState.refillData
  }

  val memoryBeatFire = io.memoryReadBeatValid && io.memoryReadBeatReady
  when(memoryBeatFire) {
    refillBeats(io.memoryReadBeat.beat) := io.memoryReadBeat.data
    refillError := refillError || io.memoryReadBeat.error
    val nextMask = refillMask | UIntToOh(
      io.memoryReadBeat.beat,
      OooCacheContract.BeatsPerLine
    )
    refillMask := nextMask
    when(nextMask.andR) { state := OooL2CacheState.installRead }
  }

  when(state === OooL2CacheState.installRead) {
    cacheArray.io.writeValid := True
    cacheArray.io.writeWay := victimWay
    cacheArray.io.writeData := refillLine
    cacheArray.io.writeDirty := False
    returnLine := refillLine
    returnError := refillError
    returnBeat := 0
    state := OooL2CacheState.returnData
  }

  when(state === OooL2CacheState.installWrite) {
    cacheArray.io.writeValid := True
    cacheArray.io.writeWay := victimWay
    cacheArray.io.writeData := pendingWriteData
    cacheArray.io.writeDirty := True
    state := OooL2CacheState.idle
  }

  val returnFire = io.readBeatValid && io.readBeatReady
  when(returnFire) {
    when(io.readBeat.last) {
      state := OooL2CacheState.idle
    }.otherwise {
      returnBeat := returnBeat + 1
    }
  }

  io.invalidateBusy := cacheArray.io.invalidateBusy ||
    (io.invalidate && state =/= OooL2CacheState.idle)
}
