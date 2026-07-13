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
ICACHE_CONTRACT ?= reference/component-contracts/icache.json
ICACHE_CYCLES ?= 12000
ICACHE_GENERATE_DIR ?= $(OUT_DIR)/icache/generate
ICACHE_RTL ?= $(ICACHE_GENERATE_DIR)/rtl/icache.v
CORE_TOP_PORTS ?= reference/core-top.ports.json
CORE_TOP_GENERATE_DIR ?= $(OUT_DIR)/core_top/generate
CORE_TOP_WRAPPER_RTL ?= $(CORE_TOP_GENERATE_DIR)/rtl/core_top.v
CORE_TOP_PACKAGE_DIR ?= $(OUT_DIR)/core_top/package
CORE_TOP_RTL ?= $(CORE_TOP_PACKAGE_DIR)/rtl/mycpu_top.v
CORE_TOP_TRACKED_RTL ?= reference/component-replacements/mycpu_top.v
CORE_TOP_REPLACEMENT_SPEC ?= reference/component-replacements/core-top.json
LINT_WAIVERS ?= lint-waivers.yml

.PHONY: doctor scala-cache-bootstrap scala-check elaborate generate port-check lint yosys-check unit formal core-contract-check core-top-contract core-top-package core-top-publish-check mul-contract mul-golden-unit mul-candidate-unit div-contract div-golden-unit div-candidate-unit axi-bridge-contract axi-bridge-candidate-unit icache-contract icache-candidate-unit chiplab-doctor golden-export chiplab-overlay rtl-smoke identity-compare evidence-check test-automation

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
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.memory.GenerateOpenLa500ICache" --expected-module "icache" --expected-file "icache.v" --out-dir "$(OUT_DIR)/icache/elaborate" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py elaborate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/alu/elaborate" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected core_top, alu, mul, or div" >&2; exit 2
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
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/spinal_generate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --main-class "openla500.memory.GenerateOpenLa500ICache" --expected-module "icache" --expected-file "icache.v" --out-dir "$(ICACHE_GENERATE_DIR)" --runs 2 $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py generate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(ALU_GENERATE_DIR)" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected core_top, alu, mul, or div" >&2; exit 2
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
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/icache_gate.py port-check --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/port-check"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py port-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/port-check"
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected core_top, alu, mul, or div" >&2; exit 2
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
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/icache_gate.py lint --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/lint"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py lint --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/lint"
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected core_top, alu, mul, or div" >&2; exit 2
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
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/icache_gate.py yosys-check --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/yosys-check"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py yosys-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/yosys-check"
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected core_top, alu, mul, or div" >&2; exit 2
endif

unit:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_diff.py candidate --contract "$(MUL_CONTRACT)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/unit" --vector-count "$(MUL_VECTOR_COUNT)" --seed "$(MUL_RANDOM_SEED)"
else ifeq ($(TARGET),div)
	$(PYTHON) -I tools/div_diff.py candidate --contract "$(DIV_CONTRACT)" --manifest "reference/manifest.lock" --rtl "$(DIV_RTL)" --out-dir "$(OUT_DIR)/div/unit" --vector-count "$(DIV_VECTOR_COUNT)" --seed "$(DIV_RANDOM_SEED)"
else ifeq ($(TARGET),axi_bridge)
	$(PYTHON) -I tools/axi_bridge_gate.py diff --contract "$(AXI_BRIDGE_CONTRACT)" --rtl "$(AXI_BRIDGE_RTL)" --out-dir "$(OUT_DIR)/axi_bridge/unit" --cycles "$(AXI_BRIDGE_CYCLES)" --seed "$(AXI_BRIDGE_RANDOM_SEED)"
else ifeq ($(TARGET),icache)
	$(PYTHON) -I tools/icache_gate.py diff --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/unit" --cycles "$(ICACHE_CYCLES)"
else ifeq ($(TARGET),alu)
	$(PYTHON) -I tools/alu_gate.py unit --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/alu/unit" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else
	@echo "ERROR: unsupported TARGET=$(TARGET); expected alu, mul, or div" >&2; exit 2
endif

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

icache-contract:
	$(PYTHON) -I tools/icache_gate.py contract --contract "$(ICACHE_CONTRACT)" --out-dir "$(OUT_DIR)/icache/contract"

icache-candidate-unit:
	$(PYTHON) -I tools/icache_gate.py diff --contract "$(ICACHE_CONTRACT)" --rtl "$(ICACHE_RTL)" --out-dir "$(OUT_DIR)/icache/unit" --cycles "$(ICACHE_CYCLES)"

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
