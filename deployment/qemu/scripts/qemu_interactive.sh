#!/bin/bash

# Interactive script for QEMU ARM with simtemp module testing
# Runs QEMU, waits for boot, and allows manual interaction

echo "Starting interactive QEMU ARM for NXP SimTemp module testing..."
echo "Workspace: /workspace"
echo "ARM module at: /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
echo ""

# Change to workspace directory
cd /workspace

# Verify required files
echo "Verifying required files..."
required_files=(
    "deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage"
    "deployment/qemu/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
    "deployment/qemu/rootfs.cpio.gz"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file not found: $file"
        exit 1
    else
        echo "OK: $file"
    fi
done

echo ""
echo "Cleaning previous QEMU processes..."
pkill -f qemu-system-arm 2>/dev/null || true
sleep 2

echo ""
echo "Starting QEMU ARM with i.MX6 Sabresd..."
echo "Waiting for complete boot (look for '=== ARM initramfs ready ===')"
echo "Once started, execute testing commands:"
echo "   lsmod"
echo "   insmod /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
echo "   lsmod | grep nxp"
echo "   ls /sys/bus/platform/drivers/ | grep nxp"
echo "   modinfo /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
echo "   rmmod nxp_simtemp"
echo ""
echo "To exit QEMU: Ctrl+A, then X"
echo "==========================================================================="
echo ""

# Execute QEMU interactively
exec qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage \
    -dtb deployment/qemu/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb \
    -initrd deployment/qemu/rootfs.cpio.gz \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 loglevel=8 debug" \
    -no-reboot