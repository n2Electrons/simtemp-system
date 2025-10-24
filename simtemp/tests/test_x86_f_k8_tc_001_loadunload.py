#!/usr/bin/env python3

import subprocess
import re
import os
import time
import pytest
from test_utils import SUDO, obj_path, SHELL_PARAMS

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
    """Verify both modules state (stub and main driver)"""
    lsmod_result = subprocess.run(['lsmod'], capture_output=True, text=True)
    if lsmod_result.returncode != 0:
        return False
    
    output_lines = lsmod_result.stdout.split('\n')
    
    # Check for both modules
    simtemp_loaded = any(line.startswith('nxp_simtemp ')
                         for line in output_lines)
    stub_loaded = any(line.startswith('nxp_simtemp_stub ')
                      for line in output_lines)
    
    if should_be_loaded:
        # Both modules should be loaded
        return simtemp_loaded and stub_loaded
    else:
        # Both modules should be unloaded
        return not simtemp_loaded and not stub_loaded


def load_simtemp_modules():
    """Load simtemp modules (main driver first, then stub)"""
    stub_path = os.path.join(obj_path, "nxp_simtemp_stub.ko")
    main_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    # Verify both files exist
    if not os.path.exists(stub_path):
        print(f"Stub module not found: {stub_path}")
        return False
    if not os.path.exists(main_path):
        print(f"Main module not found: {main_path}")
        return False
    
    # Load main driver first
    print(f"Loading main module: {main_path}")
    main_result = subprocess.run(f"{SUDO}insmod {main_path}", **SHELL_PARAMS)
    if main_result.returncode != 0:
        print(f"Failed to load main module: {main_result.stderr}")
        return False
    
    # Then load stub
    print(f"Loading stub module: {stub_path}")
    stub_result = subprocess.run(f"{SUDO}insmod {stub_path}", **SHELL_PARAMS)
    if stub_result.returncode != 0:
        print(f"Failed to load stub module: {stub_result.stderr}")
        # Clean up main module if stub fails
        subprocess.run(f"{SUDO}rmmod nxp_simtemp", **SHELL_PARAMS)
        return False
    
    # Verify both modules are now loaded
    time.sleep(0.2)
    lsmod_result = subprocess.run(['lsmod'], capture_output=True, text=True)
    if lsmod_result.returncode != 0:
        return False
    
    output_lines = lsmod_result.stdout.split('\n')
    simtemp_loaded = any(line.startswith('nxp_simtemp ')
                         for line in output_lines)
    stub_loaded = any(line.startswith('nxp_simtemp_stub ')
                      for line in output_lines)
    
    if not (simtemp_loaded and stub_loaded):
        print("Error: Expected both modules to be loaded")
        print(f"  nxp_simtemp loaded: {simtemp_loaded}")
        print(f"  nxp_simtemp_stub loaded: {stub_loaded}")
        return False
    
    print("✓ Both modules loaded successfully")
    return True


def unload_simtemp_modules():
    """Unload both simtemp modules in correct order (main first, then stub)"""
    success = True
    
    # Unload main driver first
    main_result = subprocess.run(f"{SUDO}rmmod nxp_simtemp", **SHELL_PARAMS)
    if main_result.returncode != 0:
        print(f"Failed to unload main module: {main_result.stderr}")
        success = False
    
    # Then unload stub
    stub_cmd = f"{SUDO}rmmod nxp_simtemp_stub"
    stub_result = subprocess.run(stub_cmd, **SHELL_PARAMS)
    if stub_result.returncode != 0:
        print(f"Failed to unload stub module: {stub_result.stderr}")
        success = False
    
    return success


def test_driver_load_unload_clean_sequence(capsys):
    """F-K8-TC-001: Clean load/unload sequence"""
    
    stub_path = os.path.join(obj_path, "nxp_simtemp_stub.ko")
    main_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    # Check both modules exist
    if not os.path.exists(stub_path):
        pytest.fail(f"Stub module file not found: {stub_path}")
    if not os.path.exists(main_path):
        pytest.fail(f"Main module file not found: {main_path}")
    
    print("Testing clean load/unload:")
    print(f"  Stub: {stub_path}")
    print(f"  Main: {main_path}")
    
    # Clean start - unload any existing modules
    unload_simtemp_modules()
    time.sleep(0.5)
    
    # Test 3 cycles
    for cycle in range(3):
        print(f"\n--- Cycle {cycle + 1}/3 ---")
        
        # Load test
        clear_dmesg()
        print("Testing load...")
        load_result = load_simtemp_modules()
        if not load_result:
            pytest.fail(f"Load failed in cycle {cycle + 1}")
        
        # Verify loaded
        if not verify_module_state(should_be_loaded=True):
            msg = f"Modules not found after load in cycle {cycle + 1}"
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
        rm_result = unload_simtemp_modules()
        if not rm_result:
            pytest.fail(f"Unload failed in cycle {cycle + 1}")
        
        # Verify unloaded
        time.sleep(0.2)
        if not verify_module_state(should_be_loaded=False):
            msg = f"Modules still loaded after rmmod in cycle {cycle + 1}"
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
    load_simtemp_modules()
    if not verify_module_state(should_be_loaded=True):
        pytest.fail("Failed to reload")
    print("✓ Reloaded")


def test_driver_load_unload_stress(capsys):
    """F-K8-TC-001-STRESS: Stress test for load/unload"""
    
    stub_path = os.path.join(obj_path, "nxp_simtemp_stub.ko")
    main_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    if not os.path.exists(stub_path):
        pytest.skip(f"Stub module file not found: {stub_path}")
    if not os.path.exists(main_path):
        pytest.skip(f"Main module file not found: {main_path}")
    
    print("Running stress test...")
    
    # Clean start
    unload_simtemp_modules()
    time.sleep(0.5)
    
    # Clear dmesg
    clear_dmesg()
    
    # Rapid cycles
    for cycle in range(10):
        if cycle % 5 == 0:
            print(f"Stress cycle {cycle + 1}/10")
        
        # Load
        if not load_simtemp_modules():
            pytest.fail(f"Load failed in stress cycle {cycle + 1}")
        
        time.sleep(0.1)
        
        # Unload
        if not unload_simtemp_modules():
            pytest.fail(f"Unload failed in stress cycle {cycle + 1}")
        
        time.sleep(0.1)
    
    # Check for warnings
    warnings = get_dmesg_warnings()
    if warnings:
        pytest.fail(f"Warnings during stress test: {warnings}")
    
    print("✓ Stress test completed")
    print("✓ No warnings in rapid cycles")
    
    # Reload
    load_simtemp_modules()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
