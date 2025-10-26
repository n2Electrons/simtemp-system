#!/bin/bash

set -e
(
  cd ~/challenge-2509/simtemp-system/simtemp/kernel/ \
  && make clean \
  && make nxp-driver-arm
  echo "Built kernel module:"
  ls -al ../../deployment/qemu/rootfs/tmp/prebuild/simtemp-driver/nxp_simtemp.ko
  echo "Root filesystem:"
  ls -al ../../deployment/qemu/rootfs.cpio.gz
  date
)
