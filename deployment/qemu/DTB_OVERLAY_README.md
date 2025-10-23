# DTB Overlay Integration for SimTemp Driver

This document provides comprehensive documentation for the Device Tree Blob (DTB) overlay integration used in the SimTemp driver testing with QEMU.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Build Integration](#build-integration)
- [Files Structure](#files-structure)
- [Device Tree Node](#device-tree-node)
- [Usage](#usage)
- [Testing Integration](#testing-integration)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

## Overview

Instead of modifying the base i.MX6 DTB directly, we use **Device Tree Overlays** to add the SimTemp device node dynamically. This approach provides:

- ✅ **Modular Design**: Base DTB remains unchanged
- ✅ **Maintainable**: Changes isolated to overlay files  
- ✅ **Reusable**: Same overlay can be applied to different base DTBs
- ✅ **Standard Compliant**: Follows Linux kernel overlay conventions
- ✅ **CI/CD Ready**: Automated build integration

## Architecture

### Component Overview
```
SimTemp Driver Testing Environment
├── Base DTB (i.MX6 SABRE)
├── SimTemp Overlay (DTBO)
├── Combined DTB (Base + Overlay)
├── QEMU ARM Emulation
└── Driver Testing Framework
```

### Build Flow Integration
```
make nxp-driver-arm
├── 🔧 Cross-compile ARM Driver
├── 🔐 Sign kernel module
├── 📦 Populate prebuilt directories  
├── 🗄️ Update QEMU rootfs
└── 🗂️ Build DTB with SimTemp overlay  ← AUTOMATED
```

## Build Integration

### Automatic Integration

The DTB overlay build is **automatically integrated** into the ARM driver build process:

```bash
cd simtemp/kernel
make nxp-driver-arm
```

This single command now:
1. Builds the ARM kernel module
2. Signs and packages the module
3. Updates QEMU rootfs with prebuilt driver
4. **Builds DTB with SimTemp overlay** *(NEW)*

### Integration Details

The integration is implemented in `simtemp/scripts/populate_arm_driver.sh`:

```bash
# Build DTB with SimTemp overlay for QEMU testing
print_step "Building DTB with SimTemp overlay for QEMU..."
DTB_OVERLAY_SCRIPT="$PROJECT_ROOT/deployment/qemu/scripts/build_dtb_with_overlay.sh"

if [ -x "$DTB_OVERLAY_SCRIPT" ]; then
    if ! "$DTB_OVERLAY_SCRIPT"; then
        print_warning "DTB overlay build failed, but continuing..."
        print_warning "QEMU may use base DTB without SimTemp device node"
    else
        print_success "DTB with SimTemp overlay built successfully!"
    fi
else
    print_warning "DTB overlay script not found: $DTB_OVERLAY_SCRIPT"
    print_warning "QEMU will use base DTB without SimTemp device node"
fi
```

### Error Handling Strategy
- **DTB build failure**: Warning issued, driver build continues
- **Missing script**: Warning with fallback to base DTB
- **Script not executable**: Clear remediation advice provided

## Files Structure

### Source Files
```
deployment/qemu/
├── overlay/
│   ├── nxp-simtemp-overlay.dts     # Source overlay definition
│   └── nxp-simtemp-overlay.dtbo    # Compiled overlay blob
├── scripts/
│   ├── build_dtb_with_overlay.sh   # Automated build script
│   └── run_qemu.sh                 # QEMU launcher (uses combined DTB)
└── linux-imx-5.10/arch/arm/boot/dts/
    └── imx6q-sabresd.dtb           # Base DTB
```

### Generated Files
```
deployment/qemu/
└── imx6q-sabresd-with-simtemp.dtb  # Combined DTB (auto-generated)
```

### Build Artifacts
```
simtemp/kernel/obj/
├── nxp_simtemp.ko                  # Signed ARM kernel module
└── [other build artifacts]

deployment/qemu/rootfs/
├── rootfs.cpio.gz                  # Updated QEMU rootfs
└── tmp/prebuild/simtemp-driver/    # Prebuilt driver files
    ├── nxp_simtemp.ko
    ├── Module.symvers
    ├── modules.order
    └── nxp_simtemp.mod
```

## Device Tree Node

### Node Structure

The overlay adds this device node to the root of the device tree:

```dts
simtemp@0 {
    compatible = "nxp,simtemp";
    reg = <0x0 0x1000>;
    sampling_ms = <100>;        // 100ms sampling interval
    threshold_mC = <75000>;     // 75°C threshold in millidegrees
    mode = "continuous";        // Continuous monitoring mode
    status = "okay";
};
```

### Properties Explanation

| Property | Type | Value | Description |
|----------|------|-------|-------------|
| `compatible` | string | "nxp,simtemp" | Driver binding identifier |
| `reg` | cells | <0x0 0x1000> | Memory region (4KB at 0x0) |
| `sampling_ms` | u32 | 100 | Sampling interval in milliseconds |
| `threshold_mC` | u32 | 75000 | Temperature threshold in millidegrees |
| `mode` | string | "continuous" | Operating mode |
| `status` | string | "okay" | Device enable status |

### Compatible Strings

The driver supports multiple compatible strings for flexibility:

```c
static const struct of_device_id nxp_simtemp_of_match[] = {
    { .compatible = "nxp,simtemp" },
    { .compatible = "simtemp,temperature-sensor" },
    { .compatible = "simtemp,temperature-sensor-overlay" },
    { }
};
```

## Usage

### Standard Development Workflow

```bash
# 1. Build ARM driver with DTB overlay (everything automated)
cd simtemp/kernel
make nxp-driver-arm

# 2. Run QEMU tests (automatically uses combined DTB)
cd ../tests
python3 -m pytest test_f_k8_tc_003_dtb.py -v

# 3. Start QEMU for interactive testing
cd ../../deployment/qemu
./scripts/run_qemu.sh
```

### Manual DTB Operations

#### Build DTB with Overlay
```bash
cd deployment/qemu
./scripts/build_dtb_with_overlay.sh
```

#### Verify Combined DTB
```bash
# Check DTB contains SimTemp device
dtc -I dtb -O dts imx6q-sabresd-with-simtemp.dtb | grep -A 10 simtemp

# Expected output:
# simtemp@0 {
#     compatible = "nxp,simtemp";
#     reg = <0x00 0x1000>;
#     sampling_ms = <0x64>;
#     threshold_mC = <0x124f8>;
#     mode = "continuous";
#     status = "okay";
# };
```

#### Verify QEMU Configuration
```bash
# Check QEMU uses combined DTB
grep DTB_FILE scripts/run_qemu.sh
# Should show: DTB_FILE="imx6q-sabresd-with-simtemp.dtb"
```

### Manual Build Process

If needed, you can build the overlay manually:

```bash
# Build base DTB
cd linux-imx-5.10
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- imx6q-sabresd.dtb

# Build overlay
cd ../overlay
dtc -@ -I dts -O dtb -o nxp-simtemp-overlay.dtbo nxp-simtemp-overlay.dts

# Combine with fdtoverlay
cd ..
fdtoverlay -i linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb \
           -o imx6q-sabresd-with-simtemp.dtb \
           overlay/nxp-simtemp-overlay.dtbo
```

## Testing Integration

### Test Framework Compatibility

The DTB overlay integrates seamlessly with the test framework:

```python
def test_dtb_driver_binding():
    """Test driver binding to DTB node"""
    # Test automatically detects DTB environment
    # and verifies compatible string matching
```

### Test Flow

1. **DTB Overlay Compilation** - Verifies overlay builds correctly
2. **Driver Binding** - Checks driver recognizes compatible strings  
3. **Property Parsing** - Tests DTB property extraction (when implemented)
4. **Device Functionality** - Validates device operations (when implemented)

### TDD Benefits

This overlay approach enables proper **Test-Driven Development**:

- 🔴 **Red Phase**: DTB structure ready, functionality tests fail (as expected)
- 🟢 **Green Phase**: Implement driver features to make tests pass
- 🔵 **Refactor Phase**: Modify overlay/driver without breaking tests

### Test Execution

```bash
# Run all DTB tests
cd simtemp/tests
python3 -m pytest test_f_k8_tc_003_dtb.py -v

# Run specific DTB binding test
python3 -m pytest test_f_k8_tc_003_dtb.py::test_dtb_driver_binding -v

# Run with QEMU environment
QEMU_TEST=1 python3 -m pytest test_f_k8_tc_003_dtb.py -v
```

## Troubleshooting

### Common Issues

#### DTB Build Fails
```bash
# Check build dependencies
which fdtoverlay dtc

# Manually rebuild DTB overlay
cd deployment/qemu
./scripts/build_dtb_with_overlay.sh

# Check for errors in build output
```

#### Missing Base DTB
```bash
# Rebuild kernel DTBs
cd deployment/qemu/linux-imx-5.10
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- imx6q-sabresd.dtb
```

#### Missing Overlay DTBO
```bash
# Rebuild overlay
cd deployment/qemu/overlay
dtc -@ -I dts -O dtb -o nxp-simtemp-overlay.dtbo nxp-simtemp-overlay.dts
```

#### QEMU Uses Wrong DTB
```bash
# Check QEMU script configuration
grep DTB_FILE deployment/qemu/scripts/run_qemu.sh

# Should show combined DTB path, not base DTB
```

#### Test Failures
```bash
# Verify DTB contains device node
cd deployment/qemu
dtc -I dtb -O dts imx6q-sabresd-with-simtemp.dtb | grep simtemp

# Check driver module info
cd simtemp/kernel/obj
modinfo nxp_simtemp.ko | grep alias
```

### Debug Commands

```bash
# Verify overlay syntax
cd deployment/qemu/overlay
dtc -I dts -O dtb nxp-simtemp-overlay.dts > /dev/null

# Check base DTB
cd ../linux-imx-5.10/arch/arm/boot/dts
dtc -I dtb -O dts imx6q-sabresd.dtb > /tmp/base.dts

# Verify combined DTB
cd ../../
dtc -I dtb -O dts imx6q-sabresd-with-simtemp.dtb > /tmp/combined.dts
diff /tmp/base.dts /tmp/combined.dts
```

## Advanced Topics

### Multiple Overlays

To support multiple test overlays:

```bash
# Create additional overlays
cd overlay
cp nxp-simtemp-overlay.dts test-variant-overlay.dts
# Edit as needed

# Build multiple overlays
dtc -@ -I dts -O dtb -o test-variant-overlay.dtbo test-variant-overlay.dts

# Combine multiple overlays
fdtoverlay -i ../linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb \
           -o imx6q-sabresd-multi-test.dtb \
           nxp-simtemp-overlay.dtbo \
           test-variant-overlay.dtbo
```

### Conditional Building

Add conditional building to avoid unnecessary rebuilds:

```bash
# Check if rebuild is needed
if [ overlay/nxp-simtemp-overlay.dts -nt imx6q-sabresd-with-simtemp.dtb ]; then
    echo "Overlay source newer, rebuilding DTB..."
    ./scripts/build_dtb_with_overlay.sh
fi
```

### Docker Integration

For containerized builds:

```dockerfile
# Install DTB tools
RUN apt-get update && apt-get install -y device-tree-compiler

# Copy overlay files
COPY overlay/ /workspace/deployment/qemu/overlay/
COPY scripts/build_dtb_with_overlay.sh /workspace/deployment/qemu/scripts/

# Build DTB as part of container setup
RUN cd /workspace/deployment/qemu && ./scripts/build_dtb_with_overlay.sh
```

### CI/CD Integration

```yaml
# Example GitHub Actions step
- name: Build DTB with Overlay
  run: |
    cd deployment/qemu
    ./scripts/build_dtb_with_overlay.sh
    
- name: Verify DTB Contains SimTemp
  run: |
    cd deployment/qemu
    dtc -I dtb -O dts imx6q-sabresd-with-simtemp.dtb | grep -q "nxp,simtemp"
```

## Compatibility

- **Host Testing**: Works on x86_64 (module alias verification)
- **QEMU Testing**: Works in ARM QEMU environment (device tree verification)
- **Real Hardware**: Compatible with i.MX6 boards supporting overlays
- **Cross-Platform**: Build tools available on Ubuntu, Debian, and most Linux distributions

## Summary

The DTB overlay integration provides a robust, automated solution for SimTemp driver testing that:

1. **Automates DTB preparation** as part of the driver build
2. **Maintains clean separation** between base DTB and test additions
3. **Enables comprehensive testing** of device tree functionality
4. **Supports TDD methodology** with proper test/implementation cycles
5. **Provides clear feedback** and graceful error handling

This approach ensures that the QEMU testing environment is always ready and consistent with the driver implementation, supporting both development and CI/CD workflows.