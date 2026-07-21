package openla500.observe

import spinal.core._
import spinal.lib._

/** Only the fields consumed by the shared exception/ERTN observation port. */
private final case class CommitControlObservation() extends Bundle {
  val pc = UInt(32 bits)
  val instruction = Bits(32 bits)
  val ertn = Bool()
  val exceptionValid = Bool()
  val exceptionCode = UInt(6 bits)
}

/** Typed boundary from the architectural commit/state contracts to chiplab's DPI modules.
  *
  * Up to three ordered commits are sampled for one cycle before they reach the DPI wrappers.
  * Architectural state remains live: at the following edge the official DPI modules must observe
  * all GPR/CSR updates made by that group, matching the golden nonblocking-assignment schedule. The
  * wrapper only references simulator-provided Difftest modules when `DIFFTEST_EN` is defined, so
  * normal synthesis never retains unresolved DPI blackboxes.
  */
final class ChiplabDiffTestAdapter extends Component {
  private val commitWidth = CommitGroup.Width

  val io = new Bundle {
    val clock = in Bool ()
    val commit = slave(Flow(CommitGroup(commitWidth)))
    val archState = in(ArchState())
  }

  private val ordered = new OrderedCommitGroup(commitWidth, reportViolation = false)
  ordered.io.input := io.commit

  val registeredValid = RegNext(ordered.io.output.valid) init (False)
  val registeredCommit = Reg(CommitGroup(commitWidth))
  registeredCommit := ordered.io.output.payload

  val rawRetired = Bits(commitWidth bits)
  for (lane <- 0 until commitWidth) {
    rawRetired(lane) := ordered.io.output.valid && ordered.io.output.payload.valid(lane) &&
      ordered.io.output.payload.events(lane).retired
  }
  val cycleCount = Reg(UInt(64 bits)) init (0)
  val instructionCount = Reg(UInt(64 bits)) init (0)
  cycleCount := cycleCount + 1
  instructionCount := instructionCount + CountOne(rawRetired).resize(64)

  private def zeroExtend32(value: Bits): Bits = B(0, 32 bits) ## value

  private val wrapper = new ChiplabDiffTestBlackBox(commitWidth)
  wrapper.io.clock := io.clock

  val controlValid = Bits(commitWidth bits)
  for (lane <- 0 until commitWidth) {
    val event = registeredCommit.events(lane)
    val laneValid = registeredValid && registeredCommit.valid(lane)
    val commitLow = lane * CommitGroup.EventWidth
    val commitHigh = commitLow + CommitGroup.EventWidth - 1
    val value32Low = lane * 32
    val value32High = value32Low + 31
    val value64Low = lane * 64
    val value64High = value64Low + 63
    val value8Low = lane * 8
    val value8High = value8Low + 7
    val value5Low = lane * 5
    val value5High = value5Low + 4

    wrapper.io.commitContract(commitHigh downto commitLow) := event.asBits
    wrapper.io.instrValid(lane) := laneValid && event.retired
    wrapper.io.pc(value64High downto value64Low) := zeroExtend32(event.pc.asBits)
    wrapper.io.instruction(value32High downto value32Low) := event.instruction
    wrapper.io.isTlbFill(lane) := laneValid && event.tlbFill.valid
    wrapper.io.tlbFillIndex(value5High downto value5Low) := event.tlbFill.index.asBits
    wrapper.io.isCounterInstruction(lane) := event.isCounterInstruction
    wrapper.io.timer(value64High downto value64Low) := event.timer.asBits
    wrapper.io.gprWriteValid(lane) := laneValid && event.gprWrite.valid
    wrapper.io.gprWriteIndex(value8High downto value8Low) :=
      B(0, 3 bits) ## event.gprWrite.index.asBits
    wrapper.io.gprWriteData(value64High downto value64Low) := zeroExtend32(event.gprWrite.data)
    wrapper.io.csrRstat(lane) := event.csrRstat
    wrapper.io.csrReadData(value32High downto value32Low) := event.csrReadData

    wrapper.io.storeValid(value8High downto value8Low) :=
      Mux(laneValid, event.store.instructionMask, B(0, 8 bits))
    wrapper.io.storePhysicalAddress(value64High downto value64Low) :=
      zeroExtend32(event.store.pAddr.asBits)
    wrapper.io.storeVirtualAddress(value64High downto value64Low) :=
      zeroExtend32(event.store.vAddr.asBits)
    wrapper.io.storeData(value64High downto value64Low) := zeroExtend32(event.store.data)
    wrapper.io.loadValid(value8High downto value8Low) :=
      Mux(laneValid, event.load.instructionMask, B(0, 8 bits))
    wrapper.io.loadPhysicalAddress(value64High downto value64Low) :=
      zeroExtend32(event.load.pAddr.asBits)
    wrapper.io.loadVirtualAddress(value64High downto value64Low) :=
      zeroExtend32(event.load.vAddr.asBits)

    controlValid(lane) := laneValid && (event.exception.valid || event.ertn)
  }

  private val selectedControl = CommitControlObservation()
  selectedControl.pc := registeredCommit.events(0).pc
  selectedControl.instruction := registeredCommit.events(0).instruction
  selectedControl.ertn := registeredCommit.events(0).ertn
  selectedControl.exceptionValid := registeredCommit.events(0).exception.valid
  selectedControl.exceptionCode := registeredCommit.events(0).exception.ecode
  var olderControlSelected: Bool = False
  for (lane <- 0 until commitWidth) {
    when(controlValid(lane) && !olderControlSelected) {
      selectedControl.pc := registeredCommit.events(lane).pc
      selectedControl.instruction := registeredCommit.events(lane).instruction
      selectedControl.ertn := registeredCommit.events(lane).ertn
      selectedControl.exceptionValid := registeredCommit.events(lane).exception.valid
      selectedControl.exceptionCode := registeredCommit.events(lane).exception.ecode
    }
    olderControlSelected = olderControlSelected || controlValid(lane)
  }

  wrapper.io.exceptionValid := controlValid.orR && selectedControl.exceptionValid
  wrapper.io.ertn := controlValid.orR && selectedControl.ertn
  wrapper.io.interruptNumber := B(0, 21 bits) ## io.archState.estat(12 downto 2)
  wrapper.io.exceptionCause := B(0, 26 bits) ## selectedControl.exceptionCode.asBits
  wrapper.io.exceptionPc := zeroExtend32(selectedControl.pc.asBits)
  wrapper.io.exceptionInstruction := selectedControl.instruction

  wrapper.io.trapValid := False
  wrapper.io.trapCode := io.archState.gpr(10)(2 downto 0)
  wrapper.io.trapPc := zeroExtend32(registeredCommit.events(0).pc.asBits)
  wrapper.io.cycleCount := cycleCount.asBits
  wrapper.io.instructionCount := instructionCount.asBits

  private val csrWords = Seq(
    io.archState.crmd,
    io.archState.prmd,
    io.archState.euen,
    io.archState.ecfg,
    io.archState.estat,
    io.archState.era,
    io.archState.badv,
    io.archState.eentry,
    io.archState.tlbidx,
    io.archState.tlbehi,
    io.archState.tlbelo0,
    io.archState.tlbelo1,
    io.archState.asid,
    io.archState.pgdl,
    io.archState.pgdh,
    io.archState.save0,
    io.archState.save1,
    io.archState.save2,
    io.archState.save3,
    io.archState.tid,
    io.archState.tcfg,
    io.archState.tval,
    io.archState.ticlr,
    io.archState.llbctl,
    io.archState.tlbrentry,
    io.archState.dmw0,
    io.archState.dmw1
  )
  wrapper.io.csrState := csrWords.map(zeroExtend32).reverse.reduce(_ ## _)

  private val gprWords = io.archState.gpr.map(zeroExtend32)
  wrapper.io.gprState := gprWords.reverse.reduce(_ ## _)
}

/** Conditional Verilog shell around chiplab's simulator-owned Difftest modules. */
private final class ChiplabDiffTestBlackBox(commitWidth: Int) extends BlackBox {
  require(commitWidth >= 1, "Difftest requires at least one commit lane")

  setDefinitionName("ChiplabDiffTestBlackBox")

  val io = new Bundle {
    val clock = in Bool ()
    val commitContract = in Bits (commitWidth * CommitGroup.EventWidth bits)
    val instrValid = in Bits (commitWidth bits)
    val pc = in Bits (commitWidth * 64 bits)
    val instruction = in Bits (commitWidth * 32 bits)
    val isTlbFill = in Bits (commitWidth bits)
    val tlbFillIndex = in Bits (commitWidth * 5 bits)
    val isCounterInstruction = in Bits (commitWidth bits)
    val timer = in Bits (commitWidth * 64 bits)
    val gprWriteValid = in Bits (commitWidth bits)
    val gprWriteIndex = in Bits (commitWidth * 8 bits)
    val gprWriteData = in Bits (commitWidth * 64 bits)
    val csrRstat = in Bits (commitWidth bits)
    val csrReadData = in Bits (commitWidth * 32 bits)

    val exceptionValid = in Bool ()
    val ertn = in Bool ()
    val interruptNumber = in Bits (32 bits)
    val exceptionCause = in Bits (32 bits)
    val exceptionPc = in Bits (64 bits)
    val exceptionInstruction = in Bits (32 bits)

    val trapValid = in Bool ()
    val trapCode = in Bits (3 bits)
    val trapPc = in Bits (64 bits)
    val cycleCount = in Bits (64 bits)
    val instructionCount = in Bits (64 bits)

    val storeValid = in Bits (commitWidth * 8 bits)
    val storePhysicalAddress = in Bits (commitWidth * 64 bits)
    val storeVirtualAddress = in Bits (commitWidth * 64 bits)
    val storeData = in Bits (commitWidth * 64 bits)
    val loadValid = in Bits (commitWidth * 8 bits)
    val loadPhysicalAddress = in Bits (commitWidth * 64 bits)
    val loadVirtualAddress = in Bits (commitWidth * 64 bits)

    val csrState = in Bits (27 * 64 bits)
    val gprState = in Bits (32 * 64 bits)
  }
  noIoPrefix()

  private val csrNames = Seq(
    "crmd",
    "prmd",
    "euen",
    "ecfg",
    "estat",
    "era",
    "badv",
    "eentry",
    "tlbidx",
    "tlbehi",
    "tlbelo0",
    "tlbelo1",
    "asid",
    "pgdl",
    "pgdh",
    "save0",
    "save1",
    "save2",
    "save3",
    "tid",
    "tcfg",
    "tval",
    "ticlr",
    "llbctl",
    "tlbrentry",
    "dmw0",
    "dmw1"
  )
  private val csrConnections = csrNames.zipWithIndex
    .map { case (name, index) =>
      val high = index * 64 + 63
      val low = index * 64
      val source =
        if (name == "euen") s"64'b0 & csrState[$high:$low]"
        else s"csrState[$high:$low]"
      s"    .$name($source)"
    }
    .mkString(",\n")
  private val gprConnections = (0 until 32)
    .map { index =>
      val source =
        if (index == 0) "64'b0 & gprState[63:0]"
        else s"gprState[${index * 64 + 63}:${index * 64}]"
      s"    .gpr_$index($source)"
    }
    .mkString(",\n")

  private def laneSlice(lane: Int, width: Int): String =
    s"[${lane * width + width - 1}:${lane * width}]"

  private val laneModules = (0 until commitWidth)
    .map { lane =>
      val commit = laneSlice(lane, CommitGroup.EventWidth)
      val value5 = laneSlice(lane, 5)
      val value8 = laneSlice(lane, 8)
      val value32 = laneSlice(lane, 32)
      val value64 = laneSlice(lane, 64)
      s"""  DifftestInstrCommit u_difftest_instr_commit_$lane (
    .clock(clock), .coreid(8'b0), .index(8'd$lane), .valid(instrValid[$lane]),
    .pc(pc$value64), .instr(instruction$value32),
    .skip(1'b0 & ^commitContract$commit), .is_TLBFILL(isTlbFill[$lane]),
    .TLBFILL_index(tlbFillIndex$value5), .is_CNTinst(isCounterInstruction[$lane]),
    .timer_64_value(timer$value64), .wen(gprWriteValid[$lane]),
    .wdest(gprWriteIndex$value8), .wdata(gprWriteData$value64),
    .csr_rstat(csrRstat[$lane]), .csr_data(csrReadData$value32)
  );

  DifftestStoreEvent u_difftest_store_$lane (
    .clock(clock), .coreid(8'b0), .index(8'd$lane), .valid(storeValid$value8),
    .storePAddr(storePhysicalAddress$value64), .storeVAddr(storeVirtualAddress$value64),
    .storeData(storeData$value64)
  );

  DifftestLoadEvent u_difftest_load_$lane (
    .clock(clock), .coreid(8'b0), .index(8'd$lane), .valid(loadValid$value8),
    .paddr(loadPhysicalAddress$value64), .vaddr(loadVirtualAddress$value64)
  );"""
    }
    .mkString("\n\n")

  setInlineVerilog(s"""
`ifndef DIFFTEST_EN
/* verilator lint_off UNUSEDSIGNAL */
`endif
module ChiplabDiffTestBlackBox (
    input  wire                                    clock,
    input  wire [${commitWidth * CommitGroup.EventWidth - 1}:0] commitContract,
    input  wire [${commitWidth - 1}:0]              instrValid,
    input  wire [${commitWidth * 64 - 1}:0]         pc,
    input  wire [${commitWidth * 32 - 1}:0]         instruction,
    input  wire [${commitWidth - 1}:0]              isTlbFill,
    input  wire [${commitWidth * 5 - 1}:0]          tlbFillIndex,
    input  wire [${commitWidth - 1}:0]              isCounterInstruction,
    input  wire [${commitWidth * 64 - 1}:0]         timer,
    input  wire [${commitWidth - 1}:0]              gprWriteValid,
    input  wire [${commitWidth * 8 - 1}:0]          gprWriteIndex,
    input  wire [${commitWidth * 64 - 1}:0]         gprWriteData,
    input  wire [${commitWidth - 1}:0]              csrRstat,
    input  wire [${commitWidth * 32 - 1}:0]         csrReadData,
    input  wire          exceptionValid,
    input  wire          ertn,
    input  wire [31:0]   interruptNumber,
    input  wire [31:0]   exceptionCause,
    input  wire [63:0]   exceptionPc,
    input  wire [31:0]   exceptionInstruction,
    input  wire          trapValid,
    input  wire [2:0]    trapCode,
    input  wire [63:0]   trapPc,
    input  wire [63:0]   cycleCount,
    input  wire [63:0]   instructionCount,
    input  wire [${commitWidth * 8 - 1}:0]          storeValid,
    input  wire [${commitWidth * 64 - 1}:0]         storePhysicalAddress,
    input  wire [${commitWidth * 64 - 1}:0]         storeVirtualAddress,
    input  wire [${commitWidth * 64 - 1}:0]         storeData,
    input  wire [${commitWidth * 8 - 1}:0]          loadValid,
    input  wire [${commitWidth * 64 - 1}:0]         loadPhysicalAddress,
    input  wire [${commitWidth * 64 - 1}:0]         loadVirtualAddress,
    input  wire [1727:0] csrState,
    input  wire [2047:0] gprState
);
`ifdef DIFFTEST_EN
$laneModules

  DifftestExcpEvent u_difftest_exception (
    .clock(clock), .coreid(8'b0), .excp_valid(exceptionValid), .eret(ertn),
    .intrNo(interruptNumber), .cause(exceptionCause), .exceptionPC(exceptionPc),
    .exceptionInst(exceptionInstruction)
  );

  DifftestTrapEvent u_difftest_trap (
    .clock(clock), .coreid(8'b0), .valid(trapValid), .code(trapCode), .pc(trapPc),
    .cycleCnt(cycleCount), .instrCnt(instructionCount)
  );

  DifftestCSRRegState u_difftest_csr_state (
    .clock(clock), .coreid(8'b0),
$csrConnections
  );

  DifftestGRegState u_difftest_gpr_state (
    .clock(clock), .coreid(8'b0),
$gprConnections
  );
`endif
endmodule
`ifndef DIFFTEST_EN
/* verilator lint_on UNUSEDSIGNAL */
`endif""")
}
