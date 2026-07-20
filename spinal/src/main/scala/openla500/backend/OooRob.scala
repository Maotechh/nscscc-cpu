package openla500.backend

import openla500.core._
import spinal.core._
import spinal.lib._

final case class OooRobEntry(config: OooCoreConfig) extends Bundle {
  val valid = Bool()
  val complete = Bool()
  val pointer = UInt(config.robPointerWidth bits)
  val uop = OooRenamedUop(config)
  val result = Bits(config.xlen bits)
  val sideEffectData = Bits(config.xlen bits)
  val exception = OooExceptionMeta()
  val branchMispredict = Bool()
  val branchTarget = UInt(config.xlen bits)
}

final class OooRob(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit) extends Component {
  private def selectLowest(mask: Bits, width: Int): UInt = {
    val selected = UInt(width bits)
    selected := 0
    for (index <- (0 until mask.getWidth).reverse) {
      when(mask(index)) { selected := U(index, width bits) }
    }
    selected
  }

  val io = new Bundle {
    val allocateValid = in Bits (config.renameWidth bits)
    val allocate = in Vec (OooRobAllocate(config), config.renameWidth)
    val allocateReady = out Bool ()
    val allocateAccept = in Bool ()
    val allocatedPointer = out Vec (UInt(config.robPointerWidth bits), config.renameWidth)

    val completionValid = in Bits (config.writebackWidth bits)
    val completion = in Vec (OooCompletion(config), config.writebackWidth)
    val completionAccepted = out Bits (config.writebackWidth bits)

    val commitValid = out Bits (config.commitWidth bits)
    val commit = out Vec (OooCommitRecord(config), config.commitWidth)
    val recoveryValid = out Bool ()
    val recovery = out(OooRecoveryRequest(config))

    val flush = in Bool ()
    val empty = out Bool ()
    val occupancy = out UInt (log2Up(config.robEntries + 1) bits)
    val headPointer = out UInt (config.robPointerWidth bits)
  }

  val allocatePointer = Reg(UInt(config.robPointerWidth bits)) init (0)
  val commitPointer = Reg(UInt(config.robPointerWidth bits)) init (0)
  val occupancy = Reg(UInt(log2Up(config.robEntries + 1) bits)) init (0)
  val entries = Vec.fill(config.robEntries)(Reg(OooRobEntry(config)))
  for (entry <- entries) {
    entry.valid.init(False)
    entry.complete.init(False)
  }

  val allocatePrefix = Vec(UInt(log2Up(config.renameWidth + 1) bits), config.renameWidth + 1)
  allocatePrefix(0) := U(0, allocatePrefix(0).getWidth bits)
  for (lane <- 0 until config.renameWidth) {
    allocatePrefix(lane + 1) := allocatePrefix(lane) + io.allocateValid(lane).asUInt
    io.allocatedPointer(lane) := (allocatePointer + allocatePrefix(lane)).resized
  }

  val requested = allocatePrefix(config.renameWidth)
  val freeSlots = U(config.robEntries, occupancy.getWidth bits) - occupancy
  io.allocateReady := !io.flush && freeSlots >= requested

  for (lane <- 0 until config.renameWidth) {
    when(io.allocateAccept && io.allocateValid(lane)) {
      val destination = (allocatePointer + allocatePrefix(lane)).resized
      entries(destination(config.robIndexWidth - 1 downto 0)).valid := True
      entries(destination(config.robIndexWidth - 1 downto 0)).complete :=
        io.allocate(lane).uop.decoded.exception.valid
      entries(destination(config.robIndexWidth - 1 downto 0)).pointer := destination
      entries(destination(config.robIndexWidth - 1 downto 0)).uop := io.allocate(lane).uop
      entries(destination(config.robIndexWidth - 1 downto 0)).result := B(0, config.xlen bits)
      entries(destination(config.robIndexWidth - 1 downto 0)).sideEffectData :=
        B(0, config.xlen bits)
      entries(destination(config.robIndexWidth - 1 downto 0)).exception :=
        io.allocate(lane).uop.decoded.exception
      entries(destination(config.robIndexWidth - 1 downto 0)).branchMispredict := False
      entries(destination(config.robIndexWidth - 1 downto 0)).branchTarget := U(0, config.xlen bits)
    }
  }

  val candidates = Vec(OooRobEntry(config), config.commitWidth)
  for (lane <- 0 until config.commitWidth) {
    val pointer = (commitPointer + U(lane, config.robPointerWidth bits)).resized
    candidates(lane) := entries(pointer(config.robIndexWidth - 1 downto 0))
  }

  val canCommit = Vec(Bool(), config.commitWidth)
  val stopAfter = Vec(Bool(), config.commitWidth)
  for (lane <- 0 until config.commitWidth) {
    stopAfter(lane) := candidates(lane).exception.valid ||
      candidates(lane).uop.decoded.serializing || candidates(lane).branchMispredict
    if (lane == 0) {
      canCommit(lane) := candidates(lane).valid && candidates(lane).complete
    } else {
      canCommit(lane) := candidates(lane).valid && candidates(lane).complete &&
        canCommit(lane - 1) && !stopAfter(lane - 1)
    }
    io.commitValid(lane) := canCommit(lane)
    io.commit(lane).pc := candidates(lane).uop.decoded.pc
    io.commit(lane).instruction := candidates(lane).uop.decoded.instruction
    io.commit(lane).robPointer := candidates(lane).pointer
    io.commit(lane).rd := candidates(lane).uop.decoded.rd
    io.commit(lane).pdst := candidates(lane).uop.pdst
    io.commit(lane).oldPdst := candidates(lane).uop.oldPdst
    io.commit(lane).writesGpr := candidates(lane).uop.decoded.writesGpr
    io.commit(lane).result := candidates(lane).result
    io.commit(lane).systemOperation := candidates(lane).uop.decoded.systemOperation
    io.commit(lane).csrAddress := candidates(lane).uop.decoded.csrAddress
    io.commit(lane).csrWrite := candidates(lane).uop.decoded.csrWrite
    io.commit(lane).csrMask := candidates(lane).uop.decoded.csrMask
    io.commit(lane).sideEffectData := candidates(lane).sideEffectData
    io.commit(lane).retired := canCommit(lane) && !candidates(lane).exception.valid
    io.commit(lane).serializing := candidates(lane).uop.decoded.serializing
    io.commit(lane).isLoad := candidates(lane).uop.decoded.isLoad
    io.commit(lane).isStore := candidates(lane).uop.decoded.isStore
    io.commit(lane).loadQueueIndex := candidates(lane).uop.loadQueueIndex
    io.commit(lane).storeQueueIndex := candidates(lane).uop.storeQueueIndex
    io.commit(lane).exception := candidates(lane).exception
  }

  val committedCount = CountOne(io.commitValid)
  val recoveryMask = Bits(config.commitWidth bits)
  for (lane <- 0 until config.commitWidth) {
    recoveryMask(lane) := io.commitValid(lane) &&
      (candidates(lane).exception.valid || candidates(lane).branchMispredict)
  }
  io.recoveryValid := recoveryMask.orR
  io.recovery.cause := OooRecoveryCause.none
  io.recovery.robPointer := U(0, config.robPointerWidth bits)
  io.recovery.target := U(0, config.xlen bits)
  io.recovery.exception.valid := False
  io.recovery.exception.ecode := U(0, 6 bits)
  io.recovery.exception.esubcode := U(0, 9 bits)
  io.recovery.exception.badVAddrValid := False
  io.recovery.exception.badVAddr := U(0, 32 bits)
  io.recovery.exception.tlbRefill := False
  when(recoveryMask.orR) {
    val recoveryIndex = selectLowest(recoveryMask, log2Up(config.commitWidth))
    io.recovery.robPointer := candidates(recoveryIndex).pointer
    io.recovery.target := candidates(recoveryIndex).branchTarget
    io.recovery.exception := candidates(recoveryIndex).exception
    when(candidates(recoveryIndex).exception.valid) {
      io.recovery.cause := OooRecoveryCause.exception
    }.otherwise {
      io.recovery.cause := OooRecoveryCause.branchMispredict
    }
  }

  for (lane <- 0 until config.writebackWidth) {
    io.completionAccepted(lane) := False
    when(io.completionValid(lane)) {
      val source = io.completion(lane)
      val index = source.robPointer(config.robIndexWidth - 1 downto 0)
      when(entries(index).valid && entries(index).pointer === source.robPointer) {
        io.completionAccepted(lane) := True
        entries(index).complete := True
        entries(index).result := source.data
        entries(index).sideEffectData := source.sideEffectData
        entries(index).exception := source.exception
        when(source.branchResolved) {
          entries(index).branchMispredict := source.branchMispredict
          entries(index).branchTarget := source.branchTarget
        }
      }
    }
  }

  when(io.flush) {
    // Keep the next-free pointer across a flush so delayed completions from
    // the discarded window cannot alias the first entry of the new window.
    commitPointer := allocatePointer
    occupancy := U(0, occupancy.getWidth bits)
    for (entry <- entries) {
      entry.valid := False
      entry.complete := False
    }
  }.otherwise {
    when(io.allocateAccept) {
      allocatePointer := allocatePointer + requested
    }
    for (lane <- 0 until config.commitWidth) {
      when(io.commitValid(lane)) {
        val pointer = (commitPointer + U(lane, config.robPointerWidth bits)).resized
        entries(pointer(config.robIndexWidth - 1 downto 0)).valid := False
      }
    }
    commitPointer := commitPointer + committedCount
    occupancy := occupancy + Mux(io.allocateAccept, requested, 0) - committedCount
  }

  io.empty := occupancy === 0
  io.occupancy := occupancy
  io.headPointer := commitPointer
}
