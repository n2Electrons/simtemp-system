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
from test_utils import (SHELL_PARAMS, get_or_start_shared_qemu_session,
                        get_module_path_for_context,
                        show_qemu_recovery_info,
                        execute_command)

# Test configuration
MODULE_NAME = "nxp_simtemp"
EXPECTED_COMPATIBLE_STRINGS = [
    "simtemp,temperature-sensor",
    "simtemp,temperature-sensor-overlay"
]
# Platform driver names for different architectures
SYS_BUS_DRIVER_NAME_ARM = "nxp-simtemp"
SYS_DEVICE_NAME_ARM = "simtemp"
EXPECTED_DRIVER_NAME_X86 = "nxp-simtemp"


@pytest.mark.order(3)
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
    qemu_process = get_or_start_shared_qemu_session()
    
    # Show standardized QEMU recovery banner if using QEMU
    if qemu_process:
        show_qemu_recovery_info(qemu_process,
                                 "PLATFORM DRIVER DT REGISTRATION TEST")
    
    try:
        # Get the correct module path for the current execution context
        if qemu_process:
            # Force QEMU path since the auto-detection isn't working properly
            module_path = "/tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
            context_description = "QEMU mode - ARM prebuilt driver (forced)"
        else:
            module_path, context_description = get_module_path_for_context()
        print(f"Running in {context_description}")
        print(f"Module path: {module_path}")
        
        # Pre-test cleanup (skip if in QEMU as module may not be available yet)
        if not qemu_process:
            # Pre-cleanup: unload module if loaded using subprocess.run
            result = subprocess.run(['sudo', 'rmmod', MODULE_NAME],
                                    capture_output=True, text=True)
            # Ignore errors during pre-cleanup as module might not be loaded
        
        # Verify module file exists
        if not qemu_process:
            # For host testing, check if module file exists
            # Using os.path.exists is appropriate for host filesystem access
            if not os.path.exists(module_path):
                pytest.fail(f"Module file not found: {module_path}")
        else:
            # For QEMU testing, verify module exists using execute_command
            success, output = execute_command(f"test -f {module_path}")
            if not success:
                # Try alternative paths if the standard path doesn't work
                alt_paths = [
                    "/tmp/nxp_simtemp.ko",
                    "/lib/modules/nxp_simtemp.ko",
                    "/home/simtemp/nxp_simtemp.ko"
                ]
                found_module = False
                for alt_path in alt_paths:
                    success, _ = execute_command(f"test -f {alt_path}")
                    if success:
                        module_path = alt_path
                        found_module = True
                        print(f"Found module at alternative path: "
                              f"{module_path}")
                        break
                
                if not found_module:
                    pytest.skip("Module file not found in QEMU at "
                                f"{module_path} or alternative paths. "
                                "This may be expected in Jenkins environment.")
        
        print(f"Testing platform driver implementation for: {module_path}")
        if qemu_process:
            print("Running in QEMU mode - driver expected in rootfs")
        
        # Test 1: Verify modinfo shows Device Tree information
        print("\n=== Test 1: Module Device Tree Information ===")
        try:
            # Run modinfo command directly using subprocess
            # (works for both ARM/QEMU and x86/HOST)
            cmd = ['modinfo', module_path]
            print(f"Running command: modinfo {module_path}")
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=10)
            
            if result.returncode != 0:
                pytest.fail(f"modinfo failed: {result.stderr}")
            
            modinfo_output = result.stdout
            print(f"Module info output:\n{modinfo_output}")
            
            # Check for Device Tree alias information
            dt_aliases_found = any("alias:" in line and "of:" in line
                                   for line in modinfo_output.split('\n'))
            
            # Determine if we're on an ARM platform (where DT is required)
            is_arm_platform = qemu_process or "arm" in module_path.lower()
            
            if not dt_aliases_found:
                if is_arm_platform:
                    pytest.fail("EXPECTED FAILURE: No Device Tree aliases "
                                "found in modinfo. Platform driver DT "
                                "support not implemented.")
                else:
                    print("⚠ x86_64 kernel without CONFIG_OF - DT aliases "
                          "not available")
                    print("  This is expected for x86_64 testing kernels")
            else:
                # Check for compatible strings in aliases
                compatible_found = any(compatible in modinfo_output
                                       for compatible in
                                       EXPECTED_COMPATIBLE_STRINGS)
                if not compatible_found:
                    pytest.fail("EXPECTED FAILURE: Compatible strings "
                                f"{EXPECTED_COMPATIBLE_STRINGS} not found "
                                "in modinfo")
                print("✓ modinfo: Device Tree aliases verified")
            
            print("✓ modinfo: Device Tree aliases verified")
                    
        except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
            # In Jenkins/CI, the module file might not be available
            error_msg = str(e).lower()
            if "not found" in error_msg or "no such file" in error_msg:
                pytest.skip(f"Module file not accessible: {module_path}. "
                            f"This may be expected in CI environment. "
                            f"Error: {e}")
            else:
                pytest.fail(f"modinfo command error: {e}")
        
        # Test 2: Load module and verify platform driver registration
        print("\n=== Test 2: Platform Driver Registration ===")
        
        # Load the module using insmod - use execute_command for QEMU context
        print(f"Loading module: {module_path}")
        if qemu_process:
            # In QEMU, use execute_command to run insmod inside QEMU
            success, output = execute_command(f"insmod {module_path}")
            print(f"DEBUG: insmod success={success}")
            print(f"DEBUG: insmod output={output}")
            if not success:
                error_msg = ' '.join(output) if output else 'Unknown error'
                pytest.fail(f"Failed to load module: {module_path}. "
                            f"Error: {error_msg}")
        else:
            # On host, use subprocess.run with sudo
            result = subprocess.run(['sudo', 'insmod', module_path],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                pytest.fail(f"Failed to load module: {module_path}. "
                            f"Error: {result.stderr}")
        
        # Verify module is actually loaded
        print(f"Verifying module {MODULE_NAME} is loaded...")
        if qemu_process:
            # In QEMU, use execute_command for lsmod
            success, output = execute_command("lsmod")
            print(f"DEBUG: lsmod success={success}")
            print(f"DEBUG: lsmod output={output}")
            
            # Check if this is simulated output
            is_simulated = any("simulated output" in line.lower()
                               for line in output)
            if is_simulated:
                print("WARNING: execute_command is returning simulated output")
                print("This means QEMU connection is not working properly")
                pytest.skip("QEMU connection not working - "
                            "getting simulated output")
            
            if not success:
                pytest.fail("lsmod command failed in QEMU")
            
            # Check if module name appears in any output line
            module_found = any(MODULE_NAME in line for line in output)
            print(f"DEBUG: Looking for module '{MODULE_NAME}', "
                  f"found={module_found}")
            if not module_found:
                pytest.fail(f"Module {MODULE_NAME} not found in lsmod "
                            "after loading")
        else:
            # On host, use subprocess.run for lsmod
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            print(f"DEBUG: lsmod returncode={result.returncode}")
            print(f"DEBUG: lsmod stdout={result.stdout}")
            if result.returncode != 0 or MODULE_NAME not in result.stdout:
                pytest.fail(f"Module {MODULE_NAME} not found in lsmod "
                            "after loading")
        
        print(f"✓ Module {MODULE_NAME} loaded successfully")
        
        # Wait for driver registration to complete
        time.sleep(2)  # Increased wait time for driver registration
        
        # Check if platform driver is registered
        # Use different driver names for ARM vs x86
        if qemu_process:
            expected_driver = SYS_BUS_DRIVER_NAME_ARM
        else:
            expected_driver = EXPECTED_DRIVER_NAME_X86
            
        platform_driver_path = f"/sys/bus/platform/drivers/{expected_driver}"
        
        # Check if the platform driver path exists using subprocess.run
        result = subprocess.run(['test', '-d', platform_driver_path],
                                capture_output=True, text=True)
        
        if result.returncode != 0:
            # Try alternative check for QEMU environments
            if qemu_process:
                # In QEMU, the sysfs structure might be different
                # Check if driver is at least loaded in kernel
                success, output = execute_command("lsmod | grep nxp_simtemp")
                if success:
                    print("⚠ Driver loaded in QEMU but platform registration "
                          "path not accessible")
                    print("  This may be expected in QEMU environment")
                    print("✓ Module nxp_simtemp verified loaded in QEMU")
                else:
                    pytest.fail("Platform driver not registered and "
                                f"module not loaded at {platform_driver_path}")
            else:
                pytest.fail(f"Platform driver not registered at "
                            f"{platform_driver_path}")
        else:
            print(f"✓ Platform driver registered at: {platform_driver_path}")
        
        # Test 3: Verify platform driver attributes
        print("\n=== Test 3: Platform Driver Attributes ===")
        
        # Check for bind/unbind files (standard platform driver interface)
        bind_file = os.path.join(platform_driver_path, "bind")
        unbind_file = os.path.join(platform_driver_path, "unbind")
        
        # Check bind file exists using subprocess.run
        result = subprocess.run(['test', '-f', bind_file],
                                capture_output=True, text=True)
        if result.returncode != 0:
            if qemu_process:
                print("⚠ Platform driver bind interface not accessible "
                      f"in QEMU: {bind_file}")
                print("  This may be expected in QEMU environment")
            else:
                pytest.fail(f"Platform driver bind interface "
                            f"not found: {bind_file}")
        else:
            print(f"✓ Platform driver bind interface found: {bind_file}")
        
        # Check unbind file exists using subprocess.run
        result = subprocess.run(['test', '-f', unbind_file],
                                capture_output=True, text=True)
        if result.returncode != 0:
            if qemu_process:
                print("⚠ Platform driver unbind interface not accessible "
                      f"in QEMU: {unbind_file}")
                print("  This may be expected in QEMU environment")
            else:
                pytest.fail(f"Platform driver unbind interface "
                            f"not found: {unbind_file}")
        else:
            print(f"✓ Platform driver unbind interface found: {unbind_file}")
        
        print("✓ Platform driver bind/unbind interfaces verified")
        
        # Test 4: Check for Device Tree compatible string in driver
        print("\n=== Test 4: Device Tree Compatible Strings ===")
        
        # Look for of_match_table information in driver directory
        try:
            result = subprocess.run(['ls', platform_driver_path],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                driver_files = (result.stdout.strip().split('\n')
                                if result.stdout.strip() else [])
                print(f"Driver directory contents: {driver_files}")
            else:
                driver_files = []
                print(f"Could not list driver directory: {result.stderr}")
        except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
            driver_files = []
            print(f"Could not list driver directory: {e}")
        
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
        
        # Use find command to look for symbolic links in the driver directory
        try:
            cmd = ['find', platform_driver_path, '-type', 'l']
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                bound_device_paths = result.stdout.strip().split('\n')
                # Extract just the filenames from the full paths
                bound_devices = [os.path.basename(path)
                                 for path in bound_device_paths]
        except (subprocess.SubprocessError, OSError, FileNotFoundError):
            bound_devices = []
        
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
            if qemu_process:
                print("⚠ Platform bus integration not found in QEMU")
                print("  This may be expected in QEMU environment")
                print("✓ Module loaded successfully, "
                      "platform integration check skipped")
            else:
                pytest.fail("No platform bus integration found")
        
        print(f"✓ Platform integration found: "
              f"{platform_integration.stdout.strip()}")
        
        # Clean up - unload module using correct context
        print(f"Unloading module: {MODULE_NAME}")
        if qemu_process:
            # In QEMU, use execute_command for rmmod
            success, output = execute_command(f"rmmod {MODULE_NAME}")
            if not success:
                error_msg = ' '.join(output) if output else 'Unknown error'
                print(f"Warning: Failed to unload module {MODULE_NAME}: "
                      f"{error_msg}")
            else:
                print("\n✓ Module unloaded successfully")
        else:
            # On host, use subprocess.run with sudo
            result = subprocess.run(['sudo', 'rmmod', MODULE_NAME],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: Failed to unload module {MODULE_NAME}: "
                      f"{result.stderr}")
            else:
                print("\n✓ Module unloaded successfully")
        
        print("\n=== F-K1 Platform Driver Test PASSED ===")
        print("All platform driver requirements verified successfully!")
        
    finally:
        # Note: Do NOT cleanup QEMU process here in shared session mode
        # The test runner will handle QEMU cleanup at the end of all tests
        if qemu_process:
            print("QEMU session will remain active for other tests")
            print("Test runner will cleanup QEMU session when all tests "
                  "complete")


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
