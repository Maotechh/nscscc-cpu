# nscscc-cpu — Pure SpinalHDL

## ⚡ One-command build
```bash
cd spinal && sbt "runMain openla500.GenCore"
# → generates rtl/CPUCoreFlat.v (single Verilog, all CPU logic)
```

## Architecture
- `spinal/Core.scala` — ALL CPU logic in one flat Spinal Component (inlined 5-stage pipeline + I/D-Cache + ALU + RegFile + Branch + AXI bridge)
- `spinal/*.scala` — Individual module reference implementations
- `rtl/CPUCoreFlat.v` — Generated Verilog (626 lines)
- `soc/` — SoC config, `sw/` — Software benchmarks
- cacop fix included in ICache/DCache logic

## GitHub
https://github.com/Maotechh/nscscc-cpu
