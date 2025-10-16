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
# DEPENDENCIAS HOST
# ===========================
sudo apt-get update -y
sudo apt-get install -y \
  build-essential \
  libncurses-dev \
  flex \
  bison \
  libssl-dev \
  bc \
  gcc-arm-linux-gnueabihf \
  lzop \
  busybox-static \
  python3-minimal \
  git \
  dwarves \
  cpio

# ===========================
# DESCARGA DEL KERNEL
# ===========================
rm -rf "$KDIR"
git clone --depth=1 -b "$BRANCH" "$REPO" "$KDIR"
cd "$KDIR"

# ===========================
# CONFIGURACIÓN BASE
# ===========================
export ARCH CROSS_COMPILE
make mrproper
make imx_v6_v7_defconfig

# ===========================
# AJUSTES DE CONFIG
# ===========================
# Habilitar overlays y consola serie temprana
./scripts/config --enable CONFIG_OF_OVERLAY
./scripts/config --enable CONFIG_OF_CONFIGFS
./scripts/config --enable CONFIG_CONFIGFS_FS
./scripts/config --enable CONFIG_IKCONFIG
./scripts/config --enable CONFIG_IKCONFIG_PROC
./scripts/config --enable CONFIG_PRINTK
./scripts/config --enable CONFIG_SERIAL_IMX
./scripts/config --enable CONFIG_SERIAL_IMX_CONSOLE
./scripts/config --enable CONFIG_SERIAL_EARLYCON

# Desactivar SATA/AHCI y gráficos (no necesarios en QEMU i.MX6 headless)
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

# Opcional: reducir ruido de depuración en kernel
./scripts/config --disable CONFIG_DEBUG_KERNEL
./scripts/config --disable CONFIG_DYNAMIC_DEBUG

# Aplicar defaults a cualquier nueva dependencia
make olddefconfig

# ===========================
# COMPILACIÓN
# ===========================
make -j"$(nproc)" zImage dtbs modules

# ===========================
# RESULTADOS
# ===========================
echo
echo "==============================================="
echo "Kernel i.MX6 compilado."
echo "  zImage: arch/arm/boot/zImage"
echo "  DTBs:   arch/arm/boot/dts/imx6q-sabrelite.dtb, imx6q-sabresd.dtb"
echo "==============================================="
