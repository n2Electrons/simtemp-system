# i.MX6 QEMU: Build Kernel (lf-5.10.72-2.2.0) + Initramfs (BusyBox)

Comprehensive guide to build the **NXP linux‑imx kernel (lf‑5.10.72‑2.2.0)** and a **static BusyBox initramfs (rootfs.cpio.gz)** ready for **QEMU i.MX6 (ARMv7)**.

---

## 0) Host dependencies (Ubuntu)

```bash
sudo apt-get update -y
sudo apt-get install -y   build-essential   libncurses-dev   flex   bison   libssl-dev   bc   gcc-arm-linux-gnueabihf   lzop   busybox-static   python3-minimal   git   dwarves   cpio
```

---

## 1) Build the NXP Kernel (lf-5.10.72-2.2.0)

Save as **build_kernel_imx6_5.10.72.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Configuration
REPO=https://github.com/nxp-imx/linux-imx.git
BRANCH=lf-5.10.72-2.2.0
ARCH=arm
CROSS_COMPILE=arm-linux-gnueabihf-
KDIR=linux-imx-5.10.72

# Clone repository
rm -rf "$KDIR"
git clone --depth=1 -b "$BRANCH" "$REPO" "$KDIR"
cd "$KDIR"

# Base config
export ARCH CROSS_COMPILE
export KCFLAGS='-march=armv7-a -marm'
make mrproper
make imx_v6_v7_defconfig

# Enable overlays and early serial console
./scripts/config --enable CONFIG_OF_OVERLAY
./scripts/config --enable CONFIG_OF_CONFIGFS
./scripts/config --enable CONFIG_CONFIGFS_FS
./scripts/config --enable CONFIG_IKCONFIG
./scripts/config --enable CONFIG_IKCONFIG_PROC
./scripts/config --enable CONFIG_PRINTK
./scripts/config --enable CONFIG_SERIAL_IMX
./scripts/config --enable CONFIG_SERIAL_IMX_CONSOLE
./scripts/config --enable CONFIG_SERIAL_EARLYCON

# Disable SATA/AHCI and GPU/DRM (not used in headless QEMU)
./scripts/config --disable CONFIG_ATA
./scripts/config --disable CONFIG_SATA_AHCI
./scripts/config --disable CONFIG_AHCI_IMX
./scripts/config --disable CONFIG_SATA_HOST
./scripts/config --disable CONFIG_SATA_PMP
./scripts/config --disable CONFIG_DRM_VIVANTE
./scripts/config --disable CONFIG_DRM_MSM
./scripts/config --disable CONFIG_MXC_GPU_VIV
./scripts/config --disable CONFIG_MXC_IPU3
./scripts/config --disable CONFIG_DRM

# Reduce debug verbosity
./scripts/config --disable CONFIG_DEBUG_KERNEL
./scripts/config --disable CONFIG_DYNAMIC_DEBUG

# Apply defaults for new dependencies
make olddefconfig

# Build kernel, DTBs and modules
make -j"$(nproc)" zImage dtbs modules

echo "Kernel build complete:"
echo "  arch/arm/boot/zImage"
echo "  arch/arm/boot/dts/imx6q-sabrelite.dtb, imx6q-sabresd.dtb"
```

Run:
```bash
chmod +x build_kernel_imx6_5.10.72.sh
./build_kernel_imx6_5.10.72.sh
```

Expected output:
```
arch/arm/boot/zImage
arch/arm/boot/dts/imx6q-sabrelite.dtb
arch/arm/boot/dts/imx6q-sabresd.dtb
```

---

## 2) Build Initramfs (rootfs.cpio.gz) with BusyBox



Save as **build_initramfs_imx6.sh**

```bash
#!/usr/bin/env bash
set -e

ARCH=arm
CROSS_COMPILE=arm-linux-gnueabihf-
BUSYBOX_VERSION=1.36.1
ROOTFS_DIR=rootfs
OUT_FILE=rootfs.cpio.gz

# Clone BusyBox
rm -rf busybox-${BUSYBOX_VERSION}
git clone https://git.busybox.net/busybox busybox-${BUSYBOX_VERSION}
cd busybox-${BUSYBOX_VERSION}

# Configure BusyBox
make ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE defconfig
sed -ri 's/^# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
sed -ri 's/^CONFIG_FEATURE_INSTALLER=y/# CONFIG_FEATURE_INSTALLER is not set/' .config
# Disable tc applet to avoid missing netlink headers
sed -ri 's/^CONFIG_TC=y/# CONFIG_TC is not set/' .config
sed -ri 's/^CONFIG_FEATURE_TC_.*=y/# & is not set/' .config
yes "" | make ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE oldconfig

# ARMv7 build flags
export CFLAGS_EXTRA="-march=armv7-a -marm"

# Build BusyBox
make -j"$(nproc)" ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE busybox
make ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE CONFIG_PREFIX=../rootfs install
cd ..

# Create minimal init
cat > rootfs/init << 'EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
echo "=== initramfs ready ==="
exec /bin/sh
EOF
chmod +x rootfs/init

# Package initramfs
cd rootfs
find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../$OUT_FILE
cd ..

echo "Initramfs created: $OUT_FILE"
```

Run:
```bash
chmod +x build_initramfs_imx6.sh
./build_initramfs_imx6.sh
```

Verify:
```bash
file rootfs.cpio.gz
file rootfs/bin/busybox   # should report: ARM executable, statically linked
```

---

## 3) Run on QEMU i.MX6 (SabreLite)

### Option A: SabreLite machine with SabreSD DTB (stable console)

```bash
qemu-system-arm -M sabrelite -cpu cortex-a9 -m 1024 -nographic -no-reboot   -kernel linux-imx-5.10.72/arch/arm/boot/zImage   -dtb linux-imx-5.10.72/arch/arm/boot/dts/imx6q-sabresd.dtb   -initrd rootfs.cpio.gz   -append "console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 rdinit=/init loglevel=8"
```

This configuration works reliably for headless QEMU testing even though it mixes the `sabrelite` machine with the `sabresd` device tree.

### Option B: SabreLite machine with matching DTB (requires devtmpfs + cttyhack)

Ensure the kernel has:
```
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
```

and update your `/init` as follows:
```sh
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || mount -t tmpfs -o mode=0755 none /dev
exec /bin/cttyhack /bin/sh
```

Then run:
```bash
qemu-system-arm -M sabrelite -cpu cortex-a9 -m 1024 -nographic -no-reboot   -kernel linux-imx-5.10.72/arch/arm/boot/zImage   -dtb linux-imx-5.10.72/arch/arm/boot/dts/imx6q-sabrelite.dtb   -initrd rootfs.cpio.gz   -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 rdinit=/init loglevel=8"
```

**Notes**
- `-nographic` uses your terminal. Exit with **Ctrl+a, x**.  
- `sabresd.dtb` works out of the box, while `sabrelite.dtb` requires `cttyhack` for TTY access.  

---
---

## 4) Common issues

- **Error -8 in init:** BusyBox not static or wrong architecture. Rebuild BusyBox.  
- **“VFS: Unable to mount root fs”** → missing `-initrd` or wrong `rdinit=/init`.  
- **No console output:** wrong UART configuration.  
- **Ctrl+C not working:** use **Ctrl+a, x** to exit QEMU.

---

## 5) Next step

For a complete user-space, create an ext4 image and boot with:

```bash
-drive if=sd,file=rootfs.ext4,format=raw -append "root=/dev/mmcblk0p1 rw rootwait"
```
