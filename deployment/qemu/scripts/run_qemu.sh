#!/bin/sh

DOCKER_ENV="/.dockerenv"

if [ -e "$DOCKER_ENV" ]; then
  KERNEL_IMAGE="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage"
  DTB_FILE="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
  ROOTFS_IMAGE="/var/jenkins_home/workspace/simtemp-system/deployment/qemu/rootfs.cpio.gz"
else
  KERNEL_IMAGE="linux-imx-5.10/arch/arm/boot/zImage"
  DTB_FILE="linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb"
  ROOTFS_IMAGE="rootfs.cpio.gz"
fi

echo "Current working directory: $(pwd)"
echo "KERNEL_IMAGE env var: '$KERNEL_IMAGE'"
echo "DTB_FILE env var: '$DTB_FILE'"
echo "ROOTFS_IMAGE env var: '$ROOTFS_IMAGE'"

qemu-system-arm -M sabrelite \
                -cpu cortex-a9 \
                -m 1024 -nographic -no-reboot \
                -kernel $KERNEL_IMAGE \
                -dtb $DTB_FILE \
                -initrd $ROOTFS_IMAGE \
                -append "console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 rdinit=/init \
                quiet loglevel=8 initcall_debug printk.time=1 \
                modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi, \
                galcore,max8903_driver,max8903,max11801_ts,max11801,pfuze100,pfuze100-regulator, \
                max8903_charger,max8903-charger,pfuze100_regulator,pfuze-regulator" \
#                -monitor telnet:127.0.0.1:45455,server,nowait

# To avoid annoying messages, need to unbind
# echo 1-0048 > /sys/bus/i2c/drivers/max11801_ts/unbind
# echo 3 > /proc/sys/kernel/printk



