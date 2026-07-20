package openla500.memory

import openla500.compat.Axi3Compat
import openla500.core._
import spinal.core._
import spinal.lib._

/** Converts cached line traffic and uncached narrow traffic to one AXI3 master.
  *
  * Uncached instruction fetches use a four-word burst. Uncached data reads use the architectural
  * transfer size, while uncached writes are acknowledged upstream only after the AXI B response.
  */
final class OooAxiLineBridge(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit
) extends Component {
  private val axiWordsPerLine = OooCacheContract.LineBytes / 4
  private val axiWordIndexWidth = log2Up(axiWordsPerLine)

  require(axiWordsPerLine == 16)

  val io = new Bundle {
    val memoryReadValid = in Bool ()
    val memoryRead = in(OooLineReadRequest(config))
    val memoryReadReady = out Bool ()
    val memoryReadBeatValid = out Bool ()
    val memoryReadBeat = out(OooLineReadBeat(config))
    val memoryReadBeatReady = in Bool ()

    val memoryWriteValid = in Bool ()
    val memoryWrite = in(OooLineWriteRequest(config))
    val memoryWriteReady = out Bool ()

    val uncachedInstructionRequestValid = in Bool ()
    val uncachedInstructionRequest = in(OooInstructionCacheRequest(config))
    val uncachedInstructionRequestReady = out Bool ()
    val uncachedInstructionResponseValid = out Bool ()
    val uncachedInstructionResponse = out(OooInstructionCacheResponse(config))

    val uncachedDataRequestValid = in Bool ()
    val uncachedDataRequest = in(OooCacheRequest(config))
    val uncachedDataRequestReady = out Bool ()
    val uncachedDataResponseValid = out Bool ()
    val uncachedDataResponse = out(OooCacheResponse(config))

    val axi = master(Axi3Compat())
  }

  val lineReadKind = U(0, 2 bits)
  val instructionReadKind = U(1, 2 bits)
  val dataReadKind = U(2, 2 bits)

  val readActive = RegInit(False)
  val readKind = Reg(UInt(2 bits)) init (lineReadKind)
  val readAddress = Reg(UInt(config.xlen bits))
  val readSize = Reg(Bits(3 bits)) init (B(2, 3 bits))
  val readMshrId = Reg(UInt(log2Up(config.mshrEntries) bits))
  val readAddressValid = RegInit(False)
  val readHalf = RegInit(False)
  val readLowWord = Reg(Bits(32 bits))
  val readLowError = RegInit(False)
  val readBeatIndex = Reg(UInt(OooCacheContract.BeatIndexWidth bits)) init (0)
  val readOutputValid = RegInit(False)
  val readOutput = Reg(OooLineReadBeat(config))
  val instructionReadWordIndex = Reg(UInt(2 bits)) init (0)
  val instructionReadError = RegInit(False)
  val instructionResponseValid = RegInit(False)
  val instructionResponse = Reg(OooInstructionCacheResponse(config))
  val dataReadContext = Reg(OooCacheRequest(config))
  val dataResponseValid = RegInit(False)
  val dataResponse = Reg(OooCacheResponse(config))

  val writeActive = RegInit(False)
  val writeIsUncachedData = RegInit(False)
  val writeAddress = Reg(UInt(config.xlen bits))
  val writeSize = Reg(Bits(3 bits)) init (B(2, 3 bits))
  val writeData = Reg(Bits(OooCacheContract.LineBits bits))
  val writeMask = Reg(Bits(OooCacheContract.LineBytes bits))
  val dataWriteContext = Reg(OooCacheRequest(config))
  val writeAddressValid = RegInit(False)
  val writeBeatIndex = Reg(UInt(axiWordIndexWidth bits)) init (0)
  val writeResponsePending = RegInit(False)

  instructionResponseValid := False
  dataResponseValid := False
  io.uncachedInstructionResponseValid := instructionResponseValid
  io.uncachedInstructionResponse := instructionResponse
  io.uncachedDataResponseValid := dataResponseValid
  io.uncachedDataResponse := dataResponse

  val busIdle = !readActive && !writeActive && !readOutputValid
  val startUncachedData = busIdle && io.uncachedDataRequestValid
  val startUncachedDataRead = startUncachedData && !io.uncachedDataRequest.isWrite
  val startUncachedDataWrite = startUncachedData && io.uncachedDataRequest.isWrite
  val startUncachedInstruction = busIdle && !io.uncachedDataRequestValid &&
    io.uncachedInstructionRequestValid
  io.uncachedDataRequestReady := startUncachedDataRead ||
    (writeIsUncachedData && writeResponsePending && io.axi.b.valid)
  io.uncachedInstructionRequestReady := startUncachedInstruction
  io.memoryReadReady := busIdle && !io.uncachedDataRequestValid &&
    !io.uncachedInstructionRequestValid
  io.memoryWriteReady := io.memoryReadReady && !io.memoryReadValid
  val readRequestFire = io.memoryReadValid && io.memoryReadReady
  val writeRequestFire = io.memoryWriteValid && io.memoryWriteReady

  when(readRequestFire) {
    readActive := True
    readKind := lineReadKind
    readAddress := io.memoryRead.lineAddress
    readSize := B(2, 3 bits)
    readMshrId := io.memoryRead.mshrId
    readAddressValid := True
    readHalf := False
    readBeatIndex := 0
  }
  when(startUncachedInstruction) {
    readActive := True
    readKind := instructionReadKind
    readAddress := io.uncachedInstructionRequest.physicalAddress &
      U(((BigInt(1) << config.xlen) - 1) ^ 0xf, config.xlen bits)
    readSize := B(2, 3 bits)
    readAddressValid := True
    instructionReadWordIndex := 0
    instructionReadError := False
    instructionResponse.virtualAddress := io.uncachedInstructionRequest.virtualAddress
    instructionResponse.physicalAddress := io.uncachedInstructionRequest.physicalAddress
    instructionResponse.error := False
    for (word <- 0 until config.fetchWidth) {
      instructionResponse.instructions(word) := 0
    }
  }
  when(startUncachedDataRead) {
    readActive := True
    readKind := dataReadKind
    readAddress := io.uncachedDataRequest.physicalAddress
    readSize := io.uncachedDataRequest.size
    readAddressValid := True
    dataReadContext := io.uncachedDataRequest
  }

  io.axi.ar.valid := readAddressValid
  io.axi.ar.payload.id := B(0, 4 bits)
  when(readKind === instructionReadKind) { io.axi.ar.payload.id := B(2, 4 bits) }
  when(readKind === dataReadKind) { io.axi.ar.payload.id := B(3, 4 bits) }
  io.axi.ar.payload.address := readAddress.asBits
  io.axi.ar.payload.len := B(axiWordsPerLine - 1, 8 bits)
  when(readKind === instructionReadKind) {
    io.axi.ar.payload.len := B(config.fetchWidth - 1, 8 bits)
  }
  when(readKind === dataReadKind) { io.axi.ar.payload.len := B(0, 8 bits) }
  io.axi.ar.payload.size := readSize
  io.axi.ar.payload.burst := B"2'b01"
  io.axi.ar.payload.lock := B"2'b00"
  io.axi.ar.payload.cache := B"4'b0000"
  io.axi.ar.payload.prot := B"3'b000"
  when(io.axi.ar.valid && io.axi.ar.ready) { readAddressValid := False }

  val readOutputFire = readOutputValid && io.memoryReadBeatReady
  when(readOutputFire) { readOutputValid := False }
  val secondWordReady = !readOutputValid || io.memoryReadBeatReady
  io.axi.r.ready := readActive && !readAddressValid &&
    (readKind =/= lineReadKind || !readHalf || secondWordReady)
  val readWordFire = io.axi.r.valid && io.axi.r.ready
  when(readWordFire) {
    when(readKind === lineReadKind) {
      val responseError = io.axi.r.payload.response.orR || io.axi.r.payload.id =/= 0
      when(!readHalf) {
        readLowWord := io.axi.r.payload.data
        readLowError := responseError || io.axi.r.payload.last
        readHalf := True
      }.otherwise {
        val expectedLast = readBeatIndex === OooCacheContract.BeatsPerLine - 1
        readOutputValid := True
        readOutput.mshrId := readMshrId
        readOutput.beat := readBeatIndex
        readOutput.data := io.axi.r.payload.data ## readLowWord
        readOutput.last := expectedLast
        readOutput.error := readLowError || responseError ||
          (io.axi.r.payload.last =/= expectedLast)
        readHalf := False
        when(expectedLast) {
          readActive := False
        }.otherwise {
          readBeatIndex := readBeatIndex + 1
        }
      }
    }.elsewhen(readKind === instructionReadKind) {
      val expectedLast = instructionReadWordIndex === config.fetchWidth - 1
      val responseError = io.axi.r.payload.response.orR ||
        io.axi.r.payload.id =/= B(2, 4 bits)
      instructionResponse.instructions(instructionReadWordIndex) := io.axi.r.payload.data
      instructionReadError := instructionReadError || responseError
      when(expectedLast || io.axi.r.payload.last) {
        instructionResponseValid := True
        instructionResponse.error := instructionReadError || responseError ||
          (io.axi.r.payload.last =/= expectedLast)
        readActive := False
      }.otherwise {
        instructionReadWordIndex := instructionReadWordIndex + 1
      }
    }.otherwise {
      dataResponseValid := True
      dataResponse.robPointer := dataReadContext.robPointer
      dataResponse.pdst := dataReadContext.pdst
      dataResponse.data := io.axi.r.payload.data
      dataResponse.error := io.axi.r.payload.response.orR ||
        io.axi.r.payload.id =/= B(3, 4 bits) || !io.axi.r.payload.last
      readActive := False
    }
  }

  io.memoryReadBeatValid := readOutputValid
  io.memoryReadBeat := readOutput

  when(writeRequestFire) {
    writeActive := True
    writeIsUncachedData := False
    writeAddress := io.memoryWrite.lineAddress
    writeSize := B(2, 3 bits)
    writeData := io.memoryWrite.data
    writeMask := io.memoryWrite.byteMask
    writeAddressValid := True
    writeBeatIndex := 0
    writeResponsePending := False
  }
  when(startUncachedDataWrite) {
    writeActive := True
    writeIsUncachedData := True
    writeAddress := io.uncachedDataRequest.physicalAddress
    writeSize := io.uncachedDataRequest.size
    writeData := io.uncachedDataRequest.writeData.resize(OooCacheContract.LineBits)
    writeMask := io.uncachedDataRequest.byteMask.resize(OooCacheContract.LineBytes)
    dataWriteContext := io.uncachedDataRequest
    writeAddressValid := True
    writeBeatIndex := 0
    writeResponsePending := False
  }

  io.axi.aw.valid := writeAddressValid
  io.axi.aw.payload.id := Mux(writeIsUncachedData, B(3, 4 bits), B(1, 4 bits))
  io.axi.aw.payload.address := writeAddress.asBits
  io.axi.aw.payload.len := Mux(
    writeIsUncachedData,
    B(0, 8 bits),
    B(axiWordsPerLine - 1, 8 bits)
  )
  io.axi.aw.payload.size := writeSize
  io.axi.aw.payload.burst := B"2'b01"
  io.axi.aw.payload.lock := B"2'b00"
  io.axi.aw.payload.cache := B"4'b0000"
  io.axi.aw.payload.prot := B"3'b000"
  when(io.axi.aw.valid && io.axi.aw.ready) { writeAddressValid := False }

  val writeDataShift = (writeBeatIndex ## U(0, 5 bits)).asUInt
  val writeMaskShift = (writeBeatIndex ## U(0, 2 bits)).asUInt
  io.axi.w.valid := writeActive && !writeAddressValid && !writeResponsePending
  io.axi.w.payload.id := Mux(writeIsUncachedData, B(3, 4 bits), B(1, 4 bits))
  io.axi.w.payload.data := (writeData |>> writeDataShift)(31 downto 0)
  io.axi.w.payload.byteMask := (writeMask |>> writeMaskShift)(3 downto 0)
  io.axi.w.payload.last := writeIsUncachedData || writeBeatIndex === axiWordsPerLine - 1
  when(io.axi.w.valid && io.axi.w.ready) {
    when(io.axi.w.payload.last) {
      writeResponsePending := True
    }.otherwise {
      writeBeatIndex := writeBeatIndex + 1
    }
  }

  io.axi.b.ready := writeResponsePending
  when(io.axi.b.valid && io.axi.b.ready) {
    writeResponsePending := False
    writeActive := False
  }
}
