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

.PHONY: doctor scala-cache-bootstrap scala-check chiplab-doctor golden-export chiplab-overlay rtl-smoke identity-compare evidence-check test-automation

doctor:
	$(PYTHON) -I tools/refactor.py doctor --out-dir "$(OUT_DIR)" $(if $(VIVADO_HOME),--vivado-home "$(VIVADO_HOME)",)

scala-cache-bootstrap:
	$(PYTHON) -I tools/bootstrap_scala_cache.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --cache-root "$(SCALA_CACHE_ROOT)" --lock-out "reference/scala-dependencies.lock.json"

scala-check:
	$(PYTHON) -I tools/scala_gate.py --manifest "reference/manifest.lock" --spinal-dir "spinal" --tool-root "$(CHIPLAB_TOOL_ROOT)" --out-dir "$(OUT_DIR)/scala-check" $(if $(SBT),--sbt "$(SBT)",) $(if $(JAVA_HOME),--java-home "$(JAVA_HOME)",)

chiplab-doctor:
	$(PYTHON) -I tools/refactor.py chiplab-doctor --out-dir "$(OUT_DIR)" --chiplab-ref "$(CHIPLAB_REFERENCE)" --tool-root "$(CHIPLAB_TOOL_ROOT)"

golden-export:
	$(PYTHON) -I tools/refactor.py golden-export --out-dir "$(OUT_DIR)"

chiplab-overlay:
	$(PYTHON) -I tools/refactor.py chiplab-overlay --out-dir "$(OUT_DIR)" --work-root "$(CHIPLAB_WORK_ROOT)" --iteration-id "$(ITERATION_ID)" --chiplab-ref "$(CHIPLAB_REFERENCE)" --tool-root "$(CHIPLAB_TOOL_ROOT)" --dut-source "$(DUT_SOURCE)" $(if $(REPLACEMENT_SPEC),--replacement-spec "$(REPLACEMENT_SPEC)",) $(if $(SOURCE_HEAD),--source-head "$(SOURCE_HEAD)",) $(DIAGNOSTIC_ARG)

rtl-smoke:
	$(PYTHON) -I tools/refactor.py rtl-smoke --out-dir "$(OUT_DIR)" --work-root "$(CHIPLAB_WORK_ROOT)" --iteration-id "$(ITERATION_ID)" --tool-root "$(CHIPLAB_TOOL_ROOT)" $(DIAGNOSTIC_ARG)

identity-compare:
	$(PYTHON) -I tools/identity_compare.py --out-dir "$(OUT_DIR)" --locked-iteration-id "$(LOCKED_ITERATION_ID)" --mixed-iteration-id "$(MIXED_ITERATION_ID)"

evidence-check:
	$(PYTHON) -I tools/refactor.py validate-iteration --iteration-dir "logs/refactor/$(ITERATION_ID)"

test-automation:
	$(PYTHON) -I -m unittest discover -s tests -p "test_*.py"
