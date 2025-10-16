#!/bin/bash
#
# Build i.MX6UL Linux Kernel for QEMU Testing
# This script compiles the NXP i.MX kernel with Device Tree overlay support
#

set -e

# Configuration
KERNEL_SOURCE_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu/kernel-source/linux-imx-lf-6.6.52-2.2.1"
BUILD_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu/build"
SCRIPTS_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu/scripts"

# Cross-compilation settings
export ARCH=arm
export CROSS_COMPILE=arm-linux-gnueabihf-

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check cross-compiler
    if ! command -v arm-linux-gnueabihf-gcc &> /dev/null; then
        log_error "ARM cross-compiler not found. Install with: sudo apt-get install gcc-arm-linux-gnueabihf"
        exit 1
    fi
    
    # Check kernel source
    if [ ! -d "$KERNEL_SOURCE_DIR" ]; then
        log_error "Kernel source not found at $KERNEL_SOURCE_DIR"
        exit 1
    fi
    
    # Check build tools
    for tool in make bc bison flex libssl-dev; do
        if ! dpkg -l | grep -q "^ii.*$tool"; then
            log_warn "$tool may not be installed. Consider: sudo apt-get install build-essential bc bison flex libssl-dev"
        fi
    done
    
    log_info "Prerequisites check completed"
}

clean_build() {
    log_info "Cleaning previous build artifacts..."
    
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"/*
    fi
    
    cd "$KERNEL_SOURCE_DIR"
    make mrproper O="$BUILD_DIR"
    
    log_info "Build directory cleaned"
}

configure_kernel() {
    log_info "Configuring kernel for i.MX6UL..."
    
    cd "$KERNEL_SOURCE_DIR"
    
    # Use i.MX default configuration
    make imx_v6_v7_defconfig O="$BUILD_DIR"
    
    # Enable additional features needed for testing
    # Use the config script from the source directory, not build directory
    cd "$KERNEL_SOURCE_DIR"
    
    # Enable Device Tree overlay support
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_OF_OVERLAY
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_OF_CONFIGFS
    
    # Enable NFS support for file sharing
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_NFS_FS
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_NFS_V3
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_NFS_V4
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_ROOT_NFS
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_IP_PNP
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_IP_PNP_DHCP
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_IP_PNP_BOOTP
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_IP_PNP_RARP
    
    # Enable 9P filesystem support (backup option)
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_9P_FS
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_9P_FS_POSIX_ACL
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_9P_FS_SECURITY
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_NET_9P
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_NET_9P_VIRTIO
    
    # Enable QEMU virtio support
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_VIRTIO
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_VIRTIO_PCI
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_VIRTIO_NET
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_VIRTIO_BLK
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_VIRTIO_CONSOLE
    
    # Enable debugging support
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_DEBUG_INFO
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_DEBUG_KERNEL
    scripts/config --file "$BUILD_DIR/.config" --enable CONFIG_EARLY_PRINTK
    
    # Update configuration with dependencies
    make olddefconfig O="$BUILD_DIR"
    
    log_info "Kernel configuration completed"
}

build_kernel() {
    log_info "Building kernel image..."
    
    cd "$KERNEL_SOURCE_DIR"
    
    # Build kernel image
    make -j$(nproc) zImage O="$BUILD_DIR"
    
    # Build device tree blobs
    make -j$(nproc) dtbs O="$BUILD_DIR"
    
    # Build modules
    make -j$(nproc) modules O="$BUILD_DIR"
    
    log_info "Kernel build completed successfully"
}

install_artifacts() {
    log_info "Installing build artifacts..."
    
    # Create installation directories
    mkdir -p "$BUILD_DIR/install/boot"
    mkdir -p "$BUILD_DIR/install/lib/modules"
    
    # Copy kernel image
    cp "$BUILD_DIR/arch/arm/boot/zImage" "$BUILD_DIR/install/boot/"
    
    # Copy device tree blobs
    find "$BUILD_DIR/arch/arm/boot/dts" -name "*.dtb" -exec cp {} "$BUILD_DIR/install/boot/" \;
    
    # Install modules
    cd "$KERNEL_SOURCE_DIR"
    make modules_install INSTALL_MOD_PATH="$BUILD_DIR/install" O="$BUILD_DIR"
    
    log_info "Build artifacts installed to $BUILD_DIR/install/"
}

show_summary() {
    log_info "Build Summary"
    echo "==============================================="
    echo "Kernel Image: $BUILD_DIR/install/boot/zImage"
    echo "Device Trees: $BUILD_DIR/install/boot/*.dtb"
    echo "Modules: $BUILD_DIR/install/lib/modules/"
    echo ""
    echo "Key files for QEMU:"
    echo "- Kernel: $BUILD_DIR/install/boot/zImage"
    echo "- DTB: $BUILD_DIR/install/boot/imx6ul-14x14-evk.dtb"
    echo ""
    echo "To test in QEMU:"
    echo "qemu-system-arm -M mcimx6ul-evk \\"
    echo "  -kernel $BUILD_DIR/install/boot/zImage \\"
    echo "  -dtb $BUILD_DIR/install/boot/imx6ul-14x14-evk.dtb \\"
    echo "  -nographic -serial stdio"
    echo "==============================================="
}

main() {
    log_info "Starting i.MX6UL kernel build process..."
    
    check_prerequisites
    clean_build
    configure_kernel
    build_kernel
    install_artifacts
    show_summary
    
    log_info "Kernel build process completed successfully!"
}

# Run main function
main "$@"