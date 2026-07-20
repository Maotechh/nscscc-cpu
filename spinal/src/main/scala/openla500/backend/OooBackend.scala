package openla500.backend

import openla500.core._
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

    val debugReadAddress = in UInt (config.archRegIndexWidth bits)
    val debugReadData = out Bits (config.xlen bits)

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
  val dispatchQueue = new OooDispatchQueue(config)
  val router = new OooDispatchRouter(config)
  val issueQueues = (0 until config.executionWidth).map(index => new OooIssueQueue(config, index))

  val issueAddressValid = RegInit(B(0, config.executionWidth bits))
  val issueAddressUop = Vec.fill(config.executionWidth)(Reg(OooRenamedUop(config)))
  val issueOperandValid = RegInit(B(0, config.executionWidth bits))
  val issueOperandUop = Vec.fill(config.executionWidth)(Reg(OooRenamedUop(config)))
  val issueOperandSource1 = Vec.fill(config.executionWidth)(Reg(Bits(config.xlen bits)))
  val issueOperandSource2 = Vec.fill(config.executionWidth)(Reg(Bits(config.xlen bits)))

  val renamedInput = Vec(OooRenamedUop(config), config.renameWidth)
  val dispatchInput = Vec(OooRenamedUop(config), config.renameWidth)
  for (lane <- 0 until config.renameWidth) {
    renamedInput(lane).decoded := io.rename(lane)
    renamedInput(lane).pdst := freeList.io.allocatePdst(lane)
    renamedInput(lane).oldPdst := registerMap.io.renameOldPdst(lane)
    renamedInput(lane).psrc1 := registerMap.io.renamePsrc1(lane)
    renamedInput(lane).psrc2 := registerMap.io.renamePsrc2(lane)
    renamedInput(lane).source1Ready := registerMap.io.renameSource1Ready(lane)
    renamedInput(lane).source2Ready := registerMap.io.renameSource2Ready(lane)
    renamedInput(lane).robPointer := rob.io.allocatedPointer(lane)
    renamedInput(lane).loadQueueIndex := lsqAllocator.io.allocateLoadIndex(lane)
    renamedInput(lane).storeQueueIndex := lsqAllocator.io.allocateStoreIndex(lane)

    dispatchInput(lane).decoded := renamedInput(lane).decoded
    dispatchInput(lane).pdst := renamedInput(lane).pdst
    dispatchInput(lane).oldPdst := renamedInput(lane).oldPdst
    dispatchInput(lane).psrc1 := renamedInput(lane).psrc1
    dispatchInput(lane).psrc2 := renamedInput(lane).psrc2
    dispatchInput(lane).source1Ready := False
    dispatchInput(lane).source2Ready := False
    dispatchInput(lane).robPointer := renamedInput(lane).robPointer
    dispatchInput(lane).loadQueueIndex := renamedInput(lane).loadQueueIndex
    dispatchInput(lane).storeQueueIndex := renamedInput(lane).storeQueueIndex
  }

  dispatchQueue.io.enqueueValid := io.renameValid
  dispatchQueue.io.enqueue := dispatchInput
  router.io.inputValid := dispatchQueue.io.dequeueValid
  for (lane <- 0 until config.dispatchWidth) {
    router.io.input(lane).decoded := dispatchQueue.io.dequeue(lane).decoded
    router.io.input(lane).pdst := dispatchQueue.io.dequeue(lane).pdst
    router.io.input(lane).oldPdst := dispatchQueue.io.dequeue(lane).oldPdst
    router.io.input(lane).psrc1 := dispatchQueue.io.dequeue(lane).psrc1
    router.io.input(lane).psrc2 := dispatchQueue.io.dequeue(lane).psrc2
    router.io.input(lane).source1Ready :=
      registerMap.io.physicalReady(dispatchQueue.io.dequeue(lane).psrc1)
    router.io.input(lane).source2Ready :=
      registerMap.io.physicalReady(dispatchQueue.io.dequeue(lane).psrc2)
    router.io.input(lane).robPointer := dispatchQueue.io.dequeue(lane).robPointer
    router.io.input(lane).loadQueueIndex := dispatchQueue.io.dequeue(lane).loadQueueIndex
    router.io.input(lane).storeQueueIndex := dispatchQueue.io.dequeue(lane).storeQueueIndex
  }
  router.io.flush := io.flush
  for (port <- 0 until config.executionWidth) {
    router.io.portReady(port) := issueQueues(port).io.enqueueReady
  }
  dispatchQueue.io.dequeueReady := router.io.inputReady

  rob.io.allocateValid := io.renameValid
  lsqAllocator.io.allocateValid := io.renameValid
  for (lane <- 0 until config.renameWidth) {
    lsqAllocator.io.allocateIsLoad(lane) := io.rename(lane).isLoad
    lsqAllocator.io.allocateIsStore(lane) := io.rename(lane).isStore
    freeList.io.allocateValid(lane) := io.renameValid(lane) &&
      io.rename(lane).writesGpr && io.rename(lane).rd =/= 0
  }
  val resourcesReady = dispatchQueue.io.enqueueReady && rob.io.allocateReady &&
    freeList.io.allocateReady && lsqAllocator.io.allocateReady && !io.flush
  val acceptAll = resourcesReady && io.renameValid.orR
  val accepted = Bits(config.renameWidth bits)
  val allLanes = B((BigInt(1) << config.renameWidth) - 1, config.renameWidth bits)
  accepted := Mux(acceptAll, io.renameValid, B(0, config.renameWidth bits))
  io.renameReady := Mux(resourcesReady, allLanes, B(0, config.renameWidth bits))

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
  dispatchQueue.io.enqueueAccept := acceptAll && !io.flush
  lsqAllocator.io.releaseLoadValid := io.releaseLoadValid
  lsqAllocator.io.releaseStoreValid := io.releaseStoreValid
  lsqAllocator.io.flush := io.flush
  for (lane <- 0 until config.renameWidth) {
    rob.io.allocate(lane).uop := renamedInput(lane)
    io.memoryAllocateValid(lane) := accepted(lane) &&
      (renamedInput(lane).decoded.isLoad || renamedInput(lane).decoded.isStore)
    io.memoryAllocate(lane).robPointer := renamedInput(lane).robPointer
    io.memoryAllocate(lane).isLoad := renamedInput(lane).decoded.isLoad
    io.memoryAllocate(lane).isStore := renamedInput(lane).decoded.isStore
    io.memoryAllocate(lane).loadQueueIndex := renamedInput(lane).loadQueueIndex
    io.memoryAllocate(lane).storeQueueIndex := renamedInput(lane).storeQueueIndex
  }

  for (port <- 0 until config.executionWidth) {
    issueQueues(port).io.enqueueValid := router.io.portValid(port)
    issueQueues(port).io.enqueue := router.io.portInput(port)
    issueQueues(port).io.robHeadPointer := rob.io.headPointer
    issueQueues(port).io.flush := io.flush
    prf.io.readAddress(port * 2) := issueAddressUop(port).psrc1
    prf.io.readAddress(port * 2 + 1) := issueAddressUop(port).psrc2

    val operandReady = !issueOperandValid(port) || io.issueReady(port)
    val addressReady = !issueAddressValid(port) || operandReady
    issueQueues(port).io.issueReady := addressReady
    when(io.flush) {
      issueAddressValid(port) := False
      issueOperandValid(port) := False
    }.otherwise {
      when(operandReady) {
        issueOperandValid(port) := issueAddressValid(port)
        when(issueAddressValid(port)) {
          issueOperandUop(port) := issueAddressUop(port)
          issueOperandSource1(port) := prf.io.readData(port * 2)
          issueOperandSource2(port) := prf.io.readData(port * 2 + 1)
        }
      }
      when(addressReady) {
        issueAddressValid(port) := issueQueues(port).io.issueValid
        when(issueQueues(port).io.issueValid) {
          issueAddressUop(port) := issueQueues(port).io.issue
        }
      }
    }

    io.issueValid(port) := issueOperandValid(port)
    io.issue(port) := issueOperandUop(port)
    io.issueSource1(port) := issueOperandSource1(port)
    io.issueSource2(port) := issueOperandSource2(port)
    issueQueues(port).io.wakeupValid := rob.io.completionWakeupValid
    for (write <- 0 until config.writebackWidth) {
      issueQueues(port).io.wakeupPdst(write) := rob.io.completionWakeupPdst(write)
    }
  }

  rob.io.completionValid := io.completionValid
  rob.io.completion := io.completion
  for (write <- 0 until config.writebackWidth) {
    prf.io.writeValid(write) := rob.io.completionWakeupValid(write)
    prf.io.write(write).pdst := rob.io.completionWakeupPdst(write)
    prf.io.write(write).data := rob.io.completionWakeupData(write)
    registerMap.io.writebackValid(write) :=
      rob.io.completionWakeupValid(write)
    registerMap.io.writebackPdst(write) := rob.io.completionWakeupPdst(write)
  }
  prf.io.debugReadAddress := registerMap.io.architecturalMappings(io.debugReadAddress)
  io.debugReadData := prf.io.debugReadData

  io.commitValid := rob.io.commitValid
  io.commit := rob.io.commit
  io.recoveryValid := rob.io.recoveryValid
  io.recovery := rob.io.recovery
  for (lane <- 0 until config.commitWidth) {
    val commitsDestination = rob.io.commitValid(lane) && rob.io.commit(lane).retired &&
      rob.io.commit(lane).writesGpr && rob.io.commit(lane).rd =/= 0
    registerMap.io.commitValid(lane) := commitsDestination
    freeList.io.commitFreeValid(lane) := commitsDestination
    registerMap.io.commitArch(lane) := rob.io.commit(lane).rd
    registerMap.io.commitPdst(lane) := rob.io.commit(lane).pdst
    freeList.io.commitFreePdst(lane) := rob.io.commit(lane).oldPdst
  }

  registerMap.io.flush := io.flush
  dispatchQueue.io.flush := io.flush
  freeList.io.flush := io.flush
  prf.io.flush := io.flush
  rob.io.flush := io.flush
}
