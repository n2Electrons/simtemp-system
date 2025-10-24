#!/usr/bin/env python3
"""
QEMU Guest Command Utility

This script allows sending commands to the guest system (ARM emulated) of
active QEMU sessions using the existing functionality from test_utils.py.

Usage:
    # Execute command in guest
    python3 qemu_guest_cmd.py --pid <PID> --command "lsmod"

    # Execute command with custom timeout
    python3 qemu_guest_cmd.py --pid <PID> --command "insmod /tmp/prebuild/simtemp-driver/nxp_simtemp.ko" --timeout 10

    # Open interactive shell in guest
    python3 qemu_guest_cmd.py --pid <PID> --interactive
"""

import sys
import os
import argparse
import json
import glob

# Add tests directory to path to import test_utils
# From simtemp/scripts/dev-cli/ -> simtemp/tests/
# Go up to simtemp/ and then to tests/
script_dir = os.path.dirname(__file__)  # dev-cli/
scripts_dir = os.path.dirname(script_dir)  # scripts/
simtemp_dir = os.path.dirname(scripts_dir)  # simtemp/
tests_dir = os.path.join(simtemp_dir, 'tests')  # simtemp/tests/
sys.path.insert(0, tests_dir)

try:
    from test_ucommand_exec import execute_command, set_global_qemu_pid, QemuSshCommandExecutor
except ImportError as e:
    print(f"Error: Could not import test_ucommand_exec: {e}")
    print("Make sure to run this script from simtemp-system project directory")
    sys.exit(1)


def is_process_running(pid):
    """Verifica si un proceso está ejecutándose."""
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


def execute_guest_command(pid: int, command: str, timeout: int = 10):
    """
    Execute a command in QEMU guest using test_utils.
    
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
    
    # Set global PID in test_utils to use correct session
    set_global_qemu_pid(pid)
    
    print(f"Executing command in guest (PID {pid}): {command}")
    
    try:
        success, output = execute_command(command, timeout)
        return success, output
    except Exception as e:
        print(f"Error executing command: {e}")
        return False, []


def interactive_guest_shell(pid: int):
    """
    Open an interactive shell to send commands to guest.
    
    Args:
        pid: PID of QEMU session
    """
    sessions = find_active_qemu_sessions()
    
    if pid not in sessions:
        print(f"Error: No active QEMU session found with PID {pid}")
        return
    
    session_data = sessions[pid]
    print(f"Interactive shell for QEMU guest (PID {pid})")
    print(f"Session type: {session_data.get('session_type', 'unknown')}")
    print(f"Test: {session_data.get('test_name', 'unknown')}")
    print()
    print("Useful commands:")
    print("  lsmod                                           - Loaded modules")
    print("  insmod /tmp/prebuild/simtemp-driver/nxp_simtemp.ko - Load simtemp")
    print("  rmmod nxp_simtemp                               - Unload module")
    print("  ls /sys/bus/platform/drivers/ | grep nxp       - Verify driver")
    print("  dmesg | tail -10                                - Recent kernel msg")
    print("  cat /proc/modules | grep nxp                    - Module info")
    print()
    print("Type 'quit' or 'exit' to leave, Ctrl+C to interrupt")
    print()
    
    # Set global PID
    set_global_qemu_pid(pid)
    
    try:
        while True:
            try:
                command = input("guest# ").strip()
                
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not command:
                    continue
                
                success, output = execute_command(command, timeout=15)
                
                if success:
                    for line in output:
                        print(line)
                else:
                    print("Error: Command failed or timeout")
                    if output:
                        for line in output:
                            print(f"  {line}")
                            
            except KeyboardInterrupt:
                print("\\nInterrupted by user")
                break
                
    except EOFError:
        print("\\nExiting...")


def main():
    parser = argparse.ArgumentParser(
        description="Utility to send commands to guest of active QEMU sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--pid', type=int, required=True,
                       help='PID of QEMU session')
    
    parser.add_argument('--command', type=str,
                       help='Command to execute in guest')
    
    parser.add_argument('--timeout', type=int, default=10,
                       help='Timeout in seconds (default: 10)')
    
    parser.add_argument('--interactive', action='store_true',
                       help='Open interactive guest shell')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_guest_shell(args.pid)
    elif args.command:
        success, output = execute_guest_command(args.pid, args.command, args.timeout)
        
        if success:
            for line in output:
                print(line)
            sys.exit(0)
        else:
            print("Error: Command failed")
            for line in output:
                print(f"  {line}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()