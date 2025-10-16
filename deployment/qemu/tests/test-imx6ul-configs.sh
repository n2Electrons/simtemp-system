#!/bin/bash

# Test i.MX6UL QEMU with different configurations

QEMU_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu"
IMAGES_DIR="${QEMU_DIR}/images/system"
DTB_DIR="${QEMU_DIR}/dtb"

echo "Testing i.MX6UL QEMU configurations..."
echo "Kernel: ${IMAGES_DIR}/kernel-arm.img"
echo "InitRD: ${IMAGES_DIR}/initrd.img"
echo ""

echo "=== Test 1: Basic boot without DTB ==="
timeout 15 qemu-system-arm \
  -machine mcimx6ul-evk \
  -cpu cortex-a7 \
  -m 256M \
  -kernel "${IMAGES_DIR}/kernel-arm.img" \
  -initrd "${IMAGES_DIR}/initrd.img" \
  -append "console=ttymxc0,115200 earlyprintk" \
  -nographic \
  -serial stdio

echo ""
echo "=== Test 2: With Device Tree ==="
timeout 15 qemu-system-arm \
  -machine mcimx6ul-evk \
  -cpu cortex-a7 \
  -m 256M \
  -kernel "${IMAGES_DIR}/kernel-arm.img" \
  -initrd "${IMAGES_DIR}/initrd.img" \
  -dtb "${DTB_DIR}/imx6ul-simtemp.dtb" \
  -append "console=ttymxc0,115200 earlyprintk" \
  -nographic \
  -serial stdio

echo ""
echo "=== Test 3: Alternative console ==="
timeout 15 qemu-system-arm \
  -machine mcimx6ul-evk \
  -cpu cortex-a7 \
  -m 256M \
  -kernel "${IMAGES_DIR}/kernel-arm.img" \
  -initrd "${IMAGES_DIR}/initrd.img" \
  -dtb "${DTB_DIR}/imx6ul-simtemp.dtb" \
  -append "console=ttyS0,115200 earlyprintk debug" \
  -nographic \
  -serial stdio

echo ""
echo "All tests completed"