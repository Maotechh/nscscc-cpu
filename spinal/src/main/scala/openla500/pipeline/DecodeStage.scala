package openla500.pipeline

import openla500.config.CoreConfig
import spinal.core._
import spinal.lib._

/** Forwarding metadata consumed by decode. `dependencyNeedsStall` is the locked load/mul/div
  * dependency bit; `valid` is the historical forwarding-enable bit.
  */
final case class DecodeForward() extends Bundle {
  val dependencyNeedsStall = Bool()
  val valid = Bool()
  val destination = UInt(5 bits)
  val data = Bits(32 bits)
}

final case class DecodeFlush() extends Bundle {
  val exception = Bool()
  val ertn = Bool()
  val refetch = Bool()
  val instructionCacheOperation = Bool()
  val idle = Bool()

  def active: Bool = exception || ertn || refetch || instructionCacheOperation || idle
}

final case class DecodeRegisterWrite() extends Bundle {
  val valid = Bool()
  val destination = UInt(5 bits)
  val data = Bits(32 bits)
}

final case class DecodeBtbUpdate() extends Bundle {
  val enable = Bool()
  val popReturnStack = Bool()
  val pushReturnStack = Bool()
  val addEntry = Bool()
  val deleteEntry = Bool()
  val predictionError = Bool()
  val predictionRight = Bool()
  val targetError = Bool()
  val actualTaken = Bool()
  val actualTarget = UInt(32 bits)
  val pc = UInt(32 bits)
  val index = UInt(5 bits)
}

/** Active openLA500 decode stage.
  *
  * Input/output use Stream contracts. The stage owns the decode payload register, GPR storage, and
  * branch-slot cancellation state. Global flush wins over input acceptance; backpressure keeps the
  * registered fetch payload stable. The implementation intentionally preserves the golden MS
  * forwarding quirk: branch comparison uses the register-file value while the outgoing operand uses
  * the forwarded value and decode stalls.
  */
final class DecodeStage(config: CoreConfig = CoreConfig.Locked) extends Component {
  val io = new Bundle {
    val input = slave Stream (FetchPayload())
    val output = master Stream (DecodePayload(config))
    val executeForward = in(DecodeForward())
    val memoryForward = in(DecodeForward())
    val flush = in(DecodeFlush())
    val executeTlbStall = in Bool ()
    val memoryTlbStall = in Bool ()
    val writebackTlbStall = in Bool ()
    val interruptPending = in Bool ()
    val csrReadAddress = out UInt (14 bits)
    val csrReadData = in Bits (32 bits)
    val csrPrivilege = in Bits (2 bits)
    val timer = in Bits (64 bits)
    val timerId = in Bits (32 bits)
    val reservationValid = in Bool ()
    val executeOccupied = in Bool ()
    val memoryOccupied = in Bool ()
    val writebackOccupied = in Bool ()
    val writeBufferEmpty = in Bool ()
    val dataCacheEmpty = in Bool ()
    val registerWrite = in(DecodeRegisterWrite())
    val debugReadSelect = in Bool ()
    val debugReadAddress = in UInt (5 bits)
    val debugLegacyValue = out Bits (32 bits)
    val branchRepair = out(RedirectRequest())
    val btb = out(DecodeBtbUpdate())
    val registers = config.diffTestEnabled generate out(Vec(Bits(32 bits), 32))
  }

  private def any(values: Bool*): Bool = values.reduce(_ || _)
  private def eq(value: UInt, literal: Int): Bool = value === U(literal, value.getWidth bits)

  val occupied = RegInit(False)
  val fetch = Reg(FetchPayload())
  val branchSlotCancel = RegInit(False)

  val registerFile = Vec.fill(32)(Reg(Bits(32 bits)))
  when(io.registerWrite.valid) {
    registerFile(io.registerWrite.destination) := io.registerWrite.data
  }
  private def readRegister(address: UInt): Bits =
    Mux(
      address === 0,
      B(0, 32 bits),
      Mux(
        io.registerWrite.valid && address === io.registerWrite.destination,
        io.registerWrite.data,
        registerFile(address)
      )
    )

  val instruction = fetch.instruction
  val op31To26 = instruction(31 downto 26).asUInt
  val op25To22 = instruction(25 downto 22).asUInt
  val op21To20 = instruction(21 downto 20).asUInt
  val op19To15 = instruction(19 downto 15).asUInt
  val rd = instruction(4 downto 0).asUInt
  val rj = instruction(9 downto 5).asUInt
  val rk = instruction(14 downto 10).asUInt
  val i12 = instruction(21 downto 10)
  val i14 = instruction(23 downto 10)
  val i20 = instruction(24 downto 5)
  val i16 = instruction(25 downto 10)
  val i26 = instruction(9 downto 0) ## instruction(25 downto 10)
  val csrIndex = instruction(23 downto 10).asUInt

  private def full(op21: Int, op19: Int, op25: Int = 0): Bool =
    eq(op31To26, 0) && eq(op25To22, op25) && eq(op21To20, op21) && eq(op19To15, op19)

  val instAddW = full(1, 0x00)
  val instSubW = full(1, 0x02)
  val instSlt = full(1, 0x04)
  val instSltu = full(1, 0x05)
  val instNor = full(1, 0x08)
  val instAnd = full(1, 0x09)
  val instOr = full(1, 0x0a)
  val instXor = full(1, 0x0b)
  val instOrn = full(1, 0x0c)
  val instAndn = full(1, 0x0d)
  val instSllW = full(1, 0x0e)
  val instSrlW = full(1, 0x0f)
  val instSraW = full(1, 0x10)
  val instMulW = full(1, 0x18)
  val instMulhW = full(1, 0x19)
  val instMulhWu = full(1, 0x1a)
  val instDivW = full(2, 0x00)
  val instModW = full(2, 0x01)
  val instDivWu = full(2, 0x02)
  val instModWu = full(2, 0x03)
  val instBreak = full(2, 0x14)
  val instSyscall = full(2, 0x16)
  val instSlliW = full(0, 0x01, 1)
  val instSrliW = full(0, 0x09, 1)
  val instSraiW = full(0, 0x11, 1)
  val instIdle = eq(op31To26, 1) && eq(op25To22, 9) && eq(op21To20, 0) && eq(op19To15, 0x11)
  val instInvTlb = eq(op31To26, 1) && eq(op25To22, 9) && eq(op21To20, 0) && eq(op19To15, 0x13)
  val instDbar = eq(op31To26, 0x0e) && eq(op25To22, 1) && eq(op21To20, 3) && eq(op19To15, 4)
  val instIbar = eq(op31To26, 0x0e) && eq(op25To22, 1) && eq(op21To20, 3) && eq(op19To15, 5)
  val instSlti = eq(op31To26, 0) && eq(op25To22, 8)
  val instSltui = eq(op31To26, 0) && eq(op25To22, 9)
  val instAddiW = eq(op31To26, 0) && eq(op25To22, 0x0a)
  val instAndi = eq(op31To26, 0) && eq(op25To22, 0x0d)
  val instOri = eq(op31To26, 0) && eq(op25To22, 0x0e)
  val instXori = eq(op31To26, 0) && eq(op25To22, 0x0f)
  val instLdB = eq(op31To26, 0x0a) && eq(op25To22, 0)
  val instLdH = eq(op31To26, 0x0a) && eq(op25To22, 1)
  val instLdW = eq(op31To26, 0x0a) && eq(op25To22, 2)
  val instStB = eq(op31To26, 0x0a) && eq(op25To22, 4)
  val instStH = eq(op31To26, 0x0a) && eq(op25To22, 5)
  val instStW = eq(op31To26, 0x0a) && eq(op25To22, 6)
  val instLdBu = eq(op31To26, 0x0a) && eq(op25To22, 8)
  val instLdHu = eq(op31To26, 0x0a) && eq(op25To22, 9)
  val instCacop = eq(op31To26, 1) && eq(op25To22, 8)
  val instPreload = eq(op31To26, 0x0a) && eq(op25To22, 0x0b)
  val instJirl = eq(op31To26, 0x13)
  val instB = eq(op31To26, 0x14)
  val instBl = eq(op31To26, 0x15)
  val instBeq = eq(op31To26, 0x16)
  val instBne = eq(op31To26, 0x17)
  val instBlt = eq(op31To26, 0x18)
  val instBge = eq(op31To26, 0x19)
  val instBltu = eq(op31To26, 0x1a)
  val instBgeu = eq(op31To26, 0x1b)
  val instLu12iW = eq(op31To26, 5) && !instruction(25)
  val instPcaddi = eq(op31To26, 6) && !instruction(25)
  val instPcaddu12i = eq(op31To26, 7) && !instruction(25)
  val baseCsr = eq(op31To26, 1) && !instruction(25) && !instruction(24)
  val instCsrXchg = baseCsr && rj =/= 0 && rj =/= 1
  val instLlW = eq(op31To26, 8) && !instruction(25) && !instruction(24)
  val instScW = eq(op31To26, 8) && !instruction(25) && instruction(24)
  val instCsrRead = baseCsr && rj === 0
  val instCsrWrite = baseCsr && rj === 1
  val counterBase = full(0, 0x00)
  val instRdCntIdW = counterBase && rk === 0x18 && rd === 0
  val instRdCntVlW = counterBase && rk === 0x18 && rj === 0 && rd =/= 0
  val instRdCntVhW = counterBase && rk === 0x19 && rj === 0
  val privilegedBase = eq(op31To26, 1) && eq(op25To22, 9) && eq(op21To20, 0) && eq(
    op19To15,
    0x10
  ) && rj === 0 && rd === 0
  val instErtn = privilegedBase && rk === 0x0e
  val instTlbSearch = privilegedBase && rk === 0x0a
  val instTlbRead = privilegedBase && rk === 0x0b
  val instTlbWrite = privilegedBase && rk === 0x0c
  val instTlbFill = privilegedBase && rk === 0x0d
  val instCpuCfg = counterBase && rk === 0x1b

  val destination = Mux(instBl, U(1, 5 bits), Mux(instRdCntIdW, rj, rd))
  val validCacop =
    instCacop && (destination(2 downto 0) === 0 || destination(2 downto 0) === 1) && destination(
      4 downto 3
    ) =/= 3
  val cacopNop =
    instCacop && ((destination(2 downto 0) =/= 0 && destination(2 downto 0) =/= 1) || destination(
      4 downto 3
    ) === 3)
  val laccRequest = if (config.laccEnabled) instruction(31 downto 28) === B"1100" else False
  val laccValid = if (config.laccEnabled) instruction(23 downto 22).asUInt < 3 else False

  val aluOperation = Bits(14 bits)
  aluOperation := 0
  aluOperation(0) := any(
    instAddW,
    instAddiW,
    instLdB,
    instLdH,
    instLdW,
    instStB,
    instStH,
    instStW,
    instLdBu,
    instLdHu,
    instLlW,
    instScW,
    instJirl,
    instBl,
    instPcaddi,
    instPcaddu12i,
    validCacop,
    instPreload
  )
  aluOperation(1) := instSubW
  aluOperation(2) := instSlt || instSlti
  aluOperation(3) := instSltu || instSltui
  aluOperation(4) := instAnd || instAndi
  aluOperation(5) := instNor
  aluOperation(6) := instOr || instOri
  aluOperation(7) := instXor || instXori
  aluOperation(8) := instSllW || instSlliW
  aluOperation(9) := instSrlW || instSrliW
  aluOperation(10) := instSraW || instSraiW
  aluOperation(11) := instLu12iW
  aluOperation(12) := instAndn
  aluOperation(13) := instOrn

  val mulDivOperation =
    instModW.asBits ## (instDivW || instDivWu).asBits ## (instMulhW || instMulhWu).asBits ## instMulW.asBits
  // The concatenation above must retain golden bit order [mod,div,mulh,mul].
  mulDivOperation(3) := instModW || instModWu
  val mulDivSigned = any(instMulW, instMulhW, instDivW, instModW)

  val needUi5 = any(instSlliW, instSrliW, instSraiW)
  val needSi12 = any(
    instAddiW,
    instLdB,
    instLdH,
    instLdW,
    instStB,
    instStH,
    instStW,
    instLdBu,
    instLdHu,
    instSlti,
    instSltui,
    validCacop,
    instPreload
  )
  val needUi12 = any(instAndi, instOri, instXori, laccRequest)
  val needSi14Pc = instLlW || instScW
  val needSi16Pc = any(instJirl, instBeq, instBne, instBlt, instBge, instBltu, instBgeu)
  val needSi20 = instLu12iW || instPcaddu12i
  val needSi20Pc = instPcaddi
  val needSi26Pc = instB || instBl
  val immediate = Bits(32 bits)
  immediate := 0
  when(needUi5) { immediate := rk.asBits.resize(32) }
  when(needSi12) { immediate := i12.asSInt.resize(32).asBits }
  when(needUi12) { immediate := i12.resize(32) }
  when(needSi14Pc) { immediate := (i14 ## B(0, 2 bits)).asSInt.resize(32).asBits }
  when(needSi16Pc) { immediate := (i16 ## B(0, 2 bits)).asSInt.resize(32).asBits }
  when(needSi20) { immediate := i20 ## B(0, 12 bits) }
  when(needSi20Pc) { immediate := (i20 ## B(0, 2 bits)).asSInt.resize(32).asBits }
  when(needSi26Pc) { immediate := (i26 ## B(0, 2 bits)).asSInt.resize(32).asBits }

  val sourceRegisterIsRd = any(
    instBeq,
    instBne,
    instBlt,
    instBltu,
    instBge,
    instBgeu,
    instStB,
    instStH,
    instStW,
    instScW,
    instCsrWrite,
    instCsrXchg
  )
  val source1IsPc = any(instJirl, instBl, instPcaddi, instPcaddu12i)
  val source2IsImmediate = any(
    instSlliW,
    instSrliW,
    instSraiW,
    instAddiW,
    instSlti,
    instSltui,
    instAndi,
    instOri,
    instXori,
    instPcaddi,
    instPcaddu12i,
    instLdB,
    instLdH,
    instLdW,
    instLdBu,
    instLdHu,
    instStB,
    instStH,
    instStW,
    instLlW,
    instScW,
    instLu12iW,
    validCacop,
    instPreload
  )
  val source2IsFour = instJirl || instBl
  val loadOperation = any(instLdB, instLdH, instLdW, instLdBu, instLdHu, instLlW)
  val byteMemory = any(instLdB, instLdBu, instStB)
  val halfMemory = any(instLdH, instLdHu, instStH)
  val memorySignExtend = instLdB || instLdH
  val gprWrite = !any(
    instStB,
    instStH,
    instStW,
    instBeq,
    instBne,
    instBlt,
    instBge,
    instBltu,
    instBgeu,
    instB,
    instSyscall,
    instTlbSearch,
    instTlbRead,
    instTlbWrite,
    instTlbFill,
    instInvTlb,
    validCacop,
    instPreload,
    instDbar,
    instIbar,
    cacopNop
  )
  val storeOperation = any(instStB, instStH, instStW, instScW && io.reservationValid)

  val needRj = any(
    instAddW,
    instSubW,
    instAddiW,
    instSlt,
    instSltu,
    instSlti,
    instSltui,
    instAnd,
    instOr,
    instNor,
    instXor,
    instAndi,
    instOri,
    instXori,
    instMulW,
    instMulhW,
    instMulhWu,
    instDivW,
    instDivWu,
    instModW,
    instModWu,
    instSllW,
    instSrlW,
    instSraW,
    instSlliW,
    instSrliW,
    instSraiW,
    instBeq,
    instBne,
    instBlt,
    instBltu,
    instBge,
    instBgeu,
    instJirl,
    instLdB,
    instLdBu,
    instLdH,
    instLdHu,
    instLdW,
    instStB,
    instStH,
    instStW,
    instPreload,
    instLlW,
    instScW,
    instCsrXchg,
    validCacop,
    laccRequest,
    instInvTlb
  )
  val needRkd = any(
    instAddW,
    instSubW,
    instSlt,
    instSltu,
    instAnd,
    instOr,
    instNor,
    instXor,
    instMulW,
    instMulhW,
    instMulhWu,
    instDivW,
    instDivWu,
    instModW,
    instModWu,
    instSllW,
    instSrlW,
    instSraW,
    instBeq,
    instBne,
    instBlt,
    instBltu,
    instBge,
    instBgeu,
    instStB,
    instStH,
    instStW,
    instScW,
    instCsrWrite,
    instCsrXchg,
    laccRequest,
    instInvTlb
  )

  val readAddressJ = Mux(io.debugReadSelect, io.debugReadAddress, rj)
  val readAddressKOrD = Mux(sourceRegisterIsRd, rd, rk)
  val registerDataJ = readRegister(readAddressJ)
  val registerDataKOrD = readRegister(readAddressKOrD)
  val branchNeedsRegisterData =
    any(instBeq, instBne, instBlt, instBge, instBltu, instBgeu, instJirl)

  val executeJHit =
    readAddressJ === io.executeForward.destination && io.executeForward.valid && needRj
  val memoryJHit = readAddressJ === io.memoryForward.destination && io.memoryForward.valid && needRj
  val executeKHit =
    readAddressKOrD === io.executeForward.destination && io.executeForward.valid && needRkd
  val memoryKHit =
    readAddressKOrD === io.memoryForward.destination && io.memoryForward.valid && needRkd
  val valueJ =
    Mux(executeJHit, io.executeForward.data, Mux(memoryJHit, io.memoryForward.data, registerDataJ))
  val valueKOrD = Mux(
    executeKHit,
    io.executeForward.data,
    Mux(memoryKHit, io.memoryForward.data, registerDataKOrD)
  )
  val branchValueJ = Mux(executeJHit, io.executeForward.data, registerDataJ)
  val branchValueKOrD = Mux(executeKHit, io.executeForward.data, registerDataKOrD)
  val stallJ = Mux(
    executeJHit,
    io.executeForward.dependencyNeedsStall,
    Mux(memoryJHit, io.memoryForward.dependencyNeedsStall || branchNeedsRegisterData, False)
  )
  val stallK = Mux(
    executeKHit,
    io.executeForward.dependencyNeedsStall,
    Mux(memoryKHit, io.memoryForward.dependencyNeedsStall || branchNeedsRegisterData, False)
  )

  val equalOperands = branchValueJ === branchValueKOrD
  val lessUnsigned = branchValueJ.asUInt < branchValueKOrD.asUInt
  val lessSigned = branchValueJ.asSInt < branchValueKOrD.asSInt
  val branchTakenRaw = any(
    instBeq && equalOperands,
    instBne && !equalOperands,
    instBlt && lessSigned,
    instBge && !lessSigned,
    instBltu && lessUnsigned,
    instBgeu && !lessUnsigned,
    instJirl,
    instBl,
    instB
  )
  val branchTaken = branchTakenRaw && occupied && !fetch.hasException
  val branchInstruction = branchNeedsRegisterData || instBl || instB
  val predictableBranch =
    any(instBeq, instBne, instBlt, instBge, instBltu, instBgeu, instBl, instB, instJirl)
  val pcRelativeBranch = any(instBeq, instBne, instBl, instB, instBlt, instBge, instBltu, instBgeu)
  val branchTarget = Mux(
    instJirl,
    branchValueJ.asUInt + immediate.asUInt,
    Mux(pcRelativeBranch, fetch.pc + immediate.asUInt, U(0, 32 bits))
  )

  val instructionValid = any(
    instAddW,
    instSubW,
    instSlt,
    instSltu,
    instNor,
    instAnd,
    instOr,
    instXor,
    instSllW,
    instSrlW,
    instSraW,
    instMulW,
    instMulhW,
    instMulhWu,
    instDivW,
    instModW,
    instDivWu,
    instModWu,
    instBreak,
    instSyscall,
    instSlliW,
    instSrliW,
    instSraiW,
    instIdle,
    instSlti,
    instSltui,
    instAddiW,
    instAndi,
    instOri,
    instXori,
    instLdB,
    instLdH,
    instLdW,
    instStB,
    instStH,
    instStW,
    instLdBu,
    instLdHu,
    instLlW,
    instScW,
    instJirl,
    instB,
    instBl,
    instBeq,
    instBne,
    instBlt,
    instBge,
    instBltu,
    instBgeu,
    instLu12iW,
    instPcaddu12i,
    instCsrRead,
    instCsrWrite,
    instCsrXchg,
    instRdCntIdW,
    instRdCntVhW,
    instRdCntVlW,
    instErtn,
    validCacop,
    instPreload,
    instDbar,
    instIbar,
    instTlbSearch,
    instTlbRead,
    instTlbWrite,
    instTlbFill,
    cacopNop,
    instCpuCfg,
    laccRequest && laccValid,
    instInvTlb && rd <= 6
  )
  val illegalInstruction = !instructionValid
  val kernelInstruction = any(
    instCsrRead,
    instCsrWrite,
    instCsrXchg,
    validCacop && destination(4 downto 3) =/= 2,
    instTlbSearch,
    instTlbRead,
    instTlbWrite,
    instTlbFill,
    instInvTlb,
    instErtn,
    instIdle
  )
  val privilegeException = kernelInstruction && io.csrPrivilege === B"11"
  val hasException = any(
    privilegeException,
    instSyscall,
    instBreak,
    fetch.hasException,
    illegalInstruction,
    io.interruptPending
  )
  val exceptionCode =
    privilegeException.asBits ## illegalInstruction.asBits ## instBreak.asBits ## instSyscall.asBits ## fetch.exceptionCode ## io.interruptPending.asBits

  val refetch = any(instTlbWrite, instTlbFill, instTlbRead, instInvTlb, instIbar) && occupied
  val pipelineNotEmpty = any(
    io.executeOccupied,
    io.memoryOccupied,
    io.writebackOccupied,
    !io.writeBufferEmpty,
    !io.dataCacheEmpty
  )
  val barrierStall = (instDbar || instIbar) && pipelineNotEmpty
  val tlbStall = any(io.executeTlbStall, io.memoryTlbStall, io.writebackTlbStall)
  val readyGo = !(stallJ || stallK || tlbStall || barrierStall) || hasException

  val btbAddEntry = predictableBranch && !fetch.btbEnabled && branchTaken
  val btbDeleteEntry = !predictableBranch && fetch.btbEnabled
  val btbPredictionError = predictableBranch && fetch.btbEnabled && (fetch.btbTaken ^ branchTaken)
  val btbTargetError =
    predictableBranch && fetch.btbEnabled && fetch.btbTaken && branchTaken && fetch.btbTarget =/= branchTarget
  val btbRepair = any(
    btbAddEntry,
    btbDeleteEntry,
    btbPredictionError,
    btbTargetError
  ) && occupied && readyGo && !fetch.hasException
  val btbRepairTarget = Mux(branchTaken, branchTarget, fetch.pc + 4)

  io.input.ready := !occupied || (readyGo && io.output.ready)
  io.output.valid := occupied && readyGo
  when(io.flush.active) {
    occupied := False
  } elsewhen (io.input.ready) {
    when((btbRepair && io.output.ready) || branchSlotCancel) {
      occupied := False
    } otherwise {
      occupied := io.input.valid
    }
  }
  when(io.input.valid && io.input.ready) {
    fetch := io.input.payload
  }

  when(io.flush.active) {
    branchSlotCancel := False
  } elsewhen (btbRepair && io.output.ready && !io.input.valid) {
    branchSlotCancel := True
  } elsewhen (branchSlotCancel && io.input.valid) {
    branchSlotCancel := False
  }

  val counterEnabled = any(instRdCntVlW, instRdCntVhW, instRdCntIdW)
  val counterResult =
    Mux(instRdCntVlW, io.timer(31 downto 0), Mux(instRdCntVhW, io.timer(63 downto 32), io.timerId))
  val csrData = Mux(
    counterEnabled,
    counterResult,
    Mux(instScW, B(0, 31 bits) ## io.reservationValid.asBits, io.csrReadData)
  )

  io.output.payload.pc := fetch.pc
  io.output.payload.registerDataKOrD := valueKOrD
  io.output.payload.registerDataJ := valueJ
  io.output.payload.immediate := immediate
  io.output.payload.destination := destination
  io.output.payload.isStore := storeOperation
  io.output.payload.gprWrite := gprWrite
  io.output.payload.source2IsFour := source2IsFour
  io.output.payload.source2IsImmediate := source2IsImmediate
  io.output.payload.source1IsPc := source1IsPc
  io.output.payload.isLoad := loadOperation
  io.output.payload.aluOperation := aluOperation
  io.output.payload.mulDivSigned := mulDivSigned
  io.output.payload.mulDivOperation := mulDivOperation
  io.output.payload.memorySize := halfMemory.asBits ## byteMemory.asBits
  io.output.payload.hasException := hasException
  io.output.payload.isErtn := instErtn
  io.output.payload.csrReadData := csrData
  io.output.payload.resultFromCsr := any(
    instCsrRead,
    instCsrWrite,
    instCsrXchg,
    instRdCntIdW,
    instRdCntVhW,
    instRdCntVlW,
    instScW,
    instCpuCfg
  )
  io.output.payload.csrAddress := csrIndex
  io.output.payload.csrWrite := instCsrWrite || instCsrXchg
  io.output.payload.csrMask := instCsrXchg
  io.output.payload.exceptionCode := exceptionCode
  io.output.payload.isLl := instLlW
  io.output.payload.isSc := instScW
  io.output.payload.tlbSearch := instTlbSearch
  io.output.payload.tlbWrite := instTlbWrite
  io.output.payload.tlbFill := instTlbFill
  io.output.payload.refetch := refetch
  io.output.payload.tlbRead := instTlbRead
  io.output.payload.invalidateTlb := instInvTlb
  io.output.payload.memorySignExtend := memorySignExtend
  io.output.payload.cacheOperation := validCacop
  io.output.payload.preload := instPreload
  io.output.payload.isBranch := branchInstruction
  io.output.payload.instructionCacheMiss := fetch.instructionCacheMiss
  io.output.payload.isPredictableBranch := predictableBranch
  io.output.payload.predictionError := btbRepair
  io.output.payload.idle := instIdle
  io.output.payload.instruction := instruction
  io.output.payload.timer := io.timer
  io.output.payload.isCounterInstruction := counterEnabled
  io.output.payload.loadEvent := B(
    0,
    2 bits
  ) ## instLlW.asBits ## instLdW.asBits ## instLdHu.asBits ## instLdH.asBits ## instLdBu.asBits ## instLdB.asBits
  io.output.payload.storeEvent := B(
    0,
    4 bits
  ) ## (io.reservationValid && instScW).asBits ## instStW.asBits ## instStH.asBits ## instStB.asBits
  io.output.payload.csrRstatEvent := any(instCsrRead, instCsrWrite, instCsrXchg) && csrIndex === 5
  if (config.laccEnabled) {
    io.output.payload.laccRequest := laccRequest
    io.output.payload.laccCommand := instruction(23 downto 22)
  }

  io.csrReadAddress := Mux(instCpuCfg, valueJ(13 downto 0).asUInt + U(0x00b0, 14 bits), csrIndex)
  io.debugLegacyValue := readAddressJ.asBits.resize(32)
  io.branchRepair.active := btbRepair
  io.branchRepair.target := btbRepairTarget
  io.btb.enable := occupied && readyGo && io.output.ready && !fetch.hasException
  io.btb.popReturnStack := instJirl
  io.btb.pushReturnStack := instBl
  io.btb.addEntry := btbAddEntry
  io.btb.deleteEntry := btbDeleteEntry
  io.btb.predictionError := btbPredictionError
  io.btb.predictionRight := predictableBranch && fetch.btbEnabled && !(fetch.btbTaken ^ branchTaken)
  io.btb.targetError := btbTargetError
  io.btb.actualTaken := branchTaken
  io.btb.actualTarget := branchTarget
  io.btb.pc := fetch.pc
  io.btb.index := fetch.btbIndex

  if (config.diffTestEnabled) {
    for (index <- 0 until 32) io.registers(index) := registerFile(index)
  }
}
