#!/bin/bash
# Script to populate the prebuilt ARM driver after compilation
# This script copies the ARM compiled driver to prebuilt directories for versioning and QEMU usage

set -e  # Exit on any error

# Print output functions
print_info() {
    echo "ℹ  $1"
}

print_success() {
    echo "✅ $1"
}

print_warning() {
    echo "⚠  $1"
}

print_error() {
    echo "❌ $1"
}

print_step() {
    echo "🔧 $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
BUILD_OUTPUT_DIR="$PROJECT_ROOT/simtemp/kernel/obj"
ARM_DRIVER="$BUILD_OUTPUT_DIR/nxp_simtemp.ko"
QEMU_PREBUILT_DIR="$PROJECT_ROOT/deployment/qemu/rootfs/tmp/prebuild/simtemp-driver"

print_info "ARM Driver Population Script"
print_info "==========================="

# Verify ARM driver exists
if [ ! -f "$ARM_DRIVER" ]; then
    print_error "ARM compiled driver not found: $ARM_DRIVER"
    print_error "Please run 'make nxp-driver-arm' first"
    exit 1
fi

# Ensure QEMU prebuilt directory exists
print_step "Preparing QEMU prebuilt directory..."
mkdir -p "$QEMU_PREBUILT_DIR"

# Clean prebuild directory before starting
print_info "Cleaning QEMU prebuild directory..."
rm -rf "$QEMU_PREBUILT_DIR"/*
mkdir -p "$QEMU_PREBUILT_DIR"

print_success "QEMU prebuilt directory ready: $QEMU_PREBUILT_DIR (cleaned)"

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
print_info "QEMU prebuilt driver details:"
ls -lh "$QEMU_PREBUILT_DIR/nxp_simtemp.ko"
file "$QEMU_PREBUILT_DIR/nxp_simtemp.ko"

print_success "=========================================="
print_success "ARM driver population completed successfully!"
print_success "=========================================="
print_info "Summary:"
print_info "  • ARM source driver: $ARM_DRIVER"
print_info "  • QEMU prebuilt dir: $QEMU_PREBUILT_DIR"
print_info "  • Files for insmod: $(ls -1 "$QEMU_PREBUILT_DIR"/*.ko 2>/dev/null | wc -l) kernel modules"
print_info "  • Updated rootfs: $PROJECT_ROOT/deployment/qemu/rootfs.cpio.gz"
