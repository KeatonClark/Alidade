.PHONY: clean all install 

PROJECT ?= $(basename $(firstword $(wildcard *.kicad_pro)))
PROJECT_ROOT ?= $(CURDIR)
BUILD_SCRIPTS ?= $(PROJECT_ROOT)/scripts
BUILD_DIR ?= $(PROJECT_ROOT)/build
ifeq ($(PROJECT),)
	$(error No .kicad_pro file found. Set PROJECT=<name> explicitly)
endif

KICAD_SCH ?= $(wildcard $(PROJECT_ROOT)/*.kicad_sch)
KICAD_PCB ?= $(PROJECT_ROOT)/$(PROJECT).kicad_pcb
LICENSE	  ?= $(PROJECT_ROOT)/LICENSE-CC-BY-SA

$(info KiCad Schematics: $(KICAD_SCH))
$(info KiCad PCB:        $(KICAD_PCB))
$(info Project License:  $(LICENSE))

DRC                 := $(BUILD_DIR)/pcb/drc.json
STATS               := $(BUILD_DIR)/pcb/stats.json
ERC                 := $(BUILD_DIR)/sch/erc.json
SCH_PDF             := $(BUILD_DIR)/sch/schematic.pdf
BOM                 := $(BUILD_DIR)/sch/bom.csv
STEP                := $(BUILD_DIR)/3d/alidade.step
CUTTER_LEFT         := $(BUILD_DIR)/3d/cutter_left.dxf
CUTTER_RIGHT        := $(BUILD_DIR)/3d/cutter_right.dxf
STEP_LEFT           := $(BUILD_DIR)/3d/alidade_left.step
STEP_RIGHT          := $(BUILD_DIR)/3d/alidade_right.step
GLB                 := $(BUILD_DIR)/3d/alidade.glb
GLB_LEFT            := $(BUILD_DIR)/3d/alidade_left.glb
GLB_RIGHT           := $(BUILD_DIR)/3d/alidade_right.glb

OUTPUTS_SCH := \
	$(ERC) \
	$(PDF) \
	$(BOM) \

OUTPUTS_PCB := \
	$(DRC) \
	$(STATS) \

OUTPUTS_3D := \
	$(STEP) \
	$(CUTTER_RIGHT) \
	$(CUTTER_LEFT) \
	$(STEP_LEFT) \
	$(STEP_RIGHT) \
	$(GLB) \
	$(GLB_LEFT) \
	$(GLB_RIGHT) \

OUTPUTS := \
	   $(OUTPUTS_SCH) \
	   $(OUTPUTS_PCB) \
	   $(OUTPUTS_3D) \

all: $(OUTPUTS)

###########
# SCH_PDF #
###########
SCH_PDF_FLAGS ?=
$(SCH_PDF): $(KICAD_SCH)
	@mkdir -p $(dir $@)
	@echo "Exporting Schematic"
	@kicad-cli sch export pdf -o $@ $(PDF_FLAGS) $<

#######
# ERC #
#######
ERC_FLAGS ?= --format json
$(ERC): $(KICAD_SCH)
	@mkdir -p $(dir $@)
	@echo "Running ERC"
	@kicad-cli sch erc -o $@ $(ERC_FLAGS) $<

#######
# BOM #
#######
BOM_FLAGS ?= --group-by Value
$(BOM): $(KICAD_SCH)
	@mkdir -p $(dir $@)
	@echo "Generating BOM"
	@kicad-cli sch export bom -o $@ $(BOM_FLAGS) $<

#######
# DRC #
#######
DRC_FLAGS ?= --format json --schematic-parity
$(DRC): $(KICAD_PCB)
	@mkdir -p $(dir $@)
	@echo "Running DRC"
	@kicad-cli pcb drc -o $@ $(DRC_FLAGS) $<

#########
# STATS #
#########
STATS_FLAGS ?= --format json
$(STATS): $(KICAD_PCB)
	@mkdir -p $(dir $@)
	@echo "Exporting PCB Statistics"
	@kicad-cli pcb export stats -o $@ $(STATS_FLAGS) $<

########
# STEP #
########
STEP_FLAGS ?= --grid-origin --include-tracks --include-pads --include-silkscreen --include-soldermask
$(STEP): $(KICAD_PCB)
	@mkdir -p $(dir $@)
	@echo "Exporting PCB 3D Model"
	@kicad-cli pcb export step -o $@ $(STEP_FLAGS) $<

###########
# CUTTERS #
###########
CUTTER_FLAGS ?= 
CUTTER_SCRIPT = $(BUILD_SCRIPTS)/cookicad_cutter.py
CUTTER_LEFT_LAYER ?= "Eco1.User"
CUTTER_RIGHT_LAYER ?= "Eco2.User"
$(CUTTER_LEFT): $(KICAD_PCB) $(CUTTER_SCRIPT)
	@mkdir -p $(dir $@)
	@echo "Extracting Left Outline from $(CUTTER_LEFT_LAYER)"
	@python3 $(CUTTER_SCRIPT) gen $< -l $(CUTTER_LEFT_LAYER) $@

$(CUTTER_RIGHT): $(KICAD_PCB) $(CUTTER_SCRIPT)
	@mkdir -p $(dir $@)
	@echo "Extracting Right Outline from $(CUTTER_RIGHT_LAYER)"
	@python3 $(CUTTER_SCRIPT) gen $< -l $(CUTTER_RIGHT_LAYER) $@

$(STEP_LEFT): $(STEP) $(CUTTER_LEFT) $(CUTTER_SCRIPT)
	@mkdir -p $(dir $@)
	@echo "Cutting Left Model"
	@QT_QPA_PLATFORM=offscreen freecad $(CUTTER_SCRIPT) --pass cut --pass $(STEP) --pass $(CUTTER_LEFT) --pass $@ 2>&1 > /dev/null

$(STEP_RIGHT): $(STEP) $(CUTTER_LEFT) $(CUTTER_RIGHT) $(CUTTER_SCRIPT)
	@mkdir -p $(dir $@)
	@echo "Cutting Right Model"
	@QT_QPA_PLATFORM=offscreen freecad $(CUTTER_SCRIPT) --pass cut --pass $(STEP) --pass $(CUTTER_RIGHT) --pass $@ 2>&1 > /dev/null

#######
# GLB #
#######
%.glb: %.step $(CUTTER_SCRIPT)
	@mkdir -p $(dir $@)
	@echo "Converting $< to $@"
	@QT_QPA_PLATFORM=offscreen freecad $(CUTTER_SCRIPT) --pass glb --pass $< --pass $@ 2>&1 > /dev/null

###########
# Install #
###########
PREFIX ?= /usr/local
DATAROOTDIR ?= $(PREFIX)/share
DATADIR ?= $(DATAROOTDIR)/$(PROJECT)
DESTDIR ?=

INSTALL_DIR := $(DESTDIR)$(DATADIR)
.PHONY: install_sch install_pcb install_lic install_3d

install_lic: $(LICENSE)
	@install -d $(INSTALL_DIR)
	@install -m 0644 $(LICENSE) $(INSTALL_DIR) 

install_3d: $(OUTPUTS_3D)
	@install -d $(INSTALL_DIR)/3d
	@install -m 0644 $^ $(INSTALL_DIR)/3d

install_sch: $(OUTPUTS_SCH) $(KICAD_SCH)
	@install -d $(INSTALL_DIR)/sch
	@install -m 0644 $^ $(INSTALL_DIR)/sch

install_pcb: $(OUTPUTS_PCB) $(KICAD_PCB)
	@install -d $(INSTALL_DIR)/pcb
	@install -m 0644 $^ $(INSTALL_DIR)/pcb

install: $(OUTPUTS) install_sch install_pcb install_lic install_3d

#########
# Clean #
#########
clean:
	@echo "Cleaning $(BUILD_DIR)"
	@rm -r $(BUILD_DIR)
