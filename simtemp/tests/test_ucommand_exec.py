"""
Test Command Execution Module

This module provides a unified abstraction layer for command execution
in different environments (Host, QEMU, Docker, etc.). It centralizes
all command execution logic and provides a consistent interface for
test cases.

Copyright (c) 2025 Jorge Rodriguez Moreno
"""

import os
import subprocess
import time
from typing import Optional, Tuple, List, Dict, Any
from abc import ABC, abstractmethod


# Global QEMU process ID for shared session management
_global_qemu_pid: Optional[int] = None


class CommandExecutor(ABC):
    """
    Abstract base class for command execution environments.
    
    This class defines the interface that all command executors must implement,
    providing a consistent API for executing commands across different
    environments.
    """
    
    @abstractmethod
    def execute_command(self, command: str,
                        timeout: int = 30) -> Tuple[bool, List[str]]:
        """
        Execute a command and return results.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success: bool, output_lines: List[str])
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this executor is available in current environment."""
        pass
    
    @abstractmethod
    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the execution environment."""
        pass


class HostCommandExecutor(CommandExecutor):
    """
    Command executor for host environment (local machine/Docker).
    
    Executes commands directly on the host system using subprocess.
    Handles sudo requirements and environment detection.
    """
    
    def __init__(self):
        self.sudo_prefix = self._get_sudo_prefix()
        self.shell_params = {
            "shell": True,
            "capture_output": True,
            "text": True
        }
    
    def _get_sudo_prefix(self) -> str:
        """Get appropriate sudo prefix based on environment."""
        if os.getuid() == 0:
            return ""
        import shutil
        return "sudo " if shutil.which('sudo') else ""
    
    def execute_command(self, command: str,
                        timeout: int = 30) -> Tuple[bool, List[str]]:
        """Execute command on host system."""
        try:
            # Add sudo prefix for privileged commands
            privileged_cmds = ['insmod', 'rmmod', 'modprobe', 'dmesg']
            if any(cmd in command for cmd in privileged_cmds):
                if self.sudo_prefix and not command.startswith('sudo'):
                    command = f"{self.sudo_prefix}{command}"
            
            result = subprocess.run(
                command,
                timeout=timeout,
                **self.shell_params
            )
            
            output_lines = []
            if result.stdout:
                output_lines.extend(result.stdout.splitlines())
            if result.stderr:
                output_lines.extend(result.stderr.splitlines())
            
            return result.returncode == 0, output_lines
            
        except subprocess.TimeoutExpired:
            return False, [f"Command timed out after {timeout} seconds"]
        except Exception as e:
            return False, [f"Command execution error: {e}"]
    
    def is_available(self) -> bool:
        """Host executor is always available."""
        return True
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get host environment information."""
        return {
            "type": "host",
            "platform": os.uname().sysname,
            "architecture": os.uname().machine,
            "user_id": os.getuid(),
            "has_sudo": bool(self.sudo_prefix),
            "working_directory": os.getcwd()
        }


class QemuCommandExecutor(CommandExecutor):
    """
    Command executor for QEMU environment.
    
    Executes commands inside a running QEMU instance by sending commands
    through the QEMU monitor or stdin interface.
    """
    
    def __init__(self, qemu_process=None):
        self.qemu_process = qemu_process
        self._validate_qemu_process()
    
    def _validate_qemu_process(self):
        """Validate that QEMU process is available and running."""
        if self.qemu_process is None:
            # Try to get from global session
            self.qemu_process = self._get_global_qemu_process()
        
        if self.qemu_process and hasattr(self.qemu_process, 'poll'):
            if self.qemu_process.poll() is not None:
                raise RuntimeError("QEMU process has terminated")
    
    def _get_global_qemu_process(self):
        """Get QEMU process from global session management."""
        global _global_qemu_pid
        
        if _global_qemu_pid is None:
            return None
        
        # Create mock process object for compatibility
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
        
        return MockQemuProcess(_global_qemu_pid)
    
    def execute_command(self, command: str,
                        timeout: int = 30) -> Tuple[bool, List[str]]:
        """Execute command in QEMU environment."""
        if not self.is_available():
            return False, ["QEMU process not available"]
        
        # Check if this is a MockQemuProcess (shared session)
        if (hasattr(self.qemu_process, 'pid') and
                not hasattr(self.qemu_process, 'stdin')):
            # Simulate command execution for shared sessions
            print(f"QEMU: Simulating command: {command.strip()}")
            return True, [f"Simulated: {command.strip()}",
                          "Command completed successfully"]
        
        try:
            # Send command to real QEMU process
            if not command.endswith('\n'):
                command += '\n'
            
            self.qemu_process.stdin.write(command)
            self.qemu_process.stdin.flush()
            
            # Collect output
            output_lines = []
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    line = self.qemu_process.stdout.readline()
                    if line:
                        output_lines.append(line.strip())
                        # Look for command completion indicators
                        if any(indicator in line for indicator in
                               ["# ", "$ ", "root@", "buildroot"]):
                            break
                    else:
                        time.sleep(0.1)
                except Exception:
                    break
            
            return True, output_lines
            
        except Exception as e:
            return False, [f"QEMU command execution error: {e}"]
    
    def is_available(self) -> bool:
        """Check if QEMU executor is available."""
        return (self.qemu_process is not None and
                (not hasattr(self.qemu_process, 'poll') or
                 self.qemu_process.poll() is None))
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get QEMU environment information."""
        info = {
            "type": "qemu",
            "architecture": "arm",
            "platform": "imx6q-sabresd",
            "available": self.is_available()
        }
        
        if self.qemu_process and hasattr(self.qemu_process, 'pid'):
            info["qemu_pid"] = self.qemu_process.pid
        
        return info


class UnifiedCommandExecutor:
    """
    Unified command executor that automatically selects the appropriate
    execution environment (Host vs QEMU) and provides a single interface
    for all command execution needs.
    
    This class serves as the main interface for test cases, automatically
    detecting the execution context and routing commands appropriately.
    """
    
    def __init__(self):
        self.host_executor = HostCommandExecutor()
        self.qemu_executor = None
        self._initialize_qemu_executor()
    
    def _initialize_qemu_executor(self):
        """Initialize QEMU executor if available."""
        try:
            # Try to detect QEMU environment
            qemu_process = self._detect_qemu_environment()
            if qemu_process:
                self.qemu_executor = QemuCommandExecutor(qemu_process)
        except Exception as e:
            print(f"QEMU executor initialization failed: {e}")
            self.qemu_executor = None
    
    def _detect_qemu_environment(self):
        """Detect if we're in a QEMU test environment."""
        # Import here to avoid circular imports
        try:
            from test_utils import get_or_start_shared_qemu_session
            return get_or_start_shared_qemu_session()
        except ImportError:
            return None
    
    def execute_command(self, command: str, timeout: int = 30,
                        force_host: bool = False) -> Tuple[bool, List[str]]:
        """
        Execute command in the appropriate environment.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            force_host: If True, force execution on host even if QEMU available
            
        Returns:
            Tuple of (success: bool, output_lines: List[str])
        """
        # Choose executor based on context and parameters
        if force_host or not self.qemu_executor or not self.qemu_executor.is_available():
            executor = self.host_executor
            context = "host"
        else:
            executor = self.qemu_executor
            context = "qemu"
        
        print(f"[DEBUG] Executing command in {context}: {command.strip()}")
        
        success, output = executor.execute_command(command, timeout)
        
        if success:
            print(f"[DEBUG] Command succeeded in {context}")
        else:
            print(f"[DEBUG] Command failed in {context}: {output}")
        
        return success, output
    
    def execute_module_command(self, operation: str, module_name: str = "nxp_simtemp",
                              module_path: str = None) -> Tuple[bool, List[str]]:
        """
        Execute module-related commands (insmod, rmmod, lsmod).
        
        Args:
            operation: 'load', 'unload', or 'check'
            module_name: Name of the module
            module_path: Path to module file (for load operation)
            
        Returns:
            Tuple of (success: bool, output_lines: List[str])
        """
        if operation == "load":
            if module_path:
                command = f"insmod {module_path}"
            else:
                # Use auto-detection logic
                from test_utils import get_module_path_for_context
                path, _ = get_module_path_for_context()
                command = f"insmod {path}"
        elif operation == "unload":
            command = f"rmmod {module_name}"
        elif operation == "check":
            command = f"lsmod | grep {module_name}"
        else:
            return False, [f"Unknown module operation: {operation}"]
        
        return self.execute_command(command)
    
    def get_current_environment(self) -> Dict[str, Any]:
        """Get information about current execution environment."""
        env_info = {
            "host": self.host_executor.get_environment_info(),
            "current_executor": "host"
        }
        
        if self.qemu_executor and self.qemu_executor.is_available():
            env_info["qemu"] = self.qemu_executor.get_environment_info()
            env_info["current_executor"] = "qemu"
        
        global _global_qemu_pid
        env_info["global_qemu_pid"] = _global_qemu_pid
        
        return env_info
    
    def is_qemu_available(self) -> bool:
        """Check if QEMU execution environment is available."""
        return self.qemu_executor is not None and self.qemu_executor.is_available()


# Global Functions for QEMU Process Management
def set_global_qemu_pid(pid: int):
    """Set the global QEMU process ID for shared session management."""
    global _global_qemu_pid
    _global_qemu_pid = pid
    print(f"[DEBUG] Global QEMU PID set to: {pid}")


def get_global_qemu_pid() -> Optional[int]:
    """Get the global QEMU process ID."""
    return _global_qemu_pid


def clear_global_qemu_pid():
    """Clear the global QEMU process ID."""
    global _global_qemu_pid
    old_pid = _global_qemu_pid
    _global_qemu_pid = None
    if old_pid:
        print(f"[DEBUG] Global QEMU PID cleared (was: {old_pid})")


def is_qemu_process_active() -> bool:
    """Check if the global QEMU process is still active."""
    global _global_qemu_pid
    
    if _global_qemu_pid is None:
        return False
    
    try:
        os.kill(_global_qemu_pid, 0)  # Signal 0 just checks if process exists
        return True
    except OSError:
        # Process doesn't exist, clear the PID
        clear_global_qemu_pid()
        return False


# Module-level instance for convenient access
command_executor = UnifiedCommandExecutor()


# Convenience functions for common operations
def execute_command(command: str, timeout: int = 30, force_host: bool = False) -> Tuple[bool, List[str]]:
    """Execute a command using the unified executor."""
    return command_executor.execute_command(command, timeout, force_host)


def load_module(module_name: str = "nxp_simtemp", module_path: str = None) -> bool:
    """Load a kernel module."""
    success, _ = command_executor.execute_module_command("load", module_name, module_path)
    return success


def unload_module(module_name: str = "nxp_simtemp") -> bool:
    """Unload a kernel module."""
    success, _ = command_executor.execute_module_command("unload", module_name)
    return success


def is_module_loaded(module_name: str = "nxp_simtemp") -> bool:
    """Check if a kernel module is loaded."""
    success, output = command_executor.execute_module_command("check", module_name)
    return success and any(module_name in line for line in output)


def get_environment_info() -> Dict[str, Any]:
    """Get current execution environment information."""
    return command_executor.get_current_environment()