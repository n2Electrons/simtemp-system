#!/bin/bash
pkill -9 qemu-system-arm
ps

# Launch qemu_monitor.py in background first
#echo "Starting QEMU monitor..."
# python3 qemu_monitor.py &   # Used for DEEP QEMU monitoring
MONITOR_PID=$!
sleep 1

# Run only the boot test directly
echo "Running boot test..."
python3 -m pytest test_arm_f_k1_tc_002_boot.py::test_basic_qemu_boot -v -s --tb=short | grep QEMU-HANDLER

# Clean up monitor process
kill $MONITOR_PID 2>/dev/null || true
