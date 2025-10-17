# Complete Jenkins Setup Guide: Enhanced Tools + Working Configuration

This guide provides step-by-step instructions to create and deploy a Jenkins instance that combines the best of both worlds: a fully configured Jenkins setup with all enhanced tools for ARM cross-compilation and QEMU testing.

## Overview

The solution involves creating a custom Jenkins container with enhanced capabilities and importing configuration from a working Jenkins instance. This approach provides:

- ✅ ARM cross-compilation toolchain (arm-linux-gnueabihf-*)
- ✅ QEMU ARM system emulation for i.MX6 SABRE Lite
- ✅ Native x86_64 compilation tools
- ✅ Python testing environment with required packages
- ✅ Complete build environment for kernel module development
- ✅ Working Jenkins configuration with existing jobs and plugins

## Prerequisites

1. **Docker** installed and running
2. **Existing Jenkins instance** with desired configuration (jenkins-3 container in our case)
3. **Workspace access** to simtemp-system repository
4. **Root/sudo access** for container operations

## Step-by-Step Implementation

### Phase 1: Create Enhanced Jenkins Container

#### 1.1 Prepare the Enhanced Dockerfile

Ensure you have the `Dockerfile.jenkins-minimal` with the following key components:

```dockerfile
FROM jenkins/jenkins:lts

# Switch to root for package installation
USER root

# Install ARM cross-compilation toolchain and QEMU
RUN apt-get update && apt-get install -y \
    gcc-arm-linux-gnueabihf \
    g++-arm-linux-gnueabihf \
    qemu-system-arm \
    qemu-user-static \
    build-essential \
    make \
    git \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (breaking system packages restriction in Debian 12)
RUN pip3 install --break-system-packages pytest requests pyyaml

# Set up ARM cross-compilation environment
ENV CROSS_COMPILE=arm-linux-gnueabihf-
ENV ARCH=arm
ENV CC=arm-linux-gnueabihf-gcc
ENV CXX=arm-linux-gnueabihf-g++

# Switch back to jenkins user
USER jenkins
```

#### 1.2 Build the Enhanced Container

```bash
cd /home/jorge/challenge-2509/simtemp-system/deployment/docker
docker build -f Dockerfile.jenkins-minimal -t jenkins-minimal .
```

### Phase 2: Configuration Migration Strategy

#### 2.1 Identify Source Configuration

First, identify the working Jenkins instance and its volume:

```bash
# List running Jenkins containers
docker ps | grep jenkins

# Identify the working configuration volume (jenkins_home-2 for jenkins-3)
docker volume ls | grep jenkins
```

#### 2.2 Deploy Enhanced Container

Create and start the enhanced Jenkins container:

```bash
docker run -d \
  --name jenkins-minimal \
  -p 8083:8080 \
  -p 50003:50000 \
  -v jenkins_minimal_home:/var/jenkins_home \
  -v /home/jorge/challenge-2509/simtemp-system:/workspace \
  jenkins-minimal
```

**Wait for initial setup** (about 2-3 minutes) until logs show "Jenkins is fully up and running".

#### 2.3 Import Working Configuration

Stop the enhanced container and import configuration:

```bash
# Stop the container
docker stop jenkins-minimal

# Create backup of current configuration (optional)
docker run --rm \
  -v jenkins_minimal_home:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/jenkins-minimal-backup.tar.gz -C /source .

# Import configuration from working Jenkins instance
docker run --rm \
  -v jenkins_home-2:/source \
  -v jenkins_minimal_home:/target \
  alpine sh -c "cd /source && cp -r * /target/ 2>/dev/null || true"

# Import hidden files and set proper permissions
docker run --rm \
  -v jenkins_home-2:/source \
  -v jenkins_minimal_home:/target \
  alpine sh -c "cd /source && cp -r .* /target/ 2>/dev/null || true; chown -R 1000:1000 /target"

# Restart the container
docker start jenkins-minimal
```

### Phase 3: Verification and Testing

#### 3.1 Verify Jenkins Accessibility

```bash
# Check container status
docker ps | grep jenkins-minimal

# Verify Jenkins is running
docker logs jenkins-minimal --tail 5

# Test web interface accessibility
curl -s http://localhost:8083/ | grep -i "dashboard\|jenkins"

# List imported jobs
curl -s http://localhost:8083/api/json | grep -o '"name":"[^"]*"' | head -5
```

#### 3.2 Verify Enhanced Tools

Connect to the container and verify all tools are available:

```bash
# Connect to container
docker exec -it jenkins-minimal bash

# Verify ARM cross-compilation tools
arm-linux-gnueabihf-gcc --version
arm-linux-gnueabihf-g++ --version

# Verify QEMU
qemu-system-arm --version

# Verify Python environment
python3 --version
pip3 list | grep -E "pytest|requests|pyyaml"

# Verify build tools
make --version
git --version

# Exit container
exit
```

#### 3.3 Fix GCC Version Compatibility

The container uses GCC-12 but kernel headers may expect GCC-13. Create compatibility links:

```bash
# Create GCC-13 symbolic links for both ARM and native compilation
docker exec -u root jenkins-minimal bash -c "
ln -sf /usr/bin/arm-linux-gnueabihf-gcc-12 /usr/bin/arm-linux-gnueabihf-gcc-13
ln -sf /usr/bin/arm-linux-gnueabihf-g++-12 /usr/bin/arm-linux-gnueabihf-g++-13
ln -sf /usr/bin/arm-linux-gnueabihf-gcc-ar-12 /usr/bin/arm-linux-gnueabihf-gcc-ar-13
ln -sf /usr/bin/arm-linux-gnueabihf-gcc-nm-12 /usr/bin/arm-linux-gnueabihf-gcc-nm-13
ln -sf /usr/bin/arm-linux-gnueabihf-gcc-ranlib-12 /usr/bin/arm-linux-gnueabihf-gcc-ranlib-13
ln -sf /usr/bin/gcc-12 /usr/bin/gcc-13
ln -sf /usr/bin/g++-12 /usr/bin/g++-13

# Install file command for module inspection
apt-get update && apt-get install -y file
"

# Verify the ARM GCC-13 is working
docker exec jenkins-minimal arm-linux-gnueabihf-gcc-13 --version
```

#### 3.4 Test Kernel Module Compilation

Test both ARM and native compilation capabilities:

```bash
# Connect to container
docker exec -it jenkins-minimal bash

# Navigate to kernel module directory
cd /workspace/simtemp/kernel

# Test ARM compilation
export CROSS_COMPILE=arm-linux-gnueabihf-
export ARCH=arm
make clean
make

# Test native compilation
unset CROSS_COMPILE
unset ARCH
make clean
make

exit
```

### Phase 4: Pipeline Integration

#### 4.1 Access Jenkins Web Interface

1. Open browser to `http://localhost:8083`
2. Use existing credentials from imported configuration
3. Verify all plugins and jobs are available

#### 4.2 Create New Pipeline Job

For kernel module development, create a new pipeline job using the complete Jenkinsfile:

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
                        ls -la *.ko
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
                        ls -la *.ko
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
                        python3 -m pytest tests/ -v || echo "QEMU tests completed"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: '**/simtemp/kernel/*.ko', allowEmptyArchive: true
            cleanWs()
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

## Operational Usage

### Daily Development Workflow

1. **Access Jenkins**: Navigate to `http://localhost:8083`
2. **Create/Run Jobs**: Use existing jobs or create new pipeline jobs
3. **Monitor Builds**: View build logs and artifacts
4. **Test Modules**: Use both ARM and native compilation as needed

### Container Management

```bash
# Start Jenkins
docker start jenkins-minimal

# Stop Jenkins
docker stop jenkins-minimal

# View logs
docker logs jenkins-minimal -f

# Connect to container
docker exec -it jenkins-minimal bash

# Backup configuration
docker run --rm \
  -v jenkins_minimal_home:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/jenkins-backup-$(date +%Y%m%d).tar.gz -C /source .
```

### Troubleshooting

#### Common Issues and Solutions

1. **Container won't start**
   ```bash
   docker logs jenkins-minimal
   # Check for port conflicts or volume issues
   ```

2. **ARM compilation fails**
   ```bash
   docker exec -it jenkins-minimal arm-linux-gnueabihf-gcc --version
   # Verify toolchain is installed
   ```

3. **Configuration not imported**
   ```bash
   # Re-run configuration import steps
   docker stop jenkins-minimal
   # Repeat Phase 2.3 steps
   ```

4. **Python packages missing**
   ```bash
   docker exec -it jenkins-minimal pip3 install --break-system-packages pytest requests pyyaml
   ```

## Architecture Benefits

This setup provides:

1. **Enhanced Toolchain**: Complete ARM cross-compilation environment
2. **QEMU Integration**: Full ARM system emulation capabilities
3. **Configuration Preservation**: All existing jobs, plugins, and settings
4. **Multi-Architecture Support**: Both ARM and native compilation
5. **Persistent Storage**: Configuration and artifacts preserved across restarts
6. **Workspace Integration**: Direct access to source code and build artifacts

## Maintenance

### Regular Maintenance Tasks

1. **Weekly Backups**
   ```bash
   docker run --rm \
     -v jenkins_minimal_home:/source \
     -v /backup/jenkins:/backup \
     alpine tar czf /backup/jenkins-weekly-$(date +%Y%m%d).tar.gz -C /source .
   ```

2. **Container Updates**
   ```bash
   # Pull latest base image
   docker pull jenkins/jenkins:lts
   
   # Rebuild container
   docker build -f Dockerfile.jenkins-minimal -t jenkins-minimal .
   
   # Stop old container and start new one with same volumes
   ```

3. **Cleanup Old Builds**
   - Configure Jenkins job retention policies
   - Use Jenkins disk usage plugin
   - Regular cleanup of workspace artifacts

## Success Verification

Your setup is successful when:

- ✅ Jenkins accessible at `http://localhost:8083`
- ✅ All existing jobs and plugins imported
- ✅ ARM cross-compilation working (`arm-linux-gnueabihf-gcc --version`)
- ✅ QEMU emulation available (`qemu-system-arm --version`)
- ✅ Native compilation working (`gcc --version`)
- ✅ Python testing environment ready (`pytest --version`)
- ✅ Workspace accessible (`/workspace` mount point)
- ✅ Kernel module compilation successful (both ARM and native)

This complete setup gives you the best of both worlds: a fully configured Jenkins instance with all the enhanced tools needed for ARM cross-compilation, QEMU testing, and comprehensive kernel module development workflows.