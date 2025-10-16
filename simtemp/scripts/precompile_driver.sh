#!/bin/bash
# Script to precompile the simtemp driver and update the prebuilt version
# This script compiles the driver and copies it to the prebuilt directory for versioning

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ  $1${NC}"
}

print_success() {
    echo -e "${GREEN} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}  $1${NC}"
}

print_error() {
    echo -e "${RED} $1${NC}"
}

print_step() {
    echo -e "${BLUE} $1${NC}"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
PREBUILT_DIR="$PROJECT_ROOT/simtemp/kernel/prebuilt"
BUILD_SCRIPT="$PROJECT_ROOT/deployment/qemu/scripts/build_simtemp_driver.sh"
COMPILED_DRIVER="$PROJECT_ROOT/deployment/qemu/rootfs/tmp/src/simtemp_driver/nxp_simtemp.ko"
QEMU_PREBUILT_DIR="$PROJECT_ROOT/deployment/qemu/rootfs/tmp/prebuild/simtemp-driver"
BUILD_OUTPUT_DIR="$PROJECT_ROOT/deployment/qemu/rootfs/tmp/src/simtemp_driver"

print_info "Simtemp Driver Precompilation Script"
print_info "===================================="

# Verify build script exists
if [ ! -x "$BUILD_SCRIPT" ]; then
    print_error "Build script not found or not executable: $BUILD_SCRIPT"
    exit 1
fi

# Ensure prebuilt directory exists
print_step "Preparing prebuilt directories..."
mkdir -p "$PREBUILT_DIR"
mkdir -p "$QEMU_PREBUILT_DIR"

# Clean prebuild directory before starting
print_info "Cleaning QEMU prebuild directory..."
rm -rf "$QEMU_PREBUILT_DIR"/*
mkdir -p "$QEMU_PREBUILT_DIR"

print_success "Prebuilt directories ready:"
print_info "  • Repository prebuilt: $PREBUILT_DIR"
print_info "  • QEMU prebuilt: $QEMU_PREBUILT_DIR (cleaned)"

# Force compilation mode (disable precompiled driver usage)
export USE_PRECOMPILED_DRIVER=false

print_step "Compiling simtemp driver..."
print_info "Using build script: $BUILD_SCRIPT"

# Change to QEMU directory and run build script
cd "$PROJECT_ROOT/deployment/qemu"
if ! ./scripts/build_simtemp_driver.sh; then
    print_error "Driver compilation failed"
    exit 1
fi

print_success "Driver compilation completed"

# Verify compiled driver exists
if [ ! -f "$COMPILED_DRIVER" ]; then
    print_error "Compiled driver not found: $COMPILED_DRIVER"
    exit 1
fi

# Copy compiled driver to prebuilt directory
print_step "Updating prebuilt driver..."
cp "$COMPILED_DRIVER" "$PREBUILT_DIR/nxp_simtemp.ko"
print_success "Prebuilt driver updated: $PREBUILT_DIR/nxp_simtemp.ko"

# Copy all necessary files for insmod to QEMU prebuilt directory
print_step "Copying insmod files to QEMU prebuilt directory..."

# Files needed for insmod operation
INSMOD_FILES=(
    "nxp_simtemp.ko"           # Main kernel module
    "Module.symvers"           # Symbol versions
    "modules.order"            # Module loading order
    "nxp_simtemp.mod"          # Module info
)

# Copy essential files for insmod
for file in "${INSMOD_FILES[@]}"; do
    if [ -f "$BUILD_OUTPUT_DIR/$file" ]; then
        cp "$BUILD_OUTPUT_DIR/$file" "$QEMU_PREBUILT_DIR/"
        print_info "  ✓ Copied: $file"
    else
        print_warning "  ⚠ File not found: $file (skipping)"
    fi
done

print_success "All files copied to QEMU prebuilt directory"

# Show contents of QEMU prebuilt directory
print_info "QEMU prebuilt directory contents:"
ls -la "$QEMU_PREBUILT_DIR/"

# Regenerate the rootfs with the prebuilt driver
print_step "Regenerating QEMU rootfs with prebuilt driver..."
cd "$PROJECT_ROOT/deployment/qemu"

if [ ! -x "scripts/update_rootfs.sh" ]; then
    print_error "Update rootfs script not found or not executable: scripts/update_rootfs.sh"
    exit 1
fi

print_info "Running rootfs update script..."
if ! ./scripts/update_rootfs.sh; then
    print_error "Failed to update rootfs"
    exit 1
fi

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

# Show driver details
print_info "Prebuilt driver details:"
ls -lh "$PREBUILT_DIR/nxp_simtemp.ko"
file "$PREBUILT_DIR/nxp_simtemp.ko"

# Show git status
print_step "Git status for prebuilt driver..."
cd "$PROJECT_ROOT"
git status simtemp/kernel/prebuilt/nxp_simtemp.ko 2>/dev/null || print_info "File not yet tracked in git"

print_success "============================================"
print_success "Driver precompilation completed successfully!"
print_success "============================================"
print_info "Summary:"
print_info "  • Source driver: $COMPILED_DRIVER"
print_info "  • Prebuilt driver: $PREBUILT_DIR/nxp_simtemp.ko"
print_info "  • QEMU prebuilt dir: $QEMU_PREBUILT_DIR"
print_info "  • Files for insmod: $(ls -1 "$QEMU_PREBUILT_DIR"/*.ko 2>/dev/null | wc -l) kernel modules"
print_info "  • Updated rootfs: $PROJECT_ROOT/deployment/qemu/rootfs.cpio.gz"
