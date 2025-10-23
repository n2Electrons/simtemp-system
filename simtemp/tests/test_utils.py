"""
Test utilities for simtemp test suite.
"""

import os
import subprocess
import shutil
import pytest
import json
import time
from contextlib import contextmanager

# Import unified command executor components
from test_ucommand_exec import (
    execute_command,
    load_module as uexec_load_module,
    unload_module as uexec_unload_module,
    is_module_loaded as uexec_is_loaded,
    set_global_qemu_pid,
    clear_global_qemu_pid
)


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
    print(f"Determined object directory: {obj_dir}")
    print(f"Project root directory: {project_root}")
    print(f"Module path: {module_path}")
    print(f"Test Dir: {test_dir}")

    # Validate that the module exists
    if not os.path.exists(module_path):
        raise FileNotFoundError(
            f"Kernel module not found at {module_path}. "
            f"Please build the module first."
        )
    
    return obj_dir


def get_driver_path(test_suite_name=None):
    """
    Get the appropriate driver path based on test configuration.
    
    For QEMU tests with use_precompiled_driver=true, returns precompiled path.
    Otherwise returns the compiled obj path.
    
    Args:
        test_suite_name: Name of the test suite (e.g., 'qemu_integration')
        
    Returns:
        str: Absolute path to the nxp_simtemp.ko module
        
    Raises:
        FileNotFoundError: If the module file doesn't exist
    """
    import yaml
    
    # Try to load test configuration
    try:
        test_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(test_dir, 'config', 'simtemp_tests.yml')
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check if this is a QEMU test suite with precompiled driver
            if test_suite_name and test_suite_name in config.get('tests', {}):
                suite_config = config['tests'][test_suite_name]
                
                if suite_config.get('use_precompiled_driver', False):
                    precompiled_path = suite_config.get('precompiled_path')
                    if precompiled_path:
                        # Check if we're inside QEMU (test environment)
                        if check_qemu_test():
                            # Inside QEMU - use the path as configured
                            return precompiled_path
                        
                        # On host - try different possible paths
                        # Remove leading /tmp from precompiled_path for host access
                        if precompiled_path.startswith('/tmp/'):
                            # Remove '/tmp/'
                            relative_path = precompiled_path[5:]
                        else:
                            relative_path = precompiled_path.lstrip('/')
                            
                        host_paths = [
                            # Try as-is first (host with /tmp/prebuild)
                            precompiled_path,
                            f"/workspace/deployment/qemu/rootfs/tmp/"
                            f"{relative_path}",
                        ]
                        
                        # Try Jenkins workspace path
                        jenkins_workspace = os.environ.get('WORKSPACE', '')
                        if jenkins_workspace:
                            jenkins_path = os.path.join(
                                jenkins_workspace,
                                f"deployment/qemu/rootfs/tmp/{relative_path}"
                            )
                            host_paths.append(jenkins_path)
                        
                        for path in host_paths:
                            if os.path.exists(path):
                                return path
                        
                        print(f"Precompiled driver not found at any of: "
                              f"{host_paths}, falling back to compiled "
                              f"version")
    except Exception as e:
        print(f"Could not load test configuration: {e}, "
              f"using compiled driver")
    
    # Fall back to compiled driver path
    return os.path.join(get_obj_path(), 'nxp_simtemp.ko')


def restore_terminal():
    """
    Restore terminal to normal state after QEMU or other processes
    that may have left it in raw mode.
    
    This function can be called manually if the terminal becomes
    unresponsive after QEMU processes are terminated.
    
    Returns:
        bool: True if terminal restoration was successful
    """
    try:
        print("Restoring terminal state...")
        
        # Method 1: stty sane (most reliable)
        result1 = subprocess.run(["stty", "sane"], check=False,
                                 stdin=subprocess.DEVNULL,
                                 capture_output=True)

        # Method 2: tput reset (complementary)
        result2 = subprocess.run(["tput", "reset"], check=False,
                                 stdin=subprocess.DEVNULL,
                                 capture_output=True)

        # Method 3: echo control sequences to reset terminal
        # This sends ANSI reset sequences directly
        reset_sequences = [
            "\033c",        # Full reset
            "\033[!p",      # Soft reset
            "\033[?25h",    # Show cursor
        ]

        for seq in reset_sequences:
            try:
                subprocess.run(["echo", "-e", seq], check=False,
                               stdout=subprocess.DEVNULL)
            except Exception:
                pass
        
        success = (result1.returncode == 0 or result2.returncode == 0)
        
        if success:
            print("Terminal state restored successfully")
        else:
            print("Terminal restoration may have failed")
            print("   Try running 'reset' command manually")
            
        return success
        
    except Exception as e:
        print(f"Error restoring terminal: {e}")
        print("   Try running 'reset' or 'stty sane' manually")
        return False


@contextmanager
def preserve_working_directory():
    """
    Context manager that preserves the current working directory.
    
    Usage:
        with preserve_working_directory():
            # Change directories here
            os.chdir('/some/other/path')
            # Do work...
        # Working directory is automatically restored here
    """
    original_cwd = os.getcwd()
    try:
        yield original_cwd
    finally:
        try:
            os.chdir(original_cwd)
            print(f"Restored working directory to: {original_cwd}")
        except Exception as e:
            print(f"Failed to restore working directory: {e}")


def get_initial_working_directory():
    """
    Get and store the initial working directory for tests.
    
    Returns:
        str: The absolute path of the initial working directory
    """
    return os.getcwd()


def restore_working_directory(original_dir=None):
    """
    Restore the working directory to the original location.
    
    Args:
        original_dir: Directory to restore to. If None, tries to restore
                     to the directory where tests were started.

    Returns:
        bool: True if restoration was successful, False otherwise
    """
    try:
        if original_dir is None:
            # Try to determine original directory from test context
            test_dir = os.path.dirname(os.path.abspath(__file__))
            original_dir = test_dir

        current_dir = os.getcwd()

        if current_dir != original_dir:
            os.chdir(original_dir)
            print(f"Working directory restored: {current_dir} → "
                  f"{original_dir}")
            return True
        else:
            print(f"Already in correct directory: {original_dir}")
            return True
            
    except Exception as e:
        print(f"Failed to restore working directory: {e}")
        return False


def cleanup_test_environment():
    """
    Complete test cleanup function that should be called at the end of tests.
    
    This function performs:
    1. QEMU process cleanup (preserving compiled binaries)
    2. Terminal restoration
    3. Working directory restoration
    
    Note: Compiled binaries are preserved by default for analysis
    
    Returns:
        bool: True if all cleanup operations were successful
    """
    print("\nPerforming test cleanup...")
    
    # Cleanup QEMU processes and restore terminal (preserve binaries)
    cleanup_success = cleanup_qemu_processes(force_kill=True, restore_cwd=True,
                                             preserve_binaries=True)
    
    if cleanup_success:
        print("Test cleanup completed successfully")
    else:
        print("Some cleanup operations had issues")
    
    return cleanup_success


@contextmanager
def load_environment():
    """
    Context manager for test execution that ensures proper cleanup.
    
    Usage:
        with load_environment():
            # Your test code here
            # Directory changes, QEMU processes, etc.
            pass
        # Automatic cleanup happens here
    """
    original_dir = os.getcwd()
    print(f"Starting test in directory: {original_dir}")
    
    try:
        yield original_dir
    finally:
        print("\nTest completed, performing cleanup...")
        cleanup_test_environment()


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
            
            # Restore terminal state since QEMU terminated
            print("QEMU terminated, restoring terminal state...")
            restore_terminal()
            
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


def cleanup_qemu_processes(force_kill=False, restore_cwd=True,
                           preserve_binaries=True):
    """
    Clean up any existing QEMU processes and restore terminal state.
    
    Args:
        force_kill: If True, use SIGKILL (-9), otherwise use SIGTERM
        restore_cwd: If True, restore working directory to test directory
        preserve_binaries: If True, preserve compiled binaries in QEMU dir
        
    Returns:
        bool: True if cleanup was successful, False if there were errors
    """
    import time
    
    try:
        # Kill QEMU processes (but preserve compiled binaries)
        signal_flag = "-9" if force_kill else "-f"
        subprocess.run(["pkill", signal_flag, "qemu-system-arm"],
                       check=False)
        time.sleep(2 if not force_kill else 1)  # Wait for cleanup
        
        # Note: We preserve compiled binaries in QEMU directories for analysis
        if preserve_binaries:
            print("Preserving compiled binaries in QEMU directories")
        
        # Restore terminal state after QEMU cleanup
        # QEMU can leave terminal in raw mode, so we need to reset it
        try:
            # Method 1: Use stty to restore sane terminal settings
            subprocess.run(["stty", "sane"], check=False,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)

            # Method 2: Reset terminal using tput (if available)
            subprocess.run(["tput", "reset"], check=False,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)

        except Exception as term_e:
            print(f"Warning: Could not restore terminal state: {term_e}")
            print("You may need to run 'reset' or 'stty sane' manually "
                  "if terminal is corrupted")

        # Restore working directory if requested
        if restore_cwd:
            try:
                restore_working_directory()
            except Exception as cwd_e:
                print(f"Warning: Could not restore working directory: {cwd_e}")

        return True

    except Exception as e:
        print(f"Warning: Error during QEMU cleanup: {e}")
        return False


def cleanup_qemu_binaries(qemu_dir_path=None):
    """
    Optional function to clean up compiled binaries in QEMU directory.
    This function is separate from cleanup_qemu_processes to allow
    selective cleanup of binaries when needed.
    
    Args:
        qemu_dir_path: Path to QEMU directory. If None, uses default path.
        
    Returns:
        bool: True if cleanup was successful, False if there were errors
    """
    try:
        if qemu_dir_path is None:
            # Default QEMU simtemp driver path
            test_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(test_dir))
            qemu_dir_path = os.path.join(
                project_root, "deployment", "qemu", "rootfs",
                "tmp", "src", "simtemp_driver"
            )
        
        if os.path.exists(qemu_dir_path):
            print(f"🗑️ Cleaning compiled binaries in: {qemu_dir_path}")
            
            # List of compiled files to remove
            binary_patterns = [
                "*.ko",      # Kernel modules
                "*.o",       # Object files
                "*.mod",     # Module files
                "*.mod.c",   # Generated module source
                ".*.cmd",    # Command files
                "modules.order",
                "Module.symvers"
            ]
            
            import glob
            removed_count = 0
            
            for pattern in binary_patterns:
                pattern_path = os.path.join(qemu_dir_path, pattern)
                for file_path in glob.glob(pattern_path):
                    try:
                        os.remove(file_path)
                        removed_count += 1
                        print(f"  Removed: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"  Could not remove {file_path}: {e}")
            
            if removed_count > 0:
                print(f"Removed {removed_count} compiled files")
            else:
                print("ℹNo compiled files found to remove")
            
            return True
        else:
            print(f"ℹQEMU directory not found: {qemu_dir_path}")
            return True
            
    except Exception as e:
        print(f"Error during binary cleanup: {e}")
        return False


def list_qemu_binaries(qemu_dir_path=None):
    """
    List compiled binaries in QEMU directory without removing them.
    Useful for verification and debugging.
    
    Args:
        qemu_dir_path: Path to QEMU directory. If None, uses default path.
        
    Returns:
        list: List of found binary files
    """
    try:
        if qemu_dir_path is None:
            # Default QEMU simtemp driver path
            test_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(test_dir))
            qemu_dir_path = os.path.join(
                project_root, "deployment", "qemu", "rootfs",
                "tmp", "src", "simtemp_driver"
            )
        
        binary_files = []
        
        if os.path.exists(qemu_dir_path):
            print(f"📁 Checking binaries in: {qemu_dir_path}")
            
            # List of binary patterns to look for
            binary_patterns = [
                "*.ko",      # Kernel modules
                "*.o",       # Object files
                "*.mod",     # Module files
                "*.mod.c",   # Generated module source
                ".*.cmd",    # Command files
                "modules.order",
                "Module.symvers"
            ]
            
            import glob
            
            for pattern in binary_patterns:
                pattern_path = os.path.join(qemu_dir_path, pattern)
                for file_path in glob.glob(pattern_path):
                    file_name = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    binary_files.append(file_name)
                    print(f"  📦 {file_name} ({file_size} bytes)")
            
            if binary_files:
                print(f"Found {len(binary_files)} binary/build files")
            else:
                print("ℹ️ No binary files found")
        else:
            print(f"⚠️ QEMU directory not found: {qemu_dir_path}")
        
        return binary_files
        
    except Exception as e:
        print(f"Error listing binaries: {e}")
        return []


def get_module_path_for_context():
    """
    Determine the correct module path based on execution context.
    
    Returns:
        tuple: (module_path: str, context_description: str)
               module_path is the absolute path to the kernel module
               context_description is a human-readable description
    """
    # Check execution context
    qemu_process = check_qemu_test()
    
    if qemu_process:
        # Real QEMU mode: use prebuilt ARM driver from rootfs
        module_path = "/tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
        context = "QEMU mode - using ARM prebuilt driver"
    else:
        # In host/Docker/Jenkins mode: use locally compiled driver
        module_path = os.path.join(get_obj_path(), "nxp_simtemp.ko")
        context = "host/Docker/Jenkins mode - using local driver"
    
    return module_path, context


# Global QEMU session management - shared across all tests
_global_qemu_process = None


def get_shared_qemu_session():
    """
    Get or initialize shared QEMU session for all tests.
    
    This function ensures that only ONE QEMU instance is started across
    all test files and functions, preventing multiple QEMU boots that
    cause resource conflicts and slow test execution.
    
    Returns:
        Process handle if QEMU is running, None if not in QEMU mode
    """
    global _global_qemu_process
    
    if _global_qemu_process is None:
        _global_qemu_process = check_qemu_test()
        if _global_qemu_process:
            print("=== Global Shared QEMU Session Initialized ===")
            print(f"QEMU PID: {_global_qemu_process.pid}")
        else:
            print("=== Running in Host Mode (no QEMU) ===")
    
    return _global_qemu_process


def check_qemu_test():
    """
    Check if this test should run in QEMU mode and manage shared QEMU session.
    Returns the QEMU process handle if QEMU is started/running, None otherwise.
    
    Uses introspection to detect the current test being executed and match it
    with the appropriate test_id from configuration.
    
    Uses shared QEMU session management:
    - First test starts QEMU and creates session marker
    - Subsequent tests reuse existing QEMU session
    - Session marker prevents multiple QEMU boots
    """
    try:
        import yaml
        import inspect
        
        # Use introspection to detect current test
        current_test_file = None
        current_test_function = None
        
        for frame in inspect.stack():
            frame_filename = frame.filename
            frame_function = frame.function
            
            # Look for test files and test functions
            if ('test_' in frame_filename and 
                frame_filename.endswith('.py') and
                frame_function.startswith('test_')):
                current_test_file = os.path.basename(frame_filename)
                current_test_function = frame_function
                break
        
        if not current_test_file:
            return None
            
        print(f"🔍 [DEBUG] Detected test: {current_test_file}::{current_test_function}")
        
        # Check for QEMU integration test configuration
        config_path = os.environ.get('TEST_CONFIG_PATH',
                                     'simtemp/tests/config/simtemp_tests.yml')
        if not os.path.exists(config_path):
            return None
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Look for qemu_integration section
        qemu_tests = config.get('tests', {}).get('qemu_integration', {})
        if not qemu_tests.get('enabled', False):
            return None
            
        # Find the specific test case that matches current test
        test_cases = qemu_tests.get('test_cases', [])
        for test_case in test_cases:
            pytest_file = test_case.get('pytest_file', '')
            test_id = test_case.get('test_id', '')
            
            # Match by pytest file name
            if (pytest_file == current_test_file and 
                test_case.get('enabled', False) and
                ('QEMU' in test_id or test_case.get('qemu_specific', {}).get('expects_boot', False))):
                # QEMU mode detected for specific test
                print(f"\n=== QEMU Mode Detected for {test_id} ===")
                print(f"    Test file: {current_test_file}")
                print(f"    Test function: {current_test_function}")
                return get_or_start_shared_qemu_session()
                
        return None
    except Exception as e:
        print(f"🔍 [DEBUG] Error in check_qemu_test(): {e}")
        return None


def get_qemu_session_marker_path():
    """Get the path for QEMU session marker file."""
    return '/tmp/qemu_session_active.marker'


def is_qemu_session_active():
    """Check if a QEMU session is already running."""
    marker_path = get_qemu_session_marker_path()
    if not os.path.exists(marker_path):
        return False
    
    try:
        with open(marker_path, 'r') as f:
            data = json.loads(f.read())
            pid = data.get('pid')
            
        # Check if the process is still running
        if pid:
            try:
                os.kill(pid, 0)  # Signal 0 just checks if process exists
                print(f"Found active QEMU session with PID {pid}")
                return True
            except OSError:
                # Process doesn't exist, remove stale marker
                print(f"Removing stale QEMU session marker (PID {pid} not found)")
                os.remove(marker_path)
                return False
    except (json.JSONDecodeError, IOError, OSError):
        # Corrupted or unreadable marker, remove it
        try:
            os.remove(marker_path)
        except OSError:
            pass
        return False
    
    return False


def create_qemu_session_marker(qemu_process):
    """Create a marker file indicating active QEMU session."""
    marker_path = get_qemu_session_marker_path()
    marker_data = {
        'pid': qemu_process.pid,
        'started_at': time.time(),
        'started_by': os.path.basename(__file__),
        'test_name': os.environ.get('PYTEST_CURRENT_TEST', 'unknown')
    }
    
    try:
        with open(marker_path, 'w') as f:
            json.dump(marker_data, f, indent=2)
        print(f"Created QEMU session marker: PID {qemu_process.pid}")
        
        # Set global QEMU PID in command executor
        set_global_qemu_pid(qemu_process.pid)
            
    except IOError as e:
        print(f"Warning: Could not create QEMU session marker: {e}")


def get_or_start_shared_qemu_session(force_new=False):
    """
    Get existing QEMU session or start a new one with session management.
    
    Args:
        force_new (bool): If True, starts a new private QEMU session
                         ignoring any existing shared sessions.
                         If False (default), reuses existing sessions.
    
    Returns:
        QEMU process handle or None.
    """
    print("🔧 [DEBUG] get_or_start_shared_qemu_session() called")
    print(f"🔧 [DEBUG] force_new={force_new}")
    
    # If force_new is True, start a private session
    if force_new:
        print("🔧 [DEBUG] force_new=True, starting private QEMU session...")
        return start_qemu_and_wait_for_boot()
    
    # Check if QEMU session is already active
    print("🔧 [DEBUG] Checking if QEMU session is already active...")
    if is_qemu_session_active():
        print("Reusing existing QEMU session...")
        print("🔧 [DEBUG] Found active session, will reuse it")
        
        # Try to get the process handle from the marker
        marker_path = get_qemu_session_marker_path()
        try:
            with open(marker_path, 'r') as f:
                data = json.loads(f.read())
                pid = data.get('pid')
                
            # Create a mock process object for compatibility
            # (We can't get the actual process object, but tests just need to know QEMU is running)
            class MockQemuProcess:
                def __init__(self, pid):
                    self.pid = pid
                    self.returncode = None
                
                def poll(self):
                    try:
                        os.kill(self.pid, 0)
                        return None  # Process is still running
                    except OSError:
                        return -1  # Process has terminated
                
                def terminate(self):
                    try:
                        os.kill(self.pid, 15)  # SIGTERM
                    except OSError:
                        pass
                
                def kill(self):
                    try:
                        os.kill(self.pid, 9)  # SIGKILL
                    except OSError:
                        pass
                
                def wait(self, timeout=None):
                    # Simple wait implementation
                    import time
                    start_time = time.time()
                    while self.poll() is None:
                        if timeout and (time.time() - start_time) > timeout:
                            raise subprocess.TimeoutExpired([], timeout)
                        time.sleep(0.1)
                    return self.returncode
            
            print(f"🔧 [DEBUG] Returning MockQemuProcess with PID {pid}")
            return MockQemuProcess(pid)
            
        except (json.JSONDecodeError, IOError, KeyError):
            print("Warning: Could not read QEMU session marker, starting new session")
    else:
        print("🔧 [DEBUG] No active QEMU session found")
    
    # No active session, start new QEMU
    print("Starting new shared QEMU session...")
    print("🔧 [DEBUG] About to call start_qemu_and_wait_for_boot()")
    qemu_process = start_qemu_and_wait_for_boot()
    print(f"🔧 [DEBUG] start_qemu_and_wait_for_boot() returned: {qemu_process}")
    
    if qemu_process:
        print("🔧 [DEBUG] QEMU process created successfully, creating marker...")
        create_qemu_session_marker(qemu_process)
        print("QEMU session ready - other tests will reuse this session")
        print(f"🔧 [DEBUG] Returning QEMU process with PID: {qemu_process.pid}")
    else:
        print("QEMU session NOT CREATED!")
        print("🔧 [DEBUG] QEMU process is None - something went wrong")
    return qemu_process


def cleanup_qemu_session():
    """Clean up shared QEMU session and remove marker."""
    marker_path = get_qemu_session_marker_path()
    
    # Clear global QEMU PID first
    clear_global_qemu_pid()
    
    # Get process info from marker if it exists
    qemu_pid = None
    if os.path.exists(marker_path):
        try:
            with open(marker_path, 'r') as f:
                data = json.loads(f.read())
                qemu_pid = data.get('pid')
        except (json.JSONDecodeError, IOError):
            pass
    
    # Terminate QEMU process
    if qemu_pid:
        try:
            print(f"Terminating QEMU session (PID {qemu_pid})...")
            os.kill(qemu_pid, 15)  # SIGTERM
            
            # Wait a bit for graceful shutdown
            time.sleep(2)
            
            # Check if it's still running
            try:
                os.kill(qemu_pid, 0)
                print("QEMU still running, forcing termination...")
                os.kill(qemu_pid, 9)  # SIGKILL
            except OSError:
                pass  # Process already terminated
                
        except OSError:
            print(f"QEMU process {qemu_pid} not found (may have already terminated)")
    
    # Clean up any remaining QEMU processes
    cleanup_qemu_processes(force_kill=True)
    
    # Remove session marker
    try:
        if os.path.exists(marker_path):
            os.remove(marker_path)
            print("QEMU session marker removed")
    except OSError as e:
        print(f"Warning: Could not remove QEMU session marker: {e}")
    
    # Restore terminal state
    restore_terminal()
    print("QEMU session cleanup completed")


def start_qemu_and_wait_for_boot():
    """
    Start QEMU process and wait for boot completion.
    Returns the QEMU process handle.
    """
    import subprocess
    import pytest
    
    print("[DEBUG] start_qemu_and_wait_for_boot() called")
    
    # Cleanup any existing QEMU processes first
    print("[DEBUG] Cleaning up existing QEMU processes...")
    cleanup_qemu_processes(force_kill=True)
    print("[DEBUG] Cleanup completed")
    
    # Get project root directory - handle different environments
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # In Jenkins: /var/jenkins_home/workspace/_Github_.../simtemp/tests
    # We need to go up from simtemp/tests -> simtemp -> project_root
    simtemp_dir = os.path.dirname(test_dir)  # Remove /tests
    project_root = os.path.dirname(simtemp_dir)  # Remove /simtemp
    
    print(f"[DEBUG] Test dir: {test_dir}")
    print(f"[DEBUG] Simtemp dir: {simtemp_dir}")
    print(f"[DEBUG] Project root: {project_root}")
    
    # Define QEMU file paths
    qemu_base = os.path.join(project_root, "deployment", "qemu")
    kernel_path = os.path.join(qemu_base, "linux-build-imx",
                               "arch", "arm", "boot", "zImage")
    # dtb_path = os.path.join(qemu_base, "linux-build-imx",
    #                         "arch", "arm", "boot", "dts",
    #                         "imx6q-sabresd.dtb")
    dtb_path = os.path.join(qemu_base, "imx6q-sabresd-with-simtemp.dtb")
    rootfs_path = os.path.join(qemu_base, "rootfs.cpio.gz")
    
    print(f"[DEBUG] QEMU base: {qemu_base}")
    print(f"[DEBUG] Kernel path: {kernel_path}")
    print(f"[DEBUG] DTB path: {dtb_path}")
    print(f"[DEBUG] Rootfs path: {rootfs_path}")
    
    # Verify QEMU files exist
    required_files = [kernel_path, dtb_path, rootfs_path]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"[ERROR] Required QEMU file not found: {file_path}")
            pytest.fail(f"Required QEMU file not found: {file_path}")
        else:
            print(f"[DEBUG] Found required file: {file_path}")
    
    # Start QEMU process
    qemu_cmd = [
        "qemu-system-arm",
        "-M", "sabrelite",
        "-cpu", "cortex-a9",
        "-m", "1024",
        "-nographic",
        "-kernel", kernel_path,
        "-dtb", dtb_path,
        "-initrd", rootfs_path,
        "-append",
        "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 "
        "rdinit=/init quiet loglevel=8 initcall_debug printk.time=1",
        "-no-reboot"
    ]
    
    print("Starting QEMU for platform driver testing...")
    cmd_preview = f"{' '.join(qemu_cmd[:3])}... ({len(qemu_cmd)} args total)"
    print(f"[DEBUG] QEMU command: {cmd_preview}")
    
    try:
        qemu_process = subprocess.Popen(
            qemu_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        print(f"[DEBUG] QEMU process started with PID: {qemu_process.pid}")
        
        # Small delay to let QEMU initialize
        import time
        time.sleep(1)
        
        # Check if QEMU is still running after initialization
        poll_result = qemu_process.poll()
        if poll_result is not None:
            error_msg = f"QEMU process terminated immediately " \
                       f"with exit code: {poll_result}"
            print(f"[ERROR] {error_msg}")
            # Try to get any error output
            try:
                stdout, stderr = qemu_process.communicate(timeout=1)
                if stdout:
                    print(f"[ERROR] QEMU stdout: {stdout}")
                if stderr:
                    print(f"[ERROR] QEMU stderr: {stderr}")
            except subprocess.TimeoutExpired:
                print("[ERROR] Could not get QEMU error output (timeout)")
            fail_msg = f"QEMU process terminated immediately " \
                       f"with exit code: {poll_result}"
            pytest.fail(fail_msg)
        else:
            print("[DEBUG] QEMU process is running normally")
    
    except Exception as e:
        print(f"[ERROR] Failed to start QEMU process: {e}")
        pytest.fail(f"Failed to start QEMU process: {e}")
    
    # Wait for ARM initramfs ready message
    print("Waiting for QEMU boot completion...")
    print("[DEBUG] Starting wait_for_qemu_message...")
    
    boot_success, boot_output = wait_for_qemu_message(
        qemu_process, "=== initramfs ready ===", timeout=120
    )
    
    debug_msg = f"wait_for_qemu_message returned: success={boot_success}, " \
                f"output_lines={len(boot_output)}"
    print(f"[DEBUG] {debug_msg}")
    
    if not boot_success:
        print("QEMU boot FAILED!")
        print(f"[DEBUG] Boot output captured ({len(boot_output)} lines):")
        for i, line in enumerate(boot_output[-10:], 1):  # Show last 10 lines
            print(f"[DEBUG] Line -{10-i+1}: {line}")
        
        print("[DEBUG] Terminating QEMU process...")
        qemu_process.terminate()
        pytest.fail("QEMU failed to boot - initramfs ready "
                    "message not found")
    
    print("QEMU boot completed - initramfs ready")
    print("Shell prompt available - QEMU ready for platform driver tests")
    print(f"[DEBUG] Returning QEMU process with PID: {qemu_process.pid}")
    return qemu_process


# =============================================================================
# QEMU Command Execution Functions
# =============================================================================

def send_qemu_command(qemu_process, command, timeout=5):
    """
    Send a command to QEMU process and collect output.
    
    Args:
        qemu_process: QEMU process handle (legacy parameter for compatibility)
        command (str): Command to execute
        timeout (int): Timeout in seconds
        
    Returns:
        tuple: (success: bool, output_lines: list)
        
    Note: This function now uses the UnifiedCommandExecutor which handles
    environment detection automatically. The qemu_process parameter is
    maintained for API compatibility.
    """
    return execute_command(command, timeout)


# =============================================================================
# Centralized Module Management Functions
# =============================================================================

def is_module_loaded(module_name="nxp_simtemp"):
    """
    Check if a kernel module is currently loaded.
    
    Args:
        module_name (str): Name of the module to check (default: nxp_simtemp)
        
    Returns:
        bool: True if module is loaded, False otherwise
    """
    return uexec_is_loaded(module_name)


def load_module(module_name="nxp_simtemp", module_path=None):
    """
    Load a kernel module using insmod.
    
    Args:
        module_name (str): Name of the module to load (default: nxp_simtemp)
        module_path (str): Optional explicit path to module file. If provided,
                          this path will be used instead of auto-detection.
        
    Returns:
        bool: True if successful, False otherwise
    """
    return uexec_load_module(module_name, module_path)


def rm_module(module_name="nxp_simtemp"):
    """
    Unload a kernel module using rmmod or modprobe -r.
    
    Args:
        module_name (str): Name of the module to unload (default: nxp_simtemp)
        
    Returns:
        bool: True if successful, False otherwise
    """
    return uexec_unload_module(module_name)
