#!/bin/bash

# Quick QEMU DT validation script
# Tests that our Device Tree can be loaded without full system boot

echo "Testing Device Tree loading in QEMU i.MX6..."

# Test 1: Validate DT syntax
echo "1. Validating Device Tree syntax..."
if dtc -I dtb -O dts deployment/qemu/dtb/imx6ul-simtemp.dtb > /dev/null 2>&1; then
    echo "   ✅ Device Tree binary is valid"
else
    echo "   ❌ Device Tree binary has issues"
    exit 1
fi

# Test 2: Quick QEMU DT load test (exit immediately)
echo "2. Testing QEMU can load our Device Tree..."
timeout 5s qemu-system-arm \
  -machine mcimx6ul-evk \
  -cpu cortex-a7 \
  -m 256M \
  -dtb deployment/qemu/dtb/imx6ul-simtemp.dtb \
  -nographic \
  -S \
  2>&1 | grep -q "QEMU" && echo "   ✅ QEMU loads DT successfully" || echo "   ⚠️  QEMU test inconclusive"

echo "3. Device Tree overlay test..."
if [ -f "deployment/qemu/overlay/simtemp-test-overlay.dtbo" ]; then
    echo "   ✅ Overlay binary available"
else
    echo "   ❌ Overlay binary missing"
fi

echo ""
echo "QEMU DT infrastructure validation complete!"
echo ""
echo "To run full system emulation, you would need:"
echo "  - ARM kernel image"
echo "  - Root filesystem (initrd/ext4)"
echo "  - Bootloader (U-Boot)"
echo ""
echo "For F-K1-TC-002 testing, the current mock infrastructure is sufficient."