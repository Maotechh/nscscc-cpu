package openla500.ooo

import spinal.core._

final class OooBackendWithExecution(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit
) extends Component {
  val io = new Bundle {
    val renameValid = in Bits (config.renameWidth bits)
    val rename = in Vec (OooDecodedUop(config), config.renameWidth)
    val renameReady = out Bits (config.renameWidth bits)
    val dataRequestValid = out Bool ()
    val dataRequest = out(OooCacheRequest(config))
    val dataRequestReady = in Bool ()
    val dataResponseValid = in Bool ()
    val dataResponse = in(OooCacheResponse(config))
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
    val flush = in Bool ()
  }

  val backend = new OooBackend(config)
  val execution = new OooExecutionCluster(config)
  val loadStoreQueue = new OooLoadStoreQueue(config)
  val commitAdapter = new OooCommitAdapter(config)

  backend.io.renameValid := io.renameValid
  backend.io.rename := io.rename
  backend.io.releaseLoadValid := loadStoreQueue.io.releaseLoadValid
  backend.io.releaseStoreValid := loadStoreQueue.io.releaseStoreValid
  io.renameReady := backend.io.renameReady
  loadStoreQueue.io.allocateValid := backend.io.memoryAllocateValid
  loadStoreQueue.io.allocate := backend.io.memoryAllocate

  execution.io.issueValid := backend.io.issueValid
  execution.io.issue := backend.io.issue
  execution.io.source1 := backend.io.issueSource1
  execution.io.source2 := backend.io.issueSource2
  backend.io.issueReady := execution.io.issueReady

  execution.io.aguReady := loadStoreQueue.io.aguReady
  execution.io.loadStoreCompletionValid := loadStoreQueue.io.completionValid
  execution.io.loadStoreCompletion := loadStoreQueue.io.completion
  execution.io.systemReadData := io.systemReadData
  execution.io.timer := io.timer
  execution.io.timerId := io.timerId
  loadStoreQueue.io.aguValid := execution.io.aguValid
  loadStoreQueue.io.agu := execution.io.agu
  loadStoreQueue.io.commitValid := backend.io.commitValid
  loadStoreQueue.io.commit := backend.io.commit
  loadStoreQueue.io.dataRequestReady := io.dataRequestReady
  loadStoreQueue.io.dataResponseValid := io.dataResponseValid
  loadStoreQueue.io.dataResponse := io.dataResponse
  io.dataRequestValid := loadStoreQueue.io.dataRequestValid
  io.dataRequest := loadStoreQueue.io.dataRequest
  io.systemReadValid := execution.io.systemReadValid
  io.systemReadAddress := execution.io.systemReadAddress

  backend.io.completionValid := execution.io.completionValid
  backend.io.completion := execution.io.completion
  io.commitValid := backend.io.commitValid
  io.commit := backend.io.commit
  io.recoveryValid := backend.io.recoveryValid
  io.recovery := backend.io.recovery

  commitAdapter.io.commitValid := backend.io.commitValid
  commitAdapter.io.commit := backend.io.commit
  commitAdapter.io.flush := io.flush
  io.debugCommitValid := commitAdapter.io.debugCommitValid
  io.debugCommit := commitAdapter.io.debugCommit
  io.csrWriteValid := commitAdapter.io.csrWriteValid
  io.csrWriteAddress := commitAdapter.io.csrAddress
  io.csrWriteData := commitAdapter.io.csrWriteData
  io.csrWriteMask := commitAdapter.io.csrMask
  io.ertnValid := commitAdapter.io.ertnValid
  io.refetchValid := commitAdapter.io.refetchValid
  io.tlbSearchValid := commitAdapter.io.tlbSearchValid
  io.tlbReadValid := commitAdapter.io.tlbReadValid
  io.tlbWriteValid := commitAdapter.io.tlbWriteValid
  io.tlbFillValid := commitAdapter.io.tlbFillValid
  io.tlbInvalidateValid := commitAdapter.io.tlbInvalidateValid
  io.exceptionValid := commitAdapter.io.exceptionValid
  io.exceptionPc := commitAdapter.io.exceptionPc
  io.exception := commitAdapter.io.exception

  backend.io.flush := io.flush
  execution.io.flush := io.flush
  loadStoreQueue.io.flush := io.flush
}
