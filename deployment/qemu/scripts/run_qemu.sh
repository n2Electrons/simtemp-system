#!/bin/sh

# QEMU ARM System Emulation Script for i.MX6 SABRE Lite
# This script automatically detects QEMU binary location for compatibility
# across different environments (host system, Docker containers, CI/CD)
# 
# For Jenkins container setup, see: docs/JENKINS_QEMU_CONTAINER_SETUP.md

# Detect QEMU binary location
QEMU_BIN=""
if [ -x "/usr/bin/qemu-system-arm" ]; then
    QEMU_BIN="/usr/bin/qemu-system-arm"
elif command -v qemu-system-arm >/dev/null 2>&1; then
    QEMU_BIN=$(command -v qemu-system-arm)
else
    echo "Error: qemu-system-arm not found. Please install QEMU ARM system emulation."
    echo "Install with: sudo apt install qemu-system-arm"
    echo "For Jenkins container setup, see: docs/JENKINS_QEMU_CONTAINER_SETUP.md"
    exit 1
fi

echo "Using QEMU binary: $QEMU_BIN"

# Debug: Show environment and working directory  
echo "DEBUG: Current working directory: $(pwd)"
echo "DEBUG: KERNEL_IMAGE env var: '$KERNEL_IMAGE'"
echo "DEBUG: DTB_FILE env var: '$DTB_FILE'"
echo "DEBUG: ROOTFS_IMAGE env var: '$ROOTFS_IMAGE'"

# Use environment variables if provided, otherwise auto-detect paths
KERNEL_IMAGE_PATH="${KERNEL_IMAGE:-}"
DTB_FILE_PATH="${DTB_FILE:-}"
ROOTFS_IMAGE_PATH="${ROOTFS_IMAGE:-}"

echo "DEBUG: Resolved paths:"
echo "  KERNEL_IMAGE_PATH: '$KERNEL_IMAGE_PATH'"
echo "  DTB_FILE_PATH: '$DTB_FILE_PATH'"
echo "  ROOTFS_IMAGE_PATH: '$ROOTFS_IMAGE_PATH'"

# Auto-detect Jenkins workspace if available
if [ -z "$KERNEL_IMAGE_PATH" ] && [ -f "/var/jenkins_home/workspace/simtemp-system/deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage" ]; then
    echo "DEBUG: Using Jenkins simtemp-system workspace"
    KERNEL_IMAGE_PATH="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage"
    DTB_FILE_PATH="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
    ROOTFS_IMAGE_PATH="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/rootfs.cpio.gz"
fi

# Verify required files exist - check environment variables first, then relative paths
if [ -n "$KERNEL_IMAGE_PATH" ] && [ -f "$KERNEL_IMAGE_PATH" ]; then
    KERNEL_IMAGE="$KERNEL_IMAGE_PATH"
elif [ -f "linux-imx-5.10/arch/arm/boot/zImage" ]; then
    KERNEL_IMAGE="linux-imx-5.10/arch/arm/boot/zImage"
elif [ -f "deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage" ]; then
    KERNEL_IMAGE="deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage"
else
    echo "Error: Kernel image not found"
    echo "Tried env KERNEL_IMAGE: $KERNEL_IMAGE_PATH"
    echo "Tried: linux-imx-5.10/arch/arm/boot/zImage"
    echo "Tried: deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage"
    echo "Please ensure kernel is compiled or run from correct directory"
    exit 1
fi

DTB_FILE=""
if [ -f "linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb" ]; then
    DTB_FILE="linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
elif [ -f "deployment/qemu/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb" ]; then
    DTB_FILE="deployment/qemu/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
else
    echo "Error: Device tree blob not found"
    echo "Tried: linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
    echo "Tried: deployment/qemu/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
    exit 1
fi

ROOTFS_IMAGE=""
if [ -f "rootfs.cpio.gz" ]; then
    ROOTFS_IMAGE="rootfs.cpio.gz"
elif [ -f "deployment/qemu/rootfs.cpio.gz" ]; then
    ROOTFS_IMAGE="deployment/qemu/rootfs.cpio.gz"
else
    echo "Error: Root filesystem not found"
    echo "Tried: rootfs.cpio.gz"
    echo "Tried: deployment/qemu/rootfs.cpio.gz"
    exit 1
fi

echo "Starting QEMU ARM emulation for i.MX6 SABRE Lite..."
echo "Monitor telnet: telnet 127.0.0.1 45454"
echo "To stop QEMU: Press Ctrl+C or use monitor command 'quit'"

$QEMU_BIN -M sabrelite \
                -cpu cortex-a9 \
                -m 1024 -nographic -no-reboot \
                -kernel "$KERNEL_IMAGE" \
                -dtb "$DTB_FILE" \
                -initrd "$ROOTFS_IMAGE" \
                -append "console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 rdinit=/init loglevel=8" \
                -monitor telnet:127.0.0.1:45454,server,nowait
