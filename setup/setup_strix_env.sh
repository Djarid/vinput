#!/bin/bash
# Validation script for vinput host environment on CachyOS (Arch Linux with Strix Halo NPU)
# Checks kernel, drivers, uinput permissions, and hardware readiness
# NOTE: For isolation and version pinning, use containerized deployment (Podman/Docker)
# See CONTAINERIZATION.md for full deployment guide

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${GREEN}=== vinput Host Environment Validation ===${NC}"
echo -e "${BLUE}Using project directory: ${SCRIPT_DIR}${NC}"
echo

# 1. Check kernel version and amdxdna module
echo -e "\n${YELLOW}[1/5] Checking kernel and NPU driver...${NC}"
KERNEL_VERSION=$(uname -r | cut -d. -f1-2)
echo "Kernel version: $KERNEL_VERSION"

if ! lsmod | grep -q amdxdna; then
    echo -e "${RED}ERROR: amdxdna kernel module not loaded${NC}"
    echo "Strix Halo requires Linux kernel 6.14+."
    echo "On CachyOS, update with: sudo pacman -Syu"
    exit 1
fi
echo -e "${GREEN}✓ amdxdna kernel module loaded${NC}"

# 2. Check NPU firmware
echo -e "\n${YELLOW}[2/5] Checking NPU firmware...${NC}"
if [ ! -f /lib/firmware/amdnpu/17f0_*.bin ]; then
    echo -e "${YELLOW}WARNING: NPU firmware not found in /lib/firmware/amdnpu/${NC}"
    echo "Firmware may be loaded from linux-firmware package."
fi
if ls /lib/firmware/amdnpu/17f0_*.bin 1>/dev/null 2>&1; then
    echo -e "${GREEN}✓ NPU firmware present${NC}"
fi

# 3. Check uinput device and permissions
echo -e "\n${YELLOW}[3/5] Setting up uinput permissions...${NC}"
if [ ! -c /dev/uinput ]; then
    echo -e "${YELLOW}Creating /dev/uinput...${NC}"
    sudo mknod /dev/uinput c 10 223 2>/dev/null || true
fi

# Create udev rule
UDEV_RULE="/etc/udev/rules.d/99-uinput.rules"
if [ ! -f "$UDEV_RULE" ]; then
    echo -e "${YELLOW}Creating udev rule for uinput access...${NC}"
    sudo tee "$UDEV_RULE" > /dev/null << 'EOF'
KERNEL=="uinput", SUBSYSTEM=="misc", OPTIONS+="static_node=uinput", TAG+="uaccess"
EOF
    sudo systemctl restart udev
    echo -e "${GREEN}✓ udev rule created and udev restarted${NC}"
else
    echo -e "${GREEN}✓ udev rule already exists${NC}"
fi

# Check current user permissions
if [ -r /dev/uinput ] && [ -w /dev/uinput ]; then
    echo -e "${GREEN}✓ User has read/write access to /dev/uinput${NC}"
else
    echo -e "${YELLOW}NOTE: /dev/uinput may require group membership${NC}"
    echo "If you see permission errors, you may need to:"
    echo "  sudo usermod -a -G uinput $USER"
    echo "  newgrp uinput"
fi

# 4. Check Podman/Docker availability for containerized deployment
echo -e "\n${YELLOW}[4/5] Checking container runtime (Podman/Docker)...${NC}"
if command -v podman &> /dev/null; then
    PODMAN_VERSION=$(podman --version 2>/dev/null | awk '{print $NF}')
    echo -e "${GREEN}✓ Podman found (v${PODMAN_VERSION})${NC}"
    echo "  Recommended: podman-compose up (see CONTAINERIZATION.md)"
elif command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null | grep -oP 'version \K[^,]+')
    echo -e "${GREEN}✓ Docker found (v${DOCKER_VERSION})${NC}"
    echo "  Alternative: docker-compose up (see CONTAINERIZATION.md)"
else
    echo -e "${YELLOW}WARNING: Neither Podman nor Docker found${NC}"
    echo "Install for containerized deployment:"
    echo "  sudo pacman -S podman podman-compose"
    echo "  OR"
    echo "  sudo pacman -S docker docker-compose"
fi

# 5. Summary and next steps
echo -e "\n${YELLOW}[5/5] Environment validation complete${NC}"
