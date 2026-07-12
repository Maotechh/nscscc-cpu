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
LINT_WAIVERS ?= lint-waivers.yml

.PHONY: doctor scala-cache-bootstrap scala-check elaborate generate port-check lint yosys-check unit formal mul-contract mul-golden-unit mul-candidate-unit div-contract div-golden-unit div-candidate-unit chiplab-doctor golden-export chiplab-overlay rtl-smoke identity-compare evidence-check test-automation

doctor:
	$(PYTHON) -I tools/refactor.py doctor --out-dir "$(OUT_DIR)" $(if $(VIVADO_HOME),--vivado-home "$(VIVADO_HOME)",)

scala-cache-bootstrap:
	$(PYTHON) -I tools/bootstrap_scala_cache.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --cache-root "$(SCALA_CACHE_ROOT)" --lock-out "reference/scala-dependencies.lock.json"

scala-check:
	$(PYTHON) -I tools/scala_gate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/scala-check" $(if $(SBT),--sbt "$(SBT)",) $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)

elaborate:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py elaborate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/mul/elaborate" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else
	$(PYTHON) -I tools/alu_gate.py elaborate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/alu/elaborate" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
endif

generate:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py generate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(MUL_GENERATE_DIR)" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
else
	$(PYTHON) -I tools/alu_gate.py generate --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(ALU_GENERATE_DIR)" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
endif

port-check:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py port-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/port-check"
else
	$(PYTHON) -I tools/alu_gate.py port-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/port-check"
endif

lint:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py lint --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/lint"
else
	$(PYTHON) -I tools/alu_gate.py lint --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/lint"
endif

yosys-check:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py yosys-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/yosys-check"
else
	$(PYTHON) -I tools/alu_gate.py yosys-check --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/yosys-check"
endif

unit:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_diff.py candidate --contract "$(MUL_CONTRACT)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/unit" --vector-count "$(MUL_VECTOR_COUNT)" --seed "$(MUL_RANDOM_SEED)"
else
	$(PYTHON) -I tools/alu_gate.py unit --target "$(TARGET)" --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/alu/unit" $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)
endif

formal:
ifeq ($(TARGET),mul)
	$(PYTHON) -I tools/mul_gate.py formal --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(MUL_RTL)" --out-dir "$(OUT_DIR)/mul/formal"
else
	$(PYTHON) -I tools/alu_gate.py formal --target "$(TARGET)" --manifest "reference/manifest.lock" --rtl "$(ALU_RTL)" --out-dir "$(OUT_DIR)/alu/formal"
endif

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
