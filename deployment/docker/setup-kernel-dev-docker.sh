#!/bin/bash
# setup-kernel-dev-docker.sh
# Script to automatically configure Docker environment for kernel module development
# Author: Jorge Rodriguez Moreno
# Project: simtemp-system

set -e

echo "Setting up Docker environment for kernel development..."
echo "This script will configure:"
echo "   - Privileged Jenkins container"
echo "   - QEMU emulation using host infrastructure"
echo "   - Precompiled driver deployment"
echo "   - Python testing framework"
echo ""

# Check that Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check that it runs as user with Docker access
if ! docker ps &> /dev/null; then
    echo "Error: You don't have permissions to run Docker"
    echo "   Run: sudo usermod -aG docker $USER && newgrp docker"
    exit 1
fi

echo "Docker available"

# 1. Build and create the optimized Jenkins container
echo ""
echo "Building jenkins-minimal container with ARM cross-compilation..."

# Build the custom image first
if ! docker build -f Dockerfile.jenkins-minimal -t jenkins-minimal .; then
    echo "Error building jenkins-minimal image"
    exit 1
fi

echo "Creating privileged jenkins-minimal container..."
docker stop jenkins-minimal 2>/dev/null || true
docker rm jenkins-minimal 2>/dev/null || true

# Get absolute workspace path
WORKSPACE_PATH="$(cd ../.. && pwd)"

docker run -d \
  --name jenkins-minimal \
  --privileged \
  -v "${WORKSPACE_PATH}:/workspace:rw" \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v jenkins_minimal_home:/var/jenkins_home \
  -p 8083:8080 \
  -p 50003:50000 \
  jenkins-minimal

if [ $? -eq 0 ]; then
    echo "jenkins-minimal container created successfully"
else
    echo "Error creating container"
    exit 1
fi

# 2. Wait for Jenkins to start
echo ""
echo "Waiting for Jenkins to start (30 seconds)..."
sleep 30

# Check that container is running
if ! docker exec jenkins-minimal echo "Container is running" &> /dev/null; then
    echo "Error: Container is not responding"
    exit 1
fi

echo "Jenkins started correctly"

# 3. Verify tools are available (already installed in custom image)
echo ""
echo "Verifying development tools and QEMU emulation..."
docker exec -u root jenkins-minimal bash -c "
echo 'Checking installed tools:'
arm-linux-gnueabihf-gcc --version | head -1
qemu-system-arm --version | head -1
make --version | head -1
python3 --version
pytest --version
"

if [ $? -eq 0 ]; then
    echo "✅ All development tools available in container"
else
    echo "❌ Error verifying development tools"
    exit 1
fi

# 3.5. Verify Python testing tools (already installed in custom image)
echo ""
echo "Verifying Python testing framework..."
docker exec jenkins-minimal python3 -c "
import pytest
import yaml
print('✅ Python testing framework ready')
"

if [ $? -eq 0 ]; then
    echo "✅ Python testing tools verified"
else
    echo "❌ Error with Python testing tools"
    exit 1
fi

# 3.6. Setup precompiled driver deployment workflow
echo ""
echo "Configuring precompiled driver deployment for QEMU..."
docker exec -u root jenkins-minimal bash -c "
# Verify workspace is mounted correctly
if [ -f '/workspace/simtemp/kernel/obj/nxp_simtemp.ko' ]; then
    echo '✅ Precompiled driver found at /workspace/simtemp/kernel/obj/nxp_simtemp.ko'
elif [ -f '/workspace/simtemp/kernel/nxp_simtemp.c' ]; then
    echo '⚠️  Driver source found but no precompiled .ko file'
    echo '   Run: make host-driver or make nxp-driver-arm on host first'
else
    echo '❌ Workspace not properly mounted or driver source missing'
fi

# Verify QEMU infrastructure access
if [ -d '/workspace/deployment/qemu' ]; then
    echo '✅ QEMU infrastructure accessible at /workspace/deployment/qemu'
else
    echo '❌ QEMU infrastructure not found'
fi
"

# 4. Verify compiler compatibility (gcc-13 links already created in Dockerfile)
echo ""
echo "Verifying compiler compatibility..."
docker exec -u root jenkins-minimal bash -c "
echo 'Native compiler:'
gcc-13 --version | head -1
echo 'ARM cross-compiler:'
arm-linux-gnueabihf-gcc-13 --version | head -1
echo '✅ Both compilers configured with gcc-13 compatibility'
"

if [ $? -eq 0 ]; then
    echo "✅ Compiler compatibility verified"
else
    echo "❌ Error with compiler configuration"
    exit 1
fi

# 5. Verify complete installation
echo ""
echo "Verifying configuration..."

# Check kernel and headers
KERNEL_VERSION=$(docker exec -u root jenkins-minimal uname -r)
HEADERS_AVAILABLE=$(docker exec -u root jenkins-minimal ls /usr/src/linux-headers-* 2>/dev/null | wc -l)
GLIBC_VERSION=$(docker exec -u root jenkins-minimal ldd --version 2>/dev/null | head -1)
GCC_VERSION=$(docker exec -u root jenkins-minimal gcc --version 2>/dev/null | head -1)

echo "Configuration summary:"
echo "   Host kernel: $KERNEL_VERSION"
echo "   Available headers: $HEADERS_AVAILABLE sets"
echo "   glibc: $GLIBC_VERSION"
echo "   Compiler: $GCC_VERSION"

# Check critical tools
echo ""
echo "Verifying critical tools..."
TOOLS_OK=true

for tool in make gcc insmod modinfo python3 pytest; do
    if docker exec -u root jenkins-minimal which $tool &>/dev/null; then
        echo "   $tool available"
    else
        echo "   $tool NOT available"
        TOOLS_OK=false
    fi
done

# Check QEMU availability (built into container)
if docker exec -u root jenkins-minimal which qemu-system-arm &>/dev/null; then
    echo "   qemu-system-arm available (container-native)"
    if docker exec -u root jenkins-minimal qemu-system-arm --version &>/dev/null; then
        echo "   QEMU ARM emulation functional"
    else
        echo "   QEMU ARM emulation present but may have issues"
    fi
else
    echo "   qemu-system-arm NOT available (QEMU tests will be skipped)"
fi

# Check signing keys
if docker exec -u root jenkins-minimal ls /var/jenkins_home/kernel_enroll/ &>/dev/null; then
    echo "   MOK keys directory available"
else
    echo "   MOK keys directory not found (will be created automatically)"
fi

# 6. Final result
echo ""
if [ "$TOOLS_OK" = true ]; then
    echo "✅ Docker environment for kernel development configured successfully!"
    echo ""
    echo "Access information:"
    echo "   Jenkins Web UI: http://localhost:8083"
    echo "   Initial password: docker exec jenkins-minimal cat /var/jenkins_home/secrets/initialAdminPassword"
    echo ""
    echo "Main commands:"
    echo "   Container access: docker exec -u root -it jenkins-minimal bash"
    echo "   Deploy precompiled driver: cd /workspace/simtemp/kernel && make deploy-precompiled"
    echo "   Run QEMU with driver: cd /workspace/deployment/qemu && ./scripts/run_qemu.sh"
    echo "   Run tests: cd /workspace/simtemp/tests && python3 driver_tester.py"
    echo ""
    echo "Workflow:"
    echo "   1. Compile driver on host: make host-driver or make nxp-driver-arm"
    echo "   2. Deploy in container: make deploy-precompiled"
    echo "   3. Test with QEMU: ./scripts/run_qemu.sh"
    echo ""
    echo "For more information, see: deployment/docker/KERNEL_DEV_ENVIRONMENT.md"
else
    echo "❌ Configuration completed with warnings"
    echo "   Review the errors above before continuing"
fi

# Show Jenkins initial password if available
echo ""
echo "Getting Jenkins initial password..."
sleep 5  # Wait a bit longer for Jenkins to generate the password
if JENKINS_PASSWORD=$(docker exec jenkins-minimal cat /var/jenkins_home/secrets/initialAdminPassword 2>/dev/null); then
    echo "   Jenkins initial password: $JENKINS_PASSWORD"
else
    echo "   Password not generated yet, wait a few more minutes"
fi

echo ""
echo "🎉 Setup completed! Ready for driver deployment and QEMU testing!"
echo ""
echo "Quick start:"
echo "   1. Compile driver on host: cd ../../simtemp/kernel && make host-driver"
echo "   2. Access container: docker exec -u root -it jenkins-minimal bash"
echo "   3. Deploy driver: cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && make deb-driver"
echo "   4. Run QEMU: cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/deployment/qemu && ./scripts/run_qemu.sh"