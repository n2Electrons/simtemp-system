# QEMU i.MX6UL Testing Infrastructure for Jenkins

## Overview

This document describes the complete Jenkins-integrated QEMU testing infrastructure for i.MX6UL kernel validation, specifically designed for F-K1-TC-002 Device Tree overlay testing.

## Architecture

### Components

1. **Kernel Build System**
   - NXP Linux i.MX kernel (lf-6.6.52-2.2.1)
   - ARM cross-compilation toolchain
   - Device Tree overlay support
   - NFS client/server support

2. **QEMU Testing Infrastructure**
   - mcimx6ul-evk machine emulation
   - Custom initrd with test framework
   - Automated test execution
   - Result collection and reporting

3. **Jenkins Integration**
   - Pipeline stages for QEMU testing
   - JUnit XML result reporting
   - Artifact archiving
   - PR status updates

## File Structure

```
deployment/qemu/
├── scripts/
│   ├── build-imx6ul-kernel.sh      # Kernel compilation script
│   ├── jenkins-qemu-test.sh        # Jenkins test runner
│   └── test-infrastructure.sh      # Infrastructure validation
├── kernel-source/
│   └── linux-imx-lf-6.6.52-2.2.1/ # NXP kernel source
├── build/
│   └── install/boot/               # Compiled kernel artifacts
├── tests/
│   ├── test_F_K1_TC_002.py        # Device Tree overlay test
│   └── test_framework.py          # Test execution framework
└── dtb/                           # Device Tree binaries
    └── overlay/                   # Device Tree overlays

deployment/jenkins/
├── qemu-pipeline.groovy           # Jenkins pipeline functions
└── diagnostics.groovy            # Jenkins diagnostics
```

## Jenkins Pipeline Integration

### Stage Definition

The QEMU testing is integrated as a pipeline stage:

```groovy
stage('QEMU i.MX6UL Tests') {
    timeout(time: 10, unit: 'MINUTES') {
        // Build kernel if needed
        // Run QEMU tests
        // Archive results
        // Publish JUnit results
    }
}
```

### Result Reporting

Tests produce multiple output formats:

1. **JUnit XML** (`test-results/junit-results.xml`)
   - Jenkins test result integration
   - Pass/fail status
   - Test execution details

2. **JSON Results** (`test-results/test-results.json`)
   - Detailed test metadata
   - Build information
   - Artifact references

3. **Execution Logs**
   - QEMU boot and execution log
   - Test framework output
   - Build process log

### Pipeline Configuration

Updated `simtemp/pipeline_config.yml` includes:

```yaml
qemu_test:
  enabled: true
  timeout_minutes: 15
  description: "Execute QEMU i.MX6UL kernel tests"
  depends_on: ["build"]
  test_suites: ["qemu_imx6ul"]
  machine: "mcimx6ul-evk"
  kernel_image: "deployment/qemu/build/install/boot/zImage"
  dtb_file: "deployment/qemu/build/install/boot/imx6ul-14x14-evk.dtb"
```

## Test Execution Flow

1. **Prerequisites Check**
   - Verify QEMU availability
   - Check cross-compilation tools
   - Validate kernel build artifacts

2. **Kernel Build** (if needed)
   - Extract NXP kernel source
   - Configure with i.MX6UL defaults + overlay support
   - Cross-compile for ARM
   - Generate Device Tree binaries

3. **Test Environment Setup**
   - Create initrd with test framework
   - Copy test scripts and dependencies
   - Configure Jenkins environment variables

4. **QEMU Execution**
   - Launch mcimx6ul-evk machine
   - Boot kernel with test initrd
   - Execute F-K1-TC-002 test
   - Monitor for completion signal

5. **Result Collection**
   - Extract test results from QEMU output
   - Generate JUnit XML for Jenkins
   - Create detailed JSON report
   - Archive all artifacts

## Key Features

### Device Tree Overlay Testing
- Verifies `CONFIG_OF_OVERLAY` kernel configuration
- Checks `/proc/device-tree` availability
- Tests overlay application capability

### Jenkins Compatibility
- Standard JUnit XML output
- Artifact archiving
- Build status reporting
- PR comment integration

### Error Handling
- Timeout protection for QEMU execution
- Graceful failure handling
- Detailed error reporting
- Debug artifact preservation

## Usage Examples

### Local Testing
```bash
# Test infrastructure
./deployment/qemu/scripts/test-infrastructure.sh

# Build kernel
./deployment/qemu/scripts/build-imx6ul-kernel.sh

# Run QEMU tests
./deployment/qemu/scripts/jenkins-qemu-test.sh
```

### Jenkins Integration
```groovy
// Load QEMU pipeline functions
def qemuPipeline = load 'deployment/jenkins/qemu-pipeline.groovy'

// Check prerequisites
qemuPipeline.checkQemuPrerequisites()

// Run tests
qemuPipeline.runQemuTests()

// Publish results
qemuPipeline.publishQemuTestResults()
```

## Benefits

1. **Automated Testing**
   - No manual QEMU interaction required
   - Consistent test environment
   - Reproducible results

2. **Jenkins Integration**
   - Standard CI/CD workflow
   - Automated result reporting
   - PR status updates

3. **Comprehensive Coverage**
   - Kernel compilation validation
   - Device Tree overlay support
   - QEMU machine compatibility

4. **Debugging Support**
   - Detailed logs and artifacts
   - QEMU execution traces
   - Build process visibility

## Future Enhancements

1. **Additional Test Cases**
   - More Device Tree overlay scenarios
   - Network functionality testing
   - Driver load/unload tests

2. **Performance Testing**
   - Boot time measurement
   - Memory usage analysis
   - CPU utilization tracking

3. **Multi-Architecture Support**
   - ARM64 testing
   - Different i.MX variants
   - Cross-platform validation

This infrastructure provides a solid foundation for automated kernel testing in Jenkins while maintaining compatibility with the existing simtemp-system project structure.