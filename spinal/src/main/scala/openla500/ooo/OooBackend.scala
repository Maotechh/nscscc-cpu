package openla500.ooo

import spinal.core._

final class OooBackend(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  val io = new Bundle {
    val renameValid = in Bits (config.renameWidth bits)
    val rename = in Vec (OooDecodedUop(config), config.renameWidth)
    val renameReady = out Bits (config.renameWidth bits)

    val issueValid = out Bits (config.executionWidth bits)
    val issue = out Vec (OooRenamedUop(config), config.executionWidth)
    val issueSource1 = out Vec (Bits(config.xlen bits), config.executionWidth)
    val issueSource2 = out Vec (Bits(config.xlen bits), config.executionWidth)
    val issueReady = in Bits (config.executionWidth bits)

    val completionValid = in Bits (config.writebackWidth bits)
    val completion = in Vec (OooCompletion(config), config.writebackWidth)
    val memoryAllocateValid = out Bits (config.renameWidth bits)
    val memoryAllocate = out Vec (OooLsqAllocate(config), config.renameWidth)
    val releaseLoadValid = in Bits (config.commitWidth bits)
    val releaseStoreValid = in Bits (config.commitWidth bits)

    val commitValid = out Bits (config.commitWidth bits)
    val commit = out Vec (OooCommitRecord(config), config.commitWidth)
    val recoveryValid = out Bool ()
    val recovery = out(OooRecoveryRequest(config))
    val flush = in Bool ()
  }

  val registerMap = new OooRegisterMap(config)
  val freeList = new OooFreeList(config)
  val rob = new OooRob(config)
  val lsqAllocator = new OooLsqAllocator(config)
  val prf = new OooPhysicalRegisterFile(config)
  val router = new OooDispatchRouter(config)
  val issueQueues = (0 until config.executionWidth).map(index => new OooIssueQueue(config, index))

  val wakeupCompletionValid = RegInit(B(0, config.writebackWidth bits))
  val wakeupCompletion = Vec.fill(config.writebackWidth)(Reg(OooCompletion(config)))
  when(io.flush) {
    wakeupCompletionValid := B(0, config.writebackWidth bits)
  }.otherwise {
    wakeupCompletionValid := io.completionValid & rob.io.completionAccepted
    for (write <- 0 until config.writebackWidth) {
      wakeupCompletion(write) := io.completion(write)
    }
  }

  val issuePipeValid = RegInit(B(0, config.executionWidth bits))
  val issuePipeUop = Vec.fill(config.executionWidth)(Reg(OooRenamedUop(config)))
  val issuePipeSource1 = Vec.fill(config.executionWidth)(Reg(Bits(config.xlen bits)))
  val issuePipeSource2 = Vec.fill(config.executionWidth)(Reg(Bits(config.xlen bits)))

  router.io.inputValid := io.renameValid
  for (lane <- 0 until config.renameWidth) {
    router.io.input(lane).decoded := io.rename(lane)
    router.io.input(lane).pdst := freeList.io.allocatePdst(lane)
    router.io.input(lane).oldPdst := registerMap.io.renameOldPdst(lane)
    router.io.input(lane).psrc1 := registerMap.io.renamePsrc1(lane)
    router.io.input(lane).psrc2 := registerMap.io.renamePsrc2(lane)
    router.io.input(lane).source1Ready := registerMap.io.renameSource1Ready(lane)
    router.io.input(lane).source2Ready := registerMap.io.renameSource2Ready(lane)
    router.io.input(lane).robPointer := rob.io.allocatedPointer(lane)
    router.io.input(lane).loadQueueIndex := lsqAllocator.io.allocateLoadIndex(lane)
    router.io.input(lane).storeQueueIndex := lsqAllocator.io.allocateStoreIndex(lane)
  }
  router.io.flush := io.flush
  for (port <- 0 until config.executionWidth) {
    router.io.portReady(port) := issueQueues(port).io.enqueueReady
  }

  val routingRequest = Bits(config.renameWidth bits)
  for (lane <- 0 until config.renameWidth) {
    routingRequest(lane) := io.renameValid(lane) && router.io.inputReady(lane)
  }

  rob.io.allocateValid := routingRequest
  lsqAllocator.io.allocateValid := routingRequest
  for (lane <- 0 until config.renameWidth) {
    lsqAllocator.io.allocateIsLoad(lane) := io.rename(lane).isLoad
    lsqAllocator.io.allocateIsStore(lane) := io.rename(lane).isStore
    freeList.io.allocateValid(lane) := routingRequest(lane) &&
      io.rename(lane).writesGpr && io.rename(lane).rd =/= 0
  }
  val acceptAll = rob.io.allocateReady && freeList.io.allocateReady &&
    lsqAllocator.io.allocateReady && routingRequest.orR
  val accepted = Bits(config.renameWidth bits)
  val allLanes = B((BigInt(1) << config.renameWidth) - 1, config.renameWidth bits)
  accepted := routingRequest & allLanes
  when(!acceptAll || io.flush) { accepted := B(0, config.renameWidth bits) }
  io.renameReady := router.io.inputReady
  when(!rob.io.allocateReady || !freeList.io.allocateReady || io.flush) {
    io.renameReady := B(0, config.renameWidth bits)
  }

  registerMap.io.renameValid := accepted
  for (lane <- 0 until config.renameWidth) {
    registerMap.io.renameSource1(lane) := io.rename(lane).rs1
    registerMap.io.renameSource2(lane) := io.rename(lane).rs2
    registerMap.io.renameDestination(lane) := Mux(
      io.rename(lane).writesGpr,
      io.rename(lane).rd,
      U(0, config.archRegIndexWidth bits)
    )
    registerMap.io.renamePdst(lane) := freeList.io.allocatePdst(lane)
  }

  rob.io.allocateAccept := acceptAll && !io.flush
  freeList.io.allocateAccept := acceptAll && !io.flush
  lsqAllocator.io.allocateAccept := acceptAll && !io.flush
  lsqAllocator.io.releaseLoadValid := io.releaseLoadValid
  lsqAllocator.io.releaseStoreValid := io.releaseStoreValid
  lsqAllocator.io.flush := io.flush
  for (lane <- 0 until config.renameWidth) {
    rob.io.allocate(lane).uop := router.io.input(lane)
    io.memoryAllocateValid(lane) := accepted(lane) &&
      (router.io.input(lane).decoded.isLoad || router.io.input(lane).decoded.isStore)
    io.memoryAllocate(lane).robPointer := router.io.input(lane).robPointer
    io.memoryAllocate(lane).isLoad := router.io.input(lane).decoded.isLoad
    io.memoryAllocate(lane).isStore := router.io.input(lane).decoded.isStore
    io.memoryAllocate(lane).loadQueueIndex := router.io.input(lane).loadQueueIndex
    io.memoryAllocate(lane).storeQueueIndex := router.io.input(lane).storeQueueIndex
  }

  for (port <- 0 until config.executionWidth) {
    issueQueues(port).io.enqueueValid := router.io.portValid(port) && acceptAll
    issueQueues(port).io.enqueue := router.io.portInput(port)
    issueQueues(port).io.robHeadPointer := rob.io.headPointer
    issueQueues(port).io.flush := io.flush
    prf.io.readAddress(port * 2) := issueQueues(port).io.issue.psrc1
    prf.io.readAddress(port * 2 + 1) := issueQueues(port).io.issue.psrc2

    val issuePipeReady = !issuePipeValid(port) || io.issueReady(port)
    issueQueues(port).io.issueReady := issuePipeReady
    when(io.flush) {
      issuePipeValid(port) := False
    }.elsewhen(issuePipeReady) {
      issuePipeValid(port) := issueQueues(port).io.issueValid
      when(issueQueues(port).io.issueValid) {
        issuePipeUop(port) := issueQueues(port).io.issue
        issuePipeSource1(port) := prf.io.readData(port * 2)
        issuePipeSource2(port) := prf.io.readData(port * 2 + 1)
      }
    }

    io.issueValid(port) := issuePipeValid(port)
    io.issue(port) := issuePipeUop(port)
    io.issueSource1(port) := issuePipeSource1(port)
    io.issueSource2(port) := issuePipeSource2(port)
    issueQueues(port).io.wakeupValid := wakeupCompletionValid
    for (write <- 0 until config.writebackWidth) {
      issueQueues(port).io.wakeupPdst(write) := wakeupCompletion(write).pdst
    }
  }

  rob.io.completionValid := io.completionValid
  rob.io.completion := io.completion
  for (write <- 0 until config.writebackWidth) {
    prf.io.writeValid(write) := wakeupCompletionValid(write) && wakeupCompletion(write).writesPdst
    prf.io.write(write).pdst := wakeupCompletion(write).pdst
    prf.io.write(write).data := wakeupCompletion(write).data
    registerMap.io.writebackValid(write) :=
      wakeupCompletionValid(write) && wakeupCompletion(write).writesPdst
    registerMap.io.writebackPdst(write) := wakeupCompletion(write).pdst
  }

  io.commitValid := rob.io.commitValid
  io.commit := rob.io.commit
  io.recoveryValid := rob.io.recoveryValid
  io.recovery := rob.io.recovery
  for (lane <- 0 until config.commitWidth) {
    registerMap.io.commitValid(lane) := rob.io.commitValid(lane) && rob.io.commit(lane).writesGpr
    freeList.io.commitFreeValid(lane) := rob.io.commitValid(lane) && rob.io.commit(lane).writesGpr
    registerMap.io.commitArch(lane) := rob.io.commit(lane).rd
    registerMap.io.commitPdst(lane) := rob.io.commit(lane).pdst
    freeList.io.commitFreePdst(lane) := rob.io.commit(lane).oldPdst
  }

  registerMap.io.flush := io.flush
  freeList.io.architecturalMappings := registerMap.io.architecturalMappings
  freeList.io.flush := io.flush
  prf.io.flush := io.flush
  rob.io.flush := io.flush
}
