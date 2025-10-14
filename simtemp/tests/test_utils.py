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
    
    print("\nTest environment:")
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


def is_running_in_privileged_container():
    """
    Detect if we're running in a privileged container.
    Returns True if running in a container with privileges (no sudo needed).
    """
    # Check if we're in a container
    if not os.path.exists('/.dockerenv'):
        return False

    # Check if we're running as root
    if os.getuid() == 0:
        return True

    # Check if we can access kernel modules without sudo
    # This is a good indicator of privileged container access
    try:
        result = subprocess.run(
            ['lsmod'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Additional check: try to access /proc/modules directly
            if os.access('/proc/modules', os.R_OK):
                return True
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        pass

    return False


def get_sudo_prefix():
    """
    Get the appropriate sudo prefix based on the environment.
    Returns empty string if running in privileged container or as root.
    """
    # If we're root, no need for sudo
    if os.getuid() == 0:
        return ""

    # If we're in a privileged container, no need for sudo
    if is_running_in_privileged_container():
        return ""

    # Otherwise, use sudo if available
    return "sudo " if shutil.which('sudo') else ""


# Dynamic sudo prefix based on environment detection
SUDO = get_sudo_prefix()
