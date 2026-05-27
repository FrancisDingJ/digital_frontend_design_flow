# Digital Frontend Design Flow

**Complete Verilog/SystemVerilog digital module design flow** — from RTL spec through simulation, waveform verification, and synthesis to gate-level netlist.

One command to scaffold. One command to run the full pipeline.

---

## Features

| Phase | Command | Description |
|-------|---------|-------------|
| **Init** | `python3 scripts/init_project.py <name>` | One-command project scaffolding |
| **Lint** | `make lint` | Static syntax check — **slang** + **iverilog** |
| **Simulate** | `make sim` | Compile + run self-checking testbench — **iverilog/vvp** |
| **Verify** | `make verify` | Automated VCD waveform checking — **Python vcdvcd** |
| **Synthesize** | `make syn` | Map RTL to standard cells — **Yosys + ABC** |
| **Wave** | `make wave` | Visual waveform debugging — **GTKWave** |
| **Full flow** | `make allsyn` | lint → sim → verify → syn in one shot |

### 7-Phase Methodology

```
Phase 1-2: Requirements → Design Spec (docs/*.md)
Phase 3:   RTL Implementation (one-always-one-signal style)
Phase 3b:  Static Check — slang + iverilog (0 errors, 0 warnings)
Phase 3c:  Design Review Checklist (11 items)
Phase 4:   Self-checking Testbench (10 test scenarios)
Phase 5:   Simulation — iverilog + vvp
Phase 6:   VCD Waveform Auto-Verification — Python vcdvcd
Phase 7:   Synthesis — Yosys → gate-level netlist + area report
```

---

## Quick Start

```bash
# 1. Clone and scaffold your project
git clone https://github.com/FrancisDingJ/digital_frontend_design_flow.git
python3 digital_frontend_design_flow/scripts/init_project.py my_alu

# 2. Write your RTL and testbench
cd my_alu
vim rtl/my_alu.v
vim tb/my_alu_tb.v

# 3. Run the full pipeline
make allsyn
```

---

## Project Structure

```
digital_frontend_design_flow/
├── SKILL.md                        # Complete methodology reference
├── README.md                       # This file
├── lib/
│   └── ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib  # 747 cells, 55nm (77 MB)
├── scripts/
│   ├── init_project.py             # New project scaffolding
│   ├── simulate.sh                 # Simulator auto-detection
│   └── check_vcd.py                # VCD waveform auto-verification
└── references/
    └── vcd-analysis.md             # Python VCD analysis API reference
```

### Generated Project Structure

```
my_alu/
├── rtl/my_alu.v                    # Your RTL
├── tb/my_alu_tb.v                  # Your testbench
├── syn/synth_ics55.ys              # Yosys synthesis script
├── docs/                           # Design documents
├── out/                            # .vvp .vcd .log _syn.v
├── skills/ → ~/.claude/skills      # Symlink to global skill
└── Makefile                        # All targets
```

---

## Standard Cell Library

The **ics55 55nm** standard cell library is bundled in `lib/`:

| Property | Value |
|----------|-------|
| Process | 55nm (ICsprout ICScape55) |
| Cells | 747 (combinational + sequential) |
| Corner | typ_tt_1p2_25 (typical, 1.2V, 25°C) |
| Format | NLDM Liberty (.lib) |
| Size | 77 MB |
| Source | [openecos-projects/icsprout55-pdk](https://github.com/openecos-projects/icsprout55-pdk) |

> **Using your own library:** Replace `lib/ics55_LLSC_H7CH_typ_tt_1p2_25_nldm.lib` with your `.lib` file,
> then update `LIB_STD` in the Makefile (or the synth `.ys` script) to match the new filename.

---

## EDA Tools

| Tool | Version | Purpose | Source |
|------|---------|---------|--------|
| **slang** | v11+ | SystemVerilog static checker | [MikePopoloski/slang](https://github.com/MikePopoloski/slang) |
| **Icarus Verilog** | 12+ | Verilog compiler + simulator | [steveicarus/iverilog](https://github.com/steveicarus/iverilog) |
| **Yosys** | 0.45+ | RTL synthesis | [YosysHQ/yosys](https://github.com/YosysHQ/yosys) |
| **GTKWave** | 3.3+ | VCD waveform viewer | [gtkwave/gtkwave](https://github.com/gtkwave/gtkwave) |
| **vcdvcd** | 2.6+ | Python VCD parsing | [SanDisk-Open-Source/vcdvcd](https://github.com/SanDisk-Open-Source/vcdvcd) |

### PDK / Standard Cell Library

| Resource | Source |
|----------|--------|
| ics55 55nm PDK | [openecos-projects/icsprout55-pdk](https://github.com/openecos-projects/icsprout55-pdk) |

---

## Installation

### macOS

```bash
# System dependencies
brew install cmake bison

# slang (SystemVerilog static checker)
git clone https://github.com/MikePopoloski/slang.git
cd slang && cmake -B build && cmake --build build -j
cp build/bin/slang ~/.local/bin/

# Icarus Verilog
brew install icarus-verilog

# Yosys (with GNU Bison)
export PATH="/opt/homebrew/opt/bison/bin:$PATH"
git clone https://github.com/YosysHQ/yosys.git
cd yosys && git submodule update --init
make config-clang && make -j$(sysctl -n hw.ncpu)
make install PREFIX=$HOME/.local

# GTKWave
brew install gtkwave

# Python VCD analysis
pip3 install vcdvcd

# GitHub CLI (optional)
brew install gh
```

### Linux (Ubuntu/Debian)

```bash
# System dependencies
sudo apt-get update
sudo apt-get install -y build-essential cmake bison flex \
    gperf libreadline-dev libffi-dev libbz2-dev python3 python3-pip

# slang
git clone https://github.com/MikePopoloski/slang.git
cd slang && cmake -B build && cmake --build build -j
sudo cp build/bin/slang /usr/local/bin/

# Icarus Verilog
sudo apt-get install -y iverilog

# Yosys
git clone https://github.com/YosysHQ/yosys.git
cd yosys && git submodule update --init
make config-gcc && make -j$(nproc)
sudo make install

# GTKWave
sudo apt-get install -y gtkwave

# Python VCD analysis
pip3 install vcdvcd
```

### Windows (WSL2 recommended)

```powershell
# Install WSL2 Ubuntu, then follow Linux instructions above.
# All tools work natively under WSL2.

# Alternatively, for native Windows:
# - Icarus Verilog: https://bleyer.org/icarus/ (pre-built installer)
# - GTKWave: https://gtkwave.sourceforge.net/ (pre-built installer)
# - Yosys: Use WSL2 (no native Windows build)
# - slang: Use WSL2 (no native Windows build)
```

---

## Makefile Targets

```bash
make lint        # Static check (slang + iverilog)
make compile     # Compile RTL + TB → vvp
make sim         # Run simulation
make verify      # VCD waveform auto-verification
make syn         # Yosys synthesis → gate netlist
make wave        # Open VCD in GTKWave
make all         # lint → compile → sim → verify
make allsyn      # lint → compile → sim → verify → syn
make clean       # Remove generated files
```

---

## Example Output

```
============================================
 LINT: Phase 3b — Static Syntax Check
 [LINT:slang] Clean — 0 errors, 0 warnings
============================================
 SIM: Phase 5 — Running out/my_alu_tb.vvp
 *** ALL TESTS PASSED *** (10/10)
============================================
 VERIFY: Phase 6 — VCD Waveform Auto-Verify
 VCD VERIFICATION: ALL 4 CHECKS PASSED
============================================
 SYN: Phase 7 — Synthesis → ics55 netlist
 Chip area for module '\my_alu': 26334.56
  of which sequential: 5801.88 (22.03%)
============================================
 FULL FLOW + SYNTHESIS COMPLETE
============================================
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

The bundled ics55 standard cell library is from [openecos-projects/icsprout55-pdk](https://github.com/openecos-projects/icsprout55-pdk) (Apache 2.0).
