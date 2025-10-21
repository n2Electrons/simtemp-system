#!/usr/bin/env python3
"""
Enhanced Test Runner with QEMU Session Management

This script wraps the existing test execution and adds proper QEMU session
management for tests that require QEMU emulation.

Features:
- Automatic QEMU session cleanup on exit
- Shared QEMU sessions across multiple tests
- Proper signal handling for interrupted test runs
- Integration with existing test infrastructure
"""

import os
import sys
import subprocess
import signal
import atexit
from pathlib import Path

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import QEMU session management
from qemu_session_manager import setup_qemu_session_cleanup, manual_cleanup_qemu_sessions


def run_tests_with_qemu_management(test_args=None):
    """
    Run tests with proper QEMU session management.
    
    Args:
        test_args: Additional arguments to pass to pytest
    """
    print("🚀 Starting Enhanced Test Runner with QEMU Session Management")
    
    # Setup QEMU session cleanup handlers
    setup_qemu_session_cleanup()
    
    # Determine test command
    test_cmd = ["python3", "-m", "pytest", "-v"]
    
    if test_args:
        test_cmd.extend(test_args)
    
    # Add default pytest arguments if none provided
    if not test_args:
        test_cmd.extend([
            "--tb=short",  # Shorter traceback format
            "--disable-warnings",  # Reduce noise
            "-x",  # Stop on first failure for faster feedback
            "."  # Run tests in current directory
        ])
    
    print(f"Executing: {' '.join(test_cmd)}")
    
    try:
        # Run the tests
        result = subprocess.run(test_cmd, cwd=current_dir)
        exit_code = result.returncode
        
        print(f"\n📊 Test execution completed with exit code: {exit_code}")
        
        if exit_code == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed.")
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        return 130  # Standard exit code for SIGINT
        
    except Exception as e:
        print(f"\n💥 Error during test execution: {e}")
        return 1
        
    finally:
        # Explicit cleanup (in addition to atexit handlers)
        print("\n🧹 Performing final QEMU session cleanup...")
        manual_cleanup_qemu_sessions()


def main():
    """Main entry point for the enhanced test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enhanced Test Runner with QEMU Session Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_tests_enhanced.py                    # Run all tests
  python3 run_tests_enhanced.py test_f_k1_tc_003.py   # Run specific test
  python3 run_tests_enhanced.py -k "qemu"             # Run tests matching "qemu"
  python3 run_tests_enhanced.py --cleanup-only        # Only cleanup QEMU sessions
        """
    )
    
    parser.add_argument(
        '--cleanup-only',
        action='store_true',
        help='Only perform QEMU session cleanup, do not run tests'
    )
    
    parser.add_argument(
        'pytest_args',
        nargs='*',
        help='Additional arguments to pass to pytest'
    )
    
    args = parser.parse_args()
    
    if args.cleanup_only:
        print("🧹 Cleaning up QEMU sessions only...")
        manual_cleanup_qemu_sessions()
        return 0
    
    # Run tests with QEMU management
    exit_code = run_tests_with_qemu_management(args.pytest_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()