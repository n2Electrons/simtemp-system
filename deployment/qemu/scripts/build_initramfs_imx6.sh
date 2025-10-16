#!/usr/bin/env bash
set -e

# ===========================
# CONFIGURACIÓN
# ===========================
ARCH=arm
CROSS_COMPILE=arm-linux-gnueabihf-
BUSYBOX_VERSION=1.36.1
ROOTFS_DIR=rootfs
OUT_FILE=rootfs.cpio.gz

# ===========================
# DEPENDENCIAS HOST
# ===========================
sudo apt-get update -y
sudo apt-get install -y git build-essential cpio gzip

# ===========================
# BUSYBOX COMPILACIÓN ESTÁTICA
# ===========================
rm -rf busybox-${BUSYBOX_VERSION}
git clone https://git.busybox.net/busybox busybox-${BUSYBOX_VERSION}
cd busybox-${BUSYBOX_VERSION}

make ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE defconfig
# Forzar binario estático
scripts/config --file .config --enable CONFIG_STATIC
scripts/config --file .config --disable CONFIG_FEATURE_INSTALLER
make -j"$(nproc)" ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE busybox
cd ..

# ===========================
# CREACIÓN DEL ROOTFS
# ===========================
rm -rf $ROOTFS_DIR
mkdir -p $ROOTFS_DIR/{bin,sbin,etc,proc,sys,usr/bin,usr/sbin,dev,tmp}
cp busybox-${BUSYBOX_VERSION}/busybox $ROOTFS_DIR/bin/
chmod +x $ROOTFS_DIR/bin/busybox
( cd $ROOTFS_DIR/bin && ln -sf busybox sh )

# ===========================
# SCRIPT INIT
# ===========================
cat > $ROOTFS_DIR/init << 'EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
echo "=== initramfs listo ==="
exec /bin/sh
EOF
chmod +x $ROOTFS_DIR/init

# ===========================
# EMPAQUETAR INITRAMFS
# ===========================
cd $ROOTFS_DIR
find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../$OUT_FILE
cd ..

# ===========================
# RESULTADOS
# ===========================
echo
echo "==============================================="
echo "Initramfs generado: $OUT_FILE"
echo "Verifica:"
echo "  file $OUT_FILE"
echo "  file $ROOTFS_DIR/bin/busybox"
echo "==============================================="
