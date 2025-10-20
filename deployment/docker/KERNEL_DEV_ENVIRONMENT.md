# Docker Environment for Kernel Module Development

## Overview

This document details the complete setup of a privileged Docker environment for developing, compiling, and loading Linux kernel modules with Jenkins CI/CD support.

## Environment Features

- **Base Container**: jenkins/jenkins:lts (Debian Bookworm)
- **Mode**: Privileged (`--privileged`) for full kernel access
- **Capabilities**: Compilation, digital signing, and loading of kernel modules
- **Compatibility**: Ubuntu 6.14.0-32/33-generic headers with updated glibc
- **Signing**: MOK (Machine Owner Keys) for Secure Boot

## Container Configuration

### 1. Create and Run Privileged Container

```bash
# Stop existing container if it exists
docker stop jenkins-minimal 2>/dev/null || true
docker rm jenkins-minimal 2>/dev/null || true

# Create privileged container with full kernel access
docker run -d \
  --name jenkins-minimal \
  --privileged \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v jenkins_minimal_home:/var/jenkins_home \
  -p 8080:8080 \
  -p 50000:50000 \
  jenkins/jenkins:lts

# Verify it's running
docker ps | grep jenkins-minimal
```

### 2. Initial System Configuration

```bash
# Update repositories
docker exec -u root jenkins-minimal bash -c "apt update"

# Install basic development tools
docker exec -u root jenkins-minimal bash -c "
apt install -y build-essential make gcc kmod libelf1 libelf-dev \
bc flex bison zlib1g-dev"
```

### 3. Resolving glibc Conflicts (CRITICAL)

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

### 4. Compiler Configuration

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
└── /var/jenkins_home/     # Jenkins workspace (persistent)
    └── workspace/
        └── lenge-from-Github_f-k1-reg-by-dt/
            └── simtemp/kernel/    # Driver source code
```

## Module Compilation

### Configured Makefile

The `Makefile` should use the correct headers:

```makefile
# Debian native kernel source (independent compilation in Docker)
# Force use of 6.14.0-32-generic headers to avoid glibc version conflicts
DEBIAN_KERNEL_SRC := /usr/src/linux-headers-6.14.0-32-generic
```

### Compilation Commands

```bash
# Navigate to kernel workspace
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel"

# Clean previous compilation
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
make clean"

# Compile and sign module
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
make deb-driver"
```

### Compilation Verification

```bash
# Verify compiled module
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
ls -la obj/nxp_simtemp.ko && 
modinfo obj/nxp_simtemp.ko"
```

## Module Loading

### Load Module into Kernel

```bash
# Load module (requires privileged container)
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
insmod obj/nxp_simtemp.ko"

# Verify it was loaded
docker exec -u root jenkins-minimal bash -c "lsmod | grep nxp_simtemp"

# View kernel messages
docker exec -u root jenkins-minimal bash -c "dmesg | tail -5"
```

### Unload Module

```bash
# Unload module from kernel
docker exec -u root jenkins-minimal bash -c "rmmod nxp_simtemp"
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

**Cause**: Container without privileges
**Solution**: Use `--privileged` when creating the container

### 2. Error "GLIBC_2.38 not found"

**Cause**: Incompatibility between container glibc and kernel tools
**Solution**: Update glibc as indicated in section 3

### 3. Error "objtool: command not found"

**Cause**: Missing kernel compilation dependencies
**Solution**: Install `libelf-dev`, `bc`, `flex`, `bison`

### 4. Module not signing automatically

**Cause**: MOK keys not found or incorrect permissions
**Solution**: Verify keys exist in `/var/jenkins_home/kernel_enroll/`

## Complete Environment Verification

### Verification Script

```bash
#!/bin/bash
echo "=== Docker Kernel Dev Environment Verification ==="

# Verify container
docker exec jenkins-minimal uname -r
docker exec jenkins-minimal ls -la /.dockerenv

# Verify tools
docker exec -u root jenkins-minimal which make gcc kmod insmod modinfo

# Verify headers
docker exec -u root jenkins-minimal ls -la /usr/src/linux-headers-6.14.0-32-generic/

# Verify glibc
docker exec -u root jenkins-minimal ldd --version | head -1

# Verify signing keys
docker exec -u root jenkins-minimal ls -la /var/jenkins_home/kernel_enroll/

echo "✅ Verification complete"
```

## Technical Information

### Confirmed Versions

- **Host System**: Ubuntu 24.04 LTS
- **Host Kernel**: 6.14.0-33-generic
- **Container**: jenkins/jenkins:lts (Debian Bookworm)
- **Container glibc**: 2.41-12 (updated from Debian Sid)
- **gcc**: 12.2.0 (with symbolic link to gcc-13)
- **Headers Used**: linux-headers-6.14.0-32-generic

### Environment Capabilities

✅ **Compilation**: Kernel modules with Ubuntu headers  
✅ **Digital Signing**: Automatic with MOK keys  
✅ **Module Loading**: Direct into host kernel  
✅ **Iterative Development**: Complete compile-load-test cycle  
✅ **Jenkins Integration**: Persistent workspace and CI/CD ready  
✅ **Secure Boot**: Compatible with systems requiring signed modules  

### Known Limitations

- Requires privileged container (security implications)
- Dependent on specific kernel header versions
- glibc must be manually updated for new header versions
- Modules are loaded into host kernel (not isolated)

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
**Version**: 1.0  

For updates and support, consult the project repository.