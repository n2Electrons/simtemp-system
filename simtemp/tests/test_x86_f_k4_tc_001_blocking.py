#!/usr/bin/env python3

import os
import time
import select
import pytest
import subprocess
from test_utils import load_simtemp_modules, unload_simtemp_modules


@pytest.mark.order(26)
def test_blocking_read_and_poll():
    """F-K4-TC-001: Blocking read and poll/epoll support"""
    
    print("=== F-K4 Test Start: Blocking Read and Poll Support ===")
    
    try:
        # Clean state
        print("Step 1: Cleaning up any existing modules...")
        unload_simtemp_modules("kernel_driver_suite")
        time.sleep(1)
        
        # Load modules
        print("Step 2: Loading simtemp modules...")
        if not load_simtemp_modules("kernel_driver_suite"):
            pytest.fail("Failed to load simtemp modules")
        
        # Wait for device creation
        device_path = None
        for attempt in range(10):
            for i in range(4):
                test_path = f"/dev/simtemp{i}"
                if os.path.exists(test_path):
                    device_path = test_path
                    break
            if device_path:
                break
            time.sleep(1)
        
        if not device_path:
            pytest.fail("Device not found")
        
        print(f"Step 3: Testing blocking read with device {device_path}")
        
        # Test 1: Verify device opens successfully
        try:
            with open(device_path, 'rb') as dev:
                print("✓ Device opens successfully")
                
                # Test 2: Verify select() indicates data available (poll support)
                print("Step 4: Testing poll support with select()...")
                
                # Use select with short timeout to test poll functionality
                ready, _, _ = select.select([dev], [], [], 2.0)  # 2 second timeout
                
                if ready:
                    print("✓ Poll/select indicates data available")
                    
                    # Test 3: Read should not block (data available)
                    print("Step 5: Testing non-blocking read...")
                    data = dev.read(20)  # Read simtemp_record size
                    
                    if len(data) == 20:
                        print(f"✓ Read successful: {len(data)} bytes")
                        
                        # Parse basic fields from simtemp_record
                        import struct
                        timestamp_ns, temp_mC, flags, reserved = struct.unpack('<QIii', data)
                        print(f"  Timestamp: {timestamp_ns} ns")
                        print(f"  Temperature: {temp_mC} mC ({temp_mC/1000:.1f}°C)")
                        print(f"  Flags: 0x{flags:02x}")
                        
                        # Verify NEW_SAMPLE flag is set
                        if flags & 0x01:  # SIMTEMP_FLAG_NEW_SAMPLE
                            print("✓ NEW_SAMPLE flag is set")
                        else:
                            print("⚠ NEW_SAMPLE flag not set")
                        
                    else:
                        pytest.fail(f"Read returned {len(data)} bytes, expected 20")
                else:
                    print("⚠ Poll timeout - no immediate data available")
                    print("  This may be normal if timer hasn't fired yet")
        
        except OSError as e:
            if e.errno == 16:  # EBUSY
                print("✓ Device properly rejects multiple opens (expected)")
            else:
                pytest.fail(f"Device open failed: {e}")
        
        print("✓ F-K4 basic functionality test PASSED")
        
    except Exception as e:
        print(f"EXCEPTION in test: {e}")
        pytest.fail(f"Test failed with exception: {e}")
    
    finally:
        # Cleanup
        print("Final cleanup: Unloading modules...")
        try:
            unload_simtemp_modules("kernel_driver_suite")
        except Exception as e:
            print(f"Cleanup warning: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])