PYTHON ?= $(if $(filter Windows_NT,$(OS)),python,python3)
SBT ?=
OUT_DIR ?= build
ITERATION_ID ?=
CHIPLAB_REFERENCE ?=
CHIPLAB_TOOL_ROOT ?= /opt/chiplab-tools/root
CHIPLAB_WORK_ROOT ?= /tmp/nscscc-refactor-work
DUT_SOURCE ?= candidate
REPLACEMENT_SPEC ?=
SOURCE_HEAD ?=
DIAGNOSTIC ?=
LOCKED_ITERATION_ID ?=
MIXED_ITERATION_ID ?=$(ITERATION_ID)
VIVADO_HOME ?=
SCALA_CACHE_ROOT ?= $(CHIPLAB_TOOL_ROOT)/scala-cache-sbt1.10.11-spinal1.14.2

ifneq ($(word 2,$(strip $(DIAGNOSTIC))),)
$(error DIAGNOSTIC must be empty, 0, or 1)
endif
ifneq ($(strip $(filter-out 0 1,$(DIAGNOSTIC))),)
$(error DIAGNOSTIC must be empty, 0, or 1)
endif
DIAGNOSTIC_ARG = $(if $(filter 1,$(DIAGNOSTIC)),--diagnostic,)

TARGET ?=
ALU_GENERATE_DIR ?= $(OUT_DIR)/alu/generate
ALU_RTL ?= $(ALU_GENERATE_DIR)/rtl/alu.v
MUL_GENERATE_DIR ?= $(OUT_DIR)/mul/generate
MUL_RTL ?= $(MUL_GENERATE_DIR)/rtl/mul.v
MUL_CONTRACT ?= reference/component-contracts/mul.json
MUL_VECTOR_COUNT ?= 4096
MUL_RANDOM_SEED ?= 0x158aa8
DIV_CONTRACT ?= reference/component-contracts/div.json
DIV_VECTOR_COUNT ?= 4096
DIV_RANDOM_SEED ?= 0x158aa8
DIV_GENERATE_DIR ?= $(OUT_DIR)/div/generate
DIV_RTL ?= $(DIV_GENERATE_DIR)/rtl/div.v
AXI_BRIDGE_CONTRACT ?= reference/component-contracts/axi-bridge.json
AXI_BRIDGE_CYCLES ?= 8192
AXI_BRIDGE_RANDOM_SEED ?= 0x158aa8
AXI_BRIDGE_GENERATE_DIR ?= $(OUT_DIR)/axi_bridge/generate
AXI_BRIDGE_RTL ?= $(AXI_BRIDGE_GENERATE_DIR)/rtl/axi_bridge.v
CSR_GENERATE_DIR ?= $(OUT_DIR)/csr/generate
CSR_RTL ?= $(CSR_GENERATE_DIR)/rtl/csr.v
CSR_DIFF_GENERATE_DIR ?= $(OUT_DIR)/csr/generate-diff
CSR_DIFF_RTL ?= $(CSR_DIFF_GENERATE_DIR)/rtl/csr.v
WB_STAGE_CONTRACT ?= reference/component-contracts/wb-stage.json
WB_STAGE_CYCLES ?= 8192
WB_STAGE_RANDOM_SEED ?= 0x0158aa8c
WB_STAGE_GENERATE_DIR ?= $(OUT_DIR)/wb_stage/generate
WB_STAGE_RTL ?= $(WB_STAGE_GENERATE_DIR)/rtl/wb_stage.v
WB_STAGE_DIFF_GENERATE_DIR ?= $(OUT_DIR)/wb_stage/generate-diff
WB_STAGE_DIFF_RTL ?= $(WB_STAGE_DIFF_GENERATE_DIR)/rtl/wb_stage.v
MEM_STAGE_CONTRACT ?= reference/component-contracts/mem-stage.json
MEM_STAGE_CYCLES ?= 8192
MEM_STAGE_RANDOM_SEED ?= 0x0158aa8d
MEM_STAGE_GENERATE_DIR ?= $(OUT_DIR)/mem_stage/generate
MEM_STAGE_RTL ?= $(MEM_STAGE_GENERATE_DIR)/rtl/mem_stage.v
ID_STAGE_PROFILE ?= normal
ID_STAGE_MAIN = $(if $(filter normal,$(ID_STAGE_PROFILE)),openla500.pipeline.GenerateOpenLa500DecodeStage,$(if $(filter difftest,$(ID_STAGE_PROFILE)),openla500.pipeline.GenerateOpenLa500DecodeStageDiff,$(if $(filter lacc,$(ID_STAGE_PROFILE)),openla500.pipeline.GenerateOpenLa500DecodeStageWithLacc,openla500.pipeline.GenerateOpenLa500DecodeStageWithLaccDiff)))
ID_STAGE_GENERATE_DIR ?= $(OUT_DIR)/id_stage/$(ID_STAGE_PROFILE)/generate
ID_STAGE_RTL ?= $(ID_STAGE_GENERATE_DIR)/rtl/id_stage.v
ID_STAGE_CYCLES ?= 8192
EXE_STAGE_PROFILE ?= lacc_off
EXE_STAGE_MAIN = $(if $(filter lacc_on,$(EXE_STAGE_PROFILE)),openla500.pipeline.GenerateOpenLa500ExecuteStageWithLacc,openla500.pipeline.GenerateOpenLa500ExecuteStage)
EXE_STAGE_GENERATE_DIR ?= $(OUT_DIR)/exe_stage/$(EXE_STAGE_PROFILE)/generate
EXE_STAGE_RTL ?= $(EXE_STAGE_GENERATE_DIR)/rtl/exe_stage.v
ICACHE_CONTRACT ?= reference/component-contracts/icache.json
ICACHE_CYCLES ?= 12000
ICACHE_GENERATE_DIR ?= $(OUT_DIR)/icache/generate
ICACHE_RTL ?= $(ICACHE_GENERATE_DIR)/rtl/icache.v
DCACHE_CONTRACT ?= reference/component-contracts/dcache.json
DCACHE_CYCLES ?= 12000
DCACHE_GENERATE_DIR ?= $(OUT_DIR)/dcache/generate
DCACHE_RTL ?= $(DCACHE_GENERATE_DIR)/rtl/dcache.v
CACOP_RECOVERY_OUT ?= $(OUT_DIR)/cacop-recovery/unit
CACOP_RECOVERY_REPO ?= .
TLB_RTL ?= reference/component-replacements/tlb_entry.v
TLB_CYCLES ?= 8192
TLB_RANDOM_SEED ?= 0x158aa8
TLB_GENERATE_DIR ?= $(OUT_DIR)/tlb/generate
ADDR_TRANS_GENERATE_DIR ?= $(OUT_DIR)/addr_trans/generate
ADDR_TRANS_RTL ?= $(ADDR_TRANS_GENERATE_DIR)/rtl/addr_trans.v
CORE_TOP_PORTS ?= reference/core-top.ports.json
CORE_TOP_GENERATE_DIR ?= $(OUT_DIR)/core_top/generate
CORE_TOP_WRAPPER_RTL ?= $(CORE_TOP_GENERATE_DIR)/rtl/core_top.v
CORE_TOP_PACKAGE_DIR ?= $(OUT_DIR)/core_top/package
CORE_TOP_RTL ?= $(CORE_TOP_PACKAGE_DIR)/rtl/mycpu_top.v
CORE_TOP_TRACKED_RTL ?= reference/component-replacements/mycpu_top.v
CORE_TOP_REPLACEMENT_SPEC ?= reference/component-replacements/core-top.json
LINT_WAIVERS ?= lint-waivers.yml

.PHONY: doctor scala-cache-bootstrap scala-check elaborate generate port-check lint yosys-check unit formal cacop-recovery-unit core-contract-check core-top-contract core-top-package core-top-publish-check mul-contract mul-golden-unit mul-candidate-unit div-contract div-golden-unit div-candidate-unit axi-bridge-contract axi-bridge-candidate-unit csr-generate csr-port-check csr-static csr-unit wb-stage-contract wb-stage-candidate-unit mem-stage-contract mem-stage-candidate-unit exe-stage-negative-control icache-contract icache-candidate-unit dcache-contract dcache-candidate-unit replacement-reachability chiplab-doctor golden-export chiplab-overlay rtl-smoke identity-compare evidence-check test-automation

doctor:
	$(PYTHON) -I tools/refactor.py doctor --out-dir "$(OUT_DIR)" $(if $(VIVADO_HOME),--vivado-home "$(VIVADO_HOME)",)

scala-cache-bootstrap:
	$(PYTHON) -I tools/bootstrap_scala_cache.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --cache-root "$(SCALA_CACHE_ROOT)" --lock-out "reference/scala-dependencies.lock.json"

scala-check:
	$(PYTHON) -I tools/scala_gate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/scala-check" $(if $(SBT),--sbt "$(SBT)",) $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)

elaborate:
ifeq ($(TARGET),core_top)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.compat.GenerateCoreTopCompat" --expected-module "core_top" --expected-file "core_top.v" --out-dir "$(OUT_DIR)/core_top/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py elaborate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/mul/elaborate" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),div)
	$(PYTHON) -I tools/div_gate.py elaborate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/div/elaborate" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),axi_bridge)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.memory.GenerateOpenLa500AxiBridge" --expected-module "axi_bridge" --expected-file "axi_bridge.v" --out-dir "$(OUT_DIR)/axi_bridge/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),exe_stage)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "$(EXE_STAGE_MAIN)" --expected-module "exe_stage" --expected-file "exe_stage.v" --out-dir "$(OUT_DIR)/exe_stage/$(EXE_STAGE_PROFILE)/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.memory.GenerateOpenLa500ICache" --expected-module "icache" --expected-file "icache.v" --out-dir "$(OUT_DIR)/icache/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),dcache)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.memory.GenerateOpenLa500DCache" --expected-module "dcache" --expected-file "dcache.v" --out-dir "$(OUT_DIR)/dcache/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),tlb)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.privileged.GenerateOpenLa500TlbEntry" --expected-module "tlb_entry" --expected-file "tlb_entry.v" --out-dir "$(TLB_GENERATE_DIR)/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),addr_trans)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.privileged.GenerateOpenLa500AddrTrans" --expected-module "addr_trans" --expected-file "addr_trans.v" --out-dir "$(ADDR_TRANS_GENERATE_DIR)/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),wb_stage)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.pipeline.GenerateOpenLa500WritebackStage" --expected-module "wb_stage" --expected-file "wb_stage.v" --out-dir "$(OUT_DIR)/wb_stage/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.pipeline.GenerateOpenLa500WritebackStageDiff" --expected-module "wb_stage" --expected-file "wb_stage.v" --out-dir "$(OUT_DIR)/wb_stage/elaborate-diff" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),mem_stage)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.pipeline.GenerateOpenLa500MemoryStage" --expected-module "mem_stage" --expected-file "mem_stage.v" --out-dir "$(OUT_DIR)/mem_stage/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),id_stage)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "$(ID_STAGE_MAIN)" --expected-module "id_stage" --expected-file "id_stage.v" --out-dir "$(OUT_DIR)/id_stage/$(ID_STAGE_PROFILE)/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py elaborate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/alu/elaborate" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected core_top, alu, mul, div, axi_bridge, exe_stage, mem_stage, icache, tlb, addr_trans, or wb_stage" >&2; exit 2
endif

generate:
ifeq ($(TARGET),core_top)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.compat.GenerateCoreTopCompat" --expected-module "core_top" --expected-file "core_top.v" --out-dir "$(CORE_TOP_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
	$(PYTHON) -I tools/core_top_gate.py package --repo-root "." --manifest "reference/manifest.lock" --ports "$(CORE_TOP_PORTS)" --rtl "$(CORE_TOP_WRAPPER_RTL)" --out-dir "$(CORE_TOP_PACKAGE_DIR)"
	$(PYTHON) -I tools/core_top_gate.py publish-check --repo-root "." --manifest "reference/manifest.lock" --ports "$(CORE_TOP_PORTS)" --rtl "$(CORE_TOP_RTL)" --tracked-rtl "$(CORE_TOP_TRACKED_RTL)" --replacement-spec "$(CORE_TOP_REPLACEMENT_SPEC)" --out-dir "$(OUT_DIR)/core_top/publish-check"
else ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py generate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(MUL_GENERATE_DIR)" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),div)
	$(PYTHON) -I tools/div_gate.py generate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(DIV_GENERATE_DIR)" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),axi_bridge)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.memory.GenerateOpenLa500AxiBridge" --expected-module "axi_bridge" --expected-file "axi_bridge.v" --out-dir "$(AXI_BRIDGE_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),exe_stage)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "$(EXE_STAGE_MAIN)" --expected-module "exe_stage" --expected-file "exe_stage.v" --out-dir "$(EXE_STAGE_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.memory.GenerateOpenLa500ICache" --expected-module "icache" --expected-file "icache.v" --out-dir "$(ICACHE_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),dcache)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.memory.GenerateOpenLa500DCache" --expected-module "dcache" --expected-file "dcache.v" --out-dir "$(DCACHE_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),tlb)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.privileged.GenerateOpenLa500TlbEntry" --expected-module "tlb_entry" --expected-file "tlb_entry.v" --out-dir "$(TLB_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),addr_trans)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.privileged.GenerateOpenLa500AddrTrans" --expected-module "addr_trans" --expected-file "addr_trans.v" --out-dir "$(ADDR_TRANS_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),wb_stage)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.pipeline.GenerateOpenLa500WritebackStage" --expected-module "wb_stage" --expected-file "wb_stage.v" --out-dir "$(WB_STAGE_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.pipeline.GenerateOpenLa500WritebackStageDiff" --expected-module "wb_stage" --expected-file "wb_stage.v" --out-dir "$(WB_STAGE_DIFF_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),mem_stage)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.pipeline.GenerateOpenLa500MemoryStage" --expected-module "mem_stage" --expected-file "mem_stage.v" --out-dir "$(MEM_STAGE_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),id_stage)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "$(ID_STAGE_MAIN)" --expected-module "id_stage" --expected-file "id_stage.v" --out-dir "$(ID_STAGE_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py generate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(ALU_GENERATE_DIR)" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else
	@echo "ERROR: unsupported TARGET=$(TARGET); use a target-specific gate or add a prerequisite target" >&2; exit 2
endif

port-check:
ifeq ($(TARGET),core_top)
	$(PYTHON) -I tools/core_top_gate.py port-check --repo-root "." --manifest "reference/manifest.lock" --ports "$(CORE_TOP_PORTS)" --rtl "$(CORE_TOP_RTL)" --out-dir "$(OUT_DIR)/core_top/port-check"
else ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py port-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/port-check"
else ifeq ($(TARGET),div)
	$(PYTHON) -I tools/div_gate.py port-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(DIV_RTL)" --out-dir "$(OUT_DIR)/div/port-check"
else ifeq ($(TARGET),axi_bridge)
	$(PYTHON) -I tools/axi_bridge_gate.py port-check --contract "$(AXI_BRIDGE_CONTRACT)" --rtl "$(AXI_BRIDGE_RTL)" --out-dir "$(OUT_DIR)/axi_bridge/port-check"
else ifeq ($(TARGET),exe_stage)
	$(PYTHON) -I tools/exe_stage_ports.py --rtl "$(EXE_STAGE_RTL)" --profile "$(EXE_STAGE_PROFILE)" --out-dir "$(OUT_DIR)/exe_stage/$(EXE_STAGE_PROFILE)/port-check"
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/icache_gate.py port-check --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/port-check"
else ifeq ($(TARGET),dcache)
	$(PYTHON) -I tools/dcache_gate.py port-check --contract "$(DCACHE_CONTRACT)" --rtl "$(DCACHE_RTL)" --out-dir "$(OUT_DIR)/dcache/port-check"
else ifeq ($(TARGET),wb_stage)
	$(PYTHON) -I tools/wb_stage_gate.py port-check --repo "." --contract "$(WB_STAGE_CONTRACT)" --profile normal --rtl "$(WB_STAGE_RTL)" --out-dir "$(OUT_DIR)/wb_stage/port-normal"
	$(PYTHON) -I tools/wb_stage_gate.py port-check --repo "." --contract "$(WB_STAGE_CONTRACT)" --profile difftest --rtl "$(WB_STAGE_DIFF_RTL)" --out-dir "$(OUT_DIR)/wb_stage/port-difftest"
else ifeq ($(TARGET),mem_stage)
	$(PYTHON) -I tools/mem_stage_gate.py port-check --repo "." --contract "$(MEM_STAGE_CONTRACT)" --rtl "$(MEM_STAGE_RTL)" --out-dir "$(OUT_DIR)/mem_stage/port-check"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py port-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/port-check"
else
	@echo "ERROR: unsupported TARGET=$(TARGET); use a target-specific port gate or add a prerequisite target" >&2; exit 2
endif

lint:
ifeq ($(TARGET),core_top)
	$(PYTHON) -I tools/core_top_gate.py lint --repo-root "." --manifest "reference/manifest.lock" --ports "$(CORE_TOP_PORTS)" --rtl "$(CORE_TOP_RTL)" --out-dir "$(OUT_DIR)/core_top/lint"
else ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py lint --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/lint"
else ifeq ($(TARGET),div)
	$(PYTHON) -I tools/div_gate.py lint --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(DIV_RTL)" --out-dir "$(OUT_DIR)/div/lint"
else ifeq ($(TARGET),axi_bridge)
	$(PYTHON) -I tools/axi_bridge_gate.py lint --contract "$(AXI_BRIDGE_CONTRACT)" --rtl "$(AXI_BRIDGE_RTL)" --out-dir "$(OUT_DIR)/axi_bridge/lint"
else ifeq ($(TARGET),exe_stage)
	verilator --lint-only -Wall -Wno-DECLFILENAME --top-module exe_stage "$(EXE_STAGE_RTL)"
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/icache_gate.py lint --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/lint"
else ifeq ($(TARGET),dcache)
	$(PYTHON) -I tools/dcache_gate.py lint --contract "$(DCACHE_CONTRACT)" --rtl "$(DCACHE_RTL)" --out-dir "$(OUT_DIR)/dcache/lint"
else ifeq ($(TARGET),wb_stage)
	$(PYTHON) -I tools/wb_stage_gate.py lint --repo "." --contract "$(WB_STAGE_CONTRACT)" --profile normal --rtl "$(WB_STAGE_RTL)" --out-dir "$(OUT_DIR)/wb_stage/lint-normal"
	$(PYTHON) -I tools/wb_stage_gate.py lint --repo "." --contract "$(WB_STAGE_CONTRACT)" --profile difftest --rtl "$(WB_STAGE_DIFF_RTL)" --out-dir "$(OUT_DIR)/wb_stage/lint-difftest"
else ifeq ($(TARGET),mem_stage)
	$(PYTHON) -I tools/mem_stage_gate.py lint --repo "." --contract "$(MEM_STAGE_CONTRACT)" --rtl "$(MEM_STAGE_RTL)" --out-dir "$(OUT_DIR)/mem_stage/lint"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py lint --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/lint"
else
	@echo "ERROR: unsupported TARGET=$(TARGET); use a target-specific lint gate or add a prerequisite target" >&2; exit 2
endif

yosys-check:
ifeq ($(TARGET),core_top)
	$(PYTHON) -I tools/core_top_gate.py yosys-check --repo-root "." --manifest "reference/manifest.lock" --ports "$(CORE_TOP_PORTS)" --rtl "$(CORE_TOP_RTL)" --out-dir "$(OUT_DIR)/core_top/yosys-check"
else ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py yosys-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/yosys-check"
else ifeq ($(TARGET),div)
	$(PYTHON) -I tools/div_gate.py yosys-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(DIV_RTL)" --out-dir "$(OUT_DIR)/div/yosys-check"
else ifeq ($(TARGET),axi_bridge)
	$(PYTHON) -I tools/axi_bridge_gate.py yosys-check --contract "$(AXI_BRIDGE_CONTRACT)" --rtl "$(AXI_BRIDGE_RTL)" --out-dir "$(OUT_DIR)/axi_bridge/yosys-check"
else ifeq ($(TARGET),exe_stage)
	yosys -q -p 'read_verilog "$(EXE_STAGE_RTL)"; hierarchy -check -top exe_stage; proc; check -assert'
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/icache_gate.py yosys-check --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/yosys-check"
else ifeq ($(TARGET),dcache)
	$(PYTHON) -I tools/dcache_gate.py yosys-check --contract "$(DCACHE_CONTRACT)" --rtl "$(DCACHE_RTL)" --out-dir "$(OUT_DIR)/dcache/yosys-check"
else ifeq ($(TARGET),wb_stage)
	$(PYTHON) -I tools/wb_stage_gate.py yosys-check --repo "." --contract "$(WB_STAGE_CONTRACT)" --profile normal --rtl "$(WB_STAGE_RTL)" --out-dir "$(OUT_DIR)/wb_stage/yosys-normal"
	$(PYTHON) -I tools/wb_stage_gate.py yosys-check --repo "." --contract "$(WB_STAGE_CONTRACT)" --profile difftest --rtl "$(WB_STAGE_DIFF_RTL)" --out-dir "$(OUT_DIR)/wb_stage/yosys-difftest"
else ifeq ($(TARGET),mem_stage)
	$(PYTHON) -I tools/mem_stage_gate.py yosys-check --repo "." --contract "$(MEM_STAGE_CONTRACT)" --rtl "$(MEM_STAGE_RTL)" --out-dir "$(OUT_DIR)/mem_stage/yosys-check"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py yosys-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/yosys-check"
else
	@echo "ERROR: unsupported TARGET=$(TARGET); use a target-specific Yosys gate or add a prerequisite target" >&2; exit 2
endif

unit:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_diff.py candidate --contract "$(MUL_CONTRACT)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/unit" --vector-count "$(MUL_VECTOR_COUNT)" --seed "$(MUL_RANDOM_SEED)"
else ifeq ($(TARGET),div)
	$(PYTHON) -I tools/div_diff.py candidate --contract "$(DIV_CONTRACT)" --manifest "reference/manifest.lock" --rtl "$(DIV_RTL)" --out-dir "$(OUT_DIR)/div/unit" --vector-count "$(DIV_VECTOR_COUNT)" --seed "$(DIV_RANDOM_SEED)"
else ifeq ($(TARGET),axi_bridge)
	$(PYTHON) -I tools/axi_bridge_gate.py diff --contract "$(AXI_BRIDGE_CONTRACT)" --rtl "$(AXI_BRIDGE_RTL)" --out-dir "$(OUT_DIR)/axi_bridge/unit" --cycles "$(AXI_BRIDGE_CYCLES)" --seed "$(AXI_BRIDGE_RANDOM_SEED)"
else ifeq ($(TARGET),exe_stage)
	$(PYTHON) -I tools/exe_stage_diff.py --rtl "$(EXE_STAGE_RTL)" --profile "$(EXE_STAGE_PROFILE)" --out-dir "$(OUT_DIR)/exe_stage/$(EXE_STAGE_PROFILE)/unit"
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/icache_gate.py diff --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/unit" --cycles "$(ICACHE_CYCLES)"
else ifeq ($(TARGET),dcache)
	$(PYTHON) -I tools/dcache_gate.py diff --contract "$(DCACHE_CONTRACT)" --rtl "$(DCACHE_RTL)" --out-dir "$(OUT_DIR)/dcache/unit" --cycles "$(DCACHE_CYCLES)"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py unit --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/alu/unit" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),tlb)
	$(PYTHON) -I tools/tlb_gate.py diff --repo "." --rtl "$(TLB_RTL)" --out-dir "$(OUT_DIR)/tlb/unit" --cycles "$(TLB_CYCLES)" --seed "$(TLB_RANDOM_SEED)"
else ifeq ($(TARGET),wb_stage)
	$(PYTHON) -I tools/wb_stage_gate.py diff --repo "." --contract "$(WB_STAGE_CONTRACT)" --rtl "$(WB_STAGE_DIFF_RTL)" --out-dir "$(OUT_DIR)/wb_stage/unit" --cycles "$(WB_STAGE_CYCLES)" --seed "$(WB_STAGE_RANDOM_SEED)"
else ifeq ($(TARGET),mem_stage)
	$(PYTHON) -I tools/mem_stage_gate.py diff --repo "." --contract "$(MEM_STAGE_CONTRACT)" --rtl "$(MEM_STAGE_RTL)" --out-dir "$(OUT_DIR)/mem_stage/unit" --cycles "$(MEM_STAGE_CYCLES)" --seed "$(MEM_STAGE_RANDOM_SEED)"
else ifeq ($(TARGET),id_stage)
	$(PYTHON) -I tools/id_stage_gate.py --repo "." --rtl "$(ID_STAGE_RTL)" --profile "$(ID_STAGE_PROFILE)" --out-dir "$(OUT_DIR)/id_stage/$(ID_STAGE_PROFILE)/unit" --cycles "$(ID_STAGE_CYCLES)"
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected alu, mul, div, tlb, id_stage, mem_stage, or wb_stage" >&2; exit 2
endif

cacop-recovery-unit:
	$(PYTHON) -I tools/cacop_recovery_gate.py --repo "$(CACOP_RECOVERY_REPO)" --icache-rtl "$(ICACHE_RTL)" --dcache-rtl "$(DCACHE_RTL)" --out-dir "$(CACOP_RECOVERY_OUT)"

formal:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py formal --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/formal"
else ifeq ($(TARGET),div)
	$(PYTHON) -I tools/div_gate.py formal --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(DIV_RTL)" --out-dir "$(OUT_DIR)/div/formal"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py formal --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/formal"
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected alu, mul, or div" >&2; exit 2
endif

core-top-contract:
	$(PYTHON) -I tools/core_top_gate.py contract --repo-root "." --manifest "reference/manifest.lock" --ports "$(CORE_TOP_PORTS)" $(if $(CHIPLAB_REFERENCE),--chiplab-mycpu "$(CHIPLAB_REFERENCE)/IP/myCPU",) --out-dir "$(OUT_DIR)/core_top/contract"

core-top-package:
	$(PYTHON) -I tools/core_top_gate.py package --repo-root "." --manifest "reference/manifest.lock" --ports "$(CORE_TOP_PORTS)" --rtl "$(CORE_TOP_WRAPPER_RTL)" --out-dir "$(CORE_TOP_PACKAGE_DIR)"

core-top-publish-check:
	$(PYTHON) -I tools/core_top_gate.py publish-check --repo-root "." --manifest "reference/manifest.lock" --ports "$(CORE_TOP_PORTS)" --rtl "$(CORE_TOP_RTL)" --tracked-rtl "$(CORE_TOP_TRACKED_RTL)" --replacement-spec "$(CORE_TOP_REPLACEMENT_SPEC)" --out-dir "$(OUT_DIR)/core_top/publish-check"

core-contract-check:
	$(PYTHON) -I tests/test_core_contract_manifest.py

mul-contract:
	$(PYTHON) -I tools/mul_contract.py verify --contract "$(MUL_CONTRACT)" --manifest "reference/manifest.lock" --out-dir "$(OUT_DIR)/mul/contract"

mul-golden-unit:
	$(PYTHON) -I tools/mul_diff.py golden --contract "$(MUL_CONTRACT)" --manifest "reference/manifest.lock" --waivers "$(LINT_WAIVERS)" --out-dir "$(OUT_DIR)/mul/unit" --vector-count "$(MUL_VECTOR_COUNT)" --seed "$(MUL_RANDOM_SEED)"

mul-candidate-unit:
	$(PYTHON) -I tools/mul_diff.py candidate --contract "$(MUL_CONTRACT)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/unit" --vector-count "$(MUL_VECTOR_COUNT)" --seed "$(MUL_RANDOM_SEED)"

div-contract:
	$(PYTHON) -I tools/div_contract.py verify --contract "$(DIV_CONTRACT)" --manifest "reference/manifest.lock" --out-dir "$(OUT_DIR)/div/contract"

div-golden-unit:
	$(PYTHON) -I tools/div_diff.py golden --contract "$(DIV_CONTRACT)" --manifest "reference/manifest.lock" --waivers "$(LINT_WAIVERS)" --out-dir "$(OUT_DIR)/div/unit" --vector-count "$(DIV_VECTOR_COUNT)" --seed "$(DIV_RANDOM_SEED)"

div-candidate-unit:
	$(PYTHON) -I tools/div_diff.py candidate --contract "$(DIV_CONTRACT)" --manifest "reference/manifest.lock" --rtl "$(DIV_RTL)" --out-dir "$(OUT_DIR)/div/unit" --vector-count "$(DIV_VECTOR_COUNT)" --seed "$(DIV_RANDOM_SEED)"

axi-bridge-contract:
	$(PYTHON) -I tools/axi_bridge_gate.py contract --contract "$(AXI_BRIDGE_CONTRACT)" --out-dir "$(OUT_DIR)/axi_bridge/contract"

axi-bridge-candidate-unit:
	$(PYTHON) -I tools/axi_bridge_gate.py diff --contract "$(AXI_BRIDGE_CONTRACT)" --rtl "$(AXI_BRIDGE_RTL)" --out-dir "$(OUT_DIR)/axi_bridge/unit" --cycles "$(AXI_BRIDGE_CYCLES)" --seed "$(AXI_BRIDGE_RANDOM_SEED)"

csr-generate:
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.privileged.GenerateOpenLa500Csr" --expected-module "csr" --expected-file "csr.v" --out-dir "$(CSR_GENERATE_DIR)" --runs 2
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.privileged.GenerateOpenLa500CsrDiff" --expected-module "csr" --expected-file "csr.v" --out-dir "$(CSR_DIFF_GENERATE_DIR)" --runs 2

csr-port-check:
	$(PYTHON) -I tools/csr_gate.py port-check --rtl "$(CSR_RTL)" --out-dir "$(OUT_DIR)/csr/port-off"
	$(PYTHON) -I tools/csr_gate.py port-check --diff-test --rtl "$(CSR_DIFF_RTL)" --out-dir "$(OUT_DIR)/csr/port-on"

csr-static:
	$(PYTHON) -I tools/csr_gate.py static --rtl "$(CSR_DIFF_RTL)" --out-dir "$(OUT_DIR)/csr/static"

csr-unit:
	$(PYTHON) -I tools/csr_gate.py diff --repo "." --rtl "$(CSR_DIFF_RTL)" --out-dir "$(OUT_DIR)/csr/unit" --cycles 4096

wb-stage-contract:
	$(PYTHON) -I tools/wb_stage_gate.py contract --repo "." --contract "$(WB_STAGE_CONTRACT)" --out-dir "$(OUT_DIR)/wb_stage/contract"

wb-stage-candidate-unit:
	$(PYTHON) -I tools/wb_stage_gate.py diff --repo "." --contract "$(WB_STAGE_CONTRACT)" --rtl "$(WB_STAGE_DIFF_RTL)" --out-dir "$(OUT_DIR)/wb_stage/unit" --cycles "$(WB_STAGE_CYCLES)" --seed "$(WB_STAGE_RANDOM_SEED)"

mem-stage-contract:
	$(PYTHON) -I tools/mem_stage_gate.py contract --repo "." --contract "$(MEM_STAGE_CONTRACT)" --out-dir "$(OUT_DIR)/mem_stage/contract"

mem-stage-candidate-unit:
	$(PYTHON) -I tools/mem_stage_gate.py diff --repo "." --contract "$(MEM_STAGE_CONTRACT)" --rtl "$(MEM_STAGE_RTL)" --out-dir "$(OUT_DIR)/mem_stage/unit" --cycles "$(MEM_STAGE_CYCLES)" --seed "$(MEM_STAGE_RANDOM_SEED)"

exe-stage-negative-control:
	$(PYTHON) -I tools/exe_stage_diff.py --rtl "$(EXE_STAGE_RTL)" --profile "$(EXE_STAGE_PROFILE)" --out-dir "$(OUT_DIR)/exe_stage/$(EXE_STAGE_PROFILE)/negative-control" --negative-control

icache-contract:
	$(PYTHON) -I tools/icache_gate.py contract --contract "$(ICACHE_CONTRACT)" --out-dir "$(OUT_DIR)/icache/contract"

icache-candidate-unit:
	$(PYTHON) -I tools/icache_gate.py diff --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/unit" --cycles "$(ICACHE_CYCLES)"

dcache-contract:
	$(PYTHON) -I tools/dcache_gate.py contract --contract "$(DCACHE_CONTRACT)" --out-dir "$(OUT_DIR)/dcache/contract"

dcache-candidate-unit:
	$(PYTHON) -I tools/dcache_gate.py diff --contract "$(DCACHE_CONTRACT)" --rtl "$(DCACHE_RTL)" --out-dir "$(OUT_DIR)/dcache/unit" --cycles "$(DCACHE_CYCLES)"

replacement-reachability:
	$(PYTHON) -I tools/replacement_reachability.py --repo-root "." --manifest "reference/manifest.lock" --spec "reference/component-replacements/active-reachable.json" --metadata "reference/component-replacements/active-reachable.meta.json" --out-dir "$(OUT_DIR)/replacement-reachability"

chiplab-doctor:
	$(PYTHON) -I tools/refactor.py chiplab-doctor --out-dir "$(OUT_DIR)" --chiplab-ref "$(CHIPLAB_REFERENCE)" --tool-root "$(CHIPLAB_TOOL_ROOT)"

golden-export:
	$(PYTHON) -I tools/refactor.py golden-export --out-dir "$(OUT_DIR)"

chiplab-overlay:
	$(PYTHON) -I tools/refactor.py chiplab-overlay --out-dir "$(OUT_DIR)" --work-root "$(CHIPLAB_WORK_ROOT)" --iteration-id "$(ITERATION_ID)" --chiplab-ref "$(CHIPLAB_REFERENCE)" --tool-root "$(CHIPLAB_TOOL_ROOT)" --dut-source "$(DUT_SOURCE)" $(if $(REPLACEMENT_SPEC),--replacement-spec "$(REPLACEMENT_SPEC)",) $(if $(SOURCE_HEAD),--source-head "$(SOURCE_HEAD)",) $(DIAGNOSTIC_ARG)

rtl-smoke:
	$(PYTHON) -I tools/refactor.py rtl-smoke --out-dir "$(OUT_DIR)" --work-root "$(CHIPLAB_WORK_ROOT)" --iteration-id "$(ITERATION_ID)" --tool-root "$(CHIPLAB_TOOL_ROOT)" $(DIAGNOSTIC_ARG)

identity-compare:
	$(PYTHON) -I tools/identity_compare.py --out-dir "$(OUT_DIR)" --work-root "$(CHIPLAB_WORK_ROOT)" --chiplab-ref "$(CHIPLAB_REFERENCE)" --tool-root "$(CHIPLAB_TOOL_ROOT)" --locked-iteration-id "$(LOCKED_ITERATION_ID)" --mixed-iteration-id "$(MIXED_ITERATION_ID)"

evidence-check:
	$(PYTHON) -I tools/refactor.py validate-iteration --iteration-dir "logs/refactor/$(ITERATION_ID)"

test-automation:
	$(PYTHON) -I -m unittest discover -s tests -p "test_*.py"
