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
        
        subprocess.run(["sudo", "insmod", str(driver_path)], check=True)
        yield
        
        # Cleanup
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
        
        # Open device and collect timestamps
        timestamps = []
        with open(device_path, 'rb') as f:
            start_time = time.time()
            while time.time() - start_time < 2.5:  # 5 samples in 2.5s
                data = f.read(20)  # struct simtemp_record size
                if len(data) == 20:
                    unpacked = struct.unpack('<QiII', data)
                    timestamp_ns, temp_mc, flags, reserved = unpacked
                    timestamps.append(timestamp_ns)
        
        assert len(timestamps) >= 4, "Should have at least 4 samples"
        
        # Calculate intervals and check jitter
        intervals_ns = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            intervals_ns.append(interval)
        
        expected_ns = 500 * 1_000_000  # 500ms in nanoseconds
        for interval in intervals_ns:
            jitter_percent = abs(interval - expected_ns) / expected_ns * 100
            msg = f"Jitter {jitter_percent:.1f}% > 10%"
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
            # Collect 2 samples at 1000ms
            for _ in range(2):
                data = f.read(20)
                if len(data) == 20:
                    timestamp_ns = struct.unpack('<QiII', data)[0]
                    timestamps.append(timestamp_ns)
            
            # Change to 200ms
            change_time = time.time_ns()
            cmd = ["sudo", "sh", "-c", f"echo 200 > {sampling_path}"]
            subprocess.run(cmd, check=True)
            
            # Collect next samples at 200ms
            for _ in range(3):
                data = f.read(20)
                if len(data) == 20:
                    timestamp_ns = struct.unpack('<QiII', data)[0]
                    timestamps.append(timestamp_ns)
        
        assert len(timestamps) >= 5, "Should have at least 5 samples"
        
        # Check that the rate change took effect within 2 periods (2000ms)
        change_detected = False
        max_change_delay = 2000 * 1_000_000  # 2000ms in nanoseconds
        
        for i in range(2, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            # If interval is close to 200ms, rate change was applied
            if 150_000_000 < interval < 250_000_000:  # 150-250ms range
                change_detected = True
                delay = timestamps[i-1] - change_time
                msg = f"Rate change took {delay/1e6:.0f}ms > 2000ms"
                assert delay <= max_change_delay, msg
                break
        
        assert change_detected, "Sampling rate change was not detected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])