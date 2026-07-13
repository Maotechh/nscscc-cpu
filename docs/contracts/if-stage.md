# IF Stage Contract

## Locked identity

- Golden: `a158aa8:rtl/if_stage.v`
- Golden blob SHA-256: `9fcc66200e549825c89737b420c68e97a22af1082e370536ad67e3d72e035547`
- Golden size: 12929 bytes
- Legacy `BR_BUS_WD`: 33 bits; `FS_TO_DS_BUS_WD`: 109 bits
- Reset: synchronous, active high; reset PC trick is `0x1bfffffc` so the first sequential request is `0x1c000000`.

## Typed boundary

`FetchStage` owns fetch PC, instruction request/data acknowledgement, BTB lock, delayed flush request, branch repair wait states, alignment/TLB cancellation, and the `Stream[FetchPayload]` output. `LegacyIfStage` is the only component exposing the historical `if_stage` port names.

The 109-bit payload order remains:

```text
btbTarget[108:77], btbIndex[76:72], btbTaken[71], btbEnabled[70],
icacheMiss[69], exception[68], exceptionCode[67:64], instruction[63:32], pc[31:0]
```

The golden BTB lock merge is intentionally a bitwise OR of the locked and current BTB fields. It is not replaced with a mux because that changes the observable fetch address under a stalled request.

## Evidence command

```bash
python3 -I tools/if_stage_gate.py --repo . \
  --candidate <generated>/if_stage.v --out-dir <fresh-output>
```

The gate checks the port name/direction/width set, explicit Verilator warning-ID allowlists, Yosys hierarchy/check, a fixed-seed 2048-cycle golden/candidate lockstep, and a negative-control run which must report `IF_MISMATCH` and exit non-zero. The committed candidate and its hash live in `reference/component-replacements/if_stage.v` and `reference/component-replacements/if-stage.json`; local raw result locators and hashes are in the iteration artifacts log.

## Known boundary

This evidence covers one fixed-seed isolated IF trace only. Idle/icacop/interrupt/reset-reentry combinations and multiple seeds remain open. It does not prove integration with ID/BTB/ICache, official chiplab functionality, random NEMU DiffTest, or whole-core equivalence. The current branch must remain an independent review candidate until those gates are rerun from its committed generated RTL.
