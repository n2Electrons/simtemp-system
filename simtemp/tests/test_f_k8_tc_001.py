#!/usr/bin/env python3

import subprocess
import re
import os
import pytest
from test_utils import SUDO, obj_path, SHELL_PARAMS
from test_f_k1_tc_001 import insmod_module, rmmod_module


def test_driver_load_unload(capsys):
    """F-K8-TC-001: Load/unload kernel module without WARN/OOPS"""
    
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    if not os.path.exists(module_path):
        pytest.fail(f"Module file not found: {module_path}")
    
    # Ensure module is loaded first
    insmod_module()
    
    # Test 1: rmmod with dmesg check
    subprocess.run(f"{SUDO}dmesg -C", **SHELL_PARAMS)  # Clear dmesg
    rmmod_module()
    
    # Check dmesg after rmmod
    dmesg_after_rmmod = subprocess.run(
        f"{SUDO}dmesg", **SHELL_PARAMS
    )
    if dmesg_after_rmmod.returncode == 0:
        warn_pattern = r'\bWARN\b|\bOOPS\b|\bBUG\b|\bpanic\b'
        warnings = re.findall(
            warn_pattern, dmesg_after_rmmod.stdout, re.IGNORECASE
        )
        if warnings:
            pytest.fail(f"Kernel warnings after rmmod: {warnings}")
    print("✓ rmmod: No warnings detected")
    
    # Test 2: insmod with dmesg check
    subprocess.run(f"{SUDO}dmesg -C", **SHELL_PARAMS)  # Clear dmesg
    insmod_module()
    
    # Check dmesg after insmod
    dmesg_after_insmod = subprocess.run(
        f"{SUDO}dmesg", **SHELL_PARAMS
    )
    if dmesg_after_insmod.returncode == 0:
        warn_pattern = r'\bWARN\b|\bOOPS\b|\bBUG\b|\bpanic\b'
        warnings = re.findall(
            warn_pattern, dmesg_after_insmod.stdout, re.IGNORECASE
        )
        if warnings:
            pytest.fail(f"Kernel warnings after insmod: {warnings}")
    print("✓ insmod: No warnings detected")
    
    print("✓ No kernel warnings detected during load/unload operations")

    # Keep driver loaded for subsequent tests


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
