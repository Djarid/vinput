# vinput - Quick Start Guide

## ⚡ FASTEST: Containerized Deployment (3 min)

**Recommended for isolation and exact version pinning.**

```bash
cd /home/jasonh/git/vinput
podman-compose build   # 2 min (first time only)
podman-compose up      # 1 min to start
```

That's it! The container handles:
- ✅ All Python dependencies (exact pinned versions)
- ✅ Whisper model setup
- ✅ ONNX Runtime configuration
- ✅ Virtual Xbox controller
- ✅ Audio and uinput device access

Done. Skip to "Testing" below.

For full container guide, see [CONTAINERIZATION.md](CONTAINERIZATION.md).

---

## Manual Setup: Validation + Native Development (5 min)

**Only needed for direct hardware development on Strix Halo.**

### 1. Validate Host Environment (1 min)

```bash
cd /home/jasonh/git/vinput
chmod +x setup/setup_strix_env.sh
./setup/setup_strix_env.sh
```

This checks:
- ✓ Linux kernel 6.14+
- ✓ amdxdna driver
- ✓ uinput device
- ✓ Podman/Docker installed

**⚠️ Important**: This doesn't include `onnxruntime` with Vitis AI support. You need AMD's custom wheel:

1. Download from: https://www.amd.com/en/developer/resources/ryzen-ai-software.html
2. Install: `pip install onnxruntime_vitis_ai_*.whl`

### 4. Install ONNX Runtime with Vitis AI (manual)

```bash
# Download custom wheel from AMD Developer Lounge
pip install ./onnxruntime_vitisai-*.whl
```

### 5. Download Models (1 min)

```bash
mkdir -p models/
# Download from: https://huggingface.co/amd/NPU-Whisper-Base-Small
# Place encoder_int8.onnx and decoder_int8.onnx in models/
```

### 6. Test Installation (1 min)

```bash
python test_installation.py
```

Shows:
- ✓ Dependencies OK
- ✓ Audio engine working
- ✓ Virtual controller accessible
- ✓ System environment ready

## Running vinput

### From Container (Recommended)

```bash
podman-compose up
```

App is ready to listen for voice commands.

### From Native Setup

```bash
# Activate virtualenv first
source /home/jasonh/git/vinput/.venv/bin/activate

# Run application
python src/main.py
``````bash
python src/main.py
```

You'll see:
```
INFO - VinputOrchestrator initialized
INFO - Virtual controller initialized
INFO - Inference engine initialized
INFO - Audio capture started
INFO - Listening for speech...
```

Then try voice commands:
- **"jump"** → Xbox A button
- **"move forward"** → Left stick forward
- **"fire"** → RB trigger (1 sec hold)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `amdxdna not loaded` | Update kernel: `sudo pacman -Syu` |
| `/dev/uinput: Permission denied` | Run: `./setup/setup_strix_env.sh` |
| `VitisAI provider not found` | Install AMD's onnxruntime wheel |
| `No model files found` | Download from Hugging Face, place in `models/` |
| `No audio detected` | Check microphone: `python -c "import sounddevice; sounddevice.query_devices()"` |

## Customize Commands

Edit `config/commands.yaml`:

```yaml
commands:
  jump:
    type: button
    button: A
    duration: 50
  
  reload:
    type: button
    button: X
    duration: 50
  
  sprint forward:
    type: sequence
    actions:
      - type: button
        button: A
        duration: 500
      - type: stick
        stick: left
        x: 0
        y: -32768
        duration: 2000
```

## Architecture

```
Microphone → Audio Engine (VAD) → Preprocessing 
                              ↓
                        Whisper NPU
                              ↓
                        Command Parser
                              ↓
                    Virtual Xbox Controller → Wayland
```

## Next Steps

1. **Optimize latency**: Adjust sounddevice block size in `src/audio_engine.py`
2. **Add more commands**: Expand `config/commands.yaml`
3. **Handle more models**: Swap encoder/decoder ONNX files
4. **Debug**: Check logs in console output

## Performance Metrics

- **Audio capture**: < 1ms (sounddevice callback)
- **VAD detection**: ~20ms per frame
- **Preprocessing**: < 10ms (padding/truncation)
- **NPU inference**:
  - Cold start: 3-5s (firmware load)
  - Warm start: 100-300ms per utterance
- **Command execution**: < 50ms (uinput event)

**Total latency** (speech to game input): 150-400ms after NPU warmup

## References

- [Full README.md](README.md) - Comprehensive documentation
- [.copilot_instructions](.copilot_instructions) - Architecture details
- [AMD Ryzen AI](https://www.amd.com/en/developer/resources/ryzen-ai-software.html)

---

**Enjoy voice-controlled computing on Strix Halo! 🎮🎤**
