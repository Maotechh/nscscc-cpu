package openla500.config

import java.nio.charset.StandardCharsets
import java.nio.file.Files
import openla500.observe.CommitEvent
import openla500.pipeline.DecodePayload
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._
import spinal.lib._

import scala.jdk.CollectionConverters._

private final class CoreContractsProbe(config: CoreConfig) extends Component {
  val io = new Bundle {
    val legacyDecode = in(Bits(config.decodeToExecuteWidth bits))
    val decodeRoundTrip = out(Bits(config.decodeToExecuteWidth bits))
    val commit = config.diffTestEnabled generate master(CommitEvent.flow())
  }
  noIoPrefix()

  val decoded = DecodePayload.unpackLegacy(io.legacyDecode, config)
  io.decodeRoundTrip := decoded.toLegacyBits

  if (config.diffTestEnabled) {
    io.commit.valid := False
    io.commit.payload.assignDontCare()
  }
}

class CoreContractsElaborationSpec extends AnyFunSuite {
  test("all locked LACC and DiffTest configurations elaborate as real IO") {
    CoreConfig.Supported.foreach { config =>
      val outputDirectory = Files.createTempDirectory(
        s"core-contracts-lacc-${config.laccEnabled}-difftest-${config.diffTestEnabled}-"
      )
      try {
        SpinalConfig(targetDirectory = outputDirectory.toString)
          .generateVerilog(new CoreContractsProbe(config))
        val rtl = Files.readString(
          outputDirectory.resolve("CoreContractsProbe.v"),
          StandardCharsets.UTF_8
        )
        val decodePort =
          (s"(?m)^\\s*input\\s+wire\\s+\\[${config.decodeToExecuteWidth - 1}:0\\]\\s+legacyDecode\\s*,?$$").r
        assert(decodePort.findFirstIn(rtl).nonEmpty)
        assert(rtl.contains("decodeRoundTrip"))
        assert(rtl.contains("commit_valid") == config.diffTestEnabled)
      } finally {
        Files.walk(outputDirectory).iterator().asScala.toSeq.reverse.foreach(Files.delete)
      }
    }
  }
}
