package openla500.pipeline

import java.nio.file.{Files, Path, Paths}
import openla500.config.CoreConfig
import spinal.core._

/** Exact locked `wb_stage` port adapter around the typed WritebackStage. */
final class LegacyWritebackStage(config: CoreConfig = CoreConfig.Locked) extends Component {
  setDefinitionName("wb_stage")

  val io = new Bundle {
    val clk = in Bool ()
    val reset = in Bool ()
    val ws_allowin = out Bool ()
    val ms_to_ws_valid = in Bool ()
    val ms_to_ws_bus = in Bits (MemoryPayload.LegacyWidth bits)
    val ws_to_rf_bus = out Bits (38 bits)
    val ws_to_ds_valid = out Bool ()
    val csr_era = out Bits (32 bits)
    val csr_esubcode = out Bits (9 bits)
    val csr_ecode = out Bits (6 bits)
    val excp_flush = out Bool ()
    val ertn_flush = out Bool ()
    val refetch_flush = out Bool ()
    val icacop_flush = out Bool ()
    val csr_wr_en = out Bool ()
    val wr_csr_addr = out Bits (14 bits)
    val wr_csr_data = out Bits (32 bits)
    val va_error = out Bool ()
    val bad_va = out Bits (32 bits)
    val excp_tlbrefill = out Bool ()
    val excp_tlb = out Bool ()
    val excp_tlb_vppn = out Bits (19 bits)
    val idle_flush = out Bool ()
    val ws_llbit_set = out Bool ()
    val ws_llbit = out Bool ()
    val ws_lladdr_set = out Bool ()
    val ws_lladdr = out Bits (28 bits)
    val tlb_inst_stall = out Bool ()
    val tlbsrch_en = out Bool ()
    val tlbsrch_found = out Bool ()
    val tlbsrch_index = out Bits (5 bits)
    val tlbfill_en = out Bool ()
    val tlbwr_en = out Bool ()
    val tlbrd_en = out Bool ()
    val invtlb_en = out Bool ()
    val invtlb_asid = out Bits (10 bits)
    val invtlb_vpn = out Bits (19 bits)
    val invtlb_op = out Bits (5 bits)
    val real_valid = out Bool ()
    val real_br_inst = out Bool ()
    val real_icache_miss = out Bool ()
    val real_dcache_miss = out Bool ()
    val real_mem_inst = out Bool ()
    val real_br_pre = out Bool ()
    val real_br_pre_error = out Bool ()
    val debug_ws_valid = out Bool ()
    val debug_break_point = in Bool ()
    val debug_wb_pc = out Bits (32 bits)
    val debug_wb_rf_wen = out Bits (4 bits)
    val debug_wb_rf_wnum = out Bits (5 bits)
    val debug_wb_rf_wdata = out Bits (32 bits)
    val debug_wb_inst = out Bits (32 bits)

    val ws_valid_diff = config.diffTestEnabled generate out(Bool())
    val ws_cnt_inst_diff = config.diffTestEnabled generate out(Bool())
    val ws_timer_64_diff = config.diffTestEnabled generate out(Bits(64 bits))
    val ws_inst_ld_en_diff = config.diffTestEnabled generate out(Bits(8 bits))
    val ws_ld_paddr_diff = config.diffTestEnabled generate out(Bits(32 bits))
    val ws_ld_vaddr_diff = config.diffTestEnabled generate out(Bits(32 bits))
    val ws_inst_st_en_diff = config.diffTestEnabled generate out(Bits(8 bits))
    val ws_st_paddr_diff = config.diffTestEnabled generate out(Bits(32 bits))
    val ws_st_vaddr_diff = config.diffTestEnabled generate out(Bits(32 bits))
    val ws_st_data_diff = config.diffTestEnabled generate out(Bits(32 bits))
    val ws_csr_rstat_en_diff = config.diffTestEnabled generate out(Bool())
    val ws_csr_data_diff = config.diffTestEnabled generate out(Bits(32 bits))
  }

  noIoPrefix()

  val legacyClockDomain = ClockDomain(
    clock = io.clk,
    reset = io.reset,
    config = ClockDomainConfig(clockEdge = RISING, resetKind = SYNC, resetActiveLevel = HIGH)
  )
  val area = new ClockingArea(legacyClockDomain) {
    val stage = new WritebackStage(
      emitCommit = false,
      exposeObservation = config.diffTestEnabled
    )
  }
  val stage = area.stage
  val memoryPayload = MemoryPayload.unpackLegacy(io.ms_to_ws_bus)

  stage.io.input.valid := io.ms_to_ws_valid
  stage.io.input.payload := memoryPayload
  stage.io.debugBreakPoint := io.debug_break_point

  io.ws_allowin := stage.io.input.ready
  io.ws_to_ds_valid := stage.io.stageValid
  io.ws_to_rf_bus := stage.io.registerWrite.valid.asBits ##
    stage.io.registerWrite.index.asBits ## stage.io.registerWrite.data

  io.csr_era := stage.io.debug.pc.asBits
  io.csr_esubcode := stage.io.exception.esubcode.asBits
  io.csr_ecode := stage.io.exception.ecode.asBits
  io.excp_flush := Mux(
    io.debug_break_point,
    stage.io.flush.exception,
    stage.io.exception.valid
  )
  io.ertn_flush := stage.io.flush.ertn
  io.refetch_flush := stage.io.flush.refetch
  io.icacop_flush := stage.io.flush.instructionCacheOperation
  io.csr_wr_en := stage.io.csrWrite.valid
  io.wr_csr_addr := stage.io.csrWrite.address.asBits
  io.wr_csr_data := stage.io.csrWrite.data
  io.va_error := stage.io.exception.badVAddrValid
  io.bad_va := stage.io.exception.badVAddr.asBits
  io.excp_tlbrefill := stage.io.exception.tlbRefill
  io.excp_tlb := stage.io.exception.tlbException
  io.excp_tlb_vppn := stage.io.exception.tlbVppn.asBits
  io.idle_flush := stage.io.flush.idle

  io.ws_llbit_set := stage.io.reservation.bitSet
  io.ws_llbit := stage.io.reservation.bitValue
  io.ws_lladdr_set := stage.io.reservation.addressSet
  io.ws_lladdr := stage.io.reservation.lineAddress.asBits

  io.tlb_inst_stall := stage.io.tlb.instructionStall
  io.tlbsrch_en := stage.io.tlb.search
  io.tlbsrch_found := stage.io.tlb.searchFound
  io.tlbsrch_index := stage.io.tlb.searchIndex.asBits
  io.tlbfill_en := stage.io.tlb.fill
  io.tlbwr_en := stage.io.tlb.write
  io.tlbrd_en := stage.io.tlb.read
  io.invtlb_en := stage.io.tlb.invalidate
  io.invtlb_asid := stage.io.tlb.invalidateAsid
  io.invtlb_vpn := stage.io.tlb.invalidateVpn
  io.invtlb_op := stage.io.tlb.invalidateOperation

  io.real_valid := stage.io.perf.retired
  io.real_br_inst := stage.io.perf.branch
  io.real_icache_miss := stage.io.perf.instructionCacheMiss
  io.real_dcache_miss := stage.io.perf.dataCacheMiss
  io.real_mem_inst := stage.io.perf.memoryAccess
  io.real_br_pre := stage.io.perf.predictedBranch
  io.real_br_pre_error := stage.io.perf.predictionError

  io.debug_ws_valid := stage.io.debug.stageValid
  io.debug_wb_pc := stage.io.debug.pc.asBits
  io.debug_wb_rf_wen := stage.io.debug.gprWriteMask
  io.debug_wb_rf_wnum := stage.io.debug.gprIndex.asBits
  io.debug_wb_rf_wdata := stage.io.debug.gprData
  io.debug_wb_inst := stage.io.debug.instruction

  if (config.diffTestEnabled) {
    val observation = stage.io.observation
    io.ws_valid_diff := stage.io.realValid
    io.ws_cnt_inst_diff := observation.isCounterInstruction
    io.ws_timer_64_diff := observation.timer
    io.ws_inst_ld_en_diff := observation.loadEvent
    io.ws_ld_paddr_diff := observation.memoryPhysicalAddress.asBits
    io.ws_ld_vaddr_diff := observation.memoryVirtualAddress.asBits
    io.ws_inst_st_en_diff := observation.storeEvent
    io.ws_st_paddr_diff := observation.memoryPhysicalAddress.asBits
    io.ws_st_vaddr_diff := observation.memoryVirtualAddress.asBits
    io.ws_st_data_diff := observation.storeData
    io.ws_csr_rstat_en_diff := observation.csrRstatEvent
    io.ws_csr_data_diff := observation.csrData
  }
}

private object WritebackStageGeneratorSupport {
  private def outputArgument(args: Array[String]): String = args match {
    case Array(path) if path.nonEmpty              => path
    case Array("--out-dir", path) if path.nonEmpty => path
    case Array() =>
      sys.env
        .get("OUT_DIR")
        .filter(_.nonEmpty)
        .getOrElse(
          throw new IllegalArgumentException("output directory is required")
        )
    case _ => throw new IllegalArgumentException("usage: generator [--out-dir] <directory>")
  }

  private def findRepositoryRoot(path: Path): Option[Path] =
    if (path == null) None
    else if (Files.exists(path.resolve(".git"))) Some(path)
    else findRepositoryRoot(path.getParent)

  private def prospectiveRealPath(path: Path): Path =
    if (Files.exists(path)) path.toRealPath()
    else {
      val parent = Option(path.getParent).getOrElse(
        throw new IllegalArgumentException(s"output path has no existing ancestor: $path")
      )
      prospectiveRealPath(parent).resolve(path.getFileName).normalize()
    }

  def generate(args: Array[String], config: CoreConfig): Unit = {
    val outputDirectory = Paths.get(outputArgument(args)).toAbsolutePath.normalize()
    val workingDirectory = Paths.get("").toAbsolutePath.normalize()
    val classDirectory = Paths
      .get(getClass.getProtectionDomain.getCodeSource.getLocation.toURI)
      .toAbsolutePath
      .normalize()
    val prospectiveOutput = prospectiveRealPath(outputDirectory)
    Seq(workingDirectory, classDirectory).flatMap(findRepositoryRoot).distinct.foreach { root =>
      val protectedRtl = prospectiveRealPath(root.resolve("rtl"))
      require(
        prospectiveOutput != protectedRtl && !prospectiveOutput.startsWith(protectedRtl),
        s"refusing to write generated RTL under repository RTL: $protectedRtl"
      )
    }
    Files.createDirectories(outputDirectory)
    require(Files.isDirectory(outputDirectory), s"output path is not a directory: $outputDirectory")
    require(outputDirectory.toRealPath() == prospectiveOutput, "output directory changed")

    val spinalConfig =
      SpinalConfig(targetDirectory = outputDirectory.toString, oneFilePerComponent = false)
    spinalConfig.withTimescale = false
    spinalConfig.generateVerilog(new LegacyWritebackStage(config))
  }
}

object GenerateOpenLa500WritebackStage {
  def main(args: Array[String]): Unit =
    WritebackStageGeneratorSupport.generate(args, CoreConfig.Locked)
}

object GenerateOpenLa500WritebackStageDiff {
  def main(args: Array[String]): Unit =
    WritebackStageGeneratorSupport.generate(args, CoreConfig.LockedWithDiffTest)
}
