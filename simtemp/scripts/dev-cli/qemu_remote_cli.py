#!/usr/bin/env python3
"""
QEMU Remote CLI - Command execution via telnet interface
=======================================================

This module provides remote command line interface for QEMU instances
using telnet connection instead of SSH. It's designed for embedded 
systems that don't have SSH servers available.

Features:
- Automatic connection management
- Command execution with timeout
- Output parsing and error handling
- Session persistence for multiple commands
- Compatible with busybox telnetd

Usage Examples:
    from qemu_remote_cli import QemuRemoteCLI
    
    # Connect to QEMU
    cli = QemuRemoteCLI(host='127.0.0.1', port=2323)
    
    # Execute single command
    result = cli.execute('ls -la')
    print(result.output)
    
    # Execute multiple commands
    with cli.session() as session:
        session.execute('cd /tmp')
        result = session.execute('pwd')
        print(result.output)
"""

import telnetlib
import time
import re
import socket
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, List, Union
import json
import os


@dataclass
class CommandResult:
    """Result of a remote command execution."""
    command: str
    output: str
    exit_code: Optional[int] = None
    success: bool = True
    error_message: str = ""
    execution_time: float = 0.0


class QemuRemoteCLI:
    """
    Remote CLI interface for QEMU instances via telnet.
    
    This class manages telnet connections to QEMU instances and provides
    methods for executing commands remotely.
    """
    
    def __init__(self, host='127.0.0.1', port=2323, timeout=10):
        """
        Initialize QEMU Remote CLI interface.
        
        Args:
            host (str): QEMU host IP address (default: 127.0.0.1)
            port (int): Telnet port for QEMU access (default: 2323)
            timeout (int): Connection and command timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tn = None
        self.connected = False
        self.session_id = None
        
        # Command prompt pattern for busybox shell
        self.prompt_pattern = rb'# $|#$|\$ $|\$$'
        
    def connect(self) -> bool:
        """
        Establish telnet connection to QEMU.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            print(f"Connecting to QEMU at {self.host}:{self.port}...")
            
            # Create telnet connection
            self.tn = telnetlib.Telnet(self.host, self.port, timeout=self.timeout)
            
            # Wait for initial prompt/output
            time.sleep(1)
            
            # Send a newline with proper telnet line ending to get prompt
            self.tn.write(b'\r\n')
            time.sleep(0.5)
            
            # Try to read initial output
            try:
                initial_output = self.tn.read_very_eager().decode('utf-8', errors='ignore')
                print(f"Initial QEMU output: {repr(initial_output)}")
            except Exception as e:
                print(f"Note: Could not read initial output: {e}")
            
            self.connected = True
            self.session_id = f"qemu_session_{int(time.time())}"
            
            print(f"✅ Connected to QEMU telnet interface")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to QEMU: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close telnet connection."""
        if self.tn:
            try:
                self.tn.close()
                print("✅ Disconnected from QEMU")
            except Exception as e:
                print(f"Note: Error during disconnect: {e}")
            finally:
                self.tn = None
                self.connected = False
                self.session_id = None
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        if not self.connected or not self.tn:
            return False
        
        try:
            # Try to send a simple command with proper line ending to check connection
            self.tn.write(b'\r\n')
            return True
        except Exception:
            self.connected = False
            return False
    
    def execute(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        """
        Execute a command on remote QEMU instance.
        
        Args:
            command (str): Command to execute
            timeout (int, optional): Command timeout in seconds
            
        Returns:
            CommandResult: Command execution result
        """
        if timeout is None:
            timeout = self.timeout
        
        start_time = time.time()
        
        try:
            if not self.is_connected():
                if not self.connect():
                    return CommandResult(
                        command=command,
                        output="",
                        success=False,
                        error_message="Failed to connect to QEMU"
                    )
            
            print(f"🔧 Executing command: {command}")
            
            # Clear any pending output
            try:
                self.tn.read_very_eager()
            except Exception:
                pass
            
            # Send command with proper telnet line ending (CRLF)
            command_bytes = f"{command}\r\n".encode('utf-8')
            self.tn.write(command_bytes)
            
            # Wait for command execution and collect output
            time.sleep(1.0)  # Give command more time to start
            
            output_lines = []
            end_time = start_time + timeout
            consecutive_empty_reads = 0
            
            while time.time() < end_time:
                try:
                    # Read available output
                    data = self.tn.read_very_eager()
                    if data:
                        text = data.decode('utf-8', errors='ignore')
                        output_lines.append(text)
                        consecutive_empty_reads = 0
                        print(f"📥 Received: {repr(text)}")  # Debug output
                        
                        # Check if we have a complete response
                        # Look for prompt or command completion
                        if re.search(self.prompt_pattern, data):
                            print("🔍 Found prompt pattern, stopping")
                            break
                    else:
                        consecutive_empty_reads += 1
                        if consecutive_empty_reads > 20:  # Stop after many empty reads
                            print("🔍 Too many empty reads, stopping")
                            break
                        time.sleep(0.2)
                        
                except Exception as e:
                    print(f"Error reading output: {e}")
                    break
            
            # Combine all output
            full_output = ''.join(output_lines)
            
            # Clean up output (remove command echo and prompts)
            cleaned_output = self._clean_output(full_output, command)
            
            execution_time = time.time() - start_time
            
            result = CommandResult(
                command=command,
                output=cleaned_output,
                success=True,
                execution_time=execution_time
            )
            
            print(f"✅ Command completed in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Command execution failed: {e}"
            print(f"❌ {error_msg}")
            
            return CommandResult(
                command=command,
                output="",
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )
    
    def _clean_output(self, raw_output: str, command: str) -> str:
        """
        Clean command output by removing echoed command and prompts.
        
        Args:
            raw_output (str): Raw output from telnet
            command (str): Original command that was executed
            
        Returns:
            str: Cleaned output
        """
        lines = raw_output.split('\n')
        cleaned_lines = []
        
        # Skip lines that contain the command echo
        skip_next = False
        for line in lines:
            line = line.strip()
            
            # Skip empty lines at the beginning
            if not line and not cleaned_lines:
                continue
                
            # Skip command echo
            if command in line and len(cleaned_lines) == 0:
                continue
                
            # Skip prompt lines
            if re.match(r'^[#\$]\s*$', line):
                continue
                
            # Skip lines that are just prompts
            if line in ['#', '$', '# ', '$ ']:
                continue
            
            cleaned_lines.append(line)
        
        # Join lines and remove trailing empty lines
        result = '\n'.join(cleaned_lines).strip()
        return result
    
    @contextmanager
    def session(self):
        """
        Context manager for persistent session.
        
        Usage:
            with cli.session() as session:
                session.execute('cd /tmp')
                result = session.execute('pwd')
        """
        if not self.connect():
            raise ConnectionError("Failed to establish QEMU connection")
        
        try:
            yield self
        finally:
            self.disconnect()
    
    def execute_multiple(self, commands: List[str], timeout: Optional[int] = None) -> List[CommandResult]:
        """
        Execute multiple commands in sequence.
        
        Args:
            commands (List[str]): List of commands to execute
            timeout (int, optional): Timeout per command
            
        Returns:
            List[CommandResult]: Results for each command
        """
        results = []
        
        with self.session():
            for command in commands:
                result = self.execute(command, timeout)
                results.append(result)
                
                # Stop on first failure
                if not result.success:
                    break
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test QEMU connection with a simple command.
        
        Returns:
            bool: True if connection test successful
        """
        try:
            result = self.execute('echo "connection_test"', timeout=5)
            return result.success and 'connection_test' in result.output
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


def get_qemu_connection_info():
    """
    Get QEMU connection information from session marker.
    
    Returns:
        tuple: (host, port, connection_type) or (None, None, None) if no active session
        connection_type can be 'socket' or 'telnet'
    """
    marker_path = '/tmp/qemu_session_active.marker'
    
    if not os.path.exists(marker_path):
        return None, None, None
    
    try:
        with open(marker_path, 'r') as f:
            data = json.load(f)
        
        # Prefer socket connection if available
        if 'socket_address' in data:
            socket_address = data['socket_address']
            host, port = socket_address.split(':')
            return host, int(port), 'socket'
        
        # Fall back to telnet connection
        telnet_address = data.get('telnet_address', '127.0.0.1:2323')
        host, port = telnet_address.split(':')
        return host, int(port), 'telnet'
        
    except Exception as e:
        print(f"Error reading QEMU session info: {e}")
        return None, None, None


def create_qemu_cli():
    """
    Create QEMU CLI instance with automatic connection detection.
    
    Returns:
        QemuRemoteCLI: Configured CLI instance or None if no QEMU session
    """
    host, port, connection_type = get_qemu_connection_info()
    
    if host is None or port is None:
        print("❌ No active QEMU session found")
        return None
    
    print(f"🔧 Creating QEMU CLI for {host}:{port} ({connection_type})")
    return QemuRemoteCLI(host=host, port=port)


# CLI interface for command line usage
def main():
    """Command line interface for QEMU remote CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description='QEMU Remote CLI via Telnet')
    parser.add_argument('--host', default='127.0.0.1', help='QEMU host')
    parser.add_argument('--port', type=int, default=2323, help='Telnet port')
    parser.add_argument('--test', action='store_true', help='Test connection')
    parser.add_argument('command', nargs='*', help='Command to execute')
    
    args = parser.parse_args()
    
    # Auto-detect QEMU connection if no explicit host/port
    if args.host == '127.0.0.1' and args.port == 2323:
        detected_host, detected_port, connection_type = get_qemu_connection_info()
        if detected_host and detected_port:
            args.host = detected_host
            args.port = detected_port
            print(f"🔧 Auto-detected QEMU at {args.host}:{args.port} ({connection_type})")
    
    cli = QemuRemoteCLI(host=args.host, port=args.port)
    
    if args.test:
        success = cli.test_connection()
        print(f"Connection test: {'✅ PASSED' if success else '❌ FAILED'}")
        return 0 if success else 1
    
    if not args.command:
        print("Error: No command specified")
        return 1
    
    command = ' '.join(args.command)
    result = cli.execute(command)
    
    if result.success:
        print(result.output)
        return 0
    else:
        print(f"Error: {result.error_message}")
        return 1


if __name__ == '__main__':
    exit(main())