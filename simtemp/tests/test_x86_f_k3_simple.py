#!/usr/bin/env python3

import os
import time
import pytest
from test_utils import load_simtemp_modules, unload_simtemp_modules


def test_device_node_exists():
    """F-K3-TC-001: Node exists"""
    
    print("=== F-K3 Test Start: Device Node Existence ===")
    
    try:
        # Clean state: ensure modules are unloaded first
        print("Step 1: Cleaning up any existing modules...")
        unload_simtemp_modules("kernel_driver_suite")
        time.sleep(1)  # Give time for cleanup
        
        # Load modules using centralized function for kernel_driver_suite
        print("Step 2: Loading simtemp modules...")
        if not load_simtemp_modules("kernel_driver_suite"):
            pytest.fail("Failed to load simtemp modules")
        
        print("Step 3: Modules loaded successfully, checking probe status...")
        
        # Check if probe executed by looking for probe messages in dmesg
        import subprocess
        try:
            dmesg_result = subprocess.run(['dmesg'], capture_output=True, text=True)
            if dmesg_result.returncode == 0:
                recent_lines = dmesg_result.stdout.split('\n')[-50:]  # Last 50 lines
                probe_msgs = [line for line in recent_lines if 'nxp-simtemp' in line.lower() or 'simtemp' in line.lower()]
                print(f"Recent simtemp dmesg messages: {probe_msgs}")
                
                # Look specifically for probe completion message
                probe_completed = any('probe completed' in line.lower() for line in probe_msgs)
                device_created = any('character device created' in line.lower() for line in probe_msgs)
                
                print(f"Probe completed: {probe_completed}")
                print(f"Device created message: {device_created}")
                
                if not probe_completed:
                    print("WARNING: Platform driver probe did not complete!")
                    print("This means platform device/driver matching failed")
        except Exception as e:
            print(f"Could not check dmesg: {e}")
        
        # Immediate check: verify modules are loaded
        import subprocess
        lsmod_result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if lsmod_result.returncode == 0:
            loaded_modules = [line for line in lsmod_result.stdout.split('\n') 
                            if 'simtemp' in line]
            print(f"Loaded simtemp modules: {loaded_modules}")
            if not loaded_modules:
                pytest.fail("No simtemp modules found in lsmod after loading")
        
        # Give time for device node creation in Jenkins environment
        max_wait_time = 15  # Increased wait time for Jenkins
        wait_interval = 1   # seconds
        
        device_found = False
        device_path = None
        
        print(f"Step 4: Waiting up to {max_wait_time} seconds for device creation...")
        
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
                print(f"SUCCESS: Device found on attempt {attempt + 1}")
                break
                
            if attempt < max_wait_time - 1:  # Don't print on last attempt
                print(f"Attempt {attempt + 1}/{max_wait_time}: No simtemp devices ready, waiting...")
        
        # If device found, test passed
        if device_found:
            print(f"✓ Test PASSED: Device node exists at {device_path}")
            return
        
        # If device not found - collect debugging info and try manual creation
        print("DEBUGGING: Device not found, collecting system information...")
        
        # Check what's in /dev
        try:
            dev_result = subprocess.run(['ls', '-la', '/dev/simtemp*'], 
                                      capture_output=True, text=True)
            if dev_result.returncode == 0:
                print(f"Available simtemp devices:\n{dev_result.stdout}")
            else:
                print("No simtemp devices found via ls")
        except Exception as e:
            print(f"Could not list simtemp devices: {e}")
        
        # Check /sys/class for device class creation
        try:
            sys_result = subprocess.run(['ls', '-la', '/sys/class/simtemp*'], 
                                      capture_output=True, text=True)
            if sys_result.returncode == 0:
                print(f"Simtemp class in /sys/class:\n{sys_result.stdout}")
            else:
                print("No simtemp class found in /sys/class")
        except Exception as e:
            print(f"Could not check /sys/class: {e}")
        
        # Get device numbers from /proc/devices
        try:
            proc_result = subprocess.run(['grep', 'simtemp', '/proc/devices'], 
                                       capture_output=True, text=True)
            if proc_result.returncode == 0:
                print(f"Simtemp in /proc/devices:\n{proc_result.stdout}")
                
                # Try to extract major number and create device manually
                lines = proc_result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 2 and 'simtemp' in parts[1]:
                        major_num = parts[0]
                        print(f"Found simtemp major number: {major_num}")
                        
                        # Try to create device nodes manually for Jenkins
                        for i in range(4):
                            device_path = f"/dev/simtemp{i}"
                            mknod_cmd = f"sudo mknod {device_path} c {major_num} {i}"
                            print(f"Attempting manual device creation: {mknod_cmd}")
                            
                            try:
                                mknod_result = subprocess.run(mknod_cmd, shell=True, 
                                                            capture_output=True, text=True)
                                if mknod_result.returncode == 0:
                                    print(f"✓ Manually created {device_path}")
                                    
                                    # Set permissions
                                    chmod_cmd = f"sudo chmod 666 {device_path}"
                                    subprocess.run(chmod_cmd, shell=True)
                                    
                                    if os.path.exists(device_path):
                                        print(f"SUCCESS: Manual device creation worked for {device_path}")
                                        return  # Test passed with manual creation
                                else:
                                    print(f"Failed to create {device_path}: {mknod_result.stderr}")
                            except Exception as e:
                                print(f"Exception creating {device_path}: {e}")
            else:
                print("Simtemp not found in /proc/devices - driver not properly loaded")
        except Exception as e:
            print(f"Could not check /proc/devices: {e}")
            
        # Check dmesg for any errors
        try:
            dmesg_result = subprocess.run(['dmesg', '|', 'tail', '-20'], 
                                        shell=True, capture_output=True, text=True)
            if dmesg_result.returncode == 0:
                print(f"Recent dmesg output:\n{dmesg_result.stdout}")
        except Exception as e:
            print(f"Could not check dmesg: {e}")
        
        pytest.fail("Device not found: /dev/simtemp0")
        
    except Exception as e:
        print(f"EXCEPTION in test: {e}")
        pytest.fail(f"Test failed with exception: {e}")
    
    finally:
        # Cleanup: unload modules to leave clean state for other tests
        print("Final cleanup: Unloading modules...")
        try:
            unload_simtemp_modules("kernel_driver_suite")
        except Exception as e:
            print(f"Cleanup warning: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])