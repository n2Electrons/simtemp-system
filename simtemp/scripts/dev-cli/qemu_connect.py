#!/usr/bin/env python3
"""
QEMU Connection Utility

This script allows connecting to active QEMU sessions using the monitor
port to execute commands from an independent process.

Usage:
    # Show active sessions
    python3 qemu_connect.py --list

    # Connect to specific session
    python3 qemu_connect.py --connect <PID>

    # Execute specific command
    python3 qemu_connect.py --command "info version" --pid <PID>

    # Connect and open interactive shell
    python3 qemu_connect.py --interactive --pid <PID>
"""

import json
import os
import sys
import telnetlib
import argparse
import glob
import time
from typing import Dict, List, Optional, Tuple


def find_active_qemu_sessions() -> Dict[int, dict]:
    """
    Search for all active QEMU sessions by reading marker files.
    
    Returns:
        Dict with PID as key and session data as value
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


def is_process_running(pid: int) -> bool:
    """Verify if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def list_active_sessions():
    """List all active QEMU sessions."""
    sessions = find_active_qemu_sessions()
    
    if not sessions:
        print("No active QEMU sessions found.")
        return
    
    print("Active QEMU sessions:")
    print("=" * 80)
    
    for pid, data in sessions.items():
        session_type = data.get('session_type', 'unknown')
        started_at = data.get('started_at', 0)
        started_by = data.get('started_by', 'unknown')
        test_name = data.get('test_name', 'unknown')
        monitor_port = data.get('monitor_port')
        monitor_address = data.get('monitor_address')
        
        # Format time
        if started_at:
            import datetime
            started_time = datetime.datetime.fromtimestamp(started_at)
            time_str = started_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = 'unknown'
        
        print(f"PID: {pid}")
        print(f"  Type: {session_type}")
        print(f"  Started: {time_str}")
        print(f"  By: {started_by}")
        print(f"  Test: {test_name}")
        
        if monitor_port:
            print(f"  Monitor: {monitor_address} (port {monitor_port})")
            print(f"  Connection command: telnet 127.0.0.1 {monitor_port}")
        else:
            print("  Monitor: Not available")
        
        print("-" * 40)


def connect_to_qemu_monitor(pid: int, command: Optional[str] = None,
                           interactive: bool = False) -> bool:
    """
    Connect to QEMU monitor and execute commands.
    
    Args:
        pid: PID of QEMU session
        command: Specific command to execute (optional)
        interactive: If True, open interactive shell
    
    Returns:
        True if connection was successful
    """
    sessions = find_active_qemu_sessions()
    
    if pid not in sessions:
        print(f"Error: No active QEMU session found with PID {pid}")
        return False
    
    session_data = sessions[pid]
    monitor_port = session_data.get('monitor_port')
    
    if not monitor_port:
        print(f"Error: Session {pid} has no monitor port configured")
        return False
    
    try:
        print(f"Connecting to QEMU monitor at 127.0.0.1:{monitor_port}...")
        
        # Establish telnet connection
        tn = telnetlib.Telnet('127.0.0.1', monitor_port, timeout=5)
        
        # Read initial banner
        banner = tn.read_until(b'(qemu) ', timeout=5)
        print(f"Connected to QEMU monitor (PID {pid})")
        
        if command:
            # Execute specific command
            print(f"Executing command: {command}")
            tn.write(command.encode('utf-8') + b'\n')
            
            # Read response
            response = tn.read_until(b'(qemu) ', timeout=10)
            output = response.decode('utf-8', errors='ignore')
            
            # Filter out prompt from the end
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.endswith('(qemu)'):
                    print(line)
            
        elif interactive:
            # Interactive mode
            print("Interactive mode activated. Useful commands:")
            print("  info version    - QEMU information")
            print("  info status     - VM status")
            print("  info cpus       - CPU information")
            print("  help            - Command list")
            print("  quit            - Exit")
            print()
            
            try:
                while True:
                    cmd = input("(qemu) ")
                    if cmd.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    tn.write(cmd.encode('utf-8') + b'\n')
                    response = tn.read_until(b'(qemu) ', timeout=10)
                    output = response.decode('utf-8', errors='ignore')
                    
                    # Show response without prompt
                    lines = output.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.endswith('(qemu)'):
                            print(line)
                            
            except KeyboardInterrupt:
                print("\nExiting interactive mode...")
        
        tn.close()
        return True
        
    except Exception as e:
        print(f"Error connecting to QEMU monitor: {e}")
        return False

def send_qemu_command_to_guest(pid: int, guest_command: str) -> bool:
    """
    Send a command to the guest system through QEMU monitor.
    
    Args:
        pid: PID of QEMU session
        guest_command: Command to execute in guest
    
    Returns:
        True if command was sent successfully
    """
    # To send commands to guest, we need to use the serial console
    # instead of the monitor. This is more complex and requires different approach.
    print("send_qemu_command_to_guest function not yet implemented.")
    print("For guest commands, use existing test_utils.py functionality")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Utility to connect to active QEMU sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--list', action='store_true',
                        help='List all active QEMU sessions')
    
    parser.add_argument('--connect', '--pid', type=int, metavar='PID',
                        help='PID of QEMU session to connect to')
    
    parser.add_argument('--command', type=str,
                        help='Specific command to execute in monitor')
    
    parser.add_argument('--interactive', action='store_true',
                        help='Open interactive monitor shell')
    
    args = parser.parse_args()
    
    if args.list:
        list_active_sessions()
        return
    
    if args.connect:
        if args.command:
            success = connect_to_qemu_monitor(args.connect,
                                              command=args.command)
        elif args.interactive:
            success = connect_to_qemu_monitor(args.connect, interactive=True)
        else:
            # By default, show basic info
            success = connect_to_qemu_monitor(args.connect,
                                              command="info version")
        
        sys.exit(0 if success else 1)
    
    # If no action specified, show help
    parser.print_help()


if __name__ == "__main__":
    main()