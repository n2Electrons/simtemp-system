"""
Test cases for kernel driver functionality.
"""

import os
import pytest
import subprocess
from test_utils import SUDO, obj_path, SHELL_PARAMS

# Execute with:
# python3 -m pytest test_f_k1_tc_001.py -v
# or
# python3 -m pytest test_f_k1_tc_001.py -v -s

# SUDO: Prefix for commands requiring elevated privileges (e.g., insmod/rmmod)
# Will be "sudo " if sudo is available, empty string if running as root


def is_module_loaded():
    """Check if nxp_simtemp module is currently loaded"""
    result = subprocess.run("lsmod | grep nxp_simtemp", **SHELL_PARAMS)
    return result.returncode == 0


def insmod_module():
    """Load the nxp_simtemp kernel module"""
    if is_module_loaded():
        return  # Module already loaded
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    result = subprocess.run(f"{SUDO}insmod {module_path}", **SHELL_PARAMS)
    if result.returncode != 0:
        pytest.fail(f"insmod failed: {result.stderr}")
    return result


def rmmod_module():
    """Unload the nxp_simtemp kernel module using modprobe -r for
    proper dependency handling"""
    if not is_module_loaded():
        return  # Module not loaded
    
    # Use modprobe -r on x86 for better dependency handling
    # This will automatically handle the nxp_simtemp_stub dependency
    import platform
    if platform.machine() in ['x86_64', 'i386', 'i686']:
        result = subprocess.run(f"{SUDO}modprobe -r nxp_simtemp",
                                **SHELL_PARAMS)
    else:
        # Use rmmod on non-x86 platforms (like ARM in QEMU)
        result = subprocess.run(f"{SUDO}rmmod nxp_simtemp", **SHELL_PARAMS)
    
    if result.returncode != 0:
        pytest.fail(f"Module removal failed: {result.stderr}")
    return result


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
    
    # Remove pre-existing module using same logic as rmmod_module()
    import platform
    if platform.machine() in ['x86_64', 'i386', 'i686']:
        subprocess.run(f"{SUDO}modprobe -r nxp_simtemp", **SHELL_PARAMS)
    else:
        subprocess.run(f"{SUDO}rmmod nxp_simtemp", **SHELL_PARAMS)
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
    insmod_module()
    print("✓ insmod: Module loaded successfully")
        
    # Test 3: lsmod - verify module is loaded
    lsmod = subprocess.run(
        "lsmod | grep nxp_simtemp", **SHELL_PARAMS
    )
    if lsmod.returncode != 0:
        pytest.fail("lsmod: Module not found after loading")
    print("✓ lsmod: Module found in loaded modules")
    
    # Test 4: rmmod - unload the module
    rmmod_module()
    print("✓ rmmod: Module unloaded successfully")
    
    # Verify module is unloaded
    lsmod_after = subprocess.run(
        "lsmod | grep nxp_simtemp", **SHELL_PARAMS
    )
    if lsmod_after.returncode == 0:
        pytest.fail("Module still found after rmmod")
    print("✓ lsmod: Module correctly removed from loaded modules")
    
    # Keep module loaded for subsequent tests
    insmod_module()
    print("Module reloaded for next test cases")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
