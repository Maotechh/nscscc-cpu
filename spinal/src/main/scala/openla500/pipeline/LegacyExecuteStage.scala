package openla500.pipeline

import java.nio.file.{Files, Path, Paths}
import openla500.config.CoreConfig
import spinal.core._

/** Exact legacy `exe_stage` port adapter for the locked chiplab integration. */
final class LegacyExecuteStage(config: CoreConfig = CoreConfig.Locked) extends Component {
  setDefinitionName("exe_stage")

  val io = new Bundle {
    val clk = in Bool ()
    val reset = in Bool ()
    val ms_allowin = in Bool ()
    val es_allowin = out Bool ()
    val ds_to_es_valid = in Bool ()
    val ds_to_es_bus = in Bits (DecodePayload.legacyWidth(config) bits)
    val es_to_ms_valid = out Bool ()
    val es_to_ms_bus = out Bits (ExecutePayload.LegacyWidth bits)
    val es_to_ds_forward_bus = out Bits (39 bits)
    val es_to_ds_valid = out Bool ()
    val es_div_enable = out Bool ()
    val es_mul_div_sign = out Bool ()
    val es_rj_value = out Bits (32 bits)
    val es_rkd_value = out Bits (32 bits)
    val div_complete = in Bool ()
    val es_lacc_req = config.laccEnabled generate out(Bool())
    val es_lacc_command = config.laccEnabled generate out(Bits(config.laccOpWidth bits))
    val lacc_req_ready = config.laccEnabled generate in(Bool())
    val lacc_data_valid = config.laccEnabled generate in(Bool())
    val lacc_data_read = config.laccEnabled generate in(Bool())
    val lacc_data_addr = config.laccEnabled generate in(Bits(32 bits))
    val lacc_data_wdata = config.laccEnabled generate in(Bits(32 bits))
    val lacc_data_size = config.laccEnabled generate in(Bits(2 bits))
    val lacc_rsp_valid = config.laccEnabled generate in(Bool())
    val lacc_rsp_rdat = config.laccEnabled generate in(Bits(32 bits))
    val lacc_req_imm = config.laccEnabled generate out(Bits(7 bits))
    val lacc_flush = config.laccEnabled generate out(Bool())
    val data_data_ok = config.laccEnabled generate in(Bool())
    val lacc_drsp_valid = config.laccEnabled generate out(Bool())
    val excp_flush = in Bool ()
    val ertn_flush = in Bool ()
    val refetch_flush = in Bool ()
    val icacop_flush = in Bool ()
    val idle_flush = in Bool ()
    val tlb_inst_stall = out Bool ()
    val icacop_op_en = out Bool ()
    val dcacop_op_en = out Bool ()
    val cacop_op_mode = out Bits (2 bits)
    val icache_unbusy = in Bool ()
    val preld_hint = out Bits (5 bits)
    val preld_en = out Bool ()
    val data_valid = out Bool ()
    val data_op = out Bool ()
    val data_size = out Bits (3 bits)
    val data_wstrb = out Bits (4 bits)
    val data_wdata = out Bits (32 bits)
    val data_addr_ok = in Bool ()
    val csr_vppn = in Bits (19 bits)
    val data_addr = out Bits (32 bits)
    val data_fetch = out Bool ()
    val ms_wr_tlbehi = in Bool ()
    val ms_flush = in Bool ()
  }

  noIoPrefix()

  val legacyClockDomain = ClockDomain(
    clock = io.clk,
    reset = io.reset,
    config = ClockDomainConfig(clockEdge = RISING, resetKind = SYNC, resetActiveLevel = HIGH)
  )

  val area = new ClockingArea(legacyClockDomain) {
    val stage = new ExecuteStage(config)
  }
  val stage = area.stage

  stage.io.input.valid := io.ds_to_es_valid
  stage.io.input.payload := DecodePayload.unpackLegacy(io.ds_to_es_bus, config)
  stage.io.lateForwardJ := False
  stage.io.lateForwardKOrD := False
  stage.io.lateForwardDestination := 0
  stage.io.memoryForward.valid := False
  stage.io.memoryForward.dependencyNeedsStall := False
  stage.io.memoryForward.writeEnabled := False
  stage.io.memoryForward.destination := 0
  stage.io.memoryForward.result := 0
  stage.io.output.ready := io.ms_allowin
  io.es_allowin := stage.io.input.ready
  io.es_to_ms_valid := stage.io.output.valid
  io.es_to_ms_bus := stage.io.output.payload.toLegacyBits
  io.es_to_ds_valid := stage.io.forward.valid
  io.es_to_ds_forward_bus := stage.io.forward.dependencyNeedsStall.asBits ##
    stage.io.forward.writeEnabled.asBits ##
    stage.io.forward.destination.asBits ##
    stage.io.forward.result

  io.es_div_enable := stage.io.mulDiv.divideEnable
  io.es_mul_div_sign := stage.io.mulDiv.signed
  io.es_rj_value := stage.io.mulDiv.operandJ
  io.es_rkd_value := stage.io.mulDiv.operandKOrD
  stage.io.divideComplete := io.div_complete

  stage.io.flush.exception := io.excp_flush
  stage.io.flush.ertn := io.ertn_flush
  stage.io.flush.refetch := io.refetch_flush
  stage.io.flush.instructionCacheOperation := io.icacop_flush
  stage.io.flush.idle := io.idle_flush
  stage.io.memoryFlush := io.ms_flush
  stage.io.memoryWritesTlbEntryHigh := io.ms_wr_tlbehi
  stage.io.instructionCacheUnbusy := io.icache_unbusy
  stage.io.memoryAddressAccepted := io.data_addr_ok
  stage.io.csrVirtualPageNumber := io.csr_vppn.asUInt

  io.data_valid := stage.io.memory.valid
  io.data_op := stage.io.memory.isWrite
  io.data_size := stage.io.memory.size
  io.data_wstrb := stage.io.memory.byteMask
  io.data_wdata := stage.io.memory.writeData
  io.data_addr := stage.io.memory.virtualAddress.asBits
  io.data_fetch := stage.io.dataFetch
  io.tlb_inst_stall := stage.io.tlbInstructionStall
  io.icacop_op_en := stage.io.cache.instructionOperationEnable
  io.dcacop_op_en := stage.io.cache.dataOperationEnable
  io.cacop_op_mode := stage.io.cache.operationMode
  io.preld_hint := stage.io.cache.preloadHint
  io.preld_en := stage.io.cache.preloadEnable

  if (config.laccEnabled) {
    stage.io.laccInput.requestReady := io.lacc_req_ready
    stage.io.laccInput.dataValid := io.lacc_data_valid
    stage.io.laccInput.dataRead := io.lacc_data_read
    stage.io.laccInput.dataAddress := io.lacc_data_addr.asUInt
    stage.io.laccInput.dataWriteData := io.lacc_data_wdata
    stage.io.laccInput.dataSize := io.lacc_data_size
    stage.io.laccInput.responseValid := io.lacc_rsp_valid
    stage.io.laccInput.responseData := io.lacc_rsp_rdat
    stage.io.laccInput.dataAccepted := io.data_data_ok
    io.es_lacc_req := stage.io.laccOutput.request
    io.es_lacc_command := stage.io.laccOutput.command
    io.lacc_req_imm := stage.io.laccOutput.immediate
    io.lacc_flush := stage.io.laccOutput.flush
    io.lacc_drsp_valid := stage.io.laccOutput.dataResponseValid
  }
}

private object ExecuteStageGeneratorSupport {
  private def outputArgument(args: Array[String]): String =
    args match {
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

  def generate(args: Array[String], config: CoreConfig): Unit = {
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
    spinalConfig.generateVerilog(new LegacyExecuteStage(config))
  }
}

object GenerateOpenLa500ExecuteStage {
  def main(args: Array[String]): Unit =
    ExecuteStageGeneratorSupport.generate(args, CoreConfig.Locked)
}

object GenerateOpenLa500ExecuteStageWithLacc {
  def main(args: Array[String]): Unit =
    ExecuteStageGeneratorSupport.generate(args, CoreConfig.LockedWithLacc)
}
