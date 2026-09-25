.PHONY: clean all install

PROJECT ?= $(basename $(firstword $(wildcard *.kicad_pro)))
PROJECT_ROOT ?= $(CURDIR)
BUILD_SCRIPTS ?= $(PROJECT_ROOT)/scripts
BUILD_DIR ?= $(PROJECT_ROOT)/build
ifeq ($(PROJECT),)
	$(error No .kicad_pro file found. Set PROJECT=<name> explicitly)
endif

KICAD_SCH ?= $(PROJECT_ROOT)/$(PROJECT).kicad_sch
KICAD_PCB ?= $(PROJECT_ROOT)/$(PROJECT).kicad_pcb
LICENSE	  ?= $(PROJECT_ROOT)/LICENSE-CC-BY-SA

$(info KiCad Schematic: $(KICAD_SCH))
$(info KiCad PCB:       $(KICAD_PCB))
$(info Project License: $(LICENSE))

ERC                 := $(BUILD_DIR)/erc.json
BOM                 := $(BUILD_DIR)/bom.csv
DRC                 := $(BUILD_DIR)/drc.json
STATS               := $(BUILD_DIR)/stats.json
SCH_PDF             := $(BUILD_DIR)/schematic.pdf
STEP                := $(BUILD_DIR)/alidade.step
CUTTER_LEFT         := $(BUILD_DIR)/cutter_left.dxf
CUTTER_RIGHT        := $(BUILD_DIR)/cutter_right.dxf
STEP_LEFT           := $(BUILD_DIR)/alidade_left.step
STEP_RIGHT          := $(BUILD_DIR)/alidade_right.step

OUTPUTS := \
	$(ERC) \
	$(BOM) \
	$(DRC) \
	$(STATS) \
	$(PDF) \
	$(STEP) \
	$(CUTTER_RIGHT) \
	$(CUTTER_LEFT) \
	$(STEP_LEFT) \
	$(STEP_RIGHT) \

all: $(OUTPUTS)

###########
# SCH_PDF #
###########
SCH_PDF_FLAGS ?=
$(SCH_PDF): $(KICAD_SCH)
	@mkdir -p $(dir $@)
	@kicad-cli sch export pdf -o $@ $(PDF_FLAGS) $<

#######
# ERC #
#######
ERC_FLAGS ?= --format json
$(ERC): $(KICAD_SCH)
	@mkdir -p $(dir $@)
	@kicad-cli sch erc -o $@ $(ERC_FLAGS) $<

#######
# BOM #
#######
BOM_FLAGS ?= --group-by Value
$(BOM): $(KICAD_SCH)
	@mkdir -p $(dir $@)
	@kicad-cli sch export bom -o $@ $(BOM_FLAGS) $<

#######
# DRC #
#######
DRC_FLAGS ?= --format json --schematic-parity
$(DRC): $(KICAD_PCB)
	@mkdir -p $(dir $@)
	@kicad-cli pcb drc -o $@ $(DRC_FLAGS) $<

#########
# STATS #
#########
STATS_FLAGS ?= --format json
$(STATS): $(KICAD_PCB)
	@mkdir -p $(dir $@)
	@kicad-cli pcb export stats -o $@ $(STATS_FLAGS) $<

########
# STEP #
########
STEP_FLAGS ?= --grid-origin --include-tracks --include-pads --include-silkscreen --include-soldermask
$(STEP): $(KICAD_PCB)
	@mkdir -p $(dir $@)
	@kicad-cli pcb export step -o $@ $(STEP_FLAGS) $<

###########
# CUTTERS #
###########
CUTTER_FLAGS ?= 
CUTTER_SCRIPT = $(BUILD_SCRIPTS)/cookicad_cutter.py
CUTTER_LEFT_LAYER ?= "Eco1.User"
CUTTER_RIGHT_LAYER ?= "Eco2.User"
$(CUTTER_LEFT) $(CUTTER_RIGHT) &: $(KICAD_PCB) $(CUTTER_SCRIPT)
	@mkdir -p $(dir $@)
	@python3 $(CUTTER_SCRIPT) gen $< -l $(CUTTER_LEFT_LAYER) $(CUTTER_LEFT)
	@python3 $(CUTTER_SCRIPT) gen $< -l $(CUTTER_RIGHT_LAYER) $(CUTTER_RIGHT)

$(STEP_LEFT) $(STEP_RIGHT) &: $(STEP) $(CUTTER_LEFT) $(CUTTER_RIGHT) $(CUTTER_SCRIPT)
	@mkdir -p $(dir $@)
	@freecadcmd $(CUTTER_SCRIPT) cut $(STEP) $(CUTTER_LEFT) $(STEP_LEFT) 


###########
# Install #
###########
PREFIX ?= /usr/local
DATAROOTDIR ?= $(PREFIX)/share
DATADIR ?= $(DATAROOTDIR)/$(PROJECT)
DESTDIR ?=

INSTALL_DIR := $(DESTDIR)$(DATADIR)

install: $(OUTPUTS) $(LICENSE)
	@install -d $(INSTALL_DIR)
	@install -D -m 0644 $^ $(INSTALL_DIR)

#########
# Clean #
#########
clean:
	@echo "Cleaning $(BUILD_DIR)"
	@rm -r $(BUILD_DIR)
