#!/usr/bin/env python3
"""
Test F-K8-TC-003: DTB driver binding and functionality verification

Device Tree Blob driver binding tests for the simtemp driver.
"""

import subprocess
import os
import pytest
from test_utils import get_shared_qemu_session


def test_dtb_overlay_exists():
    """Test that DTB overlay exists in repository - QEMU only"""
    qemu_process = get_shared_qemu_session()
    
    # This test is designed for QEMU ARM environment only
    if not qemu_process:
        pytest.skip("DTB tests require QEMU ARM environment")
    
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(test_dir))
    overlay_dir = os.path.join(project_root, 'deployment', 'qemu', 'overlay')
    overlay_dts = os.path.join(overlay_dir, 'nxp-simtemp-overlay.dts')
    overlay_dtbo = os.path.join(overlay_dir, 'nxp-simtemp-overlay.dtbo')
    
    # Check if DTS source file exists
    print(f"Checking path exist: {overlay_dts}")
    assert os.path.exists(overlay_dts), \
        f"DTB source file should exist at {overlay_dts}"
    
    # Compile DTBO if it doesn't exist
    print(f"Checking path exist: {overlay_dtbo}")
    if not os.path.exists(overlay_dtbo):
        print("DTB overlay not found - compiling from DTS source...")
        try:
            print(f"Compiling DTB overlay: {overlay_dts} -> {overlay_dtbo}")
            cmd = ["dtc", "-@", "-I", "dts", "-O", "dtb",
                   "-o", overlay_dtbo, overlay_dts]
            subprocess.run(cmd, capture_output=True, text=True,
                           check=True, cwd=overlay_dir)
            print("DTB overlay compiled successfully")
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Device Tree Compiler failed: {e.stderr}")
        except FileNotFoundError:
            pytest.skip("Device Tree Compiler (dtc) not available")
    try:
        # Verify DTBO file exists and is valid
        print(f"Checking path exist: {overlay_dtbo}")
        assert os.path.exists(overlay_dtbo), \
            f"DTB overlay should exist at {overlay_dtbo}"
        
        with open(overlay_dtbo, 'rb') as f:
            data = f.read()
            assert data[:4] == b'\xd0\x0d\xfe\xed', "Invalid DTB magic number"
            assert len(data) > 4, "DTB file too small"
    finally:
        if qemu_process:
            pass  # Don't terminate shared QEMU session


def test_dtb_driver_binding_and_functionality():
    """Combined DTB driver binding and functionality verification test
    
    QEMU only - tests DTB driver binding, property parsing, and functionality
    """
    # This test combines DTB driver binding, property parsing, and
    # functionality. It should fail until full DTB support is implemented
    
    # Test 1: DTB driver binding
    qemu_process = get_shared_qemu_session()
    
    # This test is designed for QEMU ARM environment only
    if not qemu_process:
        pytest.skip("DTB tests require QEMU ARM environment")
    
    # Skip module loading for now - these are configuration/path tests
    # TODO: Implement actual QEMU command execution for real module loading
    print("DTB test - validating configuration without module loading")
    print("(Module loading requires actual QEMU command execution)")
    
    binding_found = False

    try:
        dt_path = "/proc/device-tree/simtemp"
        
        print(f"Checking path exist: {dt_path}")
        if os.path.exists(dt_path):
            print("DTB system detected")
            # Real device tree system (ARM/QEMU)
            for root, dirs, files in os.walk(dt_path):
                if 'compatible' in files:
                    compatible_file = os.path.join(root, 'compatible')
                    try:
                        with open(compatible_file, 'rb') as f:
                            data = f.read().decode('utf-8', errors='ignore')
                            if 'nxp,simtemp' in data:
                                binding_found = True
                                break
                    except Exception:
                        continue
        else:
            # Non-DT system: Check module aliases
            test_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(test_dir)
            module_path = os.path.join(
                project_root, 'deployment', 'qemu', 'rootfs',
                'tmp', 'prebuild', 'simtemp-driver', 'nxp_simtemp.ko')
            
            print(f"Checking path exist: {module_path}")
            if os.path.exists(module_path):
                print("Non-DTB system detected - checking module aliases")
                try:
                    result = subprocess.run(['modinfo', module_path],
                                            capture_output=True, text=True,
                                            check=True)
                    if 'of:N*T*Csimtemp' in result.stdout:
                        binding_found = True
                except subprocess.CalledProcessError:
                    pass
        
        # Test 2: DTB property parsing
        properties_found = False
        sysfs_paths = ["/sys/devices/platform/simtemp",      # ARM QEMU DTB
                       "/sys/devices/platform/simtemp.0",    # x86_64 host
                       "/sys/devices/platform/simtemp@0"]    # Alternative DTB
        
        for path in sysfs_paths:
            print(f"Checking path exist: {path}")
            if os.path.exists(path):
                print("Found simtemp sysfs path")
                for prop in ['sampling_ms', 'threshold_mC', 'mode']:
                    prop_file = os.path.join(path, prop)
                    print(f"Checking path exist: {prop_file}")
                    if os.path.exists(prop_file):
                        print(f"Found simtemp sysfs property: {prop}")
                        properties_found = True
                        break
        
        # Test 3: DTB functionality
        device_file = "/sys/devices/platform/simtemp"
        functionality_working = False
        
        print(f"Checking path exist: {device_file}")
        if os.path.exists(device_file):
            print("Found simtemp device file")
            try:
                with open(device_file, 'r') as f:
                    data = f.read(64)
                    if data.strip():
                        functionality_working = True
            except Exception:
                pass
        
        # Combined failure check - should fail until full implementation
        if not binding_found:
            pytest.fail("DTB driver binding not implemented")
        
        if not properties_found:
            pytest.fail("DTB property parsing not implemented")
        
        if not functionality_working:
            pytest.fail("DTB-based driver functionality not implemented")
            
    finally:
        if qemu_process:
            pass  # Don't terminate shared QEMU session


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
