package openla500.config

import openla500.compat.CoreTopCompatConfig
import org.scalatest.funsuite.AnyFunSuite

class CoreConfigSpec extends AnyFunSuite {
  test("locked configurations match the active golden core") {
    for (config <- CoreConfig.Supported) {
      assert(config.xlen == 32)
      assert(config.gprCount == 32)
      assert(config.resetVector == BigInt("1c000000", 16))
      assert(config.resetDelayCycles == 1)
      assert(config.tlbEntries == 32)
      assert(config.btbEntries == 32)
      assert(config.rasEntries == 16)
      assert(config.returnStackDepth == 8)
      assert(config.instructionCache.capacityBytes == 32768)
      assert(config.dataCache.capacityBytes == 32768)
      assert(config.instructionCache == CacheGeometry(2, 1024, 16))
      assert(config.dataCache == CacheGeometry(2, 1024, 16))
      assert(config.fetchToDecodeWidth == 109)
      assert(config.executeToMemoryWidth == 425)
      assert(config.memoryToWritebackWidth == 493)
    }

    assert(!CoreConfig.Locked.laccEnabled)
    assert(CoreConfig.Locked.decodeToExecuteWidth == 350)
    assert(CoreConfig.LockedWithLacc.laccEnabled)
    assert(CoreConfig.LockedWithLacc.laccOpWidth == 2)
    assert(CoreConfig.LockedWithLacc.decodeToExecuteWidth == 353)
    assert(
      CoreConfig.Supported.map(config => (config.laccEnabled, config.diffTestEnabled)).toSet ==
        Set((false, false), (true, false), (false, true), (true, true))
    )
    assert(CoreConfig.LockedWithDiffTest.diffTestEnabled)
    assert(CoreConfig.LockedWithLaccAndDiffTest.laccEnabled)
    assert(CoreConfig.LockedWithLaccAndDiffTest.diffTestEnabled)
    assert(CoreConfig.Supported.forall(_.debugEnabled))
    assert(CoreConfig.Supported.forall(_.isa == IsaFeatures()))

    val defaultTop = CoreTopCompatConfig()
    val laccTop = CoreTopCompatConfig(laccEnabled = true)
    assert(defaultTop.backendConfig == CoreConfig.LockedWithDiffTest)
    assert(!defaultTop.backendConfig.laccEnabled)
    assert(laccTop.backendConfig == CoreConfig.LockedWithLaccAndDiffTest)
    assert(laccTop.backendConfig.laccEnabled)
  }

  test("unsupported configuration changes fail closed") {
    val invalidConfigs = Seq[() => Any](
      () => CoreConfig(xlen = 64),
      () => CoreConfig(gprCount = 16),
      () => CoreConfig(resetVector = 0),
      () => CoreConfig(resetDelayCycles = 0),
      () => CoreConfig(tlbEntries = 16),
      () => CoreConfig(btbEntries = 64),
      () => CoreConfig(rasEntries = 8),
      () => CoreConfig(returnStackDepth = 4),
      () => CoreConfig(instructionCache = CacheGeometry(2, 128, 16)),
      () => CoreConfig(dataCache = CacheGeometry(2, 256, 16)),
      () => CoreConfig(dataCache = CacheGeometry(4, 256, 16)),
      () => CoreConfig(laccEnabled = true, laccOpWidth = 3),
      () => CoreConfig(debugEnabled = false),
      () => CoreConfig(isa = IsaFeatures(barriers = false)),
      () => CacheGeometry(1, 256, 16),
      () => CacheGeometry(2, 512, 16),
      () => CacheGeometry(2, 256, 32)
    )

    invalidConfigs.foreach(make => intercept[IllegalArgumentException](make()))
  }
}
