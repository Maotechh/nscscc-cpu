package openla500.ooo

import spinal.core._

/** Blocking L1I/L1D hierarchy sharing one 64-byte L2 cache.
  *
  * Dirty L1D writebacks have priority. Read ownership is locked from L2 request acceptance through
  * the final response beat, so identical local MSHR ids from L1I and L1D cannot cross-route data.
  */
final class OooSharedCacheHierarchy(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit
) extends Component {
  val io = new Bundle {
    val instructionRequestValid = in Bool ()
    val instructionRequest = in(OooInstructionCacheRequest(config))
    val instructionRequestReady = out Bool ()
    val instructionResponseValid = out Bool ()
    val instructionResponse = out(OooInstructionCacheResponse(config))
    val instructionKill = in Bool ()

    val dataRequestValid = in Bool ()
    val dataRequest = in(OooCacheRequest(config))
    val dataRequestReady = out Bool ()
    val dataResponseValid = out Bool ()
    val dataResponse = out(OooCacheResponse(config))

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

  val l1i = new OooL1InstructionCache(config)
  val l1d = new OooL1DataCache(config)
  val l2 = new OooL2Cache(config)

  l1i.io.requestValid := io.instructionRequestValid
  l1i.io.request := io.instructionRequest
  io.instructionRequestReady := l1i.io.requestReady
  io.instructionResponseValid := l1i.io.responseValid
  io.instructionResponse := l1i.io.response
  l1i.io.kill := io.instructionKill

  l1d.io.requestValid := io.dataRequestValid
  l1d.io.request := io.dataRequest
  io.dataRequestReady := l1d.io.requestReady
  io.dataResponseValid := l1d.io.responseValid
  io.dataResponse := l1d.io.response

  val preferDataRead = RegInit(True)
  val readOwnerData = RegInit(False)
  val dataWritePending = l1d.io.lineWriteValid
  val bothReadPending = l1i.io.lineReadValid && l1d.io.lineReadValid
  val selectDataRead = !dataWritePending && l1d.io.lineReadValid &&
    (!l1i.io.lineReadValid || preferDataRead)
  val selectInstructionRead = !dataWritePending && l1i.io.lineReadValid &&
    (!l1d.io.lineReadValid || !preferDataRead)

  l2.io.writeValid := l1d.io.lineWriteValid
  l2.io.write := l1d.io.lineWrite
  l1d.io.lineWriteReady := l2.io.writeReady

  l2.io.readValid := selectDataRead || selectInstructionRead
  l2.io.read := l1i.io.lineRead
  when(selectDataRead) { l2.io.read := l1d.io.lineRead }
  l1d.io.lineReadReady := l2.io.readReady && selectDataRead
  l1i.io.lineReadReady := l2.io.readReady && selectInstructionRead

  val l2ReadFire = l2.io.readValid && l2.io.readReady
  when(l2ReadFire) {
    readOwnerData := selectDataRead
    when(bothReadPending) { preferDataRead := !selectDataRead }
  }

  l1d.io.lineReadBeatValid := l2.io.readBeatValid && readOwnerData
  l1d.io.lineReadBeat := l2.io.readBeat
  l1i.io.lineReadBeatValid := l2.io.readBeatValid && !readOwnerData
  l1i.io.lineReadBeat := l2.io.readBeat
  l2.io.readBeatReady := Mux(
    readOwnerData,
    l1d.io.lineReadBeatReady,
    l1i.io.lineReadBeatReady
  )

  io.memoryReadValid := l2.io.memoryReadValid
  io.memoryRead := l2.io.memoryRead
  l2.io.memoryReadReady := io.memoryReadReady
  l2.io.memoryReadBeatValid := io.memoryReadBeatValid
  l2.io.memoryReadBeat := io.memoryReadBeat
  io.memoryReadBeatReady := l2.io.memoryReadBeatReady

  io.memoryWriteValid := l2.io.memoryWriteValid
  io.memoryWrite := l2.io.memoryWrite
  l2.io.memoryWriteReady := io.memoryWriteReady

  l1i.io.invalidate := io.invalidate
  l1d.io.invalidate := io.invalidate
  l2.io.invalidate := io.invalidate
  io.invalidateBusy := l1i.io.invalidateBusy || l1d.io.invalidateBusy || l2.io.invalidateBusy
}
