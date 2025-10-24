#!/bin/sh

DOCKER_ENV="/.dockerenv"

if [ -e "$DOCKER_ENV" ]; then
  KERNEL_IMAGE="/workspace/deployment/qemu/linux-build-imx/arch/arm/boot/zImage"
  DTB_FILE="/workspace/deployment/qemu/imx6q-sabresd-with-simtemp.dtb"
  ROOTFS_IMAGE="/workspace/deployment/qemu/rootfs.cpio.gz"
else
  KERNEL_IMAGE="linux-build-imx/arch/arm/boot/zImage"
  #DTB_FILE="imx6q-sabresd-with-simtemp.dtb"
  #DTB_FILE="imx6q-sabrelite.dtb"
  DTB_FILE="imx6q-sabrelite-with-simtemp.dtb"
  ROOTFS_IMAGE="rootfs.cpio.gz"
fi

echo "Current working directory: $(pwd)"
echo "KERNEL_IMAGE env var: '$KERNEL_IMAGE'"
echo "DTB_FILE env var: '$DTB_FILE'"
echo "ROOTFS_IMAGE env var: '$ROOTFS_IMAGE'"


# Same setup for automation in host and in docker
# -monitor null to avoid conflicts
# -serial stdio without interactive monitor
# Let automation happen without manual intervention


qemu-system-arm -M sabrelite \
  -cpu cortex-a9 \
  -m 1024 -nographic -no-reboot \
  -kernel "$KERNEL_IMAGE" \
  -dtb "$DTB_FILE" \
  -initrd "$ROOTFS_IMAGE" \
  -append "console=ttymxc0,115200 rdinit=/init" \
  -chardev socket,id=mysensor,server=on,host=127.0.0.1,port=4445,wait=off \
  -monitor none \
  -serial stdio \
  -serial chardev:mysensor
