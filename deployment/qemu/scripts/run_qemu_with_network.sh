#!/bin/bash

# QEMU ARM script with network support for telnet/SSH access
# This enables remote command execution for automated tests

set -e

# Function to find project root
find_project_root() {
    local current_dir="$(pwd)"
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    local search_paths=(
        "$current_dir"
        "$script_dir"
        "$script_dir/.."
        "$script_dir/../.."
        "$script_dir/../../.."
    )
    
    for search_path in "${search_paths[@]}"; do
        local abs_path="$(cd "$search_path" 2>/dev/null && pwd)" || continue
        
        if [[ -f "$abs_path/simtemp/kernel/nxp_simtemp.c" ]] && \
           [[ -d "$abs_path/deployment/qemu" ]]; then
            echo "$abs_path"
            return 0
        fi
    done
    
    return 1
}

# Detect project root
PROJECT_ROOT="$(find_project_root)"
if [[ -z "$PROJECT_ROOT" ]]; then
    echo "ERROR: Could not find simtemp-system project root"
    exit 1
fi

echo "Starting QEMU ARM with network support for remote testing..."
echo "Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT"

# Define QEMU file paths
QEMU_DIR="$PROJECT_ROOT/deployment/qemu"
KERNEL_PATH="$QEMU_DIR/linux-build-imx/arch/arm/boot/zImage"
DTB_PATH="$QEMU_DIR/imx6q-sabrelite-with-simtemp.dtb"
ROOTFS_PATH="$QEMU_DIR/rootfs.cpio.gz"

# Network configuration
TELNET_PORT=2323
MONITOR_PORT=45455
SENSOR_PORT=37631

echo "🔍 Verifying required files..."
required_files=(
    "$KERNEL_PATH"
    "$DTB_PATH"
    "$ROOTFS_PATH"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file not found: $file"
        exit 1
    else
        echo "✓ $(basename "$file")"
    fi
done

echo ""
echo "🧹 Cleaning previous QEMU processes..."
pkill -f qemu-system-arm 2>/dev/null || true
sleep 2

echo ""
echo "🚀 Starting QEMU ARM with network support..."
echo "   Telnet access: telnet localhost $TELNET_PORT"
echo "   Monitor: telnet localhost $MONITOR_PORT"
echo "   Sensor socket: localhost:$SENSOR_PORT"
echo ""
echo "⏳ Starting QEMU (this may take a moment)..."
echo "   Look for '=== initramfs ready ===' to know when boot is complete"
echo ""

# Check if QEMU is available
if ! command -v qemu-system-arm &> /dev/null; then
    echo "ERROR: qemu-system-arm not found"
    echo "   Install QEMU: sudo apt-get install qemu-system-arm"
    exit 1
fi

# Execute QEMU with network support
exec qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel "$KERNEL_PATH" \
    -dtb "$DTB_PATH" \
    -initrd "$ROOTFS_PATH" \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 rdinit=/init" \
    -monitor "telnet:127.0.0.1:$MONITOR_PORT,server,nowait" \
    -serial stdio \
    -chardev "socket,id=mysensor,host=127.0.0.1,port=$SENSOR_PORT,server=on,wait=off" \
    -serial chardev:mysensor \
    -netdev user,id=net0,hostfwd=tcp::$TELNET_PORT-:23 \
    -device lan9118,netdev=net0 \
    -no-reboot