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
# Note: onnxruntime with Vitis AI EP must be obtained separately
RUN . /home/vinput/.venv/bin/activate && \
    pip install --no-cache-dir \
        numpy==1.24.3 \
        sounddevice==0.4.6 \
        webrtcvad==2.0.10 \
        evdev==1.5.0 \
        scipy==1.10.1 \
        pyyaml==6.0.1 && \
    pip install --no-cache-dir pytest pytest-cov

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
