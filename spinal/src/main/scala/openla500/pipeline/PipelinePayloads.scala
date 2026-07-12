package openla500.pipeline

import openla500.config.CoreConfig
import spinal.core._

/** One named field in an historical Verilog pipeline bus. */
final case class LegacyBitField(name: String, high: Int, low: Int) {
  require(name.nonEmpty, "legacy field name must not be empty")
  require(low >= 0 && high >= low, s"invalid legacy bit range $high:$low for $name")

  val width: Int = high - low + 1
}

private object LegacyPayloadSupport {
  def validate(width: Int, fields: Seq[LegacyBitField]): Unit = {
    require(fields.nonEmpty, "legacy layout must not be empty")
    require(fields.head.low == 0, "legacy layout must start at bit zero")
    fields.sliding(2).foreach {
      case Seq(lower, upper) =>
        require(
          lower.high + 1 == upper.low,
          s"legacy layout has a gap or overlap between ${lower.name} and ${upper.name}"
        )
      case _ =>
    }
    require(fields.last.high == width - 1, s"legacy layout does not cover $width bits")
    require(fields.map(_.name).distinct.size == fields.size, "legacy field names must be unique")
  }

  def packMostToLeast(fields: Data*): Bits = fields.map(_.asBits).reduce(_ ## _)

  def requireWidth(bits: Bits, expected: Int): Unit =
    require(bits.getWidth == expected, s"expected $expected legacy bits, got ${bits.getWidth}")
}

/** IF-to-ID data. Valid/ready ownership intentionally remains outside this directionless payload.
  */
final case class FetchPayload() extends Bundle {
  val pc = UInt(32 bits)
  val instruction = Bits(32 bits)
  val exceptionCode = Bits(4 bits)
  val hasException = Bool()
  val instructionCacheMiss = Bool()
  val btbEnabled = Bool()
  val btbTaken = Bool()
  val btbIndex = UInt(5 bits)
  val btbTarget = UInt(32 bits)

  def toLegacyBits: Bits = FetchPayload.packLegacy(this)
}

object FetchPayload {
  val LegacyWidth = 109
  val LegacyLayout: Vector[LegacyBitField] = Vector(
    LegacyBitField("pc", 31, 0),
    LegacyBitField("instruction", 63, 32),
    LegacyBitField("exceptionCode", 67, 64),
    LegacyBitField("hasException", 68, 68),
    LegacyBitField("instructionCacheMiss", 69, 69),
    LegacyBitField("btbEnabled", 70, 70),
    LegacyBitField("btbTaken", 71, 71),
    LegacyBitField("btbIndex", 76, 72),
    LegacyBitField("btbTarget", 108, 77)
  )
  LegacyPayloadSupport.validate(LegacyWidth, LegacyLayout)

  def packLegacy(payload: FetchPayload): Bits = LegacyPayloadSupport.packMostToLeast(
    payload.btbTarget,
    payload.btbIndex,
    payload.btbTaken,
    payload.btbEnabled,
    payload.instructionCacheMiss,
    payload.hasException,
    payload.exceptionCode,
    payload.instruction,
    payload.pc
  )

  def unpackLegacy(bits: Bits): FetchPayload = {
    LegacyPayloadSupport.requireWidth(bits, LegacyWidth)
    val payload = FetchPayload()
    payload.pc := bits(31 downto 0).asUInt
    payload.instruction := bits(63 downto 32)
    payload.exceptionCode := bits(67 downto 64)
    payload.hasException := bits(68)
    payload.instructionCacheMiss := bits(69)
    payload.btbEnabled := bits(70)
    payload.btbTaken := bits(71)
    payload.btbIndex := bits(76 downto 72).asUInt
    payload.btbTarget := bits(108 downto 77).asUInt
    payload
  }
}

/** ID-to-EX data in the exact golden bus order, optionally including the locked LACC extension. */
final case class DecodePayload(config: CoreConfig = CoreConfig.Locked) extends Bundle {
  val pc = UInt(32 bits)
  val registerDataKOrD = Bits(32 bits)
  val registerDataJ = Bits(32 bits)
  val immediate = Bits(32 bits)
  val destination = UInt(5 bits)
  val isStore = Bool()
  val gprWrite = Bool()
  val source2IsFour = Bool()
  val source2IsImmediate = Bool()
  val source1IsPc = Bool()
  val isLoad = Bool()
  val aluOperation = Bits(14 bits)
  val mulDivSigned = Bool()
  val mulDivOperation = Bits(4 bits)
  val memorySize = Bits(2 bits)
  val hasException = Bool()
  val isErtn = Bool()
  val csrReadData = Bits(32 bits)
  val resultFromCsr = Bool()
  val csrAddress = UInt(14 bits)
  val csrWrite = Bool()
  val csrMask = Bool()
  val exceptionCode = Bits(9 bits)
  val isLl = Bool()
  val isSc = Bool()
  val tlbSearch = Bool()
  val tlbWrite = Bool()
  val tlbFill = Bool()
  val refetch = Bool()
  val tlbRead = Bool()
  val invalidateTlb = Bool()
  val memorySignExtend = Bool()
  val cacheOperation = Bool()
  val preload = Bool()
  val isBranch = Bool()
  val instructionCacheMiss = Bool()
  val isPredictableBranch = Bool()
  val predictionError = Bool()
  val idle = Bool()
  val instruction = Bits(32 bits)
  val timer = Bits(64 bits)
  val isCounterInstruction = Bool()
  val loadEvent = Bits(8 bits)
  val storeEvent = Bits(8 bits)
  val csrRstatEvent = Bool()
  val laccRequest = config.laccEnabled generate Bool()
  val laccCommand = config.laccEnabled generate Bits(config.laccOpWidth bits)

  def toLegacyBits: Bits = DecodePayload.packLegacy(this)
}

object DecodePayload {
  val BaseLegacyWidth = 350
  val LaccLegacyWidth = 353
  val BaseLegacyLayout: Vector[LegacyBitField] = Vector(
    LegacyBitField("pc", 31, 0),
    LegacyBitField("registerDataKOrD", 63, 32),
    LegacyBitField("registerDataJ", 95, 64),
    LegacyBitField("immediate", 127, 96),
    LegacyBitField("destination", 132, 128),
    LegacyBitField("isStore", 133, 133),
    LegacyBitField("gprWrite", 134, 134),
    LegacyBitField("source2IsFour", 135, 135),
    LegacyBitField("source2IsImmediate", 136, 136),
    LegacyBitField("source1IsPc", 137, 137),
    LegacyBitField("isLoad", 138, 138),
    LegacyBitField("aluOperation", 152, 139),
    LegacyBitField("mulDivSigned", 153, 153),
    LegacyBitField("mulDivOperation", 157, 154),
    LegacyBitField("memorySize", 159, 158),
    LegacyBitField("hasException", 160, 160),
    LegacyBitField("isErtn", 161, 161),
    LegacyBitField("csrReadData", 193, 162),
    LegacyBitField("resultFromCsr", 194, 194),
    LegacyBitField("csrAddress", 208, 195),
    LegacyBitField("csrWrite", 209, 209),
    LegacyBitField("csrMask", 210, 210),
    LegacyBitField("exceptionCode", 219, 211),
    LegacyBitField("isLl", 220, 220),
    LegacyBitField("isSc", 221, 221),
    LegacyBitField("tlbSearch", 222, 222),
    LegacyBitField("tlbWrite", 223, 223),
    LegacyBitField("tlbFill", 224, 224),
    LegacyBitField("refetch", 225, 225),
    LegacyBitField("tlbRead", 226, 226),
    LegacyBitField("invalidateTlb", 227, 227),
    LegacyBitField("memorySignExtend", 228, 228),
    LegacyBitField("cacheOperation", 229, 229),
    LegacyBitField("preload", 230, 230),
    LegacyBitField("isBranch", 231, 231),
    LegacyBitField("instructionCacheMiss", 232, 232),
    LegacyBitField("isPredictableBranch", 233, 233),
    LegacyBitField("predictionError", 234, 234),
    LegacyBitField("idle", 235, 235),
    LegacyBitField("instruction", 267, 236),
    LegacyBitField("timer", 331, 268),
    LegacyBitField("isCounterInstruction", 332, 332),
    LegacyBitField("loadEvent", 340, 333),
    LegacyBitField("storeEvent", 348, 341),
    LegacyBitField("csrRstatEvent", 349, 349)
  )
  val LaccLegacyLayout: Vector[LegacyBitField] = BaseLegacyLayout ++ Vector(
    LegacyBitField("laccRequest", 350, 350),
    LegacyBitField("laccCommand", 352, 351)
  )
  LegacyPayloadSupport.validate(BaseLegacyWidth, BaseLegacyLayout)
  LegacyPayloadSupport.validate(LaccLegacyWidth, LaccLegacyLayout)

  def legacyWidth(config: CoreConfig): Int = config.decodeToExecuteWidth

  private def packBase(payload: DecodePayload): Bits = LegacyPayloadSupport.packMostToLeast(
    payload.csrRstatEvent,
    payload.storeEvent,
    payload.loadEvent,
    payload.isCounterInstruction,
    payload.timer,
    payload.instruction,
    payload.idle,
    payload.predictionError,
    payload.isPredictableBranch,
    payload.instructionCacheMiss,
    payload.isBranch,
    payload.preload,
    payload.cacheOperation,
    payload.memorySignExtend,
    payload.invalidateTlb,
    payload.tlbRead,
    payload.refetch,
    payload.tlbFill,
    payload.tlbWrite,
    payload.tlbSearch,
    payload.isSc,
    payload.isLl,
    payload.exceptionCode,
    payload.csrMask,
    payload.csrWrite,
    payload.csrAddress,
    payload.resultFromCsr,
    payload.csrReadData,
    payload.isErtn,
    payload.hasException,
    payload.memorySize,
    payload.mulDivOperation,
    payload.mulDivSigned,
    payload.aluOperation,
    payload.isLoad,
    payload.source1IsPc,
    payload.source2IsImmediate,
    payload.source2IsFour,
    payload.gprWrite,
    payload.isStore,
    payload.destination,
    payload.immediate,
    payload.registerDataJ,
    payload.registerDataKOrD,
    payload.pc
  )

  def packLegacy(payload: DecodePayload): Bits = {
    val base = packBase(payload)
    if (payload.config.laccEnabled)
      LegacyPayloadSupport.packMostToLeast(payload.laccCommand, payload.laccRequest, base)
    else base
  }

  def unpackLegacy(bits: Bits, config: CoreConfig = CoreConfig.Locked): DecodePayload = {
    LegacyPayloadSupport.requireWidth(bits, legacyWidth(config))
    val payload = DecodePayload(config)
    payload.pc := bits(31 downto 0).asUInt
    payload.registerDataKOrD := bits(63 downto 32)
    payload.registerDataJ := bits(95 downto 64)
    payload.immediate := bits(127 downto 96)
    payload.destination := bits(132 downto 128).asUInt
    payload.isStore := bits(133)
    payload.gprWrite := bits(134)
    payload.source2IsFour := bits(135)
    payload.source2IsImmediate := bits(136)
    payload.source1IsPc := bits(137)
    payload.isLoad := bits(138)
    payload.aluOperation := bits(152 downto 139)
    payload.mulDivSigned := bits(153)
    payload.mulDivOperation := bits(157 downto 154)
    payload.memorySize := bits(159 downto 158)
    payload.hasException := bits(160)
    payload.isErtn := bits(161)
    payload.csrReadData := bits(193 downto 162)
    payload.resultFromCsr := bits(194)
    payload.csrAddress := bits(208 downto 195).asUInt
    payload.csrWrite := bits(209)
    payload.csrMask := bits(210)
    payload.exceptionCode := bits(219 downto 211)
    payload.isLl := bits(220)
    payload.isSc := bits(221)
    payload.tlbSearch := bits(222)
    payload.tlbWrite := bits(223)
    payload.tlbFill := bits(224)
    payload.refetch := bits(225)
    payload.tlbRead := bits(226)
    payload.invalidateTlb := bits(227)
    payload.memorySignExtend := bits(228)
    payload.cacheOperation := bits(229)
    payload.preload := bits(230)
    payload.isBranch := bits(231)
    payload.instructionCacheMiss := bits(232)
    payload.isPredictableBranch := bits(233)
    payload.predictionError := bits(234)
    payload.idle := bits(235)
    payload.instruction := bits(267 downto 236)
    payload.timer := bits(331 downto 268)
    payload.isCounterInstruction := bits(332)
    payload.loadEvent := bits(340 downto 333)
    payload.storeEvent := bits(348 downto 341)
    payload.csrRstatEvent := bits(349)
    if (config.laccEnabled) {
      payload.laccRequest := bits(350)
      payload.laccCommand := bits(352 downto 351)
    }
    payload
  }
}

/** EX-to-MEM data in the exact 425-bit golden bus order. */
final case class ExecutePayload() extends Bundle {
  val pc = UInt(32 bits)
  val executeResult = Bits(32 bits)
  val destination = UInt(5 bits)
  val gprWrite = Bool()
  val isLoad = Bool()
  val mulDivOperation = Bits(4 bits)
  val memorySize = Bits(2 bits)
  val hasException = Bool()
  val isErtn = Bool()
  val csrResult = Bits(32 bits)
  val csrAddress = UInt(14 bits)
  val csrWrite = Bool()
  val exceptionCode = Bits(10 bits)
  val isLl = Bool()
  val isSc = Bool()
  val isStore = Bool()
  val tlbSearch = Bool()
  val tlbWrite = Bool()
  val tlbFill = Bool()
  val refetch = Bool()
  val tlbRead = Bool()
  val invalidateTlb = Bool()
  val invalidateTlbAsid = Bits(10 bits)
  val invalidateTlbVpn = Bits(19 bits)
  val memorySignExtend = Bool()
  val instructionCacheOperation = Bool()
  val isBranch = Bool()
  val instructionCacheMiss = Bool()
  val isPredictableBranch = Bool()
  val predictionError = Bool()
  val preload = Bool()
  val cacheOperation = Bool()
  val idle = Bool()
  val errorVirtualAddress = UInt(32 bits)
  val instruction = Bits(32 bits)
  val timer = Bits(64 bits)
  val isCounterInstruction = Bool()
  val loadEvent = Bits(8 bits)
  val memoryVirtualAddress = UInt(32 bits)
  val storeEvent = Bits(8 bits)
  val storeData = Bits(32 bits)
  val csrRstatEvent = Bool()
  val csrData = Bits(32 bits)

  def toLegacyBits: Bits = ExecutePayload.packLegacy(this)
}

object ExecutePayload {
  val LegacyWidth = 425
  val LegacyLayout: Vector[LegacyBitField] = Vector(
    LegacyBitField("pc", 31, 0),
    LegacyBitField("executeResult", 63, 32),
    LegacyBitField("destination", 68, 64),
    LegacyBitField("gprWrite", 69, 69),
    LegacyBitField("isLoad", 70, 70),
    LegacyBitField("mulDivOperation", 74, 71),
    LegacyBitField("memorySize", 76, 75),
    LegacyBitField("hasException", 77, 77),
    LegacyBitField("isErtn", 78, 78),
    LegacyBitField("csrResult", 110, 79),
    LegacyBitField("csrAddress", 124, 111),
    LegacyBitField("csrWrite", 125, 125),
    LegacyBitField("exceptionCode", 135, 126),
    LegacyBitField("isLl", 136, 136),
    LegacyBitField("isSc", 137, 137),
    LegacyBitField("isStore", 138, 138),
    LegacyBitField("tlbSearch", 139, 139),
    LegacyBitField("tlbWrite", 140, 140),
    LegacyBitField("tlbFill", 141, 141),
    LegacyBitField("refetch", 142, 142),
    LegacyBitField("tlbRead", 143, 143),
    LegacyBitField("invalidateTlb", 144, 144),
    LegacyBitField("invalidateTlbAsid", 154, 145),
    LegacyBitField("invalidateTlbVpn", 173, 155),
    LegacyBitField("memorySignExtend", 174, 174),
    LegacyBitField("instructionCacheOperation", 175, 175),
    LegacyBitField("isBranch", 176, 176),
    LegacyBitField("instructionCacheMiss", 177, 177),
    LegacyBitField("isPredictableBranch", 178, 178),
    LegacyBitField("predictionError", 179, 179),
    LegacyBitField("preload", 180, 180),
    LegacyBitField("cacheOperation", 181, 181),
    LegacyBitField("idle", 182, 182),
    LegacyBitField("errorVirtualAddress", 214, 183),
    LegacyBitField("instruction", 246, 215),
    LegacyBitField("timer", 310, 247),
    LegacyBitField("isCounterInstruction", 311, 311),
    LegacyBitField("loadEvent", 319, 312),
    LegacyBitField("memoryVirtualAddress", 351, 320),
    LegacyBitField("storeEvent", 359, 352),
    LegacyBitField("storeData", 391, 360),
    LegacyBitField("csrRstatEvent", 392, 392),
    LegacyBitField("csrData", 424, 393)
  )
  LegacyPayloadSupport.validate(LegacyWidth, LegacyLayout)

  def packLegacy(payload: ExecutePayload): Bits = LegacyPayloadSupport.packMostToLeast(
    payload.csrData,
    payload.csrRstatEvent,
    payload.storeData,
    payload.storeEvent,
    payload.memoryVirtualAddress,
    payload.loadEvent,
    payload.isCounterInstruction,
    payload.timer,
    payload.instruction,
    payload.errorVirtualAddress,
    payload.idle,
    payload.cacheOperation,
    payload.preload,
    payload.predictionError,
    payload.isPredictableBranch,
    payload.instructionCacheMiss,
    payload.isBranch,
    payload.instructionCacheOperation,
    payload.memorySignExtend,
    payload.invalidateTlbVpn,
    payload.invalidateTlbAsid,
    payload.invalidateTlb,
    payload.tlbRead,
    payload.refetch,
    payload.tlbFill,
    payload.tlbWrite,
    payload.tlbSearch,
    payload.isStore,
    payload.isSc,
    payload.isLl,
    payload.exceptionCode,
    payload.csrWrite,
    payload.csrAddress,
    payload.csrResult,
    payload.isErtn,
    payload.hasException,
    payload.memorySize,
    payload.mulDivOperation,
    payload.isLoad,
    payload.gprWrite,
    payload.destination,
    payload.executeResult,
    payload.pc
  )

  def unpackLegacy(bits: Bits): ExecutePayload = {
    LegacyPayloadSupport.requireWidth(bits, LegacyWidth)
    val payload = ExecutePayload()
    payload.pc := bits(31 downto 0).asUInt
    payload.executeResult := bits(63 downto 32)
    payload.destination := bits(68 downto 64).asUInt
    payload.gprWrite := bits(69)
    payload.isLoad := bits(70)
    payload.mulDivOperation := bits(74 downto 71)
    payload.memorySize := bits(76 downto 75)
    payload.hasException := bits(77)
    payload.isErtn := bits(78)
    payload.csrResult := bits(110 downto 79)
    payload.csrAddress := bits(124 downto 111).asUInt
    payload.csrWrite := bits(125)
    payload.exceptionCode := bits(135 downto 126)
    payload.isLl := bits(136)
    payload.isSc := bits(137)
    payload.isStore := bits(138)
    payload.tlbSearch := bits(139)
    payload.tlbWrite := bits(140)
    payload.tlbFill := bits(141)
    payload.refetch := bits(142)
    payload.tlbRead := bits(143)
    payload.invalidateTlb := bits(144)
    payload.invalidateTlbAsid := bits(154 downto 145)
    payload.invalidateTlbVpn := bits(173 downto 155)
    payload.memorySignExtend := bits(174)
    payload.instructionCacheOperation := bits(175)
    payload.isBranch := bits(176)
    payload.instructionCacheMiss := bits(177)
    payload.isPredictableBranch := bits(178)
    payload.predictionError := bits(179)
    payload.preload := bits(180)
    payload.cacheOperation := bits(181)
    payload.idle := bits(182)
    payload.errorVirtualAddress := bits(214 downto 183).asUInt
    payload.instruction := bits(246 downto 215)
    payload.timer := bits(310 downto 247)
    payload.isCounterInstruction := bits(311)
    payload.loadEvent := bits(319 downto 312)
    payload.memoryVirtualAddress := bits(351 downto 320).asUInt
    payload.storeEvent := bits(359 downto 352)
    payload.storeData := bits(391 downto 360)
    payload.csrRstatEvent := bits(392)
    payload.csrData := bits(424 downto 393)
    payload
  }
}

/** MEM-to-WB data in the exact 493-bit golden bus order. */
final case class MemoryPayload() extends Bundle {
  val pc = UInt(32 bits)
  val finalResult = Bits(32 bits)
  val destination = UInt(5 bits)
  val gprWrite = Bool()
  val hasException = Bool()
  val isErtn = Bool()
  val csrResult = Bits(32 bits)
  val csrAddress = UInt(14 bits)
  val csrWrite = Bool()
  val exceptionCode = Bits(16 bits)
  val isLl = Bool()
  val isSc = Bool()
  val errorVirtualAddress = UInt(32 bits)
  val tlbSearch = Bool()
  val tlbFound = Bool()
  val tlbIndex = UInt(5 bits)
  val tlbWrite = Bool()
  val tlbFill = Bool()
  val refetch = Bool()
  val tlbRead = Bool()
  val invalidateTlb = Bool()
  val invalidateTlbAsid = Bits(10 bits)
  val invalidateTlbVpn = Bits(19 bits)
  val instructionCacheOperation = Bool()
  val isBranch = Bool()
  val instructionCacheMiss = Bool()
  val accessesMemory = Bool()
  val dataCacheMiss = Bool()
  val isPredictableBranch = Bool()
  val predictionError = Bool()
  val idle = Bool()
  val physicalAddress = UInt(32 bits)
  val dataUncached = Bool()
  val instruction = Bits(32 bits)
  val timer = Bits(64 bits)
  val isCounterInstruction = Bool()
  val loadEvent = Bits(8 bits)
  val memoryPhysicalAddress = UInt(32 bits)
  val memoryVirtualAddress = UInt(32 bits)
  val storeEvent = Bits(8 bits)
  val storeData = Bits(32 bits)
  val csrRstatEvent = Bool()
  val csrData = Bits(32 bits)

  def toLegacyBits: Bits = MemoryPayload.packLegacy(this)
}

object MemoryPayload {
  val LegacyWidth = 493
  val LegacyLayout: Vector[LegacyBitField] = Vector(
    LegacyBitField("pc", 31, 0),
    LegacyBitField("finalResult", 63, 32),
    LegacyBitField("destination", 68, 64),
    LegacyBitField("gprWrite", 69, 69),
    LegacyBitField("hasException", 70, 70),
    LegacyBitField("isErtn", 71, 71),
    LegacyBitField("csrResult", 103, 72),
    LegacyBitField("csrAddress", 117, 104),
    LegacyBitField("csrWrite", 118, 118),
    LegacyBitField("exceptionCode", 134, 119),
    LegacyBitField("isLl", 135, 135),
    LegacyBitField("isSc", 136, 136),
    LegacyBitField("errorVirtualAddress", 168, 137),
    LegacyBitField("tlbSearch", 169, 169),
    LegacyBitField("tlbFound", 170, 170),
    LegacyBitField("tlbIndex", 175, 171),
    LegacyBitField("tlbWrite", 176, 176),
    LegacyBitField("tlbFill", 177, 177),
    LegacyBitField("refetch", 178, 178),
    LegacyBitField("tlbRead", 179, 179),
    LegacyBitField("invalidateTlb", 180, 180),
    LegacyBitField("invalidateTlbAsid", 190, 181),
    LegacyBitField("invalidateTlbVpn", 209, 191),
    LegacyBitField("instructionCacheOperation", 210, 210),
    LegacyBitField("isBranch", 211, 211),
    LegacyBitField("instructionCacheMiss", 212, 212),
    LegacyBitField("accessesMemory", 213, 213),
    LegacyBitField("dataCacheMiss", 214, 214),
    LegacyBitField("isPredictableBranch", 215, 215),
    LegacyBitField("predictionError", 216, 216),
    LegacyBitField("idle", 217, 217),
    LegacyBitField("physicalAddress", 249, 218),
    LegacyBitField("dataUncached", 250, 250),
    LegacyBitField("instruction", 282, 251),
    LegacyBitField("timer", 346, 283),
    LegacyBitField("isCounterInstruction", 347, 347),
    LegacyBitField("loadEvent", 355, 348),
    LegacyBitField("memoryPhysicalAddress", 387, 356),
    LegacyBitField("memoryVirtualAddress", 419, 388),
    LegacyBitField("storeEvent", 427, 420),
    LegacyBitField("storeData", 459, 428),
    LegacyBitField("csrRstatEvent", 460, 460),
    LegacyBitField("csrData", 492, 461)
  )
  LegacyPayloadSupport.validate(LegacyWidth, LegacyLayout)

  def packLegacy(payload: MemoryPayload): Bits = LegacyPayloadSupport.packMostToLeast(
    payload.csrData,
    payload.csrRstatEvent,
    payload.storeData,
    payload.storeEvent,
    payload.memoryVirtualAddress,
    payload.memoryPhysicalAddress,
    payload.loadEvent,
    payload.isCounterInstruction,
    payload.timer,
    payload.instruction,
    payload.dataUncached,
    payload.physicalAddress,
    payload.idle,
    payload.predictionError,
    payload.isPredictableBranch,
    payload.dataCacheMiss,
    payload.accessesMemory,
    payload.instructionCacheMiss,
    payload.isBranch,
    payload.instructionCacheOperation,
    payload.invalidateTlbVpn,
    payload.invalidateTlbAsid,
    payload.invalidateTlb,
    payload.tlbRead,
    payload.refetch,
    payload.tlbFill,
    payload.tlbWrite,
    payload.tlbIndex,
    payload.tlbFound,
    payload.tlbSearch,
    payload.errorVirtualAddress,
    payload.isSc,
    payload.isLl,
    payload.exceptionCode,
    payload.csrWrite,
    payload.csrAddress,
    payload.csrResult,
    payload.isErtn,
    payload.hasException,
    payload.gprWrite,
    payload.destination,
    payload.finalResult,
    payload.pc
  )

  def unpackLegacy(bits: Bits): MemoryPayload = {
    LegacyPayloadSupport.requireWidth(bits, LegacyWidth)
    val payload = MemoryPayload()
    payload.pc := bits(31 downto 0).asUInt
    payload.finalResult := bits(63 downto 32)
    payload.destination := bits(68 downto 64).asUInt
    payload.gprWrite := bits(69)
    payload.hasException := bits(70)
    payload.isErtn := bits(71)
    payload.csrResult := bits(103 downto 72)
    payload.csrAddress := bits(117 downto 104).asUInt
    payload.csrWrite := bits(118)
    payload.exceptionCode := bits(134 downto 119)
    payload.isLl := bits(135)
    payload.isSc := bits(136)
    payload.errorVirtualAddress := bits(168 downto 137).asUInt
    payload.tlbSearch := bits(169)
    payload.tlbFound := bits(170)
    payload.tlbIndex := bits(175 downto 171).asUInt
    payload.tlbWrite := bits(176)
    payload.tlbFill := bits(177)
    payload.refetch := bits(178)
    payload.tlbRead := bits(179)
    payload.invalidateTlb := bits(180)
    payload.invalidateTlbAsid := bits(190 downto 181)
    payload.invalidateTlbVpn := bits(209 downto 191)
    payload.instructionCacheOperation := bits(210)
    payload.isBranch := bits(211)
    payload.instructionCacheMiss := bits(212)
    payload.accessesMemory := bits(213)
    payload.dataCacheMiss := bits(214)
    payload.isPredictableBranch := bits(215)
    payload.predictionError := bits(216)
    payload.idle := bits(217)
    payload.physicalAddress := bits(249 downto 218).asUInt
    payload.dataUncached := bits(250)
    payload.instruction := bits(282 downto 251)
    payload.timer := bits(346 downto 283)
    payload.isCounterInstruction := bits(347)
    payload.loadEvent := bits(355 downto 348)
    payload.memoryPhysicalAddress := bits(387 downto 356).asUInt
    payload.memoryVirtualAddress := bits(419 downto 388).asUInt
    payload.storeEvent := bits(427 downto 420)
    payload.storeData := bits(459 downto 428)
    payload.csrRstatEvent := bits(460)
    payload.csrData := bits(492 downto 461)
    payload
  }
}

/** WB payload keeps the historical MEM-to-WB contents while exposing a stage-specific type. */
final case class WritebackPayload() extends Bundle {
  val memory = MemoryPayload()
}

object WritebackPayload {
  val LegacyWidth: Int = MemoryPayload.LegacyWidth

  def packLegacy(payload: WritebackPayload): Bits = payload.memory.toLegacyBits

  def unpackLegacy(bits: Bits): WritebackPayload = {
    val payload = WritebackPayload()
    payload.memory := MemoryPayload.unpackLegacy(bits)
    payload
  }
}
