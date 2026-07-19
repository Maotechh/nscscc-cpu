package openla500.ooo

import java.nio.charset.StandardCharsets
import java.nio.file.Files
import org.scalatest.funsuite.AnyFunSuite
import spinal.core._

class OooBackendWithDataCacheSpec extends AnyFunSuite {
  test("the OoO backend elaborates with the 64-byte L1D and L2 hierarchy") {
    val outputDirectory = Files.createTempDirectory("ooo-backend-data-cache-")
    val spinalConfig = SpinalConfig(
      targetDirectory = outputDirectory.toString,
      oneFilePerComponent = false,
      headerWithDate = false,
      headerWithRepoHash = false
    )
    spinalConfig.withTimescale = false
    spinalConfig.generateVerilog {
      val top = new OooBackendWithDataCache(OooCoreConfig.FourIssueThreeCommit)
      top.setDefinitionName("ooo_backend_with_data_cache")
      top
    }

    val rtl = Files.readString(
      outputDirectory.resolve("ooo_backend_with_data_cache.v"),
      StandardCharsets.UTF_8
    )
    assert(rtl.contains("module ooo_backend_with_data_cache"))
    assert(rtl.contains("module OooBackendWithExecution"))
    assert(rtl.contains("module OooL1DataCache"))
    assert(rtl.contains("module OooL2Cache"))
    assert(rtl.contains("memoryReadValid"))
    assert(rtl.contains("cacheInvalidateBusy"))
  }
}
