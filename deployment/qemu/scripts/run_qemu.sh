#!/bin/sh
qemu-system-arm -M sabrelite \
                -cpu cortex-a9 \
                -m 1024 -nographic -no-reboot \
                -kernel linux-imx-5.10/arch/arm/boot/zImage \
                -dtb linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd.dtb \
                -initrd rootfs.cpio.gz \
                -append "console=ttymxc0,115200 earlycon=imx,0x021e8000,115200 rdinit=/init loglevel=8" \
                -monitor telnet:127.0.0.1:45454,server,nowait
