#!/bin/bash

# Test QEMU with mcimx6ul-evk (known working machine)

QEMU_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu"
IMAGES_DIR="${QEMU_DIR}/images/system"
DTB_DIR="${QEMU_DIR}/dtb"

echo "Testing QEMU with mcimx6ul-evk machine..."
echo "Kernel: ${IMAGES_DIR}/kernel-arm.img"
echo "InitRD: ${IMAGES_DIR}/initrd.img"
echo "DTB: ${DTB_DIR}/imx6ul-simtemp.dtb"
echo ""

echo "Starting QEMU (should show boot messages):"
echo "=========================================="

timeout 15 qemu-system-arm \
  -machine mcimx6ul-evk \
  -cpu cortex-a7 \
  -m 256M \
  -kernel "${IMAGES_DIR}/kernel-arm.img" \
  -initrd "${IMAGES_DIR}/initrd.img" \
  -dtb "${DTB_DIR}/imx6ul-simtemp.dtb" \
  -append "console=ttymxc0,115200" \
  -nographic \
  -serial stdio

echo ""
echo "QEMU test completed."