#!/usr/bin/env python3
"""
QEMU Session Manager for shared QEMU testing sessions.

This module provides utilities for managing shared QEMU sessions across
multiple tests, ensuring efficient resource usage and proper cleanup.
"""

import os
import sys
import json
import time
import signal
import atexit
from pathlib import Path

# Add test_utils to path
sys.path.insert(0, os.path.dirname(__file__))
from test_utils import cleanup_qemu_session, is_qemu_session_active


class QemuSessionManager:
    """Manages shared QEMU sessions for test execution."""
    
    def __init__(self):
        self.session_started = False
        self.cleanup_registered = False
    
    def register_cleanup(self):
        """Register cleanup functions to run when test runner exits."""
        if self.cleanup_registered:
            return
        
        # Register cleanup for normal exit
        atexit.register(self.cleanup_all_sessions)
        
        # Register cleanup for signal interruption
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.cleanup_registered = True
        print("QEMU session cleanup handlers registered")
    
    def _signal_handler(self, signum, frame):
        """Handle signals by cleaning up QEMU sessions."""
        print(f"\nReceived signal {signum}, cleaning up QEMU sessions...")
        self.cleanup_all_sessions()
        sys.exit(1)
    
    def cleanup_all_sessions(self):
        """Clean up all active QEMU sessions."""
        if is_qemu_session_active():
            print("\n=== QEMU Session Cleanup ===")
            print("Test runner terminating - cleaning up QEMU session...")
            cleanup_qemu_session()
            print("QEMU session cleanup completed")
        else:
            print("No active QEMU sessions to clean up")
    
    def ensure_cleanup_on_exit(self):
        """Ensure QEMU sessions will be cleaned up when test runner exits."""
        self.register_cleanup()


# Global session manager instance
_session_manager = QemuSessionManager()


def setup_qemu_session_cleanup():
    """
    Set up QEMU session cleanup to run when test runner exits.
    Call this function at the start of your test runner.
    """
    _session_manager.ensure_cleanup_on_exit()


def manual_cleanup_qemu_sessions():
    """
    Manually clean up all QEMU sessions.
    Useful for explicit cleanup in test runners.
    """
    _session_manager.cleanup_all_sessions()


if __name__ == "__main__":
    # Command line interface for manual session management
    import argparse
    
    parser = argparse.ArgumentParser(description="QEMU Session Manager")
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up all active QEMU sessions')
    parser.add_argument('--status', action='store_true',
                       help='Check status of QEMU sessions')
    
    args = parser.parse_args()
    
    if args.cleanup:
        print("Cleaning up QEMU sessions...")
        manual_cleanup_qemu_sessions()
    elif args.status:
        if is_qemu_session_active():
            print("QEMU session is ACTIVE")
        else:
            print("No active QEMU sessions")
    else:
        parser.print_help()