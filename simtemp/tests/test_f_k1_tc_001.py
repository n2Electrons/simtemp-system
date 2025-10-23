"""
Test cases for kernel driver functionality.
"""

import os
import pytest
import subprocess
from test_utils import obj_path, is_module_loaded, load_module, rmmod_module

# Execute with:
# python3 -m pytest test_f_k1_tc_001.py -v
# or
# python3 -m pytest test_f_k1_tc_001.py -v -s

# Module management functions are now centralized in test_utils


def test_insmod_registers_driver(capsys: pytest.CaptureFixture[str]):
    """
    Test case F-K1-TC-001: Test lsmod, modinfo, insmod, rmmod operations.
    Expected Result: All module operations work correctly.
    """
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    # Verify module file exists
    if not os.path.exists(module_path):
        pytest.fail(f"Module file not found: {module_path}")
    
    print(f"Testing module: {module_path}")
    
    # Remove pre-existing module using centralized function
    rmmod_module()
    print("Pre-existing module removed")
    
    # Test 1: modinfo - verify module information
    try:
        modinfo = subprocess.run(
            ['modinfo', module_path], capture_output=True,
            text=True, timeout=10
        )
        if modinfo.returncode != 0:
            pytest.fail(f"modinfo failed: {modinfo.stderr}")
        print("✓ modinfo: Module information verified")
    except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
        pytest.fail(f"modinfo command error: {e}")
    
    # Test 2: insmod - load the module
    if not load_module():
        pytest.fail("insmod failed")
    print("✓ insmod: Module loaded successfully")
        
    # Test 3: lsmod - verify module is loaded
    if not is_module_loaded():
        pytest.fail("lsmod: Module not found after loading")
    print("✓ lsmod: Module found in loaded modules")
    
    # Test 4: rmmod - unload the module
    if not rmmod_module():
        pytest.fail("rmmod failed")
    print("✓ rmmod: Module unloaded successfully")
    
    # Verify module is unloaded
    if is_module_loaded():
        pytest.fail("Module still found after rmmod")
    print("✓ lsmod: Module correctly removed from loaded modules")
    
    # Keep module loaded for subsequent tests
    if not load_module():
        pytest.fail("Failed to reload module for subsequent tests")
    print("Module reloaded for next test cases")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
