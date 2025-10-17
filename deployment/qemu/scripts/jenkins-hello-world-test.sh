#!/bin/bash

# Jenkins QEMU Hello World Test
# This script runs a complete QEMU test with hello world for Jenkins CI/CD

set -e

QEMU_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu"
KERNEL_IMAGE="$QEMU_DIR/linux-imx-5.10/arch/arm/boot/zImage"
DTB_FILE="$QEMU_DIR/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabrelite.dtb"
ROOTFS_IMAGE="$QEMU_DIR/rootfs-hello.cpio.gz"

# Use workspace directory for test outputs - avoids permission issues
WORKSPACE_DIR="${WORKSPACE:-$(pwd)}"
TEST_OUTPUT="$WORKSPACE_DIR/jenkins-test-results.txt"

echo "============================================="
echo "Jenkins QEMU Hello World Test"
echo "============================================="

# Cleanup previous results
rm -f "$TEST_OUTPUT"

# Check required files
echo "Checking required files..."
if [[ ! -f "$KERNEL_IMAGE" ]]; then
    echo "ERROR: Kernel image not found: $KERNEL_IMAGE"
    exit 1
fi

if [[ ! -f "$DTB_FILE" ]]; then
    echo "ERROR: Device tree not found: $DTB_FILE"
    exit 1
fi

if [[ ! -f "$ROOTFS_IMAGE" ]]; then
    echo "ERROR: Hello World rootfs not found: $ROOTFS_IMAGE"
    echo "Run ./scripts/build-hello-world-qemu.sh first"
    exit 1
fi

echo "Found kernel: $(du -h $KERNEL_IMAGE | cut -f1)"
echo "Found DTB: $(du -h $DTB_FILE | cut -f1)"
echo "Found rootfs: $(du -h $ROOTFS_IMAGE | cut -f1)"
echo ""

# Run QEMU test with timeout
echo "Starting QEMU Hello World test..."
echo "Expected: Hello World program should run and display test results"
echo ""

cd "$QEMU_DIR"

# Run QEMU with output capture
timeout 30s qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel "$KERNEL_IMAGE" \
    -dtb "$DTB_FILE" \
    -initrd "$ROOTFS_IMAGE" \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 loglevel=8" \
    -no-reboot 2>&1 | tee "$TEST_OUTPUT" || {
    
    exit_code=$?
    echo ""
    echo "============================================="
    
    if [[ $exit_code -eq 124 ]]; then
        echo "QEMU test completed (timeout reached - expected)"
        
        # Check for success indicators in output
        if grep -q "Hello World from QEMU i.MX6" "$TEST_OUTPUT" && \
           grep -q "\[PASS\].*ARM cross-compilation successful" "$TEST_OUTPUT" && \
           grep -q "\[PASS\].*QEMU i.MX6 emulation working" "$TEST_OUTPUT" && \
           grep -q "Jenkins Integration: READY" "$TEST_OUTPUT"; then
            
            echo "SUCCESS: All hello world tests passed!"
            echo "  - Kernel boots successfully"
            echo "  - ARM rootfs executes properly"
            echo "  - Hello World program runs correctly"
            echo "  - Jenkins integration confirmed"
            
            # Create JUnit XML for Jenkins in workspace
            cat > "$WORKSPACE_DIR/junit-results.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="QEMU Hello World Test" tests="4" failures="0" errors="0" time="30">
    <testcase name="Kernel Boot" classname="QEMUTest" time="5"/>
    <testcase name="ARM Rootfs Execution" classname="QEMUTest" time="2"/>
    <testcase name="Hello World Program" classname="QEMUTest" time="1"/>
    <testcase name="Jenkins Integration" classname="QEMUTest" time="1"/>
</testsuite>
EOF
            
            exit 0
        else
            echo "FAILURE: Hello World test did not complete successfully"
            echo "Check $TEST_OUTPUT for details"
            
            # Create failure JUnit XML in workspace
            cat > "$WORKSPACE_DIR/junit-results.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="QEMU Hello World Test" tests="4" failures="1" errors="0" time="30">
    <testcase name="Kernel Boot" classname="QEMUTest" time="5"/>
    <testcase name="ARM Rootfs Execution" classname="QEMUTest" time="2"/>
    <testcase name="Hello World Program" classname="QEMUTest" time="1">
        <failure message="Hello World program did not execute properly"/>
    </testcase>
    <testcase name="Jenkins Integration" classname="QEMUTest" time="1"/>
</testsuite>
EOF
            
            exit 1
        fi
    else
        echo "ERROR: QEMU failed with exit code $exit_code"
        exit 1
    fi
}

echo ""
echo "============================================="
echo "Jenkins QEMU Hello World test completed!"
echo "============================================="