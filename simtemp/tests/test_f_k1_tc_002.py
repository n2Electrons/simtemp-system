"""
Test cases for QEMU Device Tree overlay functionality.
"""

import os
import pytest
import subprocess
from test_utils import (wait_for_qemu_message, cleanup_qemu_processes,
                        load_environment)

# Test timeout in seconds (1 minute)
QEMU_TIMEOUT = 60


@pytest.mark.order(1)
def test_basic_qemu_boot():
    """
    Test case F-K1-TC-002: Test QEMU Device Tree overlay infrastructure.
    Expected Result: QEMU boots successfully and initramfs is ready.
    """
    with load_environment():
        # Kill any existing QEMU processes to avoid port conflicts
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

        print(f"Testing QEMU script: {qemu_script}")
        print(f"Working directory will be: {qemu_dir}")

        # Launch QEMU process
        qemu_process = None
        test_passed = False
        try:
            # Change to QEMU directory where files are located
            os.chdir(qemu_dir)
            
            print("Launching QEMU...")
            qemu_process = subprocess.Popen(
                [qemu_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Wait for initramfs ready message with timeout
            print("Waiting for initramfs ready message...")
            
            try:
                found_ready, output_lines = wait_for_qemu_message(
                    qemu_process,
                    "=== initramfs ready ===",
                    QEMU_TIMEOUT
                )
                
                # Check results
                if not found_ready:
                    timeout_msg = (
                        f"Timeout waiting for initramfs ready message "
                        f"after {QEMU_TIMEOUT} seconds.\n"
                        f"QEMU output:\n{chr(10).join(output_lines)}")
                    pytest.fail(timeout_msg)
                    
            except RuntimeError as e:
                pytest.fail(str(e))

            print("✓ QEMU Device Tree overlay infrastructure test passed")
            test_passed = True

        except subprocess.SubprocessError as e:
            pytest.fail(f"Failed to launch QEMU: {e}")

        except Exception as e:
            pytest.fail(f"Unexpected error during QEMU test: {e}")

        finally:
            # Only terminate QEMU if the test failed or if there was an error
            if qemu_process and qemu_process.poll() is None:
                if test_passed:
                    print("✓ Test passed successfully - "
                          "QEMU session will continue running")
                    print(f"QEMU PID: {qemu_process.pid}")
                    print("Note: QEMU process will remain active "
                          "for manual testing")
                else:
                    print("Test failed - terminating QEMU process...")
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
            
            # Additional cleanup handled by load_environment
            print("Additional cleanup will be handled by load_environment")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

