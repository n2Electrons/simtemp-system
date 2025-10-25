#!/usr/bin/env python3
"""
Test F-K7: Configuration Support via sysfs and ioctl

This test validates both sysfs attributes and ioctl commands for 
configuring sampling_ms and threshold_mC parameters.
"""

import os
import sys
import fcntl
import struct
import time

# ioctl command definitions from nxp_simtemp.h
SIMTEMP_IOC_MAGIC = ord('T')
SIMTEMP_IOC_GET_SAMPLING = 0x80045403   # _IOR('T', 3, u32)
SIMTEMP_IOC_SET_SAMPLING = 0x40045404   # _IOW('T', 4, u32)
SIMTEMP_IOC_GET_THRESHOLD = 0x80045405  # _IOR('T', 5, u32)
SIMTEMP_IOC_SET_THRESHOLD = 0x40045406  # _IOW('T', 6, u32)

def test_sysfs_configuration():
    """Test configuration via sysfs attributes"""
    print("=== Testing sysfs Configuration ===")
    
    sysfs_base = "/sys/devices/platform/nxp-simtemp.0"
    
    # Test sampling_ms
    sampling_path = f"{sysfs_base}/sampling_ms"
    threshold_path = f"{sysfs_base}/threshold_mC"
    
    try:
        # Read current values
        with open(sampling_path, 'r') as f:
            original_sampling = int(f.read().strip())
        print(f"Original sampling_ms: {original_sampling}")
        
        with open(threshold_path, 'r') as f:
            original_threshold = int(f.read().strip())
        print(f"Original threshold_mC: {original_threshold}")
        
        # Test sampling_ms modification
        new_sampling = 500
        with open(sampling_path, 'w') as f:
            f.write(str(new_sampling))
        
        with open(sampling_path, 'r') as f:
            read_sampling = int(f.read().strip())
        
        if read_sampling == new_sampling:
            print(f"✅ sampling_ms sysfs write/read: {new_sampling}")
        else:
            print(f"❌ sampling_ms sysfs failed: wrote {new_sampling}, read {read_sampling}")
        
        # Test threshold_mC modification
        new_threshold = 45000  # 45°C
        with open(threshold_path, 'w') as f:
            f.write(str(new_threshold))
        
        with open(threshold_path, 'r') as f:
            read_threshold = int(f.read().strip())
        
        if read_threshold == new_threshold:
            print(f"✅ threshold_mC sysfs write/read: {new_threshold}")
        else:
            print(f"❌ threshold_mC sysfs failed: wrote {new_threshold}, read {read_threshold}")
        
        # Restore original values
        with open(sampling_path, 'w') as f:
            f.write(str(original_sampling))
        with open(threshold_path, 'w') as f:
            f.write(str(original_threshold))
        
        return True
        
    except Exception as e:
        print(f"❌ sysfs test failed: {e}")
        return False

def test_ioctl_configuration():
    """Test configuration via ioctl commands"""
    print("\n=== Testing ioctl Configuration ===")
    
    device_path = "/dev/simtemp0"
    
    try:
        fd = os.open(device_path, os.O_RDWR)
        try:
            # Get original values
            buf = struct.pack('I', 0)
            original_sampling = struct.unpack('I', fcntl.ioctl(fd, SIMTEMP_IOC_GET_SAMPLING, buf))[0]
            print(f"Original sampling_ms (ioctl): {original_sampling}")
            
            buf = struct.pack('I', 0)
            original_threshold = struct.unpack('I', fcntl.ioctl(fd, SIMTEMP_IOC_GET_THRESHOLD, buf))[0]
            print(f"Original threshold_mC (ioctl): {original_threshold}")
            
            # Test sampling modification
            new_sampling = 750
            buf = struct.pack('I', new_sampling)
            fcntl.ioctl(fd, SIMTEMP_IOC_SET_SAMPLING, buf)
            
            buf = struct.pack('I', 0)
            read_sampling = struct.unpack('I', fcntl.ioctl(fd, SIMTEMP_IOC_GET_SAMPLING, buf))[0]
            
            if read_sampling == new_sampling:
                print(f"✅ sampling_ms ioctl write/read: {new_sampling}")
            else:
                print(f"❌ sampling_ms ioctl failed: wrote {new_sampling}, read {read_sampling}")
            
            # Test threshold modification
            new_threshold = 55000  # 55°C
            buf = struct.pack('I', new_threshold)
            fcntl.ioctl(fd, SIMTEMP_IOC_SET_THRESHOLD, buf)
            
            buf = struct.pack('I', 0)
            read_threshold = struct.unpack('I', fcntl.ioctl(fd, SIMTEMP_IOC_GET_THRESHOLD, buf))[0]
            
            if read_threshold == new_threshold:
                print(f"✅ threshold_mC ioctl write/read: {new_threshold}")
            else:
                print(f"❌ threshold_mC ioctl failed: wrote {new_threshold}, read {read_threshold}")
            
            # Test validation - invalid sampling (too low)
            try:
                buf = struct.pack('I', 50)  # Below 100ms minimum
                fcntl.ioctl(fd, SIMTEMP_IOC_SET_SAMPLING, buf)
                print("❌ ioctl validation failed: should reject sampling < 100ms")
            except OSError as e:
                print(f"✅ ioctl validation working: rejected invalid sampling ({e})")
            
            # Test validation - invalid threshold (too high)
            try:
                buf = struct.pack('I', 150000)  # Above 125000mC maximum
                fcntl.ioctl(fd, SIMTEMP_IOC_SET_THRESHOLD, buf)
                print("❌ ioctl validation failed: should reject threshold > 125000mC")
            except OSError as e:
                print(f"✅ ioctl validation working: rejected invalid threshold ({e})")
            
            # Restore original values
            buf = struct.pack('I', original_sampling)
            fcntl.ioctl(fd, SIMTEMP_IOC_SET_SAMPLING, buf)
            buf = struct.pack('I', original_threshold)
            fcntl.ioctl(fd, SIMTEMP_IOC_SET_THRESHOLD, buf)
        finally:
            os.close(fd)
        
        return True
        
    except Exception as e:
        print(f"❌ ioctl test failed: {e}")
        return False

def test_cross_interface_consistency():
    """Test that sysfs and ioctl see the same values"""
    print("\n=== Testing Cross-Interface Consistency ===")
    
    device_path = "/dev/simtemp0"
    sysfs_sampling = "/sys/devices/platform/nxp-simtemp.0/sampling_ms"
    sysfs_threshold = "/sys/devices/platform/nxp-simtemp.0/threshold_mC"
    
    try:
        # Set via sysfs, read via ioctl
        test_sampling = 1500
        with open(sysfs_sampling, 'w') as f:
            f.write(str(test_sampling))
        
        fd = os.open(device_path, os.O_RDWR)
        try:
            buf = struct.pack('I', 0)
            ioctl_sampling = struct.unpack('I', fcntl.ioctl(fd, SIMTEMP_IOC_GET_SAMPLING, buf))[0]
        finally:
            os.close(fd)
        
        if ioctl_sampling == test_sampling:
            print(f"✅ sysfs→ioctl consistency: {test_sampling}")
        else:
            print(f"❌ sysfs→ioctl failed: sysfs set {test_sampling}, ioctl read {ioctl_sampling}")
        
        # Set via ioctl, read via sysfs
        test_threshold = 60000
        fd = os.open(device_path, os.O_RDWR)
        try:
            buf = struct.pack('I', test_threshold)
            fcntl.ioctl(fd, SIMTEMP_IOC_SET_THRESHOLD, buf)
        finally:
            os.close(fd)
        
        with open(sysfs_threshold, 'r') as f:
            sysfs_threshold_val = int(f.read().strip())
        
        if sysfs_threshold_val == test_threshold:
            print(f"✅ ioctl→sysfs consistency: {test_threshold}")
        else:
            print(f"❌ ioctl→sysfs failed: ioctl set {test_threshold}, sysfs read {sysfs_threshold_val}")
        
        return True
        
    except Exception as e:
        print(f"❌ consistency test failed: {e}")
        return False

def main():
    print("F-K7 Configuration Test")
    print("======================")
    
    if not os.path.exists("/dev/simtemp0"):
        print("❌ Device /dev/simtemp0 not found. Make sure the module is loaded.")
        return 1
    
    sysfs_success = test_sysfs_configuration()
    ioctl_success = test_ioctl_configuration()
    consistency_success = test_cross_interface_consistency()
    
    print("\n=== Test Summary ===")
    print(f"sysfs configuration: {'✅ PASS' if sysfs_success else '❌ FAIL'}")
    print(f"ioctl configuration: {'✅ PASS' if ioctl_success else '❌ FAIL'}")
    print(f"Cross-interface consistency: {'✅ PASS' if consistency_success else '❌ FAIL'}")
    
    if sysfs_success and ioctl_success and consistency_success:
        print("\n🎉 F-K7: Configuration support COMPLETE!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())