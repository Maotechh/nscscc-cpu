package openla500.pipeline

import java.nio.file.{Files, Path, Paths}
import spinal.core._

/** Exact legacy `mem_stage` shell. All architectural behavior lives in MemoryStage. */
final class LegacyMemoryStage extends Component {
  setDefinitionName("mem_stage")
  val io = new Bundle {
    val clk = in Bool ()
    val reset = in Bool ()
    val ws_allowin = in Bool ()
    val ms_allowin = out Bool ()
    val es_to_ms_valid = in Bool ()
    val es_to_ms_bus = in Bits (ExecutePayload.LegacyWidth bits)
    val ms_to_ws_valid = out Bool ()
    val ms_to_ws_bus = out Bits (MemoryPayload.LegacyWidth bits)
    val ms_to_ds_forward_bus = out Bits (39 bits)
    val ms_to_ds_valid = out Bool ()
    val div_result = in Bits (32 bits)
    val mod_result = in Bits (32 bits)
    val mul_result = in Bits (64 bits)
    val excp_flush = in Bool ()
    val ertn_flush = in Bool ()
    val refetch_flush = in Bool ()
    val icacop_flush = in Bool ()
    val idle_flush = in Bool ()
    val tlb_inst_stall = out Bool ()
    val ms_wr_tlbehi = out Bool ()
    val ms_flush = out Bool ()
    val data_data_ok = in Bool ()
    val dcache_miss = in Bool ()
    val data_rdata = in Bits (32 bits)
    val data_uncache_en = out Bool ()
    val tlb_excp_cancel_req = out Bool ()
    val sc_cancel_req = out Bool ()
    val csr_pg = in Bool ()
    val csr_da = in Bool ()
    val csr_dmw0 = in Bits (32 bits)
    val csr_dmw1 = in Bits (32 bits)
    val csr_plv = in Bits (2 bits)
    val csr_datm = in Bits (2 bits)
    val disable_cache = in Bool ()
    val lladdr = in Bits (28 bits)
    val data_index_diff = in Bits (8 bits)
    val data_tag_diff = in Bits (20 bits)
    val data_offset_diff = in Bits (4 bits)
    val data_addr_trans_en = out Bool ()
    val dmw0_en = out Bool ()
    val dmw1_en = out Bool ()
    val cacop_op_mode_di = out Bool ()
    val data_tlb_found = in Bool ()
    val data_tlb_index = in Bits (5 bits)
    val data_tlb_v = in Bool ()
    val data_tlb_d = in Bool ()
    val data_tlb_mat = in Bits (2 bits)
    val data_tlb_plv = in Bits (2 bits)
    val data_tlb_ppn = in Bits (20 bits)
  }
  noIoPrefix()

  override val clockDomain = ClockDomain(
    clock = io.clk,
    reset = io.reset,
    config = ClockDomainConfig(clockEdge = RISING, resetKind = SYNC, resetActiveLevel = HIGH)
  )
  val area = new ClockingArea(clockDomain) { val stage = new MemoryStage }
  val stage = area.stage
  stage.io.input.valid := io.es_to_ms_valid
  stage.io.input.payload := ExecutePayload.unpackLegacy(io.es_to_ms_bus)
  stage.io.output.ready := io.ws_allowin
  io.ms_allowin := stage.io.input.ready
  io.ms_to_ws_valid := stage.io.output.valid
  io.ms_to_ws_bus := stage.io.output.payload.toLegacyBits
  io.ms_to_ds_valid := stage.io.forward.valid
  io.ms_to_ds_forward_bus := stage.io.forward.dependencyNeedsStall.asBits ##
    stage.io.forward.writeEnabled.asBits ## stage.io.forward.destination.asBits ## stage.io.forward.result
  stage.io.divResult := io.div_result
  stage.io.modResult := io.mod_result
  stage.io.mulResult := io.mul_result
  stage.io.flush.exception := io.excp_flush
  stage.io.flush.ertn := io.ertn_flush
  stage.io.flush.refetch := io.refetch_flush
  stage.io.flush.instructionCacheOperation := io.icacop_flush
  stage.io.flush.idle := io.idle_flush
  stage.io.dataDataOk := io.data_data_ok
  stage.io.dcacheMiss := io.dcache_miss
  stage.io.dataReadData := io.data_rdata
  stage.io.csrPage := io.csr_pg
  stage.io.csrDirectAddress := io.csr_da
  stage.io.csrDmw0Plv0 := io.csr_dmw0(0)
  stage.io.csrDmw0Plv3 := io.csr_dmw0(3)
  stage.io.csrDmw0VirtualSegment := io.csr_dmw0(31 downto 29)
  stage.io.csrDmw0MemoryAttribute := io.csr_dmw0(5 downto 4)
  stage.io.csrDmw1Plv0 := io.csr_dmw1(0)
  stage.io.csrDmw1Plv3 := io.csr_dmw1(3)
  stage.io.csrDmw1VirtualSegment := io.csr_dmw1(31 downto 29)
  stage.io.csrDmw1MemoryAttribute := io.csr_dmw1(5 downto 4)
  stage.io.csrPlv := io.csr_plv
  stage.io.csrDatm := io.csr_datm
  stage.io.disableCache := io.disable_cache
  stage.io.llAddress := io.lladdr
  stage.io.dataIndexDiff := io.data_index_diff
  stage.io.dataTagDiff := io.data_tag_diff
  stage.io.dataOffsetDiff := io.data_offset_diff
  stage.io.dataTlbFound := io.data_tlb_found
  stage.io.dataTlbIndex := io.data_tlb_index.asUInt
  stage.io.dataTlbValid := io.data_tlb_v
  stage.io.dataTlbDirty := io.data_tlb_d
  stage.io.dataTlbMat := io.data_tlb_mat
  stage.io.dataTlbPlv := io.data_tlb_plv
  stage.io.dataTlbPpn := io.data_tlb_ppn
  io.tlb_inst_stall := stage.io.tlbInstructionStall
  io.ms_wr_tlbehi := stage.io.writeTlbEntryHigh
  io.ms_flush := stage.io.stageFlush
  io.data_uncache_en := stage.io.dataUncached
  io.tlb_excp_cancel_req := stage.io.tlbExceptionCancel
  io.sc_cancel_req := stage.io.scCancel
  io.data_addr_trans_en := stage.io.dataAddressTranslationEnable
  io.dmw0_en := stage.io.dmw0Enable
  io.dmw1_en := stage.io.dmw1Enable
  io.cacop_op_mode_di := stage.io.cacopModeDi
}

private object MemoryStageGeneratorSupport {
  private def outputArgument(args: Array[String]): String = args match {
    case Array(path) if path.nonEmpty              => path
    case Array("--out-dir", path) if path.nonEmpty => path
    case Array() =>
      sys.env
        .get("OUT_DIR")
        .filter(_.nonEmpty)
        .getOrElse(throw new IllegalArgumentException("output directory is required"))
    case _ => throw new IllegalArgumentException("usage: generator [--out-dir] <directory>")
  }

  private def findRepositoryRoot(path: Path): Option[Path] =
    if (path == null) None
    else if (Files.exists(path.resolve(".git"))) Some(path)
    else findRepositoryRoot(path.getParent)

  private def prospectiveRealPath(path: Path): Path =
    if (Files.exists(path)) path.toRealPath()
    else {
      val parent = Option(path.getParent).getOrElse {
        throw new IllegalArgumentException(s"output path has no existing ancestor: $path")
      }
      prospectiveRealPath(parent).resolve(path.getFileName).normalize()
    }

  def generate(args: Array[String]): Unit = {
    val outputDirectory = Paths.get(outputArgument(args)).toAbsolutePath.normalize()
    val workingDirectory = Paths.get("").toAbsolutePath.normalize()
    val classDirectory = Paths
      .get(getClass.getProtectionDomain.getCodeSource.getLocation.toURI)
      .toAbsolutePath
      .normalize()
    val prospectiveOutput = prospectiveRealPath(outputDirectory)
    Seq(workingDirectory, classDirectory).flatMap(findRepositoryRoot).distinct.foreach {
      repositoryRoot =>
        val protectedRtl = prospectiveRealPath(repositoryRoot.resolve("rtl"))
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
    spinalConfig.generateVerilog(new LegacyMemoryStage)
  }
}

object GenerateOpenLa500MemoryStage {
  def main(args: Array[String]): Unit = MemoryStageGeneratorSupport.generate(args)
}
