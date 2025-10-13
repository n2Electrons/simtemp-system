# Jenkins CI/CD Requirements for simtemp Kernel Module

This document outlines the specific requirements for building and testing the simtemp kernel module in Jenkins CI/CD environments.

## Related Documentation

- [Jenkins Configuration](infra/JENKINS_CONFIG.md) - Jenkins-specific setup and pipeline configuration
- [Pipeline Infrastructure](infra/PIPELINE_INFRASTRUCTURE.md) - Overall pipeline architecture
- [Jenkins Testing](infra/Jenkins_testing.md) - Detailed testing procedures

For Jenkins-specific pipeline features and troubleshooting, please refer to [Jenkins Configuration](infra/JENKINS_CONFIG.md).

## Jenkins Agent Requirements

### Base System Packages

```bash
# Ubuntu/Debian Jenkins agents
sudo apt update && sudo apt install -y \
    build-essential \
    linux-headers-$(uname -r) \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    make \
    gcc

# Red Hat/CentOS/Fedora Jenkins agents  
sudo yum install -y \
    gcc \
    make \
    kernel-devel \
    kernel-headers \
    python3 \
    python3-pip \
    git \
    curl
```

### Docker-based Jenkins Agents

If using Docker containers for Jenkins agents, use a base image with kernel headers:

```dockerfile
FROM ubuntu:24.04

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    linux-headers-generic \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    make \
    gcc \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create jenkins user
RUN useradd -m -s /bin/bash jenkins && \
    echo 'jenkins ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER jenkins
WORKDIR /home/jenkins
```

### Kernel Headers Verification

Add this verification step to your Jenkins pipeline:

```groovy
stage('Verify Build Environment') {
    steps {
        script {
            // Check kernel version
            sh 'uname -r'
            
            // Verify kernel headers exist
            sh 'ls -la /lib/modules/$(uname -r)/build || echo "Kernel headers missing"'
            
            // Check build tools
            sh 'gcc --version'
            sh 'make --version'
            
            // Install headers if missing (Ubuntu/Debian)
            sh '''
                if [ ! -d "/lib/modules/$(uname -r)/build" ]; then
                    echo "Installing kernel headers..."
                    sudo apt update
                    sudo apt install -y linux-headers-$(uname -r)
                fi
            '''
        }
    }
}
```

## Pipeline Environment Variables

Set these environment variables in your Jenkins pipeline:

```groovy
environment {
    // Kernel module build settings
    KERNEL_SRC = '/lib/modules/${shell(script: "uname -r", returnStdout: true).trim()}/build'
    
    // Build configuration
    BUILD_DIR = 'examples/kernel_module/kernel'
    OBJ_DIR = 'obj'
    MODULE_NAME = 'nxp_simtemp.ko'
    
    // Test settings
    TEST_TIMEOUT = '300'  // 5 minutes
    ALLOW_TEST_FAILURES = 'true'  // Module signing may cause failures
}
```

## Common CI/CD Issues and Solutions

### 1. Missing Kernel Headers

**Problem**: 
```
make: *** /lib/modules/6.14.0-33-generic/build: No such file or directory. Stop.
```

**Solution**:
```bash
# Add to Jenkins pipeline preparation
sudo apt update
sudo apt install -y linux-headers-$(uname -r)

# Verify installation
ls -la /lib/modules/$(uname -r)/build
```

### 2. Permission Issues

**Problem**:
```
insmod: ERROR: could not insert module: Permission denied
```

**Solution**:
- Expected in CI environments
- Configure tests to skip actual module loading
- Test only build process, not runtime loading

### 3. Module Signing Issues

**Problem**:
```
insmod: ERROR: could not insert module: Key was rejected by service
```

**Solution**:
- Normal in secure environments
- Update test configuration to handle expected failures
- Focus on build verification rather than runtime testing

### 4. Container Limitations

**Problem**: Tests fail in Docker containers

**Solution**:
```yaml
# In examples/kernel_module/tests/config/generic_driver_tests.yml
tests:
  kernel_driver:
    enabled: true
    description: "Tests for the Temperature Simulator Driver"
    depends_on: ["nxp_simtemp"]
    env:
      CI_ENVIRONMENT: true
      SKIP_MODULE_LOADING: true  # Skip actual insmod in CI
      TEST_BUILD_ONLY: true      # Only test compilation
```

## Jenkinsfile Template

```groovy
pipeline {
    agent any
    
    environment {
        PIPELINE_CONFIG_PATH = 'examples/kernel_module/pipeline_config.yml'
        CONFIG_PATH = 'examples/kernel_module/tests/config/generic_driver_tests.yml'
    }
    
    stages {
        stage('Environment Setup') {
            steps {
                script {
                    // Install dependencies
                    sh '''
                        sudo apt update
                        sudo apt install -y build-essential linux-headers-$(uname -r)
                        
                        # Verify installation
                        gcc --version
                        make --version
                        ls -la /lib/modules/$(uname -r)/build
                    '''
                }
            }
        }
        
        stage('Build') {
            steps {
                dir('examples/kernel_module/kernel') {
                    sh 'make clean'
                    sh 'make all'
                    
                    // Verify build output
                    sh 'ls -la obj/nxp_simtemp.ko'
                    sh 'file obj/nxp_simtemp.ko'
                }
            }
        }
        
        stage('Test') {
            steps {
                dir('examples/kernel_module') {
                    sh './tests/run_tests.sh'
                }
            }
            post {
                always {
                    // Archive test results even if they fail
                    archiveArtifacts artifacts: 'examples/kernel_module/tests/results/**/*', allowEmptyArchive: true
                    
                    // Publish test results
                    publishTestResults testResultsPattern: 'examples/kernel_module/tests/results/junit.xml'
                }
            }
        }
        
        stage('Archive') {
            steps {
                // Archive build artifacts
                archiveArtifacts artifacts: 'examples/kernel_module/kernel/obj/*.ko', fingerprint: true
                archiveArtifacts artifacts: 'examples/kernel_module/kernel/obj/Module.symvers', allowEmptyArchive: true
            }
        }
    }
    
    post {
        cleanup {
            // Clean workspace
            deleteDir()
        }
    }
}
```

## Multi-platform Support

For supporting multiple Linux distributions:

```bash
# Detect distribution and install appropriate packages
if [ -f /etc/debian_version ]; then
    # Debian/Ubuntu
    sudo apt update
    sudo apt install -y build-essential linux-headers-$(uname -r)
elif [ -f /etc/redhat-release ]; then
    # Red Hat/CentOS/Fedora
    if command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y gcc make kernel-devel kernel-headers
    else
        sudo yum install -y gcc make kernel-devel kernel-headers
    fi
elif [ -f /etc/arch-release ]; then
    # Arch Linux
    sudo pacman -S --noconfirm base-devel linux-headers
fi
```

## Monitoring and Alerts

Set up monitoring for:

1. **Build failures** due to missing dependencies
2. **Test failures** beyond expected (module signing)
3. **Performance regression** in build times
4. **Kernel compatibility** issues with new kernel versions

## Best Practices

1. **Cache dependencies** when possible
2. **Use specific kernel header versions** in CI images
3. **Test on multiple kernel versions** if supporting range
4. **Handle expected failures gracefully**
5. **Provide clear error messages** for missing dependencies
6. **Archive all build artifacts** for debugging

## Quick Setup Script

Create this as `examples/kernel_module/scripts/setup-ci.sh`:

```bash
#!/bin/bash
set -e

echo "Setting up CI environment for examples/kernel_module kernel module..."

# Install dependencies
if [ -f /etc/debian_version ]; then
    sudo apt update
    sudo apt install -y build-essential linux-headers-$(uname -r)
elif [ -f /etc/redhat-release ]; then
    if command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y gcc make kernel-devel kernel-headers
    else
        sudo yum install -y gcc make kernel-devel kernel-headers
    fi
fi

# Verify setup
echo "Verifying setup..."
gcc --version
make --version
ls -la /lib/modules/$(uname -r)/build

echo "CI environment setup complete!"
```
### Docker Container Configuration for Kernel Module Testing

When testing kernel modules in Docker containers, additional configuration is required to handle module loading and signing. Follow these steps:

1. Container Privileges and Mounts:
```yaml
services:
  jenkins:
    privileged: true  # Required for kernel module operations
    volumes:
      - /usr/src:/usr/src:ro  # Mount kernel headers
      - /lib/modules:/lib/modules:ro  # Mount kernel modules
```

2. Required Packages:
```bash
# Install essential packages for module building and loading
apt-get update && apt-get install -y \
    build-essential \
    gcc-13  # Match host kernel compiler version
    kmod \
    libelf-dev
```

3. Module Signing Configuration:
```bash
# Generate signing keys (on host system)
openssl req -new -x509 -newkey rsa:2048 -keyout MOK.priv \
    -outform DER -out MOK.der -nodes -days 36500 \
    -subj "/CN=Local Dev Key/"

# Enroll the key using mokutil (on host system)
sudo mokutil --import MOK.der
# Reboot and complete MOK enrollment

# In container: Sign the module
/usr/src/linux-headers-$(uname -r)/scripts/sign-file \
    sha256 /path/to/MOK.priv /path/to/MOK.der \
    /path/to/module.ko
```

4. Container Security Settings:
```groovy
// Jenkins pipeline docker configuration
options {
    docker {
        image 'jenkins/jenkins:lts'
        args '--privileged -v /usr/src:/usr/src:ro -v /lib/modules:/lib/modules:ro'
    }
}
```

5. Troubleshooting:
- Error "Key was rejected by service": Ensure module is signed with an enrolled MOK key
- Missing compiler version: Install matching gcc version (e.g., gcc-13 for Ubuntu 24.04)
- "executable not found": Install kmod package for insmod/rmmod commands
- Build errors: Install libelf-dev for module building tools

Note: For production environments, consider using dedicated bare-metal runners for kernel module testing instead of containers, as they provide better isolation and fewer security implications.

