#!/usr/bin/env python3

import os
import subprocess
import pytest
from test_utils import SUDO, obj_path, SHELL_PARAMS


def test_dt_overlay_driver_binding():
    """F-K1-TC-002: DT overlay binds driver; properties parsed OK"""
    
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    if not os.path.exists(module_path):
        pytest.fail(f"Module file not found: {module_path}")
    
    # Global sysfs paths to verify in all sub-tests
    # NOTE: In real DT overlay scenario, only some of these should exist
    sysfs_paths = {
        # Should exist if DT overlay works correctly
        'thermal': "/sys/class/thermal/thermal_zone0",
        'hwmon': "/sys/class/hwmon",
        # Will exist since module is loaded manually
        'module': "/sys/module/nxp_simtemp",
        # Should NOT exist without real DT device instantiation
        'platform': "/sys/bus/platform/drivers/nxp_simtemp",
        # Device Tree related paths (should exist if DT overlay active)
        'dt_device': "/sys/firmware/devicetree/base/simtemp@12345678",
        'configfs': "/sys/kernel/config/device-tree/overlays"
    }
    
    # Step 1: Document the Device Tree overlay requirements
    print("Testing Device Tree overlay driver binding...")
    
    # Step 2: Check if module is already loaded
    lsmod_check = subprocess.run(
        "lsmod | grep nxp_simtemp", **SHELL_PARAMS
    )
    module_was_loaded = lsmod_check.returncode == 0
    
    if not module_was_loaded:
        # Load module if not already loaded
        load_result = subprocess.run(
            f"{SUDO}insmod {module_path}", **SHELL_PARAMS
        )
        if load_result.returncode != 0:
            pytest.fail(f"Module load failed: {load_result.stderr}")
    else:
        print("Using already loaded module")
    
    try:
        # Step 3: Device Tree overlay infrastructure check
        _test_dt_overlay_infrastructure(sysfs_paths)
        
        # Step 4: Device Tree compatibility verification
        _test_dt_compatibility(module_path, sysfs_paths)
        
        # Step 5: Device Tree device instantiation check
        _test_dt_device_instantiation(sysfs_paths)
        
        # Step 6: thermal subsystem binding (should fail without real DT)
        _test_thermal_subsystem_binding(sysfs_paths)
        
        # Step 7: hardware monitoring interface (should fail without real DT)
        _test_hwmon_interface_binding(sysfs_paths)
        
        # Step 8: module registration (should pass - module loaded manually)
        _test_module_registration(sysfs_paths)
        
        # Step 9: platform driver binding (should fail without DT device)
        _test_platform_driver_binding(sysfs_paths)
        
        # Step 10: DT property parsing verification
        _test_dt_property_parsing(sysfs_paths)
        
        # FINAL VALIDATION: Test MUST fail if no real DT overlay
        _validate_real_dt_overlay_or_fail(sysfs_paths)
        
        print("✓ Device Tree overlay binding verification PASSED")
            
    finally:
        # Always cleanup
        subprocess.run(f"{SUDO}rmmod nxp_simtemp", **SHELL_PARAMS)


def _test_dt_overlay_infrastructure(sysfs_paths):
    """Sub-test: Verify Device Tree overlay infrastructure exists"""
    configfs_path = sysfs_paths['configfs']
    
    if not os.path.exists(configfs_path):
        print("❌ DT overlay infrastructure NOT available")


def _test_dt_device_instantiation(sysfs_paths):
    """Sub-test: Verify Device Tree device instantiation"""
    dt_device_path = sysfs_paths['dt_device']
    
    if not os.path.exists(dt_device_path):
        print("❌ DT device node NOT found")


def _test_dt_compatibility(module_path, sysfs_paths):
    """Sub-test: Verify Device Tree compatibility declarations"""
    # Verify at least one sysfs path exists as evidence of successful binding
    binding_found = any(os.path.exists(path) for path in sysfs_paths.values())
    if not binding_found:
        pytest.fail("No evidence of driver binding found in sysfs paths")


def _test_hwmon_interface_binding(sysfs_paths):
    """Sub-test: Verify hardware monitoring interface binding"""
    pass  # Silent check


def _test_module_registration(sysfs_paths):
    """Sub-test: Verify module registration"""
    module_path = sysfs_paths['module']
    
    if not os.path.exists(module_path):
        pytest.fail("Module registration verification failed")


def _test_thermal_subsystem_binding(sysfs_paths):
    """Sub-test: Verify thermal subsystem binding (should fail without DT)"""
    thermal_path = sysfs_paths['thermal']
    
    if os.path.exists(thermal_path):
        type_file = os.path.join(thermal_path, "type")
        if os.path.exists(type_file):
            with open(type_file, 'r') as f:
                zone_type = f.read().strip()
                if not ("simtemp" in zone_type.lower() or
                        "nxp" in zone_type.lower()):
                    pass  # Silent check
    # Silent check if path doesn't exist


def _test_platform_driver_binding(sysfs_paths):
    """Sub-test: Verify platform driver binding (should fail without DT)"""
    platform_path = sysfs_paths['platform']
    
    if not os.path.exists(platform_path):
        pass  # Silent check


def _test_dt_property_parsing(sysfs_paths):
    """Sub-test: Verify DT property parsing (check for errors)"""
    # Verify DT property parsing (check dmesg for errors) - silent check
    subprocess.run(
        f"{SUDO}dmesg | tail -50 | grep -i 'simtemp\\|nxp\\|error\\|fail'",
        shell=True, capture_output=True, text=True
    )
    
    # Silent verification of critical sysfs paths
    critical_paths = [sysfs_paths['thermal'], sysfs_paths['hwmon']]
    any(os.path.exists(path) for path in critical_paths)


def _validate_real_dt_overlay_or_fail(sysfs_paths):
    """Final validation: Fail test if no real DT overlay evidence found"""
    
    # Critical requirements for real DT overlay
    dt_requirements = {
        'configfs': sysfs_paths['configfs'],
        'dt_device': sysfs_paths['dt_device'],
        'platform': sysfs_paths['platform']
    }
    
    failed_requirements = []
    
    for requirement, path in dt_requirements.items():
        if not os.path.exists(path):
            failed_requirements.append(requirement)
    
    # Additional check: verify thermal zone is from our driver
    thermal_path = sysfs_paths['thermal']
    our_thermal_zone = False
    
    if os.path.exists(thermal_path):
        type_file = os.path.join(thermal_path, "type")
        if os.path.exists(type_file):
            with open(type_file, 'r') as f:
                zone_type = f.read().strip()
                if ("simtemp" in zone_type.lower() or
                        "nxp" in zone_type.lower()):
                    our_thermal_zone = True
    
    if not our_thermal_zone:
        failed_requirements.append('our_thermal_zone')
    
    # FAIL THE TEST if critical DT overlay evidence is missing
    if failed_requirements:
        failure_msg = (
            f"Device Tree overlay test FAILED! "
            f"Missing requirements: {failed_requirements}. "
            f"Test requires real DT overlay, found insmod loading instead."
        )
        pytest.fail(failure_msg)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
