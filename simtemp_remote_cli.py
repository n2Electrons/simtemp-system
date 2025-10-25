#!/usr/bin/env python3
"""
SimTemp Remote CLI - SSH-based Driver Configuration Tool
Copyright (c) 2025 Jorge Rodriguez Moreno

CLI remoto que utiliza SSH para interactuar con el driver SimTemp:
- Configurar sample rate via /sys/devices/platform/simtemp/sampling_ms
- Configurar threshold via /sys/devices/platform/simtemp/threshold_mC
- Leer continuamente /dev/simtemp0

Utiliza la implementación SSH de test_utils.py para comunicarse con QEMU.
"""

import sys
import os
import time
import argparse
from typing import Optional, Tuple, List

# Add the simtemp tests directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simtemp', 'tests'))

try:
    from test_utils import (start_qemu_and_wait_for_boot, wait_for_ssh_ready,
                            execute_ssh_command, cleanup_qemu_processes)
except ImportError as e:
    print(f"Error importing test_utils: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class SimTempRemoteCLI:
    """CLI remoto para configurar SimTemp via SSH"""
    
    def __init__(self, ssh_port=2222, auto_start_qemu=True):
        """Initialize the remote CLI with SSH configuration."""
        self.ssh_port = ssh_port
        self.auto_start_qemu = auto_start_qemu
        self.sysfs_base = "/sys/devices/platform/simtemp"
        self.device_path = "/dev/simtemp0"
        
        if auto_start_qemu:
            print("[INFO] Starting QEMU with SSH support...")
            qemu_process, socket_port = start_qemu_and_wait_for_boot()
            self.qemu_process = qemu_process
            self.socket_port = socket_port
            print(f"[INFO] QEMU started, socket port: {socket_port}")
            
            # Wait for SSH to be ready
            print("[INFO] Waiting for SSH service...")
            wait_for_ssh_ready(ssh_port)
            print(f"[INFO] SSH ready on port {ssh_port}")
        else:
            self.qemu_process = None
            self.socket_port = None
            print(f"[INFO] Using existing SSH connection on port {ssh_port}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n[INFO] Received shutdown signal, cleaning up...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up resources"""
        if self.qemu_process and self.auto_start_qemu:
            print("[INFO] Cleaning up QEMU process...")
            try:
                self.qemu_process.terminate()
                time.sleep(2)
                if self.qemu_process.poll() is None:
                    self.qemu_process.kill()
            except Exception as e:
                print(f"[WARNING] Error during QEMU cleanup: {e}")
            
            cleanup_qemu_processes(force_kill=True)
    
    def execute_command(self, command: str) -> Tuple[bool, List[str]]:
        """Execute SSH command wrapper"""
        return execute_ssh_command(command, self.ssh_port)
    
    def read_sysfs_attribute(self, attr_name: str) -> Optional[str]:
        """Read sysfs attribute value"""
        path = f"{self.sysfs_base}/{attr_name}"
        success, output = self.execute_command(f"cat {path} 2>/dev/null")
        
        if success and output:
            return output[0].strip()
        return None
    
    def write_sysfs_attribute(self, attr_name: str, value: str) -> bool:
        """Write sysfs attribute value"""
        path = f"{self.sysfs_base}/{attr_name}"
        success, output = self.execute_command(f"echo '{value}' > {path}")
        return success
    
    def get_sample_rate(self) -> Optional[int]:
        """Get current sampling rate in milliseconds"""
        value = self.read_sysfs_attribute("sampling_ms")
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return None
    
    def set_sample_rate(self, rate_ms: int) -> bool:
        """Set sampling rate in milliseconds"""
        if rate_ms < 1 or rate_ms > 60000:
            print(f"[ERROR] Invalid sample rate: {rate_ms}ms "
                  f"(valid range: 1-60000)")
            return False
        
        success = self.write_sysfs_attribute("sampling_ms", str(rate_ms))
        if success:
            print(f"[INFO] Sample rate set to {rate_ms}ms")
        else:
            print(f"[ERROR] Failed to set sample rate to {rate_ms}ms")
        return success
    
    def get_threshold(self) -> Optional[int]:
        """Get current threshold in milli-degrees Celsius"""
        value = self.read_sysfs_attribute("threshold_mC")
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return None
    
    def set_threshold(self, threshold_mc: int) -> bool:
        """Set threshold in milli-degrees Celsius"""
        if threshold_mc < -50000 or threshold_mc > 150000:
            temp_c = threshold_mc / 1000.0
            print(f"[ERROR] Invalid threshold: {temp_c}°C "
                  f"(valid range: -50°C to 150°C)")
            return False
        
        success = self.write_sysfs_attribute("threshold_mC", str(threshold_mc))
        if success:
            temp_c = threshold_mc / 1000.0
            print(f"[INFO] Threshold set to {temp_c}°C ({threshold_mc}mC)")
        else:
            temp_c = threshold_mc / 1000.0
            print(f"[ERROR] Failed to set threshold to {temp_c}°C")
        return success
    
    def show_current_config(self) -> bool:
        """Show current driver configuration"""
        print("\n=== SimTemp Driver Configuration ===")
        
        # Get sample rate
        sample_rate = self.get_sample_rate()
        if sample_rate is not None:
            print(f"Sample Rate: {sample_rate}ms")
        else:
            print("Sample Rate: Unable to read")
        
        # Get threshold
        threshold = self.get_threshold()
        if threshold is not None:
            temp_c = threshold / 1000.0
            print(f"Threshold: {temp_c}°C ({threshold}mC)")
        else:
            print("Threshold: Unable to read")
        
        # Check if device exists
        success, output = self.execute_command(f"ls -la {self.device_path}")
        if success:
            print(f"Device: {self.device_path} exists")
        else:
            print(f"Device: {self.device_path} not found")
        
        # Check if driver is loaded
        success, output = self.execute_command("lsmod | grep nxp_simtemp")
        if success and output:
            print(f"Driver: {output[0]}")
        else:
            print("Driver: nxp_simtemp not loaded")
        
        print("=====================================\n")
        return True
    
    def read_temperature_continuous(self, duration: int = 0,
                                    sample_count: int = 0) -> bool:
        """Read temperature continuously from /dev/simtemp0"""
        print(f"Reading from {self.device_path}", end="")
        if duration > 0:
            print(f" for {duration}s", end="")
        if sample_count > 0:
            print(f" ({sample_count} samples)", end="")
        print(" - Press Ctrl+C to stop")
        
        self.running = True
        samples_read = 0
        start_time = time.time()
        
        try:
            while self.running:
                # Read from device using hexdump for better parsing
                success, output = self.execute_command(
                    f"dd if={self.device_path} bs=20 count=1 2>/dev/null | "
                    f"hexdump -C"
                )
                
                if success and output:
                    # Parse hexdump output - single line format
                    for line in output:
                        if line.strip() and not line.startswith('*'):
                            timestamp = time.strftime("%H:%M:%S")
                            print(f"[{timestamp}] {line.strip()}")
                
                # Alternative: try to read as text
                success, output = self.execute_command(
                    f"timeout 1 cat {self.device_path} 2>/dev/null || "
                    f"echo 'timeout'"
                )
                
                if success and output and output[0] != 'timeout':
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] {output[0]}")
                
                samples_read += 1
                
                # Check termination conditions
                if sample_count > 0 and samples_read >= sample_count:
                    break
                
                if duration > 0 and (time.time() - start_time) >= duration:
                    break
                
                time.sleep(0.1)  # Small delay between reads
                
        except KeyboardInterrupt:
            print(f"\nStopped - read {samples_read} samples")
        except Exception as e:
            print(f"\nError: {e}")
            return False
        
        print(f"Completed - {samples_read} samples total")
        return True
    
    def show_help(self):
        """Show concise help information"""
        print("\n" + "="*50)
        print("🔧 SimTemp Remote CLI - Quick Help")
        print("="*50)
        print("📋 COMMANDS:")
        print("  config        - Show current settings")
        print("  rate <ms>     - Set sample rate (1-60000)")
        print("  thr <°C>      - Set temperature threshold")
        print("  read [sec]    - Read temperature (default: continuous)")
        print("  status        - Show driver status")
        print("  help          - Show this help")
        print("  quit          - Exit CLI")
        print("")
        print("📖 EXAMPLES:")
        print("  rate 500      - Set to 500ms sampling")
        print("  thr 40        - Set threshold to 40°C")
        print("  read 30       - Read for 30 seconds")
        print("="*50 + "\n")
    
    def show_welcome_message(self):
        """Show welcome message and basic commands"""
        print("\n🚀 SimTemp Remote CLI - SSH Driver Configuration")
        print("="*50)
        print("📋 Quick Commands:")
        print("  config       - Show configuration")
        print("  rate <ms>    - Set sample rate")
        print("  thr <°C>     - Set threshold")
        print("  read         - Read temperature")
        print("  help         - Extended help")
        print("  quit         - Exit")
        print("="*50)
        print("💡 Type 'help' for detailed usage information\n")
        print("")
    
    def interactive_mode(self):
        """Interactive CLI mode"""
        self.show_welcome_message()
        
        while True:
            try:
                cmd = input("simtemp> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0].lower() in ['quit', 'exit', 'q']:
                    break
                
                elif cmd[0].lower() in ['help', 'h', '?']:
                    self.show_help()
                
                elif cmd[0].lower() == 'config':
                    self.show_current_config()
                
                elif cmd[0].lower() in ['status', 'stat']:
                    self.show_current_config()  # Same as config for now
                
                elif cmd[0].lower() == 'rate':
                    if len(cmd) < 2:
                        print(" Usage: rate <milliseconds>")
                        print("   Example: rate 500")
                        continue
                    try:
                        rate = int(cmd[1])
                        self.set_sample_rate(rate)
                    except ValueError:
                        print(" Invalid rate value. Must be a number "
                              "(1-60000)")
                
                elif cmd[0].lower() in ['thr', 'threshold', 'thresh']:
                    if len(cmd) < 2:
                        print(" Usage: thr <celsius>")
                        print("   Example: thr 40.5")
                        continue
                    try:
                        temp_c = float(cmd[1])
                        threshold_mc = int(temp_c * 1000)
                        self.set_threshold(threshold_mc)
                    except ValueError:
                        print(" Invalid threshold value. Must be a number "
                              "(-50 to 150)")
                
                elif cmd[0].lower() == 'read':
                    duration = 0
                    count = 0
                    if len(cmd) > 1:
                        try:
                            duration = int(cmd[1])
                        except ValueError:
                            print(" Invalid duration. Must be a number")
                            continue
                    if len(cmd) > 2:
                        try:
                            count = int(cmd[2])
                        except ValueError:
                            print(" Invalid count. Must be a number")
                            continue
                    self.read_temperature_continuous(duration, count)
                
                else:
                    print(f" Unknown command: '{cmd[0]}'")
                    print(" Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n")
                continue  # Don't exit on Ctrl+C, just new prompt
            except EOFError:
                break
        
        print("\n Exiting SimTemp Remote CLI")
        print("Thank you for using SimTemp!")


def main():
    parser = argparse.ArgumentParser(
        description="SimTemp Remote CLI - Interactive Driver Configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default - uses existing SSH)
  %(prog)s
  
  # Interactive mode with auto-start QEMU
  %(prog)s --auto-start
  
  # Show configuration
  %(prog)s --config
  
  # Set sample rate to 500ms
  %(prog)s --set-rate 500
  
  # Set threshold to 40°C
  %(prog)s --set-threshold 40.0
  
  # Read temperature for 30 seconds
  %(prog)s --read --duration 30
  
  # Read 100 samples
  %(prog)s --read --count 100
  
  # Auto-start QEMU for testing
  %(prog)s --auto-start --config
        """
    )
    
    # Connection options
    parser.add_argument('--ssh-port', type=int, default=2222,
                       help='SSH port (default: 2222)')
    parser.add_argument('--auto-start', action='store_true',
                       help='Auto-start QEMU (default: use existing SSH)')
    
    # Actions
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode (default behavior)')
    parser.add_argument('--help-extended', '--help-ext', action='store_true',
                       help='Show extended help and usage examples')
    parser.add_argument('--config', action='store_true',
                       help='Show current configuration')
    parser.add_argument('--set-rate', type=int, metavar='MS',
                       help='Set sample rate in milliseconds')
    parser.add_argument('--set-threshold', type=float, metavar='CELSIUS',
                       help='Set threshold in Celsius')
    parser.add_argument('--read', action='store_true',
                       help='Read temperature continuously')
    parser.add_argument('--duration', type=int, metavar='SECONDS',
                       help='Duration for continuous reading (0=infinite)')
    parser.add_argument('--count', type=int, metavar='SAMPLES',
                       help='Number of samples to read (0=infinite)')
    
    args = parser.parse_args()
    
    # Check for help-extended before creating CLI
    if args.help_extended:
        # Show extended help without starting QEMU
        temp_cli = SimTempRemoteCLI(auto_start_qemu=False)
        temp_cli.show_help()
        return 0
    
    # Create CLI instance
    cli = SimTempRemoteCLI(
        ssh_port=args.ssh_port,
        auto_start_qemu=args.auto_start
    )
    
    try:
        # Execute actions
        if args.config:
            cli.show_current_config()
        
        elif args.set_rate is not None:
            cli.set_sample_rate(args.set_rate)
        
        elif args.set_threshold is not None:
            threshold_mc = int(args.set_threshold * 1000)
            cli.set_threshold(threshold_mc)
        
        elif args.read:
            duration = args.duration or 0
            count = args.count or 0
            cli.read_temperature_continuous(duration, count)
        
        elif args.interactive:
            cli.interactive_mode()
        
        else:
            # Default: interactive mode if no specific action
            cli.interactive_mode()
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1
    
    finally:
        cli.cleanup()


if __name__ == "__main__":
    sys.exit(main())
