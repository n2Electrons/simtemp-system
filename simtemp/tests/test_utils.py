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
    Returns empty string if running as root, otherwise uses sudo if available.
    """
    # If we're root, no need for sudo
    if os.getuid() == 0:
        return ""

    # Otherwise, use sudo if available (even in containers)
    return "sudo " if shutil.which('sudo') else ""


# Dynamic sudo prefix based on environment detection
SUDO = get_sudo_prefix()

# Common subprocess parameters for shell commands
SHELL_PARAMS = {
    "shell": True,
    "capture_output": True,
    "text": True
}


def get_obj_path():
    """
    Get the absolute path to the directory containing nxp_simtemp.ko module.
    
    Returns:
        str: Absolute path to the 'obj' directory containing the kernel module
        
    Raises:
        FileNotFoundError: If the module file doesn't exist
    """
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(test_dir)
    obj_dir = os.path.join(project_root, 'kernel', 'obj')
    module_path = os.path.join(obj_dir, 'nxp_simtemp.ko')
    
    # Validate that the module exists
    if not os.path.exists(module_path):
        raise FileNotFoundError(
            f"Kernel module not found at {module_path}. "
            f"Please build the module first."
        )
    
    return obj_dir


# Convenience variable for the object directory path
obj_path = get_obj_path()


def wait_for_qemu_message(qemu_process, target_message, timeout=60):
    """
    Wait for a specific message from a QEMU process with timeout.
    
    Args:
        qemu_process: subprocess.Popen object of the QEMU process
        target_message: String to search for in QEMU output
        timeout: Maximum time to wait in seconds (default: 60)
        
    Returns:
        tuple: (success: bool, output_lines: list[str])
               success is True if message found, False if timeout/error
               output_lines contains all output lines collected
               
    Raises:
        RuntimeError: If QEMU process terminates unexpectedly
    """
    import time
    
    start_time = time.time()
    output_lines = []
    
    while time.time() - start_time < timeout:
        # Check if process is still running
        if qemu_process.poll() is not None:
            # Process has terminated unexpectedly
            stdout, stderr = qemu_process.communicate()
            if stdout:
                output_lines.extend(stdout.splitlines())
            
            error_msg = (f"QEMU process terminated unexpectedly. "
                         f"Exit code: {qemu_process.returncode}\n"
                         f"Output: {chr(10).join(output_lines)}")
            raise RuntimeError(error_msg)

        # Read output line by line with short timeout
        try:
            line = qemu_process.stdout.readline()
            if line:
                line = line.strip()
                output_lines.append(line)
                print(f"QEMU: {line}")

                # Check for the target message
                if target_message in line:
                    print(f"✓ Target message found: {target_message}")
                    return True, output_lines
            else:
                # No output, sleep briefly
                time.sleep(0.1)

        except Exception as e:
            error_msg = f"Error reading QEMU output: {e}"
            raise RuntimeError(error_msg) from e

    # Timeout reached
    return False, output_lines


def cleanup_qemu_processes(force_kill=False):
    """
    Clean up any existing QEMU processes.
    
    Args:
        force_kill: If True, use SIGKILL (-9), otherwise use SIGTERM
        
    Returns:
        bool: True if cleanup was successful, False if there were errors
    """
    import time
    
    try:
        signal_flag = "-9" if force_kill else "-f"
        subprocess.run(["pkill", signal_flag, "qemu-system-arm"],
                       check=False)
        time.sleep(2 if not force_kill else 1)  # Wait for cleanup
        return True
    except Exception as e:
        print(f"Warning: Error during QEMU cleanup: {e}")
        return False
