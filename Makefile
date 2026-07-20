SHELL := bash

PYTHON ?= python3
SBT ?= sbt
VIVADO_HOME ?= D:/Xilinx/Vivado/2023.2
VIVADO ?= $(VIVADO_HOME)/bin/vivado.bat
CORE_TOP_LINT_PROFILE ?= locked
CORE_TOP_LINT_WAIVERS ?= reference/core-top-lint-waivers.json
OUT_DIR ?= build
CORE_TOP_RAW_DIR ?= $(OUT_DIR)/core_top/raw
CORE_TOP_PACKAGE_DIR ?= $(OUT_DIR)/core_top/package
CORE_TOP_RAW_RTL ?= $(CORE_TOP_RAW_DIR)/core_top.v
CORE_TOP_RTL ?= $(CORE_TOP_PACKAGE_DIR)/rtl/mycpu_top.v
CORE_TOP_SYNTH_DIR ?= $(OUT_DIR)/vivado/core_top

.PHONY: all scala test python-test generate-raw package-core generate-core generate port-check lint yosys-check publish-check vivado-synth clean

all: scala test generate-core python-test

scala:
	cd spinal && $(SBT) -batch 'Compile / compile' 'Test / compile'

test:
	cd spinal && $(SBT) -batch test

python-test:
	$(PYTHON) -I -m unittest discover -s tests -p 'test_*.py'

generate-raw:
	rm -rf "$(CORE_TOP_RAW_DIR)"
	mkdir -p "$(CORE_TOP_RAW_DIR)"
	cd spinal && $(SBT) -batch 'runMain openla500.compat.GenerateCoreTopCompat --out-dir ../$(CORE_TOP_RAW_DIR)'

package-core: generate-raw
	rm -rf "$(CORE_TOP_PACKAGE_DIR)"
	$(PYTHON) -I tools/core_top_gate.py package --repo-root . --manifest reference/manifest.lock --ports reference/core-top.ports.json --rtl "$(CORE_TOP_RAW_RTL)" --out-dir "$(CORE_TOP_PACKAGE_DIR)"
	rm -rf rtl
	mkdir -p rtl
	cp "$(CORE_TOP_RTL)" rtl/mycpu_top.v

generate-core: package-core

generate: generate-core

port-check: generate-core
	rm -rf "$(OUT_DIR)/core_top/port-check"
	$(PYTHON) -I tools/core_top_gate.py port-check --repo-root . --manifest reference/manifest.lock --ports reference/core-top.ports.json --rtl "$(CORE_TOP_RTL)" --out-dir "$(OUT_DIR)/core_top/port-check"

lint: generate-core
	rm -rf "$(OUT_DIR)/core_top/lint"
	$(PYTHON) -I tools/core_top_gate.py lint --repo-root . --manifest reference/manifest.lock --ports reference/core-top.ports.json --rtl "$(CORE_TOP_RTL)" --out-dir "$(OUT_DIR)/core_top/lint" --environment-profile "$(CORE_TOP_LINT_PROFILE)" $(if $(CORE_TOP_LINT_WAIVERS),--waivers "$(CORE_TOP_LINT_WAIVERS)",)

yosys-check: generate-core
	rm -rf "$(OUT_DIR)/core_top/yosys-check"
	$(PYTHON) -I tools/core_top_gate.py yosys-check --repo-root . --manifest reference/manifest.lock --ports reference/core-top.ports.json --rtl "$(CORE_TOP_RTL)" --out-dir "$(OUT_DIR)/core_top/yosys-check"

publish-check: generate-core
	rm -rf "$(OUT_DIR)/core_top/publish-check"
	$(PYTHON) -I tools/core_top_gate.py publish-check --repo-root . --manifest reference/manifest.lock --ports reference/core-top.ports.json --rtl "$(CORE_TOP_RTL)" --tracked-rtl rtl/mycpu_top.v --replacement-spec reference/component-replacements/core-top.json --out-dir "$(OUT_DIR)/core_top/publish-check"

vivado-synth: generate-core
	rm -rf "$(CORE_TOP_SYNTH_DIR)"
	"$(VIVADO)" -mode batch -source tools/ooo_core_top_synth.tcl -tclargs "$(CORE_TOP_RTL)" "$(CORE_TOP_SYNTH_DIR)"

clean:
	rm -rf build spinal/target
