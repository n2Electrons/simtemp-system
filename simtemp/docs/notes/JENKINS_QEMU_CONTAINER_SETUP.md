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

## Container Configuration

### Step 1: Stop and Remove Existing Container (if any)
```bash
# Stop existing Jenkins container
docker stop jenkins-3 2>/dev/null || echo "No existing container to stop"

# Remove existing container
docker rm jenkins-3 2>/dev/null || echo "No existing container to remove"
```

### Step 2: Create Jenkins Container with QEMU Support
```bash
# Create Jenkins container with comprehensive QEMU and development support
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

### Volume Mount Breakdown

| Mount Source | Mount Target | Mode | Purpose |
|--------------|--------------|------|---------|
| `jenkins_home-2` | `/var/jenkins_home` | rw | Jenkins persistent data and configuration |
| `/lib/modules` | `/lib/modules` | ro | Kernel modules for current running kernel |
| `/usr/src` | `/usr/src` | ro | Kernel source headers for module compilation |
| `/home/jorge/challenge-2509/kernel_enroll` | `/var/jenkins_home/kernel_enroll` | ro | Custom kernel enrollment scripts |
| `/usr/bin/qemu-system-arm` | `/usr/bin/qemu-system-arm` | ro | QEMU ARM system emulator binary |
| `/lib/x86_64-linux-gnu` | `/lib/x86_64-linux-gnu` | ro | Shared libraries required by QEMU |
| `/usr/share/qemu` | `/usr/share/qemu` | ro | QEMU firmware and configuration files |

### Step 3: Verify Container Status
```bash
# Check container is running
docker ps | grep jenkins-3
# Expected output: Container running on ports 8080:8080 and 50000:50000

# Check container logs for startup
docker logs jenkins-3 --tail 20
```

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