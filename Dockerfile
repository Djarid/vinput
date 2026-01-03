# Podman-optimized Dockerfile for vinput
# Builds reproducible development environment for voice-to-uinput automation
# on AMD Strix Halo with XDNA 2 NPU
#
# Build: podman build -t vinput:latest .
# Run:   podman run --rm -it \
#          --device /dev/uinput \
#          --device /dev/input \
#          --device /dev/accel/accel0 \
#          -v /run/user/1000/pulse:/run/user/1000/pulse:ro \
#          vinput:latest
#
# Or use: podman-compose up

FROM archlinux:latest

LABEL maintainer="vinput developers"
LABEL description="Voice-to-uinput automation for AMD Strix Halo + XDNA 2 NPU"
LABEL version="0.1.0"

# Set environment
ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
# Updated to match white paper requirements for XDNA 2 development
RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm \
        # Build essentials
        base-devel \
        cmake \
        git \
        wget \
        curl \
        \
        # Python 3.10 (recommended for stability)
        python=3.10 \
        python-pip \
        \
        # Audio libraries (for sounddevice)
        alsa-lib \
        libsndfile \
        pulseaudio \
        \
        # Required for evdev/uinput
        libevdev \
        \
        # For numpy/scipy compilation if wheels unavailable
        blas \
        lapack \
        gcc \
        gfortran \
        \
        # Useful utilities
        htop \
        nano \
        vim \
        less && \
    \
    # Clean package cache to reduce image size
    pacman -Sc --noconfirm && \
    \
    # Create non-root user for development
    useradd -m -s /bin/bash vinput

# Set working directory
WORKDIR /home/vinput/vinput
RUN chown -R vinput:vinput /home/vinput

# Copy project files
COPY --chown=vinput:vinput . .

# Create python virtual environment
RUN python -m venv /home/vinput/.venv && \
    . /home/vinput/.venv/bin/activate && \
    pip install --upgrade pip setuptools wheel

# Install Python dependencies (pinned versions)
RUN . /home/vinput/.venv/bin/activate && \
    pip install --no-cache-dir \
        numpy==1.24.3 \
        sounddevice==0.4.6 \
        webrtcvad==2.0.10 \
        evdev==1.5.0 \
        scipy==1.10.1 \
        pyyaml==6.0.1

# Install ONNX Runtime with Vitis AI Execution Provider (if available)
# AMD does not provide stable direct download URLs. To enable NPU acceleration:
#
# 1. Download wheel from AMD Developer Portal:
#    https://www.amd.com/en/developer/resources/ryzen-ai-software.html
#    Look for: Ryzen AI Software Platform → Downloads → ONNX Runtime
#    File: onnxruntime_vitisai-1.17.0-cp310-cp310-linux_x86_64.whl
#
# 2. Place wheel in project root: /home/jasonh/git/vinput/
#
# 3. Rebuild container: podman-compose build
#
# The build will auto-detect and install the wheel if present.
# If not present, vinput falls back to CPU inference (no NPU acceleration).
#
RUN . /home/vinput/.venv/bin/activate && \
    if [ -f /home/vinput/vinput/onnxruntime_vitisai*.whl ]; then \
        echo "✓ Installing ONNX Runtime with Vitis AI EP from local wheel..."; \
        pip install --no-cache-dir /home/vinput/vinput/onnxruntime_vitisai*.whl && \
        echo "✓ NPU acceleration enabled"; \
    else \
        echo "⚠ ONNX Runtime with Vitis AI EP not found in project root."; \
        echo "  NPU acceleration disabled. CPU inference will be used."; \
        echo "  To enable NPU: Download wheel from AMD, place in project root, rebuild."; \
        echo "  See: https://www.amd.com/en/developer/resources/ryzen-ai-software.html"; \
    fi

# Install development dependencies (for testing)
RUN . /home/vinput/.venv/bin/activate && \
    pip install --no-cache-dir \
        pytest==7.4.3 \
        pytest-asyncio==0.21.1 \
        pytest-cov==4.1.0 \
        pytest-mock==3.12.0

# Create models directory
RUN mkdir -p models config

# Set user
USER vinput

# Activate virtualenv in shell
ENV PATH="/home/vinput/.venv/bin:$PATH"

# Health check: verify audio engine can initialize
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.audio_engine import AudioEngine; AudioEngine()" || exit 1

# Default command: test installation
CMD ["python", "test_installation.py"]
