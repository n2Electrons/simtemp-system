# DTB Overlay Integration for SimTemp Driver

This directory contains Device Tree Blob (DTB) overlay integration for the SimTemp driver testing in QEMU.

## Overview

Instead of modifying the base i.MX6 DTB directly, we use **Device Tree Overlays** to add the SimTemp device node dynamically. This approach is:

- ✅ **Modular**: Base DTB remains unchanged
- ✅ **Maintainable**: Changes isolated to overlay files  
- ✅ **Reusable**: Same overlay can be applied to different base DTBs
- ✅ **Standard**: Follows Linux kernel overlay conventions

## Files

### Overlay Source Files
- `overlay/nxp-simtemp-overlay.dts` - Source overlay with SimTemp device node
- `overlay/nxp-simtemp-overlay.dtbo` - Compiled overlay blob

### Build Scripts
- `scripts/build_dtb_with_overlay.sh` - Automated DTB + overlay combination
- `scripts/run_qemu.sh` - QEMU launcher (uses combined DTB)

### Generated Files  
- `imx6q-sabresd-with-simtemp.dtb` - Combined DTB for QEMU (auto-generated)

## Device Tree Node Structure

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

## Usage

### Automatic Build
The DTB with overlay is built automatically when running tests:

```bash
cd deployment/qemu
./scripts/build_dtb_with_overlay.sh
```

### Manual Build
If you need to rebuild manually:

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

### QEMU Execution
QEMU automatically uses the combined DTB:

```bash
./scripts/run_qemu.sh
```

## Testing Integration

The test suite automatically detects the overlay-based DTB configuration:

```bash
cd ../../simtemp/tests
python3 -m pytest test_f_k8_tc_003_dtb.py -v
```

### Test Flow:
1. **DTB Overlay Compilation** - Verifies overlay builds correctly
2. **Driver Binding** - Checks driver recognizes compatible strings  
3. **Property Parsing** - Tests DTB property extraction (when implemented)
4. **Device Functionality** - Validates device operations (when implemented)

## Benefits for TDD

This overlay approach enables proper **Test-Driven Development**:

- 🔴 **Red Phase**: DTB structure ready, functionality tests fail (as expected)
- 🟢 **Green Phase**: Implement driver features to make tests pass
- 🔵 **Refactor Phase**: Modify overlay/driver without breaking tests

## Verification

To verify the combined DTB contains the SimTemp device:

```bash
dtc -I dtb -O dts imx6q-sabresd-with-simtemp.dtb | grep -A 10 simtemp
```

Expected output:
```dts
simtemp@0 {
    compatible = "nxp,simtemp";
    reg = <0x00 0x1000>;
    sampling_ms = <0x64>;
    threshold_mC = <0x124f8>;
    mode = "continuous";
    status = "okay";
};
```

## Compatibility

- **Host Testing**: Works on x86_64 (module alias verification)
- **QEMU Testing**: Works in ARM QEMU environment (device tree verification)
- **Real Hardware**: Compatible with i.MX6 boards supporting overlays