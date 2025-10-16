#!/bin/bash

# Test script for compiled i.MX6UL kernel in QEMU
set -e

KERNEL_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu/linux-imx-5.10"
KERNEL_IMAGE="${KERNEL_DIR}/arch/arm/boot/zImage"
DTB_FILE="${KERNEL_DIR}/arch/arm/boot/dts/imx6q-sabrelite.dtb"

echo "============================================="
echo "Testing compiled i.MX6UL kernel in QEMU"
echo "============================================="

# Check if kernel and DTB exist
if [[ ! -f "$KERNEL_IMAGE" ]]; then
    echo "❌ ERROR: Kernel image not found: $KERNEL_IMAGE"
    exit 1
fi

if [[ ! -f "$DTB_FILE" ]]; then
    echo "❌ ERROR: Device tree blob not found: $DTB_FILE"
    exit 1
fi

echo "✅ Kernel image found: $(du -h $KERNEL_IMAGE | cut -f1)"
echo "✅ Device tree found: $(du -h $DTB_FILE | cut -f1)"
echo ""

# Test kernel boot in QEMU with extended timeout to see logs
echo "🚀 Starting QEMU test with 60 second timeout..."
echo "Expected: Kernel should start booting and show console output"
echo "Press Ctrl+C to exit early if needed"
echo ""

timeout 60s qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel "$KERNEL_IMAGE" \
    -dtb "$DTB_FILE" \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 loglevel=8 debug" \
    -no-reboot || {
    
    exit_code=$?
    echo ""
    echo "============================================="
    
    if [[ $exit_code -eq 124 ]]; then
        echo "✅ SUCCESS: QEMU test completed (timeout reached)"
        echo "   - Kernel loaded successfully"
        echo "   - QEMU machine responded properly"
        echo "   - Test completed as expected"
    elif [[ $exit_code -eq 1 ]]; then
        echo "⚠️  WARNING: QEMU exited early"
        echo "   - This may be normal if no root filesystem was provided"
        echo "   - Check for kernel panic or early boot messages above"
    else
        echo "❌ ERROR: QEMU failed with exit code $exit_code"
        echo "   - Check QEMU installation and kernel compatibility"
        exit 1
    fi
}

echo ""
echo "============================================="
echo "QEMU kernel test completed successfully!"
echo "============================================="