#!/usr/bin/env python3
"""
F-K2-TC-001: Test periodic sampling functionality in QEMU ARM environment

Test Cases:
- F-K2-TC-001: Sampling jitter ≤ ±10%
- F-K2-TC-002: Updating sampling_ms changes rate ≤ 2 periods

This is the ARM/QEMU version of the F-K2 tests for cross-platform validation.

Copyright (c) Jorge Rodriguez Moreno
"""

import pytest
import time
import struct
from test_utils import (get_or_start_shared_qemu_session, execute_command,
                        show_qemu_recovery_info, get_module_path_for_context)

# Test configuration
MODULE_NAME = "nxp_simtemp"
DEVICE_PATH_ARM = "/dev/simtemp0"
SAMPLING_PATH_ARM = "/sys/devices/platform/simtemp/sampling_ms"


class TestF_K2_PeriodicSampling_ARM:
    """Test periodic sampling every N ms in QEMU ARM environment"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup QEMU session and load driver, yield to test, then cleanup"""
        
        # Get or start shared QEMU session
        qemu_process = get_or_start_shared_qemu_session()
        
        if qemu_process:
            show_qemu_recovery_info(qemu_process,
                                    "F-K2 PERIODIC SAMPLING TEST")
        else:
            pytest.skip("QEMU session not available for ARM testing")
        
        # Get module path and load driver
        try:
            module_path, context_description = get_module_path_for_context()
            print(f"Running in {context_description}")
            print(f"Module path: {module_path}")
            
            # Verify module exists in QEMU
            success, output = execute_command(f"test -f {module_path}")
            if not success:
                # Try alternative paths
                alt_paths = [
                    "/tmp/nxp_simtemp.ko",
                    "/lib/modules/nxp_simtemp.ko",
                    "/home/simtemp/nxp_simtemp.ko"
                ]
                found_module = False
                for alt_path in alt_paths:
                    success, _ = execute_command(f"test -f {alt_path}")
                    if success:
                        module_path = alt_path
                        found_module = True
                        print(f"Found module at alternative path: "
                              f"{module_path}")
                        break
                
                if not found_module:
                    pytest.skip(f"Module not found in QEMU at {module_path} "
                                f"or alternatives")
            
            # Load module if not already loaded
            success, output = execute_command("lsmod | grep nxp_simtemp")
            if not success:
                print(f"Loading module: {module_path}")
                success, output = execute_command(f"insmod {module_path}")
                if not success:
                    error_msg = ' '.join(output) if output else 'Unknown error'
                    pytest.fail(f"Failed to load module: {error_msg}")
                print("✓ Module loaded successfully")
            else:
                print("✓ Module already loaded")
            
            # Verify device exists
            success, output = execute_command(f"test -c {DEVICE_PATH_ARM}")
            if not success:
                pytest.fail(f"Device {DEVICE_PATH_ARM} not found "
                            f"after module load")
            print(f"✓ Device {DEVICE_PATH_ARM} available")
            
            # Set device permissions (QEMU should allow this)
            execute_command(f"chmod 666 {DEVICE_PATH_ARM}")
            
        except Exception as e:
            pytest.fail(f"Setup failed: {e}")
        
        yield
        
        # Cleanup: Note - keep module loaded for other tests
        print("✓ F-K2 test completed - keeping module loaded for other tests")

    def test_sampling_jitter_within_10_percent_arm(self):
        """F-K2-TC-001: Sampling jitter ≤ ±10% in QEMU ARM environment"""
        
        # Use platform device path for ARM QEMU environment
        sampling_path = SAMPLING_PATH_ARM
        print(f"Using platform device path: {sampling_path}")
        
        # Set 500ms sampling
        success, output = execute_command(f"echo 500 > {sampling_path}")
        if not success:
            error_msg = ' '.join(output) if output else 'Write failed'
            pytest.fail(f"Failed to set sampling rate: {error_msg}")
        
        # Check if this is simulated output
        is_simulated = any("simulated output" in line.lower() or
                           "Command executed successfully" in line
                           for line in output)
        if is_simulated:
            print("WARNING: execute_command is returning simulated output")
            print("This means QEMU connection is not working properly")
            pytest.skip("QEMU connection not working - "
                        "getting simulated output")
        
        # Verify sampling rate was set
        success, output = execute_command(f"cat {sampling_path}")
        if not success:
            error_msg = ' '.join(output) if output else 'Read failed'
            pytest.fail(f"Failed to read sampling rate: {error_msg}")
        
        actual_ms = int(''.join(output).strip())
        assert actual_ms == 500, f"Expected 500ms, got {actual_ms}ms"
        print(f"✓ Sampling rate set to {actual_ms}ms")
        
        # Collect timestamps with proper timing
        timestamps = []
        print("Collecting temperature samples...")
        
        # Open device and collect samples
        for i in range(6):  # Collect 6 samples
            # Read 20 bytes (simtemp_record size)
            cmd = (f"timeout 2 dd if={DEVICE_PATH_ARM} bs=20 count=1 "
                   f"2>/dev/null | hexdump -C")
            success, output = execute_command(cmd)
            if not success:
                pytest.fail(f"Failed to read from device on sample {i}")
            
            # Parse hexdump output to extract timestamp
            try:
                # Filter out kernel messages and find hexdump lines
                hex_lines = [line for line in output
                             if line.strip() and
                             not line.startswith('[') and  # Remove kernel msgs
                             not line.startswith('*') and  # Remove repetition
                             ('|' in line or len(line.split()) > 8)]  # Hex lines
                
                if not hex_lines:
                    pytest.fail(f"No hex data received from device on "
                                f"sample {i}")
                
                # Use first hex line (should be "00000000  xx xx xx xx ...")
                hex_line = hex_lines[0]
                print(f"Sample {i} hex line: {hex_line}")
                
                # Extract hex bytes (skip address, take hex part before |)
                if '|' in hex_line:
                    # Get part before ASCII representation
                    hex_part = hex_line.split('|')[0].strip()
                    hex_data = hex_part.split()[1:]  # Skip address
                else:
                    # Fallback: skip address, take first 8 bytes
                    hex_data = hex_line.split()[1:9]
                
                if len(hex_data) < 8:
                    pytest.fail(f"Insufficient hex data on sample {i}: "
                                f"got {len(hex_data)} bytes, need 8")
                
                print(f"Sample {i} hex data: {hex_data[:8]}")
                
                # Convert little-endian hex to timestamp (first 8 bytes)
                timestamp_bytes = bytes.fromhex(''.join(hex_data[:8]))
                timestamp_ns = struct.unpack('<Q', timestamp_bytes)[0]
                timestamps.append(timestamp_ns)
                
                print(f"Sample {i}: timestamp={timestamp_ns}")
                
            except (ValueError, struct.error) as e:
                pytest.fail(f"Failed to parse device data on sample {i}: {e}")
            
            if i < 5:  # Don't sleep after last sample
                time.sleep(0.6)  # Wait 600ms between reads (>500ms period)
        
        assert len(timestamps) >= 5, (f"Expected at least 5 samples, "
                                      f"got {len(timestamps)}")
        
        # Calculate intervals and check jitter
        intervals_ns = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            intervals_ns.append(interval)

        expected_ns = 500 * 1_000_000  # 500ms in nanoseconds
        print(f"Expected interval: {expected_ns} ns")
        
        # Check jitter for all intervals
        for i, interval in enumerate(intervals_ns):
            jitter_percent = abs(interval - expected_ns) / expected_ns * 100
            interval_ms = interval / 1_000_000
            print(f"Interval {i+1}: {interval_ms:.1f}ms, "
                  f"jitter: {jitter_percent:.1f}%")
            
            msg = f"Interval {i+1}: {jitter_percent:.1f}% jitter > 10%"
            assert jitter_percent <= 10.0, msg
        
        print("✓ All intervals within ±10% jitter requirement")

    def test_sampling_rate_update_within_2_periods_arm(self):
        """F-K2-TC-002: Update sampling_ms changes rate ≤ 2 periods ARM"""
        
        # Use platform device path for ARM QEMU environment
        sampling_path = SAMPLING_PATH_ARM
        print(f"Using platform device path: {sampling_path}")
        
        # Start with 1000ms sampling
        success, output = execute_command(f"echo 1000 > {sampling_path}")
        if not success:
            error_msg = ' '.join(output) if output else 'Write failed'
            pytest.fail(f"Failed to set initial sampling rate: {error_msg}")
        
        # Check if this is simulated output
        is_simulated = any("simulated output" in line.lower() or
                           "Command executed successfully" in line
                           for line in output)
        if is_simulated:
            print("WARNING: execute_command is returning simulated output")
            print("This means QEMU connection is not working properly")
            pytest.skip("QEMU connection not working - "
                        "getting simulated output")
        
        timestamps = []
        print("Collecting samples with rate change...")
        
        # Collect 2 samples at 1000ms rate
        for i in range(2):
            cmd = (f"timeout 2 dd if={DEVICE_PATH_ARM} bs=20 count=1 "
                   f"2>/dev/null | hexdump -C")
            success, output = execute_command(cmd)
            if not success:
                pytest.fail(f"Failed to read from device on "
                            f"initial sample {i}")
            
            # Parse timestamp from hexdump
            try:
                hex_lines = [line for line in output
                             if line.strip() and not line.startswith('*')]
                hex_data = hex_lines[0].split()[1:9]
                timestamp_bytes = bytes.fromhex(''.join(hex_data[:8]))
                timestamp_ns = struct.unpack('<Q', timestamp_bytes)[0]
                timestamps.append(timestamp_ns)
                print(f"Initial sample {i}: timestamp={timestamp_ns}")
            except (ValueError, struct.error) as e:
                pytest.fail(f"Failed to parse initial sample {i}: {e}")
            
            if i < 1:  # Sleep after first sample
                time.sleep(1.1)  # Wait >1000ms
        
        # Change to 200ms and collect more samples
        print("Changing sampling rate to 200ms...")
        success, output = execute_command(f"echo 200 > {sampling_path}")
        if not success:
            error_msg = ' '.join(output) if output else 'Write failed'
            pytest.fail(f"Failed to change sampling rate: {error_msg}")
        
        # Collect samples at new 200ms rate
        for i in range(4):
            time.sleep(0.25)  # Wait 250ms between reads
            cmd = (f"timeout 2 dd if={DEVICE_PATH_ARM} bs=20 count=1 "
                   f"2>/dev/null | hexdump -C")
            success, output = execute_command(cmd)
            if not success:
                pytest.fail(f"Failed to read from device on "
                            f"changed sample {i}")
            
            # Parse timestamp from hexdump
            try:
                hex_lines = [line for line in output
                             if line.strip() and not line.startswith('*')]
                hex_data = hex_lines[0].split()[1:9]
                timestamp_bytes = bytes.fromhex(''.join(hex_data[:8]))
                timestamp_ns = struct.unpack('<Q', timestamp_bytes)[0]
                timestamps.append(timestamp_ns)
                print(f"Changed sample {i}: timestamp={timestamp_ns}")
            except (ValueError, struct.error) as e:
                pytest.fail(f"Failed to parse changed sample {i}: {e}")
        
        assert len(timestamps) >= 5, (f"Expected at least 5 samples, "
                                      f"got {len(timestamps)}")
        
        # Check that the rate change took effect
        change_detected = False
        
        # Look for intervals around 200ms after the change
        for i in range(2, len(timestamps)):  # Start from 3rd sample
            interval = timestamps[i] - timestamps[i-1]
            interval_ms = interval / 1_000_000
            print(f"Interval {i}: {interval_ms:.1f}ms")
            
            # If interval is close to 200ms, rate change was applied
            if 150 < interval_ms < 250:  # 150-250ms range
                change_detected = True
                print(f"✓ Rate change detected at interval {i}: "
                      f"{interval_ms:.1f}ms")
                break
        
        assert change_detected, "Sampling rate change was not detected"
        print("✓ Sampling rate change validated successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

