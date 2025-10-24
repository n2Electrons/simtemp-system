#!/usr/bin/env python3

import os
import subprocess
import time
import pytest
from test_utils import obj_path, SUDO, SHELL_PARAMS


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
    
    # Check if modules are already loaded
    lsmod_result = subprocess.run(['lsmod'], capture_output=True, text=True)
    if lsmod_result.returncode != 0:
        print("Failed to check module status")
        return False
    
    output_lines = lsmod_result.stdout.split('\n')
    simtemp_loaded = any(line.startswith('nxp_simtemp ')
                         for line in output_lines)
    stub_loaded = any(line.startswith('nxp_simtemp_stub ')
                      for line in output_lines)
    
    if simtemp_loaded and stub_loaded:
        print("✓ Both modules already loaded")
        return True
    
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
    
    # Wait for device node creation
    time.sleep(0.5)
    print("✓ Both modules loaded successfully")
    return True


def test_device_node_exists():
    """F-K3-TC-001: Node exists"""
    
    stub_path = os.path.join(obj_path, "nxp_simtemp_stub.ko")
    main_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    if not os.path.exists(stub_path):
        pytest.fail(f"Stub module not found: {stub_path}")
    if not os.path.exists(main_path):
        pytest.fail(f"Main module not found: {main_path}")
    
    # Load modules
    if not load_simtemp_modules():
        pytest.fail("Failed to load simtemp modules")
    
    # Check device exists
    device_path = "/dev/simtemp0"
    assert os.path.exists(device_path), f"Device not found: {device_path}"
    
    print("✓ Device node exists")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])