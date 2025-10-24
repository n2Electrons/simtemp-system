#!/usr/bin/env python3

import os
import pytest
from test_utils import load_simtemp_modules


def test_device_node_exists():
    """F-K3-TC-001: Node exists"""
    
    # Load modules using centralized function for kernel_driver_suite
    if not load_simtemp_modules("kernel_driver_suite"):
        pytest.fail("Failed to load simtemp modules")
    
    # Check device exists
    device_path = "/dev/simtemp0"
    assert os.path.exists(device_path), f"Device not found: {device_path}"
    
    print("✓ Device node exists")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])