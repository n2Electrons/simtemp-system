#!/bin/bash

# Simple QEMU test to verify booting and 9P mount

QEMU_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu"
IMAGES_DIR="${QEMU_DIR}/images/system"
DTB_DIR="${QEMU_DIR}/dtb"
WORKSPACE_ROOT="/home/jorge/challenge-2509/simtemp-system"

echo "Testing QEMU boot with 9P filesystem..."

# Create a simple test script that doesn't require Python
cat > "/tmp/simple_qemu_test.sh" << 'EOF'
#!/bin/sh

echo "=== Simple QEMU Test ==="
echo "Mounting 9P filesystem..."

# Try to mount 9P
mount -t 9p -o trans=virtio,version=9p2000.L workspace /mnt/workspace 2>&1

if [ $? -eq 0 ]; then
    echo "✅ 9P mount successful"
    echo "📁 Listing workspace contents:"
    ls -la /mnt/workspace/ | head -10
    echo "📄 Test files:"
    ls -la /mnt/workspace/simtemp/tests/ | head -5
else
    echo "❌ 9P mount failed"
fi

echo ""
echo "🎯 Test completed - auto shutdown"
halt -f
EOF

chmod +x "/tmp/simple_qemu_test.sh"

echo "🧪 Running simple QEMU test..."

qemu-system-arm \
  -machine virt \
  -cpu cortex-a15 \
  -m 256M \
  -kernel "${IMAGES_DIR}/kernel-arm.img" \
  -initrd "${IMAGES_DIR}/initrd.img" \
  -append "console=ttyAMA0,115200 rdinit=/tmp/simple_qemu_test.sh" \
  -fsdev local,security_model=passthrough,id=fsdev0,path="${WORKSPACE_ROOT}" \
  -device virtio-9p-pci,id=fs0,fsdev=fsdev0,mount_tag=workspace \
  -nographic \
  -no-reboot

echo "🏁 Simple test completed"