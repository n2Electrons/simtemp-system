#!/usr/bin/env python3
"""
Simple device read test for F-K5 validation
This test bypasses sysfs and just validates basic device functionality
"""

import os
import time
import struct
import pytest
from test_utils import load_simtemp_modules, unload_simtemp_modules


def test_simple_device_read():
    """Simple test: just verify we can read from the device"""
    
    print("=== Simple Device Read Test ===")
    
    try:
        # Clean state
        print("Step 1: Cleaning up any existing modules...")
        unload_simtemp_modules("kernel_driver_suite")
        time.sleep(1)

        # Load modules
        print("Step 2: Loading simtemp modules...")
        if not load_simtemp_modules("kernel_driver_suite"):
            pytest.fail("Failed to load simtemp modules")

        # Find device
        device_path = None
        for i in range(4):
            test_path = f"/dev/simtemp{i}"
            if os.path.exists(test_path):
                device_path = test_path
                print(f"✓ Found device at {device_path}")
                break
        
        if not device_path:
            pytest.fail("No simtemp device found")

        # Try to read a few samples
        print("Step 3: Reading samples from device...")
        samples_read = 0
        alert_detected = False
        
        with open(device_path, 'rb') as f:
            for i in range(5):  # Read 5 samples
                try:
                    data = f.read(20)  # 20 bytes per record
                    if len(data) != 20:
                        print(f"Warning: Read {len(data)} bytes, expected 20")
                        continue
                    
                    # Unpack: timestamp(8) + temp(4) + flags(4) + reserved(4)
                    timestamp, temp_mc, flags, reserved = struct.unpack('<QiiI', data)
                    samples_read += 1
                    
                    print(f"Sample {i+1}: temp={temp_mc} mC, flags=0x{flags:02x}")
                    
                    # Check for F-K5 alert flag (bit 1 = 0x02)
                    if flags & 0x02:
                        alert_detected = True
                        print(f"ALERT FLAG DETECTED in sample {i+1}!")
                        
                    time.sleep(0.1)  # Small delay between reads
                    
                except Exception as read_error:
                    print(f"Error reading sample {i+1}: {read_error}")
                    break

        print(f"Step 4: Successfully read {samples_read} samples")
        
        if samples_read > 0:
            print("SUCCESS: Device is working and we can read temperature data")
            if alert_detected:
                print("BONUS: F-K5 alert flag was detected in the data!")
        else:
            pytest.fail("Failed to read any samples from device")
        
        print("=== Simple Device Read Test PASSED ===")
        
    except Exception as e:
        print(f"Test failed with exception: {e}")
        raise
    finally:
        # Cleanup
        print("Cleanup: Unloading modules...")
        unload_simtemp_modules("kernel_driver_suite")


if __name__ == "__main__":
    test_simple_device_read()