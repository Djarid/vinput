# Containerization Guide for vinput

## Overview

This guide covers deployment of vinput using **Podman** and **Podman Compose** - a rootless, daemonless container solution preferred in the Linux community.

## Why Containerization?

The white paper emphasizes specific versions for:
- Kernel amdxdna module (6.14+)
- Python runtime (3.9-3.11)
- ONNX Runtime with Vitis AI EP
- Pinned dependency versions

Containerization ensures:
- **Reproducibility**: Exact versions every time
- **Isolation**: No conflicts with system Python
- **Portability**: Same container on different machines
- **Consistency**: Development = production environment

## Podman vs Docker

**Why Podman?** (preferred for Linux developers)
- ✅ Rootless by default (more secure)
- ✅ No daemon required (simple, clean)
- ✅ Docker-compatible (same image format)
- ✅ Better suited for local development
- ✅ OCI standard (future-proof)

**Docker compatibility**: This setup works with both! Just replace `podman` with `docker` commands if needed.

## Installation

### Podman Installation

**Arch Linux / CachyOS:**
```bash
sudo pacman -S podman podman-compose
```

**Ubuntu/Debian:**
```bash
sudo apt install podman podman-compose
```

**Fedora:**
```bash
sudo dnf install podman podman-compose
```

### Verify Installation

```bash
podman --version
podman-compose --version
```

## Building the Container

### Option 1: Using Podman Compose (Recommended)

```bash
cd /path/to/vinput
podman-compose build
```

This builds according to `compose.yaml` configuration.

### Option 2: Direct Podman Build

```bash
podman build -t vinput:latest .
```

### Build with Custom Tags

```bash
podman build -t vinput:0.1.0 -t vinput:latest .
```

## Running vinput in Container

### Option 1: Podman Compose (Recommended)

```bash
cd /path/to/vinput
podman-compose up
```

Stop with:
```bash
podman-compose down
```

### Option 2: Direct Podman Run

```bash
podman run --rm -it \
  --device /dev/uinput \
  --device /dev/input \
  --device /dev/snd \
  --device /dev/accel/accel0 \
  -v $(pwd):/home/vinput/vinput:rw \
  -v $(pwd)/models:/home/vinput/vinput/models:rw \
  -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
  -v /run/user/1000/pulse:/run/user/1000/pulse:ro \
  vinput:latest
```

## Device Access (Critical!)

### Required Devices

| Device | Purpose | Permission |
|--------|---------|-----------|
| `/dev/uinput` | Virtual input emulation | rw |
| `/dev/input/*` | Input event devices | ro |
| `/dev/snd/*` | Audio devices (ALSA/PulseAudio) | rw |
| `/dev/accel/accel0` | NPU (XDNA 2) | rw |

### Podman Device Mapping

In `compose.yaml`:
```yaml
devices:
  - /dev/uinput:/dev/uinput:rw
  - /dev/input:/dev/input:ro
  - /dev/snd:/dev/snd:rw
  - /dev/accel/accel0:/dev/accel/accel0:rw  # Strix Halo only
```

### Audio Configuration

PulseAudio or ALSA sound requires special handling in containers:

**For PulseAudio:**
```bash
-v /run/user/1000/pulse:/run/user/1000/pulse:ro \
-e PULSE_SERVER=unix:/run/user/1000/pulse/native
```

**For ALSA (direct):**
```bash
--device /dev/snd:/dev/snd:rw
```

## Container Architecture

### Image Specification

- **Base**: `archlinux:latest`
- **Python**: 3.10 (recommended for stability)
- **User**: Non-root `vinput` user (security best practice)
- **Virtual Env**: Created at `/home/vinput/.venv`
- **Size**: ~1.2 GB (with dependencies)

### Volumes

| Mount | Type | Purpose |
|-------|------|---------|
| `.` → `/home/vinput/vinput` | rw | Project directory |
| `./models` → `./models` | rw | ONNX models (persistent) |
| `vinput-cache` | named | ONNX runtime cache |
| `/run/user/1000/pulse` | ro | Audio socket |

## Version Matrix

### Tested Configurations

| Component | Version | Status |
|-----------|---------|--------|
| Linux Kernel | 6.14+ | ✅ Required |
| Python | 3.10 | ✅ Recommended |
| numpy | 1.24.3 | ✅ Pinned |
| sounddevice | 0.4.6 | ✅ Pinned |
| webrtcvad | 2.0.10 | ✅ Pinned |
| evdev | 1.5.0 | ✅ Pinned |
| ONNX Runtime | Latest Vitis AI | ⚠️ Manual install |
| Vitis AI EP | Latest | ⚠️ From AMD |
| XRT | Latest | ⚠️ From AUR |

### ONNX Runtime Installation in Container

The Dockerfile does NOT include ONNX Runtime (requires separate wheel from AMD).

**Option 1: Pre-install on host, mount to container**
```bash
pip download onnxruntime_vitisai-*.whl
podman cp onnxruntime_vitisai-*.whl vinput-dev:/home/vinput/
podman exec vinput-dev pip install /home/vinput/onnxruntime_vitisai-*.whl
```

**Option 2: Extend Dockerfile**
Create custom `Dockerfile.custom`:
```dockerfile
FROM vinput:latest
COPY onnxruntime_vitisai-*.whl /tmp/
RUN . ~/.venv/bin/activate && \
    pip install /tmp/onnxruntime_vitisai-*.whl
```

Build:
```bash
podman build -f Dockerfile.custom -t vinput:with-onnx .
```

## Common Tasks

### Verify Version Isolation (Important!)

Ensure the container is using its own packages, not host Python:

```bash
# This should show container versions (1.24.3, 0.4.6, etc.)
podman-compose exec vinput python -c "import numpy; import sounddevice; print(f'numpy: {numpy.__version__}'); print(f'sounddevice: {sounddevice.__version__}')"

# Verify Python path points to container virtualenv
podman-compose exec vinput which python
# Should output: /home/vinput/.venv/bin/python

# Run full version validation
podman-compose exec vinput python test_installation.py
```

If any versions don't match requirements.txt, rebuild:
```bash
podman-compose down
podman-compose build --no-cache
podman-compose up
```

### Test Installation

```bash
podman-compose exec vinput python test_installation.py
```

### View Logs

```bash
podman-compose logs -f vinput
```

### Access Container Shell

```bash
podman-compose exec vinput /bin/bash
```

### Install/Upgrade Packages

```bash
podman-compose exec vinput pip install --upgrade <package>
```

### Download Whisper Models

```bash
podman-compose exec vinput bash -c '\
  wget https://huggingface.co/amd/NPU-Whisper-Base-Small/resolve/main/encoder_int8.onnx -O models/encoder_int8.onnx && \
  wget https://huggingface.co/amd/NPU-Whisper-Base-Small/resolve/main/decoder_int8.onnx -O models/decoder_int8.onnx
'
```

### Run Custom Command

```bash
podman-compose exec vinput python src/main.py
```

## Troubleshooting

### "Permission denied" on /dev/uinput

**Cause**: uinput device permissions

**Solution**: Add udev rule (host side)
```bash
sudo tee /etc/udev/rules.d/99-uinput.rules << EOF
KERNEL=="uinput", SUBSYSTEM=="misc", OPTIONS+="static_node=uinput", TAG+="uaccess"
EOF
sudo systemctl restart udev
```

### Audio not working in container

**Cause**: PulseAudio socket path mismatch

**Solution**: Check your XDG_RUNTIME_DIR
```bash
echo $XDG_RUNTIME_DIR
# Should be /run/user/1000 or similar
```

Update `compose.yaml` with correct path:
```yaml
environment:
  PULSE_SERVER: unix:$XDG_RUNTIME_DIR/pulse/native
```

### NPU device not found

**Cause**: Container running on non-Strix Halo system

**Solution**: Disable in `compose.yaml`:
```yaml
devices:
  # Comment out:
  # - /dev/accel/accel0:/dev/accel/accel0:rw
```

Or use environment check in Dockerfile.

### ONNX Runtime Vitis AI EP not found

**Cause**: Custom wheel not installed in container

**Solution**: Use extended Dockerfile or install after running:
```bash
podman-compose exec vinput pip install /path/to/onnxruntime_vitisai-*.whl
```

## Performance Tuning

### CPU/Memory Limits

In `compose.yaml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'          # Use 2 cores
      memory: 4G         # Max 4GB RAM
    reservations:
      cpus: '1'
      memory: 2G
```

Adjust for your hardware.

### Network Isolation

Current setup isolates container network. For host network access:
```yaml
network_mode: host
```

(Not recommended for security)

## Advanced Usage

### Building Multi-Stage for Size Optimization

Create `Dockerfile.optimized`:
```dockerfile
FROM archlinux:latest as builder
# ... build dependencies ...

FROM archlinux:latest
# Copy only built artifacts
COPY --from=builder /home/vinput /home/vinput
```

### Running Multiple Instances

```bash
podman-compose up -d
podman-compose exec vinput python src/main.py &
podman-compose exec vinput python test_installation.py &
```

### Persistent Configuration

Mount host config into container:
```yaml
volumes:
  - ./config/commands.yaml:/home/vinput/vinput/config/commands.yaml:ro
```

## Container Best Practices

✅ **Do:**
- Use rootless Podman (default)
- Pin dependency versions (done in requirements.txt)
- Use non-root user (done)
- Mount volumes read-only when possible
- Check health with healthcheck directive
- Use named volumes for persistent data

❌ **Don't:**
- Run as root in container
- Use latest tags without pinning
- Mount entire /dev without specific devices
- Store models in container image
- Disable SELinux/AppArmor completely

## Migration from Docker

If you're using Docker instead:

```bash
# Build (identical)
docker build -t vinput:latest .

# Run with compose
docker-compose up  # instead of podman-compose up

# All commands work the same:
docker ps, docker exec, docker logs, etc.
```

The only difference is `podman` is rootless and doesn't need a daemon.

## Resources

- [Podman Documentation](https://podman.io/docs/)
- [Podman Compose](https://github.com/containers/podman-compose)
- [OCI Image Format](https://github.com/opencontainers/image-spec)
- [AMD Ryzen AI Software](https://www.amd.com/en/developer/resources/ryzen-ai-software.html)

## Next Steps

1. Install Podman and Podman Compose
2. Build the container: `podman-compose build`
3. Test: `podman-compose up`
4. Install ONNX Runtime wheel separately
5. Download Whisper models
6. Customize `config/commands.yaml`
7. Run: `podman-compose exec vinput python src/main.py`

---

**For bare-metal setup** (without containers), see [QUICKSTART.md](QUICKSTART.md).
