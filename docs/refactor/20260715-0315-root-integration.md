# 20260715 ECHO root Makefile integration

## Boundary

This iteration records the root-only governance and integration milestone. The
CPU evidence is on `nscscc-cpu/refactor/ECHO`; root `main` may commit `AGENTS.md`
and `Makefile` but has no remote and is never pushed. `chiplab` remains dirty only
with pre-existing Vivado journal files and received no commit or push.

- Root base before milestone: `de6133775d615a808089ffa5db6349fb6233f27f`
- CPU ECHO input: `1a08373127af31c495f19005ac1204f7766da78a`
- Official nested `myCPU`: `aa3bde1f3e720e71c2c78d6b81930d797b810149`
- CPU profile: official-default, SpinalHDL generated `core_top`; LACC/store-buffer remain opt-in
- Local temp profile: `/tmp` by default; `LOCAL_TMP_ROOT` can explicitly select a host temp path

## Commands and exits

| command | exit | result |
| --- | --- | --- |
| `make local-doctor` | 0 | Java 21.0.11, Verilator 5.051, Python 3.10.12, SBT runner, GCC/QEMU/NEMU captured; Yosys missing is explicit |
| `make cpu` | 0 | `GenerateCoreTopCompat` emitted one `core_top.v`; Spinal reported 115 pruned signals |
| `make cpu-package` | 0 | package gate: 49 ports, 17 inputs, 32 outputs, `TLBNUM=32` |
| `make core-contract` | 0 | official aa3bde1 header/raw contract and 49-port manifest pass |
| `make cpu-stage` | 0 | one staged `mycpu_top.v`; official `chiplab/IP/myCPU` unchanged |
| `make sim TEST=func/func_lab19 SIM_TIME_LIMIT=100000` | 2 | fail-closed transcript: 12014 instructions, 49995 clocks, `Time limit exceeded`, no good trap/end marker, 27 compiler warnings |
| `codex execpolicy check ... make cpu-stage` | allow | exact default.rules match |
| `codex execpolicy check ... git push ...` | no match | Git push remains approval-gated |

The earlier unlimited smoke was interrupted with exit 130 after about six minutes
because it made no progress marker under `TIME_LIMIT=0`; it is not a pass claim.

## Artifact hashes

- generated raw `core_top.v`: `de3a9a3b4b762091da564962bc99b3895ee8c9083ca05ce54f4ed0ca726d57e8`
- packaged `rtl/mycpu_top.v`: `ac6a631e696d3bc75f41604b1f7191ad62655834b9f9ed37abcab030c6e706f1`
- official contract summary: `2643352d23af81699d5ab4a8cc407a010b0284c5b14e41cdc1043c0312d01a09`
- bounded simulation transcript: `58f16dc7c4244786ee8a2c423f56fa04513454457730e4a69d06247963a451c2`
- bounded simulation summary: `5e9516ba606d5c13d8b56ffa3c51ee8c39899a221501dc7ebefa8d07e707668a`
- root Makefile after edits: `5d58b58f683bbf38715e3622a3baf1b3c62ab7be90528f8d3db51c3d62df21c6`
- root `AGENTS.md` after edits: `a15de4d861f806bda9cbc4a3445742ba102e90d92dacb8556b2c62038a23430a`
- `.codex/rules/default.rules`: `eafa4cc477cea74e431e5a17fd3d87403ba76c813b7a85ac455a42ee5d09090a`

## Claims, risks, rollback

Qualified evidence: canonical generation, package contract, official source contract,
and isolated source staging pass. The simulation is diagnostic-only and explicitly
fails closed. The generated design still has unresolved warning policy, full
functional behavior, random/DiffTest, performance/system, Yosys, and Vivado gates.

Rollback is the root milestone commit after review; CPU rollback is the pushed ECHO
commit `1a08373127af31c495f19005ac1204f7766da78a`. Do not remove chiplab journals or
clean user workspaces.
