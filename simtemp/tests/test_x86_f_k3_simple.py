#!/usr/bin/env python3

import os
import pytest
from test_utils import obj_path, load_module


def test_device_node_exists():
    """F-K3-TC-001: Node exists"""
    
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    
    if not os.path.exists(module_path):
        pytest.fail(f"Module not found: {module_path}")
    
    load_module()
    
    # Check device exists
    device_path = "/dev/simtemp0"
    assert os.path.exists(device_path), f"Device not found: {device_path}"
    
    print("✓ Device node exists")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])