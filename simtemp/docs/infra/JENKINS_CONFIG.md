# Jenkins Configuration Guide for simtemp

This document focuses on Jenkins-specific configuration and pipeline behavior for the simtemp kernel module project.

## Related Documentation

- [CI Requirements](../CI_REQUIREMENTS.md) - Complete CI/CD setup requirements
  - [Container Setup](../CI_REQUIREMENTS.md#docker-based-jenkins-agents)
  - [Common Issues](../CI_REQUIREMENTS.md#common-cicd-issues-and-solutions)
  - [Multi-platform Support](../CI_REQUIREMENTS.md#multi-platform-support)
- [Pipeline Infrastructure](PIPELINE_INFRASTRUCTURE.md) - Overall pipeline architecture
- [Jenkins Testing](Jenkins_testing.md) - Detailed testing guide

For general CI/CD requirements, container setup, and common troubleshooting, please refer to [CI Requirements](../CI_REQUIREMENTS.md).

## Pipeline Overview

The Jenkins pipeline for simtemp includes enhanced environment reporting and container-aware behavior. This guide covers Jenkins-specific configurations and adaptations needed for the build pipeline.

### Required Plugins

- Pipeline
- Docker Pipeline
- JUnit
- Warnings Next Generation
- Workspace Cleanup

### Pipeline Configuration

In Jenkins UI:

1. Create new Pipeline job
2. Configure Git repository
3. Set pipeline script path to `Jenkinsfile`
4. Configure workspace cleanup policy
5. Enable test result collection

For container setup and dependency requirements, see [CI Requirements](../CI_REQUIREMENTS.md#docker-based-jenkins-agents).

## Pipeline Features

### Smart Environment Detection

The pipeline includes advanced environment detection and adaptation:

1. **Container Detection**
   - Automatically detects if running in container
   - Adapts commands based on environment type
   - Provides appropriate error messages

2. **Environment Validation**
   - Checks for required tools and dependencies
   - Verifies kernel headers availability
   - Validates build tool versions

3. **Build Adaptation**
   - Uses appropriate kernel headers automatically
   - Handles version mismatches gracefully
   - Provides clear build status feedback

### Pipeline Stages

1. **Setup Dependencies Stage**:
   ```groovy
   stage('Setup Dependencies') {
       steps {
           script {
               // Environment reporting
               sh '''
                   echo "=== Environment Check ==="
                   uname -r
                   gcc --version
                   make --version
                   echo "========================"
               '''
           }
       }
   }
   ```

2. **Build Stage**:
   ```groovy
   stage('Build') {
       steps {
           dir('simtemp/kernel') {
               sh 'make clean'
               sh 'make all'
               sh 'file obj/nxp_simtemp.ko'
           }
       }
   }
   ```

3. **Test Stage**:
   ```groovy
   stage('Test') {
       steps {
           dir('simtemp') {
               sh './tests/run_tests.sh'
           }
       }
       post {
           always {
               junit '**/test-results/*.xml'
           }
       }
   }
   ```

## Pipeline Enhancements

The pipeline includes several enhancements for improved reliability and feedback:

### Enhanced Error Handling

1. **Smart Error Detection**:
   ```groovy
   post {
       failure {
           script {
               def buildLog = currentBuild.rawBuild.getLog(1000)
               if (buildLog.contains("No such file or directory")) {
                   echo "Build failed due to missing dependencies. See CI_REQUIREMENTS.md"
               }
           }
       }
   }
   ```

2. **Test Result Collection**:
   ```groovy
   post {
       always {
           junit '**/test-results/*.xml'
           recordIssues enabledForFailure: true
       }
   }
   ```

3. **Artifact Management**:
   ```groovy
   post {
       success {
           archiveArtifacts artifacts: 'simtemp/kernel/obj/*.ko'
       }
   }
   ```

### Workspace Management

1. **Cleanup Policy**:
   ```groovy
   options {
       skipDefaultCheckout(true)
       cleanWs()
   }
   ```

2. **Safe Environment Reset**:
   ```groovy
   post {
       cleanup {
           cleanWs(
               deleteDirs: true,
               patterns: [
                   [pattern: '**/obj/**', type: 'INCLUDE'],
                   [pattern: '**/test-results/**', type: 'EXCLUDE']
               ]
           )
       }
   }
   ```

## Additional Resources

- [CI Requirements](../CI_REQUIREMENTS.md) - Complete CI/CD setup guide
- [Pipeline Infrastructure](../PIPELINE_INFRASTRUCTURE.md) - General pipeline architecture
- [Jenkins Testing](Jenkins_testing.md) - Detailed testing guide
    sh "make ${target}"
}
```

### Enhanced Environment Reporting

The pipeline now provides detailed environment information and automatically handles kernel headers in both build and test stages:

```
=== Environment Check ===
Host kernel version: 6.14.0-33-generic
GCC available: /usr/bin/gcc
Make available: /usr/bin/make
Python available: /usr/bin/python3
Host kernel headers: NOT FOUND
Available kernel header versions:
  ✅ 6.1.0-40-amd64 (headers available)
========================
```

### Container-Aware Error Handling

The Setup Dependencies stage and Test stage gracefully handle container limitations:

- **Build Stage**: Automatically detects and uses available kernel headers
- **Test Stage**: Pre-builds kernel module with correct headers before running tests  
- **Test Script**: Uses system packages when available, avoids unnecessary installations
- **Setup Stage**: Detects missing `sudo` in containers and provides guidance
- **Error Reporting**: Shows exactly what packages are needed and which kernel headers are available

The test runner (`simtemp/tests/run_tests.sh`) is designed for multiple environments:
- **Jenkins Containers**: Uses pre-installed system packages directly
- **Local Development**: Falls back to virtual environment when needed
- **CI/CD Environments**: Respects externally managed dependencies

## Troubleshooting

### Issue: `sudo: command not found`
**Cause**: Running in Docker container without sudo
**Solution**: Use Option 1 (install in running container) or Option 2 (pre-configured container)

### Issue: `linux-headers-generic` not found
**Cause**: Container using different kernel than host
**Solution**: Install `linux-headers-generic` instead of specific kernel version

### Issue: Kernel version mismatch in container
**Cause**: Container reports host kernel version but has different headers installed
**Solution**: Pipeline automatically detects and uses available headers
```bash
# Manual override if needed:
make KERNEL_SRC=/lib/modules/6.1.0-40-amd64/build all
```

### Issue: Setup script fails but build works
**Cause**: Packages already installed or alternative package names
**Solution**: This is normal - the script detects missing sudo and continues

### Issue: Tests fail with "Key was rejected by service"
**Cause**: Module signing restrictions in secure environments
**Solution**: This is expected in CI - focus on build success, not runtime tests

### Issue: Tests fail with "sudo: command not found" 
**Cause**: Container environment lacks sudo for insmod/rmmod operations
**Solution**: Updated tests detect container environment and skip sudo-dependent tests
```python
# New test behavior:
if is_container_environment():
    pytest.skip("Skipping insmod test - sudo not available")
# Alternative build artifacts test runs instead
```

### Issue: Test stage fails with kernel headers not found
**Cause**: Test script using default Makefile without kernel headers detection
**Solution**: Pipeline now pre-builds kernel module with correct headers before running tests
```bash
# The pipeline automatically runs this before tests:
make clean && make KERNEL_SRC=/lib/modules/6.1.0-40-amd64/build
```

### Issue: Test script tries to install packages with sudo
**Cause**: Older versions of test script attempted package installation
**Solution**: Updated test script detects system packages and avoids installation
```bash
# New behavior - detects system packages:
python3 -c "import pytest, yaml, requests" && echo "Using system packages"
```

### Issue: Container dependencies lost after restart
**Cause**: Dependencies installed in running container with Option 1
**Solution**: Use Option 2 (pre-configured container) for persistent setup

## Verification

### For Running Containers (Option 1)

After installing dependencies in a running container, verify:

```bash
# Check kernel headers
docker exec jenkins ls -la /lib/modules/

# Check build tools
docker exec jenkins gcc --version
docker exec jenkins make --version
docker exec jenkins python3 --version

# Test kernel module build
docker exec jenkins bash -c "cd /var/jenkins_home/workspace/YOUR_PROJECT/simtemp/kernel && make clean"
docker exec jenkins bash -c "cd /var/jenkins_home/workspace/YOUR_PROJECT/simtemp/kernel && make KERNEL_SRC=/lib/modules/6.1.0-40-amd64/build all"
```

### For Pre-configured Containers (Option 2)

After setup, verify the environment has required dependencies:

```bash
# Check kernel headers
ls -la /lib/modules/$(uname -r)/build

# Check build tools
gcc --version
make --version
python3 --version

# Test kernel module build
cd simtemp/kernel
make clean && make all
```

Expected output:
```
✅ Kernel headers found at /lib/modules/6.14.0-33-generic/build
Kernel module built successfully in obj/
```

### Container Environment Verification

For containers with mismatched kernel versions:

```bash
# Check kernel version mismatch
echo "Host kernel: $(uname -r)"
echo "Available headers:"
ls /lib/modules/

# Verify automatic detection works
cd simtemp/kernel
make clean
make all  # Should automatically find and use available headers
```

Expected output for containers:
```
Host kernel: 6.14.0-33-generic
Available headers:
6.1.0-40-amd64

Using kernel headers: /lib/modules/6.1.0-40-amd64/build
✅ Kernel module built successfully in obj/
```

## Enhanced Error Handling

The project now includes:

1. **Smart Setup Script**: Detects container environment and handles missing sudo gracefully
2. **Enhanced Pipeline**: Better error messages and environment verification
3. **Multiple Options**: Different solutions for different Jenkins setups
4. **Comprehensive Documentation**: Complete setup guides and troubleshooting

## Pipeline Behavior

The Jenkins pipeline now:

1. **Setup Dependencies Stage**: 
   - Tries to run setup script
   - Gracefully handles missing sudo
   - Provides clear error messages and guidance
   
2. **Environment Verification**:
   - Shows available tools and versions
   - Checks for kernel headers
   - Reports what's missing

3. **Build Stage**:
   - Proceeds with available tools
   - Fails clearly if dependencies missing
   - Provides guidance on fixing environment

## Files Updated

- `simtemp/scripts/setup-ci.sh` - Container-aware dependency installation
- `Jenkinsfile` - Enhanced error handling and environment checking
- `simtemp/pipeline_config.yml` - Added setup stage configuration
- `simtemp/tests/run_tests.sh` - Smart package detection, no sudo installation attempts
- `simtemp/tests/test_kernel_driver.py` - Container-aware testing with build artifacts validation
- `simtemp/README.md` - Complete requirements documentation
- `simtemp/docs/CI_REQUIREMENTS.md` - Detailed CI/CD setup guide

## Next Build Should:

1. ✅ Run "Setup Dependencies" stage first
2. ✅ Install kernel headers automatically
3. ✅ Verify installation before building
4. ✅ Build kernel module successfully
5. ✅ Run tests (may fail due to module signing - this is expected)

## Contact

For issues or questions, refer to:
- `simtemp/README.md` - Complete setup guide
- `simtemp/docs/CI_REQUIREMENTS.md` - CI/CD specific requirements
- Project repository issues for support