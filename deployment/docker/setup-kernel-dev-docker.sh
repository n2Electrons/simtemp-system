#!/bin/bash
# setup-kernel-dev-docker.sh
# Script to automatically configure Docker environment for kernel module development
# Author: Jorge Rodriguez Moreno
# Project: simtemp-system

set -e

echo "Setting up Docker environment for kernel development..."
echo "This script will configure:"
echo "   - Privileged Jenkins container"
echo "   - Kernel compilation tools"
echo "   - Updated glibc for compatibility"
echo "   - MOK signing keys"
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

# 1. Create privileged container
echo ""
echo "Creating privileged jenkins-minimal container..."
docker stop jenkins-minimal 2>/dev/null || true
docker rm jenkins-minimal 2>/dev/null || true

docker run -d \
  --name jenkins-minimal \
  --privileged \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v /usr/bin:/usr/bin:ro \
  -v /usr/lib:/usr/lib:ro \
  -v $(pwd):/host-workspace:ro \
  -v jenkins_minimal_home:/var/jenkins_home \
  -p 8080:8080 \
  -p 50000:50000 \
  jenkins/jenkins:lts

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

# 3. Install basic tools
echo ""
echo "Installing development tools and QEMU emulation..."
docker exec -u root jenkins-minimal bash -c "
apt update -qq && 
apt install -y -qq build-essential make gcc kmod libelf1 libelf-dev bc flex bison zlib1g-dev python3 python3-pip python3-dev python3-venv qemu-system-arm qemu-utils device-tree-compiler" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "Development tools and QEMU installed"
else
    echo "Error installing development tools"
    exit 1
fi

# 3.5. Install Python testing tools and dependencies
echo ""
echo "Installing Python testing framework and dependencies..."
docker exec -u root jenkins-minimal bash -c "
pip3 install --no-cache-dir pytest PyYAML requests pytest-timeout" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "Python testing tools installed"
else
    echo "Error installing Python testing tools"
    exit 1
fi

# 3.6. Setup QEMU ARM emulation from host system
echo ""
echo "Configuring QEMU ARM emulation access from host system..."
docker exec -u root jenkins-minimal bash -c "
# Host QEMU tools are now directly accessible via /usr/bin mount
# No need for symlinks since we mount /usr/bin directly
echo "QEMU tools mounted directly from host /usr/bin"
" &>/dev/null

# Test QEMU access
if docker exec -u root jenkins-minimal test -f /usr/bin/qemu-system-arm; then
    echo "QEMU ARM emulation configured from host system"
else
    echo "Host QEMU not found - F-K1-TC-002 tests may be skipped"
fi

# 4. Update glibc (CRITICAL for compatibility)
echo ""
echo "Updating glibc for Ubuntu headers compatibility..."
echo "   (This fixes 'GLIBC_2.38 not found' error)"
docker exec -u root jenkins-minimal bash -c "
echo 'deb http://deb.debian.org/debian sid main' >> /etc/apt/sources.list &&
apt update -qq 2>/dev/null &&
DEBIAN_FRONTEND=noninteractive apt install -y -qq libc6/sid libc-bin/sid libc-dev-bin/sid libc-devtools/sid libc6-dev/sid base-files/sid" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "glibc updated successfully"
else
    echo "Error updating glibc"
    exit 1
fi

# 5. Configure gcc
echo ""
echo "Configuring gcc-13 (required by Ubuntu headers)..."
docker exec -u root jenkins-minimal bash -c "ln -sf /usr/bin/gcc /usr/bin/gcc-13"

if [ $? -eq 0 ]; then
    echo "gcc-13 configured"
else
    echo "Error configuring gcc-13"
    exit 1
fi

# 6. Verify complete installation
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

# Check QEMU availability from host system
if docker exec -u root jenkins-minimal test -f /usr/bin/qemu-system-arm &>/dev/null; then
    echo "   qemu-system-arm available (from host)"
    if docker exec -u root jenkins-minimal /usr/bin/qemu-system-arm --version &>/dev/null; then
        echo "   QEMU ARM emulation functional (host-mounted)"
    else
        echo "   QEMU ARM emulation mounted but may need library setup"
    fi
else
    echo "   qemu-system-arm NOT available on host (QEMU tests will be skipped)"
fi

# Check signing keys
if docker exec -u root jenkins-minimal ls /var/jenkins_home/kernel_enroll/ &>/dev/null; then
    echo "   MOK keys directory available"
else
    echo "   MOK keys directory not found (will be created automatically)"
fi

# 7. Final result
echo ""
if [ "$TOOLS_OK" = true ]; then
    echo "Docker environment for kernel development configured successfully!"
    echo ""
    echo "Access information:"
    echo "   Jenkins Web UI: http://localhost:8080"
    echo "   Initial password: docker exec jenkins-minimal cat /var/jenkins_home/secrets/initialAdminPassword"
    echo ""
    echo "Main commands:"
    echo "   Container access: docker exec -u root -it jenkins-minimal bash"
    echo "   Compile module: make deb-driver"
    echo "   Load module: insmod obj/module.ko"
    echo "   View modules: lsmod | grep module_name"
    echo "   Unload module: rmmod module_name"
    echo "   Run tests: python3 simtemp/tests/driver_tester.py"
    echo ""
    echo "For more information, see: deployment/docker/KERNEL_DEV_ENVIRONMENT.md"
else
    echo "Configuration completed with warnings"
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
echo "Setup completed. Happy kernel hacking!"