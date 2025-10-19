# QEMU Driver Blacklist Documentation

## Overview

This document tracks the drivers that have been blacklisted in the QEMU boot process to prevent system hangs and improve boot performance during testing and development.

## Current Blacklist

The following drivers are currently blacklisted in `deployment/qemu/scripts/run_qemu.sh` via the kernel parameter:

```bash
modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi,galcore,max8903_driver,max11801_ts
```

## Driver Details

### Video and Graphics Drivers

#### `mxc_v4l2_output`
- **Type**: Video4Linux2 output driver
- **Purpose**: Video output interface for i.MX processors
- **Issue**: Causes system hangs during QEMU emulation
- **Impact**: Video output functionality disabled in QEMU
- **Added**: 2025-10-17

#### `imx-ipuv3` 
- **Type**: Image Processing Unit driver
- **Purpose**: Hardware-accelerated image/video processing
- **Issue**: Not properly emulated in QEMU, causes timeouts
- **Impact**: Image processing acceleration disabled
- **Added**: 2025-10-17

#### `imx6q-vdoa`
- **Type**: Video Data Order Adapter driver
- **Purpose**: Video data format conversion
- **Issue**: Hardware not available in QEMU emulation
- **Impact**: Video format conversion disabled
- **Added**: 2025-10-17

#### `imx-vpu`
- **Type**: Video Processing Unit driver
- **Purpose**: Hardware video encoding/decoding
- **Issue**: VPU hardware not emulated in QEMU
- **Impact**: Hardware video processing disabled
- **Added**: 2025-10-17

#### `imxdrm`
- **Type**: Direct Rendering Manager driver
- **Purpose**: Graphics display management
- **Issue**: Display hardware emulation issues in QEMU
- **Impact**: Advanced graphics features disabled
- **Added**: 2025-10-17

#### `imx-hdmi`
- **Type**: HDMI output driver
- **Purpose**: HDMI video output support
- **Issue**: HDMI hardware not properly emulated
- **Impact**: HDMI output disabled in QEMU
- **Added**: 2025-10-17

#### `galcore`
- **Type**: GPU core driver (Vivante)
- **Purpose**: 3D graphics acceleration
- **Issue**: GPU hardware not available in QEMU
- **Impact**: 3D graphics acceleration disabled
- **Added**: 2025-10-17

### Input Drivers

#### `max11801_ts`
- **Type**: Touchscreen controller driver
- **Purpose**: Touchscreen input support
- **Issue**: Causes delays during boot, hardware not emulated
- **Impact**: Touchscreen functionality disabled in QEMU
- **Boot Message**: `input: max11801_ts as /devices/platform/.../input/input2`
- **Added**: 2025-10-18

### Power Management Drivers

#### `max8903_driver`
- **Type**: Battery charger driver
- **Purpose**: Battery charging management
- **Issue**: Power management hardware not relevant in QEMU
- **Impact**: Battery charging management disabled
- **Added**: 2025-10-17

## Kernel Boot Parameters

### Complete Command Line
```bash
console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 rdinit=/init loglevel=8 ignore_loglevel initcall_debug printk.time=1 modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi,galcore,max8903_driver,max11801_ts
```

### Debug Parameters
- `ignore_loglevel`: Show all kernel messages regardless of log level
- `initcall_debug`: Display initialization call debugging information
- `printk.time=1`: Add timestamps to kernel messages

## Boot Performance Impact

Before blacklisting these drivers, QEMU boot would:
- Hang at various driver initialization points
- Take 60+ seconds to reach initramfs
- Generate numerous timeout errors

After blacklisting:
- Faster boot process
- Reduced timeout errors
- More reliable QEMU testing environment

## Testing Environment

- **QEMU Version**: arm system emulation
- **Target**: i.MX6 SABRE Smart Device Board (`imx6q-sabresd.dtb`)
- **Machine**: `sabrelite`
- **CPU**: `cortex-a9`
- **Kernel**: linux-imx-5.10.72

## Maintenance Notes

### Adding New Drivers to Blacklist
1. Identify problematic driver from boot logs
2. Add to comma-separated list in `run_qemu.sh`
3. Update this documentation with driver details
4. Test boot performance improvement

### Removing Drivers from Blacklist
1. Ensure driver functionality is not needed for testing
2. Remove from blacklist and test boot process
3. Update documentation if removal is permanent

## Related Files

- `deployment/qemu/scripts/run_qemu.sh` - QEMU launch script
- `simtemp/tests/test_f_k1_tc_002.py` - QEMU boot test
- `simtemp/tests/test_utils.py` - Test utilities

## History

- **2025-10-17**: Initial blacklist created with video/graphics drivers
- **2025-10-18**: Added `max11801_ts` touchscreen driver