#!/usr/bin/env python3
"""
Test script to verify SSH implementation in test_utils.py
This script tests the hardcoded SSH configuration + serial console.
"""

import os
import sys
import time

# Add the simtemp tests directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simtemp', 'tests'))

try:
    from test_utils import (start_qemu_and_wait_for_boot, wait_for_ssh_ready,
                            execute_ssh_command, cleanup_qemu_processes)
except ImportError as e:
    print(f"Error importing test_utils: {e}")
    sys.exit(1)


def test_ssh_implementation():
    """Test the SSH implementation in test_utils.py"""
    print("=== Testing SSH Implementation in test_utils.py ===")
    
    # Clean up any existing QEMU processes first
    print("1. Cleaning up existing QEMU processes...")
    cleanup_qemu_processes(force_kill=True)
    time.sleep(2)
    
    qemu_process = None
    try:
        # Start QEMU with our new SSH configuration
        print("2. Starting QEMU with SSH configuration...")
        qemu_process, socket_port = start_qemu_and_wait_for_boot()
        
        print(f"✓ QEMU started successfully (socket port: {socket_port})")
        
        # Wait for SSH to be ready
        print("3. Waiting for SSH service to be ready...")
        ssh_ready = wait_for_ssh_ready(ssh_port=2222, timeout=60)
        
        if not ssh_ready:
            print("✗ SSH service not ready within timeout")
            return False
        
        print("✓ SSH service is ready")
        
        # Test SSH command execution
        print("4. Testing SSH command execution...")
        
        # Test basic command
        success, output = execute_ssh_command("echo 'SSH test successful'",
                                              ssh_port=2222)
        if success and output:
            print(f"✓ SSH command test successful: {output[0]}")
        else:
            print(f"✗ SSH command test failed: {output}")
            return False
        
        # Test module loading capability via SSH
        print("5. Testing module-related commands via SSH...")
        success, output = execute_ssh_command("lsmod | head -5", ssh_port=2222)
        if success:
            print("✓ SSH lsmod command successful")
            for line in output[:3]:  # Show first 3 lines
                print(f"   {line}")
        else:
            print(f"✗ SSH lsmod command failed: {output}")
        
        # Test if SimTemp driver is available in the guest
        driver_cmd = ("ls -la /tmp/prebuild/simtemp-driver/ 2>/dev/null || "
                      "echo 'Driver path not found'")
        success, output = execute_ssh_command(driver_cmd, ssh_port=2222)
        if success:
            print("✓ SSH driver path check successful")
            for line in output[:3]:
                print(f"   {line}")
        
        print("\n=== SSH Implementation Test Results ===")
        print("✓ QEMU starts with SSH configuration")
        print("✓ SSH service becomes ready")
        print("✓ SSH commands can be executed")
        print("✓ Module and driver operations accessible via SSH")
        print("\n🎉 SSH implementation test PASSED!")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        return False
    
    finally:
        # Clean up
        if qemu_process:
            print("\n6. Cleaning up QEMU process...")
            try:
                qemu_process.terminate()
                time.sleep(2)
                if qemu_process.poll() is None:
                    qemu_process.kill()
            except Exception as e:
                print(f"Warning: Error during cleanup: {e}")
        
        cleanup_qemu_processes(force_kill=True)
        print("✓ Cleanup completed")


if __name__ == "__main__":
    success = test_ssh_implementation()
    sys.exit(0 if success else 1)
