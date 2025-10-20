# Docker Environment for Kernel Module Development

## Overview

This document details the complete setup of a privileged Docker environment for developing, compiling, loading, and testing Linux kernel modules with Jenkins CI/CD support.

## Environment Features

- **Base Container**: jenkins/jenkins:lts (Debian Bookworm)
- **Mode**: Privileged (`--privileged`) for full kernel access
- **Capabilities**: Compilation, digital signing, loading, and automated testing of kernel modules
- **Compatibility**: Ubuntu 6.14.0-32/33-generic headers with updated glibc
- **Signing**: MOK (Machine Owner Keys) for Secure Boot
- **Testing**: Python pytest framework with automated module testing
- **Auto-Detection**: Environment-aware build system (Docker vs Host)
- **Permissions**: Configured sudoers for automated kernel operations
- **QEMU Support**: ARM emulation using host QEMU tools for Device Tree overlay testing (F-K1-TC-002)

## Quick Setup

### Automated Setup Script

The fastest way to set up the complete environment:

```bash
# Run the automated setup script
./setup-kernel-dev-docker.sh
```

This script automatically configures:
- Privileged Jenkins container
- Development tools and Python testing framework
- Host QEMU tools mounting for ARM emulation (for Device Tree overlay tests)
- glibc compatibility updates
- Sudoers permissions for jenkins user
- Environment verification

### Manual Setup (Advanced Users)

For manual configuration or troubleshooting, follow the detailed sections below.

## Container Configuration

### 1. Create and Run Privileged Container

```bash
# Stop existing container if it exists
docker stop jenkins-minimal 2>/dev/null || true
docker rm jenkins-minimal 2>/dev/null || true

# Create privileged container with full kernel access and host QEMU tools
docker run -d \
  --name jenkins-minimal \
  --privileged \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v /usr/bin:/usr/bin:ro \
  -v /usr/lib:/usr/lib:ro \
  -v jenkins_minimal_home:/var/jenkins_home \
  -p 8080:8080 \
  -p 50000:50000 \
  jenkins/jenkins:lts

# Verify it's running
docker ps | grep jenkins-minimal
```

### 2. Development Tools and Python Testing

```bash
# Install basic development tools
docker exec -u root jenkins-minimal bash -c "
apt install -y build-essential make gcc kmod libelf1 libelf-dev \
bc flex bison zlib1g-dev python3 python3-pip python3-dev python3-venv sudo"

# Install Python testing framework and dependencies
docker exec -u root jenkins-minimal bash -c "
pip3 install --break-system-packages pytest PyYAML requests pytest-timeout"

# Install device-tree-compiler for DTB operations (QEMU tools mounted from host)
docker exec -u root jenkins-minimal bash -c "
apt install -y --no-install-recommends device-tree-compiler"
```

### 3. Configure Permissions for Automated Testing

```bash
# Add jenkins user to sudo group
docker exec -u root jenkins-minimal usermod -aG sudo jenkins

# Create sudoers configuration for kernel operations
docker exec -u root jenkins-minimal bash -c 'cat > /etc/sudoers.d/jenkins-kernel << EOF
# Jenkins user permissions for kernel module operations
jenkins ALL=(ALL) NOPASSWD: /sbin/insmod, /sbin/rmmod, /sbin/modprobe
jenkins ALL=(ALL) NOPASSWD: /usr/sbin/insmod, /usr/sbin/rmmod, /usr/sbin/modprobe
jenkins ALL=(ALL) NOPASSWD: /bin/insmod, /bin/rmmod, /bin/modprobe
# Full sudo access for development container (use with caution)
jenkins ALL=(ALL) NOPASSWD: ALL
EOF'
```

### 4. Resolving glibc Conflicts (CRITICAL)

The main issue is incompatibility between the Debian container's glibc and Ubuntu kernel tools:

```bash
# Add Debian Sid repository for newer glibc
docker exec -u root jenkins-minimal bash -c "
echo 'deb http://deb.debian.org/debian sid main' >> /etc/apt/sources.list"

# Update glibc to compatible version (2.41+)
docker exec -u root jenkins-minimal bash -c "
apt update && apt install -y libc6/sid libc-bin/sid libc-dev-bin/sid \
libc-devtools/sid libc6-dev/sid base-files/sid"
```

### 5. Compiler Configuration

```bash
# Create symbolic link for gcc-13 (required by Ubuntu headers)
docker exec -u root jenkins-minimal bash -c "
ln -sf /usr/bin/gcc /usr/bin/gcc-13"

# Verify installation
docker exec -u root jenkins-minimal bash -c "
gcc --version && gcc-13 --version"
```

## Mounted Directory Structure

```
Privileged container:
├── /lib/modules/          # Kernel modules (read-only from host)
│   └── 6.14.0-33-generic/ # Current host kernel
├── /usr/src/              # Kernel headers (read-only from host)  
│   ├── linux-headers-6.14.0-32-generic/  # Compatible headers
│   └── linux-headers-6.14.0-33-generic/  # Current headers
├── /usr/bin/              # Host binaries including QEMU tools (read-only)
├── /usr/lib/              # Host libraries for QEMU dependencies (read-only)
└── /var/jenkins_home/     # Jenkins workspace (persistent)
    └── workspace/
        └── lenge-from-Github_f-k1-reg-by-dt/
            └── simtemp/kernel/    # Driver source code
```

## Module Compilation and Testing

### Auto-Detection Build System

The Makefile now includes intelligent environment detection:

```makefile
# Default target - Auto-detect environment (Docker vs Host)
all: $(shell if [ -f "/.dockerenv" ]; then echo "deb-driver"; else echo "host-driver"; fi)
```

### Available Build Targets

```bash
# Auto-detected build (recommended)
make all                # Builds deb-driver in Docker, host-driver on host

# Specific targets
make host-driver        # Native x86_64 build with signing (production)
make deb-driver         # Debian independent x86_64 build with signing (Docker)
make nxp-driver-arm     # Build and sign for NXP ARM devices (i.MX6/i.MX7)
make clean              # Remove all build artifacts with improved error handling

# Information
make info               # Show configuration and available targets
```

### Compilation Commands

```bash
# Navigate to kernel workspace
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel"

# Clean previous compilation (improved error handling)
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
make clean"

# Auto-detected compile and sign module
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
make all"

# Or explicitly use Docker-optimized target
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
make deb-driver"
```

### Automated Testing Framework

```bash
# Run all tests as jenkins user (with sudo permissions)
docker exec -u jenkins jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/tests && 
python3 -m pytest -v"

# Run specific test cases
docker exec -u jenkins jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/tests && 
python3 -m pytest test_f_k1_tc_001.py -v"

# Run driver load/unload tests
docker exec -u jenkins jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/tests && 
python3 -m pytest test_f_k8_tc_001.py::test_driver_load_unload -v"

# Run QEMU Device Tree overlay tests (if QEMU is available)
docker exec -u jenkins jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/tests && 
python3 -m pytest test_f_k1_tc_002.py::test_basic_qemu_boot -v -s"
```

### Compilation Verification

```bash
# Verify compiled module
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
ls -la obj/nxp_simtemp.ko && 
modinfo obj/nxp_simtemp.ko"
```

## Module Loading and Testing

### Load Module into Kernel

```bash
# Load module as jenkins user (with sudo permissions)
docker exec -u jenkins jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
sudo insmod obj/nxp_simtemp.ko"

# Verify it was loaded
docker exec -u jenkins jenkins-minimal bash -c "lsmod | grep nxp_simtemp"

# View kernel messages
docker exec -u jenkins jenkins-minimal bash -c "dmesg | tail -5"
```

### Unload Module

```bash
# Unload module from kernel as jenkins user
docker exec -u jenkins jenkins-minimal bash -c "sudo rmmod nxp_simtemp"
```

### Automated Testing

The testing framework automatically handles module loading/unloading with proper permissions:

```bash
# Test utilities handle sudo automatically
from test_utils import SUDO, obj_path

# Example test function
def insmod_module():
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    result = subprocess.run(f"{SUDO}insmod {module_path}", **SHELL_PARAMS)
    if result.returncode != 0:
        pytest.fail(f"insmod failed: {result.stderr}")
```

## Digital Signing Configuration

### MOK (Machine Owner Keys)

Signing keys are located at:
- **Private key**: `/var/jenkins_home/kernel_enroll/MOK.priv`
- **Certificate**: `/var/jenkins_home/kernel_enroll/MOK.der`

### Verify Signing

```bash
# Verify that the module is signed
docker exec -u root jenkins-minimal bash -c "
modinfo /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel/obj/nxp_simtemp.ko | 
grep -E 'sig_id|signer|sig_key'"
```

## Common Troubleshooting

### 1. Error "Operation not permitted" when loading module

**Cause**: Missing sudo permissions for jenkins user
**Solution**: 
```bash
# Configure sudoers for jenkins user
docker exec -u root jenkins-minimal usermod -aG sudo jenkins
docker exec -u root jenkins-minimal bash -c 'cat > /etc/sudoers.d/jenkins-kernel << EOF
jenkins ALL=(ALL) NOPASSWD: /sbin/insmod, /sbin/rmmod, /sbin/modprobe
jenkins ALL=(ALL) NOPASSWD: ALL
EOF'
```

### 2. Error "GLIBC_2.38 not found"

**Cause**: Incompatibility between container glibc and kernel tools
**Solution**: Update glibc as indicated in section 4

### 3. Error "objtool: command not found"

**Cause**: Missing kernel compilation dependencies
**Solution**: Install `libelf-dev`, `bc`, `flex`, `bison`

### 4. Module not signing automatically

**Cause**: MOK keys not found or incorrect permissions
**Solution**: Verify keys exist in `/var/jenkins_home/kernel_enroll/`

### 5. Error "Clean failed - manual intervention required"

**Cause**: Permission issues with build artifacts
**Solution**: The improved clean target handles this automatically:
```bash
make clean  # Now includes robust permission handling
```

### 6. Python test failures "ModuleNotFoundError"

**Cause**: Missing Python dependencies
**Solution**: Install testing framework:
```bash
pip3 install pytest PyYAML requests pytest-timeout
```

### 7. QEMU tests fail "qemu-system-arm: not found"

**Cause**: Host QEMU not properly mounted or not installed on host
**Solution**: Ensure host has QEMU installed and container has proper mounts:
```bash
# Check if QEMU is available on host
qemu-system-arm --version

# If not installed on host, install it:
sudo apt install qemu-system-arm qemu-utils device-tree-compiler

# Recreate container with proper host tool mounting:
docker stop jenkins-minimal && docker rm jenkins-minimal
docker run -d --name jenkins-minimal --privileged \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v /usr/bin:/usr/bin:ro \
  -v /usr/lib:/usr/lib:ro \
  -v jenkins_minimal_home:/var/jenkins_home \
  -p 8080:8080 -p 50000:50000 \
  jenkins/jenkins:lts
```

**Note**: This approach uses host QEMU tools instead of installing in container, avoiding complex dependency chains.

## Complete Environment Verification

### Automated Verification Script

The setup script includes comprehensive verification:

```bash
./setup-kernel-dev-docker.sh
```

### Manual Verification

```bash
#!/bin/bash
echo "=== Docker Kernel Dev Environment Verification ==="

# Verify container
docker exec jenkins-minimal uname -r
docker exec jenkins-minimal ls -la /.dockerenv

# Verify tools (including Python, pytest, and host QEMU)
docker exec -u root jenkins-minimal which make gcc kmod insmod modinfo python3 pytest qemu-system-arm

# Verify headers and auto-detection
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel &&
make info"

# Verify glibc
docker exec -u root jenkins-minimal ldd --version | head -1

# Verify signing keys
docker exec -u root jenkins-minimal ls -la /var/jenkins_home/kernel_enroll/

# Verify jenkins user permissions
docker exec -u jenkins jenkins-minimal sudo -l

# Verify Python testing environment
docker exec -u jenkins jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/tests &&
python3 -c 'import pytest, yaml, requests; print(\"Python environment OK\")'
"

echo "Environment verification complete"
```

## Technical Information

### Confirmed Versions

- **Host System**: Ubuntu 24.04 LTS
- **Host Kernel**: 6.14.0-33-generic
- **Host QEMU**: 7.2.19 (mounted into container)
- **Container**: jenkins/jenkins:lts (Debian Bookworm)
- **Container glibc**: 2.41-12 (updated from Debian Sid)
- **gcc**: 12.2.0 (with symbolic link to gcc-13)
- **Headers Used**: Auto-detected (linux-headers-6.14.0-32/33-generic)
- **Python**: 3.13.9 with pytest framework
- **Testing**: pytest 8.4.2, PyYAML 6.0.3, requests, pytest-timeout

### Environment Capabilities

✅ **Auto-Detection**: Intelligent Docker vs Host environment detection  
✅ **Compilation**: Kernel modules with Ubuntu headers  
✅ **Digital Signing**: Automatic with MOK keys  
✅ **Module Loading**: Direct into host kernel with proper permissions  
✅ **Automated Testing**: Python pytest framework with module operations  
✅ **QEMU Integration**: Host QEMU tools mounted for ARM emulation  
✅ **Iterative Development**: Complete compile-load-test cycle  
✅ **Jenkins Integration**: Persistent workspace and CI/CD ready  
✅ **Secure Boot**: Compatible with systems requiring signed modules  
✅ **Error Handling**: Robust clean operations and permission management  

### Development Workflow

1. **Build**: `make all` (auto-detects environment)
2. **Test**: `python3 -m pytest -v` (as jenkins user with sudo)
3. **Debug**: Manual `sudo insmod/rmmod` operations
4. **Clean**: `make clean` (improved error handling)
5. **Deploy**: Signed modules ready for production

### Known Limitations

- Requires privileged container (security implications)
- Dependent on specific kernel header versions
- glibc must be manually updated for new header versions
- Modules are loaded into host kernel (not isolated)
- Full sudo access granted to jenkins user in development container

## Quick Environment Regeneration

To automatically regenerate the entire environment, run:

```bash
./setup-kernel-dev-docker.sh
```

This script automates all the steps documented above and includes environment verification.

## Contact and Maintenance

**Author**: Jorge Rodriguez Moreno  
**Project**: simtemp-system  
**Date**: October 2025  
**Version**: 2.0 - Enhanced with auto-detection, testing framework, and improved permissions  

For updates and support, consult the project repository.