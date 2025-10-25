#!/bin/sh

# Update rootfs.cpio.gz with proper root ownership using fakeroot
# This ensures all files in the cpio archive have root:root ownership

set -e

echo "Building rootfs.cpio.gz with fakeroot for proper ownership..."

# Use fakeroot to ensure proper root ownership in cpio archive
fakeroot bash -c 'cd rootfs && chown -R root:root . && find . | cpio -H newc -o | gzip > ../rootfs.cpio.gz'

echo "Rootfs updated successfully:"
ls -lh rootfs.cpio.gz
