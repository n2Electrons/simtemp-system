# Tests by Architecture - SimTemp System

## Overview

This document describes the distribution of SimTemp system tests across different hardware architectures. The system supports execution on x86_64 (host/Debian) and ARM (emulated via QEMU i.MX6).

---

## Test Matrix by Architecture

| Test ID | Test Name | Host (x86_64) | Debian (x86_64) | ARM (QEMU) | Notes |
|---------|-------------------------------------------|:-------------:|:---------------:|:----------:|-------|
| **F-K1-TC-001** | `test_insmod_registers_driver` | ✅ | ✅ | ✅ | Basic module loading test |
| **F-K1-TC-002** | `test_basic_qemu_boot` | ❌ | ❌ | ✅ | QEMU validation only |
| **F-K1-TC-003** | `test_f_k1_platform_driver_dt_registration` | ✅ | ✅ | ✅ | TDD - expected to fail until implementation |
| **F-K8-TC-001** | `test_driver_load_unload` | ✅ | ✅ | ❌ | Host/Debian with modprobe -r |
| **F-K8-TC-001-QEMU** | `test_qemu_driver_load_unload` | ❌ | ❌ | ✅ | ARM version in QEMU |
| **F-K8-TC-002** | `test_readers_exit_gracefully_on_unload` | ✅ | ✅ | ✅ | Multi-platform support |
| **F-K8-TC-003-A** | `test_dtb_overlay_exists` | ✅ | ✅ | ✅ | DTB overlay compilation |
| **F-K8-TC-003-B** | `test_dtb_driver_binding` | ✅ | ✅ | ✅ | DTB driver binding |
| **F-K8-TC-003** | `test_dtb_driver_binding_and_functionality` | ✅ | ✅ | ✅ | Complete DTB functionality |
| **F-K8-TC-004** | `test_driver_validation` | ✅ | ✅ | ✅ | Comprehensive validation |

---

## Platform Configuration Details

### Host/Debian (x86_64)
- **Platform detection**: `platform.machine() in ['x86_64', 'i386', 'i686']`
- **Module tools**: `modprobe -r` (automatic dependency handling)
- **Stub module**: Required for dependency resolution on x86
- **Device Tree**: Simulated/emulated (no native support)
- **Compilation**: Native with host kernel headers

### ARM (QEMU i.MX6)
- **Platform detection**: Specific tests with `_qemu.py` suffix or detected QEMU mode
- **Module tools**: `rmmod` (manual removal)
- **Stub module**: Not required on ARM architecture
- **Device Tree**: Full native support
- **Kernel**: linux-imx-5.10 
- **DTB**: `imx6q-sabresd-with-simtemp.dtb`
- **Rootfs**: Initramfs with precompiled drivers

---

## Test Categories

### Multi-platform Tests (7 tests)
These tests run on all architectures with adaptive logic:

- **F-K1-TC-001**: Basic driver registration
- **F-K1-TC-003**: Platform driver with Device Tree
- **F-K8-TC-002**: Graceful reader exit on unload
- **F-K8-TC-003-A**: DTB overlay existence
- **F-K8-TC-003-B**: DTB driver binding
- **F-K8-TC-003**: Complete DTB functionality
- **F-K8-TC-004**: Comprehensive driver validation

### x86-Specific Tests (1 test)
Optimized for x86 architectures with specific features:

- **F-K8-TC-001**: Load/unload with `modprobe -r` for automatic dependency handling

### ARM-Specific Tests (2 tests)
Designed exclusively for QEMU ARM environment:

- **F-K1-TC-002**: QEMU boot validation
- **F-K8-TC-001-QEMU**: Load/unload in emulated ARM environment

---

## Key Differences by Architecture

### Kernel Module Handling

#### x86_64 (Host/Debian)
```bash
# Load with automatic dependency resolution
modprobe nxp_simtemp

# Unload with automatic dependency cleanup
modprobe -r nxp_simtemp
```

#### ARM (QEMU)
```bash
# Manual loading
insmod nxp_simtemp_stub.ko  # Only if needed
insmod nxp_simtemp.ko

# Manual unloading
rmmod nxp_simtemp
rmmod nxp_simtemp_stub     # Only if loaded
```

### Device Tree Support

#### x86_64
- Device Tree simulated via overlays
- DTB compilation for testing
- Emulated driver binding

#### ARM (QEMU)
- Native Device Tree from i.MX6 kernel
- Precompiled DTB: `imx6q-sabresd-with-simtemp.dtb`
- Real platform driver binding

---

## Execution Commands

### Development on x86_64
```bash
# Basic development tests
cd simtemp/tests
python3 -m pytest test_f_k1_tc_001.py test_f_k8_tc_001.py -v

# Multi-platform tests
python3 -m pytest test_f_k8_tc_002.py test_f_k8_tc_004.py -v

# DTB tests (compatible)
python3 -m pytest test_f_k8_tc_003_dtb.py -v
```

### CI/CD on ARM (QEMU)
```bash
# QEMU-specific tests
python3 -m pytest test_f_k1_tc_002.py test_f_k8_tc_001_qemu.py -v

# Multi-platform tests on ARM
python3 -m pytest test_f_k8_tc_002.py test_f_k8_tc_003_dtb.py -v
```

### Complete Execution
```bash
# Comprehensive monitor with automatic detection
python3 test_monitor.py --run-all --architecture-aware
```

---

## Current System Status

- **Host Architecture**: x86_64 (Linux-6.14.0-33-generic)
- **Platform**: Linux/Debian with glibc2.39
- **QEMU Support**: ✅ Available for ARM tests
- **Tests Implemented**: 10/10 test cases configured
- **Tests Validated**: F-K8-TC-001, F-K8-TC-002 ✅

---

## Coverage Statistics

| Metric | Value | Percentage |
|--------|-------|------------|
| **Total Tests** | 10 | 100% |
| **Multi-platform** | 7 | 70% |
| **x86-Specific** | 1 | 10% |
| **ARM-Specific** | 2 | 20% |
| **DTB Tests** | 4 | 40% |
| **QEMU Tests** | 3 | 30% |

---

## Test Configuration Files

Main configuration files:

- **`simtemp/tests/config/simtemp_tests.yml`**: Central test configuration
- **`simtemp/tests/test_f_k1_tc_001.py`**: Base functions with platform detection
- **`simtemp/tests/test_utils.py`**: QEMU utilities and platform handling

---

*Document generated on: 2025-10-21*  
*System architecture: x86_64*  
*Current branch: f-k8-tc-002-dtb-drv-bind*  
*Repository: n2Electrons/simtemp-system*