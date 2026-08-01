package openla500.predict

import openla500.core._
import spinal.core._

object OooPredictedBranchType {
  val Width = 3
  def conditional: UInt = U(0, Width bits)
  def direct: UInt = U(1, Width bits)
  def indirect: UInt = U(2, Width bits)
  def ret: UInt = U(3, Width bits)
  def call: UInt = U(4, Width bits)
}

final case class OooBankedFetchPrediction(config: OooCoreConfig) extends Bundle {
  val hit = Bool()
  val phtValid = Bool()
  val branchType = UInt(OooPredictedBranchType.Width bits)
  val phtState = UInt(2 bits)
  val phtIndex = UInt(10 bits)
  val target = UInt(config.xlen bits)
  val fallbackTaken = Bool()
}

/** Four-bank synchronous BTB/PHT with speculative and architectural history state.
  *
  * A 16-byte group reads all lane banks in parallel. BTB and PHT arrays are cleared through their
  * write ports after reset, preserving block-RAM inference. Speculative GHR/RAS state advances when
  * a predicted group enters L1I and is restored from architectural state on a precise redirect.
  */
final class OooBankedFetchPredictor(
    config: OooCoreConfig = OooCoreConfig.FourIssueThreeCommit,
    btbEntriesPerBank: Int = 128,
    phtEntriesPerBank: Int = 1024,
    historyWidth: Int = 8,
    rasDepth: Int = 8
) extends Component {
  private val fetchGroupOffsetWidth = log2Up(config.fetchWidth * 4)
  private val bankWidth = log2Up(config.fetchWidth)
  private val btbRowWidth = log2Up(btbEntriesPerBank)
  private val phtRowWidth = log2Up(phtEntriesPerBank)
  private val btbTagWidth = config.xlen - fetchGroupOffsetWidth - btbRowWidth
  private val rasIndexWidth = log2Up(rasDepth)
  private val rasCountWidth = log2Up(rasDepth + 1)

  private val btbTargetLsb = 0
  private val btbTypeLsb = config.xlen
  private val btbTagLsb = btbTypeLsb + OooPredictedBranchType.Width
  private val btbValidBit = btbTagLsb + btbTagWidth
  private val btbDirectionTrainedBit = btbValidBit + 1
  private val btbEntryWidth = btbDirectionTrainedBit + 1

  require(config.fetchWidth == 4)
  require(btbEntriesPerBank == 128)
  require(phtEntriesPerBank == 1024)
  require(historyWidth == 8)
  require(rasDepth == 8)

  val io = new Bundle {
    val lookupValid = in Bool ()
    val lookupPc = in UInt (config.xlen bits)
    val responseValid = out Bool ()
    val prediction = out Vec (OooBankedFetchPrediction(config), config.fetchWidth)

    val btbUpdateValid = in Bool ()
    val btbUpdatePc = in UInt (config.xlen bits)
    val btbUpdateTarget = in UInt (config.xlen bits)
    val btbUpdateType = in UInt (OooPredictedBranchType.Width bits)
    val btbUpdateDirectionTrained = in Bool ()

    val phtUpdateValid = in Bool ()
    val phtUpdatePc = in UInt (config.xlen bits)
    val phtUpdateIndex = in UInt (phtRowWidth bits)
    val phtUpdateOldState = in UInt (2 bits)
    val phtUpdateOldValid = in Bool ()
    val phtUpdateTaken = in Bool ()

    val speculativeHistoryValid = in Bool ()
    val speculativeHistoryTaken = in Bool ()
    val speculativeRasPush = in Bool ()
    val speculativeRasPop = in Bool ()
    val speculativeReturnAddress = in UInt (config.xlen bits)

    val commitRasPush = in Bool ()
    val commitRasPop = in Bool ()
    val commitReturnAddress = in UInt (config.xlen bits)
    val flush = in Bool ()
  }

  val btbBanks = Array.fill(config.fetchWidth)(
    Mem(Bits(btbEntryWidth bits), btbEntriesPerBank)
  )
  val phtBanks = Array.fill(config.fetchWidth)(
    Mem(Bits(2 bits), phtEntriesPerBank)
  )

  val invalidating = RegInit(True)
  val invalidateRow = Reg(UInt(btbRowWidth bits)) init (0)
  when(invalidating) {
    when(invalidateRow === U(btbEntriesPerBank - 1, btbRowWidth bits)) {
      invalidating := False
    }.otherwise {
      invalidateRow := invalidateRow + 1
    }
  }

  val stageBtbUpdateValid = RegNext(io.btbUpdateValid) init (False)
  val stageBtbUpdatePc = RegNext(io.btbUpdatePc) init (0)
  val stageBtbUpdateTarget = RegNext(io.btbUpdateTarget) init (0)
  val stageBtbUpdateType = RegNext(io.btbUpdateType) init (OooPredictedBranchType.conditional)
  val stageBtbUpdateDirectionTrained = RegNext(io.btbUpdateDirectionTrained) init (False)

  val stagePhtUpdateValid = RegNext(io.phtUpdateValid) init (False)
  val stagePhtUpdatePc = RegNext(io.phtUpdatePc) init (0)
  val stagePhtUpdateIndex = RegNext(io.phtUpdateIndex) init (0)
  val stagePhtUpdateOldState = RegNext(io.phtUpdateOldState) init (0)
  val stagePhtUpdateOldValid = RegNext(io.phtUpdateOldValid) init (False)
  val stagePhtUpdateTaken = RegNext(io.phtUpdateTaken) init (False)

  val stageCommitRasPush = RegNext(io.commitRasPush) init (False)
  val stageCommitRasPop = RegNext(io.commitRasPop) init (False)
  val stageCommitReturnAddress = RegNext(io.commitReturnAddress) init (0)

  private val bimodalEntries = 64
  private val bimodalIndexWidth = log2Up(bimodalEntries)
  val bimodalTable = Vec.fill(bimodalEntries)(Reg(UInt(2 bits)) init (0))
  val bimodalUpdateIdx = stagePhtUpdatePc(2 + bimodalIndexWidth - 1 downto 2)
  val bimodalOldState = bimodalTable(bimodalUpdateIdx)
  when(stagePhtUpdateValid && stagePhtUpdateTaken && bimodalOldState =/= 3) {
    bimodalTable(bimodalUpdateIdx) := bimodalOldState + 1
  }.elsewhen(stagePhtUpdateValid && !stagePhtUpdateTaken && bimodalOldState =/= 0) {
    bimodalTable(bimodalUpdateIdx) := bimodalOldState - 1
  }

  val speculativeGhr = Reg(Bits(historyWidth bits)) init (0)
  val architecturalGhr = Reg(Bits(historyWidth bits)) init (0)

  val speculativeRas = Vec.fill(rasDepth)(Reg(UInt(config.xlen bits)) init (0))
  val architecturalRas = Vec.fill(rasDepth)(Reg(UInt(config.xlen bits)) init (0))
  val speculativeRasCount = Reg(UInt(rasCountWidth bits)) init (0)
  val architecturalRasCount = Reg(UInt(rasCountWidth bits)) init (0)

  when(io.phtUpdateValid) {
    architecturalGhr := architecturalGhr(historyWidth - 2 downto 0) ##
      io.phtUpdateTaken.asBits
  }
  when(io.speculativeHistoryValid) {
    speculativeGhr := speculativeGhr(historyWidth - 2 downto 0) ##
      io.speculativeHistoryTaken.asBits
  }

  when(stageCommitRasPush && !stageCommitRasPop) {
    when(architecturalRasCount =/= U(rasDepth, rasCountWidth bits)) {
      architecturalRas(architecturalRasCount(rasIndexWidth - 1 downto 0)) :=
        stageCommitReturnAddress
      architecturalRasCount := architecturalRasCount + 1
    }
  }.elsewhen(stageCommitRasPop && !stageCommitRasPush) {
    when(architecturalRasCount =/= 0) {
      architecturalRasCount := architecturalRasCount - 1
    }
  }
  when(io.speculativeRasPush && !io.speculativeRasPop) {
    when(speculativeRasCount =/= U(rasDepth, rasCountWidth bits)) {
      speculativeRas(speculativeRasCount(rasIndexWidth - 1 downto 0)) :=
        io.speculativeReturnAddress
      speculativeRasCount := speculativeRasCount + 1
    }
  }.elsewhen(io.speculativeRasPop && !io.speculativeRasPush) {
    when(speculativeRasCount =/= 0) {
      speculativeRasCount := speculativeRasCount - 1
    }
  }
  when(io.flush) {
    speculativeGhr := Mux(
      io.phtUpdateValid,
      architecturalGhr(historyWidth - 2 downto 0) ## io.phtUpdateTaken.asBits,
      architecturalGhr
    )
    speculativeRasCount := architecturalRasCount
    for (entry <- 0 until rasDepth) {
      speculativeRas(entry) := architecturalRas(entry)
    }
  }

  val lookupFire = io.lookupValid && !invalidating
  val lookupBtbRow = io.lookupPc(
    fetchGroupOffsetWidth + btbRowWidth - 1 downto fetchGroupOffsetWidth
  )
  val lookupTag = io
    .lookupPc(
      config.xlen - 1 downto fetchGroupOffsetWidth + btbRowWidth
    )
    .asBits
  val lookupGhr = Bits(historyWidth bits)
  lookupGhr := speculativeGhr
  when(io.speculativeHistoryValid) {
    lookupGhr := speculativeGhr(historyWidth - 2 downto 0) ##
      io.speculativeHistoryTaken.asBits
  }
  val lookupPhtIndex = lookupGhr(4 downto 0) ##
    io.lookupPc(fetchGroupOffsetWidth + 4 downto fetchGroupOffsetWidth)
  val capturedTag = Reg(Bits(btbTagWidth bits)) init (0)
  val capturedPhtIndex = Reg(UInt(phtRowWidth bits)) init (0)
  val capturedLookupPc = Reg(UInt(config.xlen bits)) init (0)
  when(lookupFire) {
    capturedTag := lookupTag
    capturedPhtIndex := lookupPhtIndex.asUInt
    capturedLookupPc := io.lookupPc
  }
  io.responseValid := RegNext(lookupFire) init (False)

  val btbUpdateBank = stageBtbUpdatePc(fetchGroupOffsetWidth - 1 downto 2)
  val btbUpdateRow = stageBtbUpdatePc(
    fetchGroupOffsetWidth + btbRowWidth - 1 downto fetchGroupOffsetWidth
  )
  val btbUpdateTag = stageBtbUpdatePc(
    config.xlen - 1 downto fetchGroupOffsetWidth + btbRowWidth
  ).asBits
  val btbUpdateEntry = B(0, btbEntryWidth bits)
  btbUpdateEntry(btbTargetLsb + config.xlen - 1 downto btbTargetLsb) :=
    stageBtbUpdateTarget.asBits
  btbUpdateEntry(
    btbTypeLsb + OooPredictedBranchType.Width - 1 downto btbTypeLsb
  ) := stageBtbUpdateType.asBits
  btbUpdateEntry(btbTagLsb + btbTagWidth - 1 downto btbTagLsb) := btbUpdateTag
  btbUpdateEntry(btbValidBit) := True
  btbUpdateEntry(btbDirectionTrainedBit) := stageBtbUpdateDirectionTrained

  val phtUpdateBank = stagePhtUpdatePc(fetchGroupOffsetWidth - 1 downto 2)
  val phtNextState = UInt(2 bits)
  phtNextState := Mux(stagePhtUpdateTaken, U(2, 2 bits), U(1, 2 bits))
  when(stagePhtUpdateOldValid && stagePhtUpdateTaken && stagePhtUpdateOldState =/= 3) {
    phtNextState := stagePhtUpdateOldState + 1
  }.elsewhen(stagePhtUpdateOldValid && !stagePhtUpdateTaken && stagePhtUpdateOldState =/= 0) {
    phtNextState := stagePhtUpdateOldState - 1
  }.elsewhen(stagePhtUpdateOldValid) {
    phtNextState := stagePhtUpdateOldState
  }

  val btbRead = Vec(Bits(btbEntryWidth bits), config.fetchWidth)
  val phtRead = Vec(Bits(2 bits), config.fetchWidth)
  for (bank <- 0 until config.fetchWidth) {
    val btbWrite = stageBtbUpdateValid &&
      btbUpdateBank === U(bank, bankWidth bits) && !invalidating
    btbBanks(bank).write(
      address = Mux(invalidating, invalidateRow, btbUpdateRow),
      data = Mux(invalidating, B(0, btbEntryWidth bits), btbUpdateEntry),
      enable = invalidating || btbWrite
    )
    btbRead(bank) := btbBanks(bank).readSync(
      address = lookupBtbRow,
      enable = lookupFire
    )

    val phtWrite = stagePhtUpdateValid &&
      phtUpdateBank === U(bank, bankWidth bits)
    phtBanks(bank).write(
      address = stagePhtUpdateIndex,
      data = phtNextState.asBits,
      enable = phtWrite
    )
    phtRead(bank) := phtBanks(bank).readSync(
      address = lookupPhtIndex.asUInt,
      enable = lookupFire
    )

    val entryTag = btbRead(bank)(btbTagLsb + btbTagWidth - 1 downto btbTagLsb)
    io.prediction(bank).hit := io.responseValid && btbRead(bank)(btbValidBit) &&
      entryTag === capturedTag
    io.prediction(bank).phtValid := io.responseValid &&
      btbRead(bank)(btbDirectionTrainedBit)
    io.prediction(bank).branchType :=
      btbRead(bank)(btbTypeLsb + OooPredictedBranchType.Width - 1 downto btbTypeLsb).asUInt
    io.prediction(bank).phtState := phtRead(bank).asUInt
    io.prediction(bank).phtIndex := capturedPhtIndex
    io.prediction(bank).target :=
      btbRead(bank)(btbTargetLsb + config.xlen - 1 downto btbTargetLsb).asUInt
    val lanePc = capturedLookupPc + U(bank * 4, config.xlen bits)
    io.prediction(bank).fallbackTaken := io.responseValid &&
      bimodalTable(lanePc(2 + bimodalIndexWidth - 1 downto 2))(1)
    when(io.prediction(bank).branchType === OooPredictedBranchType.ret) {
      when(speculativeRasCount =/= 0) {
        io.prediction(bank).target :=
          speculativeRas(speculativeRasCount(rasIndexWidth - 1 downto 0) - 1)
      }.elsewhen(architecturalRasCount =/= 0) {
        io.prediction(bank).target :=
          architecturalRas(architecturalRasCount(rasIndexWidth - 1 downto 0) - 1)
      }
    }
  }
}
