#!/usr/bin/env bash
set -euo pipefail

ARCH=arm
CROSS_COMPILE=arm-linux-gnueabihf-
BUSYBOX_VERSION=1.36.1
ROOTFS_DIR=rootfs
OUT_FILE=rootfs.cpio.gz

# ===========================
# HOST DEPENDENCIES (Ubuntu)
# ===========================
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y git build-essential cpio gzip
fi

# ===========================
# FETCH BUSYBOX
# ===========================
rm -rf busybox-${BUSYBOX_VERSION}
git clone https://git.busybox.net/busybox busybox-${BUSYBOX_VERSION}
cd busybox-${BUSYBOX_VERSION}

# ===========================
# CONFIGURE BUSYBOX
# ===========================
make ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE defconfig

# Force static binary and disable installer
sed -ri 's/^# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
sed -ri 's/^CONFIG_FEATURE_INSTALLER=y/# CONFIG_FEATURE_INSTALLER is not set/' .config

# Disable tc applet to avoid netlink header mismatches on some hosts
sed -ri 's/^CONFIG_TC=y/# CONFIG_TC is not set/' .config
sed -ri 's/^CONFIG_FEATURE_TC_.*=y/# & is not set/' .config

yes "" | make ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE oldconfig

# Extra flags for ARMv7-A
export CFLAGS_EXTRA="-march=armv7-a -marm"

# ===========================
# BUILD & INSTALL BUSYBOX
# ===========================
make -j"$(nproc)" ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE busybox
cd ..

# Prepare rootfs layout and install BusyBox symlinks
rm -rf $ROOTFS_DIR
mkdir -p $ROOTFS_DIR
make -C busybox-${BUSYBOX_VERSION} ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE CONFIG_PREFIX=../$ROOTFS_DIR install

# Ensure minimal dirs
mkdir -p $ROOTFS_DIR/{proc,sys,dev,tmp}

# ===========================
# CREATE /init
# ===========================
cat > $ROOTFS_DIR/init << 'EOF'
#!/bin/sh
mount -t proc     proc /proc
mount -t sysfs    sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || mount -t tmpfs -o mode=0755 none /dev
echo "=== initramfs ready ==="
# Requires BusyBox cttyhack applet for a proper controlling TTY
if command -v cttyhack >/dev/null 2>&1; then
  exec /bin/cttyhack /bin/sh
else
  [ -c /dev/console ] || mknod -m 600 /dev/console c 5 1
  [ -c /dev/null ]    || mknod -m 666 /dev/null    c 1 3
  exec setsid /bin/sh </dev/console >/dev/console 2>&1
fi
EOF
chmod +x $ROOTFS_DIR/init

# ===========================
# PACKAGE INITRAMFS
# ===========================
( cd $ROOTFS_DIR && find . -print0 | cpio --null -ov --format=newc ) | gzip -9 > $OUT_FILE

echo
echo "Initramfs created: $OUT_FILE"
