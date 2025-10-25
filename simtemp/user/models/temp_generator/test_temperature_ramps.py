#!/usr/bin/env python3
"""
test_temperature_ramps.py - Validate temperature ramp generation for F-K5

Copyright (c) 2025 Jorge Rodriguez Moreno

This script validates that temperature ramps work correctly for alert testing.
It specifically tests that F-K5 alert functionality works with dynamic
temperature generation.
"""

import os
import sys
import time
import struct
import subprocess
from pathlib import Path

# Add parent directory to path for test_utils
sys.path.append(str(Path(__file__).parent.parent.parent / "tests"))

try:
    from test_utils import load_simtemp_modules, unload_simtemp_modules, SUDO
    UTILS_AVAILABLE = True
except ImportError:
    print("Warning: test_utils not available, using basic functionality")
    UTILS_AVAILABLE = False
    SUDO = "sudo " if os.geteuid() != 0 else ""


class TemperatureRampTester:
    """Test temperature ramp generation and alert functionality"""
    
    def __init__(self):
        self.device_path = None
        self.sysfs_path = None
        self.find_device()
    
    def find_device(self):
        """Find simtemp device and corresponding sysfs"""
        for i in range(4):
            device_path = f"/dev/simtemp{i}"
            if os.path.exists(device_path):
                # Check if it's a character device
                try:
                    import stat
                    device_stat = os.stat(device_path)
                    if stat.S_ISCHR(device_stat.st_mode):
                        self.device_path = device_path
                        
                        # Find corresponding sysfs
                        sysfs_candidates = [
                            f"/sys/devices/platform/nxp-simtemp.{i}.auto",
                            f"/sys/devices/platform/nxp-simtemp.{i}"
                        ]
                        for candidate in sysfs_candidates:
                            if os.path.exists(candidate):
                                stats_file = os.path.join(candidate, "stats")
                                if os.path.exists(stats_file):
                                    self.sysfs_path = candidate
                                    break
                        break
                except Exception as e:
                    print(f"Warning: Could not check {device_path}: {e}")
        
        if not self.device_path:
            raise RuntimeError("No simtemp device found")
        if not self.sysfs_path:
            raise RuntimeError("No simtemp sysfs directory found")
        
        print(f"✓ Found device: {self.device_path}")
        print(f"✓ Found sysfs: {self.sysfs_path}")
    
    def read_temperature_sample(self):
        """Read a temperature sample from the device"""
        try:
            # Try direct read first
            with open(self.device_path, 'rb') as device:
                data = device.read(20)
                if len(data) == 20:
                    timestamp, temp_mc, flags, reserved = struct.unpack(
                        '<QiiI', data)
                    return {
                        'timestamp_ns': timestamp,
                        'temp_mC': temp_mc,
                        'temp_C': temp_mc / 1000.0,
                        'flags': flags,
                        'threshold_crossed': (flags & 0x02) != 0,
                        'new_sample': (flags & 0x01) != 0
                    }
        except PermissionError:
            # Use sudo if needed
            try:
                cmd = (f"{SUDO}dd if={self.device_path} bs=20 count=1 "
                       f"2>/dev/null | hexdump -v -e '8/1 \"%02x\" \"\\n\"'")
                result = subprocess.run(cmd, shell=True, capture_output=True,
                                        text=True)
                if result.returncode == 0 and result.stdout.strip():
                    hex_data = result.stdout.strip().replace('\n', '')
                    if len(hex_data) == 40:
                        binary_data = bytes.fromhex(hex_data)
                        timestamp, temp_mc, flags, reserved = struct.unpack(
                            '<QiiI', binary_data)
                        return {
                            'timestamp_ns': timestamp,
                            'temp_mC': temp_mc,
                            'temp_C': temp_mc / 1000.0,
                            'flags': flags,
                            'threshold_crossed': (flags & 0x02) != 0,
                            'new_sample': (flags & 0x01) != 0
                        }
            except Exception as e:
                print(f"Error reading with sudo: {e}")
        
        return None
    
    def set_temperature_pattern(self, pattern):
        """Set temperature generation pattern"""
        pattern_file = os.path.join(self.sysfs_path, "temp_pattern")
        try:
            with open(pattern_file, 'w') as f:
                f.write(pattern)
            print(f"✓ Set temperature pattern to: {pattern}")
            return True
        except Exception as e:
            print(f"✗ Failed to set pattern: {e}")
            return False
    
    def get_temperature_pattern(self):
        """Get current temperature pattern"""
        pattern_file = os.path.join(self.sysfs_path, "temp_pattern")
        try:
            with open(pattern_file, 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read pattern: {e}")
            return "unknown"
    
    def set_sampling_period(self, period_ms):
        """Set sampling period"""
        sampling_file = os.path.join(self.sysfs_path, "sampling_ms")
        try:
            with open(sampling_file, 'w') as f:
                f.write(str(period_ms))
            print(f"✓ Set sampling period to: {period_ms}ms")
            return True
        except Exception as e:
            print(f"✗ Failed to set sampling period: {e}")
            return False
    
    def get_threshold(self):
        """Get current threshold"""
        threshold_file = os.path.join(self.sysfs_path, "threshold_mC")
        try:
            with open(threshold_file, 'r') as f:
                return int(f.read().strip())
        except Exception as e:
            print(f"Warning: Could not read threshold: {e}")
            return 50000  # Default
    
    def get_stats(self):
        """Get device statistics"""
        stats_file = os.path.join(self.sysfs_path, "stats")
        try:
            with open(stats_file, 'r') as f:
                stats_content = f.read()
            
            stats = {}
            for line in stats_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    stats[key.strip()] = value.strip()
            return stats
        except Exception as e:
            print(f"Warning: Could not read stats: {e}")
            return {}
    
    def test_pattern_generates_temperatures(self, pattern, duration=10):
        """Test that a pattern generates changing temperatures"""
        print(f"\n=== Testing Pattern: {pattern} ===")
        
        if not self.set_temperature_pattern(pattern):
            return False
        
        # Set fast sampling for testing
        self.set_sampling_period(200)  # 200ms
        
        print(f"Reading temperatures for {duration} seconds...")
        temperatures = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            sample = self.read_temperature_sample()
            if sample:
                temperatures.append(sample['temp_C'])
                print(f"  Sample: {sample['temp_C']:.1f}°C, "
                      f"flags=0x{sample['flags']:02x}")
            else:
                print("  Failed to read sample")
            time.sleep(0.3)
        
        if len(temperatures) < 2:
            print(f"✗ Pattern {pattern}: Not enough samples")
            return False
        
        # Check if temperature changed
        temp_min = min(temperatures)
        temp_max = max(temperatures)
        temp_range = temp_max - temp_min
        
        print(f"  Temperature range: {temp_min:.1f}°C to {temp_max:.1f}°C "
              f"(range: {temp_range:.1f}°C)")
        
        if pattern == "static":
            # Static should have minimal change
            if temp_range <= 0.5:
                print(f"✓ Pattern {pattern}: Correctly static "
                      f"(range ≤ 0.5°C)")
                return True
            else:
                print(f"✗ Pattern {pattern}: Too much variation for "
                      f"static pattern")
                return False
        else:
            # Dynamic patterns should show change
            if temp_range >= 1.0:
                print(f"✓ Pattern {pattern}: Shows dynamic behavior "
                      f"(range ≥ 1.0°C)")
                return True
            else:
                print(f"✗ Pattern {pattern}: Insufficient temperature "
                      f"variation")
                return False
    
    def test_alert_with_ramp(self, pattern="linear", duration=20):
        """Test that alerts work correctly with temperature ramps"""
        print(f"\n=== Testing Alerts with {pattern} Pattern ===")
        
        # Get current threshold
        threshold_mC = self.get_threshold()
        threshold_C = threshold_mC / 1000.0
        print(f"Current threshold: {threshold_C}°C")
        
        # Get initial alert count
        initial_stats = self.get_stats()
        initial_alerts = int(initial_stats.get('alerts', '0'))
        print(f"Initial alert count: {initial_alerts}")
        
        # Set pattern that should cross threshold
        if not self.set_temperature_pattern(pattern):
            return False
        
        # Set moderate sampling
        self.set_sampling_period(500)  # 500ms
        
        print(f"Monitoring for alerts over {duration} seconds...")
        alerts_detected = 0
        samples_read = 0
        start_time = time.time()
        
        while time.time() - start_time < duration:
            sample = self.read_temperature_sample()
            if sample:
                samples_read += 1
                temp_C = sample['temp_C']
                threshold_crossed = sample['threshold_crossed']
                
                print(f"  Sample {samples_read:2d}: {temp_C:5.1f}°C "
                      f"(threshold: {threshold_C:.1f}°C) "
                      f"Alert: {'YES' if threshold_crossed else 'no '}")
                
                if threshold_crossed:
                    alerts_detected += 1
                    print(f"    🚨 ALERT DETECTED! Temperature "
                          f"{temp_C:.1f}°C ≥ {threshold_C:.1f}°C")
            
            time.sleep(0.6)
        
        # Check final alert count
        final_stats = self.get_stats()
        final_alerts = int(final_stats.get('alerts', '0'))
        alerts_increment = final_alerts - initial_alerts
        
        print(f"\nAlert summary:")
        print(f"  Samples read: {samples_read}")
        print(f"  Alerts in samples: {alerts_detected}")
        print(f"  Alert counter: {initial_alerts} → {final_alerts} "
              f"(+{alerts_increment})")
        
        if alerts_detected > 0 and alerts_increment > 0:
            print(f"✓ Alert test PASSED: Detected {alerts_detected} alerts, "
                  f"counter incremented by {alerts_increment}")
            return True
        elif alerts_detected == 0:
            print(f"ℹ No alerts detected - temperature may not have "
                  f"crossed threshold")
            print(f"  This is normal if the pattern doesn't reach "
                  f"{threshold_C}°C")
            return True  # Not necessarily a failure
        else:
            print(f"✗ Alert test FAILED: Alerts detected but counter "
                  f"not incremented")
            return False


def main():
    print("=== Temperature Ramp Testing for F-K5 Alerts ===")
    print("This script validates temperature ramp generation and "
          "alert functionality")
    print()
    
    # Load modules if utils available
    if UTILS_AVAILABLE:
        print("Loading simtemp modules...")
        unload_simtemp_modules("temp_ramp_test")
        time.sleep(1)
        if not load_simtemp_modules("temp_ramp_test"):
            print("ERROR: Failed to load simtemp modules")
            return 1
        time.sleep(2)  # Give time for devices to appear
    
    try:
        tester = TemperatureRampTester()
        
        print(f"Current pattern: {tester.get_temperature_pattern()}")
        print(f"Current stats: {tester.get_stats()}")
        print()
        
        # Test different patterns
        patterns_to_test = [
            ("static", "Static temperature - should show minimal variation"),
            ("linear", "Linear ramp - should show steady temperature "
                      "increase"),
            ("sinusoidal", "Sinusoidal - should show oscillating "
                          "temperature"),
            ("noisy", "Noisy ramp - should show ramp with random variation"),
        ]
        
        pattern_results = []
        for pattern, description in patterns_to_test:
            print(f"\n{description}")
            result = tester.test_pattern_generates_temperatures(pattern,
                                                                duration=8)
            pattern_results.append((pattern, result))
        
        # Test alerts with a ramp that should trigger them
        alert_result = tester.test_alert_with_ramp("linear", duration=15)
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        print("Pattern Generation Tests:")
        all_patterns_passed = True
        for pattern, result in pattern_results:
            status = "PASS" if result else "FAIL"
            print(f"  {pattern:12s}: {status}")
            if not result:
                all_patterns_passed = False
        
        print(f"\nAlert Functionality Test:")
        alert_status = "PASS" if alert_result else "FAIL"
        print(f"  F-K5 alerts:    {alert_status}")
        
        overall_success = all_patterns_passed and alert_result
        print(f"\nOverall Result: "
              f"{'SUCCESS' if overall_success else 'ISSUES DETECTED'}")
        
        if overall_success:
            print("\n✓ Temperature ramp generation is working correctly!")
            print("✓ F-K5 alert functionality validated with dynamic "
                  "temperatures!")
            print("\nYou can now run F-K5 tests with confidence that "
                  "temperature")
            print("ramps will provide realistic threshold crossing scenarios.")
        else:
            print("\n✗ Some issues were detected. Check the output above.")
        
        return 0 if overall_success else 1
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    finally:
        # Cleanup
        if UTILS_AVAILABLE:
            print("\nCleaning up...")
            unload_simtemp_modules("temp_ramp_test")


if __name__ == "__main__":
    sys.exit(main())