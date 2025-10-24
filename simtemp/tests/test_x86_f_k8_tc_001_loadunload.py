#!/usr/bin/env python3

import subprocess
import re
import os
import time
import pytest
from test_utils import (SUDO, obj_path, SHELL_PARAMS, load_module,
                        rm_module)

# Execute with:
# python3 -m pytest test_x86_f_k8_tc_001_loadunload.py -v
# or
# python3 -m pytest test_x86_f_k8_tc_001_loadunload.py -v -s


def clear_dmesg():
    """Clear dmesg buffer"""
    subprocess.run(f"{SUDO}dmesg -C", **SHELL_PARAMS)


def get_dmesg_warnings():
    """Get kernel warnings from dmesg"""
    dmesg_result = subprocess.run(f"{SUDO}dmesg", **SHELL_PARAMS)
    if dmesg_result.returncode != 0:
        return []
    
    # Pattern for warnings
    warn_pattern = (r'\bWARN\b|\bOOPS\b|\bBUG\b|\bpanic\b|'
                    r'\bkernel BUG\b|\bCall Trace\b|\bstack trace\b|\bRIP:\b')
    warnings = re.findall(warn_pattern, dmesg_result.stdout, re.IGNORECASE)
    return warnings


def verify_module_state(should_be_loaded=True):
    """Verify module state"""
    lsmod_result = subprocess.run(['lsmod'], capture_output=True, text=True)
    if lsmod_result.returncode != 0:
        return False
    
    is_loaded = any(line.startswith('nxp_simtemp ')
                    for line in lsmod_result.stdout.split('\n'))
    return is_loaded == should_be_loaded


def test_driver_load_unload_clean_sequence(capsys):
    """F-K8-TC-001: Clean load/unload sequence"""
    
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    if not os.path.exists(module_path):
        pytest.fail(f"Module file not found: {module_path}")
    
    print(f"Testing clean load/unload: {module_path}")
    
    # Clean start
    rm_module()
    time.sleep(0.5)
    
    # Test 3 cycles
    for cycle in range(3):
        print(f"\n--- Cycle {cycle + 1}/3 ---")
        
        # Load test
        clear_dmesg()
        print("Testing load...")
        load_result = load_module()
        if not load_result:
            pytest.fail(f"Load failed in cycle {cycle + 1}")
        
        # Verify loaded
        if not verify_module_state(should_be_loaded=True):
            msg = f"Module not found after load in cycle {cycle + 1}"
            pytest.fail(msg)
        
        # Check warnings after load
        time.sleep(0.2)
        warnings = get_dmesg_warnings()
        if warnings:
            msg = f"Kernel warnings after load in cycle {cycle + 1}: "
            msg += f"{warnings}"
            pytest.fail(msg)
        print("✓ Load: No warnings")
        
        # Unload test
        clear_dmesg()
        print("Testing unload...")
        rm_result = rm_module()
        if not rm_result:
            pytest.fail(f"Unload failed in cycle {cycle + 1}")
        
        # Verify unloaded
        time.sleep(0.2)
        if not verify_module_state(should_be_loaded=False):
            msg = f"Module still loaded after rmmod in cycle {cycle + 1}"
            pytest.fail(msg)
        
        # Check warnings after unload
        warnings = get_dmesg_warnings()
        if warnings:
            msg = f"Kernel warnings after unload in cycle {cycle + 1}: "
            msg += f"{warnings}"
            pytest.fail(msg)
        print("✓ Unload: No warnings")
        
        time.sleep(0.5)
    
    print("\n✓ All cycles completed")
    print("✓ No warnings detected")
    print("✓ Clean lifecycle verified")
    
    # Reload for next tests
    print("\nReloading for next tests...")
    load_module()
    if not verify_module_state(should_be_loaded=True):
        pytest.fail("Failed to reload")
    print("✓ Reloaded")


def test_driver_load_unload_stress(capsys):
    """F-K8-TC-001-STRESS: Stress test for load/unload"""
    
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    if not os.path.exists(module_path):
        pytest.skip(f"Module file not found: {module_path}")
    
    print("Running stress test...")
    
    # Clean start
    rm_module()
    time.sleep(0.5)
    
    # Clear dmesg
    clear_dmesg()
    
    # Rapid cycles
    for cycle in range(10):
        if cycle % 5 == 0:
            print(f"Stress cycle {cycle + 1}/10")
        
        # Load
        if not load_module():
            pytest.fail(f"Load failed in stress cycle {cycle + 1}")
        
        time.sleep(0.1)
        
        # Unload
        if not rm_module():
            pytest.fail(f"Unload failed in stress cycle {cycle + 1}")
        
        time.sleep(0.1)
    
    # Check for warnings
    warnings = get_dmesg_warnings()
    if warnings:
        pytest.fail(f"Warnings during stress test: {warnings}")
    
    print("✓ Stress test completed")
    print("✓ No warnings in rapid cycles")
    
    # Reload
    load_module()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
