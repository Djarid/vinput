# Installing ONNX Runtime with Vitis AI Execution Provider

## Why a Separate Wheel?

The Vitis AI Execution Provider (EP) is AMD's proprietary NPU acceleration layer for ONNX Runtime. It's not available on PyPI because it requires:

- XDNA 2 NPU hardware (Strix Halo)
- AMD-specific driver integration (amdxdna kernel module)
- Vitis AI compiler toolchain
- Hardware-specific compilation

## Where to Get It

AMD distributes the Vitis AI wheel through their developer portal (requires free registration):

**Primary Source**: https://www.amd.com/en/developer/resources/ryzen-ai-software.html
**Docs (Linux guide)**: https://ryzenai.docs.amd.com/en/latest/linux.html

Navigate to: **Ryzen AI Software Platform** → **Downloads** → **ONNX Runtime with Vitis AI**

Look for: `onnxruntime_vitisai-1.17.0-cp310-cp310-linux_x86_64.whl`

**Alternative Sources**:
- GitHub Releases: https://github.com/amd/RyzenAI-SW/releases (check for ONNX Runtime wheels)
- AMD Support Site: https://www.amd.com/en/support

**Note**: AMD does not provide stable direct download URLs. You must download manually from the portal.

## Installation

### Recommended Method: Manual Download + Container Build

**Step 1**: Download the wheel from AMD Developer Portal

1. Visit: https://www.amd.com/en/developer/resources/ryzen-ai-software.html
2. Register/login (free)
3. Navigate to: **Ryzen AI Software Platform** → **Downloads**
4. Download: `onnxruntime_vitisai-1.17.0-cp310-cp310-linux_x86_64.whl`

**Step 2**: Place wheel in project root

```bash
# Copy downloaded wheel to vinput project directory
cp ~/Downloads/onnxruntime_vitisai-*.whl /home/jasonh/git/vinput/
```

**Step 3**: Build container (auto-detects and installs wheel)

```bash
podman-compose build
```

The Dockerfile will automatically detect the wheel and install it with NPU support enabled.

### Alternative Method: Install in Running Container

If you already have a built container without Vitis AI EP:

```bash
# Start container
podman-compose up -d

# Copy wheel into container
podman cp onnxruntime_vitisai-*.whl vinput-dev:/tmp/

# Install in container
podman exec -it vinput-dev bash
source /home/vinput/.venv/bin/activate
pip install /tmp/onnxruntime_vitisai-*.whl

# Verify installation
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
# Expected output: ['VitisAIExecutionProvider', 'CPUExecutionProvider', ...]
```

### Advanced Method: Build from Source

If you want to compile from source:

```bash
# Clone ONNX Runtime
git clone --recursive https://github.com/microsoft/onnxruntime.git
cd onnxruntime

# Build with Vitis AI EP
./build.sh --config Release \
    --use_vitisai \
    --build_wheel \
    --parallel \
    --skip_tests

# Install wheel
pip install build/Linux/Release/dist/onnxruntime_vitisai-*.whl
```

**Note**: Building from source requires Vitis AI development environment (XRT, Vitis AI library, etc.)

## Version Compatibility

Ensure your wheel matches:

| Component | Version |
|-----------|---------|
| Python | 3.10 |
| ONNX Runtime | 1.17.0 |
| XDNA Driver | 6.14+ kernel |
| Vitis AI | 3.5+ |

Mismatches may cause:
- Runtime errors
- NPU not detected
- Performance degradation
- Kernel panics

## Verification

After installation, verify NPU is accessible:

```bash
# Check ONNX Runtime providers
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"

# Check XDNA device
ls -l /dev/accel/accel0

# Check kernel module
lsmod | grep amdxdna

# Run test
python test_installation.py
```

Expected output should include:
- `VitisAIExecutionProvider` in available providers
- `/dev/accel/accel0` exists and is readable
- `amdxdna` kernel module loaded
- Test suite passes with NPU inference

## Fallback Behavior

If Vitis AI EP is not available, vinput automatically falls back to CPU inference:

```python
# In inference_engine.py
if 'VitisAIExecutionProvider' not in ort.get_available_providers():
    logger.warning("VitisAI EP not available, using CPU")
    providers = ['CPUExecutionProvider']
```

This allows development and testing without NPU hardware.

## Current Status (January 2026)

As of kernel 6.14+, XDNA 2 support is upstream in Linux mainline. AMD provides Vitis AI wheels through their developer portal:

- **Primary**: https://www.amd.com/en/developer/resources/ryzen-ai-software.html
- **GitHub**: https://github.com/amd/RyzenAI-SW (check releases for wheels)

**There are no stable direct download URLs.** Always download manually from AMD's portal and place in project root before building containers.

## Troubleshooting

### "VitisAIExecutionProvider not found"

```bash
# Check if wheel is actually installed
pip list | grep onnxruntime

# Reinstall if needed
pip uninstall onnxruntime onnxruntime-gpu onnxruntime-vitisai
pip install --no-deps /path/to/onnxruntime_vitisai-*.whl
```

### "No NPU device found"

```bash
# Check device node
ls -l /dev/accel/

# Check kernel module
sudo modprobe amdxdna

# Check dmesg for errors
dmesg | grep -i xdna
```

### Container can't access NPU

```bash
# Ensure device is passed to container
podman run --device /dev/accel/accel0 ...

# Or in compose.yaml:
devices:
  - /dev/accel/accel0:/dev/accel/accel0:rw
```

## License Notes

The Vitis AI Execution Provider may have different licensing than ONNX Runtime core. Check AMD's license terms when downloading from their portal.

vinput itself is GPL-3.0-or-later and can use any ONNX Runtime provider (CPU, Vitis AI, CUDA, etc.) as they are separate components.
