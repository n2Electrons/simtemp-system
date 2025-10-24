#!/usr/bin/env python3
"""
QEMU SSH Command Utility

This script allows sending commands to the QEMU guest via SSH connection.
Much simpler than the simulation approach - uses real SSH to execute
commands in the ARM guest system.

Usage:
    # Execute command in guest via SSH
    python3 qemu_ssh_cmd.py --pid <PID> --command "ls /tmp"

    # Execute command with custom timeout
    python3 qemu_ssh_cmd.py --pid <PID> --command "lsmod" --timeout 10

    # Open interactive SSH shell
    python3 qemu_ssh_cmd.py --pid <PID> --interactive
"""

import sys
import os
import argparse
import json
import glob
import subprocess
import time

def is_process_running(pid):
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def find_active_qemu_sessions():
    """
    Search for all active QEMU sessions by reading marker files.
    """
    sessions = {}
    
    # Search for shared marker
    shared_marker = '/tmp/qemu_session_active.marker'
    if os.path.exists(shared_marker):
        try:
            with open(shared_marker, 'r') as f:
                data = json.load(f)
                pid = data.get('pid')
                if pid and is_process_running(pid):
                    data['session_type'] = 'shared'
                    sessions[pid] = data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Error reading shared marker: {e}")
    
    # Search for private markers
    uid = os.getuid()
    pattern = f"/tmp/qemu_private_session_{uid}_*.json"
    for marker_file in glob.glob(pattern):
        try:
            with open(marker_file, 'r') as f:
                data = json.load(f)
                pid = data.get('pid')
                if pid and is_process_running(pid):
                    sessions[pid] = data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Error reading private marker {marker_file}: {e}")
    
    return sessions


def wait_for_ssh_ready(ssh_port=2222, timeout=30):
    """
    Wait for SSH service to be ready in QEMU guest.
    
    Args:
        ssh_port: SSH port to test
        timeout: Timeout in seconds
    
    Returns:
        bool: True if SSH is ready, False if timeout
    """
    print(f"Waiting for SSH service on port {ssh_port}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Test SSH connection without authentication
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=2',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'LogLevel=QUIET',
                '-p', str(ssh_port),
                'root@127.0.0.1',
                'echo ssh_ready'
            ], capture_output=True, timeout=5)
            
            if result.returncode == 0 or 'ssh_ready' in result.stdout.decode():
                print(f"SSH service ready on port {ssh_port}")
                return True
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
            
        time.sleep(2)
    
    print(f"Timeout waiting for SSH service on port {ssh_port}")
    return False


def execute_ssh_command(pid: int, command: str, timeout: int = 10):
    """
    Execute a command in QEMU guest via SSH.
    
    Args:
        pid: PID of QEMU session
        command: Command to execute in guest
        timeout: Timeout in seconds
    
    Returns:
        Tuple (success, output_lines)
    """
    sessions = find_active_qemu_sessions()
    
    if pid not in sessions:
        print(f"Error: No active QEMU session found with PID {pid}")
        return False, []
    
    session_data = sessions[pid]
    ssh_port = session_data.get('ssh_port', 2222)
    
    print(f"Executing command via SSH (PID {pid}, port {ssh_port}): {command}")
    
    try:
        # Execute SSH command
        result = subprocess.run([
            'ssh', '-o', 'ConnectTimeout=5',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=QUIET',
            '-p', str(ssh_port),
            'root@127.0.0.1',
            command
        ], capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0:
            output_lines = result.stdout.splitlines()
            return True, output_lines
        else:
            error_lines = result.stderr.splitlines()
            print(f"SSH command failed with exit code {result.returncode}")
            return False, error_lines
            
    except subprocess.TimeoutExpired:
        print(f"SSH command timed out after {timeout} seconds")
        return False, ["Command timed out"]
    except Exception as e:
        print(f"Error executing SSH command: {e}")
        return False, [str(e)]


def interactive_ssh_shell(pid: int):
    """
    Open an interactive SSH shell to QEMU guest.
    
    Args:
        pid: PID of QEMU session
    """
    sessions = find_active_qemu_sessions()
    
    if pid not in sessions:
        print(f"Error: No active QEMU session found with PID {pid}")
        return
    
    session_data = sessions[pid]
    ssh_port = session_data.get('ssh_port', 2222)
    
    print(f"Opening interactive SSH shell (PID {pid}, port {ssh_port})")
    print(f"Session type: {session_data.get('session_type', 'unknown')}")
    print(f"Test: {session_data.get('test_name', 'unknown')}")
    print()
    
    # Wait for SSH to be ready
    if not wait_for_ssh_ready(ssh_port):
        print("Error: SSH service not available")
        return
    
    print("Starting interactive SSH session...")
    print("Type 'exit' to leave the SSH session")
    print()
    
    try:
        # Start interactive SSH session
        subprocess.run([
            'ssh', '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-p', str(ssh_port),
            'root@127.0.0.1'
        ])
    except KeyboardInterrupt:
        print("\\nSSH session interrupted")
    except Exception as e:
        print(f"Error in SSH session: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Utility to send commands to QEMU guest via SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--pid', type=int, required=True,
                       help='PID of QEMU session')
    
    parser.add_argument('--command', type=str,
                       help='Command to execute in guest via SSH')
    
    parser.add_argument('--timeout', type=int, default=10,
                       help='Timeout in seconds (default: 10)')
    
    parser.add_argument('--interactive', action='store_true',
                       help='Open interactive SSH shell')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_ssh_shell(args.pid)
    elif args.command:
        success, output = execute_ssh_command(args.pid, args.command, args.timeout)
        
        if success:
            for line in output:
                print(line)
            sys.exit(0)
        else:
            print("Error: SSH command failed")
            for line in output:
                print(f"  {line}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()