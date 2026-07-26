package openla500.memory

import openla500.core._
import spinal.core._
import spinal.lib._

object OooL2CacheState extends SpinalEnum {
  val normal, maintenanceLookup, maintenanceWriteback, maintenanceInvalidate = newElement()
}

/** Nonblocking 64-KiB shared L2 indexed by the hierarchy-global MSHR identity.
  *
  * Different sets may be looked up and refilled concurrently. Same-set requests are held above L2
  * until the active owner installs, which prevents two MSHRs from selecting one physical victim.
  */
final class OooL2Cache(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private val geometry = config.level2Cache
  private val wayWidth = log2Up(geometry.ways)
  private val indexWidth = geometry.indexWidth
  private val offsetWidth = geometry.offsetWidth
  private val mshrIdWidth = log2Up(config.mshrEntries)

  require(geometry.capacityBytes == 64 * 1024)
  require(geometry.lineBytes == OooCacheContract.LineBytes)

  private def lineAddress(address: UInt): UInt =
    address & U(((BigInt(1) << config.xlen) - 1) ^ (geometry.lineBytes - 1), config.xlen bits)

  private def indexOf(address: UInt): UInt =
    address(offsetWidth + indexWidth - 1 downto offsetWidth)

  private def tagOf(address: UInt): UInt =
    address(config.xlen - 1 downto offsetWidth + indexWidth)

  private def selectLowest(mask: Bits, count: Int): UInt = {
    val selected = UInt(log2Up(count) bits)
    selected := 0
    for (index <- (0 until count).reverse) {
      when(mask(index)) { selected := U(index, log2Up(count) bits) }
    }
    selected
  }

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
    val writebackInvalidate = in Bool ()
    val invalidateBusy = out Bool ()
  }

  val cacheArray = new OooCacheArray(geometry)
  val state = RegInit(OooL2CacheState.normal)
  val misses = Vec.fill(config.mshrEntries)(Reg(OooL2Mshr(config)))
  val lineMemories = Array.fill(OooCacheContract.BeatsPerLine)(
    Mem(Bits(OooCacheContract.BeatBits bits), config.mshrEntries)
  )
  val missVictimData = Reg(Bits(OooCacheContract.LineBits bits))
  for (entry <- misses) {
    entry.valid.init(False)
    entry.state.init(OooL2MshrState.readRequest)
  }

  val lookupPending = RegInit(False)
  val lookupIsWrite = RegInit(False)
  val lookupMshrId = Reg(UInt(mshrIdWidth bits))
  val lookupAddress = Reg(UInt(config.xlen bits))
  val lookupCriticalBeat = Reg(UInt(OooCacheContract.BeatIndexWidth bits))

  val writeState = RegInit(OooL2WriteState.idle)
  val writeAddress = Reg(UInt(config.xlen bits))
  val writeMshrId = Reg(UInt(mshrIdWidth bits))
  val writeData = Reg(Bits(OooCacheContract.LineBits bits))
  val writeWay = Reg(UInt(wayWidth bits))
  val writeVictimAddress = Reg(UInt(config.xlen bits))
  val writeVictimData = Reg(Bits(OooCacheContract.LineBits bits))

  val invalidateSeen = RegInit(False)
  val invalidatePending = RegInit(False)
  val writebackInvalidateSeen = RegInit(False)
  val writebackInvalidatePending = RegInit(False)
  val maintenanceIndex = Reg(UInt(indexWidth bits)) init (0)
  val maintenanceWay = Reg(UInt(wayWidth bits)) init (0)
  val maintenanceVictimAddress = Reg(UInt(config.xlen bits))
  val maintenanceVictimData = Reg(Bits(OooCacheContract.LineBits bits))

  val newInvalidate = io.invalidate && !invalidateSeen
  when(io.invalidate) { invalidateSeen := True }.otherwise { invalidateSeen := False }
  when(newInvalidate) { invalidatePending := True }
  val newWritebackInvalidate = io.writebackInvalidate && !writebackInvalidateSeen
  when(io.writebackInvalidate) { writebackInvalidateSeen := True }
    .otherwise { writebackInvalidateSeen := False }
  when(newWritebackInvalidate) { writebackInvalidatePending := True }

  val activeMissMask = Bits(config.mshrEntries bits)
  for (entry <- 0 until config.mshrEntries) {
    activeMissMask(entry) := misses(entry).valid
  }
  val normalBusy = lookupPending || activeMissMask.orR ||
    writeState =/= OooL2WriteState.idle
  val maintenanceRequest = invalidatePending || newInvalidate ||
    writebackInvalidatePending || newWritebackInvalidate
  val startInvalidate = (invalidatePending || newInvalidate) && !normalBusy &&
    state === OooL2CacheState.normal && !cacheArray.io.invalidateBusy
  val startWritebackInvalidate = (writebackInvalidatePending || newWritebackInvalidate) &&
    !normalBusy && state === OooL2CacheState.normal &&
    !(invalidatePending || newInvalidate) && !cacheArray.io.invalidateBusy
  when(startInvalidate) { invalidatePending := False }
  when(startWritebackInvalidate) {
    writebackInvalidatePending := False
    maintenanceIndex := 0
    maintenanceWay := 0
    state := OooL2CacheState.maintenanceLookup
  }

  val installMask = Bits(config.mshrEntries bits)
  val missWritebackMask = Bits(config.mshrEntries bits)
  val readRequestMask = Bits(config.mshrEntries bits)
  val hitResponseMask = Bits(config.mshrEntries bits)
  for (entry <- 0 until config.mshrEntries) {
    installMask(entry) := misses(entry).valid && misses(entry).state === OooL2MshrState.install
    missWritebackMask(entry) := misses(entry).valid &&
      misses(entry).state === OooL2MshrState.writeback
    readRequestMask(entry) := misses(entry).valid &&
      misses(entry).state === OooL2MshrState.readRequest
    hitResponseMask(entry) := misses(entry).valid &&
      misses(entry).state === OooL2MshrState.respond
  }

  val readSetConflict = Bits(config.mshrEntries bits)
  val writeSetConflict = Bits(config.mshrEntries bits)
  for (entry <- 0 until config.mshrEntries) {
    readSetConflict(entry) := misses(entry).valid &&
      indexOf(misses(entry).lineAddress) === indexOf(io.read.lineAddress)
    writeSetConflict(entry) := misses(entry).valid &&
      indexOf(misses(entry).lineAddress) === indexOf(io.write.lineAddress)
  }
  val writeContextConflictsRead = writeState =/= OooL2WriteState.idle &&
    indexOf(writeAddress) === indexOf(io.read.lineAddress)
  val canStartLookup = state === OooL2CacheState.normal && !maintenanceRequest &&
    !cacheArray.io.invalidateBusy && !lookupPending && !installMask.orR &&
    !missWritebackMask.orR && writeState =/= OooL2WriteState.install &&
    cacheArray.io.lookupReady

  io.readReady := canStartLookup && !misses(io.read.mshrId).valid &&
    !readSetConflict.orR && !writeContextConflictsRead
  io.writeReady := canStartLookup && writeState === OooL2WriteState.idle &&
    !io.readValid && !writeSetConflict.orR && io.write.byteMask.andR
  val readFire = io.readValid && io.readReady
  val writeFire = io.writeValid && io.writeReady

  cacheArray.io.lookupValid := readFire || writeFire
  cacheArray.io.lookupAddress := Mux(readFire, io.read.lineAddress, io.write.lineAddress)
  cacheArray.io.writeValid := False
  cacheArray.io.writeIndex := 0
  cacheArray.io.writeWay := 0
  cacheArray.io.writeTag := 0
  cacheArray.io.writeData := 0
  cacheArray.io.writeEntryValid := True
  cacheArray.io.writeDirty := False
  cacheArray.io.invalidate := startInvalidate
  cacheArray.io.maintenanceReadValid := state === OooL2CacheState.maintenanceLookup
  cacheArray.io.maintenanceReadIndex := maintenanceIndex
  cacheArray.io.maintenanceReadWay := maintenanceWay

  when(readFire) {
    lookupPending := True
    lookupIsWrite := False
    lookupMshrId := io.read.mshrId
    lookupAddress := lineAddress(io.read.lineAddress)
    lookupCriticalBeat := io.read.criticalBeat
  }.elsewhen(writeFire) {
    lookupPending := True
    lookupIsWrite := True
    lookupMshrId := io.write.mshrId
    lookupAddress := lineAddress(io.write.lineAddress)
    writeState := OooL2WriteState.lookup
    writeAddress := lineAddress(io.write.lineAddress)
    writeMshrId := io.write.mshrId
    writeData := io.write.data
  }

  val lookupResponse = lookupPending && cacheArray.io.responseValid
  when(lookupResponse) {
    lookupPending := False
    when(lookupIsWrite) {
      writeWay := Mux(cacheArray.io.hit, cacheArray.io.hitWay, cacheArray.io.victimWay)
      writeVictimAddress := cacheArray.io.victimAddress
      writeVictimData := cacheArray.io.victimData
      writeState := Mux(
        !cacheArray.io.hit && cacheArray.io.victimValid && cacheArray.io.victimDirty,
        OooL2WriteState.victimWriteback,
        OooL2WriteState.writeThrough
      )
    }.otherwise {
      val entry = misses(lookupMshrId)
      entry.valid := True
      entry.lineAddress := lookupAddress
      entry.criticalBeat := lookupCriticalBeat
      entry.returnBeat := lookupCriticalBeat
      entry.returnCount := U(0, OooCacheContract.BeatIndexWidth bits)
      entry.error := False
      entry.refillMask := B(0, OooCacheContract.BeatsPerLine bits)
      when(cacheArray.io.hit) {
        entry.state := OooL2MshrState.respond
      }.otherwise {
        entry.victimWay := cacheArray.io.victimWay
        entry.victimAddress := cacheArray.io.victimAddress
        entry.state := Mux(
          cacheArray.io.victimValid && cacheArray.io.victimDirty,
          OooL2MshrState.writeback,
          OooL2MshrState.readRequest
        )
        when(cacheArray.io.victimValid && cacheArray.io.victimDirty) {
          missVictimData := cacheArray.io.victimData
        }
      }
    }
  }

  val captureHitLine = lookupResponse && !lookupIsWrite && cacheArray.io.hit
  val hitCaptureValid = RegInit(False)
  val hitCaptureMshrId = Reg(UInt(mshrIdWidth bits))
  val hitCaptureData = Reg(Bits(OooCacheContract.LineBits bits))
  when(hitCaptureValid) { hitCaptureValid := False }
  when(captureHitLine) {
    hitCaptureValid := True
    hitCaptureMshrId := lookupMshrId
    hitCaptureData := cacheArray.io.hitData
  }

  val missWritebackId = selectLowest(missWritebackMask, config.mshrEntries)
  io.memoryWriteValid := False
  io.memoryWrite.lineAddress := misses(missWritebackId).victimAddress
  io.memoryWrite.data := missVictimData
  io.memoryWrite.byteMask := B(
    (BigInt(1) << OooCacheContract.LineBytes) - 1,
    OooCacheContract.LineBytes bits
  )
  io.memoryWrite.mshrId := missWritebackId
  when(state === OooL2CacheState.normal) {
    when(writeState === OooL2WriteState.victimWriteback) {
      io.memoryWriteValid := True
      io.memoryWrite.lineAddress := writeVictimAddress
      io.memoryWrite.data := writeVictimData
      io.memoryWrite.mshrId := writeMshrId
    }.elsewhen(writeState === OooL2WriteState.writeThrough) {
      io.memoryWriteValid := True
      io.memoryWrite.lineAddress := writeAddress
      io.memoryWrite.data := writeData
      io.memoryWrite.mshrId := writeMshrId
    }.otherwise {
      io.memoryWriteValid := missWritebackMask.orR
    }
  }
  when(state === OooL2CacheState.maintenanceWriteback) {
    io.memoryWriteValid := True
    io.memoryWrite.lineAddress := maintenanceVictimAddress
    io.memoryWrite.data := maintenanceVictimData
    io.memoryWrite.mshrId := 0
  }
  val memoryWriteFire = io.memoryWriteValid && io.memoryWriteReady
  when(state === OooL2CacheState.normal && memoryWriteFire) {
    when(writeState === OooL2WriteState.victimWriteback) {
      writeState := OooL2WriteState.writeThrough
    }.elsewhen(writeState === OooL2WriteState.writeThrough) {
      writeState := OooL2WriteState.install
    }.otherwise {
      misses(missWritebackId).state := OooL2MshrState.readRequest
    }
  }

  val readRequestId = selectLowest(readRequestMask, config.mshrEntries)
  io.memoryReadValid := state === OooL2CacheState.normal && readRequestMask.orR
  io.memoryRead.lineAddress := misses(readRequestId).lineAddress
  io.memoryRead.mshrId := readRequestId
  io.memoryRead.criticalBeat := misses(readRequestId).criticalBeat
  val memoryReadFire = io.memoryReadValid && io.memoryReadReady
  when(memoryReadFire) {
    misses(readRequestId).state := OooL2MshrState.refill
    misses(readRequestId).refillMask := B(0, OooCacheContract.BeatsPerLine bits)
    misses(readRequestId).error := False
  }

  val memoryResponseId = io.memoryReadBeat.mshrId
  val eligibleHitResponseMask = Bits(config.mshrEntries bits)
  for (entry <- 0 until config.mshrEntries) {
    eligibleHitResponseMask(entry) := hitResponseMask(entry) &&
      !(hitCaptureValid && hitCaptureMshrId === U(entry, mshrIdWidth bits))
  }
  val hitResponseId = selectLowest(eligibleHitResponseMask, config.mshrEntries)
  val hitResponseBeats = Vec(Bits(OooCacheContract.BeatBits bits), OooCacheContract.BeatsPerLine)
  for (beat <- 0 until OooCacheContract.BeatsPerLine) {
    hitResponseBeats(beat) := lineMemories(beat).readAsync(hitResponseId)
  }

  // Only cache hits need a register boundary: external beats already leave the AXI bridge from
  // a registered output.  The hit stage retires and replaces one beat in the same cycle, keeping
  // full line bandwidth without adding another cycle to critical-word-first memory refills.
  val hitOutputValid = RegInit(False)
  val hitOutput = Reg(OooLineReadBeat(config))
  val streamingRefillBeat = io.memoryReadBeatValid && !hitCaptureValid
  io.readBeatValid := streamingRefillBeat || hitOutputValid
  io.readBeat := hitOutput
  when(streamingRefillBeat) { io.readBeat := io.memoryReadBeat }

  val streamingRefillFire = streamingRefillBeat && io.readBeatReady
  val hitOutputFire = !streamingRefillBeat && hitOutputValid && io.readBeatReady
  val hitOutputReady = !hitOutputValid || hitOutputFire
  val hitResponseLoad = eligibleHitResponseMask.orR && hitOutputReady
  when(hitOutputReady) {
    hitOutputValid := eligibleHitResponseMask.orR
    when(eligibleHitResponseMask.orR) {
      hitOutput.mshrId := hitResponseId
      hitOutput.beat := misses(hitResponseId).returnBeat
      hitOutput.data := hitResponseBeats(misses(hitResponseId).returnBeat)
      hitOutput.last := misses(hitResponseId).returnCount ===
        OooCacheContract.BeatsPerLine - 1
      hitOutput.error := misses(hitResponseId).error
    }
  }

  // A registered hit capture writes all eight shallow banks and therefore backpressures an
  // external refill for one cycle. External traffic otherwise has priority over a buffered hit.
  io.memoryReadBeatReady := !hitCaptureValid && io.readBeatReady

  // A hit captures all banks in parallel. A simultaneous external refill is backpressured for
  // that cycle, keeping each shallow memory bank single-write while preserving four line IDs.
  for (beat <- 0 until OooCacheContract.BeatsPerLine) {
    val refillSelect = streamingRefillFire &&
      io.memoryReadBeat.beat === U(beat, OooCacheContract.BeatIndexWidth bits)
    lineMemories(beat).write(
      address = Mux(refillSelect, memoryResponseId, hitCaptureMshrId),
      data = Mux(
        refillSelect,
        io.memoryReadBeat.data,
        hitCaptureData(
          beat * OooCacheContract.BeatBits + OooCacheContract.BeatBits - 1 downto
            beat * OooCacheContract.BeatBits
        )
      ),
      enable = refillSelect || hitCaptureValid
    )
  }

  when(streamingRefillFire) {
    val entry = misses(memoryResponseId)
    entry.error := entry.error || io.memoryReadBeat.error
    val nextMask = entry.refillMask | UIntToOh(
      io.memoryReadBeat.beat,
      OooCacheContract.BeatsPerLine
    )
    entry.refillMask := nextMask
    when(nextMask.andR) { entry.state := OooL2MshrState.install }
  }
  when(hitResponseLoad) {
    when(misses(hitResponseId).returnCount === OooCacheContract.BeatsPerLine - 1) {
      misses(hitResponseId).valid := False
    }.otherwise {
      misses(hitResponseId).returnBeat := misses(hitResponseId).returnBeat + 1
      misses(hitResponseId).returnCount := misses(hitResponseId).returnCount + 1
    }
  }

  val installId = selectLowest(installMask, config.mshrEntries)
  val installLine = Bits(OooCacheContract.LineBits bits)
  for (beat <- 0 until OooCacheContract.BeatsPerLine) {
    installLine(
      beat * OooCacheContract.BeatBits + OooCacheContract.BeatBits - 1 downto
        beat * OooCacheContract.BeatBits
    ) := lineMemories(beat).readAsync(installId)
  }
  val writeInstall = state === OooL2CacheState.normal &&
    writeState === OooL2WriteState.install && !lookupResponse
  val missInstall = state === OooL2CacheState.normal && installMask.orR &&
    !writeInstall && !lookupResponse
  when(writeInstall) {
    cacheArray.io.writeValid := True
    cacheArray.io.writeIndex := indexOf(writeAddress)
    cacheArray.io.writeWay := writeWay
    cacheArray.io.writeTag := tagOf(writeAddress)
    cacheArray.io.writeData := writeData
    cacheArray.io.writeEntryValid := True
    cacheArray.io.writeDirty := False
    writeState := OooL2WriteState.idle
  }.elsewhen(missInstall) {
    cacheArray.io.writeValid := True
    cacheArray.io.writeIndex := indexOf(misses(installId).lineAddress)
    cacheArray.io.writeWay := misses(installId).victimWay
    cacheArray.io.writeTag := tagOf(misses(installId).lineAddress)
    cacheArray.io.writeData := installLine
    cacheArray.io.writeEntryValid := True
    cacheArray.io.writeDirty := False
    misses(installId).valid := False
  }

  when(
    state === OooL2CacheState.maintenanceLookup &&
      cacheArray.io.maintenanceResponseValid
  ) {
    when(cacheArray.io.maintenanceEntryValid && cacheArray.io.maintenanceEntryDirty) {
      maintenanceVictimAddress := cacheArray.io.maintenanceEntryAddress
      maintenanceVictimData := cacheArray.io.maintenanceEntryData
      state := OooL2CacheState.maintenanceWriteback
    }.otherwise {
      state := OooL2CacheState.maintenanceInvalidate
    }
  }
  when(state === OooL2CacheState.maintenanceWriteback && memoryWriteFire) {
    state := OooL2CacheState.maintenanceInvalidate
  }
  when(state === OooL2CacheState.maintenanceInvalidate) {
    cacheArray.io.writeValid := True
    cacheArray.io.writeIndex := maintenanceIndex
    cacheArray.io.writeWay := maintenanceWay
    cacheArray.io.writeTag := 0
    cacheArray.io.writeData := 0
    cacheArray.io.writeEntryValid := False
    cacheArray.io.writeDirty := False
    when(maintenanceWay === U(geometry.ways - 1, wayWidth bits)) {
      maintenanceWay := 0
      when(maintenanceIndex === U(geometry.sets - 1, indexWidth bits)) {
        state := OooL2CacheState.normal
      }.otherwise {
        maintenanceIndex := maintenanceIndex + 1
        state := OooL2CacheState.maintenanceLookup
      }
    }.otherwise {
      maintenanceWay := maintenanceWay + 1
      state := OooL2CacheState.maintenanceLookup
    }
  }

  io.invalidateBusy := cacheArray.io.invalidateBusy || maintenanceRequest ||
    state =/= OooL2CacheState.normal
}
