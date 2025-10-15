#!/usr/bin/env python3

import subprocess
import re
import os
import pytest
from test_utils import SUDO, obj_path, SHELL_PARAMS

# Test Command:
# python3 -m pytest test_f_k8_tc_001.py::test_driver_load_unload


def test_driver_load_unload(capsys):
    """F-K8-TC-001: Load/unload kernel module without WARN/OOPS"""
    
    # Use the obj_path utility to get the module path
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    # Verify module file exists
    if not os.path.exists(module_path):
        pytest.fail(f"Module file not found: {module_path}")
    
    print(f"Testing module: {module_path}")
    
    # Verify module info before loading
    modinfo = subprocess.run(
        f"modinfo {module_path}", **SHELL_PARAMS
    )
    if modinfo.returncode != 0:
        pytest.fail(f"Module info check failed: {modinfo.stderr}")
    else:
        print(f"Module info verified:\n{modinfo.stdout}")
    
    # Ensure module is not already loaded (cleanup)
    cleanup_result = subprocess.run(
        f"{SUDO}rmmod nxp_simtemp", **SHELL_PARAMS
    )
    if cleanup_result.returncode == 0:
        print("Pre-existing module unloaded for clean test")
    
    # Load module
    load_result = subprocess.run(
        f"{SUDO}insmod {module_path}", **SHELL_PARAMS
    )
    if load_result.returncode != 0:
        pytest.fail(f"Module load failed: {load_result.stderr}")
    else:
        print("Module loaded successfully")
        
    # Verify module is loaded
    lsmod = subprocess.run(
        "lsmod | grep nxp_simtemp", **SHELL_PARAMS
    )
    if lsmod.returncode != 0:
        pytest.fail("Module not found in lsmod after loading")
    else:
        print(f"Module found in lsmod:\n{lsmod.stdout}")

    # Check dmesg for any immediate warnings after load
    dmesg_after_load = subprocess.run(
        f"{SUDO}dmesg | tail -n 10", **SHELL_PARAMS
    )
    if dmesg_after_load.returncode == 0:
        warn_pattern = r'\bWARN\b|\bOOPS\b|\bBUG\b|\bpanic\b'
        warnings = re.findall(
            warn_pattern, dmesg_after_load.stdout, re.IGNORECASE
        )
        if warnings:
            pytest.fail(f"Kernel warnings found after load: {warnings}")
    
    # Unload module
    unload_result = subprocess.run(
        f"{SUDO}rmmod nxp_simtemp", **SHELL_PARAMS
    )
    if unload_result.returncode != 0:
        pytest.fail(f"Module unload failed: {unload_result.stderr}")
    else:
        print("Module unloaded successfully")

    # Verify module is unloaded
    lsmod_after = subprocess.run(
        "lsmod | grep nxp_simtemp", **SHELL_PARAMS
    )
    if lsmod_after.returncode == 0:
        pytest.fail(
            f"Module still found in lsmod after unloading:\n"
            f"{lsmod_after.stdout}"
        )
    else:
        print("Module successfully removed from lsmod")

    # Final check for warnings/errors in dmesg
    dmesg_final = subprocess.run(
        f"{SUDO}dmesg | tail -n 15", **SHELL_PARAMS
    )
    if dmesg_final.returncode == 0:
        warn_pattern = r'\bWARN\b|\bOOPS\b|\bBUG\b|\bpanic\b'
        warnings = re.findall(warn_pattern, dmesg_final.stdout, re.IGNORECASE)
        if warnings:
            pytest.fail(f"Kernel warnings found after unload: {warnings}")
        else:
            print("No kernel warnings detected during load/unload cycle")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
