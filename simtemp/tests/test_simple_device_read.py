#!/usr/bin/env python3
"""
Simple device read test for F-K5 validation
This test bypasses sysfs and just validates basic device functionality
"""

import os
import time
import struct
import subprocess
import pytest
from test_utils import load_simtemp_modules, unload_simtemp_modules, SUDO


@pytest.mark.order(20)
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

        # Try to read a few samples using automatic sudo detection
        print("Step 3: Reading samples from device...")
        samples_read = 0
        alert_detected = False
        
        # Try direct access first, fall back to sudo if needed
        try:
            with open(device_path, 'rb') as f:
                for i in range(5):  # Read 5 samples
                    try:
                        data = f.read(20)  # 20 bytes per record
                        if len(data) != 20:
                            print(f"Warning: Read {len(data)} bytes, expected 20")
                            continue
                        
                        # Unpack: timestamp(8) + temp(4) + flags(4) + reserved(4)
                        timestamp, temp_mc, flags, reserved = struct.unpack(
                            '<QiiI', data)
                        samples_read += 1
                        
                        print(f"Sample {i+1}: temp={temp_mc} mC, "
                              f"flags=0x{flags:02x}")
                        
                        # Check for F-K5 alert flag (bit 1 = 0x02)
                        if flags & 0x02:
                            alert_detected = True
                            print(f"ALERT FLAG DETECTED in sample {i+1}!")
                            
                        time.sleep(0.1)  # Small delay between reads
                        
                    except Exception as read_error:
                        print(f"Error reading sample {i+1}: {read_error}")
                        break
        except PermissionError:
            print(f"⚠ Need elevated privileges - using {SUDO}dd command")
            # Use the same sudo approach as F-K5 tests
            for i in range(5):
                try:
                    # Use dd to read exactly 20 bytes, with hex conversion like F-K5
                    cmd = f"{SUDO}dd if={device_path} bs=20 count=1 skip={i} 2>/dev/null | hexdump -v -e '8/1 \"%02x\" \"\\n\"'"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0 or not result.stdout.strip():
                        print(f"Error reading sample {i+1} with sudo")
                        continue
                    
                    # Parse hex output back to binary (like F-K5)
                    hex_data = result.stdout.strip().replace('\n', '')
                    if len(hex_data) != 40:  # 20 bytes * 2 hex chars = 40 chars
                        print(f"Warning: Read {len(hex_data)//2} bytes, expected 20")
                        continue
                    
                    # Convert hex to binary data
                    binary_data = bytes.fromhex(hex_data)
                    timestamp, temp_mc, flags, reserved = struct.unpack(
                        '<QiiI', binary_data)
                    samples_read += 1
                    
                    print(f"Sample {i+1}: temp={temp_mc} mC, "
                          f"flags=0x{flags:02x}")
                    
                    # Check for F-K5 alert flag (bit 1 = 0x02)
                    if flags & 0x02:
                        alert_detected = True
                        print(f"ALERT FLAG DETECTED in sample {i+1}!")
                        
                    time.sleep(0.1)  # Small delay between reads
                    
                except Exception as read_error:
                    print(f"Error reading sample {i+1} with sudo: {read_error}")
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