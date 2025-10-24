#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Driver Validation Test Module
============================

This module contains comprehensive validation tests for the NXP SimTemp driver
based on the most important commands from the development history.

Test Categories:
- Device and sysfs attribute verification
- Module loading and dependency verification  
- Kernel log verification
- Complete driver functionality validation
"""

import pytest
import subprocess
import os
import glob
import time

# Import common test utilities
from test_utils import SUDO, obj_path, load_simtemp_modules


@pytest.mark.order(25)
class TestDriverValidation:
    """Comprehensive driver validation test suite"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Clean up any existing modules (correct order: main first, then stub)
        subprocess.run(f"{SUDO}rmmod nxp_simtemp",
                       shell=True, stderr=subprocess.DEVNULL)
        subprocess.run(f"{SUDO}rmmod nxp_simtemp_stub",
                       shell=True, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up modules after test (correct order: main first, then stub)
        subprocess.run(f"{SUDO}rmmod nxp_simtemp",
                       shell=True, stderr=subprocess.DEVNULL)
        subprocess.run(f"{SUDO}rmmod nxp_simtemp_stub",
                       shell=True, stderr=subprocess.DEVNULL)

    def test_device_sysfs_attributes(self):
        """
        Test: Verify device creation and sysfs attributes
        
        Based on commands:
        - ls -la /sys/devices/platform/nxp-simtemp.0/
        - ls -la /sys/devices/platform/nxp-simtemp.1.auto/
        - cat sysfs attributes
        """
        print("\n=== Testing Device and Sysfs Attributes ===")
        
        # Load modules using our consistent method
        if not load_simtemp_modules():
            pytest.fail("Failed to load simtemp modules")
        
        # Give kernel time to create devices
        time.sleep(1)
        
        # Verify device directories exist
        device0_path = "/sys/devices/platform/nxp-simtemp.0"
        device1_path = "/sys/devices/platform/nxp-simtemp.1.auto"
        
        assert os.path.exists(device0_path), f"Device 0 not found at {device0_path}"
        
        # Check if Device 1 exists (may not exist in all environments)
        device1_exists = os.path.exists(device1_path)
        if device1_exists:
            print(f"✓ Both devices found: {device0_path}, {device1_path}")
        else:
            print(f"✓ Device 0 found: {device0_path}")
            print(f"ℹ Device 1 not found (normal in some environments): {device1_path}")
        
        # Verify sysfs attributes exist for device 0
        device0_attrs = ["sampling_ms", "threshold_mC", "mode"]
        for attr in device0_attrs:
            attr_path = f"{device0_path}/{attr}"
            assert os.path.exists(attr_path), f"Attribute {attr} not found for device 0"
        
        # Verify sysfs attributes exist for device 1 (if it exists)
        if device1_exists:
            for attr in device0_attrs:
                attr_path = f"{device1_path}/{attr}"
                if not os.path.exists(attr_path):
                    print(f"Warning: Attribute {attr} not found for device 1")
                    device1_exists = False
                    break
        
        if device1_exists:
            print("✓ All sysfs attributes found for both devices")
        else:
            print("✓ All sysfs attributes found for device 0")
        
        # Read and verify attribute values for each device
        # Note: Device configurations may vary between environments
        devices_validated = 0
        
        # Validate Device 0
        with open(f"{device0_path}/sampling_ms", 'r') as f:
            sampling_ms_0 = f.read().strip()
        with open(f"{device0_path}/threshold_mC", 'r') as f:
            threshold_mC_0 = f.read().strip()
        with open(f"{device0_path}/mode", 'r') as f:
            mode_0 = f.read().strip()
            
        print(f"Device 0 values: sampling_ms={sampling_ms_0}, threshold_mC={threshold_mC_0}, mode={mode_0}")
        
        # Validate Device 1 (if it exists and is accessible)
        try:
            if device1_exists:
                with open(f"{device1_path}/sampling_ms", 'r') as f:
                    sampling_ms_1 = f.read().strip()
                with open(f"{device1_path}/threshold_mC", 'r') as f:
                    threshold_mC_1 = f.read().strip()
                with open(f"{device1_path}/mode", 'r') as f:
                    mode_1 = f.read().strip()
                    
                print(f"Device 1 values: sampling_ms={sampling_ms_1}, threshold_mC={threshold_mC_1}, mode={mode_1}")
                devices_validated += 1
            else:
                sampling_ms_1, threshold_mC_1, mode_1 = None, None, None
        except (FileNotFoundError, PermissionError) as e:
            print(f"Warning: Could not read Device 1 attributes: {e}")
            sampling_ms_1, threshold_mC_1, mode_1 = None, None, None
        
        # Flexible validation based on environment
        # Check if we have the expected device configurations
        devices_config = [
            (sampling_ms_0, threshold_mC_0, mode_0),
        ]
        if sampling_ms_1:
            devices_config.append((sampling_ms_1, threshold_mC_1, mode_1))
        
        # Expected configurations (main driver and stub)
        expected_configs = [
            ("1000", "50000", "default"),  # Main driver default
            ("200", "60000", "lab")        # Stub device lab config
        ]
        
        # Validate that we have at least one valid configuration
        valid_devices = 0
        for i, (sampling, threshold, mode) in enumerate(devices_config):
            device_name = f"Device {i}"
            
            # Check if this device matches any expected configuration
            for exp_sampling, exp_threshold, exp_mode in expected_configs:
                if (sampling == exp_sampling and 
                    threshold == exp_threshold and 
                    mode == exp_mode):
                    print(f"✓ {device_name} matches expected config: {exp_sampling}ms, {exp_threshold}mC, {exp_mode}")
                    valid_devices += 1
                    break
            else:
                print(f"ℹ {device_name} has non-standard config: {sampling}ms, {threshold}mC, {mode}")
        
        # Ensure we have at least one properly configured device
        assert valid_devices >= 1, f"No devices match expected configurations. Found: {devices_config}"
        print(f"✓ Validated {valid_devices} device(s) with correct configurations")

    def test_module_dependencies_and_loading(self):
        """
        Test: Verify module dependencies and loading behavior
        
        Based on commands:
        - modinfo obj/nxp_simtemp.ko | grep -E "(filename|depends|softdep)"
        - modinfo obj/nxp_simtemp_stub.ko | grep -E "(filename|depends|softdep)"
        - lsmod | grep nxp
        - Load modules using consistent method
        """
        print("\n=== Testing Module Dependencies and Loading ===")
        
        module_path = os.path.join(obj_path, "nxp_simtemp.ko")
        stub_path = os.path.join(obj_path, "nxp_simtemp_stub.ko")
        
        # Verify module files exist
        assert os.path.exists(module_path), f"Main module not found: {module_path}"
        assert os.path.exists(stub_path), f"Stub module not found: {stub_path}"
        
        # Test modinfo for main module
        modinfo_main = subprocess.run(
            ['modinfo', module_path], capture_output=True, text=True
        )
        assert modinfo_main.returncode == 0, "modinfo failed for main module"
        
        # Check for softdep in main module (optional for ARM builds)
        if "softdep:" in modinfo_main.stdout:
            assert "pre: nxp_simtemp_stub" in modinfo_main.stdout, "Main module missing stub dependency"
            print("✓ Main module has correct softdep: pre: nxp_simtemp_stub")
        else:
            print("ℹ Main module has no softdep configuration (normal for ARM builds)")
        
        # Test modinfo for stub module
        modinfo_stub = subprocess.run(
            ['modinfo', stub_path], capture_output=True, text=True
        )
        assert modinfo_stub.returncode == 0, "modinfo failed for stub module"
        
        # Check for softdep in stub module (conditional on x86)
        if os.path.exists(stub_path):
            assert "softdep:" in modinfo_stub.stdout, "Stub module missing softdep configuration"
            assert "post: nxp_simtemp" in modinfo_stub.stdout, "Stub module missing main dependency"
            print("✓ Stub module has correct softdep: post: nxp_simtemp")
        else:
            print("ℹ Stub module not present (normal for ARM builds)")
        
        # Test loading with our consistent method
        if not load_simtemp_modules():
            pytest.fail("Failed to load simtemp modules")
        
        # Verify main module is loaded (stub is optional)
        lsmod = subprocess.run("lsmod | grep nxp", shell=True,
                               capture_output=True, text=True)
        assert "nxp_simtemp" in lsmod.stdout, "Main module not found in lsmod"
        
        if os.path.exists(stub_path):
            assert "nxp_simtemp_stub" in lsmod.stdout, "Stub module not found in lsmod"
            print("✓ Both modules loaded successfully")
        else:
            print("✓ Main module loaded (stub not needed for ARM)")

    def test_kernel_logs_verification(self):
        """
        Test: Verify kernel logs show proper driver operation
        
        Based on commands:
        - sudo dmesg | grep -A 5 -B 5 "NXP SimTemp driver"
        - sudo dmesg | grep -E "(Failed to create|sysfs.*error|probe.*failed)"
        - sudo dmesg | tail -10
        """
        print("\n=== Testing Kernel Logs ===")
        
        # Clear any old logs by getting current dmesg position
        pre_dmesg = subprocess.run(f"{SUDO}dmesg | wc -l", shell=True, capture_output=True, text=True)
        pre_lines = int(pre_dmesg.stdout.strip())
        
        # Load the driver using our consistent method
        if not load_simtemp_modules():
            pytest.fail("Failed to load simtemp modules")
        
        time.sleep(1)  # Give kernel time to generate logs
        
        # Get new logs
        post_dmesg = subprocess.run(f"{SUDO}dmesg", shell=True, capture_output=True, text=True)
        dmesg_lines = post_dmesg.stdout.split('\n')
        new_logs = dmesg_lines[pre_lines:]
        new_logs_text = '\n'.join(new_logs)
        
        # Check for driver initialization messages
        assert "NXP SimTemp driver: Initializing" in new_logs_text, \
            "Driver initialization message not found"
        assert "NXP SimTemp driver: Initialized successfully" in new_logs_text, \
            "Driver initialization completion message not found"
        print("✓ Driver initialization logs found")
        
        # Check for device probe messages
        assert "NXP SimTemp probe starting" in new_logs_text, \
            "Device probe messages not found"
        assert "Probe completed:" in new_logs_text, \
            "Successful probe messages not found"
        print("✓ Device probe logs found")
        
        # Check for absence of error messages
        error_patterns = ["Failed to create", "sysfs.*error", "probe.*failed", "ERROR"]
        for pattern in error_patterns:
            error_check = subprocess.run(
                f"echo '{new_logs_text}' | grep -E '{pattern}'", 
                shell=True, capture_output=True
            )
            if error_check.returncode == 0:
                pytest.fail(f"Found error pattern '{pattern}' in kernel logs: {error_check.stdout.decode()}")
        
        print("✓ No error patterns found in kernel logs")

    def test_complete_driver_functionality(self):
        """
        Test: Complete end-to-end driver functionality test
        
        This is the comprehensive test combining all important validation steps.
        """
        print("\n=== Complete Driver Functionality Test ===")
        
        # 1. Verify compilation and dependencies (flexible for ARM/x86)
        module_path = os.path.join(obj_path, "nxp_simtemp.ko")
        modinfo = subprocess.run(
            f"modinfo {module_path} | grep -E '(softdep|alias.*of)'",
            shell=True, capture_output=True, text=True
        )
        assert modinfo.returncode == 0, "Failed to get module info"
        
        # Check for dependencies (optional for ARM)
        if "softdep" in modinfo.stdout:
            print("✓ Module compilation and dependencies verified")
        else:
            # Check for device tree aliases instead
            assert "alias" in modinfo.stdout, "Module aliases not found"
            print("✓ Module compilation and device tree aliases verified")
        
        # 2. Load with automatic dependencies using our consistent method
        if not load_simtemp_modules():
            pytest.fail("Failed to load simtemp modules")
        print("✓ Module loading successful")
        
        # 3. Verify devices created (flexible - at least 1 device required)
        devices = glob.glob("/sys/devices/platform/nxp-simtemp*")
        assert len(devices) >= 1, f"Expected at least 1 device, found {len(devices)}"
        print(f"✓ Found {len(devices)} device(s): {[os.path.basename(d) for d in devices]}")
        
        # 4. Verify DTB attributes working
        for device in devices:
            sampling_ms_file = f"{device}/sampling_ms"
            assert os.path.exists(sampling_ms_file), f"sampling_ms not found in {device}"
            
            with open(sampling_ms_file, 'r') as f:
                value = f.read().strip()
                assert value.isdigit(), f"Invalid sampling_ms value: {value}"
        
        print("✓ DTB attributes accessible and valid")
        
        # 5. Verify logs without errors
        recent_logs = subprocess.run(
            f"{SUDO}dmesg | grep 'Probe completed:' | tail -2",
            shell=True, capture_output=True, text=True
        )
        assert "Probe completed:" in recent_logs.stdout, \
            f"Successful probe not found: {recent_logs.stdout}"
        print("✓ Recent logs show successful operation")
        
        print("🎉 Complete driver functionality validation PASSED!")

    def test_driver_bind_unbind_operations(self):
        """
        Test: Advanced bind/unbind operations for driver robustness
        
        Based on commands:
        - echo "nxp-simtemp.0" | sudo tee /sys/bus/platform/devices/nxp-simtemp.0/driver/unbind
        - echo "nxp-simtemp.0" | sudo tee /sys/bus/platform/drivers/nxp-simtemp/bind
        """
        print("\n=== Testing Driver Bind/Unbind Operations ===")
        
        # Load the driver first using our consistent method
        if not load_simtemp_modules():
            pytest.fail("Failed to load simtemp modules")
        
        time.sleep(1)
        
        device_name = "nxp-simtemp.0"
        unbind_path = f"/sys/bus/platform/devices/{device_name}/driver/unbind"
        bind_path = "/sys/bus/platform/drivers/nxp-simtemp/bind"
        
        # Verify device is initially bound
        driver_link = f"/sys/devices/platform/{device_name}/driver"
        assert os.path.exists(driver_link), f"Device {device_name} not initially bound"
        print("✓ Device initially bound to driver")
        
        # Test unbind operation
        unbind_result = subprocess.run(
            f"echo '{device_name}' | {SUDO}tee {unbind_path}",
            shell=True, capture_output=True
        )
        assert unbind_result.returncode == 0, "Failed to unbind device"
        
        time.sleep(0.5)
        
        # Verify device is unbound
        assert not os.path.exists(driver_link), f"Device {device_name} still bound after unbind"
        print("✓ Device successfully unbound")
        
        # Test bind operation  
        bind_result = subprocess.run(
            f"echo '{device_name}' | {SUDO}tee {bind_path}",
            shell=True, capture_output=True
        )
        assert bind_result.returncode == 0, "Failed to bind device"
        
        time.sleep(0.5)
        
        # Verify device is bound again
        assert os.path.exists(driver_link), f"Device {device_name} not bound after bind operation"
        print("✓ Device successfully rebound")
        
        # Verify sysfs attributes are still accessible after rebind
        sampling_ms_path = f"/sys/devices/platform/{device_name}/sampling_ms"
        assert os.path.exists(sampling_ms_path), "sysfs attributes not accessible after rebind"
        
        with open(sampling_ms_path, 'r') as f:
            value = f.read().strip()
            assert value == "1000", f"Unexpected sampling_ms value after rebind: {value}"
        
        print("✓ sysfs attributes working correctly after rebind")


@pytest.mark.order(26)
def test_driver_validation():
    """
    Master test function for driver validation - runs all validation tests
    
    This function is called by the test configuration system and orchestrates
    all the comprehensive driver validation tests in the proper sequence.
    """
    print("\n🚀 Starting Comprehensive Driver Validation Suite")
    print("=" * 60)
    
    # Create an instance of the test class
    test_instance = TestDriverValidation()
    
    try:
        # Run all validation tests in sequence
        test_instance.setup_method()
        print("\n1/5: Testing device and sysfs attributes...")
        test_instance.test_device_sysfs_attributes()
        test_instance.teardown_method()
        
        test_instance.setup_method()
        print("\n2/5: Testing module dependencies and loading...")
        test_instance.test_module_dependencies_and_loading()
        test_instance.teardown_method()
        
        test_instance.setup_method()
        print("\n3/5: Testing kernel logs verification...")
        test_instance.test_kernel_logs_verification()
        test_instance.teardown_method()
        
        test_instance.setup_method()
        print("\n4/5: Testing complete driver functionality...")
        test_instance.test_complete_driver_functionality()
        test_instance.teardown_method()
        
        test_instance.setup_method()
        print("\n5/5: Testing driver bind/unbind operations...")
        test_instance.test_driver_bind_unbind_operations()
        test_instance.teardown_method()
        
        print("\n" + "=" * 60)
        print("🎉 ALL DRIVER VALIDATION TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        # Ensure cleanup on failure
        test_instance.teardown_method()
        print(f"\n❌ Driver validation failed: {str(e)}")
        raise


if __name__ == "__main__":
    # Allow running individual tests
    import sys
    if len(sys.argv) > 1:
        pytest.main([__file__ + "::" + sys.argv[1], "-v"])
    else:
        pytest.main([__file__, "-v"])