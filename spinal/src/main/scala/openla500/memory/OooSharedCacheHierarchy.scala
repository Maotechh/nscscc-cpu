package openla500.memory

import openla500.core._
import spinal.core._

object OooSharedCacheMaintenanceState extends SpinalEnum {
  val idle, kickDataL1, waitDataL1, kickDataL2, waitDataL2 = newElement()
}

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
    val instructionUncachedRequestValid = in Bool ()
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

    val uncachedInstructionRequestValid = out Bool ()
    val uncachedInstructionRequest = out(OooInstructionCacheRequest(config))
    val uncachedInstructionRequestReady = in Bool ()
    val uncachedInstructionResponseValid = in Bool ()
    val uncachedInstructionResponse = in(OooInstructionCacheResponse(config))

    val uncachedDataRequestValid = out Bool ()
    val uncachedDataRequest = out(OooCacheRequest(config))
    val uncachedDataRequestReady = in Bool ()
    val uncachedDataResponseValid = in Bool ()
    val uncachedDataResponse = in(OooCacheResponse(config))

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
    val dataInvalidate = in Bool ()
    val dataWritebackInvalidate = in Bool ()
    val level2Invalidate = in Bool ()
    val invalidateBusy = out Bool ()
  }

  val l1i = new OooL1InstructionCache(config)
  val l1d = new OooL1DataCache(config)
  val readMshrs = new OooSharedReadMshrRouter(config)
  val l2 = new OooL2Cache(config)
  val maintenanceState = RegInit(OooSharedCacheMaintenanceState.idle)
  val maintenanceSeen = RegInit(False)
  val newDataWritebackInvalidate = io.dataWritebackInvalidate && !maintenanceSeen
  when(io.dataWritebackInvalidate) { maintenanceSeen := True }
    .otherwise { maintenanceSeen := False }
  when(newDataWritebackInvalidate && maintenanceState === OooSharedCacheMaintenanceState.idle) {
    maintenanceState := OooSharedCacheMaintenanceState.kickDataL1
  }
  when(maintenanceState === OooSharedCacheMaintenanceState.kickDataL1) {
    maintenanceState := OooSharedCacheMaintenanceState.waitDataL1
  }
  when(
    maintenanceState === OooSharedCacheMaintenanceState.waitDataL1 &&
      !l1d.io.invalidateBusy
  ) {
    maintenanceState := OooSharedCacheMaintenanceState.kickDataL2
  }
  when(maintenanceState === OooSharedCacheMaintenanceState.kickDataL2) {
    maintenanceState := OooSharedCacheMaintenanceState.waitDataL2
  }
  when(
    maintenanceState === OooSharedCacheMaintenanceState.waitDataL2 &&
      !l2.io.invalidateBusy
  ) {
    maintenanceState := OooSharedCacheMaintenanceState.idle
  }
  val hierarchyMaintenanceBusy = l1i.io.invalidateBusy || l1d.io.invalidateBusy ||
    l2.io.invalidateBusy || maintenanceState =/= OooSharedCacheMaintenanceState.idle

  l1i.io.requestValid := io.instructionRequestValid
  l1i.io.request := io.instructionRequest
  io.uncachedInstructionRequestValid := io.instructionUncachedRequestValid &&
    !hierarchyMaintenanceBusy
  io.uncachedInstructionRequest := io.instructionRequest
  io.instructionRequestReady := !hierarchyMaintenanceBusy && Mux(
    io.instructionRequest.uncached,
    io.uncachedInstructionRequestReady,
    l1i.io.requestReady
  )
  io.instructionResponseValid := l1i.io.responseValid || io.uncachedInstructionResponseValid
  io.instructionResponse := io.uncachedInstructionResponse
  // A killed uncached AXI transaction may return in the same cycle as a new L1I hit.  The
  // frontend can discard the stale uncached response by PC, but it cannot recover an L1I pulse
  // hidden behind that response, so the live private-cache response has priority.
  when(l1i.io.responseValid) {
    io.instructionResponse := l1i.io.response
  }
  l1i.io.kill := io.instructionKill

  val dataUncached = io.dataRequestValid && io.dataRequest.uncached
  l1d.io.requestValid := io.dataRequestValid && !io.dataRequest.uncached
  l1d.io.request := io.dataRequest
  io.uncachedDataRequestValid := dataUncached && !hierarchyMaintenanceBusy
  io.uncachedDataRequest := io.dataRequest
  io.dataRequestReady := !hierarchyMaintenanceBusy && Mux(
    io.dataRequest.uncached,
    io.uncachedDataRequestReady,
    l1d.io.requestReady
  )
  io.dataResponseValid := l1d.io.responseValid || io.uncachedDataResponseValid
  io.dataResponse := l1d.io.response
  when(io.uncachedDataResponseValid) { io.dataResponse := io.uncachedDataResponse }

  val dataWritePending = l1d.io.lineWriteValid

  l2.io.writeValid := l1d.io.lineWriteValid
  l2.io.write := l1d.io.lineWrite
  l1d.io.lineWriteReady := l2.io.writeReady

  readMshrs.io.instructionReadValid := l1i.io.lineReadValid && !dataWritePending
  readMshrs.io.instructionRead := l1i.io.lineRead
  l1i.io.lineReadReady := readMshrs.io.instructionReadReady
  l1i.io.lineReadBeatValid := readMshrs.io.instructionReadBeatValid
  l1i.io.lineReadBeat := readMshrs.io.instructionReadBeat
  readMshrs.io.instructionReadBeatReady := l1i.io.lineReadBeatReady

  readMshrs.io.dataReadValid := l1d.io.lineReadValid && !dataWritePending
  readMshrs.io.dataRead := l1d.io.lineRead
  l1d.io.lineReadReady := readMshrs.io.dataReadReady
  l1d.io.lineReadBeatValid := readMshrs.io.dataReadBeatValid
  l1d.io.lineReadBeat := readMshrs.io.dataReadBeat
  readMshrs.io.dataReadBeatReady := l1d.io.lineReadBeatReady

  l2.io.readValid := readMshrs.io.lowerReadValid
  l2.io.read := readMshrs.io.lowerRead
  readMshrs.io.lowerReadReady := l2.io.readReady
  readMshrs.io.lowerReadBeatValid := l2.io.readBeatValid
  readMshrs.io.lowerReadBeat := l2.io.readBeat
  l2.io.readBeatReady := readMshrs.io.lowerReadBeatReady

  io.memoryReadValid := l2.io.memoryReadValid
  io.memoryRead := l2.io.memoryRead
  l2.io.memoryReadReady := io.memoryReadReady
  l2.io.memoryReadBeatValid := io.memoryReadBeatValid
  l2.io.memoryReadBeat := io.memoryReadBeat
  io.memoryReadBeatReady := l2.io.memoryReadBeatReady

  io.memoryWriteValid := l2.io.memoryWriteValid
  io.memoryWrite := l2.io.memoryWrite
  l2.io.memoryWriteReady := io.memoryWriteReady

  // An I-cache maintenance operation must also evict the shared copy.  Otherwise an uncached
  // self-modifying-code store is followed by an L1I miss that simply reloads the stale L2 line.
  // L1D remains untouched because dropping a dirty private line would lose architectural data.
  l1i.io.invalidate := io.invalidate
  l1d.io.invalidate := io.dataInvalidate
  l1d.io.writebackInvalidate := maintenanceState ===
    OooSharedCacheMaintenanceState.kickDataL1
  l2.io.writebackInvalidate := maintenanceState ===
    OooSharedCacheMaintenanceState.kickDataL2
  l2.io.invalidate := io.invalidate || io.dataInvalidate || io.level2Invalidate
  io.invalidateBusy := hierarchyMaintenanceBusy
}
