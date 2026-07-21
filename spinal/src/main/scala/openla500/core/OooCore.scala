package openla500.core

import openla500.backend._
import openla500.frontend._
import openla500.memory._
import openla500.privileged._
import spinal.core._
import spinal.lib._

/** Self-fetching four-issue, three-commit out-of-order core.
  *
  * Branch recovery is handled internally. Precise exception entry and privileged redirects remain
  * explicit inputs until the architectural CSR/MMU block is connected at the final core boundary.
  */
final class OooCore(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  val io = new Bundle {
    val instructionTranslationRequest = master(Stream(OooTranslationRequest(config)))
    val instructionTranslationResponse = slave(Stream(OooTranslationResponse(config)))
    val dataTranslationRequest = master(Stream(OooTranslationRequest(config)))
    val dataTranslationResponse = slave(Stream(OooTranslationResponse(config)))
    val reservationValid = in Bool ()
    val reservationLineAddress = in Bits (28 bits)

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

    val systemReadValid = out Bool ()
    val systemReadAddress = out UInt (14 bits)
    val systemReadData = in Bits (config.xlen bits)
    val timer = in Bits (64 bits)
    val timerId = in Bits (config.xlen bits)
    val debugReadAddress = in UInt (config.archRegIndexWidth bits)
    val debugReadData = out Bits (config.xlen bits)

    val privilege = in Bits (2 bits)
    val interruptPending = in Bool ()
    val exceptionEntryTarget = in UInt (config.xlen bits)
    val tlbRefillTarget = in UInt (config.xlen bits)
    val externalRedirectValid = in Bool ()
    val externalRedirectTarget = in UInt (config.xlen bits)

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
    val serialCommitPc = out UInt (config.xlen bits)
    val ertnValid = out Bool ()
    val idleValid = out Bool ()
    val refetchValid = out Bool ()
    val cacheInvalidateValid = out Bool ()
    val dataCacheInvalidateValid = out Bool ()
    val dataCacheWritebackInvalidateValid = out Bool ()
    val level2CacheInvalidateValid = out Bool ()
    val tlbSearchValid = out Bool ()
    val tlbReadValid = out Bool ()
    val tlbWriteValid = out Bool ()
    val tlbFillValid = out Bool ()
    val tlbInvalidateValid = out Bool ()
    val tlbInvalidateAsid = out Bits (10 bits)
    val tlbInvalidateVpn = out Bits (19 bits)
    val tlbInvalidateOperation = out Bits (5 bits)
    val reservationBitSet = out Bool ()
    val reservationBitValue = out Bool ()
    val reservationAddressSet = out Bool ()
    val reservationLineAddressUpdate = out Bits (28 bits)
    val exceptionValid = out Bool ()
    val exceptionPc = out UInt (config.xlen bits)
    val exception = out(OooExceptionMeta())

    val cacheInvalidate = in Bool ()
    val dataCacheInvalidate = in Bool ()
    val dataCacheWritebackInvalidate = in Bool ()
    val level2CacheInvalidate = in Bool ()
    val cacheInvalidateBusy = out Bool ()
    val fetchPc = out UInt (config.xlen bits)
    val frontendOccupancy = out UInt (log2Up(config.instructionBufferEntries + 1) bits)
  }

  val frontend = new OooFrontend(config)
  val decodeRenameBuffer = new OooDecodeRenameBuffer(config)
  val backend = new OooBackendWithDataCache(config)

  io.instructionTranslationRequest.valid := frontend.io.translationRequest.valid
  io.instructionTranslationRequest.payload := frontend.io.translationRequest.payload
  frontend.io.translationRequest.ready := io.instructionTranslationRequest.ready
  frontend.io.translationResponse.valid := io.instructionTranslationResponse.valid
  frontend.io.translationResponse.payload := io.instructionTranslationResponse.payload
  io.instructionTranslationResponse.ready := frontend.io.translationResponse.ready
  io.dataTranslationRequest.valid := backend.io.dataTranslationRequest.valid
  io.dataTranslationRequest.payload := backend.io.dataTranslationRequest.payload
  backend.io.dataTranslationRequest.ready := io.dataTranslationRequest.ready
  backend.io.dataTranslationResponse.valid := io.dataTranslationResponse.valid
  backend.io.dataTranslationResponse.payload := io.dataTranslationResponse.payload
  io.dataTranslationResponse.ready := backend.io.dataTranslationResponse.ready
  backend.io.reservationValid := io.reservationValid
  backend.io.reservationLineAddress := io.reservationLineAddress

  decodeRenameBuffer.io.inputValid := frontend.io.decodeValid
  decodeRenameBuffer.io.input := frontend.io.decoded
  frontend.io.decodeReady := decodeRenameBuffer.io.inputReady
  backend.io.renameValid := decodeRenameBuffer.io.outputValid
  backend.io.rename := decodeRenameBuffer.io.output
  decodeRenameBuffer.io.outputReady := backend.io.renameReady

  backend.io.instructionRequestValid := frontend.io.cacheRequestValid
  backend.io.instructionRequest := frontend.io.cacheRequest
  frontend.io.cacheRequestReady := backend.io.instructionRequestReady
  frontend.io.cacheResponseValid := backend.io.instructionResponseValid
  frontend.io.cacheResponse := backend.io.instructionResponse
  backend.io.instructionKill := frontend.io.cacheKill
  io.uncachedInstructionRequestValid := backend.io.uncachedInstructionRequestValid
  io.uncachedInstructionRequest := backend.io.uncachedInstructionRequest
  backend.io.uncachedInstructionRequestReady := io.uncachedInstructionRequestReady
  backend.io.uncachedInstructionResponseValid := io.uncachedInstructionResponseValid
  backend.io.uncachedInstructionResponse := io.uncachedInstructionResponse
  io.uncachedDataRequestValid := backend.io.uncachedDataRequestValid
  io.uncachedDataRequest := backend.io.uncachedDataRequest
  backend.io.uncachedDataRequestReady := io.uncachedDataRequestReady
  backend.io.uncachedDataResponseValid := io.uncachedDataResponseValid
  backend.io.uncachedDataResponse := io.uncachedDataResponse

  val recoveryPending = RegInit(False)
  val recoveryPayload = Reg(OooRecoveryRequest(config))
  val recoveryCapture = backend.io.recoveryValid && !recoveryPending &&
    !io.externalRedirectValid
  recoveryPending := recoveryCapture
  when(recoveryCapture) { recoveryPayload := backend.io.recovery }

  val exceptionRecovery = recoveryPending &&
    recoveryPayload.cause === OooRecoveryCause.exception
  val internalRedirectValid = recoveryPending || io.externalRedirectValid
  val internalRedirectTarget = UInt(config.xlen bits)
  internalRedirectTarget := recoveryPayload.target
  when(exceptionRecovery) {
    internalRedirectTarget := Mux(
      recoveryPayload.exception.tlbRefill,
      io.tlbRefillTarget,
      io.exceptionEntryTarget
    )
  }
  when(io.externalRedirectValid) {
    internalRedirectTarget := io.externalRedirectTarget
  }

  frontend.io.redirectValid := internalRedirectValid
  frontend.io.redirectTarget := internalRedirectTarget
  frontend.io.predictorUpdateValid := backend.io.recoveryValid &&
    backend.io.recovery.cause === OooRecoveryCause.branchMispredict
  frontend.io.predictorUpdatePc := backend.io.recovery.pc
  frontend.io.predictorUpdateTaken := backend.io.recovery.taken
  frontend.io.predictorUpdateTarget := backend.io.recovery.target
  frontend.io.privilege := io.privilege
  frontend.io.interruptPending := io.interruptPending
  decodeRenameBuffer.io.flush := internalRedirectValid
  backend.io.flush := internalRedirectValid

  io.memoryReadValid := backend.io.memoryReadValid
  io.memoryRead := backend.io.memoryRead
  backend.io.memoryReadReady := io.memoryReadReady
  backend.io.memoryReadBeatValid := io.memoryReadBeatValid
  backend.io.memoryReadBeat := io.memoryReadBeat
  io.memoryReadBeatReady := backend.io.memoryReadBeatReady
  io.memoryWriteValid := backend.io.memoryWriteValid
  io.memoryWrite := backend.io.memoryWrite
  backend.io.memoryWriteReady := io.memoryWriteReady

  backend.io.systemReadData := io.systemReadData
  backend.io.timer := io.timer
  backend.io.timerId := io.timerId
  io.systemReadValid := backend.io.systemReadValid
  io.systemReadAddress := backend.io.systemReadAddress
  backend.io.debugReadAddress := io.debugReadAddress
  io.debugReadData := backend.io.debugReadData

  io.commitValid := Mux(
    internalRedirectValid,
    B(0, config.commitWidth bits),
    backend.io.commitValid
  )
  io.commit := backend.io.commit
  io.recoveryValid := backend.io.recoveryValid && !internalRedirectValid
  io.recovery := backend.io.recovery
  io.debugCommitValid := backend.io.debugCommitValid
  io.debugCommit := backend.io.debugCommit
  io.csrWriteValid := backend.io.csrWriteValid
  io.csrWriteAddress := backend.io.csrWriteAddress
  io.csrWriteData := backend.io.csrWriteData
  io.csrWriteMask := backend.io.csrWriteMask
  io.serialCommitPc := backend.io.serialCommitPc
  io.ertnValid := backend.io.ertnValid
  io.idleValid := backend.io.idleValid
  io.refetchValid := backend.io.refetchValid
  io.cacheInvalidateValid := backend.io.cacheInvalidateValid
  io.dataCacheInvalidateValid := backend.io.dataCacheInvalidateValid
  io.dataCacheWritebackInvalidateValid :=
    backend.io.dataCacheWritebackInvalidateValid
  io.level2CacheInvalidateValid := backend.io.level2CacheInvalidateValid
  io.tlbSearchValid := backend.io.tlbSearchValid
  io.tlbReadValid := backend.io.tlbReadValid
  io.tlbWriteValid := backend.io.tlbWriteValid
  io.tlbFillValid := backend.io.tlbFillValid
  io.tlbInvalidateValid := backend.io.tlbInvalidateValid
  io.tlbInvalidateAsid := backend.io.tlbInvalidateAsid
  io.tlbInvalidateVpn := backend.io.tlbInvalidateVpn
  io.tlbInvalidateOperation := backend.io.tlbInvalidateOperation
  io.reservationBitSet := backend.io.reservationBitSet
  io.reservationBitValue := backend.io.reservationBitValue
  io.reservationAddressSet := backend.io.reservationAddressSet
  io.reservationLineAddressUpdate := backend.io.reservationLineAddressUpdate
  io.exceptionValid := backend.io.exceptionValid
  io.exceptionPc := backend.io.exceptionPc
  io.exception := backend.io.exception

  backend.io.cacheInvalidate := io.cacheInvalidate
  backend.io.dataCacheInvalidate := io.dataCacheInvalidate
  backend.io.dataCacheWritebackInvalidate := io.dataCacheWritebackInvalidate
  backend.io.level2CacheInvalidate := io.level2CacheInvalidate
  io.cacheInvalidateBusy := backend.io.cacheInvalidateBusy
  io.fetchPc := frontend.io.fetchPc
  io.frontendOccupancy := frontend.io.occupancy
}
