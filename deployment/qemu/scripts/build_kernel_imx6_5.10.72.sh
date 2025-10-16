#!/usr/bin/env bash
set -euo pipefail

# ===========================
# CONFIG
# ===========================
REPO=https://github.com/nxp-imx/linux-imx.git
BRANCH=lf-5.10.72-2.2.0
ARCH=arm
CROSS_COMPILE=arm-linux-gnueabihf-
KDIR=linux-imx-5.10.72

# ===========================
# HOST DEPENDENCIES (Ubuntu)
# ===========================
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y     build-essential     libncurses-dev     flex     bison     libssl-dev     bc     gcc-arm-linux-gnueabihf     lzop     busybox-static     python3-minimal     git     dwarves     cpio
fi

# ===========================
# FETCH KERNEL
# ===========================
rm -rf "$KDIR"
git clone --depth=1 -b "$BRANCH" "$REPO" "$KDIR"
cd "$KDIR"

# ===========================
# BASE CONFIG
# ===========================
export ARCH CROSS_COMPILE
export KCFLAGS='-march=armv7-a -marm'
make mrproper
make imx_v6_v7_defconfig

# Ensure helper scripts (like scripts/config) are built
make scripts

# ===========================
# CONFIG TWEAKS
# ===========================
./scripts/config --enable CONFIG_OF_OVERLAY
./scripts/config --enable CONFIG_OF_CONFIGFS
./scripts/config --enable CONFIG_CONFIGFS_FS
./scripts/config --enable CONFIG_IKCONFIG
./scripts/config --enable CONFIG_IKCONFIG_PROC
./scripts/config --enable CONFIG_PRINTK
./scripts/config --enable CONFIG_SERIAL_IMX
./scripts/config --enable CONFIG_SERIAL_IMX_CONSOLE
./scripts/config --enable CONFIG_SERIAL_EARLYCON
./scripts/config --enable CONFIG_DEVTMPFS
./scripts/config --enable CONFIG_DEVTMPFS_MOUNT

# Disable SATA/AHCI and graphics (not needed for headless QEMU)
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

# Reduce debug
./scripts/config --disable CONFIG_DEBUG_KERNEL
./scripts/config --disable CONFIG_DYNAMIC_DEBUG

# Apply defaults for new deps
make olddefconfig

# ===========================
# BUILD
# ===========================
make -j"$(nproc)" zImage dtbs modules

echo
echo "Kernel build complete:"
echo "  arch/arm/boot/zImage"
echo "  arch/arm/boot/dts/imx6q-sabrelite.dtb (preferred)"
echo "  arch/arm/boot/dts/imx6q-sabresd.dtb   (alt DTB that also boots on sabrelite)"
