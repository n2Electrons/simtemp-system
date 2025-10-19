# Disabling Kernel Modules and DTB Nodes on i.MX6 / Linux

## 1. Introduction
On embedded systems like i.MX6, certain drivers can hang or slow down boot if the hardware is not present. They can be disabled either in the **kernel configuration** or via the **Device Tree (DTB)**.

---

## 2. Disable Kernel Modules

### 2.1 Check Current Status
From a running kernel:
```bash
zcat /proc/config.gz | grep CONFIG_XXX
```
Example:
```bash
zcat /proc/config.gz | grep CONFIG_CHARGER_MAX8903
```
If `/proc/config.gz` is missing, enable these options and rebuild:
```
CONFIG_IKCONFIG=y
CONFIG_IKCONFIG_PROC=y
```

### 2.2 Modify the `.config`
Inside the kernel source tree:
```bash
scripts/config --disable TOUCHSCREEN_MAX11801
scripts/config --disable CHARGER_MAX8903
scripts/config --disable REGULATOR_PFUZE100
scripts/config --disable DRM_IMX
scripts/config --disable DRM_IMX_IPUV3
scripts/config --disable DRM_IMX_HDMI
scripts/config --disable IMX_IPUV3_CORE
scripts/config --disable VIDEO_IMX_VDOA
scripts/config --disable VIDEO_MXC_OUTPUT
scripts/config --disable MXC_VPU
scripts/config --disable MXC_GPU_VIV
scripts/config --disable DRM_ETNAVIV
scripts/config --disable DRM_IMX_PARALLEL_DISPLAY

grep TOUCHSCREEN_MAX11801 .config
grep CHARGER_MAX8903 .config
grep REGULATOR_PFUZE100 .config
grep DRM_IMX .config
grep DRM_IMX_IPUV3 .config
grep DRM_IMX_HDMI .config
grep IMX_IPUV3_CORE .config
grep VIDEO_IMX_VDOA .config
grep VIDEO_MXC_OUTPUT .config
grep MXC_VPU .config
grep MXC_GPU_VIV .config
grep DRM_ETNAVIV .config
grep DRM_IMX_PARALLEL_DISPLAY .config
```

### 2.3 Rebuild the Kernel
```bash
export ARCH=arm
export CROSS_COMPILE=arm-linux-gnueabihf-
export ARCH CROSS_COMPILE
export KCFLAGS='-march=armv7-a -marm'
make imx_v7_defconfig
* Disable modules as mentioned in 2.2 *
make olddefconfig
make -j$(nproc) zImage dtbs modules
```

### 2.4 Disable Modules at Runtime
If the driver is built as a module (`=m`):
```bash
modprobe -r max11801_ts
echo "blacklist max11801_ts" >> /etc/modprobe.d/blacklist.conf
```
Or via bootargs (e.g. QEMU or U-Boot):
```bash
modprobe.blacklist=max11801_ts,max8903_charger,pfuze100_regulator
```

---

## 3. Disable Device Tree Nodes (DTB)

### 3.1 Permanent Method (edit DTS source)
```dts
&i2c1 { max11801@48 { status = "disabled"; }; };
&i2c2 { pfuze100@08 { status = "disabled"; }; };
&max8903 { status = "disabled"; };
&ipu1 { status = "disabled"; };
&ipu2 { status = "disabled"; };
&vpu { status = "disabled"; };
&hdmi { status = "disabled"; };
&gpu { status = "disabled"; };
```
Rebuild DTB:
```bash
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- dtbs
```

### 3.2 Without Rebuilding (overlay method)
Create `disable-nodes.overlay`:
```dts
/dts-v1/;
/plugin/;
/ {
  fragment@0 { target-path = "/soc/aips-bus@02100000/i2c@021a4000/max11801@48"; __overlay__ { status = "disabled"; }; };
  fragment@1 { target-path = "/soc/aips-bus@02100000/i2c@021a8000/pfuze100@08"; __overlay__ { status = "disabled"; }; };
  fragment@2 { target-path = "/soc/aips-bus@02100000/max8903@0"; __overlay__ { status = "disabled"; }; };
};
```
Apply the overlay:
```bash
fdtoverlay -o imx6q-sabrelite-disabled.dtb imx6q-sabrelite.dtb disable-nodes.overlay
```
Run QEMU with the patched DTB:
```bash
qemu-system-arm -M sabrelite -cpu cortex-a9 -m 1024 -nographic -serial mon:stdio   -kernel zImage -dtb imx6q-sabrelite-disabled.dtb -initrd initramfs.cpio.gz   -append "console=ttymxc0,115200 earlycon=ec_imx6q,0x02020000 loglevel=3"
```

---

## 4. Verification
```bash
dmesg | egrep -i 'max11801|max8903|pfuze|ipu|vpu|hdmi|drm' || echo "OK: no active drivers"
ls /sys/bus/i2c/devices | grep -E '1-0048|0-0008' || echo "OK: no active DT devices"
```

---

## 5. References
- https://cateee.net/lkddb/
- https://www.nxp.com/docs/en/reference-manual/IMX6DQRM.pdf
- https://docs.kernel.org/driver-api/driver-model/overlays.html
- https://github.com/qemu/qemu/blob/master/hw/arm/fsl-imx6.c
