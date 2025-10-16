# QEMU Configuration for i.MX6 Development

## Overview

This document provides comprehensive configuration details for running NXP i.MX6 kernels in QEMU for development, testing, and Jenkins CI/CD integration.

## Project Context

**Repository**: simtemp-system  
**Branch**: f-k1-enabler-qemu-infra  
**Purpose**: Device Tree overlay testing for temperature sensor simulation  
**Target Hardware**: Freescale i.MX6 Quad SABRE Lite Board  

## Kernel Configuration

### Source
- **Kernel**: NXP linux-imx-5.10.72-2.2.0
- **Repository**: https://github.com/nxp-imx/linux-imx
- **Branch**: lf-5.10.72-2.2.0
- **Configuration**: imx_v6_v7_defconfig (modified)

### Build Environment
```bash
# Cross-compilation toolchain
export ARCH=arm
export CROSS_COMPILE=arm-linux-gnueabihf-

# Toolchain info
arm-linux-gnueabihf-gcc (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0
```

### Essential Kernel Config Options
```bash
CONFIG_PRINTK=y                    # Enable kernel logging
CONFIG_SERIAL_EARLYCON=y           # Early console support
CONFIG_SERIAL_IMX=y                # i.MX serial driver
CONFIG_SERIAL_IMX_CONSOLE=y        # i.MX console support
CONFIG_DEBUG_KERNEL=y              # Debug kernel features
CONFIG_DYNAMIC_DEBUG=y             # Dynamic debug support
```

### Disabled Components (for compilation success)
```bash
# ATA/AHCI drivers disabled due to compilation issues
CONFIG_ATA=n
CONFIG_SATA_AHCI=n

# GPU drivers disabled due to compilation issues  
CONFIG_DRM_ETNAVIV=n
CONFIG_DRM_IMX=n
```

## QEMU Configuration

### Working QEMU Command
```bash
qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel arch/arm/boot/zImage \
    -dtb arch/arm/boot/dts/imx6q-sabrelite.dtb \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 loglevel=8 debug" \
    -no-reboot
```

### QEMU Parameters Explanation

| Parameter | Value | Description |
|-----------|--------|-------------|
| `-M` | `sabrelite` | Machine type: Freescale i.MX6 Quad SABRE Lite Board |
| `-cpu` | `cortex-a9` | CPU type: ARM Cortex-A9 (matches i.MX6 Quad) |
| `-m` | `1024` | Memory: 1GB RAM |
| `-nographic` | - | No graphical output, console only |
| `-kernel` | `zImage` | ARM kernel image location |
| `-dtb` | `imx6q-sabrelite.dtb` | Device Tree Blob for SABRE Lite |
| `-append` | kernel cmdline | Boot parameters (see below) |
| `-no-reboot` | - | Exit QEMU instead of rebooting on panic |

### Kernel Command Line Parameters

```bash
console=ttymxc0,115200 earlycon=imx,0x02020000,115200 loglevel=8 debug
```

| Parameter | Value | Description |
|-----------|--------|-------------|
| `console` | `ttymxc0,115200` | Main console on i.MX UART0 at 115200 baud |
| `earlycon` | `imx,0x02020000,115200` | Early console for boot messages |
| `loglevel` | `8` | Maximum kernel log verbosity |
| `debug` | - | Enable additional debug output |

### Critical Configuration Notes

1. **Console Port**: Must use `ttymxc0` (NOT `ttymxc1`)
   - `ttymxc1` results in no console output
   - `ttymxc0` maps to the correct UART in QEMU sabrelite machine

2. **Earlycon Address**: `0x02020000` is the correct i.MX6 UART0 base address
   - This enables very early boot message visibility
   - Essential for debugging kernel boot issues

3. **Serial Configuration**: Do NOT use `-serial stdio` 
   - Conflicts with `-nographic` option
   - Results in "cannot use stdio by multiple character devices" error

## File Locations

### Kernel Files
```
linux-imx-5.10/
├── arch/arm/boot/zImage              # Main kernel image (9.8MB)
├── arch/arm/boot/dts/
│   └── imx6q-sabrelite.dtb          # Device Tree Blob (48KB)
└── .config                          # Kernel configuration
```

### Test Scripts
```
deployment/qemu/scripts/
├── test-compiled-kernel.sh          # Main test script
├── successful-kernel-config.md      # Success documentation
└── QEMU_FOR_I.MX6.md               # This documentation
```

## Boot Process Verification

### Successful Boot Indicators
```
[    0.000000] Booting Linux on physical CPU 0x0
[    0.000000] Linux version 5.10.72 (jorge@n2e-box) (arm-linux-gnueabihf-gcc...)
[    0.000000] CPU: ARMv7 Processor [410fc090] revision 0 (ARMv7), cr=10c5387d
[    0.000000] OF: fdt: Machine model: Freescale i.MX6 Quad SABRE Lite Board
[    5.156334] printk: console [ttymxc0] enabled
[    6.732385] Kernel panic - not syncing: VFS: Unable to mount root fs...
```

### Expected Final State
- Kernel boots completely through hardware initialization
- All drivers load successfully
- Console output is fully visible
- Final panic on root filesystem is expected (no initramfs provided)
- This confirms kernel is ready for Device Tree overlay testing

### Boot Success Checklist
- ✅ Kernel loads and detects machine model correctly
- ✅ Memory initialization successful (681476K/1048576K available)
- ✅ Console output fully visible with earlycon + main console
- ✅ Device Tree overlay support ready
- ✅ All essential drivers load correctly
- ✅ Boot completes to expected root filesystem error

The final kernel panic with "VFS: Unable to mount root fs on unknown-block(0,0)" is expected and indicates successful kernel boot to userspace initialization. This confirms the kernel is properly compiled and ready for Device Tree overlay testing.

## Tested Configuration Summary

**Date**: October 15, 2025  
**Kernel**: NXP linux-imx-5.10.72-2.2.0  
**Target**: i.MX6 Quad SABRE Lite Board  
**Status**: ✅ VERIFIED WORKING

### Key Success Factors
1. **Console Port**: `ttymxc0,115200` (NOT ttymxc1)
2. **Earlycon Address**: `imx,0x02020000,115200` (correct i.MX6 UART0)
3. **Machine Type**: `sabrelite` (exact match with DTB)
4. **CPU Type**: `cortex-a9` (explicit specification)
5. **Debug Options**: `loglevel=8 debug` (full visibility)

## Usage Examples

### Basic Kernel Test
```bash
#!/bin/bash
cd /path/to/linux-imx-5.10
timeout 60s qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel arch/arm/boot/zImage \
    -dtb arch/arm/boot/dts/imx6q-sabrelite.dtb \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 loglevel=8 debug" \
    -no-reboot
```

### Jenkins Integration
```bash
# Use in Jenkins pipeline
./deployment/qemu/scripts/test-compiled-kernel.sh
```

### Interactive Testing
```bash
# Run without timeout for interactive debugging
qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel arch/arm/boot/zImage \
    -dtb arch/arm/boot/dts/imx6q-sabrelite.dtb \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 loglevel=8 debug"
```

## Troubleshooting

### Common Issues

1. **No Console Output**
   - **Cause**: Using `ttymxc1` instead of `ttymxc0`
   - **Solution**: Change console parameter to `console=ttymxc0,115200`

2. **Serial Device Conflict**
   - **Error**: "cannot use stdio by multiple character devices"
   - **Solution**: Remove `-serial stdio` parameter (not needed with `-nographic`)

3. **Kernel Compilation Failures**
   - **Cause**: ATA/AHCI or GPU drivers
   - **Solution**: Disable problematic drivers in kernel config

4. **Early Boot Failures**
   - **Solution**: Ensure earlycon is configured: `earlycon=imx,0x02020000,115200`

### Debug Commands

```bash
# Check kernel configuration
grep -E "CONFIG_PRINTK|CONFIG_SERIAL" .config

# Verify file sizes
ls -lh arch/arm/boot/zImage arch/arm/boot/dts/imx6q-sabrelite.dtb

# Test QEMU installation
qemu-system-arm --version
```

## Performance Notes

- **Boot Time**: ~6-7 seconds to kernel panic (expected)
- **Memory Usage**: 1GB allocated, ~680MB available to kernel
- **CPU Emulation**: Single core Cortex-A9 sufficient for testing

## Next Steps

1. Add initramfs or root filesystem for complete boot testing
2. Integrate Device Tree overlay testing
3. Add automated testing in Jenkins pipeline
4. Consider adding network configuration for advanced testing

## References

- [QEMU ARM System Emulation](https://qemu-project.gitlab.io/qemu/system/target-arm.html)
- [i.MX6 Quad SABRE Lite Documentation](https://www.nxp.com/design/development-boards/i-mx-evaluation-and-development-boards/sabre-board-for-smart-devices-based-on-the-i-mx-6quad-applications-processors:RD-IMX6Q-SABRE)
- [NXP linux-imx Repository](https://github.com/nxp-imx/linux-imx)
- [Device Tree Overlay Documentation](https://www.kernel.org/doc/Documentation/devicetree/overlay-notes.txt)