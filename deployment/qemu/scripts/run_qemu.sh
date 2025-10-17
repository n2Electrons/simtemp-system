#!/bin/sh

# Detect QEMU binary location
# NOTE: for running QEMU inside Jenkins container, we assume /usr/bin/qemu-system-arm exists
# Refer to JENKINS_QEMU_CONTAINER_SETUP.md
QEMU_BIN=""
if [ -x "/usr/bin/qemu-system-arm" ]; then
    QEMU_BIN="/usr/bin/qemu-system-arm"
elif command -v qemu-system-arm >/dev/null 2>&1; then
    QEMU_BIN=$(command -v qemu-system-arm)
else
    echo "Error: qemu-system-arm not found. Please install QEMU ARM system emulation."
    echo "Install with: sudo apt install qemu-system-arm"
    exit 1
fi

echo "Using QEMU binary: $QEMU_BIN"

$QEMU_BIN -M sabrelite \
                -cpu cortex-a9 \
                -m 1024 -nographic -no-reboot \
                -kernel linux-imx-5.10.72/arch/arm/boot/zImage \
                -dtb linux-imx-5.10.72/arch/arm/boot/dts/imx6q-sabresd.dtb \
                -initrd rootfs.cpio.gz \
                -append "console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 rdinit=/init loglevel=8" \
                -monitor telnet:127.0.0.1:45454,server,nowait
