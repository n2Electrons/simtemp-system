#!/bin/bash
#
# Build DTB with SimTemp overlay for QEMU testing
# 
# For complete documentation, see: ../DTB_OVERLAY_README.md
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QEMU_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building DTB with SimTemp overlay..."

cd "$QEMU_DIR"

# Paths
BASE_DTB="linux-build-imx/arch/arm/boot/dts/imx6q-sabresd.dtb"
OVERLAY_DTBO="overlay/nxp-simtemp-overlay.dtbo"
COMBINED_DTB="imx6q-sabresd-with-simtemp.dtb"

# Check if base DTB exists
if [ ! -f "$BASE_DTB" ]; then
    echo "❌ Base DTB not found: $BASE_DTB"
    echo "   Building kernel DTBs first..."
    cd linux-imx-5.10
    make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- imx6q-sabresd.dtb
    cd ..
fi

# Check if overlay exists
if [ ! -f "$OVERLAY_DTBO" ]; then
    echo "❌ Overlay DTBO not found: $OVERLAY_DTBO"
    echo "   Building overlay first..."
    cd overlay
    dtc -@ -I dts -O dtb -o nxp-simtemp-overlay.dtbo nxp-simtemp-overlay.dts
    cd ..
fi

# Combine DTB with overlay
echo "🔨 Combining DTB with overlay..."
fdtoverlay -i "$BASE_DTB" -o "$COMBINED_DTB" "$OVERLAY_DTBO"

# Verify the result
echo "✅ Verifying combined DTB..."
if dtc -I dtb -O dts "$COMBINED_DTB" 2>/dev/null | grep -q "nxp,simtemp"; then
    echo "✅ Combined DTB created successfully: $COMBINED_DTB"
    echo "   SimTemp device node included ✓"
else
    echo "❌ Combined DTB verification failed"
    exit 1
fi

echo "📋 Combined DTB ready for QEMU testing"