# vinput: Voice-Driven Automation for AMD Strix Halo

A cutting-edge voice automation system that translates natural speech into system input events via Linux uinput, powered by the XDNA 2 Neural Processing Unit in AMD Strix Halo.

## Overview

**vinput** combines:
- **Real-time audio capture** with voice activity detection (VAD)
- **On-device speech recognition** using quantized Whisper running on the NPU
- **Kernel-level input emulation** via Linux uinput for Wayland compatibility
- **Async architecture** to prevent audio buffer underruns and input latency

Perfect for hands-free gaming, application control, and accessibility on modern Linux systems.

## System Requirements

### Hardware
- **AMD Strix Halo** (MS-S1) with **Ryzen AI Max** processor
- **XDNA 2 Neural Processing Unit** (required)
- Microphone input (3.5mm or USB audio device)

### Operating System
- **CachyOS** (Arch Linux optimized for x86-64-v4)
- Kernel **6.14 or newer** (required for amdxdna driver)
- Wayland or X11 display server

### Python
- Python 3.9+

## Installation

**Choose your setup method:**

### ✅ Recommended: Containerized (Podman)

For complete **isolation** and **exact version pinning**, use containers:

```bash
cd /path/to/vinput
podman-compose build
podman-compose up
```

This approach:
- ✅ Guarantees exact versions (no system Python conflicts)
- ✅ Isolates all dependencies completely
- ✅ Requires zero Python virtualenv management
- ✅ Works on any Linux system

See [CONTAINERIZATION.md](CONTAINERIZATION.md) for full guide.

### ⚠️ Advanced: Native Development

For development on the hardware itself, manual setup required:

#### 1. Validate Host Environment

```bash
chmod +x setup/setup_strix_env.sh
./setup/setup_strix_env.sh
```

This validates:
- ✓ Linux kernel version (6.14+)
- ✓ amdxdna module loaded
- ✓ NPU firmware present
- ✓ uinput device access
- ✓ Podman/Docker availability

### 2. Create Virtual Environment (Manual)

```bash
python3 -m venv /path/to/vinput/.venv
source /path/to/vinput/.venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Version Management**: All packages are pinned to exact versions based on the white paper specifications. See [requirements.txt](requirements.txt) for detailed constraints and rationale.

**ONNX Runtime with Vitis AI**: The standard `pip install onnxruntime` does NOT include the Vitis AI Execution Provider. You must install AMD's custom wheel:

1. Visit: https://www.amd.com/en/developer/resources/ryzen-ai-software.html
2. Download the ONNX Runtime wheel with Vitis AI support for Linux
3. Install with: `pip install <wheel_file>`

### 3. Download Quantized Whisper Models

Download the Int8-quantized Whisper models from AMD's Model Zoo:

```bash
mkdir -p models/
# Download encoder and decoder from Hugging Face:
# https://huggingface.co/amd/NPU-Whisper-Base-Small

# Place the ONNX files in:
# models/encoder_int8.onnx
# models/decoder_int8.onnx
```

### 4. Configure Voice Commands

Edit `config/commands.yaml` to define your voice commands. Examples:

```yaml
commands:
  jump:
    type: button
    button: A
    duration: 50
  
  crouch:
    type: button
    button: B
    duration: 2000
  
  move forward:
    type: stick
    stick: left
    x: 0
    y: -32768
    duration: 1000
```

## Usage

### Basic Start

```bash
python src/main.py
```

The system will:
1. Initialize the virtual Xbox 360 controller
2. Load quantized Whisper models into ONNX Runtime
3. Warm up the NPU (first inference loads firmware)
4. Begin listening for voice commands

### Example Commands

Once running, try:
- **"jump"** → Xbox A button press
- **"move forward"** → Left stick forward (Y = -32768)
- **"fire"** → RB trigger hold (1 second)
- **"combo attack"** → X + Y + A sequence

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Microphone (sounddevice callback)                           │
└─────────────────────────────────────────────────────────────┘
           ↓ (Thread-safe asyncio.Queue)
┌─────────────────────────────────────────────────────────────┐
│ Audio Engine                                                │
│ • VAD (Voice Activity Detection)                            │
│ • Accumulate frames while speaking                          │
│ • Preprocess: pad/truncate to 480,000 samples              │
│ • Ensure contiguous memory for DMA                          │
└─────────────────────────────────────────────────────────────┘
           ↓ (ThreadPoolExecutor.run_in_executor)
┌─────────────────────────────────────────────────────────────┐
│ Inference Engine (NPU)                                      │
│ • Whisper Encoder → mel-spectrogram features               │
│ • Whisper Decoder → token sequence                          │
│ • Vitis AI Execution Provider handles XDNA 2               │
└─────────────────────────────────────────────────────────────┘
           ↓ (Text transcription)
┌─────────────────────────────────────────────────────────────┐
│ Command Parser                                              │
│ • Match transcription against commands.yaml                 │
│ • Support exact and partial matches                         │
└─────────────────────────────────────────────────────────────┘
           ↓ (Action dictionary)
┌─────────────────────────────────────────────────────────────┐
│ Input Engine (uinput)                                       │
│ • Virtual Xbox 360 Controller (uinput)                      │
│ • Emit kernel-level input events                            │
│ • Wayland compositor receives as physical device            │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### commands.yaml

Define voice commands as a mapping:

```yaml
commands:
  <voice_phrase>:
    type: <action_type>
    <action_params>
```

**Action Types**:

| Type | Params | Description |
|------|--------|-------------|
| `button` | `button`, `duration` | Press and release button (duration in ms) |
| `stick` | `stick`, `x`, `y`, `duration` | Move stick to (x,y) and hold |
| `trigger` | `trigger`, `value` | Set trigger value (0-255) |
| `dpad` | `direction` | Move D-Pad (up/down/left/right/etc) |
| `sequence` | `actions` | Execute multiple actions in order |

**Button Names**: A, B, X, Y, LB, RB, Back, Start, Guide, L3, R3

**Stick Names**: left, right

**Trigger Names**: left, right

**Directions**: up, down, left, right, up-left, up-right, down-left, down-right, center

### vaip_config.json

Vitis AI compiler configuration (advanced users):

```json
{
  "model_type": "int8",
  "target_device": "amdxdna",
  "compiler_flags": {
    "enable_context_caching": true,
    "optimization_level": 3
  }
}
```

## Troubleshooting

### "amdxdna kernel module not loaded"

**Solution**: Upgrade kernel to 6.14+
```bash
sudo pacman -Syu
```

### "Device not found" (XRT error)

**Cause**: amdxdna and XRT versions mismatch

**Solution**: Rebuild xrt-plugin-amdxdna
```bash
yay -S xrt-plugin-amdxdna --rebuild
```

### No /dev/accel/accel0

**Cause**: NPU device not recognized by driver

**Solution**: Check firmware and kernel module
```bash
ls /lib/firmware/amdnpu/17f0*.bin
lsmod | grep amdxdna
dmesg | grep amdxdna
```

### "Vitis AI Execution Provider not found"

**Cause**: Standard onnxruntime installed instead of Vitis AI wheel

**Solution**: Install AMD's custom ONNX Runtime wheel
1. Download from AMD developer site
2. `pip uninstall onnxruntime`
3. `pip install <custom_wheel>`

### Virtual controller not visible in Steam

**Cause**: udev rule not applied or wrong permissions

**Solution**:
```bash
sudo systemctl restart udev
ls -la /dev/uinput  # Check permissions
sudo usermod -a -G input $USER
newgrp input
```

Also ensure controller is created **before** launching Steam.

### Stick drift in games

**Cause**: Incorrect AbsInfo axis ranges in uinput

**Solution**: The code sets ranges correctly (-32768 to 32767). If drift persists:
1. Check with `evtest` to verify axis ranges
2. Rebuild evdev package

### "IOMMU fault" or silent CPU fallback

**Cause**: Input tensors not contiguous in memory

**Solution**: Already handled in code (uses `np.ascontiguousarray()`). If issue persists:
1. Check XLNX_VART_FIRMWARE is set
2. Verify audio preprocessing in audio_engine.py

## Performance Tips

### Reduce Latency

1. **NPU Warm-up**: First inference runs dummy input to load firmware. Subsequent calls are faster.

2. **Block Size**: 1024-2048 frames (~60-120ms) balances latency and CPU overhead
   - Smaller = lower latency, higher CPU
   - Larger = higher latency, lower CPU

3. **Context Caching**: Enabled in vaip_config.json. First run compiles model, subsequent runs load cached binary.

4. **Threading**: Audio capture runs in sounddevice callback thread; inference offloaded to ThreadPoolExecutor to prevent GIL blocking.

### Monitor Performance

```bash
# Check NPU utilization
xrt-smi examine

# Monitor audio buffer
# Add logging in audio_engine.py

# Check inference timing
# Look at console output for "Transcription time"
```

## Advanced Usage

### Custom Audio Devices

Edit `audio_engine.py`:
```python
self._stream = sd.InputStream(
    device=<device_id>,  # Use sounddevice.query_devices() to list
    samplerate=self.sample_rate,
    ...
)
```

### Fine-Tune VAD Sensitivity

```python
self.vad = webrtcvad.Vad(vad_mode)  # 0=least aggressive, 3=most
```

### Modify Whisper Models

To use larger Whisper models (base-small, medium, large):
1. Download corresponding quantized ONNX models from AMD
2. Update model paths in main.py

## Known Limitations

1. **Static Audio Shape**: All audio must be padded/truncated to 480,000 samples (30 seconds at 16kHz) due to XDNA 2 compiler constraints.

2. **ONNX Operators**: Some operators may not be supported by Vitis AI EP and will fall back to CPU. Monitor provider output.

3. **Latency**: First inference on cold NPU ~3-5 seconds (firmware load). Subsequent ~100-200ms.

4. **Model Precision**: Only Int8 and BF16 quantized models are officially supported for XDNA 2.

## Development Notes

### Project Structure

```
vinput/
├── src/
│   ├── audio_engine.py         # Audio capture, VAD, preprocessing
│   ├── inference_engine.py     # ONNX Runtime, Whisper, Vitis AI EP
│   ├── input_engine.py         # uinput virtual controller
│   └── main.py                 # Async orchestrator
├── config/
│   ├── commands.yaml           # Voice command mappings
│   ├── vaip_config.json        # Vitis AI compiler settings
├── setup/
│   ├── setup_strix_env.sh      # Environment setup script
│   └── 99-uinput.rules         # udev rules
├── models/
│   ├── encoder_int8.onnx       # (to be downloaded)
│   └── decoder_int8.onnx       # (to be downloaded)
├── requirements.txt
└── README.md
```

### Adding New Components

Each engine follows a pattern:
1. `__init__()` - Initialize with config
2. `initialize()` - Load resources
3. `async method()` - Main operation
4. `shutdown()` - Cleanup

## Testing

vinput includes comprehensive unit tests for all components. **Always run tests in containers to avoid version conflicts.**

### Run Tests

```bash
# Run all tests (containerized - safe)
podman-compose run --rm vinput-test

# Run specific test file
podman-compose run --rm vinput-test pytest tests/test_audio_engine.py

# With coverage report
podman-compose run --rm vinput-test pytest --cov=src --cov-report=html
```

See [TESTING.md](TESTING.md) for complete testing guide.

**⚠️ WARNING**: Do NOT install `requirements-dev.txt` in your production environment! Test dependencies may conflict with pinned runtime versions and cause hardware failures.

### Manual Installation Validation

To verify your installation works:

```bash
python test_installation.py
```

This runs integration tests without mocks (requires hardware access).

## Contributing

Contributions welcome! Areas of interest:
- Additional model backends (beyond Whisper)
- Mouse automation support
- Keyboard input via uinput
- Persistent command learning
- GUI for command configuration

## References

- [AMD Ryzen AI Software](https://www.amd.com/en/developer/resources/ryzen-ai-software.html)
- [Vitis AI Execution Provider](https://fs-eire.github.io/onnxruntime/docs/execution-providers/Vitis-AI-ExecutionProvider.html)
- [Linux uinput Documentation](https://www.kernel.org/doc/html/latest/input/uinput.html)
- [WebRTC VAD](https://github.com/wiseman/py-webrtcvad)
- [evdev (python)](https://python-evdev.readthedocs.io/)

## License

MIT License - See LICENSE file

## Support

For issues specific to:
- **NPU/XDNA 2**: See [AMD RyzenAI-SW Issues](https://github.com/amd/RyzenAI-SW/issues)
- **Arch Linux**: Visit [Arch Linux Forums](https://bbs.archlinux.org/)
- **CachyOS**: Visit [CachyOS Community](https://discuss.cachyos.org/)
- **vinput**: Open an issue in this repository

---

**vinput** - Voice-in, Input-out. Built for the future of AI-powered heterogeneous computing.
