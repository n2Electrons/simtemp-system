# Test Execution Order Summary

This document summarizes the pytest execution order assigned to critical tests:

## Order 1-10: Boot and Initialization
- `@pytest.mark.order(1)` - test_arm_f_k1_tc_002_boot.py::test_basic_qemu_boot()

## Order 11-20: Module Loading
- `@pytest.mark.order(12)` - test_x86_f_k1_tc_001_insmod.py::test_insmod_registers_driver()
- `@pytest.mark.order(13)` - test_x86_f_k8_tc_001_loadunload.py::test_driver_load_unload_clean_sequence()
- `@pytest.mark.order(15)` - test_arm_f_k1_tc_003_platform.py::test_f_k1_platform_driver_dt_registration()

## Order 21-30: Basic Functionality
- `@pytest.mark.order(20)` - test_simple_device_read.py::test_simple_device_read()
- `@pytest.mark.order(21)` - test_x86_f_k3_simple.py::test_device_node_exists()
- `@pytest.mark.order(25)` - test_x86_f_k8_tc_004_validation.py::TestDriverValidation (all methods)
- `@pytest.mark.order(26)` - test_x86_f_k8_tc_004_validation.py::test_driver_validation()
- `@pytest.mark.order(30)` - test_x86_f_k8_tc_002_graceful.py::test_readers_exit_gracefully_on_unload()

## Order 31-40: Advanced Functionality
- `@pytest.mark.order(35)` - test_x86_f_k5_tc_001_alert.py::test_alert_within_2_periods()

## Order 41-50: Problem Tests and Stress Tests
- `@pytest.mark.order(45)` - test_arm_f_k8_tc_003_dtbbind.py::test_dtb_overlay_exists()
- `@pytest.mark.order(46)` - test_arm_f_k8_tc_003_dtbbind.py::test_dtb_driver_binding_and_functionality()
- `@pytest.mark.order(48)` - test_arm_f_k8_tc_001_loadunload.py::test_qemu_driver_load_unload()
- `@pytest.mark.order(50)` - test_x86_f_k8_tc_001_loadunload.py::test_driver_load_unload_stress()

## Rationale

1. **Boot tests first**: Ensure QEMU environment is ready
2. **Module loading**: Test basic insmod/rmmod functionality
3. **Platform registration**: Verify Device Tree integration
4. **Basic functionality**: Device creation, reading, validation
5. **Advanced features**: F-K5 alert functionality, graceful shutdown
6. **Problem tests last**: DTB binding tests that may fail in certain environments
7. **Stress tests last**: Heavy load tests that might affect other tests

This order ensures:
- Dependencies are met (QEMU → modules → devices → functionality)
- Stable tests run first
- Problematic tests don't affect others
- Cleanup happens in proper sequence