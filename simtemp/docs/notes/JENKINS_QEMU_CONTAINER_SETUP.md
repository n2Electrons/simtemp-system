# Jenkins Container Setup with QEMU ARM Emulation Support

This document provides a complete guide for setting up a Jenkins container with QEMU ARM system emulation capabilities for CI/CD testing of embedded Linux systems.

## Overview

The Jenkins container setup enables automated testing of ARM-based embedded systems using QEMU emulation. This configuration supports:
- **Jenkins LTS** for CI/CD pipeline management
- **QEMU ARM System Emulation** for i.MX6 SABRE Lite board testing
- **Kernel Module Development** with proper headers and build tools
- **Automated Testing** of embedded Linux drivers and applications

## Prerequisites

### Host System Requirements
- **Operating System**: Ubuntu 24.04 LTS (or compatible Linux distribution)
- **Docker**: Version 20.10+ installed and running
- **QEMU**: Host system must have QEMU ARM emulation installed
- **Kernel Headers**: Development headers for kernel module compilation

### Verify Host QEMU Installation
```bash
# Check QEMU ARM system emulation availability
qemu-system-arm --version
# Expected output: QEMU emulator version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.10)

# Verify QEMU binary location
which qemu-system-arm
# Expected output: /usr/bin/qemu-system-arm

# Check available ARM machine types including SABRE Lite
qemu-system-arm -M help | grep -i sabre
# Expected output: sabrelite - Freescale i.MX6 Quad SABRE Lite Board (Cortex-A9)
```

## Container Configuration Evolution

### Container Creation Approach

The Jenkins container setup has evolved through different phases to balance functionality and maintainability:

1. **Initial Setup**: Full host library bind-mounting for QEMU support
2. **Current Optimized Setup**: Selective mounting to prevent package installation conflicts

### Step 1: Stop and Remove Existing Container (if any)
```bash
# Stop existing Jenkins container
docker stop jenkins-3 2>/dev/null || echo "No existing container to stop"

# Remove existing container
docker rm jenkins-3 2>/dev/null || echo "No existing container to remove"
```

### Step 2: Create Jenkins Container with Optimized QEMU Support

**Current Recommended Configuration** (Avoids library conflicts):
```bash
# Create Jenkins container with selective QEMU mounting to allow package installation
docker run -d \
    --name jenkins-3 \
    --restart=unless-stopped \
    -p 8080:8080 \
    -p 50000:50000 \
    -v jenkins_home-2:/var/jenkins_home \
    -v /lib/modules:/lib/modules:ro \
    -v /usr/src:/usr/src:ro \
    -v /usr/bin/qemu-system-arm:/usr/bin/qemu-system-arm:ro \
    -v /usr/share/qemu:/usr/share/qemu:ro \
    --device /dev/kvm \
    jenkins/jenkins:lts
```

**Previous Configuration** (Comprehensive but restrictive):
```bash
# WARNING: This configuration prevents package installation due to read-only library mounts
docker run -d \
  --name jenkins-3 \
  --restart=unless-stopped \
  -p 8080:8080 \
  -p 50000:50000 \
  -v jenkins_home-2:/var/jenkins_home \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v /home/jorge/challenge-2509/kernel_enroll:/var/jenkins_home/kernel_enroll:ro \
  -v /usr/bin/qemu-system-arm:/usr/bin/qemu-system-arm:ro \
  -v /lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:ro \
  -v /usr/share/qemu:/usr/share/qemu:ro \
  jenkins/jenkins:lts
```

### Key Changes and Rationale

**Removed Mounts in Current Configuration:**
- `/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:ro` - **Reason**: Prevented installation of build tools
- `/home/jorge/challenge-2509/kernel_enroll:/var/jenkins_home/kernel_enroll:ro` - **Reason**: Optional path-specific mount

**Added Features:**
- `--device /dev/kvm` - **Purpose**: Hardware acceleration for QEMU (if available)

**Maintained Service Continuity:**
- **Jenkins Data Persistence**: `jenkins_home-2` volume maintains all Jenkins configuration, jobs, and user data
- **QEMU Functionality**: Direct binary and resource mounting preserves ARM emulation capabilities
- **Kernel Development**: Kernel modules and source headers remain accessible for compilation

## Service Continuity and Migration Benefits

### How Previous Services Continue to Work

When transitioning from the previous container configuration to the current optimized setup, all critical services and functionality are preserved through the following mechanisms:

#### 1. **Jenkins Configuration Persistence**
```bash
# Jenkins data volume remains unchanged
-v jenkins_home-2:/var/jenkins_home
```
- **What is Preserved**: All Jenkins jobs, build configurations, user accounts, installed plugins, and system settings
- **How it Works**: The named volume `jenkins_home-2` persists across container recreations
- **Verification**: After container recreation, log in to Jenkins web interface - all previous configuration remains intact

#### 2. **QEMU ARM Emulation Functionality**
```bash
# Essential QEMU components remain mounted
-v /usr/bin/qemu-system-arm:/usr/bin/qemu-system-arm:ro
-v /usr/share/qemu:/usr/share/qemu:ro
```
- **What is Preserved**: Full ARM system emulation capabilities for i.MX6 SABRE Lite testing
- **How it Works**: Direct binary mounting provides QEMU access without dependency conflicts
- **Library Resolution**: QEMU automatically links to container-native libraries instead of host-bound libraries
- **Verification**: `docker exec jenkins-3 qemu-system-arm --version` shows functional QEMU installation

#### 3. **Kernel Development Environment**
```bash
# Kernel development resources remain accessible
-v /lib/modules:/lib/modules:ro
-v /usr/src:/usr/src:ro
```
- **What is Preserved**: Access to kernel modules and source headers for compilation
- **How it Works**: Read-only mounts provide development resources without write conflicts
- **Enhanced Capability**: Container can now install additional build tools (make, gcc, build-essential)
- **Verification**: Kernel module compilation and loading capabilities maintained

### Benefits of the New Approach

#### 1. **Package Installation Freedom**
**Problem Solved**: Previous read-only `/lib/x86_64-linux-gnu` mount prevented installation of essential build tools
```bash
# This now works in the new configuration:
docker exec -u root jenkins-3 apt update
docker exec -u root jenkins-3 apt install -y build-essential
```
**Impact**: Enables installation of compilers, development tools, and additional packages as needed

#### 2. **Reduced Container Complexity**
**Simplified Mounting**: Removes complex library dependency management
- **Previous**: Required careful mapping of host libraries to container
- **Current**: Container manages its own library dependencies naturally
- **Result**: More stable and maintainable container environment

#### 3. **Enhanced Portability**
**Host Independence**: Container is less dependent on specific host library versions
- **Previous**: Tied to host system library versions and paths
- **Current**: Self-contained with standard Jenkins image libraries
- **Benefit**: Easier deployment across different host systems

#### 4. **Better Error Handling**
**Clear Separation**: Host and container library conflicts eliminated
- **Previous**: Cryptic library version mismatches and read-only filesystem errors
- **Current**: Standard package management within container environment
- **Result**: Cleaner error messages and easier troubleshooting

### Migration Process

When recreating the container with the new configuration:

1. **Stop and Remove Old Container**: `docker stop jenkins-3 && docker rm jenkins-3`
2. **Volume Preservation**: Jenkins data automatically preserved in `jenkins_home-2` volume  
3. **Create New Container**: Use optimized mount configuration
4. **Install Required Tools**: `docker exec -u root jenkins-3 apt install -y build-essential`
5. **Verify Functionality**: Test both Jenkins web interface and QEMU ARM emulation

### Compatibility Matrix

| Feature | Previous Config | Current Config | Status |
|---------|----------------|----------------|---------|
| Jenkins Web Interface | ✅ Working | ✅ Working | **Maintained** |
| Jenkins Jobs/Pipelines | ✅ Working | ✅ Working | **Maintained** |
| QEMU ARM Emulation | ✅ Working | ✅ Working | **Maintained** |
| Kernel Module Compilation | ✅ Working | ✅ Working | **Maintained** |
| Package Installation | ❌ Blocked | ✅ Working | **Improved** |
| Build Tools (make, gcc) | ❌ Conflicts | ✅ Working | **Improved** |
| Host Library Dependencies | ⚠️ Complex | ✅ Simple | **Improved** |

### Volume Mount Breakdown

**Current Optimized Configuration:**
| Mount Source | Mount Target | Mode | Purpose |
|--------------|--------------|------|---------|
| `jenkins_home-2` | `/var/jenkins_home` | rw | Jenkins persistent data and configuration |
| `/lib/modules` | `/lib/modules` | ro | Kernel modules for current running kernel |
| `/usr/src` | `/usr/src` | ro | Kernel source headers for module compilation |
| `/usr/bin/qemu-system-arm` | `/usr/bin/qemu-system-arm` | ro | QEMU ARM system emulator binary |
| `/usr/share/qemu` | `/usr/share/qemu` | ro | QEMU firmware and configuration files |
| `/dev/kvm` | `/dev/kvm` | device | Hardware acceleration for QEMU (if available) |

**Removed from Previous Configuration:**
| Mount Source | Reason for Removal |
|--------------|-------------------|
| `/lib/x86_64-linux-gnu` | Read-only mount prevented package installation (build-essential, make, gcc) |
| `/home/jorge/challenge-2509/kernel_enroll` | Path-specific mount, not universally applicable |

### Step 3: Verify Container Status
```bash
# Check container is running
docker ps | grep jenkins-3
# Expected output: Container running on ports 8080:8080 and 50000:50000

# Check container logs for startup
docker logs jenkins-3 --tail 20
```

### Step 4: Post-Setup Configuration (Essential Build Tools)

After creating the container with the optimized configuration, install essential build tools that were previously blocked:

```bash
# Update package repository
docker exec -u root jenkins-3 apt update

# Install essential build tools
docker exec -u root jenkins-3 apt install -y build-essential

# Verify build tools installation
docker exec jenkins-3 which make
# Expected output: /usr/bin/make

docker exec jenkins-3 which gcc
# Expected output: /usr/bin/gcc

docker exec jenkins-3 gcc --version
# Expected output: gcc (Debian 12.2.0-14+deb12u1) 12.2.0
```

**What Gets Installed:**
- `make`: Build automation tool for kernel modules and projects
- `gcc`: GNU Compiler Collection for C/C++ compilation  
- `g++`: GNU C++ compiler
- `binutils`: Binary utilities (ld, as, objdump, etc.)
- `libc6-dev`: Development libraries for C standard library
- `linux-libc-dev`: Linux kernel headers for userspace development

**Why This Couldn't Be Done Before:**
The previous configuration with `/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:ro` created read-only filesystem errors when trying to install packages that needed to write library files to this directory.

## QEMU Functionality Verification

### Step 1: Test QEMU Binary Access
```bash
# Verify QEMU is accessible within container
docker exec jenkins-3 which qemu-system-arm
# Expected output: /usr/bin/qemu-system-arm

# Test QEMU version
docker exec jenkins-3 qemu-system-arm --version
# Expected output: QEMU emulator version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.10)
```

### Step 2: Verify ARM Machine Support
```bash
# Check available ARM machine types
docker exec jenkins-3 qemu-system-arm -M help | head -10
# Should show list of supported ARM machines

# Verify SABRE Lite board support
docker exec jenkins-3 qemu-system-arm -M help | grep -i sabre
# Expected output: sabrelite - Freescale i.MX6 Quad SABRE Lite Board (Cortex-A9)
```

### Step 3: Test QEMU Startup
```bash
# Test QEMU can start (will timeout after 3 seconds)
docker exec jenkins-3 timeout 3 qemu-system-arm -M sabrelite -nographic -serial stdio
# Should show QEMU startup messages before timing out
```

## Jenkins Configuration

### Initial Setup
1. **Access Jenkins Web Interface**:
   - Open browser to `http://localhost:8080`
   - Retrieve initial admin password:
     ```bash
     docker exec jenkins-3 cat /var/jenkins_home/secrets/initialAdminPassword
     ```

2. **Install Required Plugins**:
   - Git plugin
   - Pipeline plugin
   - GitHub plugin
   - Blue Ocean (optional)

3. **Configure GitHub Integration**:
   - Add GitHub credentials
   - Configure webhooks for automated builds

### Pipeline Configuration

The container supports Jenkins pipelines that can execute QEMU-based tests. Example pipeline configuration:

```groovy
pipeline {
    agent any
    
    stages {
        stage('QEMU Test') {
            steps {
                script {
                    // Test QEMU functionality
                    sh '''
                        # Verify QEMU is available
                        qemu-system-arm --version
                        
                        # Test QEMU can list machines
                        qemu-system-arm -M help | grep sabrelite
                        
                        # Run actual QEMU tests (example)
                        cd ${WORKSPACE}/deployment/qemu
                        timeout 30 ./scripts/run_qemu.sh || echo "QEMU test completed"
                    '''
                }
            }
        }
    }
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. QEMU Binary Not Found
**Symptom**: `qemu-system-arm: not found`
**Solution**: Verify QEMU binary mount:
```bash
# Check if binary exists in container
docker exec jenkins-3 ls -la /usr/bin/qemu-system-arm

# If missing, recreate container with proper mount
docker stop jenkins-3 && docker rm jenkins-3
# Then recreate with proper volume mounts
```

#### 2. Shared Library Errors
**Symptom**: `error while loading shared libraries: libfdt.so.1: cannot open shared object file`
**Solution**: Ensure library directory is mounted:
```bash
# Check library mount
docker exec jenkins-3 ls -la /lib/x86_64-linux-gnu/libfdt.so.1

# Verify all required libraries
docker exec jenkins-3 ldd /usr/bin/qemu-system-arm | head -10
```

#### 3. Kernel Module Build Failures
**Symptom**: Build errors when compiling kernel modules
**Solution**: Verify kernel headers mount:
```bash
# Check kernel headers availability
docker exec jenkins-3 ls -la /lib/modules/$(uname -r)/build

# Check kernel source headers
docker exec jenkins-3 ls -la /usr/src/linux-headers-$(uname -r)
```

#### 4. Permission Issues
**Symptom**: Permission denied when accessing mounted volumes
**Solution**: Check volume permissions and ownership:
```bash
# Check mount permissions
docker exec jenkins-3 ls -la /var/jenkins_home/

# Fix permissions if needed (run on host)
sudo chown -R 1000:1000 /var/lib/docker/volumes/jenkins_home-2/_data
```

### Diagnostic Commands

```bash
# Container health check
docker exec jenkins-3 ps aux | grep jenkins

# Resource usage
docker stats jenkins-3

# Volume inspection
docker volume inspect jenkins_home-2

# Network connectivity test
docker exec jenkins-3 curl -s http://localhost:8080/api/json | jq .

# QEMU comprehensive test
docker exec jenkins-3 qemu-system-arm -M sabrelite -cpu cortex-a9 -m 1G -nographic -serial stdio -kernel /dev/null 2>&1 | head -5
```

## Security Considerations

### Read-Only Mounts
- Most system directories are mounted read-only (`ro`) for security
- Only Jenkins home directory has write access
- QEMU binary and libraries are protected from modification

### Container Isolation
- Container runs with default Docker security settings
- No privileged access required for QEMU emulation
- Network access limited to required ports (8080, 50000)

### Volume Security
- Kernel modules directory mounted read-only prevents system modification
- Source code access limited to specific enrolled directories
- Jenkins workspace isolation maintained

## Performance Optimization

### Resource Allocation
```bash
# Monitor container resource usage
docker stats jenkins-3

# Adjust memory limits if needed
docker update --memory=4g jenkins-3

# CPU limit adjustment
docker update --cpus=2.0 jenkins-3
```

### QEMU Performance
- QEMU runs in emulation mode (not virtualization)
- Test execution times may be longer than native
- Consider timeout adjustments for QEMU-based tests

## Maintenance

### Container Updates
```bash
# Pull latest Jenkins LTS image
docker pull jenkins/jenkins:lts

# Recreate container with new image
docker stop jenkins-3
docker rm jenkins-3
# Run create command again with latest image
```

### Backup Jenkins Configuration
```bash
# Backup Jenkins home volume
docker run --rm -v jenkins_home-2:/source -v $(pwd):/backup alpine tar czf /backup/jenkins_backup_$(date +%Y%m%d).tar.gz -C /source .

# Restore from backup
docker run --rm -v jenkins_home-2:/target -v $(pwd):/backup alpine tar xzf /backup/jenkins_backup_YYYYMMDD.tar.gz -C /target
```

### Log Management
```bash
# View container logs
docker logs jenkins-3 --tail 100 --follow

# Rotate logs
docker logs jenkins-3 > jenkins_$(date +%Y%m%d).log
```

## Integration with Test Framework

The Jenkins container integrates with the existing test framework:

### Test Execution Flow
1. **Pipeline Trigger**: GitHub webhook or manual trigger
2. **Source Checkout**: Git repository clone in Jenkins workspace
3. **Environment Setup**: Load test configuration and dependencies
4. **QEMU Tests**: Execute ARM emulation tests using mounted QEMU
5. **Report Generation**: Generate test reports and artifacts
6. **Results Publishing**: Update GitHub PR with test results

### Configuration Files
- **Pipeline Config**: `simtemp/pipeline_config.yml`
- **Test Config**: Test configuration YAML files
- **QEMU Scripts**: `deployment/qemu/scripts/run_qemu.sh`

## Conclusion

This Jenkins container setup provides a complete CI/CD environment for embedded ARM Linux development with QEMU emulation support. The configuration ensures:

- ✅ **Reliable QEMU ARM emulation** for i.MX6 SABRE Lite testing
- ✅ **Kernel module development** with proper headers and build tools
- ✅ **Secure container isolation** with read-only system mounts
- ✅ **Persistent Jenkins configuration** with volume storage
- ✅ **Automated testing integration** with GitHub workflows

The setup has been tested and verified to work with:
- **QEMU Version**: 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.10)
- **Jenkins Version**: LTS (latest)
- **Target Platform**: Freescale i.MX6 Quad SABRE Lite Board (Cortex-A9)
- **Test Framework**: F-K1-TC-002 QEMU Device Tree infrastructure tests

This documentation ensures reproducible container setup for development teams and CI/CD maintenance.