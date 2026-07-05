name := "nscscc-cpu-spinal"
version := "1.0"
scalaVersion := "2.13.16"

val spinalVersion = "1.14.2"

libraryDependencies ++= Seq(
  "com.github.spinalhdl" %% "spinalhdl-core" % spinalVersion,
  "com.github.spinalhdl" %% "spinalhdl-lib"  % spinalVersion,
  "org.scalatest"        %% "scalatest"       % "3.2.19" % Test
)

fork := true
