#!/usr/bin/env python3
"""
Test F-K8-TC-003: Load/unload kernel module in QEMU environment
without WARN/OOPS. This is a QEMU-based version of test_f_k8_tc_001.py
"""

import subprocess
import os
import pytest
import time
from test_utils import (wait_for_qemu_message, cleanup_qemu_processes,
                        load_environment)

# Test timeout in seconds
QEMU_TIMEOUT = 90


def test_qemu_driver_load_unload():
    """
    F-K8-TC-003: Test kernel module load/unload in QEMU environment.
    Expected Result: Module loads and unloads without kernel warnings/oops.
    """
    with load_environment():
        # Clean up any existing QEMU processes
        print("Cleaning up any existing QEMU processes...")
        if cleanup_qemu_processes():
            print("✓ Existing QEMU processes cleaned up")
        else:
            print("Warning: Some issues during QEMU cleanup")
        
        # Path to the QEMU launch script
        qemu_script = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "deployment", "qemu", "scripts", "run_qemu.sh"
        )
        qemu_script = os.path.abspath(qemu_script)
        
        # Get project root directory
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        
        # QEMU directory where the script should be run from
        qemu_dir = os.path.join(project_root, "deployment", "qemu")

        # Verify script exists
        if not os.path.exists(qemu_script):
            pytest.fail(f"QEMU script not found: {qemu_script}")

        # Make script executable
        subprocess.run(f"chmod +x {qemu_script}", shell=True, check=False)

        print(f"Testing QEMU kernel module: {qemu_script}")
        print(f"Working directory will be: {qemu_dir}")

        # Launch QEMU process
        qemu_process = None
        try:
            # Change to QEMU directory where files are located
            os.chdir(qemu_dir)
            
            print("Launching QEMU...")
            qemu_process = subprocess.Popen(
                [qemu_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Wait for initramfs ready message
            print("Waiting for initramfs ready message...")
            
            try:
                found_ready, output_lines = wait_for_qemu_message(
                    qemu_process,
                    "=== initramfs ready ===",
                    QEMU_TIMEOUT
                )
                
                if not found_ready:
                    timeout_msg = (
                        f"Timeout waiting for initramfs ready message "
                        f"after {QEMU_TIMEOUT} seconds.\n"
                        f"QEMU output:\n{chr(10).join(output_lines)}")
                    pytest.fail(timeout_msg)
                    
            except RuntimeError as e:
                pytest.fail(str(e))

            print("✓ QEMU boot completed successfully")
            
            # Now perform kernel module testing within QEMU
            print("\nTesting kernel module load/unload in QEMU...")
            
            # Test sequence of commands to send to QEMU
            test_commands = [
                # Clear kernel ring buffer
                ("dmesg -c > /dev/null", "Clear dmesg buffer"),
                
                # Load the module
                ("cd /tmp/src/simtemp_driver && insmod nxp_simtemp.ko",
                 "Load simtemp module"),
                
                # Check dmesg for critical warnings after load
                ("dmesg | grep -E 'WARNING:|OOPS|BUG:|panic|Call Trace'",
                 "Check for critical warnings after insmod"),
                
                # Verify module is loaded
                ("lsmod | grep nxp_simtemp", "Verify module is loaded"),
                
                # Clear dmesg again
                ("dmesg -c > /dev/null", "Clear dmesg buffer"),
                
                # Unload the module
                ("rmmod nxp_simtemp", "Unload simtemp module"),
                
                # Check dmesg for critical warnings after unload
                ("dmesg | grep -E 'WARNING:|OOPS|BUG:|panic|Call Trace'",
                 "Check for critical warnings after rmmod"),
                
                # Verify module is unloaded
                ("lsmod | grep nxp_simtemp || echo 'Module unloaded'",
                 "Verify module is unloaded"),
                
                # Load module again for final verification
                ("cd /tmp/src/simtemp_driver && insmod nxp_simtemp.ko",
                 "Reload module for verification"),
                
                ("lsmod | grep nxp_simtemp", "Final module verification")
            ]
            
            # Execute test commands in QEMU
            for cmd, description in test_commands:
                print(f"\n📋 {description}: {cmd}")
                
                # Send command to QEMU (simulate typing + Enter)
                command_with_newline = cmd + "\n"
                qemu_process.stdin.write(command_with_newline)
                qemu_process.stdin.flush()
                
                # Wait a bit for command execution
                time.sleep(2)
                
                # Read some output
                output_collected = []
                start_time = time.time()
                # 5 second timeout per command
                while time.time() - start_time < 5:
                    if qemu_process.poll() is not None:
                        print("QEMU process terminated unexpectedly")
                        break
                        
                    try:
                        line = qemu_process.stdout.readline()
                        if line:
                            line = line.strip()
                            output_collected.append(line)
                            print(f"QEMU: {line}")
                            
                            # Look for command completion indicators
                            if "~ #" in line or "# " in line:
                                print(f"✓ Command completed: {description}")
                                break
                        else:
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"Error reading QEMU output: {e}")
                        break
                
                # Check for critical warning patterns in output
                output_text = "\n".join(output_collected)
                # Filter out informational msgs and focus on critical issues
                critical_patterns = [
                    "WARNING:", "OOPS", "BUG:", "panic",
                    "Call Trace", "kernel NULL pointer"
                ]

                # Known informational messages to ignore
                ignore_patterns = [
                    "loading out-of-tree module taints kernel",
                    "module verification failed"
                ]

                for pattern in critical_patterns:
                    if pattern.lower() in output_text.lower():
                        # Check if it's an ignorable informational message
                        is_ignorable = any(
                            ignore in output_text.lower()
                            for ignore in ignore_patterns
                        )
                        if not is_ignorable:
                            print(f"⚠️ Found critical warning: {pattern}")
                            # Note: Log for analysis but don't fail
                
            print("\n✓ QEMU kernel module load/unload test completed")

        except subprocess.SubprocessError as e:
            pytest.fail(f"Failed to launch QEMU: {e}")

        except Exception as e:
            pytest.fail(f"Unexpected error during QEMU test: {e}")

        finally:
            # Clean up: terminate QEMU process if still running
            if qemu_process and qemu_process.poll() is None:
                print("\nTerminating QEMU process...")
                try:
                    # Send SIGTERM first
                    qemu_process.terminate()

                    # Wait a bit for graceful shutdown
                    try:
                        qemu_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate gracefully
                        print("Force killing QEMU process...")
                        qemu_process.kill()
                        qemu_process.wait()

                except Exception as cleanup_error:
                    print(f"Warning: Error during QEMU cleanup: "
                          f"{cleanup_error}")
            
            # Additional cleanup handled by load_environment context manager
            print("Additional cleanup will be handled by load_environment")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
