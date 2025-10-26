#!/bin/bash

set -e
(
  cd ~/challenge-2509/simtemp-system/simtemp/kernel/ \
  && make clean \
  && make nxp-driver-arm
  ls -al ../../deployment/qemu/rootfs/tmp/prebuild/simtemp-driver/nxp_simtemp.ko
  date
)
