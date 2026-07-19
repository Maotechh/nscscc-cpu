package openla500.ooo

import spinal.core._
import spinal.lib._

final case class OooStoreQueueEntry(config: OooCoreConfig) extends Bundle {
  val valid = Bool()
  val addressReady = Bool()
  val committed = Bool()
  val robPointer = UInt(config.robPointerWidth bits)
  val virtualAddress = UInt(config.xlen bits)
  val size = Bits(3 bits)
  val byteMask = Bits(4 bits)
  val writeData = Bits(config.xlen bits)
}

final case class OooLoadQueueEntry(config: OooCoreConfig) extends Bundle {
  val valid = Bool()
  val addressReady = Bool()
  val requestSent = Bool()
  val completed = Bool()
  val robPointer = UInt(config.robPointerWidth bits)
  val pdst = UInt(config.physicalRegIndexWidth bits)
  val writesPdst = Bool()
  val virtualAddress = UInt(config.xlen bits)
  val size = Bits(3 bits)
  val byteMask = Bits(4 bits)
  val signExtend = Bool()
}

final class OooLoadStoreQueue(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private def isOlder(older: UInt, younger: UInt): Bool = {
    val distance = (younger - older).resize(config.robPointerWidth)
    (distance =/= U(0, config.robPointerWidth bits)) && !distance.msb
  }

  private def formatLoad(word: Bits, address: UInt, size: Bits, signExtend: Bool): Bits = {
    val shift = (address(1 downto 0) ## U(0, 3 bits)).asUInt
    val shifted = word |>> shift
    val byteUpper = Bits(24 bits)
    val halfUpper = Bits(16 bits)
    byteUpper := B(0, 24 bits)
    halfUpper := B(0, 16 bits)
    when(signExtend && shifted(7)) { byteUpper := B((BigInt(1) << 24) - 1, 24 bits) }
    when(signExtend && shifted(15)) { halfUpper := B((BigInt(1) << 16) - 1, 16 bits) }
    val result = Bits(config.xlen bits)
    result := shifted(config.xlen - 1 downto 0)
    when(size === B(0, 3 bits)) {
      result := byteUpper ## shifted(7 downto 0)
    }.elsewhen(size === B(1, 3 bits)) {
      result := halfUpper ## shifted(15 downto 0)
    }
    result
  }

  private def clearCompletion(completion: OooCompletion): Unit = {
    completion.robPointer := U(0, config.robPointerWidth bits)
    completion.pdst := U(0, config.physicalRegIndexWidth bits)
    completion.writesPdst := False
    completion.data := B(0, config.xlen bits)
    completion.sideEffectData := B(0, config.xlen bits)
    completion.exception.valid := False
    completion.exception.ecode := U(0, 6 bits)
    completion.exception.esubcode := U(0, 9 bits)
    completion.exception.badVAddrValid := False
    completion.exception.badVAddr := U(0, config.xlen bits)
    completion.exception.tlbRefill := False
    completion.branchResolved := False
    completion.branchTaken := False
    completion.branchTarget := U(0, config.xlen bits)
    completion.branchMispredict := False
  }

  val io = new Bundle {
    val allocateValid = in Bits (config.renameWidth bits)
    val allocate = in Vec (OooLsqAllocate(config), config.renameWidth)
    val aguValid = in Bool ()
    val agu = in(OooAguRequest(config))
    val aguReady = out Bool ()
    val commitValid = in Bits (config.commitWidth bits)
    val commit = in Vec (OooCommitRecord(config), config.commitWidth)
    val dataRequestValid = out Bool ()
    val dataRequest = out(OooCacheRequest(config))
    val dataRequestReady = in Bool ()
    val dataResponseValid = in Bool ()
    val dataResponse = in(OooCacheResponse(config))
    val completionValid = out Bool ()
    val completion = out(OooCompletion(config))
    val releaseLoadValid = out Bits (config.commitWidth bits)
    val releaseStoreValid = out Bits (config.commitWidth bits)
    val flush = in Bool ()
  }

  val stores = Vec.fill(config.storeQueueEntries)(Reg(OooStoreQueueEntry(config)))
  val loads = Vec.fill(config.loadQueueEntries)(Reg(OooLoadQueueEntry(config)))
  for (entry <- stores) {
    entry.valid.init(False)
    entry.addressReady.init(False)
    entry.committed.init(False)
  }
  for (entry <- loads) {
    entry.valid.init(False)
    entry.addressReady.init(False)
    entry.requestSent.init(False)
    entry.completed.init(False)
  }
  val storeHead = Reg(UInt(config.storeQueueIndexWidth bits)) init (0)
  val loadHead = Reg(UInt(config.loadQueueIndexWidth bits)) init (0)

  val headStore = stores(storeHead)
  val headLoad = loads(loadHead)
  val loadHeadReady = headLoad.valid && headLoad.addressReady &&
    !headLoad.requestSent && !headLoad.completed

  val unknownOlderStore = Bits(config.storeQueueEntries bits)
  val partialOverlapStore = Bits(config.storeQueueEntries bits)
  val forwardingStore = Bits(config.storeQueueEntries bits)
  for (entry <- 0 until config.storeQueueEntries) {
    val store = stores(entry)
    val older = store.valid && isOlder(store.robPointer, headLoad.robPointer)
    val sameWord = store.virtualAddress(config.xlen - 1 downto 2) ===
      headLoad.virtualAddress(config.xlen - 1 downto 2)
    val overlap = (store.byteMask & headLoad.byteMask).orR
    val covers = (store.byteMask & headLoad.byteMask) === headLoad.byteMask
    unknownOlderStore(entry) := older && !store.addressReady
    partialOverlapStore(entry) := older && store.addressReady && sameWord && overlap && !covers
    forwardingStore(entry) := older && store.addressReady && sameWord && covers
  }

  val forwardingCount = CountOne(forwardingStore)
  val forwardingId = OHToUInt(OHMasking.first(forwardingStore))
  val loadOrderClear = !unknownOlderStore.orR && !partialOverlapStore.orR
  val forwardCandidate = loadHeadReady && loadOrderClear && forwardingCount === 1
  val cacheLoadCandidate = loadHeadReady && loadOrderClear && forwardingCount === 0
  val storeRequest = headStore.valid && headStore.addressReady && headStore.committed

  io.dataRequestValid := !io.flush && (storeRequest || cacheLoadCandidate)
  io.dataRequest.virtualAddress := headLoad.virtualAddress
  io.dataRequest.physicalAddress := headLoad.virtualAddress
  io.dataRequest.isWrite := False
  io.dataRequest.size := headLoad.size
  io.dataRequest.byteMask := headLoad.byteMask
  io.dataRequest.writeData := B(0, config.xlen bits)
  io.dataRequest.uncached := False
  io.dataRequest.robPointer := headLoad.robPointer
  io.dataRequest.pdst := headLoad.pdst
  when(storeRequest) {
    io.dataRequest.virtualAddress := headStore.virtualAddress
    io.dataRequest.physicalAddress := headStore.virtualAddress
    io.dataRequest.isWrite := True
    io.dataRequest.size := headStore.size
    io.dataRequest.byteMask := headStore.byteMask
    io.dataRequest.writeData := headStore.writeData
    io.dataRequest.robPointer := headStore.robPointer
    io.dataRequest.pdst := U(0, config.physicalRegIndexWidth bits)
  }
  val dataRequestFire = io.dataRequestValid && io.dataRequestReady
  val storeRequestFire = dataRequestFire && storeRequest
  val loadRequestFire = dataRequestFire && !storeRequest

  val responseAccepted = io.dataResponseValid && headLoad.valid && headLoad.requestSent &&
    !headLoad.completed && io.dataResponse.robPointer === headLoad.robPointer
  val forwardFire = !io.dataResponseValid && forwardCandidate

  val aguMisaligned = (io.agu.size === B(2, 3 bits) && io.agu.virtualAddress(1 downto 0) =/= 0) ||
    (io.agu.size === B(1, 3 bits) && io.agu.virtualAddress(0))
  val aguTargetAvailable = Mux(
    io.agu.isWrite,
    stores(io.agu.uop.storeQueueIndex).valid &&
      stores(io.agu.uop.storeQueueIndex).robPointer === io.agu.uop.robPointer &&
      !stores(io.agu.uop.storeQueueIndex).addressReady,
    loads(io.agu.uop.loadQueueIndex).valid &&
      loads(io.agu.uop.loadQueueIndex).robPointer === io.agu.uop.robPointer &&
      !loads(io.agu.uop.loadQueueIndex).addressReady
  )
  val aguProducesCompletion = io.agu.isWrite || aguMisaligned
  val completionPortAvailable = !io.dataResponseValid && !forwardCandidate
  io.aguReady := !io.flush && aguTargetAvailable &&
    (!aguProducesCompletion || completionPortAvailable)
  val aguFire = io.aguValid && io.aguReady
  val aguCompletionFire = aguFire && aguProducesCompletion

  val generatedCompletionValid = responseAccepted || forwardFire || aguCompletionFire
  val generatedCompletion = OooCompletion(config)
  clearCompletion(generatedCompletion)
  when(responseAccepted) {
    generatedCompletion.robPointer := headLoad.robPointer
    generatedCompletion.pdst := headLoad.pdst
    generatedCompletion.writesPdst := headLoad.writesPdst
    generatedCompletion.data := formatLoad(
      io.dataResponse.data,
      headLoad.virtualAddress,
      headLoad.size,
      headLoad.signExtend
    )
    when(io.dataResponse.error) {
      generatedCompletion.exception.valid := True
      generatedCompletion.exception.ecode := U(8, 6 bits)
      generatedCompletion.exception.badVAddrValid := True
      generatedCompletion.exception.badVAddr := headLoad.virtualAddress
    }
  }.elsewhen(forwardFire) {
    generatedCompletion.robPointer := headLoad.robPointer
    generatedCompletion.pdst := headLoad.pdst
    generatedCompletion.writesPdst := headLoad.writesPdst
    generatedCompletion.data := formatLoad(
      stores(forwardingId).writeData,
      headLoad.virtualAddress,
      headLoad.size,
      headLoad.signExtend
    )
  }.elsewhen(aguCompletionFire) {
    generatedCompletion.robPointer := io.agu.uop.robPointer
    generatedCompletion.pdst := io.agu.uop.pdst
    generatedCompletion.writesPdst := io.agu.uop.decoded.writesGpr
    generatedCompletion.data := Mux(
      io.agu.uop.decoded.isSc,
      B(1, config.xlen bits),
      B(0, config.xlen bits)
    )
    generatedCompletion.sideEffectData := io.agu.writeData
    generatedCompletion.exception := io.agu.uop.decoded.exception
    when(aguMisaligned) {
      generatedCompletion.exception.valid := True
      generatedCompletion.exception.ecode := U(9, 6 bits)
      generatedCompletion.exception.esubcode := U(0, 9 bits)
      generatedCompletion.exception.badVAddrValid := True
      generatedCompletion.exception.badVAddr := io.agu.virtualAddress
      generatedCompletion.exception.tlbRefill := False
    }
  }

  val completionValid = RegInit(False)
  val completion = Reg(OooCompletion(config))
  when(io.flush) {
    completionValid := False
  }.otherwise {
    completionValid := generatedCompletionValid
    when(generatedCompletionValid) { completion := generatedCompletion }
  }
  io.completionValid := completionValid
  io.completion := completion

  io.releaseLoadValid := B(0, config.commitWidth bits)
  io.releaseStoreValid := B(0, config.commitWidth bits)
  for (lane <- 0 until config.commitWidth) {
    val loadCommitMatch = io.commitValid(lane) && io.commit(lane).isLoad &&
      loads(io.commit(lane).loadQueueIndex).valid &&
      loads(io.commit(lane).loadQueueIndex).robPointer === io.commit(lane).robPointer
    io.releaseLoadValid(lane) := !io.flush && loadCommitMatch
  }
  io.releaseStoreValid(0) := !io.flush && storeRequestFire

  when(io.flush) {
    storeHead := 0
    loadHead := 0
    for (entry <- stores) {
      entry.valid := False
      entry.addressReady := False
      entry.committed := False
    }
    for (entry <- loads) {
      entry.valid := False
      entry.addressReady := False
      entry.requestSent := False
      entry.completed := False
    }
  }.otherwise {
    for (lane <- 0 until config.renameWidth) {
      when(io.allocateValid(lane) && io.allocate(lane).isStore) {
        val index = io.allocate(lane).storeQueueIndex
        stores(index).valid := True
        stores(index).addressReady := False
        stores(index).committed := False
        stores(index).robPointer := io.allocate(lane).robPointer
      }
      when(io.allocateValid(lane) && io.allocate(lane).isLoad) {
        val index = io.allocate(lane).loadQueueIndex
        loads(index).valid := True
        loads(index).addressReady := False
        loads(index).requestSent := False
        loads(index).completed := False
        loads(index).robPointer := io.allocate(lane).robPointer
      }
    }

    when(aguFire && io.agu.isWrite) {
      val index = io.agu.uop.storeQueueIndex
      stores(index).virtualAddress := io.agu.virtualAddress
      stores(index).size := io.agu.size
      stores(index).byteMask := io.agu.byteMask
      stores(index).writeData := io.agu.writeData
      stores(index).addressReady := !aguMisaligned
    }
    when(aguFire && !io.agu.isWrite) {
      val index = io.agu.uop.loadQueueIndex
      loads(index).pdst := io.agu.uop.pdst
      loads(index).writesPdst := io.agu.uop.decoded.writesGpr
      loads(index).virtualAddress := io.agu.virtualAddress
      loads(index).size := io.agu.size
      loads(index).byteMask := io.agu.byteMask
      loads(index).signExtend := io.agu.uop.decoded.memorySignExtend
      loads(index).addressReady := !aguMisaligned
      loads(index).completed := aguMisaligned
    }

    for (lane <- 0 until config.commitWidth) {
      when(io.releaseLoadValid(lane)) {
        loads(io.commit(lane).loadQueueIndex).valid := False
      }
      when(
        io.commitValid(lane) && io.commit(lane).isStore &&
          !io.commit(lane).exception.valid &&
          stores(io.commit(lane).storeQueueIndex).valid &&
          stores(io.commit(lane).storeQueueIndex).robPointer === io.commit(lane).robPointer
      ) {
        stores(io.commit(lane).storeQueueIndex).committed := True
      }
    }

    when(loadRequestFire) { loads(loadHead).requestSent := True }
    when(responseAccepted || forwardFire) {
      loads(loadHead).completed := True
      loadHead := loadHead + 1
    }.elsewhen(headLoad.valid && headLoad.completed) {
      loadHead := loadHead + 1
    }
    when(storeRequestFire) {
      stores(storeHead).valid := False
      stores(storeHead).addressReady := False
      stores(storeHead).committed := False
      storeHead := storeHead + 1
    }
  }
}
