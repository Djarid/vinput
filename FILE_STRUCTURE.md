# vinput Project Structure

## Complete File Listing

```
vinput/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── audio_engine.py          # Audio capture, VAD, preprocessing
│   ├── inference_engine.py      # ONNX Runtime, Whisper, Vitis AI
│   ├── input_engine.py          # Virtual Xbox controller via uinput
│   └── main.py                  # Async orchestrator (main entry point)
│
├── config/
│   ├── commands.yaml            # Voice command mappings (20+ examples)
│   └── vaip_config.json         # Vitis AI compiler settings
│
├── setup/
│   ├── setup_strix_env.sh       # Environment validation script
│   └── 99-uinput.rules          # udev rules for /dev/uinput
│
├── models/                      # (directory for ONNX models)
│   ├── encoder_int8.onnx        # (to be downloaded)
│   └── decoder_int8.onnx        # (to be downloaded)
│
├── Documentation
│   ├── README.md                # Complete reference (520+ lines)
│   ├── QUICKSTART.md            # 5-minute setup guide
│   ├── BUILD_SUMMARY.md         # Build information
│   ├── FILE_STRUCTURE.md        # This file
│   └── .copilot_instructions    # Architecture spec for GitHub Copilot
│
├── Utilities
│   ├── requirements.txt          # Python dependencies
│   ├── test_installation.py     # Validation suite
│   └── .gitignore               # Git ignore patterns
│
└── Existing Documentation
    └── Python AI Automation... # Original Gemini research report
```

## File Statistics

| Component | Files | Lines | Purpose |
|-----------|-------|-------|---------|
| Core Python Modules | 5 | ~1,240 | Audio, inference, input, orchestrator |
| Configuration | 2 | ~90 | Commands, Vitis AI settings |
| Setup & Build | 2 | ~110 | Environment setup, udev rules |
| Tests & Utilities | 3 | ~270 | Installation validation, dependencies |
| Documentation | 6+ | ~1,700+ | Guides, architecture, reference |
| **TOTAL** | **~20** | **~3,400+** | **Complete prototype** |

## Quick File Guide

### To Get Started
1. Read: **QUICKSTART.md** (5 minutes)
2. Run: **setup/setup_strix_env.sh** (environment validation)
3. Test: **test_installation.py** (installation check)
4. Run: **src/main.py** (start the system)

### To Understand Architecture
- **README.md** - Complete reference documentation
- **.copilot_instructions** - Technical architecture spec

### To Customize
- **config/commands.yaml** - Add your voice commands here
- **config/vaip_config.json** - Vitis AI compiler tuning

### To Develop
- **src/audio_engine.py** - Audio capture and preprocessing
- **src/inference_engine.py** - Model inference wrapper
- **src/input_engine.py** - Virtual controller implementation
- **src/main.py** - Main orchestrator and event loop

## Key Statistics

- **Total Python Code**: ~1,240 lines (5 modules)
- **Total Documentation**: ~1,700+ lines
- **Configuration Files**: 2 (YAML, JSON)
- **Shell Scripts**: 1 setup script
- **Example Commands**: 20+ predefined voice commands
- **Test Coverage**: 4-part validation suite

## Dependencies

**Python Packages**:
- numpy
- sounddevice
- webrtcvad
- evdev
- pyyaml
- onnxruntime (with Vitis AI EP)

**System**:
- Linux kernel 6.14+
- amdxdna kernel module
- /dev/uinput device
- libinput

## Typical Workflow

```
1. Clone repo
   ↓
2. Run ./setup/setup_strix_env.sh
   ↓
3. pip install -r requirements.txt
   ↓
4. Download models to models/
   ↓
5. python test_installation.py
   ↓
6. Edit config/commands.yaml (optional)
   ↓
7. python src/main.py
   ↓
8. Say voice commands!
```

---

For details, see **README.md** or **QUICKSTART.md**
