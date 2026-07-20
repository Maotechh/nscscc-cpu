package openla500.ooo

import spinal.core._

/** OoO execution backend connected to the shared 64-byte L1I/L1D/L2 hierarchy. */
final class OooBackendWithDataCache(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit
) extends Component {
  val io = new Bundle {
    val renameValid = in Bits (config.renameWidth bits)
    val rename = in Vec (OooDecodedUop(config), config.renameWidth)
    val renameReady = out Bits (config.renameWidth bits)

    val instructionRequestValid = in Bool ()
    val instructionRequest = in(OooInstructionCacheRequest(config))
    val instructionRequestReady = out Bool ()
    val instructionResponseValid = out Bool ()
    val instructionResponse = out(OooInstructionCacheResponse(config))
    val instructionKill = in Bool ()

    val memoryReadValid = out Bool ()
    val memoryRead = out(OooLineReadRequest(config))
    val memoryReadReady = in Bool ()
    val memoryReadBeatValid = in Bool ()
    val memoryReadBeat = in(OooLineReadBeat(config))
    val memoryReadBeatReady = out Bool ()
    val memoryWriteValid = out Bool ()
    val memoryWrite = out(OooLineWriteRequest(config))
    val memoryWriteReady = in Bool ()

    val systemReadValid = out Bool ()
    val systemReadAddress = out UInt (14 bits)
    val systemReadData = in Bits (config.xlen bits)
    val timer = in Bits (64 bits)
    val timerId = in Bits (config.xlen bits)

    val commitValid = out Bits (config.commitWidth bits)
    val commit = out Vec (OooCommitRecord(config), config.commitWidth)
    val recoveryValid = out Bool ()
    val recovery = out(OooRecoveryRequest(config))
    val debugCommitValid = out Bool ()
    val debugCommit = out(OooCommitRecord(config))
    val csrWriteValid = out Bool ()
    val csrWriteAddress = out UInt (14 bits)
    val csrWriteData = out Bits (config.xlen bits)
    val csrWriteMask = out Bool ()
    val ertnValid = out Bool ()
    val refetchValid = out Bool ()
    val tlbSearchValid = out Bool ()
    val tlbReadValid = out Bool ()
    val tlbWriteValid = out Bool ()
    val tlbFillValid = out Bool ()
    val tlbInvalidateValid = out Bool ()
    val exceptionValid = out Bool ()
    val exceptionPc = out UInt (config.xlen bits)
    val exception = out(OooExceptionMeta())

    val cacheInvalidate = in Bool ()
    val cacheInvalidateBusy = out Bool ()
    val flush = in Bool ()
  }

  val backend = new OooBackendWithExecution(config)
  val cacheHierarchy = new OooSharedCacheHierarchy(config)

  backend.io.renameValid := io.renameValid
  backend.io.rename := io.rename
  io.renameReady := backend.io.renameReady

  cacheHierarchy.io.instructionRequestValid := io.instructionRequestValid
  cacheHierarchy.io.instructionRequest := io.instructionRequest
  cacheHierarchy.io.instructionKill := io.instructionKill
  io.instructionRequestReady := cacheHierarchy.io.instructionRequestReady
  io.instructionResponseValid := cacheHierarchy.io.instructionResponseValid
  io.instructionResponse := cacheHierarchy.io.instructionResponse

  cacheHierarchy.io.dataRequestValid := backend.io.dataRequestValid
  cacheHierarchy.io.dataRequest := backend.io.dataRequest
  backend.io.dataRequestReady := cacheHierarchy.io.dataRequestReady
  backend.io.dataResponseValid := cacheHierarchy.io.dataResponseValid
  backend.io.dataResponse := cacheHierarchy.io.dataResponse

  io.memoryReadValid := cacheHierarchy.io.memoryReadValid
  io.memoryRead := cacheHierarchy.io.memoryRead
  cacheHierarchy.io.memoryReadReady := io.memoryReadReady
  cacheHierarchy.io.memoryReadBeatValid := io.memoryReadBeatValid
  cacheHierarchy.io.memoryReadBeat := io.memoryReadBeat
  io.memoryReadBeatReady := cacheHierarchy.io.memoryReadBeatReady
  io.memoryWriteValid := cacheHierarchy.io.memoryWriteValid
  io.memoryWrite := cacheHierarchy.io.memoryWrite
  cacheHierarchy.io.memoryWriteReady := io.memoryWriteReady

  backend.io.systemReadData := io.systemReadData
  backend.io.timer := io.timer
  backend.io.timerId := io.timerId
  io.systemReadValid := backend.io.systemReadValid
  io.systemReadAddress := backend.io.systemReadAddress

  io.commitValid := backend.io.commitValid
  io.commit := backend.io.commit
  io.recoveryValid := backend.io.recoveryValid
  io.recovery := backend.io.recovery
  io.debugCommitValid := backend.io.debugCommitValid
  io.debugCommit := backend.io.debugCommit
  io.csrWriteValid := backend.io.csrWriteValid
  io.csrWriteAddress := backend.io.csrWriteAddress
  io.csrWriteData := backend.io.csrWriteData
  io.csrWriteMask := backend.io.csrWriteMask
  io.ertnValid := backend.io.ertnValid
  io.refetchValid := backend.io.refetchValid
  io.tlbSearchValid := backend.io.tlbSearchValid
  io.tlbReadValid := backend.io.tlbReadValid
  io.tlbWriteValid := backend.io.tlbWriteValid
  io.tlbFillValid := backend.io.tlbFillValid
  io.tlbInvalidateValid := backend.io.tlbInvalidateValid
  io.exceptionValid := backend.io.exceptionValid
  io.exceptionPc := backend.io.exceptionPc
  io.exception := backend.io.exception

  cacheHierarchy.io.invalidate := io.cacheInvalidate
  io.cacheInvalidateBusy := cacheHierarchy.io.invalidateBusy
  backend.io.flush := io.flush
}
