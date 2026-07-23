package openla500.memory

import spinal.core._

/** Cycle-compatible implementation of `a158aa8:rtl/icache.v`.
  *
  * Inputs are the exact legacy request/refill contract. A request spends one cycle in lookup; cache
  * hits may accept the next request in that cycle, while misses serialize one AXI-side read. The
  * two-way tag and four-bank data memories are synchronous-read, unreset memories. Lookup, refill,
  * backpressure, cancellation and CACOP invalidation sequencing are preserved.
  */
final class OpenLa500ICache(
    setCount: Int = 256,
    scrubOnReset: Boolean = false,
    exposeLineResponse: Boolean = false
) extends Component {
  private val ExternalIndexWidth = 8
  private val ExternalTagWidth = 20
  private val WayCount = 2
  private val WordsPerLine = 4
  private val LineOffsetWidth = 4
  private val SetIndexWidth = log2Up(setCount)
  private val ExtraIndexWidth = SetIndexWidth - ExternalIndexWidth
  private val StoredTagWidth = ExternalTagWidth - ExtraIndexWidth

  require(setCount == 256 || setCount == 1024, "I-cache supports 256 or 1024 sets")

  private def physicalSet(tag: Bits, index: Bits): UInt =
    if (ExtraIndexWidth == 0) index.asUInt
    else (tag(ExtraIndexWidth - 1 downto 0) ## index).asUInt

  private def storedTag(tag: Bits): Bits =
    if (ExtraIndexWidth == 0) tag
    else tag(ExternalTagWidth - 1 downto ExtraIndexWidth)

  private def requestAddress(tag: Bits, set: UInt, offset: Bits): Bits =
    tag ## set(ExternalIndexWidth - 1 downto 0).asBits ## offset

  val io = new Bundle {
    val clk = in Bool ()
    val reset = in Bool ()

    val valid = in Bool ()
    val op = in Bool ()
    val index = in Bits (8 bits)
    val tag = in Bits (20 bits)
    val speculativeColor = (ExtraIndexWidth > 0) generate in(Bits(ExtraIndexWidth bits))
    val offset = in Bits (4 bits)
    val wstrb = in Bits (4 bits)
    val wdata = in Bits (32 bits)
    val addr_ok = out Bool ()
    val data_ok = out Bool ()
    val rdata = out Bits (32 bits)
    // The complete core can consume all four synchronous data banks at once. Standalone legacy
    // generation leaves these ports out, so the historical I-cache module contract stays exact.
    val line_valid = if (exposeLineResponse) out(Bool()) else null
    val line_data = if (exposeLineResponse) out(Bits(128 bits)) else null
    val uncache_en = in Bool ()
    val icacop_op_en = in Bool ()
    val cacop_op_mode = in Bits (2 bits)
    val cacop_op_addr_index = in Bits (8 bits)
    val cacop_op_addr_tag = in Bits (20 bits)
    val cacop_op_addr_offset = in Bits (4 bits)
    val icache_unbusy = out Bool ()
    val tlb_excp_cancel_req = in Bool ()

    val rd_req = out Bool ()
    val rd_type = out Bits (3 bits)
    val rd_addr = out Bits (32 bits)
    val rd_rdy = in Bool ()
    val ret_valid = in Bool ()
    val ret_last = in Bool ()
    val ret_data = in Bits (32 bits)
    val wr_req = out Bool ()
    val wr_type = out Bits (3 bits)
    val wr_addr = out Bits (32 bits)
    val wr_wstrb = out Bits (4 bits)
    val wr_data = out Bits (128 bits)
    val wr_rdy = in Bool ()

    val cache_miss = out Bool ()
  }

  noIoPrefix()

  private val cacheClockDomain = ClockDomain(
    clock = io.clk,
    reset = io.reset,
    config = ClockDomainConfig(
      clockEdge = RISING,
      resetKind = SYNC,
      resetActiveLevel = HIGH
    )
  )

  private val logic = new ClockingArea(cacheClockDomain) {
    val MainIdle = B"5'b00001"
    val MainLookup = B"5'b00010"
    val MainReplace = B"5'b01000"
    val MainRefill = B"5'b10000"

    val mainState = Reg(Bits(5 bits)) init (MainIdle)
    val requestSet = Reg(UInt(SetIndexWidth bits)) init (0)
    val requestTag = Reg(Bits(20 bits)) init (0)
    val requestOffset = Reg(Bits(4 bits)) init (0)
    val requestUncache = Reg(Bool()) init (False)
    val requestCacop = Reg(Bool()) init (False)
    val requestCacopMode = Reg(Bits(2 bits)) init (0)
    val setReplayPending =
      if (ExtraIndexWidth > 0) Some(Reg(Bool()) init (False))
      else None

    def clearSetReplay(): Unit = setReplayPending.foreach(_ := False)
    def markSetReplay(): Unit = setReplayPending.foreach(_ := True)

    val missReplaceWay = Reg(Bits(2 bits)) init (0)
    val missRetNum = Reg(UInt(2 bits))
    val lookupWayHitBuffer = Reg(Bits(2 bits)) init (0)
    val rdReqBuffer = Reg(Bool()) init (False)
    val lfsr = Reg(Bits(8 bits)) init (B"8'b00000001")
    val legacyWrReq = Reg(Bool()) init (False)

    val dataMem = Array.fill(WayCount, WordsPerLine)(Mem(Bits(32 bits), setCount))
    val tagMem = Array.fill(WayCount)(Mem(Bits(StoredTagWidth + 1 bits), setCount))

    // 活动 profile 与 D-cache 并行 scrub tag-valid；standalone oracle 保留历史未复位 SRAM。
    val scrubActive: Bool =
      if (scrubOnReset) Reg(Bool()) init (True)
      else False
    val scrubIndex: UInt =
      if (scrubOnReset) Reg(UInt(SetIndexWidth bits)) init (0)
      else U(0, SetIndexWidth bits)
    if (scrubOnReset) {
      when(scrubActive) {
        when(scrubIndex === U(setCount - 1, SetIndexWidth bits)) {
          scrubActive := False
        } otherwise {
          scrubIndex := scrubIndex + 1
        }
      }
    }

    val isIdle = mainState === MainIdle
    val isLookup = mainState === MainLookup
    val isReplace = mainState === MainReplace
    val isRefill = mainState === MainRefill

    val realOffset = Mux(io.icacop_op_en, io.cacop_op_addr_offset, io.offset)
    val requestValid = io.valid || io.icacop_op_en

    val mode0 = requestCacop && requestCacopMode === B"2'b00"
    val mode1 = requestCacop && (requestCacopMode === B"2'b01" || requestCacopMode === B"2'b11")
    val mode2 = requestCacop && requestCacopMode === B"2'b10"
    val mode2HitWrite = mode2 && lookupWayHitBuffer.orR

    // 与 D-cache 相同：先以当前虚拟页颜色探测 SRAM，下一拍用物理 tag 低位核验。
    val speculativeSet =
      if (ExtraIndexWidth == 0) physicalSet(io.tag, io.index)
      else (io.speculativeColor ## io.index).asUInt
    val cacopSet = physicalSet(io.cacop_op_addr_tag, io.cacop_op_addr_index)
    val initialSet = Mux(io.icacop_op_en, cacopSet, speculativeSet)
    // Address translation captures the accepted virtual address on the same edge as this cache.
    // Its physical tag therefore belongs to the lookup cycle, not the request-accept cycle.
    val lookupRequestTag = io.tag
    val lookupRequestUncache = io.uncache_en
    val translatedSet = physicalSet(
      lookupRequestTag,
      requestSet(ExternalIndexWidth - 1 downto 0).asBits
    )
    val effectiveLookupTag = Bits(ExternalTagWidth bits)
    effectiveLookupTag := Mux(requestCacop, io.cacop_op_addr_tag, io.tag)
    if (ExtraIndexWidth > 0) {
      when(setReplayPending.get) {
        effectiveLookupTag := requestTag
      }
    }
    val physicalColorMismatch =
      if (ExtraIndexWidth > 0) {
        isLookup && !setReplayPending.get && !requestCacop &&
        requestSet(SetIndexWidth - 1 downto ExternalIndexWidth).asBits =/=
          lookupRequestTag(ExtraIndexWidth - 1 downto 0) && !lookupRequestUncache
      } else False
    val replaySet = Mux(physicalColorMismatch, translatedSet, requestSet)
    // CACOP is intentionally excluded from addr_ok, but its accept cycle still has to launch the
    // synchronous tag lookup. Otherwise a mode2 operation compares the previous fetch set and can
    // silently leave self-modifying code resident in the enlarged cache.
    val readCurrentRequest =
      io.addr_ok || (io.icacop_op_en && (isIdle || isLookup))
    val pipelineReadSet = Mux(readCurrentRequest, initialSet, replaySet)
    val tagReadWriteSet = Mux(scrubActive, scrubIndex, pipelineReadSet)

    val tagOutputs = Vec(Bits(StoredTagWidth + 1 bits), WayCount)
    val dataOutputs = Array.fill(WayCount)(Vec(Bits(32 bits), WordsPerLine))

    val wayHit = Bits(WayCount bits)
    val tagEnabled = scrubActive || !requestUncache || isIdle || isLookup
    val dataEnabled = !scrubActive && (!(requestUncache || mode0) || isIdle || isLookup)
    for (way <- 0 until WayCount) {
      val normalTagWrite =
        missReplaceWay(way) && isRefill &&
          ((io.ret_valid && io.ret_last) || mode0 || mode1 || mode2HitWrite)
      val tagWriteNow = scrubActive || normalTagWrite
      val invalidate = mode0 || mode1 || mode2HitWrite
      val normalTagData = Mux(
        invalidate,
        B(0, StoredTagWidth + 1 bits),
        storedTag(requestTag) ## True
      )
      tagOutputs(way) := tagMem(way).readWriteSync(
        address = tagReadWriteSet,
        data = Mux(scrubActive, B(0, StoredTagWidth + 1 bits), normalTagData),
        enable = tagEnabled,
        write = tagWriteNow,
        duringWrite = dontRead
      )
      wayHit(way) :=
        tagOutputs(way)(0) &&
          tagOutputs(way)(StoredTagWidth downto 1) === storedTag(effectiveLookupTag)

      for (bank <- 0 until WordsPerLine) {
        val refillWrite =
          isRefill && missReplaceWay(way) && io.ret_valid && missRetNum === U(bank, 2 bits)
        // The instruction RAM has no byte stores.  Keep the read and refill
        // write explicit so Spinal does not emit an unused byte-mask port.
        dataOutputs(way)(bank) := dataMem(way)(bank).readSync(
          address = pipelineReadSet,
          enable = dataEnabled
        )
        dataMem(way)(bank).write(
          address = pipelineReadSet,
          data = io.ret_data,
          enable = dataEnabled && refillWrite
        )
      }
    }
    // CACOP follows the locked passing d22c13c state path: it must not be
    // treated as a normal lookup hit, even when the indexed line is valid.
    val cacheHit =
      wayHit.orR && !(lookupRequestUncache || mode0 || mode1 || mode2) &&
        !physicalColorMismatch
    val addrOk =
      !scrubActive && (isIdle || (isLookup && cacheHit)) && !io.icacop_op_en

    val wayWords = Vec(Bits(32 bits), 2)
    for (way <- 0 until WayCount) {
      wayWords(way) := dataOutputs(way)(requestOffset(3 downto 2).asUInt)
    }
    val loadResult =
      Mux(wayHit(0), wayWords(0), B(0, 32 bits)) |
        Mux(wayHit(1), wayWords(1), B(0, 32 bits))

    val lineValid = if (exposeLineResponse) Bool() else null
    val lineData = if (exposeLineResponse) Bits(128 bits) else null
    if (exposeLineResponse) {
      val refillWords = Vec.fill(WordsPerLine)(Reg(Bits(32 bits)) init (0))
      val selectedHitWords = Vec(Bits(32 bits), WordsPerLine)
      val completedRefillWords = Vec(Bits(32 bits), WordsPerLine)
      for (bank <- 0 until WordsPerLine) {
        selectedHitWords(bank) :=
          Mux(wayHit(0), dataOutputs(0)(bank), B(0, 32 bits)) |
            Mux(wayHit(1), dataOutputs(1)(bank), B(0, 32 bits))
        completedRefillWords(bank) := Mux(
          io.ret_valid && missRetNum === U(bank, 2 bits),
          io.ret_data,
          refillWords(bank)
        )
        when(isRefill && io.ret_valid && missRetNum === U(bank, 2 bits)) {
          refillWords(bank) := io.ret_data
        }
      }

      val hitLine = selectedHitWords.reverse.reduce(_ ## _)
      val refillLine = completedRefillWords.reverse.reduce(_ ## _)
      lineValid :=
        (isLookup && cacheHit) ||
          (isRefill && io.ret_valid && io.ret_last && !requestUncache && !requestCacop)
      lineData := Mux(isLookup, hitLine, refillLine)
    }

    val invalidWay = Bits(2 bits)
    invalidWay := B"2'b00"
    when(!tagOutputs(0)(0)) {
      invalidWay := B"2'b01"
    }.elsewhen(!tagOutputs(1)(0)) {
      invalidWay := B"2'b10"
    }
    val hasInvalidWay = invalidWay.orR
    val randomWay = Mux(lfsr(6), B"2'b10", B"2'b01")
    val randomReplacement = Mux(hasInvalidWay, invalidWay, randomWay)
    val cacopChosenWay = Mux(requestOffset(0), B"2'b10", B"2'b01")
    val replaceWay = Bits(2 bits)
    replaceWay := B"2'b00"
    when(mode0 || mode1) {
      replaceWay := cacopChosenWay
    }.elsewhen(mode2) {
      replaceWay := wayHit
    }.elsewhen(!requestCacop) {
      replaceWay := randomReplacement
    }

    val rdReq = isReplace && !(mode0 || mode1 || mode2)
    // A wide frontend consumes one cacheable miss only after all four words are assembled. Keep
    // the legacy critical-word response for the scalar profile and every uncached transaction.
    val refillProducesScalar =
      if (exposeLineResponse) requestUncache
      else {
        val refillMatch = missRetNum === requestOffset(3 downto 2).asUInt
        refillMatch || requestUncache
      }
    val dataOk =
      ((isLookup && (cacheHit || io.tlb_excp_cancel_req)) ||
        (isRefill && io.ret_valid && refillProducesScalar && !requestCacop)) &&
        !physicalColorMismatch

    // The legacy source increments this exact two-bit binary counter.
    val nextRetNum = (missRetNum + U(1, 2 bits)).resized

    private def captureRequest(): Unit = {
      requestSet := initialSet
      requestOffset := realOffset
      requestCacopMode := io.cacop_op_mode
      requestCacop := io.icacop_op_en
      clearSetReplay()
    }

    switch(mainState) {
      is(MainIdle) {
        when(!scrubActive && requestValid) {
          mainState := MainLookup
          captureRequest()
        }
      }
      is(MainLookup) {
        when(requestValid && cacheHit) {
          mainState := MainLookup
          captureRequest()
        }.elsewhen(io.tlb_excp_cancel_req) {
          mainState := MainIdle
          clearSetReplay()
        }.elsewhen(physicalColorMismatch) {
          requestSet := translatedSet
          requestTag := lookupRequestTag
          markSetReplay()
        }.elsewhen(!cacheHit) {
          mainState := MainReplace
          requestTag := effectiveLookupTag
          requestUncache := lookupRequestUncache && !requestCacop
          missReplaceWay := replaceWay
          clearSetReplay()
        }.otherwise {
          mainState := MainIdle
          clearSetReplay()
        }
      }
      is(MainReplace) {
        when(io.rd_rdy) {
          mainState := MainRefill
          missRetNum := 0
        }
      }
      is(MainRefill) {
        when((io.ret_valid && io.ret_last) || !rdReqBuffer) {
          mainState := MainIdle
          clearSetReplay()
        }.elsewhen(io.ret_valid) {
          missRetNum := nextRetNum
        }
      }
      default {
        mainState := MainIdle
      }
    }

    when(mode2 && isLookup) {
      lookupWayHitBuffer := wayHit
    }

    when(rdReq) {
      rdReqBuffer := True
    }.elsewhen(isRefill && io.ret_valid && io.ret_last) {
      rdReqBuffer := False
    }

    when(!scrubActive) {
      lfsr(0) := lfsr(7)
      lfsr(1) := lfsr(0)
      lfsr(2) := lfsr(1)
      lfsr(3) := lfsr(2)
      lfsr(4) := lfsr(3) ^ lfsr(7)
      lfsr(5) := lfsr(4) ^ lfsr(7)
      lfsr(6) := lfsr(5) ^ lfsr(7)
      lfsr(7) := lfsr(6)
    }

    // Golden only assigns this register in reset; the other write outputs are undriven.
    legacyWrReq := legacyWrReq
  }

  io.addr_ok := logic.addrOk
  io.data_ok := logic.dataOk
  io.rdata := Mux(
    logic.isLookup,
    logic.loadResult,
    Mux(logic.isRefill, io.ret_data, B(0, 32 bits))
  )
  if (exposeLineResponse) {
    io.line_valid := logic.lineValid
    io.line_data := logic.lineData
  }
  io.icache_unbusy := logic.isIdle && !logic.scrubActive
  io.rd_req := logic.rdReq
  io.rd_type := Mux(logic.requestUncache, B"3'b010", B"3'b100")
  io.rd_addr := Mux(
    logic.requestUncache,
    requestAddress(logic.requestTag, logic.requestSet, logic.requestOffset),
    requestAddress(logic.requestTag, logic.requestSet, B(0, LineOffsetWidth bits))
  )
  io.wr_req := logic.legacyWrReq
  io.wr_type := B"3'b000"
  io.wr_addr := B(0, 32 bits)
  io.wr_wstrb := B"4'b0000"
  io.wr_data := B(0, 128 bits)
  io.cache_miss :=
    logic.isRefill && io.ret_last && !(logic.requestUncache || logic.requestCacop)
}
