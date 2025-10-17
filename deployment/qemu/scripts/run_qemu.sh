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

# Verify required files exist
if [ ! -f "linux-imx-5.10/arch/arm/boot/zImage" ]; then
    echo "Error: Kernel image not found: linux-imx-5.10/arch/arm/boot/zImage"
    echo "Please ensure you're running this script from the deployment/qemu directory"
    exit 1
fi

if [ ! -f "linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb" ]; then
    echo "Error: Device tree blob not found: linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
    exit 1
fi

if [ ! -f "rootfs.cpio.gz" ]; then
    echo "Error: Root filesystem not found: rootfs.cpio.gz"
    exit 1
fi

echo "Starting QEMU ARM emulation for i.MX6 SABRE Lite..."
echo "Monitor telnet: telnet 127.0.0.1 45454"
echo "To stop QEMU: Press Ctrl+C or use monitor command 'quit'"

$QEMU_BIN -M sabrelite \
                -cpu cortex-a9 \
                -m 1024 -nographic -no-reboot \
                -kernel linux-imx-5.10/arch/arm/boot/zImage \
                -dtb linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb \
                -initrd rootfs.cpio.gz \
                -append "console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 rdinit=/init loglevel=8" \
                -monitor telnet:127.0.0.1:45454,server,nowait
