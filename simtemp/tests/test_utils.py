"""
Test utilities for simtemp test suite.
"""

import os
import subprocess
import shutil
import pytest

def setup_test_environment():
    """
    Setup test environment and return module path.
    Returns the path to the kernel module for testing.
    Validates that the module exists before returning.
    """
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(test_dir)
    module_path = os.path.join(project_root, 'kernel', 'obj', 'nxp_simtemp.ko')
    
    print(f"\nTest environment:")
    print(f"Current directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Module path: {module_path}\n")
    
    # Validate module exists
    if not os.path.exists(module_path):
        pytest.fail(
            f"Kernel module not found at {module_path}.\n"
            f"Build may have failed.\n"
            f"Please ensure module is built before running tests."
        )
    
    return module_path

# Simple sudo prefix - assume environment is ready for testing
SUDO = "sudo " if shutil.which('sudo') else ""
