"""
Test cases for kernel driver functionality on x86 host.
"""

import os
import pytest
import subprocess
from test_utils import obj_path

# Execute with:
# python3 -m pytest test_x86_f_k1_tc_001_insmod.py -v
# or
# python3 -m pytest test_x86_f_k1_tc_001_insmod.py -v -s

# Direct host functions for x86 testing (bypass QEMU)


def is_module_loaded_host(module_name="nxp_simtemp"):
    """Check if module is loaded on host using direct lsmod."""
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if result.returncode != 0:
            return False
        return any(line.startswith(module_name + ' ')
                   for line in result.stdout.split('\n'))
    except Exception:
        return False


def load_module_host(module_path):
    """Load module on host using direct insmod."""
    try:
        result = subprocess.run(['sudo', 'insmod', module_path],
                                capture_output=True, text=True)
        if result.returncode != 0:
            print(f"insmod failed with return code {result.returncode}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Exception during insmod: {e}")
        return False


def unload_module_host(module_name="nxp_simtemp"):
    """Unload module on host using direct rmmod."""
    try:
        result = subprocess.run(['sudo', 'rmmod', module_name],
                                capture_output=True, text=True)
        if result.returncode != 0 and result.returncode != 1:
            # Return code 1 is normal when module is not loaded
            print(f"rmmod failed with return code {result.returncode}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
        return True  # Consider rmmod successful even if module wasn't loaded
    except Exception as e:
        print(f"Exception during rmmod: {e}")
        return False


@pytest.mark.order(12)
def test_insmod_registers_driver(capsys: pytest.CaptureFixture[str]):
    """
    Test case F-K1-TC-001: Test lsmod, modinfo, insmod, rmmod on x86.
    Expected Result: All module operations work correctly.
    """
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    # Verify module file exists
    if not os.path.exists(module_path):
        pytest.fail(f"Module file not found: {module_path}")
    
    print(f"Testing module on x86 host: {module_path}")
    
    # Remove pre-existing module using direct host function
    unload_module_host()
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
    if not load_module_host(module_path):
        pytest.fail("insmod failed")
    print("✓ insmod: Module loaded successfully")
        
    # Test 3: lsmod - verify module is loaded
    if not is_module_loaded_host():
        pytest.fail("lsmod: Module not found after loading")
    print("✓ lsmod: Module found in loaded modules")
    
    # Test 4: rmmod - unload the module
    if not unload_module_host():
        pytest.fail("rmmod failed")
    print("✓ rmmod: Module unloaded successfully")
    
    # Verify module is unloaded
    if is_module_loaded_host():
        pytest.fail("Module still found after rmmod")
    print("✓ lsmod: Module correctly removed from loaded modules")
    
    # Keep module loaded for subsequent tests
    if not load_module_host(module_path):
        pytest.fail("Failed to reload module for subsequent tests")
    print("Module reloaded for next test cases")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
