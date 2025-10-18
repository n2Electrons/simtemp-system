#!/bin/sh

DOCKER_ENV="/.dockerenv"

if [ -e "$DOCKER_ENV" ]; then
  KERNEL_IMAGE="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/build/arch/arm/boot/zImage"
  DTB_FILE="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/build/arch/arm/boot/dts/imx6q-sabrelite.dtb"
  ROOTFS_IMAGE="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/rootfs.cpio.gz"
else
  KERNEL_IMAGE="linux-imx-5.10/arch/arm/boot/zImage"
  DTB_FILE="linux-imx-5.10/arch/arm/boot/dts/imx6q-sabrelite.dtb"
  ROOTFS_IMAGE="rootfs.cpio.gz"
fi

qemu-system-arm -M sabrelite \
                -cpu cortex-a9 \
                -m 1024 -nographic -no-reboot \
                -kernel $KERNEL_IMAGE \
                -dtb $DTB_FILE \
                -initrd $ROOTFS_IMAGE \
                -append "console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 rdinit=/init loglevel=8" \
                -monitor telnet:127.0.0.1:45454,server,nowait
