#!/usr/bin/env python3
"""
SimTemp Configuration Client
Copyright (c) 2025 Jorge Rodriguez Moreno

CLI client to configure SimTemp sensor in QEMU via socket.
Connects to port 4445 (QEMU socket) to send configuration commands.

Usage:
    python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --get-config
    python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --set-sampling 200
    python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --set-threshold 35000
"""

import sys
import time
import socket
import argparse
from typing import Optional, Dict, Any


class SimTempConfigClient:
    """Client to configure SimTemp via TCP socket"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 4445, timeout: int = 5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        
    def connect(self) -> bool:
        """Connect to SimTemp sensor"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            print(f"✓ Connected to SimTemp sensor at {self.host}:{self.port}")
            
            # Read welcome message if available
            try:
                welcome = self.socket.recv(1024).decode('ascii', errors='ignore')
                if welcome.strip():
                    print(f"Sensor response: {welcome.strip()}")
            except socket.timeout:
                pass  # No welcome message, that's fine
            
            return True
            
        except Exception as e:
            print(f"✗ Error connecting to {self.host}:{self.port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from sensor"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send_command(self, command: str) -> Optional[str]:
        """Send command and receive response"""
        if not self.socket:
            print("✗ No active connection")
            return None
        
        try:
            # Send command with terminator
            cmd_bytes = f"{command}\r\n".encode('ascii')
            self.socket.send(cmd_bytes)
            
            # Receive response (may include "simtemp>" prompt)
            response = self.socket.recv(1024).decode('ascii', errors='ignore')
            
            # Clean response by removing prompt
            lines = response.strip().split('\n')
            clean_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.endswith('simtemp>') and line != 'simtemp>':
                    clean_lines.append(line)
            
            return '\n'.join(clean_lines) if clean_lines else None
            
        except Exception as e:
            print(f"✗ Error sending command '{command}': {e}")
            return None
    
    def get_temperature(self) -> Optional[float]:
        """Get current temperature"""
        response = self.send_command("GET_TEMP")
        if response and response.startswith("TEMP:"):
            try:
                # Parse "TEMP: 25.50°C"
                temp_str = response.split(":")[1].strip().replace("°C", "")
                return float(temp_str)
            except (ValueError, IndexError):
                pass
        return None
    
    def set_temperature(self, temp_celsius: float) -> bool:
        """Set temperature"""
        response = self.send_command(f"SET_TEMP {temp_celsius:.2f}")
        return response and response.startswith("OK:")
    
    def get_sampling_period(self) -> Optional[int]:
        """Get sampling period in ms"""
        response = self.send_command("GET_SAMPLING")
        if response and response.startswith("SAMPLING:"):
            try:
                # Parse "SAMPLING: 100 ms"
                ms_str = response.split(":")[1].strip().replace(" ms", "")
                return int(ms_str)
            except (ValueError, IndexError):
                pass
        return None
    
    def set_sampling_period(self, period_ms: int) -> bool:
        """Set sampling period in ms"""
        response = self.send_command(f"SET_SAMPLING {period_ms}")
        return response and response.startswith("OK:")
    
    def get_threshold(self) -> Optional[int]:
        """Get threshold in milli-degrees Celsius"""
        response = self.send_command("GET_THRESHOLD")
        if response and response.startswith("THRESHOLD:"):
            try:
                # Parse "THRESHOLD: 45.0°C (45000 mC)"
                parts = response.split("(")
                if len(parts) > 1:
                    mc_str = parts[1].replace(" mC)", "").strip()
                    return int(mc_str)
            except (ValueError, IndexError):
                pass
        return None
    
    def set_threshold(self, threshold_mc: int) -> bool:
        """Set threshold in milli-degrees Celsius"""
        response = self.send_command(f"SET_THRESHOLD {threshold_mc}")
        return response and response.startswith("OK:")
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get complete sensor status"""
        response = self.send_command("STATUS")
        if not response or not response.startswith("STATUS:"):
            return None
        
        # Parse "STATUS: OK, Temp=25.0°C, Sampling=100ms, Threshold=45.0°C, Uptime=120s, Clients=1"
        status = {}
        try:
            parts = response.split("STATUS:")[1].strip()
            for part in parts.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Clean values
                    if key == "Temp":
                        status["temperature_c"] = float(value.replace("°C", ""))
                    elif key == "Sampling":
                        status["sampling_ms"] = int(value.replace("ms", ""))
                    elif key == "Threshold":
                        status["threshold_c"] = float(value.replace("°C", ""))
                    elif key == "Uptime":
                        status["uptime_s"] = int(value.replace("s", ""))
                    elif key == "Clients":
                        status["clients"] = int(value)
                    else:
                        status[key.lower()] = value
        except Exception as e:
            print(f"Warning: Error parsing status: {e}")
        
        return status
    
    def get_help(self) -> Optional[str]:
        """Get command help"""
        return self.send_command("HELP")


def print_config_table(status: Dict[str, Any]):
    """Print configuration in table format"""
    print("\n=== SimTemp Sensor Configuration ===")
    print(f"Current temperature:   {status.get('temperature_c', 'N/A')} °C")
    print(f"Sampling period:       {status.get('sampling_ms', 'N/A')} ms")
    print(f"Temperature threshold: {status.get('threshold_c', 'N/A')} °C")
    print(f"Uptime:                {status.get('uptime_s', 'N/A')} s")
    print(f"Connected clients:     {status.get('clients', 'N/A')}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="SimTemp Configuration Client - Configure sensor via TCP socket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --host 127.0.0.1 --port 4445 --get-config
  %(prog)s --host 127.0.0.1 --port 4445 --set-sampling 200
  %(prog)s --host 127.0.0.1 --port 4445 --set-threshold 35000
  %(prog)s --host 127.0.0.1 --port 4445 --set-temp 30.5
        """
    )
    
    # Connection parameters
    parser.add_argument('--host', default='127.0.0.1',
                       help='SimTemp sensor host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=4445,
                       help='SimTemp sensor port (default: 4445)')
    parser.add_argument('--timeout', type=int, default=5,
                       help='Connection timeout in seconds (default: 5)')
    
    # Configuration commands
    config_group = parser.add_argument_group('configuration commands')
    config_group.add_argument('--get-config', action='store_true',
                             help='Get current sensor configuration')
    config_group.add_argument('--set-sampling', type=int, metavar='MS',
                             help='Set sampling period in milliseconds')
    config_group.add_argument('--set-threshold', type=int, metavar='MILLIC',
                             help='Set threshold in milli-degrees Celsius')
    config_group.add_argument('--set-temp', type=float, metavar='CELSIUS',
                             help='Set current temperature in Celsius')
    
    # Information commands
    info_group = parser.add_argument_group('information commands')
    info_group.add_argument('--get-temp', action='store_true',
                           help='Get current temperature')
    info_group.add_argument('--get-status', action='store_true',
                           help='Get detailed sensor status')
    info_group.add_argument('--help-commands', action='store_true',
                           help='Get available sensor commands')
    
    args = parser.parse_args()
    
    # Create client and connect
    client = SimTempConfigClient(args.host, args.port, args.timeout)
    
    try:
        if not client.connect():
            return 1
        
        # Handle commands
        if args.get_config or args.get_status:
            status = client.get_status()
            if status:
                print_config_table(status)
            else:
                print("✗ Could not get sensor configuration")
                return 1
        
        if args.set_sampling is not None:
            if client.set_sampling_period(args.set_sampling):
                print(f"✓ Sampling period set to {args.set_sampling} ms")
            else:
                print("✗ Error setting sampling period")
                return 1
        
        if args.set_threshold is not None:
            temp_c = args.set_threshold / 1000.0
            if client.set_threshold(args.set_threshold):
                print(f"✓ Threshold set to {temp_c:.1f}°C ({args.set_threshold} mC)")
            else:
                print("✗ Error setting threshold")
                return 1
        
        if args.set_temp is not None:
            if client.set_temperature(args.set_temp):
                print(f"✓ Temperature set to {args.set_temp}°C")
            else:
                print("✗ Error setting temperature")
                return 1
        
        if args.get_temp:
            temp = client.get_temperature()
            if temp is not None:
                print(f"Current temperature: {temp}°C")
            else:
                print("✗ Could not get temperature")
        
        if args.help_commands:
            help_text = client.get_help()
            if help_text:
                print("Available sensor commands:")
                print(help_text)
            else:
                print("✗ Could not get help")
        
        # If no specific action, show config by default
        if not any([args.get_config, args.get_status, args.set_sampling, 
                   args.set_threshold, args.set_temp, args.get_temp, 
                   args.help_commands]):
            status = client.get_status()
            if status:
                print_config_table(status)
            else:
                print("Usage: python3 simtemp_config_client.py --help")
        
    except KeyboardInterrupt:
        print("\n✓ Interrupted by user")
    finally:
        client.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())