#!/usr/bin/env python3
"""
init_project.py — Initialize a new Verilog digital design project.

Usage:
    python3 init_project.py [project_dir]

If project_dir is omitted, uses the current working directory.
The project name is derived from the directory basename.
Module / entity names follow the directory name (with underscores).

Creates:
    <project>/
    ├── rtl/
    ├── tb/
    ├── syn/
    ├── docs/
    ├── out/
    ├── skills/            → symlink to ~/.claude/skills (if exists)
    └── Makefile            ← from template, with MODULE/TOP/TOP_SYN filled in

Example:
    cd ~/work
    python3 ~/.claude/skills/verilog-design/scripts/init_project.py my_alu
    cd my_alu
    # create rtl/my_alu.v, tb/my_alu_tb.v, syn/synth_ics55.ys
    make allsyn
"""

import os
import sys
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Makefile template — variables marked with __PLACEHOLDER__ are filled in
# ---------------------------------------------------------------------------
MAKEFILE_TEMPLATE = """#=================================================================
# __MODULE__ — Verilog Design Flow (verilog-design skill)
#=================================================================
# Targets:
#   make lint     — slang + iverilog static check
#   make sim      — compile + run self-checking simulation
#   make verify   — VCD waveform auto-verification
#   make syn      — yosys synthesis → ics55 gate netlist
#   make wave     — open VCD in GTKWave
#   make all      — lint → compile → sim → verify
#   make allsyn   — lint → compile → sim → verify → syn
#   make clean    — remove generated files

RTL_DIR      = rtl
TB_DIR       = tb
OUT_DIR      = out
SYN_DIR      = syn
SKILL_DIR    = skills/verilog-design

MODULE       = __MODULE__
TOP          = __MODULE___tb
TOP_SYN      = __MODULE__

RTL          = $(RTL_DIR)/$(MODULE).v
TB           = $(TB_DIR)/$(MODULE)_tb.v
VCD_CHECK    = $(TB_DIR)/check_$(MODULE).py
SYN_SCRIPT   = $(SYN_DIR)/synth_ics55.ys
VVP          = $(OUT_DIR)/$(TOP).vvp
VCD          = $(OUT_DIR)/$(TOP).vcd
SYN_NETLIST  = $(OUT_DIR)/$(TOP_SYN)_syn.v

# ics55 liberty — bundled in skill, single source for all projects
LIB_STD      = ics55_LLSC_H7CH_typ_tt_1p2_25_nldm
LIB_FILE     = $(SKILL_DIR)/lib/$(LIB_STD).lib

IVL          = iverilog
VVP_RUN      = vvp
GTKWAVE      = gtkwave
SLANG        = slang
PYTHON       = python3
YOSYS        = yosys

IVL_FLAGS    = -g2012 -Wall -I$(RTL_DIR) -I$(TB_DIR) -o $(VVP)
YOSYS_FLAGS  = -Q -T

.PHONY: all allsyn lint compile sim verify syn wave clean

all: lint compile sim verify
	@echo ""
	@echo "============================================"
	@echo " FULL FLOW COMPLETE"
	@echo "============================================"

allsyn: lint compile sim verify syn
	@echo ""
	@echo "============================================"
	@echo " FULL FLOW + SYNTHESIS COMPLETE"
	@echo "============================================"

lint:
	@echo "============================================"
	@echo " LINT: Phase 3b — Static Syntax Check"
	@echo "============================================"
	@mkdir -p $(OUT_DIR)
	@echo "--- iverilog elaboration ---"
	@$(IVL) $(IVL_FLAGS) -tnull $(RTL) $(TB) 2>&1 | tee $(OUT_DIR)/lint.log
	@echo ""
	@if grep -qE "error|syntax error" $(OUT_DIR)/lint.log; then \
		echo "[LINT:iverilog] ERRORS FOUND"; \
		exit 1; \
	else \
		echo "[LINT:iverilog] Clean"; \
	fi
	@echo "--- slang static check ---"
	@$(SLANG) $(RTL) $(TB) 2>&1 | tee $(OUT_DIR)/slang.log; \
	if grep -q "Build succeeded: 0 errors, 0 warnings" $(OUT_DIR)/slang.log; then \
		echo "[LINT:slang] Clean — 0 errors, 0 warnings"; \
	else \
		echo "[LINT:slang] Issues found — review $(OUT_DIR)/slang.log"; \
		exit 1; \
	fi
	@echo "[LINT] Done"

compile:
	@echo "============================================"
	@echo " COMPILE: $(RTL) + $(TB)"
	@echo "============================================"
	@mkdir -p $(OUT_DIR)
	$(IVL) $(IVL_FLAGS) $(RTL) $(TB)
	@echo "[COMPILE] Done → $(VVP)"

sim: compile
	@echo "============================================"
	@echo " SIM: Running $(VVP)"
	@echo "============================================"
	@cd $(OUT_DIR) && $(VVP_RUN) ../$(VVP) 2>&1 | tee sim.log
	@if grep -q "ALL TESTS PASSED" $(OUT_DIR)/sim.log; then \
		echo "[SIM] *** ALL TESTS PASSED ***"; \
	else \
		echo "[SIM] *** SOME TESTS FAILED — check $(OUT_DIR)/sim.log ***"; \
	fi
	@echo "[SIM] VCD dumped → $(VCD)"

verify:
	@echo "============================================"
	@echo " VERIFY: VCD Waveform Auto-Verify"
	@echo "============================================"
	@if [ -f $(VCD_CHECK) ]; then \
		$(PYTHON) $(VCD_CHECK) $(VCD); \
	else \
		$(PYTHON) $(SKILL_DIR)/scripts/check_vcd.py $(VCD); \
	fi

syn:
	@echo "============================================"
	@echo " SYN: Phase 7 — Synthesis → ics55 netlist"
	@echo "============================================"
	@mkdir -p $(OUT_DIR)
	@if [ ! -f $(LIB_FILE) ]; then \
		echo "[SYN] ERROR: Liberty not found: $(LIB_FILE)"; \
		exit 1; \
	fi
	@echo "[SYN] Liberty: $(LIB_FILE)"
	@ln -sf $(LIB_FILE) $(LIB_STD).lib
	@$(YOSYS) $(YOSYS_FLAGS) -s $(SYN_SCRIPT) 2>&1 | tee $(OUT_DIR)/syn.log
	@if grep -q "Chip area" $(OUT_DIR)/syn.log; then \
		echo "[SYN] Synthesis complete → $(SYN_NETLIST)"; \
		grep -A2 "Chip area" $(OUT_DIR)/syn.log | head -4; \
	else \
		echo "[SYN] FAILED — review $(OUT_DIR)/syn.log"; \
		exit 1; \
	fi

wave:
	@echo "Opening $(VCD) in GTKWave..."
	@$(GTKWAVE) $(VCD) &
	@echo "[WAVE] GTKWave launched"

clean:
	rm -rf $(OUT_DIR)
	@echo "[CLEAN] Done"
"""

# ---------------------------------------------------------------------------
# Synthesis script template
# ---------------------------------------------------------------------------
SYN_TEMPLATE = """# __MODULE__ — Yosys Synthesis for ics55 (55nm)
read -sv rtl/__MODULE__.v
hierarchy -top __MODULE__

# High-level synthesis
proc; fsm; opt; memory; opt

# Map to internal cells
techmap; opt

# Map FFs → ics55
dfflibmap -liberty ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib

# Map logic → ics55
abc -liberty ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib

# Cleanup and report
clean; opt
write_verilog -noattr -noexpr -nohex out/__MODULE___syn.v
stat -liberty ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib
"""

# ---------------------------------------------------------------------------
# TB skeleton template
# ---------------------------------------------------------------------------
TB_SKELETON = """/**
 * __MODULE___tb — Self-checking testbench for __MODULE__
 */
`timescale 1ns / 1ps

module __MODULE___tb;

    parameter CLK_PERIOD = 10;

    reg clk;
    reg rst_n;

    // TODO: add DUT signals and instantiation

    // __MODULE__ dut (
    //     .clk   (clk),
    //     .rst_n (rst_n)
    // );

    // Clock
    initial begin
        clk = 1'b0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end

    // VCD dump
    initial begin
        $dumpfile("__MODULE___tb.vcd");
        $dumpvars(0, __MODULE___tb);
    end

    // Test stimulus
    integer test_pass, test_fail;
    initial begin
        test_pass = 0;
        test_fail = 0;

        // Reset
        rst_n = 1'b0;
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        $display("============================================");
        $display("[%0t] TESTBENCH START — __MODULE__", $time);
        $display("============================================");

        // TODO: add test cases

        // Summary
        $display("============================================");
        $display("[%0t] TESTBENCH COMPLETE", $time);
        $display("    Passed: %0d", test_pass);
        $display("    Failed: %0d", test_fail);
        $display("============================================");
        #100;
        if (test_fail > 0)
            $display("*** SOME TESTS FAILED ***");
        else
            $display("*** ALL TESTS PASSED ***");
        $finish;
    end

endmodule
"""


def init_project(project_dir):
    """Initialize a new Verilog design project."""
    project_path = Path(project_dir).resolve()
    project_name = project_path.name

    # Validate project name (alphanumeric + underscore, start with letter)
    if not project_name or not project_name[0].isalpha():
        print(f"ERROR: Project name '{project_name}' must start with a letter.")
        sys.exit(1)
    if not all(c.isalnum() or c == '_' for c in project_name):
        print(f"ERROR: Project name '{project_name}' may only contain [a-zA-Z0-9_].")
        sys.exit(1)

    print(f"Initializing project: {project_name}")
    print(f"Location: {project_path}")
    print()

    # Create directories
    dirs = ["rtl", "tb", "syn", "docs", "out"]
    for d in dirs:
        (project_path / d).mkdir(parents=True, exist_ok=True)
        print(f"  ✓  {d}/")

    # Symlink skills → global
    global_skills = Path.home() / ".claude" / "skills"
    skill_link = project_path / "skills"
    if global_skills.exists():
        if skill_link.exists() or skill_link.is_symlink():
            skill_link.unlink()
        skill_link.symlink_to(global_skills)
        print(f"  ✓  skills/ → {global_skills}")
    else:
        print(f"  ⚠  Global skills not found at {global_skills}")

    # Write Makefile
    makefile_content = MAKEFILE_TEMPLATE.replace("__MODULE__", project_name)
    makefile_path = project_path / "Makefile"
    makefile_path.write_text(makefile_content)
    print(f"  ✓  Makefile (MODULE={project_name})")

    # Write synthesis script
    syn_content = SYN_TEMPLATE.replace("__MODULE__", project_name)
    syn_path = project_path / "syn" / "synth_ics55.ys"
    syn_path.write_text(syn_content)
    print(f"  ✓  syn/synth_ics55.ys")

    # Write TB skeleton
    tb_content = TB_SKELETON.replace("__MODULE__", project_name)
    tb_path = project_path / "tb" / f"{project_name}_tb.v"
    tb_path.write_text(tb_content)
    print(f"  ✓  tb/{project_name}_tb.v (skeleton)")

    # Write empty RTL placeholder
    rtl_header = f"""/**
 * Module: {project_name}
 * Description: TODO
 * Author: -
 * Date: {Path.cwd().stat().st_mtime if False else 'TODO'}
 * Version: 0.1.0
 */

`timescale 1ns / 1ps

module {project_name} (
    input  clk,
    input  rst_n
    // TODO: add ports
);

    // TODO: implement

endmodule
"""
    rtl_path = project_path / "rtl" / f"{project_name}.v"
    rtl_path.write_text(rtl_header)
    print(f"  ✓  rtl/{project_name}.v (placeholder)")

    print()
    print("============================================")
    print(f" Project '{project_name}' ready!")
    print("============================================")
    print()
    print("Next steps:")
    print(f"  cd {project_path}")
    print(f"  1. Edit rtl/{project_name}.v — implement your design")
    print(f"  2. Edit tb/{project_name}_tb.v — add test cases")
    print(f"  3. make allsyn")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        project_dir = os.getcwd()

    init_project(project_dir)
