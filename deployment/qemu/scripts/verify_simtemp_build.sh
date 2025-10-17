#!/bin/bash
# Quick verification script for simtemp driver build readiness

set -e

echo "🔍 Verifying Simtemp Driver Build Readiness for Jenkins"
echo "======================================================="

# Check current directory
echo "Current directory: $(pwd)"

# Check for essential components
COMPONENTS=(
    "scripts/build_simtemp_driver.sh:Build script"
    "../../simtemp/kernel/nxp_simtemp.c:Simtemp source"
    "../../simtemp/kernel/Makefile:Simtemp Makefile"
    "linux-imx-5.10:Kernel source"
    "rootfs:Root filesystem"
)

echo ""
echo "📋 Component Check:"
for component in "${COMPONENTS[@]}"; do
    path="${component%%:*}"
    desc="${component##*:}"
    
    if [ -e "$path" ]; then
        echo "  ✅ $desc: $path"
    else
        echo "  ❌ $desc: $path (MISSING)"
    fi
done

# Check cross-compiler
echo ""
echo "🔧 Cross-compiler Check:"
if command -v arm-linux-gnueabihf-gcc >/dev/null 2>&1; then
    echo "  ✅ ARM cross-compiler: $(arm-linux-gnueabihf-gcc --version | head -n1)"
else
    echo "  ❌ ARM cross-compiler: NOT FOUND"
fi

# Check if script is executable
echo ""
echo "🏃 Script Execution Check:"
if [ -x "scripts/build_simtemp_driver.sh" ]; then
    echo "  ✅ Build script is executable"
else
    echo "  ❌ Build script is not executable"
    echo "     Fix with: chmod +x scripts/build_simtemp_driver.sh"
fi

echo ""
echo "🎯 Summary:"
echo "   All components should show ✅ for successful Jenkins execution"
echo "   If any show ❌, the Jenkins stage will fail"
echo ""
echo "✅ Verification complete!"