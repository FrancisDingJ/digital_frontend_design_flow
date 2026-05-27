---
name: Verilog Design Flow
description: Complete digital module design flow — spec → RTL → lint → simulate → VCD verify → synthesize. Covers Verilog/SystemVerilog with slang, iverilog/vvp, GTKWave, yosys, and PDK liberty mapping. Reusable Makefile-driven automation for any new module.
---

# Verilog Digital Module Design Flow (7 Phases)

## Quick Start — New Project

```bash
# One command to scaffold a new project
python3 ~/.claude/skills/verilog-design/scripts/init_project.py my_new_module

cd my_new_module
# 1. Edit rtl/my_new_module.v — implement your design
# 2. Edit tb/my_new_module_tb.v — add test cases
# 3. make allsyn
```

The script creates the full directory tree, a Makefile with `MODULE`/`TOP`/`TOP_SYN` pre-filled from the directory name, skeleton RTL/TB files, a synthesis script, and a symlink to the global skill.

## Directory Convention

```
<project>/
├── rtl/<module>.v              # RTL source
├── tb/<module>_tb.v            # Testbench
├── tb/check_<module>.py        # VCD auto-verify script
├── syn/synth_<pdk>.ys          # Yosys synthesis script (.ys NOT .tcl!)
├── docs/<module>_design.md     # Design spec
├── out/                        # Generated: .vvp .vcd .log _syn.v
├── Makefile                    # All targets (see below)
└── skills/verilog-design/      # This skill (bundle with PDK lib)
    ├── lib/<pdk>.lib           # Standard-cell liberty file (77 MB)
    ├── scripts/simulate.sh     # Simulator auto-detection
    ├── scripts/check_vcd.py    # VCD auto-verify script
    ├── references/vcd-analysis.md
    └── SKILL.md
```

> **PDK Library:** The ics55 standard-cell liberty (`ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib`, 747 cells)
> is bundled at `skills/verilog-design/lib/`. All projects reference this single copy.

## Makefile Targets Summary

| Target | Phase | Tools | Description |
|--------|-------|-------|-------------|
| `make lint` | 3b | slang + iverilog | Static syntax + elaboration check |
| `make compile` | 5 | iverilog | Compile RTL + TB → vvp |
| `make sim` | 5 | vvp | Run self-checking simulation |
| `make verify` | 6 | python3 | VCD waveform auto-verification |
| `make syn` | 7 | yosys + PDK | Synthesis → gate netlist |
| `make wave` | — | gtkwave | Open VCD waveform viewer |
| `make all` | 3b-6 | all above | lint → compile → sim → verify |
| `make allsyn` | 3b-7 | all above | lint → compile → sim → verify → syn |
| `make clean` | — | rm | Delete `out/` |

## Makefile Template (parametrized for reuse)

```makefile
#=================================================================
# <project> — Verilog Design Flow Makefile
# Set MODULE, TOP, TOP_SYN, PDK_DIR, LIB_FILE before use
#=================================================================
MODULE       = <module_name>
TOP          = <module_name>_tb
TOP_SYN      = <module_name>

RTL          = rtl/$(MODULE).v
TB           = tb/$(MODULE)_tb.v
VCD_CHECK    = tb/check_$(MODULE).py
SYN_SCRIPT   = syn/synth_<pdk>.ys
OUT_DIR      = out
VVP          = $(OUT_DIR)/$(TOP).vvp
VCD          = $(OUT_DIR)/$(TOP).vcd

# PDK Liberty — bundled in skill, single source for all projects
SKILL_DIR    = skills/verilog-design
LIB_FILE     = $(SKILL_DIR)/lib/ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib

IVL          = iverilog
SLANG        = slang
YOSYS        = yosys
GTKWAVE      = gtkwave

IVL_FLAGS    = -g2012 -Wall -Irtl -Itb -o $(VVP)
YOSYS_FLAGS  = -Q -T

.PHONY: all allsyn lint compile sim verify syn wave clean

all: lint compile sim verify

allsyn: lint compile sim verify syn

lint:
	@mkdir -p $(OUT_DIR)
	@echo "--- iverilog elaboration ---"
	@$(IVL) $(IVL_FLAGS) -tnull $(RTL) $(TB) 2>&1 | tee $(OUT_DIR)/lint.log
	@if grep -qE "error|syntax error" $(OUT_DIR)/lint.log; then exit 1; fi
	@echo "--- slang ---"
	@$(SLANG) $(RTL) $(TB) 2>&1 | tee $(OUT_DIR)/slang.log
	@grep -q "Build succeeded: 0 errors, 0 warnings" $(OUT_DIR)/slang.log

compile:
	@mkdir -p $(OUT_DIR)
	$(IVL) $(IVL_FLAGS) $(RTL) $(TB)

sim: compile
	@cd $(OUT_DIR) && $(VVP_RUN) ../$(VVP) 2>&1 | tee sim.log
	@grep -q "ALL TESTS PASSED" $(OUT_DIR)/sim.log

verify:
	@if [ -f $(VCD_CHECK) ]; then python3 $(VCD_CHECK) $(VCD); fi

syn:
	@mkdir -p $(OUT_DIR)
	@ln -sf $(LIB_FILE) $(notdir $(LIB_FILE))
	@$(YOSYS) $(YOSYS_FLAGS) -s $(SYN_SCRIPT) 2>&1 | tee $(OUT_DIR)/syn.log
	@grep -q "Chip area" $(OUT_DIR)/syn.log
	@echo "[SYN] Synthesis complete → $(OUT_DIR)/$(MODULE)_syn.v"

wave:
	@$(GTKWAVE) $(VCD) &

clean:
	rm -rf $(OUT_DIR)
```

## Yosys Synthesis Script Template (syn/synth_<pdk>.ys)

> **CRITICAL: Use `.ys` extension (NOT `.tcl`).** Yosys `.tcl` scripts run in TCL interpreter mode where `read -sv` fails with "can not find channel named -sv".

```tcl
# <module> — Yosys Synthesis for <PDK>
read -sv rtl/<module>.v
hierarchy -top <module>

# High-level: resolve processes, FSMs, memories
proc; fsm; opt; memory; opt

# Map to internal Yosys cells
techmap; opt

# Map flip-flops to ics55 sequential cells
dfflibmap -liberty ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib

# Map combinational logic to ics55 cells (ABC technology mapping)
abc -liberty ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib

# Cleanup and report
clean; opt
write_verilog -noattr -noexpr -nohex out/<module>_syn.v
stat -liberty ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib
```

## Full 7-Phase Design Flow

### Phase 1: Understand Requirements
1. Clarify: clock/reset strategy, interface signals, functionality, timing constraints
2. Confirm target: synthesis (FPGA/ASIC) or simulation only
3. Identify width/speed/area goals

### Phase 2: Write Design Spec
Create `docs/<module>_design.md` with:
- Module name, purpose, block diagram
- Port list (direction, width, description)
- Functional description + timing diagram
- Test scenarios checklist

### Phase 3: Implement RTL
1. **One-always-one-signal**: each signal in exactly one always block
2. Separate sequential (`@posedge clk`) and combinational (`@*`) logic
3. Avoid mixing `=` and `<=` in same block
4. Explicit reset for all sequential registers
5. `default` branch in all case statements
6. File header with version tracking (see template below)
7. Comment every key signal, always block, and complex logic

### Phase 3b: Static Check (`make lint`)
- `slang` — SystemVerilog syntax/type/reference checker
- `iverilog -Wall -tnull` — elaboration check
- Fix all errors before proceeding

### Phase 3c: Design Review Checklist
- [ ] slang: 0 errors, 0 warnings
- [ ] All sequential signals have explicit reset values
- [ ] No combinational logic loops
- [ ] No unintentional latches (all if/case branches assign)
- [ ] State machines have `default` case
- [ ] Vector widths match source ↔ destination
- [ ] No `=` in sequential blocks, no `<=` in combinational blocks
- [ ] `timescale directive present

### Phase 4: Write Testbench (`tb/<module>_tb.v`)
- Clock: `always #(CLK_PERIOD/2) clk = ~clk;`
- Reset stimulus (hold low ≥ 2 cycles)
- VCD dump: `$dumpfile` + `$dumpvars`
- **Self-checking**: compare outputs to expected values
- 10 test scenarios covering: single beat, burst (INCR/WRAP/FIXED), back-to-back, error injection
- **Handshake timing**: source channels sample data AFTER `@(posedge clk)` handshake completes; sink channels sample data ON the `valid=1` cycle BEFORE the next `@(posedge clk)`
- `$display` for pass/fail; `$finish` at end
- Print `*** ALL TESTS PASSED ***` on success (used by make sim check)

### Phase 5: Simulate (`make sim`)
- Compile: `iverilog -g2012 -Wall -Irtl -Itb -o out/<top>.vvp`
- Run: `vvp out/<top>.vvp`
- Check output for `ALL TESTS PASSED`

### Phase 6: VCD Waveform Auto-Verify (`make verify`)
- Use `tb/check_<module>.py` with vcdvcd library
- Verify: state machine sequence, APB/AXI protocol timing, burst address sequence, error propagation
- Install dependency: `pip3 install vcdvcd`

### Phase 7: Synthesis (`make syn`)
- Yosys flows: proc → fsm → opt → memory → techmap → dfflibmap → abc → clean
- Requires PDK `.lib` file (NLDM or CCS Liberty format)
- Output: `out/<module>_syn.v` (gate netlist), area/timing report

## AXI BFM Handshake Convention

```
SOURCE channel (AW, W, AR — TB is master):
  1. valid = 1 (blocking =)
  2. while (!ready) @(posedge clk);   // wait for slave ready
  3. @(posedge clk);                  // let DUT latch via NBA
  4. valid = 0;                       // deassert

SINK channel (B, R — TB is slave):
  1. ready = 1
  2. while (!valid) @(posedge clk);   // wait for master valid
  3. sample_data = rdata/rresp/etc;   // sample NOW (combinational)
  4. @(posedge clk);                  // let DUT advance state
```

## File Header Template

```verilog
/**
 * Module: <module_name>
 * Description: <brief>
 * Author: <name>
 * Date: <YYYY-MM-DD>
 * Version: <major>.<minor>.<patch>
 *
 * Changelog:
 *   v1.0.0 - <date> - Initial release
 *
 * Parameters:
 *   - PARAM: <desc> (default: <val>)
 *
 * Ports:
 *   - clk / rst_n: Clock and async reset
 */
```

## Common Pitfalls

| Issue | Fix |
|-------|-----|
| Latch inference | Ensure all `if`/`case` branches assign in combinational blocks |
| Missing reset | Add explicit reset in sequential always blocks |
| Race: TB samples X data | Sample sink data BEFORE `@(posedge clk)` that advances state |
| Race: DUT misses handshake | For source, keep valid=1 through the `@(posedge clk)` after ready |
| `yosys -c` fails on `.tcl` | Use `.ys` extension + `-s` flag (native script mode) |
| `read -sv` fails in TCL mode | Rename script to `.ys`, use `-s` not `-c` |
| VCD not generated | Ensure `$dumpfile()` before `$dumpvars()` |

## External Tools

| Tool | Command | Purpose |
|------|---------|---------|
| **init_project.py** | `python3 <skill>/scripts/init_project.py <name>` | Scaffold new project |
| slang | `slang file1.v file2.v` | SystemVerilog static checker |
| Icarus Verilog | `iverilog -g2012 -Wall` | Verilog compiler |
| VVP | `vvp <file>.vvp` | Simulation runtime |
| GTKWave | `gtkwave dump.vcd` | Waveform viewer |
| Yosys | `yosys -s script.ys` | Logic synthesis |
| Python vcdvcd | `pip3 install vcdvcd` | VCD waveform analysis |
