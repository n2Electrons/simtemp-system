#!/usr/bin/env python3

import os
import time
import pytest
from test_utils import load_simtemp_modules, unload_simtemp_modules


def test_device_node_exists():
    """F-K3-TC-001: Node exists"""
    
    try:
        # Clean state: ensure modules are unloaded first
        unload_simtemp_modules("kernel_driver_suite")
        time.sleep(1)  # Give time for cleanup
        
        # Load modules using centralized function for kernel_driver_suite
        if not load_simtemp_modules("kernel_driver_suite"):
            pytest.fail("Failed to load simtemp modules")
        
        # Give time for device node creation in Jenkins environment
        max_wait_time = 10  # seconds
        wait_interval = 1   # seconds
        
        device_found = False
        device_path = None
        
        for attempt in range(max_wait_time):
            time.sleep(wait_interval)
            
            # Check for any simtemp device (driver creates simtemp0, simtemp1, etc.)
            for i in range(4):  # Driver allocates up to 4 devices
                test_path = f"/dev/simtemp{i}"
                if os.path.exists(test_path):
                    # Verify it's a character device
                    import stat
                    try:
                        device_stat = os.stat(test_path)
                        if stat.S_ISCHR(device_stat.st_mode):
                            device_found = True
                            device_path = test_path
                            major = os.major(device_stat.st_rdev)
                            minor = os.minor(device_stat.st_rdev)
                            print(f"✓ Character device found at {device_path}")
                            print(f"  Device major:minor = {major}:{minor}")
                            break
                        else:
                            print(f"Warning: {test_path} exists but is not a character device")
                    except Exception as e:
                        print(f"Warning: Could not stat {test_path}: {e}")
            
            if device_found:
                break
                
            print(f"Attempt {attempt + 1}/{max_wait_time}: No simtemp devices ready, waiting...")
        
        # If we get here and device_found is True, test passed
        if device_found:
            return
        
        # Additional debugging: check if modules are actually loaded
        import subprocess
        lsmod_result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if lsmod_result.returncode == 0:
            loaded_modules = [line for line in lsmod_result.stdout.split('\n') 
                            if 'simtemp' in line]
            print(f"Debug: Loaded simtemp modules: {loaded_modules}")
        
        # Additional debugging: list all devices in /dev
        try:
            dev_result = subprocess.run(['ls', '-la', '/dev/'], 
                                      capture_output=True, text=True)
            if dev_result.returncode == 0:
                simtemp_devices = [line for line in dev_result.stdout.split('\n') 
                                 if 'simtemp' in line]
                print(f"Debug: Found simtemp devices: {simtemp_devices}")
            else:
                print("Debug: Could not list /dev/ directory")
        except Exception as e:
            print(f"Debug: Error listing /dev/: {e}")
        
        # Check device exists
        device_path = "/dev/simtemp0"
        if not os.path.exists(device_path):
            # Try alternative device nodes in case of numbering differences
            for i in range(4):  # Check simtemp0 through simtemp3
                alt_path = f"/dev/simtemp{i}"
                if os.path.exists(alt_path):
                    print(f"✓ Device node found at {alt_path}")
                    return
            
            # Additional debugging: check dmesg for device creation messages
            try:
                dmesg_result = subprocess.run(['dmesg'], capture_output=True, text=True)
                if dmesg_result.returncode == 0:
                    simtemp_msgs = [line for line in dmesg_result.stdout.split('\n')[-50:]
                                  if 'simtemp' in line.lower()]
                    print(f"Debug: Recent simtemp dmesg messages: {simtemp_msgs}")
            except Exception as e:
                print(f"Debug: Could not check dmesg: {e}")
            
            # List available simtemp devices for debugging
            try:
                ls_result = subprocess.run(['ls', '-la', '/dev/simtemp*'], 
                                         capture_output=True, text=True)
                if ls_result.returncode == 0:
                    print(f"Available simtemp devices:\n{ls_result.stdout}")
                else:
                    print("No simtemp devices found")
            except Exception as e:
                print(f"Could not list simtemp devices: {e}")
            
            pytest.fail(f"Device not found: {device_path}")
        
        print(f"✓ Device node exists at {device_path}")
        
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")
    
    finally:
        # Cleanup: unload modules to leave clean state for other tests
        try:
            unload_simtemp_modules("kernel_driver_suite")
        except Exception:
            pass  # Ignore cleanup errors


if __name__ == '__main__':
    pytest.main([__file__, '-v'])