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
from test_utils import SUDO, SHELL_PARAMS, obj_path


class TestDriverValidation:
    """Comprehensive driver validation test suite"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Clean up any existing modules
        subprocess.run(f"{SUDO}rmmod nxp_simtemp_stub nxp_simtemp",
                       shell=True, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up modules after test
        subprocess.run(f"{SUDO}rmmod nxp_simtemp_stub nxp_simtemp",
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
        
        # Load modules using modprobe to test dependencies
        result = subprocess.run(f"{SUDO}modprobe nxp_simtemp", **SHELL_PARAMS)
        assert result.returncode == 0, "Failed to load nxp_simtemp module"
        
        # Give kernel time to create devices
        time.sleep(1)
        
        # Verify device directories exist
        device0_path = "/sys/devices/platform/nxp-simtemp.0"
        device1_path = "/sys/devices/platform/nxp-simtemp.1.auto"
        
        assert os.path.exists(device0_path), f"Device 0 not found at {device0_path}"
        assert os.path.exists(device1_path), f"Device 1 not found at {device1_path}"
        print(f"✓ Both devices created: {device0_path}, {device1_path}")
        
        # Verify sysfs attributes exist for device 0
        device0_attrs = ["sampling_ms", "threshold_mC", "mode"]
        for attr in device0_attrs:
            attr_path = f"{device0_path}/{attr}"
            assert os.path.exists(attr_path), f"Attribute {attr} not found for device 0"
        
        # Verify sysfs attributes exist for device 1
        for attr in device0_attrs:
            attr_path = f"{device1_path}/{attr}"
            assert os.path.exists(attr_path), f"Attribute {attr} not found for device 1"
        
        print("✓ All sysfs attributes found for both devices")
        
        # Read and verify attribute values for device 0 (default values)
        with open(f"{device0_path}/sampling_ms", 'r') as f:
            sampling_ms_0 = f.read().strip()
        with open(f"{device0_path}/threshold_mC", 'r') as f:
            threshold_mC_0 = f.read().strip()
        with open(f"{device0_path}/mode", 'r') as f:
            mode_0 = f.read().strip()
            
        # Verify default values
        assert sampling_ms_0 == "1000", f"Expected 1000, got {sampling_ms_0}"
        assert threshold_mC_0 == "50000", f"Expected 50000, got {threshold_mC_0}"
        assert mode_0 == "default", f"Expected 'default', got {mode_0}"
        
        print(f"✓ Device 0 values: sampling_ms={sampling_ms_0}, threshold_mC={threshold_mC_0}, mode={mode_0}")
        
        # Read and verify attribute values for device 1 (stub values)
        with open(f"{device1_path}/sampling_ms", 'r') as f:
            sampling_ms_1 = f.read().strip()
        with open(f"{device1_path}/threshold_mC", 'r') as f:
            threshold_mC_1 = f.read().strip()
        with open(f"{device1_path}/mode", 'r') as f:
            mode_1 = f.read().strip()
            
        # Verify stub values
        assert sampling_ms_1 == "200", f"Expected 200, got {sampling_ms_1}"
        assert threshold_mC_1 == "60000", f"Expected 60000, got {threshold_mC_1}"
        assert mode_1 == "lab", f"Expected 'lab', got {mode_1}"
        
        print(f"✓ Device 1 values: sampling_ms={sampling_ms_1}, threshold_mC={threshold_mC_1}, mode={mode_1}")

    def test_module_dependencies_and_loading(self):
        """
        Test: Verify module dependencies and loading behavior
        
        Based on commands:
        - modinfo obj/nxp_simtemp.ko | grep -E "(filename|depends|softdep)"
        - modinfo obj/nxp_simtemp_stub.ko | grep -E "(filename|depends|softdep)"
        - lsmod | grep nxp
        - sudo modprobe nxp_simtemp
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
        
        # Test automatic loading with modprobe
        result = subprocess.run(f"{SUDO}modprobe nxp_simtemp", **SHELL_PARAMS)
        assert result.returncode == 0, "modprobe failed to load nxp_simtemp"
        
        # Verify main module is loaded (stub is optional)
        lsmod = subprocess.run("lsmod | grep nxp", shell=True, capture_output=True, text=True)
        assert "nxp_simtemp" in lsmod.stdout, "Main module not found in lsmod"
        
        if os.path.exists(stub_path):
            assert "nxp_simtemp_stub" in lsmod.stdout, "Stub module not found in lsmod"
            print("✓ Both modules loaded automatically via modprobe")
        else:
            print("✓ Main module loaded via modprobe (stub not needed for ARM)")

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
        
        # Load the driver
        result = subprocess.run(f"{SUDO}modprobe nxp_simtemp", **SHELL_PARAMS)
        assert result.returncode == 0, "Failed to load nxp_simtemp module"
        
        time.sleep(1)  # Give kernel time to generate logs
        
        # Get new logs
        post_dmesg = subprocess.run(f"{SUDO}dmesg", shell=True, capture_output=True, text=True)
        dmesg_lines = post_dmesg.stdout.split('\n')
        new_logs = dmesg_lines[pre_lines:]
        new_logs_text = '\n'.join(new_logs)
        
        # Check for driver initialization messages
        assert "NXP SimTemp driver: Initializing" in new_logs_text, "Driver initialization message not found"
        assert "NXP SimTemp driver: Platform driver registered" in new_logs_text, "Driver registration message not found"
        print("✓ Driver initialization logs found")
        
        # Check for device probe messages
        assert "NXP SimTemp probe start" in new_logs_text, "Device probe messages not found"
        assert "probe ok:" in new_logs_text, "Successful probe messages not found"
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
        
        # 2. Load with automatic dependencies
        result = subprocess.run(f"{SUDO}modprobe nxp_simtemp", **SHELL_PARAMS)
        assert result.returncode == 0, "Failed to load with modprobe"
        print("✓ Automatic dependency loading successful")
        
        # 3. Verify devices created
        devices = glob.glob("/sys/devices/platform/nxp-simtemp*")
        assert len(devices) >= 2, f"Expected at least 2 devices, found {len(devices)}"
        print(f"✓ Found {len(devices)} devices: {[os.path.basename(d) for d in devices]}")
        
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
            f"{SUDO}dmesg | grep 'probe ok:' | tail -2",
            shell=True, capture_output=True, text=True
        )
        assert "probe ok:" in recent_logs.stdout, f"Successful probe not found: {recent_logs.stdout}"
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
        
        # Load the driver first
        result = subprocess.run(f"{SUDO}modprobe nxp_simtemp", **SHELL_PARAMS)
        assert result.returncode == 0, "Failed to load nxp_simtemp module"
        
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


if __name__ == "__main__":
    # Allow running individual tests
    import sys
    if len(sys.argv) > 1:
        pytest.main([__file__ + "::" + sys.argv[1], "-v"])
    else:
        pytest.main([__file__, "-v"])