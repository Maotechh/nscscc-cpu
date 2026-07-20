package openla500.backend

import openla500.core._
import spinal.core._
import spinal.lib._

final case class OooPrfWrite(config: OooCoreConfig) extends Bundle {
  val pdst = UInt(config.physicalRegIndexWidth bits)
  val data = Bits(config.xlen bits)
}

final class OooPhysicalRegisterFile(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  val io = new Bundle {
    val readAddress = in Vec (UInt(config.physicalRegIndexWidth bits), config.executionWidth * 2)
    val readData = out Vec (Bits(config.xlen bits), config.executionWidth * 2)
    val writeValid = in Bits (config.writebackWidth bits)
    val write = in Vec (OooPrfWrite(config), config.writebackWidth)
    val debugReadAddress = in UInt (config.physicalRegIndexWidth bits)
    val debugReadData = out Bits (config.xlen bits)
    val flush = in Bool ()
  }

  val registers = Vec.fill(config.physicalRegs)(Reg(Bits(config.xlen bits)))
  registers(0) := B(0, config.xlen bits)

  for (readPort <- 0 until config.executionWidth * 2) {
    val selected = Bits(config.xlen bits)
    selected := Mux(
      io.readAddress(readPort) === 0,
      B(0, config.xlen bits),
      registers(io.readAddress(readPort))
    )
    for (writePort <- (0 until config.writebackWidth).reverse) {
      when(io.writeValid(writePort) && io.write(writePort).pdst === io.readAddress(readPort)) {
        selected := io.write(writePort).data
      }
    }
    io.readData(readPort) := selected
  }

  io.debugReadData := Mux(
    io.debugReadAddress === 0,
    B(0, config.xlen bits),
    registers(io.debugReadAddress)
  )
  for (writePort <- (0 until config.writebackWidth).reverse) {
    when(io.writeValid(writePort) && io.write(writePort).pdst === io.debugReadAddress) {
      io.debugReadData := io.write(writePort).data
    }
  }

  for (writePort <- 0 until config.writebackWidth) {
    when(io.writeValid(writePort) && io.write(writePort).pdst =/= 0) {
      registers(io.write(writePort).pdst) := io.write(writePort).data
    }
  }
  when(io.flush) { registers(0) := B(0, config.xlen bits) }
}

final class OooRegisterMap(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  val io = new Bundle {
    val renameValid = in Bits (config.renameWidth bits)
    val renameSource1 = in Vec (UInt(config.archRegIndexWidth bits), config.renameWidth)
    val renameSource2 = in Vec (UInt(config.archRegIndexWidth bits), config.renameWidth)
    val renameDestination = in Vec (UInt(config.archRegIndexWidth bits), config.renameWidth)
    val renamePdst = in Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)
    val renamePsrc1 = out Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)
    val renamePsrc2 = out Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)
    val renameSource1Ready = out Bits (config.renameWidth bits)
    val renameSource2Ready = out Bits (config.renameWidth bits)
    val renameOldPdst = out Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)

    val writebackValid = in Bits (config.writebackWidth bits)
    val writebackPdst = in Vec (UInt(config.physicalRegIndexWidth bits), config.writebackWidth)

    val commitValid = in Bits (config.commitWidth bits)
    val commitArch = in Vec (UInt(config.archRegIndexWidth bits), config.commitWidth)
    val commitPdst = in Vec (UInt(config.physicalRegIndexWidth bits), config.commitWidth)
    val commitPreviousPdst = out Vec (UInt(config.physicalRegIndexWidth bits), config.commitWidth)

    val architecturalMappings = out Vec (UInt(config.physicalRegIndexWidth bits), config.archRegs)
    val physicalReady = out Bits (config.physicalRegs bits)
    val flush = in Bool ()
  }

  val speculative = Vec.fill(config.archRegs)(Reg(UInt(config.physicalRegIndexWidth bits)) init (0))
  val architectural =
    Vec.fill(config.archRegs)(Reg(UInt(config.physicalRegIndexWidth bits)) init (0))
  val ready = Vec.fill(config.physicalRegs)(Reg(Bool()) init (True))
  speculative(0).init(U(0, config.physicalRegIndexWidth bits))
  architectural(0).init(U(0, config.physicalRegIndexWidth bits))
  ready(0).init(True)
  ready(0) := True

  for (arch <- 0 until config.archRegs) {
    io.architecturalMappings(arch) := architectural(arch)
  }
  io.physicalReady := ready.asBits

  for (lane <- 0 until config.renameWidth) {
    io.renamePsrc1(lane) := speculative(io.renameSource1(lane))
    io.renamePsrc2(lane) := speculative(io.renameSource2(lane))
    io.renameSource1Ready(lane) := ready(io.renamePsrc1(lane))
    io.renameSource2Ready(lane) := ready(io.renamePsrc2(lane))
    io.renameOldPdst(lane) := Mux(
      io.renameDestination(lane) === 0,
      U(0, config.physicalRegIndexWidth bits),
      speculative(io.renameDestination(lane))
    )

    for (older <- 0 until lane) {
      when(
        io.renameValid(older) && io.renameDestination(older) =/= 0 &&
          io.renameDestination(older) === io.renameSource1(lane)
      ) {
        io.renamePsrc1(lane) := io.renamePdst(older)
        io.renameSource1Ready(lane) := False
      }
      when(
        io.renameValid(older) && io.renameDestination(older) =/= 0 &&
          io.renameDestination(older) === io.renameSource2(lane)
      ) {
        io.renamePsrc2(lane) := io.renamePdst(older)
        io.renameSource2Ready(lane) := False
      }
      when(
        io.renameValid(older) && io.renameDestination(older) =/= 0 &&
          io.renameDestination(older) === io.renameDestination(lane)
      ) {
        io.renameOldPdst(lane) := io.renamePdst(older)
      }
    }
  }

  for (lane <- 0 until config.renameWidth) {
    for (write <- 0 until config.writebackWidth) {
      when(io.writebackValid(write) && io.writebackPdst(write) === io.renamePsrc1(lane)) {
        io.renameSource1Ready(lane) := True
      }
      when(io.writebackValid(write) && io.writebackPdst(write) === io.renamePsrc2(lane)) {
        io.renameSource2Ready(lane) := True
      }
    }
  }

  for (lane <- 0 until config.commitWidth) {
    io.commitPreviousPdst(lane) := architectural(io.commitArch(lane))
    for (older <- 0 until lane) {
      when(io.commitValid(older) && io.commitArch(older) === io.commitArch(lane)) {
        io.commitPreviousPdst(lane) := io.commitPdst(older)
      }
    }
  }

  when(io.flush) {
    for (arch <- 1 until config.archRegs) {
      speculative(arch) := architectural(arch)
    }
    for (phys <- 1 until config.physicalRegs) { ready(phys) := True }
  }.otherwise {
    for (lane <- 0 until config.renameWidth) {
      when(io.renameValid(lane) && io.renameDestination(lane) =/= 0) {
        speculative(io.renameDestination(lane)) := io.renamePdst(lane)
      }
    }
    for (phys <- 1 until config.physicalRegs) {
      val allocated = (0 until config.renameWidth)
        .map { lane =>
          io.renameValid(lane) && io.renameDestination(lane) =/= 0 &&
          io.renamePdst(lane) === U(phys, config.physicalRegIndexWidth bits)
        }
        .reduce(_ || _)
      val completed = (0 until config.writebackWidth)
        .map { write =>
          io.writebackValid(write) &&
          io.writebackPdst(write) === U(phys, config.physicalRegIndexWidth bits)
        }
        .reduce(_ || _)
      when(allocated) {
        ready(phys) := False
      }.elsewhen(completed) {
        ready(phys) := True
      }
    }
    for (lane <- 0 until config.commitWidth) {
      when(io.commitValid(lane) && io.commitArch(lane) =/= 0) {
        architectural(io.commitArch(lane)) := io.commitPdst(lane)
      }
    }
  }
}

final class OooFreeList(config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit)
    extends Component {
  private val selectionGroupWidth = 8
  private val selectionGroupCount = config.physicalRegs / selectionGroupWidth
  require(config.physicalRegs % selectionGroupWidth == 0)

  private def selectLowest(mask: Bits): Bits = {
    val groupValid = Bits(selectionGroupCount bits)
    val localFirst = Vec(Bits(selectionGroupWidth bits), selectionGroupCount)
    for (group <- 0 until selectionGroupCount) {
      val high = (group + 1) * selectionGroupWidth - 1
      val low = group * selectionGroupWidth
      val groupMask = mask(high downto low)
      groupValid(group) := groupMask.orR
      localFirst(group) := OHMasking.first(groupMask)
    }
    val selectedGroup = OHMasking.first(groupValid)
    val selected = Bits(config.physicalRegs bits)
    for (group <- 0 until selectionGroupCount) {
      val high = (group + 1) * selectionGroupWidth - 1
      val low = group * selectionGroupWidth
      selected(high downto low) := localFirst(group).andMask(selectedGroup(group))
    }
    selected
  }

  val io = new Bundle {
    val allocateValid = in Bits (config.renameWidth bits)
    val allocatePdst = out Vec (UInt(config.physicalRegIndexWidth bits), config.renameWidth)
    val allocateReady = out Bool ()
    val allocateAccept = in Bool ()
    val commitFreeValid = in Bits (config.commitWidth bits)
    val commitFreePdst = in Vec (UInt(config.physicalRegIndexWidth bits), config.commitWidth)
    val architecturalMappings = in Vec (UInt(config.physicalRegIndexWidth bits), config.archRegs)
    val flush = in Bool ()
    val freeCount = out UInt (log2Up(config.physicalRegs + 1) bits)
  }

  val freeBits = Vec((0 until config.physicalRegs).map { phys =>
    Reg(Bool()) init (if (phys == 0) False else True)
  })

  val remaining = Vec(Bits(config.physicalRegs bits), config.renameWidth + 1)
  remaining(0) := freeBits.asBits
  for (lane <- 0 until config.renameWidth) {
    val selected = selectLowest(remaining(lane))
    io.allocatePdst(lane) := OHToUInt(selected)
    remaining(lane + 1) := remaining(lane) &
      ~Mux(io.allocateValid(lane), selected, B(0, config.physicalRegs bits))
  }

  val freeNow = CountOne(freeBits.asBits)
  val requested = CountOne(io.allocateValid)
  io.allocateReady := !io.flush && freeNow >= requested
  io.freeCount := freeNow

  when(io.flush) {
    for (phys <- 0 until config.physicalRegs) {
      if (phys == 0) {
        freeBits(phys) := False
      } else {
        val architecturallyMapped = io.architecturalMappings
          .map(_ === U(phys, config.physicalRegIndexWidth bits))
          .reduce(_ || _)
        freeBits(phys) := !architecturallyMapped
      }
    }
  }.otherwise {
    for (phys <- 1 until config.physicalRegs) {
      val allocated = (0 until config.renameWidth)
        .map { lane =>
          io.allocateAccept && io.allocateValid(lane) &&
          io.allocatePdst(lane) === U(phys, config.physicalRegIndexWidth bits)
        }
        .reduce(_ || _)
      val released = (0 until config.commitWidth)
        .map { lane =>
          io.commitFreeValid(lane) &&
          io.commitFreePdst(lane) === U(phys, config.physicalRegIndexWidth bits)
        }
        .reduce(_ || _)
      when(allocated) {
        freeBits(phys) := False
      }.elsewhen(released) {
        freeBits(phys) := True
      }
    }
  }
}
