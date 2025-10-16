#!/bin/bash
# Build script for simtemp kernel driver in QEMU environment
# This script handles cross-compilation and rootfs integration

###############################################################################
#	THIS SCRIPT WILL BE USED IN CASE THAT WE DECIDE TO                        #
#	UPLOAD A SUB-SET OF (COMPRESSED) LINUX KERNEL SOURCE FILES INTO THE REPO  #
#	OR TO CLONE AN BUILD IN THE PIPELINE                                      #
###############################################################################

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_step() {
    echo -e "${BLUE}🔨 $1${NC}"
}

# Configuration variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QEMU_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$QEMU_DIR")")"
SIMTEMP_SRC_DIR="$PROJECT_ROOT/simtemp/kernel"
ROOTFS_DRIVER_DIR="$QEMU_DIR/rootfs/tmp/src/simtemp_driver"
# Allow kernel source directory to be overridden by env variable
KERNEL_SRC_DIR="${KERNEL_SRC_DIR:-$QEMU_DIR/linux-imx-5.10.72}"

# Precompiled driver settings
USE_PRECOMPILED_DRIVER="${USE_PRECOMPILED_DRIVER:-false}"
PRECOMPILED_DRIVER_PATH="${PRECOMPILED_DRIVER_PATH:-$PROJECT_ROOT/simtemp/kernel/prebuilt/nxp_simtemp.ko}"

# Cross-compilation environment
export ARCH="${ARCH:-arm}"
export CROSS_COMPILE="${CROSS_COMPILE:-arm-linux-gnueabihf-}"
export CFLAGS_EXTRA="${CFLAGS_EXTRA:--march=armv7-a -marm}"

print_info "Simtemp Driver Build Script for QEMU"
print_info "====================================="

# Debug: Show environment variables
print_info "Environment variables:"
print_info "  USE_PRECOMPILED_DRIVER: ${USE_PRECOMPILED_DRIVER:-not set}"
print_info "  PRECOMPILED_DRIVER_PATH: ${PRECOMPILED_DRIVER_PATH:-not set}"

# Check if we should use precompiled driver
if [ "$USE_PRECOMPILED_DRIVER" = "true" ]; then
    print_info "Using precompiled driver mode"
    
    # In QEMU context, the precompiled driver should already be in the rootfs
    # We just need to verify it exists and copy it to the expected location
    if [ -f "$PRECOMPILED_DRIVER_PATH" ]; then
        print_success "Found precompiled driver in QEMU filesystem: $PRECOMPILED_DRIVER_PATH"
        
        # Create target directory and copy precompiled driver  
        print_step "Preparing target directory..."
        mkdir -p "$ROOTFS_DRIVER_DIR"
        
        print_step "Using precompiled simtemp driver from QEMU filesystem..."
        cp "$PRECOMPILED_DRIVER_PATH" "$ROOTFS_DRIVER_DIR/nxp_simtemp.ko"
        print_success "Precompiled driver copied to: $ROOTFS_DRIVER_DIR/nxp_simtemp.ko"
    else
        # If not found in QEMU path, try host path (fallback)
        HOST_PRECOMPILED_PATH="$PROJECT_ROOT/simtemp/kernel/prebuilt/nxp_simtemp.ko"
        if [ -f "$HOST_PRECOMPILED_PATH" ]; then
            print_warning "QEMU path not found, using host precompiled driver: $HOST_PRECOMPILED_PATH"
            
            # Create target directory and copy precompiled driver
            print_step "Preparing target directory..."
            mkdir -p "$ROOTFS_DRIVER_DIR"
            
            print_step "Using precompiled simtemp driver from host..."
            cp "$HOST_PRECOMPILED_PATH" "$ROOTFS_DRIVER_DIR/nxp_simtemp.ko"
            print_success "Host precompiled driver copied to: $ROOTFS_DRIVER_DIR/nxp_simtemp.ko"
        else
            print_error "Precompiled driver not found in either location:"
            print_error "  QEMU path: $PRECOMPILED_DRIVER_PATH"
            print_error "  Host path: $HOST_PRECOMPILED_PATH"
            exit 1
        fi
    fi
    
    # Show driver details
    print_info "Precompiled driver details:"
    ls -lh "$ROOTFS_DRIVER_DIR/nxp_simtemp.ko"
    file "$ROOTFS_DRIVER_DIR/nxp_simtemp.ko"
    
    # Skip to rootfs integration
    cd "$ROOTFS_DRIVER_DIR"
    
else
    print_info "Using compilation mode"
    
    # Verify prerequisites
    print_step "Checking prerequisites..."

    # Check if we're in the right directory structure
    if [ ! -d "$SIMTEMP_SRC_DIR" ]; then
        print_error "Simtemp source directory not found: $SIMTEMP_SRC_DIR"
        exit 1
    fi

    if [ ! -d "$KERNEL_SRC_DIR" ]; then
        print_error "Kernel source directory not found: $KERNEL_SRC_DIR"
        print_info "Available kernel directories:"
        find "$QEMU_DIR" -maxdepth 1 -name "linux-imx*" -type d || print_warning "No linux-imx directories found"
        exit 1
    fi

    # Check cross-compiler
    if ! which "${CROSS_COMPILE}gcc" >/dev/null 2>&1; then
        print_error "Cross-compiler not found: ${CROSS_COMPILE}gcc"
        print_info "Please install ARM cross-compilation toolchain"
        print_info "On Ubuntu/Debian: sudo apt-get install gcc-arm-linux-gnueabihf"
        exit 1
    fi

    print_success "Prerequisites check passed"

    # Display environment information
    print_info "Build Environment:"
    print_info "  Architecture: $ARCH"
    print_info "  Cross-compiler: $CROSS_COMPILE"
    print_info "  Extra CFLAGS: $CFLAGS_EXTRA"
    print_info "  Kernel source: $KERNEL_SRC_DIR"
    print_info "  Simtemp source: $SIMTEMP_SRC_DIR"
    print_info "  Target directory: $ROOTFS_DRIVER_DIR"

    # Create target directory structure
    print_step "Preparing target directory..."
    mkdir -p "$ROOTFS_DRIVER_DIR"
    print_success "Target directory ready: $ROOTFS_DRIVER_DIR"

    # Copy only essential simtemp sources for compilation
    print_step "Copying essential simtemp kernel sources..."

    # List of essential files needed for kernel module compilation
    ESSENTIAL_FILES=(
        "nxp_simtemp.c"     # Main source code
        "Makefile"          # Build configuration
        "Kbuild"            # Kernel build configuration
        "Kconfig"           # Optional kernel configuration
    )

    # Copy only essential files
    for file in "${ESSENTIAL_FILES[@]}"; do
        if [ -f "$SIMTEMP_SRC_DIR/$file" ]; then
            cp -v "$SIMTEMP_SRC_DIR/$file" "$ROOTFS_DRIVER_DIR/"
            print_info "  ✓ Copied: $file"
        else
            print_warning "  ⚠ File not found: $file (skipping)"
        fi
    done

    print_success "Essential sources copied successfully"

    # Verify source files
    print_info "Source files in target directory:"
    ls -la "$ROOTFS_DRIVER_DIR/"

    # Cross-compile the kernel module
    print_step "Cross-compiling simtemp kernel module..."
    cd "$ROOTFS_DRIVER_DIR"

    # Create a simple Makefile for cross-compilation if it doesn't exist or use the existing one
    if [ ! -f "Makefile" ]; then
        print_warning "No Makefile found, creating basic cross-compilation Makefile"
        cat > Makefile << 'EOF'
obj-m := nxp_simtemp.o

all:
	$(MAKE) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) -C $(KERNEL_SRC) M=$(PWD) modules

clean:
	$(MAKE) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) -C $(KERNEL_SRC) M=$(PWD) clean
EOF
    fi

    # Build the module
    print_info "Starting kernel module compilation..."
    KERNEL_SRC="$KERNEL_SRC_DIR" make ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" -C "$KERNEL_SRC_DIR" M="$(pwd)" modules

    # Verify compilation results
    if [ -f "nxp_simtemp.ko" ]; then
        print_success "Kernel module compiled successfully!"
        print_info "Module details:"
        ls -lh nxp_simtemp.ko
        file nxp_simtemp.ko
    else
        print_error "Kernel module compilation failed - no .ko file generated"
        print_info "Build artifacts:"
        ls -la *.o *.mod* 2>/dev/null || print_warning "No object files found"
        exit 1
    fi
fi

# Optional: Copy module to a standard location within rootfs
MODULES_DIR="$QEMU_DIR/rootfs/lib/modules/extra"
if mkdir -p "$MODULES_DIR" 2>/dev/null; then
    cp nxp_simtemp.ko "$MODULES_DIR/"
    print_success "Module installed to: $MODULES_DIR/nxp_simtemp.ko"
fi

# Regenerate rootfs
print_step "Regenerating rootfs with simtemp driver..."
cd "$QEMU_DIR"

if [ ! -x "scripts/update_rootfs.sh" ]; then
    print_error "Update rootfs script not found or not executable: scripts/update_rootfs.sh"
    exit 1
fi

print_info "Running rootfs update script..."
./scripts/update_rootfs.sh

# Verify rootfs was updated
if [ -f "rootfs.cpio.gz" ]; then
    print_success "Rootfs updated successfully!"
    print_info "New rootfs details:"
    ls -lh rootfs.cpio.gz
    
    # Show timestamp to confirm it was just updated
    print_info "Rootfs timestamp: $(stat -c %y rootfs.cpio.gz)"
else
    print_error "Rootfs update failed - no rootfs.cpio.gz found"
    exit 1
fi

print_success "========================================="
print_success "✅ Simtemp driver build completed successfully!"
print_success "========================================="
print_info "Summary:"
print_info "  • Build mode: $([ "$USE_PRECOMPILED_DRIVER" = "true" ] && echo "Precompiled" || echo "Compiled from source")"
print_info "  • Kernel module: $ROOTFS_DRIVER_DIR/nxp_simtemp.ko"
print_info "  • Module in rootfs: $MODULES_DIR/nxp_simtemp.ko"
print_info "  • Updated rootfs: $QEMU_DIR/rootfs.cpio.gz"
if [ "$USE_PRECOMPILED_DRIVER" != "true" ]; then
    print_info "  • Architecture: $ARCH"
    print_info "  • Cross-compiler: $CROSS_COMPILE"
fi

print_info ""
print_info "The simtemp driver is now ready for QEMU testing!"
print_info "You can run QEMU with: ./scripts/run_qemu.sh"