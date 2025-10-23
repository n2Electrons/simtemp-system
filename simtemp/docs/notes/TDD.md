# Test-Driven Development (TDD) in the SimTemp Framework

## Introduction

This document describes the implementation and flow of Test-Driven Development (TDD) in the SimTemp project, showing how the test-driven development methodology is structured for Linux kernel module development.

## TDD Philosophy in SimTemp

Kernel module development requires a rigorous testing approach due to:
- The criticality of code running in kernel space
- The difficulty of debugging in the kernel
- The need to ensure system stability
- Associated security risks

## Testing Framework Structure

### Test Organization

The SimTemp framework organizes tests into three main categories:

1. **kernel_driver_base**: Fundamental driver tests
2. **kernel_driver_suite**: Complete driver test suite
3. **qemu_integration**: Integration tests in QEMU environment

### TDD Flow Example

#### Red-Green-Refactor Cycle

**1. RED - Write failing test**
```python
def test_insmod_registers_driver(self):
    """Test that verifies insmod registers the driver correctly"""
    # This test will initially fail
    result = self.load_module()
    assert "registered successfully" in result.stdout
```

**2. GREEN - Implement minimal code**
```c
// In nxp_simtemp.c
static int __init nxp_simtemp_init(void)
{
    printk(KERN_INFO "nxp_simtemp: registered successfully\n");
    return platform_driver_register(&nxp_simtemp_driver);
}
```

**3. REFACTOR - Improve the code**
```c
static int __init nxp_simtemp_init(void)
{
    int ret;
    
    ret = platform_driver_register(&nxp_simtemp_driver);
    if (ret) {
        pr_err("nxp_simtemp: Failed to register platform driver\n");
        return ret;
    }
    
    pr_info("nxp_simtemp: registered successfully\n");
    return 0;
}
```

## Test Execution Results

### Current Test Suite Results

Here's a real example of test execution from the current development branch `f-k8-tc-002-dtb-drv-bind`:

```
================================= test session starts ==================================
platform linux -- Python 3.12.3, pytest-7.4.4, pluggy-1.4.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/jorge/challenge-2509/simtemp-system/simtemp/tests
configfile: pytest.ini
collected 5 items                                                                      

test_f_k8_tc_003_dtb.py::test_dtb_overlay_exists PASSED
test_f_k8_tc_003_dtb.py::test_dtb_driver_binding PASSED
test_f_k8_tc_003_dtb.py::test_dtb_property_parsing FAILED
test_f_k8_tc_003_dtb.py::test_dtb_functionality FAILED
test_f_k8_tc_003_dtb.py::test_dtb_driver_binding_and_functionality FAILED

============================= 3 failed, 2 passed in 0.07s ==============================
```

### Visual Test Results Summary

| Test Case | Status | Description |
|-----------|--------|-------------|
| 📄 `test_dtb_overlay_exists` | ✅ **PASSED** | Device Tree overlay file exists and is properly formatted |
| 🔗 `test_dtb_driver_binding` | ✅ **PASSED** | Driver correctly declares device tree compatibility |
| ⚙️ `test_dtb_property_parsing` | ❌ **FAILED** | DTB property parsing functionality not yet implemented |
| 🖥️ `test_dtb_functionality` | ❌ **FAILED** | Device file `/dev/simtemp` not created |
| 🔄 `test_dtb_driver_binding_and_functionality` | ❌ **FAILED** | Combined test fails due to missing property parsing |

### Progress Indicator

```
Overall Progress: 40% Complete (2/5 tests passing)

✅✅❌❌❌  [████████░░░░░░░░░░] 40%

Foundation Phase:    ✅ Complete (DTB binding works)
Implementation Phase: 🔄 In Progress (Property parsing needed)
Integration Phase:   ❌ Pending (Full functionality)
```

### Results Interpretation

**✅ Successful Tests (2/5):**
- `test_dtb_overlay_exists`: Device Tree overlay file exists and is properly formatted
- `test_dtb_driver_binding`: Driver correctly declares device tree compatibility (`nxp,simtemp`)

**❌ Failed Tests (3/5):**
- `test_dtb_property_parsing`: DTB property parsing functionality not yet implemented
- `test_dtb_functionality`: Device file `/dev/simtemp` not created, functionality missing
- `test_dtb_driver_binding_and_functionality`: Combined test fails due to missing property parsing

### TDD Status Analysis

This is a perfect example of **TDD in action**. The test results show:

1. **Foundation Complete**: Basic device tree binding is working
2. **Next Implementation Phase**: Property parsing needs to be implemented
3. **Clear Requirements**: Tests define exactly what needs to be built
4. **Incremental Progress**: 40% of functionality is working (2/5 tests pass)

```
TDD Cycle Visualization:

Current State:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RED Phase     │    │  GREEN Phase    │    │ REFACTOR Phase  │
│                 │    │                 │    │                 │
│ ❌ 3 tests fail │ -> │ 🔄 Implement    │ -> │ ✨ Clean code   │
│ Property parse  │    │ DTB parsing     │    │ Optimize        │
│ Device creation │    │ Char device     │    │ performance     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
      ^                                                    │
      │                                                    │
      └────────────────────────────────────────────────────┘
                           REPEAT

Next Implementation Priority:
1. 🎯 test_dtb_property_parsing  <- Start here
2. 🎯 test_dtb_functionality     <- Then this  
3. 🎯 Integration test           <- Will pass automatically
```

The failing tests provide clear guidance on what to implement next in the TDD cycle.

## Types of Implemented Tests

### Current Test Suite: `test_f_k8_tc_003_dtb.py`

This test file demonstrates a comprehensive TDD approach for Device Tree Blob (DTB) functionality:

#### 1. Test Structure Analysis
```python
def test_dtb_overlay_exists():
    """Verify DTB overlay file exists and is properly formatted"""
    # ✅ PASSING - Foundation test ensuring DTB file exists

def test_dtb_driver_binding():
    """Test DTB driver binding using compatible string"""
    # ✅ PASSING - Driver properly declares device tree compatibility

def test_dtb_property_parsing():
    """Test DTB property parsing functionality"""
    # ❌ FAILING - Property parsing not yet implemented
    sysfs_paths = ["/sys/devices/platform/simtemp.0",
                   "/sys/devices/platform/simtemp@0"]
    
    for path in sysfs_paths:
        if os.path.exists(path):
            for prop in ['sampling_ms', 'threshold_mC', 'mode']:
                # Check if device tree properties are exposed in sysfs
                prop_file = os.path.join(path, prop)
                if os.path.exists(prop_file):
                    properties_found = True

def test_dtb_functionality():
    """Test driver functionality with DTB configuration"""
    # ❌ FAILING - Device file creation not implemented
    device_file = "/dev/simtemp"
    if not os.path.exists(device_file):
        pytest.fail("Device file not found. DTB-based driver functionality not implemented.")

def test_dtb_driver_binding_and_functionality():
    """Combined DTB driver binding and functionality verification test"""
    # ❌ FAILING - Integration test that combines all previous tests
```

### 2. Module Load Tests (insmod/rmmod)
```python
def test_driver_load_unload(self):
    """Verifies that the module can be loaded and unloaded correctly"""
    # Load module
    load_result = self.load_module()
    assert load_result.returncode == 0
    
    # Verify it's loaded
    assert self.is_module_loaded()
    
    # Unload module
    unload_result = self.unload_module()
    assert unload_result.returncode == 0
    assert not self.is_module_loaded()
```

### 2. Device Tree Binding Tests
```python
def test_f_k1_platform_driver_dt_registration(self):
    """Verifies platform driver registration with device tree"""
    result = self.load_module()
    
    # Verify the driver registers with the platform subsystem
    assert "platform driver registered" in result.stdout
    
    # Verify device tree binding
    assert self.check_dt_binding()
```

### 3. QEMU Integration Tests
```python
def test_basic_qemu_boot(self):
    """Basic boot test in QEMU environment"""
    boot_result = self.qemu_boot()
    assert boot_result.success
    assert "Linux version" in boot_result.console_output
```

## TDD Best Practices in SimTemp

### 1. Test Isolation
- Each test must be independent
- Proper setup and teardown for loading/unloading modules
- State cleanup between tests

### 2. Granular Tests
- Separate tests for specific functionality
- One assertion per test when possible
- Descriptive names that indicate what is being tested

### 3. Testing Environments
- **Unit tests**: Fast tests of individual components
- **Integration tests**: Tests in controlled QEMU environment
- **System tests**: Tests on real hardware (when available)

### 4. Automation
- Jenkins integration for CI/CD
- Automatic execution on each push
- Results reporting and artifacts

## Execution Commands

### Run all tests
```bash
cd /home/jorge/challenge-2509/simtemp-system/simtemp/tests
python3 -m pytest -v
```

### Run specific test categories
```bash
# DTB-specific tests (current development focus)
python3 -m pytest test_f_k8_tc_003_dtb.py -v -s

# Kernel driver base tests
python3 -m pytest -v -k "kernel_driver_base"

# QEMU integration tests  
python3 -m pytest -v -k "qemu_integration"
```

### Run individual tests for TDD development
```bash
# Test only property parsing (currently failing)
python3 -m pytest test_f_k8_tc_003_dtb.py::test_dtb_property_parsing -v -s

# Test only device functionality (currently failing)
python3 -m pytest test_f_k8_tc_003_dtb.py::test_dtb_functionality -v -s

# Test only driver binding (currently passing)
python3 -m pytest test_f_k8_tc_003_dtb.py::test_dtb_driver_binding -v -s
```

### Current Development Workflow
```bash
# 1. Run failing test to understand requirements
python3 -m pytest test_f_k8_tc_003_dtb.py::test_dtb_property_parsing -v -s

# 2. Implement minimal fix in nxp_simtemp.c

# 3. Re-run test to verify fix
python3 -m pytest test_f_k8_tc_003_dtb.py::test_dtb_property_parsing -v -s

# 4. Run full DTB suite to check for regressions
python3 -m pytest test_f_k8_tc_003_dtb.py -v -s
```

## Failure Analysis

### Current Failure Analysis: F-K8-TC-003 DTB Tests

Based on the actual test results, here's the TDD-driven development roadmap:

#### 1. **test_dtb_property_parsing** - Priority 1
**Failure Message**: `DTB property parsing failed. DTB property parsing not implemented.`

**Root Cause**: The driver loads and binds to device tree, but doesn't parse or expose device tree properties.

**TDD Solution Path**:
```c
// In nxp_simtemp.c - Add property parsing in probe function
static int nxp_simtemp_probe(struct platform_device *pdev)
{
    struct device_node *np = pdev->dev.of_node;
    u32 sampling_ms, threshold_mC;
    const char *mode;
    
    // Parse device tree properties
    if (of_property_read_u32(np, "sampling_ms", &sampling_ms))
        sampling_ms = 1000; // default value
    
    if (of_property_read_u32(np, "threshold_mC", &threshold_mC))
        threshold_mC = 25000; // default 25°C in milli-celsius
    
    if (of_property_read_string(np, "mode", &mode))
        mode = "normal"; // default mode
    
    // Create sysfs attributes to expose these properties
    // This will make the test pass
}
```

#### 2. **test_dtb_functionality** - Priority 2
**Failure Message**: `Device file not found. DTB-based driver functionality not implemented.`

**Root Cause**: Driver doesn't create `/dev/simtemp` character device.

**TDD Solution Path**:
```c
// Add character device creation
static int nxp_simtemp_probe(struct platform_device *pdev)
{
    // After property parsing...
    
    // Register character device
    major_number = register_chrdev(0, DEVICE_NAME, &simtemp_fops);
    if (major_number < 0) {
        pr_err("Failed to register character device\n");
        return major_number;
    }
    
    // Create device class and device file
    simtemp_class = class_create(THIS_MODULE, CLASS_NAME);
    simtemp_device = device_create(simtemp_class, NULL, 
                                   MKDEV(major_number, 0), 
                                   NULL, DEVICE_NAME);
}
```

#### 3. **test_dtb_driver_binding_and_functionality** - Priority 3
**Failure Message**: `DTB property parsing not implemented`

**Root Cause**: Integration test that depends on fixes for tests 1 and 2.

**TDD Approach**: This test will automatically pass once the previous two issues are resolved.

### TDD Development Cycle

The current failure pattern shows a typical TDD development cycle:

1. **RED**: 3 tests failing, defining required functionality
2. **GREEN**: Implement minimal code to make tests pass (property parsing first)
3. **REFACTOR**: Clean up implementation while keeping tests green
4. **REPEAT**: Move to next failing test

When a test fails (as seen with the current DTB tests), the TDD process requires:

1. **Analyze the failure**: Review logs and error messages
2. **Identify the root cause**: Missing implementation? Code bug?
3. **Implement minimal solution**: Make the test pass
4. **Refactor**: Improve code while keeping tests green

## Environment Configuration

The framework uses:
- **pytest**: Python testing framework
- **Docker/QEMU**: Isolated testing environment
- **Jenkins**: CI/CD pipeline
- **Device Tree**: Hardware configuration for IMX6

## Conclusion

The TDD approach in SimTemp ensures:
- More robust and reliable code
- Living documentation through tests
- Early detection of regressions
- Greater confidence in code changes
- Incremental and controlled development

### Current Project Status

The SimTemp project demonstrates active TDD development:

**✅ Completed (40% - 2/5 tests passing)**:
- Device Tree overlay infrastructure
- Driver binding to device tree compatible strings
- Basic test framework and CI/CD integration

**🔄 In Progress (60% - 3/5 tests failing)**:
- Device Tree property parsing (`sampling_ms`, `threshold_mC`, `mode`)
- Character device creation (`/dev/simtemp`)
- Full DTB functionality integration

**📋 Next Steps**:
1. Implement device tree property parsing in `nxp_simtemp_probe()`
2. Add character device registration
3. Create sysfs attributes for device tree properties
4. Verify all tests pass (target: 5/5 green)

The framework provides the necessary tools to implement TDD effectively in Linux kernel module development, with support for testing in both virtualized environments and real hardware. The current test results clearly show what needs to be implemented next, demonstrating the power of test-driven development in guiding implementation priorities.

## Visual Development Roadmap

```
SimTemp TDD Development Pipeline:

Phase 1: Foundation ✅ COMPLETE
├── test_dtb_overlay_exists      ✅ PASSED
└── test_dtb_driver_binding      ✅ PASSED

Phase 2: Implementation 🔄 IN PROGRESS
├── test_dtb_property_parsing    ❌ NEXT → Implement property parsing
└── test_dtb_functionality       ❌ TODO → Create /dev/simtemp device

Phase 3: Integration ⏳ PENDING
└── test_dtb_driver_binding_and_functionality ❌ AUTO → Will pass when above complete

Current Branch: f-k8-tc-002-dtb-drv-bind
Target: 5/5 tests passing ✅✅✅✅✅
Status: 2/5 tests passing ✅✅❌❌❌
```

This visual representation shows the clear path forward in the TDD development process.