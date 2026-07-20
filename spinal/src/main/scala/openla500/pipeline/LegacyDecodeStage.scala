package openla500.pipeline

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}
import openla500.config.CoreConfig
import spinal.core._

/** Exact locked `id_stage` boundary. It only translates legacy buses and clock/reset into typed
  * decode contracts; instruction semantics remain in [[DecodeStage]].
  */
final class LegacyDecodeStage(config: CoreConfig = CoreConfig.Locked) extends Component {
  setDefinitionName("id_stage")

  val io = new Bundle {
    val clk = in Bool ()
    val reset = in Bool ()
    val es_allowin = in Bool ()
    val ds_allowin = out Bool ()
    val fs_to_ds_valid = in Bool ()
    val fs_to_ds_bus = in Bits (FetchPayload.LegacyWidth bits)
    val es_to_ds_forward_bus = in Bits (39 bits)
    val ms_to_ds_forward_bus = in Bits (39 bits)
    val ds_to_es_valid = out Bool ()
    val ds_to_es_bus = out Bits (DecodePayload.legacyWidth(config) bits)
    val br_bus = out Bits (33 bits)
    val excp_flush = in Bool ()
    val ertn_flush = in Bool ()
    val refetch_flush = in Bool ()
    val icacop_flush = in Bool ()
    val idle_flush = in Bool ()
    val es_tlb_inst_stall = in Bool ()
    val ms_tlb_inst_stall = in Bool ()
    val ws_tlb_inst_stall = in Bool ()
    val has_int = in Bool ()
    val rd_csr_addr = out Bits (14 bits)
    val rd_csr_data = in Bits (32 bits)
    val csr_plv = in Bits (2 bits)
    val timer_64 = in Bits (64 bits)
    val csr_tid = in Bits (32 bits)
    val ds_llbit = in Bool ()
    val es_to_ds_valid = in Bool ()
    val ms_to_ds_valid = in Bool ()
    val ws_to_ds_valid = in Bool ()
    val write_buffer_empty = in Bool ()
    val dcache_empty = in Bool ()
    val btb_operate_en = out Bool ()
    val btb_pop_ras = out Bool ()
    val btb_push_ras = out Bool ()
    val btb_add_entry = out Bool ()
    val btb_delete_entry = out Bool ()
    val btb_pre_error = out Bool ()
    val btb_pre_right = out Bool ()
    val btb_target_error = out Bool ()
    val btb_right_orien = out Bool ()
    val btb_right_target = out Bits (32 bits)
    val btb_operate_pc = out Bits (32 bits)
    val btb_operate_index = out Bits (5 bits)
    val infor_flag = in Bool ()
    val reg_num = in Bits (5 bits)
    val debug_rf_rdata1 = out Bits (32 bits)
    val ws_to_rf_bus = in Bits (38 bits)
    val rf_to_diff = config.diffTestEnabled generate out(Vec(Bits(32 bits), 32))
  }
  noIoPrefix()

  val legacyClockDomain = ClockDomain(
    clock = io.clk,
    reset = io.reset,
    config = ClockDomainConfig(clockEdge = RISING, resetKind = SYNC, resetActiveLevel = HIGH)
  )
  val area = new ClockingArea(legacyClockDomain) {
    val stage = new DecodeStage(config)
  }
  val stage = area.stage

  stage.io.input.valid := io.fs_to_ds_valid
  stage.io.input.payload := FetchPayload.unpackLegacy(io.fs_to_ds_bus)
  stage.io.directionPrediction.phtIndex := 0
  stage.io.directionPrediction.baseTaken := False
  stage.io.directionPrediction.localTaken := False
  io.ds_allowin := stage.io.input.ready
  stage.io.output.ready := io.es_allowin
  io.ds_to_es_valid := stage.io.output.valid
  io.ds_to_es_bus := stage.io.output.payload.toLegacyBits

  stage.io.executeForward.dependencyNeedsStall := io.es_to_ds_forward_bus(38)
  stage.io.executeForward.writeEnabled := io.es_to_ds_forward_bus(37)
  stage.io.executeForward.destination := io.es_to_ds_forward_bus(36 downto 32).asUInt
  stage.io.executeForward.data := io.es_to_ds_forward_bus(31 downto 0)
  stage.io.executeLateResultAllowed := False
  stage.io.memoryForward.dependencyNeedsStall := io.ms_to_ds_forward_bus(38)
  stage.io.memoryForward.writeEnabled := io.ms_to_ds_forward_bus(37)
  stage.io.memoryForward.destination := io.ms_to_ds_forward_bus(36 downto 32).asUInt
  stage.io.memoryForward.data := io.ms_to_ds_forward_bus(31 downto 0)

  stage.io.flush.exception := io.excp_flush
  stage.io.flush.ertn := io.ertn_flush
  stage.io.flush.refetch := io.refetch_flush
  stage.io.flush.instructionCacheOperation := io.icacop_flush
  stage.io.flush.idle := io.idle_flush
  stage.io.executeTlbStall := io.es_tlb_inst_stall
  stage.io.memoryTlbStall := io.ms_tlb_inst_stall
  stage.io.writebackTlbStall := io.ws_tlb_inst_stall
  stage.io.interruptPending := io.has_int
  io.rd_csr_addr := stage.io.csrReadAddress.asBits
  stage.io.csrReadData := io.rd_csr_data
  stage.io.csrPrivilege := io.csr_plv
  stage.io.timer := io.timer_64
  stage.io.timerId := io.csr_tid
  stage.io.reservationValid := io.ds_llbit
  stage.io.executeOccupied := io.es_to_ds_valid
  stage.io.memoryOccupied := io.ms_to_ds_valid
  stage.io.writebackOccupied := io.ws_to_ds_valid
  stage.io.writeBufferEmpty := io.write_buffer_empty
  stage.io.dataCacheEmpty := io.dcache_empty
  stage.io.registerWrite.valid := io.ws_to_rf_bus(37)
  stage.io.registerWrite.destination := io.ws_to_rf_bus(36 downto 32).asUInt
  stage.io.registerWrite.data := io.ws_to_rf_bus(31 downto 0)
  stage.io.debugReadSelect := io.infor_flag
  stage.io.debugReadAddress := io.reg_num.asUInt
  io.debug_rf_rdata1 := stage.io.debugLegacyValue

  io.br_bus := stage.io.branchRepair.active.asBits ## stage.io.branchRepair.target.asBits
  io.btb_operate_en := stage.io.btb.enable
  io.btb_pop_ras := stage.io.btb.popReturnStack
  io.btb_push_ras := stage.io.btb.pushReturnStack
  io.btb_add_entry := stage.io.btb.addEntry
  io.btb_delete_entry := stage.io.btb.deleteEntry
  io.btb_pre_error := stage.io.btb.predictionError
  io.btb_pre_right := stage.io.btb.predictionRight
  io.btb_target_error := stage.io.btb.targetError
  io.btb_right_orien := stage.io.btb.actualTaken
  io.btb_right_target := stage.io.btb.actualTarget.asBits
  io.btb_operate_pc := stage.io.btb.pc.asBits
  io.btb_operate_index := stage.io.btb.index.asBits

  if (config.diffTestEnabled) {
    for (index <- 0 until 32) io.rf_to_diff(index) := stage.io.registers(index)
  }
}

private object DecodeStageGeneratorSupport {
  private val DiffTestPort = raw"\s*output wire \[31:0\]\s+rf_to_diff_(\d+),?".r

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

  private def restoreLegacyDiffTestArray(outputDirectory: Path): Unit = {
    val path = outputDirectory.resolve("id_stage.v")
    val original = Files.readString(path, StandardCharsets.US_ASCII)
    val lines = original.split("\n", -1).toVector
    val indices = lines.indices.filter(index => DiffTestPort.matches(lines(index))).toVector
    require(indices.size == 32, s"expected 32 flattened DiffTest ports, found ${indices.size}")
    require(indices == (indices.head to indices.last).toVector, "DiffTest ports are not contiguous")
    val portNumbers =
      indices.map(index => DiffTestPort.findFirstMatchIn(lines(index)).get.group(1).toInt)
    require(portNumbers == (0 until 32), s"unexpected DiffTest port order: $portNumbers")
    var rewritten =
      (lines.take(indices.head) ++ Vector("  output wire [31:0]   rf_to_diff [31:0]") ++ lines
        .drop(indices.last + 1)).mkString("\n")
    for (index <- (0 until 32).reverse) {
      rewritten = rewritten.replace(s"rf_to_diff_$index", s"rf_to_diff[$index]")
    }
    Files.writeString(path, rewritten, StandardCharsets.US_ASCII)
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
    spinalConfig.generateVerilog(new LegacyDecodeStage(config))
    if (config.diffTestEnabled) restoreLegacyDiffTestArray(outputDirectory)
  }
}

object GenerateOpenLa500DecodeStage {
  def main(args: Array[String]): Unit =
    DecodeStageGeneratorSupport.generate(args, CoreConfig.Locked)
}

object GenerateOpenLa500DecodeStageWithLacc {
  def main(args: Array[String]): Unit =
    DecodeStageGeneratorSupport.generate(args, CoreConfig.LockedWithLacc)
}

object GenerateOpenLa500DecodeStageDiff {
  def main(args: Array[String]): Unit =
    DecodeStageGeneratorSupport.generate(args, CoreConfig.LockedWithDiffTest)
}

object GenerateOpenLa500DecodeStageWithLaccDiff {
  def main(args: Array[String]): Unit =
    DecodeStageGeneratorSupport.generate(args, CoreConfig.LockedWithLaccAndDiffTest)
}
