#!/usr/bin/env python3
"""
Terminal restoration utility for QEMU tests.

This script can be run directly to restore terminal state
after QEMU processes have corrupted the terminal.

Usage:
    python3 restore_terminal.py
    
Or make it executable and run directly:
    chmod +x restore_terminal.py
    ./restore_terminal.py
"""

import sys
import os

# Add the current directory to path to import test_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from test_utils import restore_terminal, cleanup_qemu_processes
except ImportError as e:
    print(f"Error importing test utilities: {e}")
    sys.exit(1)


def main():
    """Main function to restore terminal and clean up QEMU processes."""
    print("Terminal Restoration Utility")
    print("=" * 40)
    
    # Store original directory
    original_dir = os.getcwd()
    print(f"Current directory: {original_dir}")
    
    # First, clean up any remaining QEMU processes (preserve binaries)
    print("\nCleaning up QEMU processes...")
    cleanup_success = cleanup_qemu_processes(force_kill=True, restore_cwd=True,
                                             preserve_binaries=True)
    
    if cleanup_success:
        print("QEMU cleanup completed")
    else:
        print("QEMU cleanup had issues")
    
    # Now restore terminal
    print("\nRestoring terminal state...")
    restore_success = restore_terminal()
    
    # Final directory check
    current_dir = os.getcwd()
    if current_dir != original_dir:
        print(f"\nDirectory changed during cleanup: "
              f"{original_dir} → {current_dir}")
    else:
        print(f"\nWorking directory maintained: {original_dir}")
    
    if restore_success:
        print("Terminal restoration completed successfully")
        print("\nYour terminal should now be working normally!")
    else:
        print("Terminal restoration had issues")
        print("\nTry running these commands manually:")
        print("   reset")
        print("   stty sane")
        print("   tput reset")
    
    return 0 if (cleanup_success and restore_success) else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)