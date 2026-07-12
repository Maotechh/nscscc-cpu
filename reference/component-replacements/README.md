# Generated Component Replacements

`alu.v` is generated from `spinal/src/main/scala/openla500/execute/OpenLa500Alu.scala` by the locked Scala/SBT/Spinal toolchain. It is committed so a chiplab overlay can consume an ordinary Git blob rather than a local build directory.

The corresponding `alu.json` binds the target, source blob SHA256 and `a158aa8` base SHA256. Regenerate into a fresh `OUT_DIR` with `make generate TARGET=alu`, then update the spec only after the generated hash and all ALU gates pass. This directory is not the active whole-CPU top; the old Verilog remains the stable path until integration evidence exists.
