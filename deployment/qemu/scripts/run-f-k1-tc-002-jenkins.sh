#!/bin/bash

# QEMU Test Runner for F-K1-TC-002 in Jenkins Environment
# Uses 9P filesystem to share workspace between host and QEMU

set -e

QEMU_DIR="/home/jorge/challenge-2509/simtemp-system/deployment/qemu"
IMAGES_DIR="${QEMU_DIR}/images/system"
DTB_DIR="${QEMU_DIR}/dtb"
WORKSPACE_ROOT="/home/jorge/challenge-2509/simtemp-system"
RESULTS_DIR="${WORKSPACE_ROOT}/simtemp/tests/results"

# Create results directory if it doesn't exist
mkdir -p "${RESULTS_DIR}"

echo "🚀 QEMU Test Runner for Jenkins Environment"
echo "=========================================="
echo "Workspace: ${WORKSPACE_ROOT}"
echo "Results: ${RESULTS_DIR}"
echo ""

# Check required files
if [[ ! -f "${IMAGES_DIR}/kernel-arm.img" ]]; then
    echo "❌ Kernel image not found: ${IMAGES_DIR}/kernel-arm.img"
    exit 1
fi

if [[ ! -f "${IMAGES_DIR}/initrd.img" ]]; then
    echo "❌ InitRD not found: ${IMAGES_DIR}/initrd.img"
    exit 1
fi

if [[ ! -f "${DTB_DIR}/imx6ul-simtemp.dtb" ]]; then
    echo "❌ Device Tree not found: ${DTB_DIR}/imx6ul-simtemp.dtb"
    exit 1
fi

echo "✅ All required QEMU components found"
echo ""

# Create test execution script for QEMU
cat > "${RESULTS_DIR}/run_test_in_qemu.sh" << 'EOF'
#!/bin/sh

echo "=== Running F-K1-TC-002 inside QEMU ==="
echo "Mounting shared workspace..."

# Mount the shared workspace from host
mount -t 9p -o trans=virtio,version=9p2000.L workspace /mnt/workspace

echo "✅ Workspace mounted at /mnt/workspace"
echo "📁 Available files:"
ls -la /mnt/workspace/simtemp/tests/ | head -10

# Change to workspace
cd /mnt/workspace

# Set up environment for the test
export PYTHONPATH="/mnt/workspace/simtemp/tests:/mnt/workspace"
export PATH="/usr/bin:/bin:/sbin:/usr/sbin"

echo ""
echo "🧪 Running F-K1-TC-002 test..."

# Run the specific test with XML output for Jenkins
python3 -m pytest simtemp/tests/test_f_k1_tc_002.py::test_dt_overlay_driver_binding \
    -v --tb=short \
    --junit-xml=simtemp/tests/results/f-k1-tc-002-qemu-results.xml \
    --json-report --json-report-file=simtemp/tests/results/f-k1-tc-002-qemu-report.json

PYTEST_EXIT_CODE=$?

echo ""
echo "📊 Test completed with exit code: ${PYTEST_EXIT_CODE}"

# Show results summary
echo ""
echo "📄 Generated files:"
ls -la simtemp/tests/results/ | grep -E "(xml|json)" || echo "No XML/JSON files found"

echo ""
if [[ ${PYTEST_EXIT_CODE} -eq 0 ]]; then
    echo "✅ F-K1-TC-002 PASSED in QEMU environment"
else
    echo "❌ F-K1-TC-002 FAILED in QEMU environment (this may be expected)"
fi

echo ""
echo "🏁 Test execution completed in QEMU"

# Keep a simple shell for debugging if needed (comment out for automation)
# echo "Type 'exit' to shutdown QEMU"
# /bin/sh

# Auto-shutdown for Jenkins automation
echo "Auto-shutdown for Jenkins automation"
sleep 2
halt -f
EOF

chmod +x "${RESULTS_DIR}/run_test_in_qemu.sh"

echo "📋 Test script created: ${RESULTS_DIR}/run_test_in_qemu.sh"
echo ""

# Start QEMU with 9P filesystem sharing
echo "🖥️  Starting QEMU with shared workspace..."
echo "📁 Sharing: ${WORKSPACE_ROOT} -> /mnt/workspace"
echo ""

qemu-system-arm \
  -machine virt \
  -cpu cortex-a15 \
  -m 512M \
  -kernel "${IMAGES_DIR}/kernel-arm.img" \
  -initrd "${IMAGES_DIR}/initrd.img" \
  -dtb "${DTB_DIR}/imx6ul-simtemp.dtb" \
  -append "console=ttyAMA0,115200 rdinit=/mnt/workspace/simtemp/tests/results/run_test_in_qemu.sh" \
  -fsdev local,security_model=passthrough,id=fsdev0,path="${WORKSPACE_ROOT}" \
  -device virtio-9p-pci,id=fs0,fsdev=fsdev0,mount_tag=workspace \
  -nographic \
  -no-reboot

QEMU_EXIT_CODE=$?

echo ""
echo "📊 QEMU execution completed with exit code: ${QEMU_EXIT_CODE}"
echo ""

# Check if results were generated
echo "📄 Checking generated results..."
if [[ -f "${RESULTS_DIR}/f-k1-tc-002-qemu-results.xml" ]]; then
    echo "✅ XML results found:"
    ls -la "${RESULTS_DIR}/f-k1-tc-002-qemu-results.xml"
    echo ""
    echo "📋 XML Content Preview:"
    head -20 "${RESULTS_DIR}/f-k1-tc-002-qemu-results.xml"
else
    echo "❌ XML results not found"
fi

if [[ -f "${RESULTS_DIR}/f-k1-tc-002-qemu-report.json" ]]; then
    echo "✅ JSON report found:"
    ls -la "${RESULTS_DIR}/f-k1-tc-002-qemu-report.json"
else
    echo "❌ JSON report not found"
fi

echo ""
echo "🎯 F-K1-TC-002 QEMU test execution completed"
echo "📁 Results available in: ${RESULTS_DIR}"

exit ${QEMU_EXIT_CODE}