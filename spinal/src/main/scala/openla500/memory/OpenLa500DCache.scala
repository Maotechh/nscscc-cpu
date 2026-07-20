package openla500.memory

import spinal.core._

/** Cycle-oriented replacement for the active a158aa8 dcache boundary.
  *
  * The external contract intentionally remains the legacy 35-port interface. The request,
  * write-back and refill state machines retain the old ordering: lookup, optional dirty write-back,
  * refill, and delayed hit-store write buffer.
  */
final class OpenLa500DCache(
    setCount: Int = 256,
    scrubOnReset: Boolean = false,
    goldenCacopBypass: Boolean = false
) extends Component {
  private val ExternalIndexWidth = 8
  private val ExternalTagWidth = 20
  private val WayCount = 2
  private val WordsPerLine = 4
  private val LineOffsetWidth = 4
  private val SetIndexWidth = log2Up(setCount)
  private val ExtraIndexWidth = SetIndexWidth - ExternalIndexWidth
  private val StoredTagWidth = ExternalTagWidth - ExtraIndexWidth

  require(setCount == 256 || setCount == 1024, "D-cache supports 256 or 1024 sets")
  require(ExtraIndexWidth >= 0, "D-cache cannot use fewer than 256 sets")
  require(
    !goldenCacopBypass || (setCount == 256 && !scrubOnReset),
    "golden CACOP bypass is restricted to the standalone 256-set oracle profile"
  )

  private def physicalSet(tag: Bits, index: Bits): UInt =
    if (ExtraIndexWidth == 0) index.asUInt
    else (tag(ExtraIndexWidth - 1 downto 0) ## index).asUInt

  private def storedTag(tag: Bits): Bits =
    if (ExtraIndexWidth == 0) tag
    else tag(ExternalTagWidth - 1 downto ExtraIndexWidth)

  private def requestAddress(tag: Bits, set: UInt, offset: Bits): Bits =
    tag ## set(ExternalIndexWidth - 1 downto 0).asBits ## offset

  private def replacementLineAddress(tag: Bits, set: UInt): Bits =
    tag ## set.asBits ## B(0, LineOffsetWidth bits)

  val io = new Bundle {
    val clk = in Bool ()
    val reset = in Bool ()
    val valid = in Bool ()
    val op = in Bool ()
    val size = in Bits (3 bits)
    val index = in Bits (ExternalIndexWidth bits)
    val tag = in Bits (ExternalTagWidth bits)
    val speculativeColor = (ExtraIndexWidth > 0) generate in(Bits(ExtraIndexWidth bits))
    val offset = in Bits (4 bits)
    val wstrb = in Bits (4 bits)
    val wdata = in Bits (32 bits)
    val addr_ok = out Bool ()
    val data_ok = out Bool ()
    val rdata = out Bits (32 bits)
    val uncache_en = in Bool ()
    val dcacop_op_en = in Bool ()
    val cacop_op_mode = in Bits (2 bits)
    val preld_hint = in Bits (5 bits)
    val preld_en = in Bool ()
    val tlb_excp_cancel_req = in Bool ()
    val sc_cancel_req = in Bool ()
    val dcache_empty = out Bool ()
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
    config = ClockDomainConfig(clockEdge = RISING, resetKind = SYNC, resetActiveLevel = HIGH)
  )

  private val logic = new ClockingArea(cacheClockDomain) {
    val MainIdle = B"5'b00001"
    val MainLookup = B"5'b00010"
    val MainMiss = B"5'b00100"
    val MainReplace = B"5'b01000"
    val MainRefill = B"5'b10000"
    val mainState = Reg(Bits(5 bits)) init (MainIdle)

    val requestOp = Reg(Bool()) init (False)
    val requestPreld = Reg(Bool()) init (False)
    val requestSize = Reg(Bits(3 bits)) init (0)
    val requestSet = Reg(UInt(SetIndexWidth bits)) init (0)
    val requestTag = Reg(Bits(ExternalTagWidth bits))
    val requestOffset = Reg(Bits(4 bits)) init (0)
    val requestWstrb = Reg(Bits(4 bits)) init (0)
    val requestWdata = Reg(Bits(32 bits)) init (0)
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
    val rdReqBuffer = Reg(Bool()) init (False)
    val lfsr = Reg(Bits(8 bits)) init (B"8'b00000001")
    val legacyWrReq = Reg(Bool()) init (False)

    val writeBufferState = Reg(Bool()) init (False)
    val writeBufferSet = Reg(UInt(SetIndexWidth bits)) init (0)
    val writeBufferWstrb = Reg(Bits(4 bits)) init (0)
    val writeBufferWdata = Reg(Bits(32 bits)) init (0)
    val writeBufferWay = Reg(Bits(2 bits)) init (0)
    val writeBufferWord = Reg(UInt(2 bits)) init (0)

    val uncacheWrBuffer = Reg(Bool())
    val cacopMode2HitWrBuffer = Reg(Bool())

    val dataMem = Array.fill(WayCount, WordsPerLine)(Mem(Bits(32 bits), setCount))
    val tagMem = Array.fill(WayCount)(Mem(Bits(StoredTagWidth + 1 bits), setCount))
    val dirtyMem = Vec.fill(setCount)(Reg(Bits(2 bits)))

    // 活动核心必须先逐组清除 tag-valid/dirty，再开放请求；叶级 golden profile 不生成 scrub 状态。
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
    val writeBufferFull = writeBufferState
    val cancelReq = io.tlb_excp_cancel_req || io.sc_cancel_req

    val requestValid = io.valid || io.dcacop_op_en || io.preld_en
    val sameWord = writeBufferWord === io.offset(3 downto 2).asUInt
    val idleToLookup = !writeBufferFull || !(sameWord || io.dcacop_op_en)
    val mode0 = requestCacop && requestCacopMode === B"2'b00"
    val mode1 = requestCacop && (requestCacopMode === B"2'b01" || requestCacopMode === B"2'b11")
    val mode2 = requestCacop && requestCacopMode === B"2'b10"

    val writeIn = Bits(32 bits)
    for (byte <- 0 until 4) {
      val hi = byte * 8 + 7
      val lo = byte * 8
      writeIn(hi downto lo) := Mux(
        requestWstrb(byte),
        requestWdata(hi downto lo),
        io.ret_data(hi downto lo)
      )
    }
    val refillData = Mux(
      requestOp && requestOffset(3 downto 2).asUInt === missRetNum,
      writeIn,
      io.ret_data
    )

    // data_index 和虚拟页号属于当前 EX 请求，而物理 data_tag 要到下一拍才由地址翻译给出。
    // 先用虚拟页颜色预测 set；若翻译后的物理颜色不一致，只重放 SRAM 读，不产生副作用。
    val speculativeSet =
      if (ExtraIndexWidth == 0) physicalSet(io.tag, io.index)
      else (io.speculativeColor ## io.index).asUInt
    val translatedSet = physicalSet(
      io.tag,
      requestSet(ExternalIndexWidth - 1 downto 0).asBits
    )
    val effectiveLookupTag = Bits(ExternalTagWidth bits)
    effectiveLookupTag := io.tag
    if (ExtraIndexWidth > 0) {
      when(setReplayPending.get) {
        effectiveLookupTag := requestTag
      }
    }
    val physicalColorMismatch =
      if (ExtraIndexWidth > 0) {
        isLookup && !setReplayPending.get &&
        requestSet(SetIndexWidth - 1 downto ExternalIndexWidth).asBits =/=
          io.tag(ExtraIndexWidth - 1 downto 0) &&
          !(io.uncache_en && !requestCacop)
      } else False
    val replaySet = Mux(physicalColorMismatch, translatedSet, requestSet)
    val pipelineReadSet = Mux(io.addr_ok, speculativeSet, replaySet)
    val tagReadWriteSet = Mux(scrubActive, scrubIndex, pipelineReadSet)
    val invalidateTag = mode0 || mode1 || cacopMode2HitWrBuffer
    val zeroTag = B(0, StoredTagWidth + 1 bits)
    val normalTagWriteData = Mux(invalidateTag, zeroTag, storedTag(requestTag) ## True)
    val tagWriteData = Mux(scrubActive, zeroTag, normalTagWriteData)
    val tagEnabled = scrubActive || !requestUncache || isIdle || isLookup
    val dataEnabled = !scrubActive && (!(requestUncache || mode0) || isIdle || isLookup)

    val tagOutputs = Vec(Bits(StoredTagWidth + 1 bits), WayCount)
    val dataOutputs = Array.fill(WayCount)(Vec(Bits(32 bits), WordsPerLine))
    val realHit = Bits(WayCount bits)
    val cacheHit = Bool()
    val loadResult = Bits(32 bits)

    // tag SRAM 的写优先级为 scrub > 失效/CACOP > refill；data SRAM 不参与 scrub。
    for (way <- 0 until WayCount) {
      val normalTagWrite = isRefill && missReplaceWay(way) &&
        ((io.ret_valid && io.ret_last) || mode0 || mode1 || cacopMode2HitWrBuffer)
      val tagWriteNow = scrubActive || normalTagWrite
      tagOutputs(way) := tagMem(way).readWriteSync(
        address = tagReadWriteSet,
        data = tagWriteData,
        enable = tagEnabled,
        write = tagWriteNow,
        duringWrite = dontRead
      )
      realHit(way) :=
        tagOutputs(way)(0) &&
          tagOutputs(way)(StoredTagWidth downto 1) === storedTag(effectiveLookupTag)
      for (bank <- 0 until WordsPerLine) {
        val hitStoreNow =
          writeBufferFull && writeBufferWay(way) &&
            writeBufferWord === U(bank, 2 bits)
        val refillWriteNow =
          isRefill && missReplaceWay(way) && io.ret_valid && missRetNum === U(bank, 2 bits)
        val writeNow = hitStoreNow || refillWriteNow
        // hit-store 与 refill 同拍命中同一 bank 时沿用 golden 优先级：store 数据优先，但写满四字节。
        val writeMask = Mux(refillWriteNow, B"4'b1111", writeBufferWstrb)
        val writeAddress = Mux(hitStoreNow, writeBufferSet, pipelineReadSet)
        val writeData = Mux(hitStoreNow, writeBufferWdata, refillData)
        dataOutputs(way)(bank) := dataMem(way)(bank).readWriteSync(
          address = writeAddress,
          data = writeData,
          enable = dataEnabled,
          write = writeNow,
          mask = writeMask,
          duringWrite = dontRead
        )
      }
    }
    // 叶级 oracle 保留 a158aa8 的 CACOP 即时完成语义；活动核心沿用已通过板测的 d22c13c 路径。
    val cacopBlocksHit = if (goldenCacopBypass) False else mode0 || mode1 || mode2
    cacheHit :=
      realHit.orR && !io.uncache_en && !physicalColorMismatch && !cacopBlocksHit
    loadResult :=
      (Mux(realHit(0), dataOutputs(0)(requestOffset(3 downto 2).asUInt), B(0, 32 bits)) |
        Mux(realHit(1), dataOutputs(1)(requestOffset(3 downto 2).asUInt), B(0, 32 bits)))

    val cacopChosenWay = Mux(requestOffset(0), B"2'b10", B"2'b01")
    val invalidWay = Mux(
      !tagOutputs(0)(0),
      B"2'b01",
      Mux(!tagOutputs(1)(0), B"2'b10", B"2'b00")
    )
    val randomWay = Mux(lfsr(6), B"2'b10", B"2'b01")
    val normalReplacementWay = Mux(invalidWay.orR, invalidWay, randomWay)
    val replacementWay = Mux(
      mode0 || mode1,
      cacopChosenWay,
      Mux(mode2, realHit, normalReplacementWay)
    )

    val dirtyAtIndex = dirtyMem(requestSet)
    val effectiveDirty = dirtyAtIndex | Mux(
      writeBufferFull && writeBufferSet === requestSet,
      writeBufferWay,
      B(0, 2 bits)
    )
    val replacementDirty = (replacementWay & effectiveDirty).orR
    val validWays = Bits(2 bits)
    validWays(0) := tagOutputs(0)(0)
    validWays(1) := tagOutputs(1)(0)
    val replacementValid = (replacementWay & validWays).orR
    val lookupWriteConflict =
      writeBufferFull &&
        (writeBufferWord === io.offset(3 downto 2).asUInt || io.dcacop_op_en)
    val consecutiveStoreLoadConflict =
      requestOp && !io.op &&
        (requestOffset(3 downto 2) === io.offset(3 downto 2) || io.dcacop_op_en)
    val lookupToLookup = !lookupWriteConflict && !consecutiveStoreLoadConflict && cacheHit
    val addrOk = !scrubActive && ((isIdle && idleToLookup) || (isLookup && lookupToLookup))

    val uncacheRequest = io.uncache_en && !requestCacop
    val cacopMode2Hit = mode2 && realHit.orR
    val uncacheWrite = uncacheRequest && requestOp && !mode1 && !cacopMode2Hit
    val rdReq = isReplace && !(uncacheWrBuffer || mode0 || mode1 || mode2)
    val refillMatch = missRetNum === requestOffset(3 downto 2).asUInt
    val cacopCompletesLookup = if (goldenCacopBypass) requestCacop else False
    val cacopBlocksResponse = if (goldenCacopBypass) False else requestCacop
    val lookupCompletes = isLookup && (cacheHit || requestOp || cancelReq || cacopCompletesLookup)
    val refillCompletes =
      isRefill && !requestOp && io.ret_valid && (refillMatch || requestUncache)
    val dataOk =
      (lookupCompletes || refillCompletes) &&
        !(requestPreld || cacopBlocksResponse || physicalColorMismatch)

    val replaceTag = Mux(
      missReplaceWay(0),
      tagOutputs(0)(StoredTagWidth downto 1),
      Mux(
        missReplaceWay(1),
        tagOutputs(1)(StoredTagWidth downto 1),
        B(0, StoredTagWidth bits)
      )
    )
    val way0Line =
      dataOutputs(0)(3) ## dataOutputs(0)(2) ## dataOutputs(0)(1) ## dataOutputs(0)(0)
    val way1Line =
      dataOutputs(1)(3) ## dataOutputs(1)(2) ## dataOutputs(1)(1) ## dataOutputs(1)(0)
    val replaceData = Mux(
      missReplaceWay(0),
      way0Line,
      Mux(missReplaceWay(1), way1Line, B(0, 128 bits))
    )

    def captureRequest(): Unit = {
      requestOp := io.op
      requestPreld := io.preld_en
      requestSize := io.size
      requestSet := speculativeSet
      requestOffset := io.offset
      requestWstrb := io.wstrb
      requestWdata := io.wdata
      requestCacopMode := io.cacop_op_mode
      requestCacop := io.dcacop_op_en
      clearSetReplay()
    }

    val bypassCacop = if (goldenCacopBypass) requestCacop else False

    switch(mainState) {
      is(MainIdle) {
        when(!scrubActive && requestValid && idleToLookup) {
          mainState := MainLookup
          captureRequest()
        }
      }
      is(MainLookup) {
        when(requestValid && lookupToLookup) {
          mainState := MainLookup
          captureRequest()
        }.elsewhen(cancelReq) {
          mainState := MainIdle
          clearSetReplay()
        }.elsewhen(physicalColorMismatch) {
          requestSet := translatedSet
          requestTag := io.tag
          markSetReplay()
        }.elsewhen(bypassCacop) {
          mainState := MainIdle
          clearSetReplay()
        }.elsewhen(!cacheHit) {
          when(
            uncacheWrite ||
              (replacementDirty && replacementValid && (!uncacheRequest || cacopMode2Hit) && !mode0)
          ) { mainState := MainMiss }
            .otherwise { mainState := MainReplace }
          requestTag := effectiveLookupTag
          requestUncache := uncacheRequest
          uncacheWrBuffer := uncacheWrite
          missReplaceWay := replacementWay
          cacopMode2HitWrBuffer := cacopMode2Hit
          clearSetReplay()
        }.otherwise {
          mainState := MainIdle
          clearSetReplay()
        }
      }
      is(MainMiss) {
        when(io.wr_rdy) { mainState := MainReplace; legacyWrReq := True }
      }
      is(MainReplace) {
        when(io.rd_rdy) { mainState := MainRefill; missRetNum := 0 }
        legacyWrReq := False
      }
      is(MainRefill) {
        when((io.ret_valid && io.ret_last) || !rdReqBuffer) {
          mainState := MainIdle
        }.elsewhen(io.ret_valid) {
          missRetNum := missRetNum + U(1, 2 bits)
        }
      }
      default { mainState := MainIdle }
    }

    when(rdReq) { rdReqBuffer := True }
      .elsewhen(isRefill && io.ret_valid && io.ret_last) { rdReqBuffer := False }

    when(scrubActive) {
      dirtyMem(scrubIndex) := B(0, 2 bits)
    }.elsewhen(
      isRefill && ((io.ret_valid && io.ret_last) || !rdReqBuffer) && !(requestUncache || mode0)
    ) {
      for (way <- 0 until WayCount) {
        when(missReplaceWay(way)) { dirtyMem(requestSet)(way) := requestOp }
      }
    }.elsewhen(writeBufferFull) {
      dirtyMem(writeBufferSet) := dirtyMem(writeBufferSet) | writeBufferWay
    }

    when(isLookup && cacheHit && requestOp && !cancelReq) {
      writeBufferState := True
      writeBufferSet := requestSet
      writeBufferWstrb := requestWstrb
      writeBufferWdata := requestWdata
      writeBufferWord := requestOffset(3 downto 2).asUInt
      writeBufferWay := realHit
    }.otherwise {
      writeBufferState := False
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

    io.addr_ok := addrOk
    io.data_ok := dataOk
    io.rdata := Mux(isLookup, loadResult, Mux(isRefill, io.ret_data, B(0, 32 bits)))
    io.dcache_empty := isIdle && !scrubActive
    io.rd_req := rdReq
    io.rd_type := Mux(requestUncache, requestSize, B"3'b100")
    val requestByteAddress = requestAddress(requestTag, requestSet, requestOffset)
    val requestLineAddress =
      requestAddress(requestTag, requestSet, B(0, LineOffsetWidth bits))
    io.rd_addr := Mux(
      requestUncache,
      requestByteAddress,
      requestLineAddress
    )
    io.wr_req := legacyWrReq
    io.wr_type := Mux(uncacheWrBuffer, requestSize, B"3'b100")
    io.wr_addr := Mux(
      uncacheWrBuffer,
      requestByteAddress,
      replacementLineAddress(replaceTag, requestSet)
    )
    io.wr_wstrb := Mux(uncacheWrBuffer, requestWstrb, B"4'hf")
    io.wr_data := Mux(uncacheWrBuffer, B(0, 96 bits) ## requestWdata, replaceData)
    io.cache_miss := isRefill && io.ret_last && !(requestUncache || requestCacop || requestPreld)
  }
}
