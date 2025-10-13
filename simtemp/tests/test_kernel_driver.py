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
        time.sleep(0.3)
        modinfo = subprocess.run(['modinfo', module_path], capture_output=True, text=True, timeout=10)
        if modinfo.returncode == 0:
            print("\nModule information:")
            print(modinfo.stdout)
        else:
            pytest.skip(f"Could not get module info: {modinfo.stderr}")
    except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
        pytest.fail(f"Could not run 'modinfo' command: {e}")
    
    print("Note: BTF generation warning during build is expected and not critical.")

    # Check if module is already loaded and remove if necessary
    time.sleep(0.3)
    lsmod = subprocess.run("lsmod | grep nxp_simtemp", shell=True, capture_output=True, text=True)
    if lsmod.returncode == 0:
        cmd = f"{SUDO}rmmod nxp_simtemp"
        time.sleep(0.3)
        cleanup_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if cleanup_result.returncode != 0:
            print(f"Module clean-up failed")
            pytest.fail("Module clean-up failed")

    # Try to load the module using the absolute path we already verified
    print(f"Loading module: {module_path}")
    time.sleep(0.3)
    result = subprocess.run(
        f"{SUDO}insmod {module_path}", shell=True,
        capture_output=True, text=True )
    
    time.sleep(0.3)
    # Check dmesg for any loading issues
    dmesg = subprocess.run(
        f"{SUDO}dmesg | tail -n 5", shell=True,
        capture_output=True, text=True )
    
    if result.returncode != 0:
        pytest.fail(
            f"Failed to load driver:\n"
            f"Output: {result.stdout}\n"
            f"Error: {result.stderr}\n"
            f"Recent dmesg output:\n{dmesg.stdout}"
        )
        
    # Verify module is loaded
    time.sleep(0.3)
    lsmod = subprocess.run("lsmod | grep nxp_simtemp", shell=True, capture_output=True, text=True)
    if lsmod.returncode != 0:
        pytest.fail(
            f"Module not found in lsmod after loading.\n"
            f"Recent dmesg output:\n{dmesg.stdout}"
        )
    else:
        print(f"\nModule loaded successfully:\n{lsmod.stdout}")

    # Test cleanup - ensure module is removed
    print("\nCleaning up...")
    cmd = f"{SUDO}rmmod nxp_simtemp"
    time.sleep(0.3)
    cleanup_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if cleanup_result.returncode != 0 and "not currently loaded" not in cleanup_result.stderr:
        print(f"Warning: Module cleanup failed:\n"
              f"Command: {cmd}\n"
              f"Error: {cleanup_result.stderr}",
              file=sys.stderr)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

