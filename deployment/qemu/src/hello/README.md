# Hello World ARM Application

This directory contains a Hello World application designed for ARM cross-compilation and QEMU i.MX6 testing.

## Purpose

The Hello World application serves as:
- A validation tool for ARM cross-compilation setup
- A test program for QEMU i.MX6 emulation
- A demonstration of proper ARM binary creation for embedded systems
- A Jenkins CI/CD integration test component

## Files

- `hello_world.c` - Main Hello World source code
- `hello_world` - Compiled ARM binary (created by build process)
- `Makefile` - Build configuration for ARM cross-compilation
- `README.md` - This documentation

## Building

### Prerequisites

Install the ARM cross-compilation toolchain:
```bash
sudo apt install gcc-arm-linux-gnueabihf
```

### Build Commands

```bash
# Build the ARM binary
make

# Build and verify architecture
make verify

# Install to deployment directory
make install

# Create stripped version (smaller size)
make stripped

# Clean build artifacts
make clean
```

## Features

The Hello World application displays:
- System information (OS, kernel version, architecture, hostname)
- Test validation results for ARM compilation and QEMU emulation
- Jenkins integration readiness confirmation

## Integration

This application is integrated with:
- **QEMU Testing**: Used in `deployment/qemu/scripts/build-hello-world-qemu.sh`
- **Jenkins CI/CD**: Configured in `simtemp/tests/config/simtemp_tests.yml`
- **PyTest Framework**: Tested via `simtemp/tests/test_f_k1_tc_002.py`

## Usage in QEMU

The application runs automatically when the enhanced ARM rootfs boots in QEMU:

```bash
cd deployment/qemu
qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel linux-imx-5.10/arch/arm/boot/zImage \
    -dtb linux-imx-5.10/arch/arm/boot/dts/imx6q-sabrelite.dtb \
    -initrd rootfs-hello.cpio.gz \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200"
```

## Expected Output

```
===================================
   Hello World from QEMU i.MX6!
===================================

System Information:
  OS: Linux
  Kernel: 5.10.72
  Architecture: armv7l
  Hostname: (none)

Test Results:
  [PASS] ARM cross-compilation successful
  [PASS] QEMU i.MX6 emulation working
  [PASS] Device Tree loading successful
  [PASS] ARM rootfs execution successful

Jenkins Integration: READY
===================================
```