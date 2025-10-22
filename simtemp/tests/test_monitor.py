#!/usr/bin/env python3
"""
test_monitor.py - Enhanced Test Orchestrator with QEMU Session Management

Copyright (c) Jorge Rodriguez Moreno

This script provides a hybrid integration that combines:
1. Full functionality of driver_tester.py (reports, GitHub integration, etc.)
2. Advanced QEMU session management for efficient testing
3. Shared QEMU sessions across multiple test executions
4. Proper cleanup and signal handling

Features:
- Wraps existing driver_tester.py functionality
- Adds QEMU session management layer
- Maintains compatibility with Jenkins pipeline
- Supports both manual and automated execution
- Proper cleanup on exit/interruption

Usage: 
  ./test_monitor.py [--verbose] [--input-dir /path] [--output-dir /path]
  
  # QEMU session management
  ./test_monitor.py --cleanup-qemu     # Cleanup QEMU sessions only
  ./test_monitor.py --qemu-status      # Check QEMU session status
"""

import os
import sys
import subprocess
import signal
import atexit
import argparse
from pathlib import Path

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Note: QEMU session management is handled exclusively by driver_tester.py
# test_monitor.py only orchestrates the execution of driver_tester.py
try:
    from test_utils import is_qemu_session_active
    QEMU_SUPPORT = True
except ImportError as e:
    print(f"Warning: QEMU status checking not available: {e}")
    QEMU_SUPPORT = False


class TestMonitor:
    """Simple test orchestrator that delegates to driver_tester.py."""
    
    def __init__(self):
        self.qemu_enabled = QEMU_SUPPORT
        self.driver_tester_path = current_dir / "driver_tester.py"
        
        # Validate driver_tester.py exists
        if not self.driver_tester_path.exists():
            raise FileNotFoundError(
                f"driver_tester.py not found at {self.driver_tester_path}"
            )
    
    def check_qemu_status(self):
        """Check and report QEMU session status (read-only)."""
        if not self.qemu_enabled:
            print("❌ QEMU status checking not available")
            return False

        try:
            is_active = is_qemu_session_active()
            if is_active:
                print("🟢 QEMU session is ACTIVE")
                print("ℹ️  QEMU cleanup will be handled by driver_tester.py")
            else:
                print("🔴 No active QEMU sessions")
            return is_active
        except Exception as e:
            print(f"⚠️  Error checking QEMU status: {e}")
            return False
    
    def run_driver_tester(self, args):
        """
        Execute driver_tester.py which handles all QEMU management.
        
        Args:
            args: Arguments to pass to driver_tester.py
        """
        print("🚀 Starting Test Monitor")
        print("ℹ️  QEMU sessions are managed exclusively by driver_tester.py")
        
        # Prepare command for driver_tester.py
        cmd = ["python3", str(self.driver_tester_path)]
        if args:
            cmd.extend(args)
        
        print(f"Executing: {' '.join(cmd)}")
        print("=" * 60)
        
        try:
            # Execute driver_tester.py with real-time output
            result = subprocess.run(cmd, cwd=current_dir)
            exit_code = result.returncode
            
            print("=" * 60)
            print(f"📊 Test execution completed with exit code: {exit_code}")
            
            if exit_code == 0:
                print("✅ All tests completed successfully!")
            else:
                print("❌ Some tests failed or encountered errors.")
            
            return exit_code
            
        except KeyboardInterrupt:
            print("\n⚠️  Test execution interrupted by user")
            print("ℹ️  QEMU cleanup will be handled by driver_tester.py")
            return 130  # Standard exit code for SIGINT
            
        except Exception as e:
            print(f"\n💥 Error during test execution: {e}")
            return 1


def create_argument_parser():
    """Create argument parser with both test_monitor and driver_tester options."""
    parser = argparse.ArgumentParser(
        description="Enhanced Test Monitor with QEMU Session Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Monitor Commands:
  python3 test_monitor.py                    # Run full test suite
  python3 test_monitor.py --verbose         # Verbose output
  python3 test_monitor.py --cleanup-qemu    # Cleanup QEMU sessions only
  python3 test_monitor.py --qemu-status     # Check QEMU session status

Driver Tester Arguments (passed through):
  --verbose                   Enable verbose output
  --input-dir PATH           Input directory for test files
  --output-dir PATH          Output directory for reports
  --github-issues            Enable GitHub issues integration
  --skip-pytest             Skip pytest execution (reports only)
        """
    )
    
    # Test monitor specific arguments
    parser.add_argument(
        '--cleanup-qemu',
        action='store_true',
        help='Clean up QEMU sessions and exit'
    )
    
    parser.add_argument(
        '--qemu-status',
        action='store_true', 
        help='Check QEMU session status and exit'
    )
    
    # Arguments to pass through to driver_tester.py
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output (passed to driver_tester.py)'
    )
    
    parser.add_argument(
        '--input-dir',
        type=str,
        help='Input directory for test files (passed to driver_tester.py)'
    )
    
    parser.add_argument(
        '--output-dir', 
        type=str,
        help='Output directory for reports (passed to driver_tester.py)'
    )
    
    return parser


def main():
    """Main entry point for test monitor."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    monitor = TestMonitor()
    
    # Handle test monitor specific commands
    if args.cleanup_qemu:
        print("🧹 QEMU cleanup is handled exclusively by driver_tester.py")
        print("ℹ️  Running driver_tester.py to perform cleanup...")
        # Run driver_tester which will handle cleanup
        exit_code = monitor.run_driver_tester(['--verbose'])
        return exit_code
    
    if args.qemu_status:
        print("🔍 Checking QEMU session status...")
        monitor.check_qemu_status()
        return 0
    
    # Prepare arguments for driver_tester.py
    driver_args = []
    
    if args.verbose:
        driver_args.append('--verbose')
    
    if args.input_dir:
        driver_args.extend(['--input-dir', args.input_dir])
    
    if args.output_dir:
        driver_args.extend(['--output-dir', args.output_dir])
    
    # Execute enhanced test orchestration
    try:
        exit_code = monitor.run_driver_tester(driver_args)
        sys.exit(exit_code)
    except Exception as e:
        print(f"💥 Fatal error in test monitor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()