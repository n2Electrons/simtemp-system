"""
Test cases for QEMU Device Tree overlay functionality.
"""

import os
import pytest
import subprocess
import time


# Test timeout in seconds (1 minute)
QEMU_TIMEOUT = 60


def test_qemu_initramfs_ready():
    """
    Test case F-K1-TC-002: Test QEMU Device Tree overlay infrastructure.
    Expected Result: QEMU boots successfully and initramfs is ready.
    """
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
        start_time = time.time()
        output_lines = []
        found_ready = False

        print("Waiting for initramfs ready message...")

        while time.time() - start_time < QEMU_TIMEOUT:
            # Check if process is still running
            if qemu_process.poll() is not None:
                # Process has terminated
                stdout, stderr = qemu_process.communicate()
                output_lines.extend(stdout.splitlines() if stdout else [])
                fail_msg = (f"QEMU process terminated unexpectedly. "
                            f"Exit code: {qemu_process.returncode}\n"
                            f"Output: {chr(10).join(output_lines)}")
                pytest.fail(fail_msg)

            # Read output line by line with short timeout
            try:
                line = qemu_process.stdout.readline()
                if line:
                    line = line.strip()
                    output_lines.append(line)
                    print(f"QEMU: {line}")

                    # Check for the expected ready message
                    if "=== initramfs ready ===" in line:
                        found_ready = True
                        print("✓ initramfs ready message found!")
                        break
                else:
                    # No output, sleep briefly
                    time.sleep(0.1)

            except Exception as e:
                pytest.fail(f"Error reading QEMU output: {e}")

        # Check results
        if not found_ready:
            timeout_msg = (f"Timeout waiting for initramfs ready message "
                           f"after {QEMU_TIMEOUT} seconds.\n"
                           f"QEMU output:\n{chr(10).join(output_lines)}")
            pytest.fail(timeout_msg)

        print("✓ QEMU Device Tree overlay infrastructure test passed")

    except subprocess.SubprocessError as e:
        pytest.fail(f"Failed to launch QEMU: {e}")

    except Exception as e:
        pytest.fail(f"Unexpected error during QEMU test: {e}")

    finally:
        # Clean up: terminate QEMU process if still running
        if qemu_process and qemu_process.poll() is None:
            print("Terminating QEMU process...")
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
                print(f"Warning: Error during QEMU cleanup: {cleanup_error}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

