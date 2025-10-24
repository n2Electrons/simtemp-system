# SDMA and Kernel Module Disabling Guide for i.MX6

This consolidated guide covers all methods for disabling SDMA (Smart Direct Memory Access) and other problematic kernel modules on i.MX6 platforms, particularly for QEMU environments.

## Overview

SDMA and related modules can cause kernel panics or boot hangs in QEMU environments where hardware emulation is incomplete. This guide provides multiple approaches to disable these modules.

## 1. SDMA Disabling Methods

### Method 1: Device Tree Modification (Recommended)

**For specific SDMA disabling:**
```dts
&sdma {
    status = "disabled";
};
```

**Complete SDMA node override:**
```dts
sdma: sdma@20ec000 {
    compatible = "fsl,imx6q-sdma", "fsl,imx35-sdma";
    reg = <0x020ec000 0x4000>;
    interrupts = <0 2 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&clks IMX6QDL_CLK_IPG>,
             <&clks IMX6QDL_CLK_SDMA>;
    clock-names = "ipg", "ahb";
    #dma-cells = <3>;
    fsl,sdma-ram-script-name = "imx/sdma/sdma-imx6q.bin";
    status = "disabled"; // <-- ADD THIS LINE
};
```

### Method 2: Remove DMA from UART Nodes

For UARTs that cause panics when accessing (e.g., ttymxc1):

**Before:**
```dts
&uart1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart1>;
    status = "okay";
    dmas = <&sdma 26 4 0>, <&sdma 27 4 0>;
    dma-names = "rx", "tx";
};
```

**After:**
```dts
&uart1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart1>;
    status = "okay";
    // dmas = <&sdma 26 4 0>, <&sdma 27 4 0>;
    // dma-names = "rx", "tx";
};
```

### Method 3: Kernel Configuration

Disable SDMA at build time:
```bash
CONFIG_IMX_SDMA=n
```

Or build as module for runtime blacklisting:
```bash
CONFIG_IMX_SDMA=m
```

### Method 4: Runtime Blacklisting (Module Only)

If built as module:
```bash
echo "blacklist imx-sdma" > /etc/modprobe.d/blacklist-sdma.conf
```

Or via kernel command line:
```bash
modprobe.blacklist=imx-sdma
```

## 2. Other Problematic Modules for QEMU

### Complete Blacklist for QEMU Boot

Add to kernel command line for comprehensive driver blacklisting:
```bash
modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi,galcore,max8903_driver,max11801_ts,imx-sdma
```

### Individual Module Descriptions

#### Video and Graphics Drivers
- **`mxc_v4l2_output`**: Video4Linux2 output driver - causes system hangs in QEMU
- **`imx-ipuv3`**: Image Processing Unit driver - hardware not emulated
- **`imx6q-vdoa`**: Video Data Order Adapter - not available in QEMU
- **`imx-vpu`**: Video Processing Unit - VPU hardware not emulated
- **`imxdrm`**: Direct Rendering Manager - display hardware emulation issues
- **`imx-hdmi`**: HDMI output driver - HDMI hardware not emulated
- **`galcore`**: GPU core driver (Vivante) - 3D acceleration not available

#### Input Drivers
- **`max11801_ts`**: Touchscreen controller - causes boot delays, hardware not emulated

#### Power Management Drivers
- **`max8903_driver`**: Battery charger driver - power management hardware not relevant

#### DMA Controllers
- **`imx-sdma`**: Smart Direct Memory Access - see Section 1 for detailed SDMA handling

### Individual Module Disabling

**Touchscreen (MAX11801):**
```bash
scripts/config --disable TOUCHSCREEN_MAX11801
```

**Charger (MAX8903):**
```bash
scripts/config --disable CHARGER_MAX8903
```

**Voltage Regulator (PFUZE100):**
```bash
scripts/config --disable REGULATOR_PFUZE100
```

**Graphics/Display Modules:**
```bash
scripts/config --disable DRM_IMX
scripts/config --disable DRM_IMX_IPUV3
scripts/config --disable DRM_IMX_HDMI
scripts/config --disable IMX_IPUV3_CORE
scripts/config --disable VIDEO_IMX_VDOA
scripts/config --disable MXC_VPU
scripts/config --disable MXC_GPU_VIV
scripts/config --disable DRM_ETNAVIV
scripts/config --disable DRM_IMX_PARALLEL_DISPLAY
```

### Boot Performance Impact

**Before blacklisting:**
- Boot hangs at various driver initialization points
- Takes 60+ seconds to reach initramfs
- Generates numerous timeout errors
- System appears frozen during driver probes

**After blacklisting:**
- Faster boot process (typically <30 seconds)
- Reduced timeout errors
- More reliable QEMU testing environment
- Clean initramfs startup messages

### Device Tree Disabling

**Multiple nodes via overlay:**
```dts
/dts-v1/;
/plugin/;
/ {
    fragment@0 { 
        target-path = "/soc/aips-bus@02100000/i2c@021a4000/max11801@48"; 
        __overlay__ { status = "disabled"; }; 
    };
    fragment@1 { 
        target-path = "/soc/aips-bus@02100000/i2c@021a8000/pfuze100@08"; 
        __overlay__ { status = "disabled"; }; 
    };
    fragment@2 { 
        target-path = "/soc/aips-bus@02100000/max8903@0"; 
        __overlay__ { status = "disabled"; }; 
    };
};
```

**Apply overlay:**
```bash
fdtoverlay -o imx6q-sabrelite-disabled.dtb imx6q-sabrelite.dtb disable-nodes.overlay
```

## 3. QEMU-Specific Configuration

### Complete QEMU Command with Blacklisting

```bash
qemu-system-arm -M sabrelite -cpu cortex-a9 -m 1024 -nographic -no-reboot \
    -kernel zImage \
    -dtb imx6q-sabrelite-with-simtemp.dtb \
    -initrd rootfs.cpio.gz \
    -append "console=ttymxc0,115200 console=ttymxc1,115200 earlycon=imx,0x02020000,115200 \
             rdinit=/init quiet loglevel=8 initcall_debug printk.time=1 \
             modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi,galcore,imx-sdma" \
    -monitor none \
    -serial stdio \
    -chardev socket,id=serial1,host=127.0.0.1,port=4445,server=on,wait=off \
    -serial chardev:serial1
```

### Boot Hang Prevention

**Common command line options for QEMU:**
```bash
console=ttymxc0,115200 earlycon=ec_imx6q,0x02020000 ignore_loglevel initcall_debug printk.time=1
```

**Additional diagnostic options:**
| Option | Purpose |
|--------|---------|
| `initcall_debug` | Shows driver initialization timing |
| `clk_ignore_unused` | Prevents clock gating issues |
| `systemd.mask=systemd-random-seed.service` | Avoids entropy waits |

## 4. Verification Methods

### Check SDMA Status
```bash
# Device tree status
cat /proc/device-tree/soc/bus@2000000/sdma@20ec000/status
# Expected: "disabled"

# Kernel logs
dmesg | grep -i sdma
# Should show no driver binding or "disabled" status

# Process check
find /proc/device-tree -iname "*sdma*"
```

### Verify Module Blacklisting
```bash
# Check if modules are loaded
lsmod | grep -E "imx|sdma|v4l2|drm"

# Check blacklist files
cat /etc/modprobe.d/blacklist*.conf

# Verify no DT devices active
ls /sys/bus/i2c/devices | grep -E '1-0048|0-0008' || echo "OK: no active DT devices"
```

## 5. Troubleshooting Boot Hangs

### Common Symptoms
- Boot stops after i2c or v4l2 driver messages:
  ```
  [   11.159482] i2c /dev entries driver
  [   11.173667] mxc_v4l2_output v4l2_out: V4L2 device registered as video16
  [   11.174567] mxc_v4l2_output v4l2_out: V4L2 device registered as video17
  ```
- System appears frozen but isn't actually crashed
- Long timeouts during driver initialization
- Boot process hangs indefinitely at driver probe points

### Root Cause Analysis
**Not an actual kernel freeze**: QEMU emulates limited hardware. Drivers like IPU, VPU, and HDMI wait on non-existent devices, blocking boot progression.

### Recommended Kernel Command Line for QEMU

Use proper serial console and disable problematic subsystems:
```bash
console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 ignore_loglevel initcall_debug printk.time=1 modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi,galcore,max8903_driver,max11801_ts,imx-sdma
```

### Diagnostic Steps

1. **Enable verbose logging:**
   ```bash
   ignore_loglevel initcall_debug printk.time=1
   ```

2. **Check last driver message:**
   ```bash
   echo t > /proc/sysrq-trigger  # Dump tasks to identify hangs
   ```

3. **Progressive blacklisting:**
   Start with minimal blacklist and add modules causing hangs

4. **Additional diagnostic options:**
   | Option | Purpose |
   |--------|---------|
   | `initcall_debug` | Shows driver initialization timing |
   | `clk_ignore_unused` | Prevents clock gating issues |
   | `systemd.mask=systemd-random-seed.service` | Avoids entropy waits |

### Common Mistakes
- Using wrong console (`ttyAMA0` instead of `ttymxc0`)
- Missing rootfs specification (`root=/dev/ram0` for initramfs)
- Leaving IPU/VPU/HDMI enabled in DTS for QEMU
- Incorrect DTB path or missing DTB
- Forgetting to blacklist video drivers in QEMU environment

## 6. Architecture-Specific Notes

### For QEMU (ARM Emulation)
- **Always disable**: SDMA, IPU, VPU, HDMI, graphics modules
- **Use**: Simplified device tree without hardware-specific peripherals
- **Enable**: Serial console debugging and verbose logging

### For Real Hardware
- **Keep enabled**: Hardware-specific drivers as needed
- **Verify**: Power supplies, clocks, and pin configurations
- **Test**: Individual modules before enabling all

## 7. Build Process Integration

### Kernel Build with Disabled Modules
```bash
export ARCH=arm
export CROSS_COMPILE=arm-linux-gnueabihf-
export KCFLAGS='-march=armv7-a -marm'

# Configure
make imx_v7_defconfig

# Disable problematic modules
scripts/config --disable TOUCHSCREEN_MAX11801
scripts/config --disable CHARGER_MAX8903
scripts/config --disable REGULATOR_PFUZE100
scripts/config --disable DRM_IMX
scripts/config --disable IMX_SDMA

# Build
make olddefconfig
make -j$(nproc) zImage dtbs modules
```

### DTB Compilation
```bash
# Compile modified device tree
dtc -I dts -O dtb -o imx6q-sabrelite-disabled.dtb imx6q-sabrelite.dts

# Verify compilation
fdtdump imx6q-sabrelite-disabled.dtb | grep -A5 -B5 "status.*disabled"
```

## 8. Summary Decision Matrix

| Use Case | Recommended Method | Effectiveness |
|----------|-------------------|---------------|
| QEMU Development | Device Tree + Blacklist | ✅ Best |
| Kernel Rebuild OK | Kernel Config Disable | ✅ Permanent |
| Runtime Only | Module Blacklist | ☑️ Limited to modules |
| Quick Testing | Command Line Blacklist | ☑️ Temporary |
| Production | Device Tree Disable | ✅ Recommended |

## References

- [NXP i.MX6 Reference Manual](https://www.nxp.com/docs/en/reference-manual/IMX6DQRM.pdf)
- [QEMU i.MX6 Implementation](https://github.com/qemu/qemu/blob/master/hw/arm/fsl-imx6.c)
- [Linux Kernel Parameters](https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html)
- [Device Tree Overlays](https://docs.kernel.org/driver-api/driver-model/overlays.html)

---
© Jorge Rodriguez Moreno – i.MX6 QEMU Development