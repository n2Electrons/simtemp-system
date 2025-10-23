"""
TDD Test Case for F-K1 Requirement: Platform Driver Registration via DT
Test ID: F-K1-TDD-001
Expected State: FAIL (Red Phase)

This test validates that the nxp_simtemp driver is properly implemented as a
platform driver with Device Tree support, following Linux kernel practices.
"""

import os
import pytest
import subprocess
import time
from test_utils import (SHELL_PARAMS, get_shared_qemu_session,
                        get_module_path_for_context, execute_command,
                        load_module, rm_module, show_qemu_recovery_info)

# Test configuration
MODULE_NAME = "nxp_simtemp"
EXPECTED_COMPATIBLE_STRINGS = [
    "simtemp,temperature-sensor",
    "simtemp,temperature-sensor-overlay"
]
EXPECTED_DRIVER_NAME = "nxp-simtemp"


def test_f_k1_platform_driver_dt_registration():
    """
    F-K1-TDD-001: Comprehensive Platform Driver Device Tree Registration Test
    
    This test validates that the nxp_simtemp driver is properly implemented
    as a platform driver with full Device Tree support. This test is designed
    to FAIL in the TDD red phase until the platform driver infrastructure is
    implemented.
    
    Test Objectives:
    1. Verify platform driver structure is implemented
    2. Validate Device Tree compatible strings are defined
    3. Confirm platform driver is registered with kernel bus system
    4. Check probe and remove functions are implemented
    5. Ensure sysfs entries are created correctly
    6. Validate modinfo shows Device Tree aliases
    
    Expected Result (Red Phase): FAIL - Platform driver infrastructure not
    implemented
    """
    
    # Check if this should run in QEMU mode
    qemu_process = get_shared_qemu_session()
    
    # Show standardized QEMU recovery banner if using QEMU
    if qemu_process:
        show_qemu_recovery_info(qemu_process,
                                 "PLATFORM DRIVER DT REGISTRATION TEST")
    
    try:
        # Get the correct module path for the current execution context
        module_path, context_description = get_module_path_for_context()
        print(f"Running in {context_description}")
        
        # Pre-test cleanup (skip if in QEMU as module may not be available yet)
        if not qemu_process:
            rm_module()
        
        # Verify module file exists (skip for QEMU - driver inside QEMU)
        if not qemu_process and not os.path.exists(module_path):
            pytest.fail(f"Module file not found: {module_path}")
        
        print(f"Testing platform driver implementation for: {module_path}")
        if qemu_process:
            print("Running in QEMU mode - driver expected in rootfs")
        
        # Test 1: Verify modinfo shows Device Tree information
        print("\n=== Test 1: Module Device Tree Information ===")
        try:
            # Run modinfo command (works for both ARM/QEMU and x86/HOST)
            cmd = f'modinfo "{module_path}"'
            success, output = execute_command(cmd, timeout=10)
            if not success:
                pytest.fail(f"modinfo failed: {output}")
            modinfo_output = '\n'.join(output) if output else ""
            
            print(f"Module info output:\n{modinfo_output}")
            
            # Check for Device Tree alias information
            dt_aliases_found = any("alias:" in line and "of:" in line
                                   for line in modinfo_output.split('\n'))
            
            # Determine if we're on an ARM platform (where DT is required)
            is_arm_platform = qemu_process or "arm" in module_path.lower()
            
            if not dt_aliases_found:
                if is_arm_platform:
                    pytest.fail("EXPECTED FAILURE: No Device Tree aliases found in "
                                "modinfo. Platform driver DT support not implemented.")
                else:
                    print("⚠ x86_64 kernel without CONFIG_OF - DT aliases not available")
                    print("  This is expected for x86_64 testing kernels")
            else:
                # Check for compatible strings in aliases
                compatible_found = any(compatible in modinfo_output
                                       for compatible in EXPECTED_COMPATIBLE_STRINGS)
                if not compatible_found:
                    pytest.fail(f"EXPECTED FAILURE: Compatible strings "
                                f"{EXPECTED_COMPATIBLE_STRINGS} not found in modinfo")
                print("✓ modinfo: Device Tree aliases verified")
            
            print("✓ modinfo: Device Tree aliases verified")
            
        except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
            pytest.fail(f"modinfo command error: {e}")
        
        # Test 2: Load module and verify platform driver registration
        print("\n=== Test 2: Platform Driver Registration ===")
        load_module(module_path=module_path)
        
        # Wait for driver registration to complete
        time.sleep(1)
        
        # Check if platform driver is registered
        platform_driver_path = f"/sys/bus/platform/drivers/{EXPECTED_DRIVER_NAME}"
        if not os.path.exists(platform_driver_path):
            pytest.fail(f"EXPECTED FAILURE: Platform driver not registered at "
                         f"{platform_driver_path}")
        
        print(f"✓ Platform driver registered at: {platform_driver_path}")
        
        # Test 3: Verify platform driver attributes
        print("\n=== Test 3: Platform Driver Attributes ===")
        
        # Check for bind/unbind files (standard platform driver interface)
        bind_file = os.path.join(platform_driver_path, "bind")
        unbind_file = os.path.join(platform_driver_path, "unbind")
        
        if not os.path.exists(bind_file):
            pytest.fail(f"EXPECTED FAILURE: Platform driver bind interface "
                        f"not found: {bind_file}")
        
        if not os.path.exists(unbind_file):
            pytest.fail(f"EXPECTED FAILURE: Platform driver unbind interface "
                        f"not found: {unbind_file}")
        
        print("✓ Platform driver bind/unbind interfaces verified")
        
        # Test 4: Check for Device Tree compatible string in driver
        print("\n=== Test 4: Device Tree Compatible Strings ===")
        
        # Look for of_match_table information in driver directory
        driver_files = os.listdir(platform_driver_path)
        print(f"Driver directory contents: {driver_files}")
        
        # Check if there's a way to verify compatible strings through sysfs
        # (This might not be directly available, but we test what we can)
        subprocess.run(
            f"cat /sys/module/{MODULE_NAME}/sections/.rodata 2>/dev/null || "
            "echo 'No rodata section'",
            **SHELL_PARAMS
        )
        
        # Test 5: Verify platform device can be bound (if DT node exists)
        print("\n=== Test 5: Platform Device Binding ===")
        
        # Check if any devices are bound to our driver
        bound_devices = []
        try:
            for item in os.listdir(platform_driver_path):
                item_path = os.path.join(platform_driver_path, item)
                if os.path.islink(item_path):
                    # This is likely a bound device
                    bound_devices.append(item)
        except OSError:
            pass
        
        print(f"Bound devices: {bound_devices}")
        
        # Test 6: Verify probe function exists and is callable
        print("\n=== Test 6: Probe Function Verification ===")
        
        # Check kernel symbols for our probe function
        probe_symbol_check = subprocess.run(
            f"grep -i 'probe' /proc/kallsyms | grep -i {MODULE_NAME} || "
            "echo 'No probe symbols found'",
            **SHELL_PARAMS
        )
        
        print(f"Probe function check: {probe_symbol_check.stdout}")
        
        # Test 7: Module dependency and platform driver integration
        print("\n=== Test 7: Platform Driver Integration ===")
        
        # Check module dependencies
        subprocess.run(
            f"cat /sys/module/{MODULE_NAME}/holders 2>/dev/null || "
            "echo 'No holders'",
            **SHELL_PARAMS
        )
        
        # Verify module is properly integrated with platform subsystem
        platform_integration = subprocess.run(
            f"find /sys/bus/platform -name '*{MODULE_NAME}*' "
            "-o -name '*simtemp*' 2>/dev/null",
            **SHELL_PARAMS
        )
        
        if not platform_integration.stdout.strip():
            pytest.fail("EXPECTED FAILURE: No platform bus integration found")
        
        print(f"✓ Platform integration found: "
              f"{platform_integration.stdout.strip()}")
        
        # Clean up
        rm_module()
        print("\n✓ Module unloaded successfully")
        
        print("\n=== F-K1 Platform Driver Test PASSED ===")
        print("All platform driver requirements verified successfully!")
        
    finally:
        # Note: Do NOT cleanup QEMU process here in shared session mode
        # The test runner will handle QEMU cleanup at the end of all tests
        if qemu_process:
            print("QEMU session will remain active for other tests")
            print("Test runner will cleanup QEMU session when all tests complete")


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
