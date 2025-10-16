#!/bin/bash
#
# Quick Test Script for QEMU Infrastructure
# This script performs basic validation without running full kernel compilation
#

set -e

WORKSPACE_ROOT="/home/jorge/challenge-2509/simtemp-system"
QEMU_DIR="$WORKSPACE_ROOT/deployment/qemu"
SCRIPTS_DIR="$QEMU_DIR/scripts"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "============================================="
echo "QEMU Infrastructure Quick Test"
echo "============================================="

# Test 1: Check QEMU availability
log_info "Testing QEMU ARM system emulator..."
if command -v qemu-system-arm &> /dev/null; then
    qemu_version=$(qemu-system-arm --version | head -n1)
    log_info "✓ QEMU found: $qemu_version"
else
    log_error "✗ QEMU ARM system emulator not found"
    exit 1
fi

# Test 2: Check cross-compiler
log_info "Testing ARM cross-compiler..."
if command -v arm-linux-gnueabihf-gcc &> /dev/null; then
    gcc_version=$(arm-linux-gnueabihf-gcc --version | head -n1)
    log_info "✓ ARM GCC found: $gcc_version"
else
    log_error "✗ ARM cross-compiler not found"
    exit 1
fi

# Test 3: Check kernel source download status
log_info "Checking kernel source status..."
if [ -f "$QEMU_DIR/kernel-source/lf-6.6.52-2.2.1.tar.gz" ]; then
    file_size=$(du -h "$QEMU_DIR/kernel-source/lf-6.6.52-2.2.1.tar.gz" | cut -f1)
    log_info "✓ Kernel source archive found: $file_size"
    
    # Check if extracted
    if [ -d "$QEMU_DIR/kernel-source/linux-imx-lf-6.6.52-2.2.1" ]; then
        log_info "✓ Kernel source already extracted"
    else
        log_info "Extracting kernel source..."
        cd "$QEMU_DIR/kernel-source"
        tar -xzf lf-6.6.52-2.2.1.tar.gz
        log_info "✓ Kernel source extracted"
    fi
else
    log_warn "✗ Kernel source not downloaded yet"
fi

# Test 4: Check scripts
log_info "Checking build scripts..."
if [ -x "$SCRIPTS_DIR/build-imx6ul-kernel.sh" ]; then
    log_info "✓ Kernel build script ready"
else
    log_error "✗ Kernel build script not found or not executable"
fi

if [ -x "$SCRIPTS_DIR/jenkins-qemu-test.sh" ]; then
    log_info "✓ Jenkins QEMU test script ready"
else
    log_error "✗ Jenkins QEMU test script not found or not executable"
fi

# Test 5: Check Jenkins pipeline integration
log_info "Checking Jenkins integration files..."
if [ -f "$WORKSPACE_ROOT/deployment/jenkins/qemu-pipeline.groovy" ]; then
    log_info "✓ Jenkins pipeline script found"
else
    log_warn "✗ Jenkins pipeline script not found"
fi

if [ -f "$WORKSPACE_ROOT/simtemp/pipeline_config.yml" ]; then
    if grep -q "qemu_test:" "$WORKSPACE_ROOT/simtemp/pipeline_config.yml"; then
        log_info "✓ QEMU test configuration found in pipeline config"
    else
        log_warn "✗ QEMU test not configured in pipeline"
    fi
else
    log_warn "✗ Pipeline configuration file not found"
fi

# Test 6: Simulate Jenkins environment
log_info "Testing Jenkins environment simulation..."
export BUILD_NUMBER="test-$(date +%s)"
export JOB_NAME="simtemp-system-test"
export WORKSPACE="$WORKSPACE_ROOT"

log_info "Simulated Jenkins environment:"
log_info "  BUILD_NUMBER: $BUILD_NUMBER"
log_info "  JOB_NAME: $JOB_NAME"
log_info "  WORKSPACE: $WORKSPACE"

echo "============================================="
log_info "Infrastructure test completed successfully!"
echo ""
echo "Next steps:"
echo "1. Complete kernel source download (if not done)"
echo "2. Run: $SCRIPTS_DIR/build-imx6ul-kernel.sh"
echo "3. Run: $SCRIPTS_DIR/jenkins-qemu-test.sh"
echo "4. Integrate with Jenkins pipeline"
echo "============================================="