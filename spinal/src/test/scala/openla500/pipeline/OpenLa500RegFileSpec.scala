package openla500.pipeline

import java.nio.charset.StandardCharsets
import java.nio.file.Files
import openla500.compat.GenerateOpenLa500RegFile
import openla500.config.CoreConfig
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.core.sim._

import scala.jdk.CollectionConverters._
import scala.util.Random

private final class OpenLa500RegFileSimTop extends Component {
  val io = new Bundle {
    val clk = in(Bool())
    val raddr1 = in(UInt(5 bits))
    val rdata1 = out(Bits(32 bits))
    val raddr2 = in(UInt(5 bits))
    val rdata2 = out(Bits(32 bits))
    val we = in(Bool())
    val waddr = in(UInt(5 bits))
    val wdata = in(Bits(32 bits))
    val rf_o = out(Vec(Bits(32 bits), 32))
    val heartbeat = out(Bool())
  }
  noIoPrefix()

  val regfile = new OpenLa500RegFile(CoreConfig.LockedWithDiffTest)
  regfile.io.clk := io.clk
  regfile.io.raddr1 := io.raddr1
  io.rdata1 := regfile.io.rdata1
  regfile.io.raddr2 := io.raddr2
  io.rdata2 := regfile.io.rdata2
  regfile.io.we := io.we
  regfile.io.waddr := io.waddr
  regfile.io.wdata := io.wdata
  io.rf_o := regfile.io.rf_o

  val heartbeat = Reg(Bool()) init (False)
  heartbeat := !heartbeat
  io.heartbeat := heartbeat
}

class OpenLa500RegFileSpec extends AnyFunSuite {
  private def deleteRecursively(path: java.nio.file.Path): Unit = {
    val paths = Files.walk(path)
    try paths.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists)
    finally paths.close()
  }

  test("base and DiffTest variants elaborate without an implicit reset") {
    for (config <- Seq(CoreConfig.Locked, CoreConfig.LockedWithDiffTest)) {
      val output = Files.createTempDirectory(s"openla500-regfile-${config.diffTestEnabled}-")
      try {
        SpinalConfig(targetDirectory = output.toString)
          .generateVerilog(new OpenLa500RegFile(config))
        val rtl = Files.readString(output.resolve("regfile.v"), StandardCharsets.UTF_8)
        assert(rtl.contains("module regfile"))
        assert(!rtl.matches("(?s).*\\breset\\b.*"))
        assert(rtl.contains("rf_o") == config.diffTestEnabled)
      } finally deleteRecursively(output)
    }
  }

  test("Scala generator emits the exact legacy unpacked DiffTest array shell") {
    val output = Files.createTempDirectory("openla500-regfile-generator-")
    try {
      GenerateOpenLa500RegFile.emit(output.toString)
      val wrapper = Files.readString(output.resolve("regfile.v"), StandardCharsets.UTF_8)
      assert(wrapper.contains("module regfile("))
      assert(wrapper.contains("output [31:0] rf_o [31:0]"))
      val header = wrapper.substring(0, wrapper.indexOf(");") + 2)
      val publicPorts =
        "(?m)^\\s*(?:input|output)\\s+(?:\\[[^]]+\\]\\s+)?([A-Za-z][A-Za-z0-9_]*)".r
          .findAllMatchIn(header)
          .map(_.group(1))
          .toSet
      assert(
        publicPorts == Set(
          "clk",
          "raddr1",
          "rdata1",
          "raddr2",
          "rdata2",
          "we",
          "waddr",
          "wdata",
          "rf_o"
        )
      )
      assert(!header.contains("tmp"))
      for (index <- 0 until 32) assert(wrapper.contains(s"assign rf_o[$index]"))
      assert("(?m)^module\\s+".r.findAllIn(wrapper).size == 1)
      assert(!wrapper.contains("openla500_regfile_impl"))
      assert(!wrapper.matches("(?s).*\\breset\\b.*"))
      assert(!Files.exists(output.resolve("openla500_regfile_impl.v")))
    } finally deleteRecursively(output)
  }

  test("unreset storage, zero-read priority and write bypass match the golden contract") {
    val workspace =
      sys.env.getOrElse("SPINAL_SIM_WORKSPACE", "target/sim-workspace-contracts") + "/regfile"
    SimConfig
      .withConfig(SpinalConfig(oneFilePerComponent = true))
      .withVerilator
      .addSimulatorFlag("-Wall")
      .addSimulatorFlag("-Wwarn-WIDTH")
      .addSimulatorFlag("-Wwarn-UNOPTFLAT")
      .addSimulatorFlag("-Wwarn-CMPCONST")
      .addSimulatorFlag("-Wwarn-UNSIGNED")
      .disableCache
      .workspacePath(workspace)
      .compile(new OpenLa500RegFileSimTop)
      .doSim { dut =>
        dut.clockDomain.forkStimulus(period = 10)
        dut.io.clk #= false
        dut.io.we #= false
        dut.io.raddr1 #= 0
        dut.io.raddr2 #= 0
        dut.io.waddr #= 0
        dut.io.wdata #= 0

        def risingEdge(): Unit = {
          sleep(2)
          dut.io.clk #= true
          sleep(2)
          dut.io.clk #= false
          sleep(2)
        }

        val model = Array.fill[BigInt](32)(0)
        for (index <- 0 until 32) {
          val value = BigInt("81000000", 16) + index
          dut.io.we #= true
          dut.io.waddr #= index
          dut.io.wdata #= value
          risingEdge()
          model(index) = value
        }
        dut.io.we #= false
        sleep(1)
        for (index <- 0 until 32) assert(dut.io.rf_o(index).toBigInt == model(index))

        dut.io.raddr1 #= 0
        dut.io.raddr2 #= 9
        dut.io.we #= true
        dut.io.waddr #= 0
        dut.io.wdata #= BigInt("deadbeef", 16)
        sleep(1)
        assert(dut.io.rdata1.toBigInt == 0)
        assert(dut.io.rdata2.toBigInt == model(9))
        risingEdge()
        model(0) = BigInt("deadbeef", 16)
        assert(dut.io.rf_o(0).toBigInt == model(0))
        assert(dut.io.rdata1.toBigInt == 0)

        val random = new Random(0x158aa8L)
        for (_ <- 0 until 1024) {
          val read1 = random.nextInt(32)
          val read2 = random.nextInt(32)
          val write = random.nextBoolean()
          val writeAddress = random.nextInt(32)
          val writeData = BigInt(32, random)
          dut.io.raddr1 #= read1
          dut.io.raddr2 #= read2
          dut.io.we #= write
          dut.io.waddr #= writeAddress
          dut.io.wdata #= writeData
          sleep(1)

          def expected(address: Int): BigInt =
            if (address == 0) 0
            else if (write && address == writeAddress) writeData
            else model(address)

          assert(dut.io.rdata1.toBigInt == expected(read1))
          assert(dut.io.rdata2.toBigInt == expected(read2))
          risingEdge()
          if (write) model(writeAddress) = writeData
        }
      }
  }
}
