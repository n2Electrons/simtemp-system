#!/usr/bin/env python3
"""
F-K2-TC-001: Test periodic sampling functionality

Test Cases:
- F-K2-TC-001: Sampling jitter ≤ ±10%
- F-K2-TC-002: Updating sampling_ms changes rate ≤ 2 periods

Copyright (c) Jorge Rodriguez Moreno
"""

import pytest
import subprocess
import time
import struct
from pathlib import Path


class TestF_K2_PeriodicSampling:
    """Test periodic sampling every N ms"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Load driver, yield to test, then cleanup"""
        # Setup
        driver_path = Path("../kernel/obj/nxp_simtemp.ko")
        if not driver_path.exists():
            pytest.skip(f"Driver not found: {driver_path}")
        
        # Check if module is already loaded
        result = subprocess.run(["lsmod"], capture_output=True, text=True)
        module_loaded = "nxp_simtemp" in result.stdout
        
        if not module_loaded:
            subprocess.run(["sudo", "insmod", str(driver_path)], check=True)
        
        yield
        
        # Cleanup only if we loaded it
        if not module_loaded:
            subprocess.run(["sudo", "rmmod", "nxp_simtemp"], check=False)

    def test_sampling_jitter_within_10_percent(self):
        """F-K2-TC-001: Sampling jitter ≤ ±10%"""
        device_path = "/dev/simtemp0"
        sampling_path = "/sys/class/simtemp_class/simtemp0/sampling_ms"
        
        # Set 500ms sampling
        cmd = ["sudo", "sh", "-c", f"echo 500 > {sampling_path}"]
        subprocess.run(cmd, check=True)
        
        # Read current sampling rate
        with open(sampling_path, 'r') as f:
            actual_ms = int(f.read().strip())
        assert actual_ms == 500
        
        # Open device and collect timestamps with proper timing
        timestamps = []
        with open(device_path, 'rb') as f:
            for i in range(6):  # Collect 6 samples
                data = f.read(20)  # struct simtemp_record size
                if len(data) == 20:
                    unpacked = struct.unpack('<QiII', data)
                    timestamp_ns, temp_mc, flags, reserved = unpacked
                    timestamps.append(timestamp_ns)
                if i < 5:  # Don't sleep after last sample
                    time.sleep(0.6)  # Wait 600ms between reads (>500ms period)
        
        assert len(timestamps) >= 5, "Should have at least 5 samples"
        
        # Calculate intervals and check jitter
        intervals_ns = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            intervals_ns.append(interval)

        expected_ns = 500 * 1_000_000  # 500ms in nanoseconds
        # All intervals should be close to expected
        for i, interval in enumerate(intervals_ns):
            jitter_percent = abs(interval - expected_ns) / expected_ns * 100
            msg = f"Interval {i+1}: {jitter_percent:.1f}% jitter > 10%"
            assert jitter_percent <= 10.0, msg

    def test_sampling_rate_update_within_2_periods(self):
        """F-K2-TC-002: Updating sampling_ms changes rate ≤ 2 periods"""
        device_path = "/dev/simtemp0"
        sampling_path = "/sys/class/simtemp_class/simtemp0/sampling_ms"
        
        # Start with 1000ms sampling
        cmd = ["sudo", "sh", "-c", f"echo 1000 > {sampling_path}"]
        subprocess.run(cmd, check=True)
        
        timestamps = []
        with open(device_path, 'rb') as f:
            # Collect 2 samples at 1000ms rate
            for i in range(2):
                data = f.read(20)
                if len(data) == 20:
                    timestamp_ns = struct.unpack('<QiII', data)[0]
                    timestamps.append(timestamp_ns)
                if i < 1:  # Sleep after first sample
                    time.sleep(1.1)  # Wait >1000ms
            
            # Change to 200ms and collect more samples
            change_time = time.time_ns()
            cmd = ["sudo", "sh", "-c", f"echo 200 > {sampling_path}"]
            subprocess.run(cmd, check=True)
            
            # Collect samples at new 200ms rate
            for i in range(4):
                time.sleep(0.25)  # Wait 250ms between reads
                data = f.read(20)
                if len(data) == 20:
                    timestamp_ns = struct.unpack('<QiII', data)[0]
                    timestamps.append(timestamp_ns)
        
        assert len(timestamps) >= 5, "Should have at least 5 samples"
        
        # Check that the rate change took effect
        change_detected = False
        
        # Look for intervals around 200ms after the change
        for i in range(2, len(timestamps)):  # Start from 3rd sample
            interval = timestamps[i] - timestamps[i-1]
            interval_ms = interval / 1_000_000
            # If interval is close to 200ms, rate change was applied
            if 150 < interval_ms < 250:  # 150-250ms range
                change_detected = True
                break
        
        assert change_detected, "Sampling rate change was not detected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
