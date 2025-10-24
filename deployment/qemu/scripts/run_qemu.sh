#!/bin/sh

DOCKER_ENV="/.dockerenv"

if [ -e "$DOCKER_ENV" ]; then
  KERNEL_IMAGE="/workspace/deployment/qemu/linux-build-imx/arch/arm/boot/zImage"
  DTB_FILE="/workspace/deployment/qemu/imx6q-sabresd-with-simtemp.dtb"
  ROOTFS_IMAGE="/workspace/deployment/qemu/rootfs.cpio.gz"
else
  KERNEL_IMAGE="linux-build-imx/arch/arm/boot/zImage"
  DTB_FILE="imx6q-sabresd-with-simtemp.dtb"
  ROOTFS_IMAGE="rootfs.cpio.gz"
fi

echo "Current working directory: $(pwd)"
echo "KERNEL_IMAGE env var: '$KERNEL_IMAGE'"
echo "DTB_FILE env var: '$DTB_FILE'"
echo "ROOTFS_IMAGE env var: '$ROOTFS_IMAGE'"

# Set default ports if not provided
SOCKET_PORT=${SOCKET_PORT:-4444}

echo "SOCKET_PORT: $SOCKET_PORT"

# ARM QEMU with socket serial interface for CLI access
# No monitor needed - simplified configuration
# Direct socket access to ARM system shell

qemu-system-arm -M sabrelite \
                -cpu cortex-a9 \
                -m 1024 -nographic -no-reboot \
                -kernel $KERNEL_IMAGE \
                -dtb $DTB_FILE \
                -initrd $ROOTFS_IMAGE \
                -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 rdinit=/init quiet loglevel=8 initcall_debug printk.time=1 modprobe.blacklist=mxc_v4l2_output,imx-ipuv3,imx6q-vdoa,imx-vpu,imxdrm,imx-hdmi,galcore,max8903_driver,max8903,max11801_ts,max11801,pfuze100,pfuze100-regulator,max8903_charger,max8903-charger,pfuze100_regulator,pfuze-regulator,max8903_driver_init" \
                -monitor none \
                -chardev socket,id=mysensor,server=on,host=127.0.0.1,port=${SOCKET_PORT} \
                -serial chardev:mysensor &

echo "QEMU started in background with socket on port ${SOCKET_PORT}"
echo "Connect with: telnet 127.0.0.1 ${SOCKET_PORT}"
echo "QEMU PID: $!"
