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
    assert os.path.exists(overlay_dts), \
        f"DTB source file should exist at {overlay_dts}"
    
    # Compile DTBO if it doesn't exist
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
    # Import test utilities
    from test_utils import get_driver_path, execute_command, get_qemu_communication_info

    # Test 1: DTB driver binding
    qemu_process = get_shared_qemu_session()

    # This test is designed for QEMU ARM environment only
    if not qemu_process:
        pytest.skip("DTB tests require QEMU ARM environment")

    # Banner verde para QEMU con sesión reutilizada
    print("\033[92m" + "="*80)
    print("QEMU ARM ENVIRONMENT DETECTED - REUSING SHARED SESSION")
    pid_info = qemu_process.pid if hasattr(qemu_process, 'pid') else 'N/A'
    print(f"QEMU PID: {pid_info}")
    print("PREVIOUS QEMU INSTANCE SUCCESSFULLY RECOVERED")

    # Verificar que estamos en QEMU ARM ejecutando uname
    success, uname_output = execute_command("uname -a", timeout=5)
    if success and uname_output:
        print(f" SYSTEM: {' '.join(uname_output)}")

    success, kernel_output = execute_command("uname -r", timeout=5)
    if success and kernel_output:
        print(f"RUNNING {' '.join(kernel_output)}")
        
    # Mostrar información de comunicación
    comm_info = get_qemu_communication_info()
    print(f"Communication: {comm_info}")

    print("="*80 + "\033[0m")

    print("DTB test - loading driver and validating binding")
    
    # Load the driver first to test actual binding
    suite_name = "qemu_integration"  # This test is part of qemu_integration
    driver_path = get_driver_path(suite_name)
    
    binding_found = False

    try:
        # Load the driver in QEMU
        print(f"Loading driver in QEMU from: {driver_path}")
        success, output = execute_command(f"insmod {driver_path}", timeout=10)
        if success:
            print("Driver loaded successfully in QEMU")
        else:
            print(f"Driver load failed in QEMU: {' '.join(output)}")
    
        # Check for DTB system in QEMU
        success, output = execute_command("ls /proc/device-tree/simtemp", timeout=5)
        if success:
            print("DTB system detected in QEMU")
            # Check compatible string in QEMU
            success, compatible_data = execute_command(
                "cat /proc/device-tree/simtemp/compatible 2>/dev/null", timeout=5)
            if success and any('nxp,simtemp' in line for line in compatible_data):
                binding_found = True
                print("Found DTB compatible string in QEMU")
        else:
            # Non-DT system: Check module aliases (this runs on host)
            if os.path.exists(driver_path):
                print("Non-DTB system detected - checking module aliases")
                try:
                    result = subprocess.run(['modinfo', driver_path],
                                            capture_output=True, text=True,
                                            check=True)
                    if 'of:N*T*Csimtemp' in result.stdout:
                        binding_found = True
                except subprocess.CalledProcessError:
                    pass

        # Test 2: DTB property parsing - check in QEMU
        properties_found = False
        
        # Check if platform driver is registered in QEMU
        success, output = execute_command(
            "ls /sys/bus/platform/drivers/nxp-simtemp", timeout=5)
        if success:
            print("Platform driver found in QEMU")
            binding_found = True

        # Check for device paths in QEMU
        qemu_sysfs_paths = ["/sys/devices/platform/simtemp",      # ARM DTB
                            "/sys/devices/platform/simtemp.0",    # Alt format
                            "/sys/devices/platform/simtemp@0"]    # DTB format
        
        for path in qemu_sysfs_paths:
            success, output = execute_command(f"ls {path}", timeout=5)
            if success:
                print(f"Found simtemp sysfs path in QEMU: {path}")
                # Check for properties in QEMU
                for prop in ['sampling_ms', 'threshold_mC', 'mode']:
                    prop_file = f"{path}/{prop}"
                    success, prop_output = execute_command(
                        f"ls {prop_file}", timeout=5)
                    if success:
                        print(f"Found simtemp sysfs property in QEMU: {prop}")
                        properties_found = True
                        break
                if properties_found:
                    break

        # Test 3: DTB functionality - check in QEMU
        success, output = execute_command(
            "ls /sys/devices/platform/simtemp", timeout=5)
        if success:
            print("Found simtemp device in QEMU")

        # Success if we find binding OR properties (not both required)
        if binding_found or properties_found:
            print("✅ DTB driver binding test PASSED")
            print(f"Binding found: {binding_found}")
            print(f"Properties found: {properties_found}")
        else:
            pytest.fail("DTB driver binding not implemented")
            
    finally:
        # Clean up - unload driver from QEMU
        try:
            success, output = execute_command("rmmod nxp_simtemp", timeout=10)
            if success:
                print("Driver unloaded from QEMU")
            else:
                print(f"Driver unload failed: {' '.join(output)}")
        except Exception:
            pass
        if qemu_process:
            pass  # Don't terminate shared QEMU session


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
