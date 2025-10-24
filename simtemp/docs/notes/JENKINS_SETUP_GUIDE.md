# Jenkins Container Setup - Complete Implementation Guide

This consolidated guide provides comprehensive instructions for setting up Jenkins containers with QEMU ARM emulation support, combining all previous approaches into a single, authoritative reference.

## Overview

This setup provides a complete CI/CD environment for embedded ARM Linux development with:

- ✅ **Jenkins LTS** with persistent configuration
- ✅ **QEMU ARM System Emulation** for i.MX6 SABRE Lite testing  
- ✅ **ARM Cross-Compilation Toolchain** (arm-linux-gnueabihf-*)
- ✅ **Kernel Module Development** with proper headers and build tools
- ✅ **Python Testing Environment** with pytest, PyYAML
- ✅ **Configuration Migration** from existing Jenkins instances

## Implementation Approaches

### Approach 1: Enhanced Container with Toolchain (Recommended)

**Best for:** New setups requiring complete ARM development environment

#### 1.1 Enhanced Dockerfile (Dockerfile.jenkins-minimal)

```dockerfile
# Optimized Jenkins Container with ARM Cross-Compilation and Essential Tools
FROM jenkins/jenkins:lts

# Switch to root to install packages
USER root

# Update package list and install essential tools
RUN apt-get update && apt-get install -y \
    # Essential build tools
    build-essential \
    make \
    # ARM cross-compilation toolchain
    gcc-arm-linux-gnueabihf \
    # QEMU for ARM emulation  
    qemu-system-arm \
    # Required QEMU libraries
    libfdt1 \
    libpixman-1-0 \
    libglib2.0-0 \
    libslirp0 \
    # Linux kernel development
    linux-libc-dev \
    # Essential utilities
    curl \
    wget \
    git \
    tree \
    nano \
    net-tools \
    # Python for test scripts
    python3 \
    python3-pip \
    # Kernel build dependencies
    file \
    flex \
    bison \
    bc \
    libssl-dev \
    libelf-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (override externally-managed-environment)
RUN pip3 install --no-cache-dir --break-system-packages pytest pyyaml requests

# Create GCC-13 compatibility symbolic links
RUN ln -sf /usr/bin/arm-linux-gnueabihf-gcc-12 /usr/bin/arm-linux-gnueabihf-gcc-13 && \
    ln -sf /usr/bin/arm-linux-gnueabihf-g++-12 /usr/bin/arm-linux-gnueabihf-g++-13 && \
    ln -sf /usr/bin/arm-linux-gnueabihf-gcc-ar-12 /usr/bin/arm-linux-gnueabihf-gcc-ar-13 && \
    ln -sf /usr/bin/arm-linux-gnueabihf-gcc-nm-12 /usr/bin/arm-linux-gnueabihf-gcc-nm-13 && \
    ln -sf /usr/bin/arm-linux-gnueabihf-gcc-ranlib-12 /usr/bin/arm-linux-gnueabihf-gcc-ranlib-13 && \
    ln -sf /usr/bin/gcc-12 /usr/bin/gcc-13 && \
    ln -sf /usr/bin/g++-12 /usr/bin/g++-13

# Verify installations
RUN arm-linux-gnueabihf-gcc --version && \
    qemu-system-arm --version && \
    make --version

# Create workspace and module directories
RUN mkdir -p /workspace /lib/modules/extra && \
    chown -R jenkins:jenkins /workspace /lib/modules/extra

# Set environment variables for cross-compilation
ENV CROSS_COMPILE=arm-linux-gnueabihf-
ENV ARCH=arm
ENV CC=arm-linux-gnueabihf-gcc

# Switch back to jenkins user
USER jenkins

# Set working directory
WORKDIR /var/jenkins_home

# Expose Jenkins ports
EXPOSE 8080 50000
```

#### 1.2 Automated Setup Script (setup-jenkins-minimal.sh)

```bash
#!/bin/bash
# Enhanced Jenkins Container Setup Script

set -e

CONTAINER_NAME="jenkins-minimal"
IMAGE_NAME="jenkins-minimal"
HTTP_PORT="8083"
AGENT_PORT="50003"
VOLUME_NAME="jenkins_minimal_home"
WORKSPACE_PATH="/home/jorge/challenge-2509/simtemp-system"

echo "=== Jenkins Minimal Container Setup ==="

# Stop and remove existing container
echo "Stopping existing container..."
docker stop $CONTAINER_NAME 2>/dev/null || echo "No container to stop"
docker rm $CONTAINER_NAME 2>/dev/null || echo "No container to remove"

# Build the enhanced image
echo "Building enhanced Jenkins image..."
docker build -f Dockerfile.jenkins-minimal -t $IMAGE_NAME .

# Create and start the container
echo "Creating enhanced Jenkins container..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart=unless-stopped \
  -p $HTTP_PORT:8080 \
  -p $AGENT_PORT:50000 \
  -v $VOLUME_NAME:/var/jenkins_home \
  -v $WORKSPACE_PATH:/workspace \
  $IMAGE_NAME

# Wait for startup
echo "Waiting for Jenkins to start..."
sleep 30

# Get initial admin password
echo "=== Setup Complete ==="
echo "Jenkins URL: http://localhost:$HTTP_PORT"
echo "Initial admin password:"
docker exec $CONTAINER_NAME cat /var/jenkins_home/secrets/initialAdminPassword 2>/dev/null || echo "Password not yet available"

# Verify tools
echo "=== Tool Verification ==="
docker exec $CONTAINER_NAME arm-linux-gnueabihf-gcc --version | head -1
docker exec $CONTAINER_NAME qemu-system-arm --version | head -1
docker exec $CONTAINER_NAME python3 --version
docker exec $CONTAINER_NAME pip3 list | grep -E "pytest|pyyaml"

echo "Setup complete! Access Jenkins at http://localhost:$HTTP_PORT"
```

### Approach 2: Host Mount Configuration (Lightweight)

**Best for:** Existing QEMU installations, minimal container footprint

#### 2.1 Optimized Mount Configuration

```bash
docker run -d \
    --name jenkins-host-mount \
    --restart=unless-stopped \
    -p 8080:8080 \
    -p 50000:50000 \
    -v jenkins_home:/var/jenkins_home \
    -v /lib/modules:/lib/modules:ro \
    -v /usr/src:/usr/src:ro \
    -v /usr/bin/qemu-system-arm:/usr/bin/qemu-system-arm:ro \
    -v /usr/share/qemu:/usr/share/qemu:ro \
    --device /dev/kvm \
    jenkins/jenkins:lts

# Post-creation setup
docker exec -u root jenkins-host-mount apt update
docker exec -u root jenkins-host-mount apt install -y build-essential
```

#### 2.2 Volume Mount Breakdown

| Mount Source | Mount Target | Mode | Purpose |
|--------------|--------------|------|---------|
| `jenkins_home` | `/var/jenkins_home` | rw | Jenkins configuration and data |
| `/lib/modules` | `/lib/modules` | ro | Kernel modules for current kernel |
| `/usr/src` | `/usr/src` | ro | Kernel headers for compilation |
| `/usr/bin/qemu-system-arm` | `/usr/bin/qemu-system-arm` | ro | QEMU ARM emulator binary |
| `/usr/share/qemu` | `/usr/share/qemu` | ro | QEMU firmware and data files |
| `/dev/kvm` | `/dev/kvm` | device | Hardware acceleration (optional) |

## Configuration Migration

### Migrating from Existing Jenkins

#### Step 1: Identify Source Configuration
```bash
# List existing Jenkins containers
docker ps -a | grep jenkins

# Identify configuration volume
docker volume ls | grep jenkins
```

#### Step 2: Stop Target Container and Import Configuration
```bash
# Stop the new container
docker stop jenkins-minimal

# Import configuration from existing instance
docker run --rm \
  -v jenkins_home-2:/source \
  -v jenkins_minimal_home:/target \
  alpine sh -c "cd /source && cp -r * /target/ 2>/dev/null || true"

# Import hidden files and fix permissions
docker run --rm \
  -v jenkins_home-2:/source \
  -v jenkins_minimal_home:/target \
  alpine sh -c "cd /source && cp -r .* /target/ 2>/dev/null || true; chown -R 1000:1000 /target"

# Restart container
docker start jenkins-minimal
```

#### Step 3: Verify Configuration Import
```bash
# Check Jenkins accessibility
curl -s http://localhost:8083/ | grep -i "dashboard\|jenkins"

# Verify imported jobs
curl -s http://localhost:8083/api/json | grep -o '"name":"[^"]*"' | head -5
```

## Development Environment Configuration

### ARM Cross-Compilation Setup

The enhanced container includes automatic ARM cross-compilation support through environment variables and symbolic links.

#### Makefile Integration (simtemp/kernel/Makefile)

The kernel Makefile includes Jenkins auto-detection:

```makefile
# Auto-detect Jenkins container environment
ifeq ($(findstring /var/jenkins_home/workspace/,$(PWD)),/var/jenkins_home/workspace/)
    ARCH ?= arm
    CROSS_COMPILE ?= arm-linux-gnueabihf-
endif

# Architecture-specific kernel source
ifeq ($(ARCH),arm)
    KERNEL_SRC ?= /workspace/deployment/qemu/linux-imx-5.10.72
else
    KERNEL_SRC ?= /lib/modules/$(shell uname -r)/build
endif

# Module build configuration
obj-m := nxp_simtemp.o
nxp_simtemp-objs := nxp_simtemp.o

all:
	$(MAKE) -C $(KERNEL_SRC) M=$(PWD) modules

clean:
	$(MAKE) -C $(KERNEL_SRC) M=$(PWD) clean
```

### Pipeline Configuration

#### Complete Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    parameters {
        choice(
            name: 'BUILD_ARCH',
            choices: ['arm', 'native', 'both'],
            description: 'Target architecture for build'
        )
        booleanParam(
            name: 'RUN_QEMU_TESTS',
            defaultValue: false,
            description: 'Run QEMU integration tests'
        )
    }
    
    environment {
        WORKSPACE_PATH = '/workspace'
        KERNEL_MODULE_PATH = '/workspace/simtemp/kernel'
    }
    
    stages {
        stage('Environment Setup') {
            steps {
                sh '''
                    echo "=== Environment Information ==="
                    uname -a
                    gcc --version | head -1
                    arm-linux-gnueabihf-gcc --version | head -1
                    qemu-system-arm --version | head -1
                    python3 --version
                '''
            }
        }
        
        stage('Build ARM Module') {
            when {
                anyOf {
                    params.BUILD_ARCH == 'arm'
                    params.BUILD_ARCH == 'both'
                }
            }
            steps {
                dir("${env.KERNEL_MODULE_PATH}") {
                    sh '''
                        echo "=== Building ARM Module ==="
                        export CROSS_COMPILE=arm-linux-gnueabihf-
                        export ARCH=arm
                        make clean
                        make
                        echo "=== ARM Build Results ==="
                        ls -la obj/*.ko
                        file obj/nxp_simtemp.ko
                    '''
                }
            }
        }
        
        stage('Build Native Module') {
            when {
                anyOf {
                    params.BUILD_ARCH == 'native'
                    params.BUILD_ARCH == 'both'
                }
            }
            steps {
                dir("${env.KERNEL_MODULE_PATH}") {
                    sh '''
                        echo "=== Building Native Module ==="
                        unset CROSS_COMPILE
                        unset ARCH
                        make clean
                        make
                        echo "=== Native Build Results ==="
                        ls -la obj/*.ko
                        file obj/nxp_simtemp.ko
                    '''
                }
            }
        }
        
        stage('QEMU Integration Tests') {
            when {
                params.RUN_QEMU_TESTS == true
            }
            steps {
                dir("${env.WORKSPACE_PATH}") {
                    sh '''
                        echo "=== Running QEMU Tests ==="
                        cd deployment/qemu
                        timeout 60 python3 -m pytest tests/ -v || echo "QEMU tests completed"
                    '''
                }
            }
        }
        
        stage('Module Verification') {
            steps {
                dir("${env.KERNEL_MODULE_PATH}") {
                    sh '''
                        echo "=== Module Verification ==="
                        for ko_file in obj/*.ko; do
                            if [ -f "$ko_file" ]; then
                                echo "File: $ko_file"
                                file "$ko_file"
                                modinfo "$ko_file" | head -10
                                echo "---"
                            fi
                        done
                    '''
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: '**/simtemp/kernel/obj/*.ko', allowEmptyArchive: true
            publishTestResults testResultsPattern: '**/test-*.xml', allowEmptyResults: true
        }
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check logs for details.'
        }
    }
}
```

## Testing and Verification

### Tool Verification Commands

```bash
# Connect to container
docker exec -it jenkins-minimal bash

# Verify ARM cross-compilation
arm-linux-gnueabihf-gcc --version
arm-linux-gnueabihf-gcc-13 --version

# Verify QEMU
qemu-system-arm --version
qemu-system-arm -M help | grep sabrelite

# Verify Python environment
python3 --version
pip3 list | grep -E "pytest|pyyaml|requests"

# Verify build tools
make --version
git --version

# Test ARM compilation
cd /workspace/simtemp/kernel
export CROSS_COMPILE=arm-linux-gnueabihf-
export ARCH=arm
make clean && make
file obj/nxp_simtemp.ko
```

### Expected Output Examples

**ARM Cross-Compilation Success:**
```
obj/nxp_simtemp.ko: ELF 32-bit LSB relocatable, ARM, EABI5 version 1 (SYSV)
```

**QEMU Availability:**
```
QEMU emulator version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.10)
sabrelite - Freescale i.MX6 Quad SABRE Lite Board (Cortex-A9)
```

### Common Issues and Solutions

#### 1. GCC Version Mismatch
**Problem:** `gcc-13: not found`
**Solution:** Enhanced Dockerfile creates compatibility symlinks automatically

#### 2. QEMU Binary Not Found
**Problem:** `qemu-system-arm: not found` 
**Solution:** Use enhanced container approach or verify host mount paths

#### 3. Python Package Issues
**Problem:** `externally-managed-environment` error
**Solution:** Enhanced Dockerfile uses `--break-system-packages` flag

#### 4. Kernel Headers Missing
**Problem:** Compilation fails with missing headers
**Solution:** Verify workspace mount includes kernel source at `/workspace/deployment/qemu/linux-imx-5.10.72`

#### 5. Permission Issues
**Problem:** Permission denied accessing workspace
**Solution:** Verify workspace mount permissions and container user ID

### Container Management

#### Daily Operations
```bash
# Start Jenkins
docker start jenkins-minimal

# Stop Jenkins  
docker stop jenkins-minimal

# View logs
docker logs jenkins-minimal -f

# Monitor resources
docker stats jenkins-minimal

# Access container
docker exec -it jenkins-minimal bash
```

#### Backup and Restore
```bash
# Backup Jenkins configuration
docker run --rm \
  -v jenkins_minimal_home:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/jenkins-backup-$(date +%Y%m%d).tar.gz -C /source .

# Restore from backup
docker run --rm \
  -v jenkins_minimal_home:/target \
  -v $(pwd):/backup \
  alpine tar xzf /backup/jenkins-backup-YYYYMMDD.tar.gz -C /target
```

## Architecture Comparison

| Feature | Enhanced Container | Host Mount | 
|---------|-------------------|------------|
| **Setup Complexity** | Moderate | Simple |
| **ARM Toolchain** | ✅ Built-in | ❌ Manual install |
| **QEMU Support** | ✅ Native | ✅ Host mount |
| **Python Environment** | ✅ Pre-configured | ❌ Manual install |
| **Container Size** | Larger (~2GB) | Smaller (~500MB) |
| **Host Dependencies** | Minimal | QEMU required |
| **Portability** | ✅ Self-contained | ❌ Host-dependent |
| **Performance** | ✅ Optimized | ✅ Native QEMU |
| **Maintenance** | Low | Medium |

## Deployment Recommendations

### For New Projects (Recommended: Enhanced Container)
1. Use `Dockerfile.jenkins-minimal` approach
2. Run automated setup script
3. Configure ARM-first pipeline
4. Enable QEMU integration tests

### For Existing Setups (Host Mount + Migration)
1. Use optimized host mount configuration
2. Import existing Jenkins configuration
3. Add build tools post-creation
4. Maintain current workflow

### For CI/CD Environments
1. Use enhanced container for consistency
2. Pre-build container images for faster deployment
3. Configure automated backups
4. Monitor resource usage

## Security Considerations

- Most system directories mounted read-only
- Container runs with non-root Jenkins user
- QEMU operates in emulation mode (not virtualization)
- Workspace access limited to mounted directories
- Network exposure limited to required ports (8080, 50000)

## Performance Optimization

### Resource Allocation
```bash
# Set memory limits
docker update --memory=4g jenkins-minimal

# Set CPU limits
docker update --cpus=2.0 jenkins-minimal

# Monitor performance
docker stats jenkins-minimal
```

### Build Performance
- ARM cross-compilation: ~2-3x slower than native
- QEMU tests: ~5-10x slower than hardware
- Parallel builds: Use `make -j$(nproc)` 
- Consider build caching for large projects

## Migration History Summary

This guide consolidates knowledge from multiple Jenkins setup documents:

**Consolidated Sources:**
- `JENKINS_CONTAINER_SUMMARY.md` - Configuration evolution and troubleshooting
- `JENKINS_QEMU_CONTAINER_SETUP.md` - Detailed host mount setup procedures
- `COMPLETE_DOCKER_JENKINS_QEMU_SETUP_GUIDE.md` - Enhanced container implementation

**Key Improvements:**
- Single authoritative reference
- Unified approach combining best practices
- Comprehensive troubleshooting
- Clear architecture comparisons
- Complete pipeline examples

---

© Jorge Rodriguez Moreno – Jenkins ARM Development Environment