#!/bin/sh
cd rootfs
find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../rootfs.cpio.gz
cd ..
ls -lh rootfs.cpio.gz
