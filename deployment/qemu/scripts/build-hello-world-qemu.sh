#!/bin/bash

# Hello World QEMU Test for Jenkins Integration
set -e

QEMU_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu"
HELLO_SRC_DIR="/home/jorge/challenge-2509/simtemp-system/src/hello"
CROSS_COMPILER="arm-linux-gnueabihf-gcc"

echo "============================================="
echo "Hello World PRE-BUILD BINARY FOR QEMU Test on Jenkins"
echo "============================================="

# Check cross-compiler
if ! command -v $CROSS_COMPILER &> /dev/null; then
    echo "ERROR: ARM cross-compiler not found: $CROSS_COMPILER"
    echo "Install with: sudo apt install gcc-arm-linux-gnueabihf"
    exit 1
fi

echo "Found ARM cross-compiler: $($CROSS_COMPILER --version | head -1)"

# Build hello world using Makefile
echo "Building Hello World using Makefile..."
cd "$HELLO_SRC_DIR"
make clean
make all
make verify
make install

# Verify binary in QEMU dir
cd "$QEMU_DIR"
if [[ ! -f "hello_world" ]]; then
    echo "ERROR: Hello World binary not found after install"
    exit 1
fi

echo "Hello World binary installed successfully"

# Create enhanced rootfs with hello world
echo "Creating enhanced rootfs with hello world..."
cp hello_world rootfs/bin/

# Update init script to run hello world
cat > rootfs/init << 'EOF'
#!/bin/sh

# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys

echo "=== ARM initramfs ready ==="
echo "Linux i.MX6 ARM kernel boot successful!"
echo "ARM BusyBox working perfectly!"
echo "Device Tree overlay support ready!"
echo ""

# Run hello world test
echo "Running Hello World test..."
echo ""
/bin/hello_world
echo ""

echo "Ready for DT overlay testing!"
echo ""

# Start interactive shell
exec /bin/sh
EOF

chmod +x rootfs/init

# Repackage rootfs
echo "Repackaging rootfs with hello world..."
cd rootfs
find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../rootfs-hello.cpio.gz
cd ..

echo "Enhanced rootfs created: $(ls -lh rootfs-hello.cpio.gz | awk '{print $5}')"
echo ""
echo "============================================="
echo "Ready for QEMU Jenkins testing!"
echo "============================================="