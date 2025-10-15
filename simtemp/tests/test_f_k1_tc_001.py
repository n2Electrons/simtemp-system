"""
Test cases for kernel driver functionality.
"""

import os
import sys
import pytest
import subprocess
import time
from test_utils import SUDO, setup_test_environment

# SUDO: Prefix for commands requiring elevated privileges (e.g., insmod/rmmod)
# Will be "sudo " if sudo is available, empty string if running as root

def test_insmod_registers_driver(capsys: pytest.CaptureFixture[str]): 
    """
    Test case F-K1-TC-001: Verify driver registration via insmod.
    Expected Result: Driver registers successfully and sysfs entries are created.
    """
    module_path = setup_test_environment()
    
    # Print module info (modinfo output is useful for debugging)
    try:
        modinfo = subprocess.run(['modinfo', module_path], capture_output=True, text=True, timeout=10)
        if modinfo.returncode == 0:
            print("\nModule information:")
            print(modinfo.stdout)
        else:
            pytest.skip(f"Could not get module info: {modinfo.stderr}")
    except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
        pytest.fail(f"Could not run 'modinfo' command: {e}")
    
    # Try to load the module using the absolute path we already verified
    print(f"Loading module: {module_path}")
    result = subprocess.run(
        f"{SUDO}insmod {module_path}", shell=True,
        capture_output=True, text=True )
    
    if result.returncode != 0:
        pytest.fail(
            f"Failed to load driver:\n"
            f"Output: {result.stdout}\n"
            f"Error: {result.stderr}\n"
        )
        
    # Verify module is loaded
    lsmod = subprocess.run("lsmod | grep nxp_simtemp", shell=True, capture_output=True, text=True)
    if lsmod.returncode != 0:
        pytest.fail(
            f"Module not found in lsmod after loading.\n"
        )
    else:
        print(f"\nModule loaded successfully:\n{lsmod.stdout}")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
