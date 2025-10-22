# Test Execution Commands

This document provides comprehensive commands for executing the SimTemp test suite in different configurations and environments.

## Table of Contents
- [Quick Start](#quick-start)
- [Suite-Specific Execution](#suite-specific-execution)
- [QEMU Integration Tests](#qemu-integration-tests)
- [Individual Test Execution](#individual-test-execution)
- [Development and Debugging](#development-and-debugging)
- [CI/CD Commands](#cicd-commands)

## Quick Start

### Run All Tests
```bash
# Execute complete test suite
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest -v

# Run with detailed output
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest -v -s
```

### Check Test Collection
```bash
# Verify all tests can be collected without errors
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest --collect-only
```

## Suite-Specific Execution

### Kernel Driver Base Suite
```bash
# Basic kernel driver tests
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_001.py \
  -v -s
```

### Kernel Driver Suite
```bash
# Extended kernel driver validation
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k8_tc_001.py \
  test_f_k8_tc_004.py \
  -v -s
```

### QEMU Integration Suite (Shared Session Optimized)
```bash
# Execute all QEMU integration tests with shared session optimization
# NOTE: Order matters - test_basic_qemu_boot should run first to initialize the shared session
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_002.py::test_basic_qemu_boot \
  test_f_k1_tc_003.py::test_f_k1_platform_driver_dt_registration \
  test_f_k8_tc_001_qemu.py::test_qemu_driver_load_unload \
  test_f_k8_tc_002.py::test_readers_exit_gracefully_on_unload \
  test_f_k8_tc_003_dtb.py::test_dtb_overlay_exists \
  test_f_k8_tc_003_dtb.py::test_dtb_driver_binding \
  -v -s
```

**Note**: The QEMU integration suite uses shared session management to optimize performance:
- Single QEMU instance shared across all tests
- ~80% reduction in memory usage
- ~5x faster execution compared to individual QEMU instances

## QEMU Integration Tests

### Individual QEMU Test Execution

#### Basic QEMU Boot Test
```bash
# Test QEMU boot and kernel messages
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_002.py::test_basic_qemu_boot \
  -v -s
```

#### Graceful Reader Exit Test
```bash
# Test reader applications exit gracefully on module unload
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k8_tc_002.py::test_readers_exit_gracefully_on_unload \
  -v -s
```

#### Platform Driver Device Tree Test
```bash
# Test platform driver with Device Tree registration
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_003.py::test_f_k1_platform_driver_dt_registration \
  -v -s
```

#### DTB Overlay Tests
```bash
# Test DTB overlay compilation and existence
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k8_tc_003_dtb.py::test_dtb_overlay_exists \
  -v -s

# Test DTB driver binding verification
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k8_tc_003_dtb.py::test_dtb_driver_binding \
  -v -s
```

### QEMU Environment Variables
```bash
# Set specific QEMU configuration
export QEMU_DIR='deployment/qemu'
export KERNEL_IMAGE='/workspace/deployment/qemu/linux-imx-5.10/arch/arm/boot/zImage'
export DTB_FILE='/workspace/deployment/qemu/linux-imx-5.10/arch/arm/boot/dts/imx6q-sabresd-with-simtemp.dtb'
export ROOTFS_IMAGE='/workspace/deployment/qemu/rootfs.cpio.gz'

# Execute with environment
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest test_f_k1_tc_002.py -v -s
```

## Individual Test Execution

### Kernel Module Tests
```bash
# F-K1-TC-001: Driver registration via insmod
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_001.py::test_insmod_registers_driver \
  -v -s

# F-K8-TC-001: Load/unload without warnings
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k8_tc_001.py::test_driver_load_unload \
  -v -s

# F-K8-TC-004: Comprehensive driver validation
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k8_tc_004.py::test_driver_validation \
  -v -s
```

### Specific Test Functions
```bash
# Run specific test function with pattern matching
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  -k "test_basic_qemu_boot" \
  -v -s

# Run multiple specific functions
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  -k "test_basic_qemu_boot or test_driver_load_unload" \
  -v -s
```

## Development and Debugging

### Debug Mode Execution
```bash
# Enable maximum verbosity for debugging
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_002.py \
  -v -s --tb=long --capture=no

# Run with Python debugger on failure
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_002.py \
  -v -s --pdb
```

### Performance and Resource Monitoring
```bash
# Run tests with performance monitoring
time TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_002.py::test_basic_qemu_boot \
  -v -s

# Monitor memory usage during QEMU tests
/usr/bin/time -v TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  test_f_k1_tc_002.py::test_basic_qemu_boot \
  -v -s
```

### Test Environment Validation
```bash
# Verify test dependencies
python3 -c "import test_utils; print('✓ Test utilities imported successfully')"

# Check sudo configuration
python3 -c "from test_utils import get_sudo_prefix; print(f'Sudo prefix: \"{get_sudo_prefix()}\"')"

# Validate QEMU session management
python3 -c "from test_utils import get_shared_qemu_session; print('✓ QEMU session management available')"
```

## CI/CD Commands

### Jenkins Pipeline Commands
```bash
# Jenkins execution with proper environment
export TEST_CONFIG_PATH=config/simtemp_tests.yml
export CI=true
export WORKSPACE=/var/jenkins_home/workspace/simtemp-tests

# Execute full suite for CI
python3 -m pytest --tb=short --maxfail=1

# Execute QEMU integration for CI (optimized with correct order)
python3 -m pytest \
  test_f_k1_tc_002.py::test_basic_qemu_boot \
  test_f_k1_tc_003.py::test_f_k1_platform_driver_dt_registration \
  test_f_k8_tc_001_qemu.py::test_qemu_driver_load_unload \
  test_f_k8_tc_002.py::test_readers_exit_gracefully_on_unload \
  test_f_k8_tc_003_dtb.py::test_dtb_overlay_exists \
  test_f_k8_tc_003_dtb.py::test_dtb_driver_binding \
  --tb=short --maxfail=1
```

### Docker Container Execution
```bash
# Run in privileged container (recommended for CI)
docker run --privileged -v $(pwd):/workspace simtemp-tests \
  TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest -v

# Run as root in container
docker run --user root -v $(pwd):/workspace simtemp-tests \
  TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest -v
```

### GitHub Actions Commands
```bash
# GitHub Actions environment setup
export CI=true
export GITHUB_ACTIONS=true

# Execute with GitHub Actions optimizations
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest \
  --tb=short \
  --maxfail=1 \
  --durations=10
```

## Troubleshooting Commands

### Import Error Diagnosis
```bash
# Test individual imports
python3 -c "import test_f_k8_tc_002; print('✓ F-K8-TC-002 imports successfully')"
python3 -c "import test_f_k1_tc_003; print('✓ F-K1-TC-003 imports successfully')"

# Check for import errors across all tests
TEST_CONFIG_PATH=config/simtemp_tests.yml python3 -m pytest --collect-only -q 2>&1 | grep -i error || echo "✓ No import errors found"
```

### QEMU Session Debugging
```bash
# Check QEMU session status
python3 -c "
from test_utils import is_qemu_session_active, get_qemu_session_marker_path
print(f'QEMU session active: {is_qemu_session_active()}')
print(f'Marker path: {get_qemu_session_marker_path()}')
"

# Manual QEMU session cleanup
python3 -c "from test_utils import cleanup_qemu_session; cleanup_qemu_session()"
```

### Module and Kernel Status
```bash
# Check if module is loaded
lsmod | grep nxp_simtemp || echo "Module not loaded"

# Check kernel messages
sudo dmesg | tail -20

# Verify module file exists
ls -la kernel/obj/nxp_simtemp.ko
```

## Performance Optimization Notes

### QEMU Shared Session Benefits
- **Before optimization**: Each test started individual QEMU instance (~60s boot time each)
- **After optimization**: Single shared QEMU session across all tests (~60s total boot time)
- **Memory savings**: ~80% reduction in memory usage
- **Time savings**: ~5x faster execution for QEMU test suite

### Recommended Test Execution Order
1. Quick validation tests (F-K1-TC-001)
2. Host-based driver tests (F-K8-TC-001, F-K8-TC-004)
3. QEMU integration suite (all QEMU tests together for session optimization)

### Resource Requirements
- **Host tests**: ~100MB RAM, no special privileges
- **QEMU tests**: ~1GB RAM, sudo access for module operations
- **CI environment**: Privileged container or passwordless sudo configuration

## Configuration Files

### Test Configuration
- **Main config**: `config/simtemp_tests.yml`
- **Pytest config**: `pytest.ini`
- **Environment**: Set `TEST_CONFIG_PATH=config/simtemp_tests.yml`

### Suite Configurations
- **kernel_driver_base**: Basic infrastructure tests
- **kernel_driver_suite**: Extended validation tests  
- **qemu_integration**: ARM QEMU emulation tests with shared session optimization

For more detailed information about test suites and configurations, see:
- `config/simtemp_tests.yml` - Main test configuration
- `docs/QEMU_INSTANCE_OPTIMIZATION.md` - QEMU optimization details
- `docs/SUDO_CONFIGURATION.md` - Privilege configuration guide