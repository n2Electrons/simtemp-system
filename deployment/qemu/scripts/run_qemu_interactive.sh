#!/bin/bash

# Interactive script for QEMU ARM with simtemp module testing
# Can be executed from any directory - automatically detects project paths
# Runs QEMU, waits for boot, and allows manual interaction

# For develpopment/debugging in x86_64
set -e

# Function to find project root from any location
find_project_root() {
    local current_dir="$(pwd)"
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Try to find project root by looking for characteristic files
    local search_paths=(
        "$current_dir"
        "$script_dir"
        "$script_dir/.."
        "$script_dir/../.."
        "$script_dir/../../.."
    )
    
    for search_path in "${search_paths[@]}"; do
        local abs_path="$(cd "$search_path" 2>/dev/null && pwd)" || continue
        
        # Look for simtemp-system project indicators
        if [[ -f "$abs_path/simtemp/kernel/nxp_simtemp.c" ]] && \
           [[ -d "$abs_path/deployment/qemu" ]]; then
            echo "$abs_path"
            return 0
        fi
    done
    
    # If not found, try common workspace locations
    local workspace_paths=(
        "/workspace"
        "/home/jorge/challenge-2509/simtemp-system"
        "$HOME/simtemp-system"
        "$(dirname "$(dirname "$(dirname "$script_dir")")")"
    )
    
    for workspace_path in "${workspace_paths[@]}"; do
        if [[ -f "$workspace_path/simtemp/kernel/nxp_simtemp.c" ]] && \
           [[ -d "$workspace_path/deployment/qemu" ]]; then
            echo "$workspace_path"
            return 0
        fi
    done
    
    return 1
}

# Detect project root
PROJECT_ROOT="$(find_project_root)"
if [[ -z "$PROJECT_ROOT" ]]; then
    echo "ERROR: Could not find simtemp-system project root"
    echo "Make sure you're running this script from within the project directory"
    echo "or that the project structure is intact"
    exit 1
fi

echo "Starting interactive QEMU ARM for NXP SimTemp module testing..."
echo "Project root: $PROJECT_ROOT"
echo "Current directory: $(pwd)"
echo "ARM module at: /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
echo ""

# Change to project root for consistent paths
cd "$PROJECT_ROOT"

# Define QEMU file paths
QEMU_DIR="$PROJECT_ROOT/deployment/qemu"
KERNEL_PATH="$QEMU_DIR/linux-build-imx/arch/arm/boot/zImage"
# DTB_PATH="$QEMU_DIR/linux-build-imx/arch/arm/boot/dts/imx6q-sabresd.dtb"
DTB_PATH="$QEMU_DIR/imx6q-sabresd-with-simtemp.dtb"
ROOTFS_PATH="$QEMU_DIR/rootfs.cpio.gz"

# Verify required files
echo "🔍 Verifying required files..."
required_files=(
    "$KERNEL_PATH"
    "$DTB_PATH"
    "$ROOTFS_PATH"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file not found: $file"
        echo "   Make sure QEMU environment is properly built"
        exit 1
    else
        echo "OK: $(basename "$file")"
    fi
done

echo ""
echo "🧹 Cleaning previous QEMU processes..."
pkill -f qemu-system-arm 2>/dev/null || true
sleep 2

echo ""
echo "  Starting QEMU ARM with i.MX6 Sabresd..."
echo "  Waiting for complete boot (look for '=== initramfs ready ===')"
echo ""
echo "  Testing commands to execute once started:"
echo "   lsmod"
echo "   insmod /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
echo "   lsmod | grep nxp"
echo "   ls /sys/bus/platform/drivers/ | grep nxp"
echo "   modinfo /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
echo "   rmmod nxp_simtemp"
echo ""
echo "🚪 To exit QEMU: Ctrl+A, then X"
echo "==========================================================================="
echo ""

# Check if QEMU is available
if ! command -v qemu-system-arm &> /dev/null; then
    echo "ERROR: qemu-system-arm not found"
    echo "   Install QEMU: sudo apt-get install qemu-system-arm"
    exit 1
fi

# Execute QEMU interactively with absolute paths
exec qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel "$KERNEL_PATH" \
    -dtb "$DTB_PATH" \
    -initrd "$ROOTFS_PATH" \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 rdinit=/init quiet loglevel=8 initcall_debug printk.time=1" \
    -no-reboot