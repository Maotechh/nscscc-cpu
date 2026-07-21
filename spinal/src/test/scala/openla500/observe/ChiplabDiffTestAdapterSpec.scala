package openla500.observe

import java.nio.charset.StandardCharsets
import java.nio.file.Files
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._

import scala.jdk.CollectionConverters._

private final class ChiplabDiffTestAdapterProbe extends Component {
  val io = new Bundle {
    val clock = in Bool ()
  }
  val adapter = new ChiplabDiffTestAdapter
  adapter.io.clock := io.clock
  adapter.io.commit.valid := False
  adapter.io.commit.payload.assignDontCare()
  adapter.io.archState.assignDontCare()
}

class ChiplabDiffTestAdapterSpec extends AnyFunSuite {
  test("generated conditional wrapper contains all seven official chiplab Difftest modules") {
    val outputDirectory = Files.createTempDirectory("openla500-chiplab-difftest-")
    try {
      SpinalConfig(targetDirectory = outputDirectory.toString, removePruned = false)
        .generateVerilog(new ChiplabDiffTestAdapterProbe)

      val rtl = Files
        .walk(outputDirectory)
        .iterator()
        .asScala
        .filter(path => Files.isRegularFile(path) && path.toString.endsWith(".v"))
        .map(path => Files.readString(path, StandardCharsets.UTF_8))
        .mkString("\n")

      val officialModules = Seq(
        "DifftestInstrCommit",
        "DifftestExcpEvent",
        "DifftestTrapEvent",
        "DifftestStoreEvent",
        "DifftestLoadEvent",
        "DifftestCSRRegState",
        "DifftestGRegState"
      )
      officialModules.foreach(name => assert(rtl.contains(s"$name u_difftest_")))
      (0 until CommitGroup.Width).foreach { lane =>
        assert(rtl.contains(s"u_difftest_instr_commit_$lane"))
        assert(rtl.contains(s"u_difftest_store_$lane"))
        assert(rtl.contains(s"u_difftest_load_$lane"))
      }
      assert(rtl.contains("`ifdef DIFFTEST_EN"))
      assert(rtl.contains("`ifndef DIFFTEST_EN"))
      assert(
        rtl
          .sliding("verilator lint_off UNUSEDSIGNAL".length)
          .count(_ == "verilator lint_off UNUSEDSIGNAL") == 1
      )
      assert(
        rtl
          .sliding("verilator lint_on UNUSEDSIGNAL".length)
          .count(_ == "verilator lint_on UNUSEDSIGNAL") == 1
      )
      assert(rtl.contains(".valid(instrValid[0])"))
      assert(rtl.contains(".index(8'd1)"))
      assert(rtl.contains(".index(8'd2)"))
      assert(rtl.contains(".skip(1'b0 & ^commitContract[504:0])"))
      assert(rtl.contains(".TLBFILL_index(tlbFillIndex[4:0])"))
      assert(rtl.contains(".valid(storeValid[15:8])"))
      assert(rtl.contains(".valid(loadValid[23:16])"))
      assert(rtl.contains(".euen(64'b0 & csrState[191:128])"))
      assert(rtl.contains(".gpr_0(64'b0 & gprState[63:0])"))
      assert(rtl.contains("input  wire [2047:0] gprState"))
      assert(!rtl.contains("registeredArchState"))
      assert(rtl.contains("registeredCommit"))
      Seq(
        "assign wrapper_interruptNumber = {21'h0,io_archState_estat[12 : 2]};",
        "assign wrapper_exceptionCause = {26'h0,selectedControl_exceptionCode};",
        "assign wrapper_exceptionPc = {32'h0,selectedControl_pc};",
        "assign wrapper_trapPc = {32'h0,registeredCommit_events_0_pc};"
      ).foreach(expected => assert(rtl.contains(expected)))
      assert(!rtl.contains("selectedControl_gprWrite"))
      assert(!rtl.contains("selectedControl_store"))
    } finally {
      Files.walk(outputDirectory).iterator().asScala.toSeq.reverse.foreach(Files.delete)
    }
  }
}
