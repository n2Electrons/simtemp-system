#!/usr/bin/env python3

import subprocess
import re
import sys
import time
from test_utils import SUDO

# Test Command:
# python3 -m pytest test_f_k8_tc_001.py::test_driver_load_unload


def test_driver_load_unload():
    """F-K8-TC-001: Load/unload kernel module without WARN/OOPS"""

    # Load module
    time.sleep(0.3)
    result = subprocess.run(
        f"{SUDO}insmod ../kernel/obj/nxp_simtemp.ko", shell=True,
        capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"Module load failed: {result.stderr}")

    # Unload module
    time.sleep(0.3)
    result = subprocess.run(
        f"{SUDO}rmmod nxp_simtemp", shell=True,
        capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"Module unload failed: {result.stderr}")

    # Check dmesg for WARN/OOPS (last 10 lines should be enough)
    time.sleep(0.3)
    result = subprocess.run(
        f"{SUDO}dmesg | tail -n 10", shell=True,
        capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"Failed to read dmesg: {result.stderr}")
    
    dmesg_output = result.stdout
    warn_pattern = r'\bWARN\b|\bOOPS\b|\bBUG\b|\bpanic\b'
    warnings = re.findall(warn_pattern, dmesg_output, re.IGNORECASE)

    if warnings:
        raise AssertionError(f"Kernel warnings found: {warnings}")


if __name__ == "__main__":
    try:
        test_driver_load_unload()
        print("PASS: F-K8-TC-001")
        sys.exit(0)
    except AssertionError as e:
        print(f"FAIL: F-K8-TC-001 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: F-K8-TC-001 - {e}")
        sys.exit(1)
