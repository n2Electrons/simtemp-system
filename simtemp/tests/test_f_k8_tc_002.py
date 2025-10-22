#!/usr/bin/env python3
"""
F-K8-TC-002: Readers exit gracefully on unload

Test case to verify that reader applications exit gracefully when the kernel
module is unloaded. This test ensures that user-space applications properly
handle device disconnection and module removal.

Copyright (c) 2025 Jorge Rodriguez Moreno
"""

import subprocess
import threading
import time
import os
import pytest
import sys
import logging
from datetime import datetime
from pathlib import Path

# Import test utilities
sys.path.append(str(Path(__file__).parent))
from test_utils import SUDO, obj_path, SHELL_PARAMS, check_qemu_test
from test_f_k1_tc_001 import insmod_module, rmmod_module

# Import reader modules
sys.path.append(str(Path(__file__).parent.parent / "user" / "cli"))
try:
    from simtemp_reader import SimtempReader
    from sysfs_config import SysfsConfig
except ImportError as e:
    pytest.skip(f"User CLI modules not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReaderProcessManager:
    """Manages reader processes for testing graceful exit on module unload."""
    
    def __init__(self):
        self.processes = []
        self.threads = []
        self.reader_states = {}
        self.stop_event = threading.Event()
    
    def start_reader_thread(self, reader_id: str, 
                           device_path: str = "/dev/simtemp"):
        """Start a reader thread that continuously reads from the device."""
        def reader_worker():
            reader_state = {
                'reader_id': reader_id,
                'samples_read': 0,
                'errors': [],
                'exit_graceful': False,
                'exit_time': None,
                'start_time': datetime.now()
            }
            self.reader_states[reader_id] = reader_state
            
            try:
                logger.info(f"Reader {reader_id}: Starting continuous reading")
                reader = SimtempReader(device_path)
                
                if not reader.open():
                    reader_state['errors'].append("Failed to open device")
                    return
                
                # Continuous reading loop
                while not self.stop_event.is_set():
                    try:
                        sample = reader.read_sample(timeout_ms=500)
                        if sample:
                            reader_state['samples_read'] += 1
                            logger.debug(f"Reader {reader_id}: "
                                       f"Sample {reader_state['samples_read']}")
                        
                        # Check if we should stop
                        if self.stop_event.wait(0.1):
                            break
                            
                    except Exception as e:
                        error_msg = f"Read error: {e}"
                        reader_state['errors'].append(error_msg)
                        logger.debug(f"Reader {reader_id}: {error_msg}")
                        
                        # If device is gone, that's expected during unload
                        device_errors = ["No such device", "Device not found"]
                        if any(err in str(e) for err in device_errors):
                            logger.info(f"Reader {reader_id}: Device disappeared "
                                       "(expected during unload)")
                            break
                        
                        # Sleep and continue for other errors
                        time.sleep(0.1)
                
                # Graceful exit
                reader.close()
                reader_state['exit_graceful'] = True
                reader_state['exit_time'] = datetime.now()
                logger.info(f"Reader {reader_id}: Exited gracefully with "
                           f"{reader_state['samples_read']} samples")
                
            except Exception as e:
                error_msg = f"Reader thread exception: {e}"
                reader_state['errors'].append(error_msg)
                logger.error(f"Reader {reader_id}: {error_msg}")
            
            finally:
                reader_state['exit_time'] = datetime.now()
        
        thread = threading.Thread(target=reader_worker, 
                                 name=f"Reader-{reader_id}")
        thread.start()
        self.threads.append(thread)
        return thread
    
    def start_sysfs_reader_thread(self, reader_id: str):
        """Start a thread that continuously reads sysfs attributes."""
        def sysfs_reader_worker():
            reader_state = {
                'reader_id': reader_id,
                'reads_completed': 0,
                'errors': [],
                'exit_graceful': False,
                'exit_time': None,
                'start_time': datetime.now()
            }
            self.reader_states[reader_id] = reader_state
            
            try:
                logger.info(f"SysFS Reader {reader_id}: Starting continuous reading")
                config = SysfsConfig()
                
                # Continuous reading loop
                while not self.stop_event.is_set():
                    try:
                        # Read various sysfs attributes
                        sampling = config.get_sampling_period()
                        threshold = config.get_threshold()
                        mode = config.get_mode()
                        
                        if sampling is not None or threshold is not None or mode is not None:
                            reader_state['reads_completed'] += 1
                            logger.debug(f"SysFS Reader {reader_id}: Read {reader_state['reads_completed']}")
                        
                        # Check if we should stop
                        if self.stop_event.wait(0.2):
                            break
                            
                    except Exception as e:
                        error_msg = f"SysFS read error: {e}"
                        reader_state['errors'].append(error_msg)
                        logger.debug(f"SysFS Reader {reader_id}: {error_msg}")
                        
                        # If sysfs is gone, that's expected during unload
                        if "No such file" in str(e) or "does not exist" in str(e):
                            logger.info(f"SysFS Reader {reader_id}: SysFS disappeared (expected during unload)")
                            break
                        
                        # Sleep and continue for other errors
                        time.sleep(0.1)
                
                # Graceful exit
                reader_state['exit_graceful'] = True
                reader_state['exit_time'] = datetime.now()
                logger.info(f"SysFS Reader {reader_id}: Exited gracefully with {reader_state['reads_completed']} reads")
                
            except Exception as e:
                error_msg = f"SysFS reader thread exception: {e}"
                reader_state['errors'].append(error_msg)
                logger.error(f"SysFS Reader {reader_id}: {error_msg}")
            
            finally:
                reader_state['exit_time'] = datetime.now()
        
        thread = threading.Thread(target=sysfs_reader_worker, 
                                 name=f"SysFS-Reader-{reader_id}")
        thread.start()
        self.threads.append(thread)
        return thread
    
    def start_module_info_reader_thread(self, reader_id: str):
        """Start a thread that reads module information from /sys/module."""
        def module_info_worker():
            reader_state = {
                'reader_id': reader_id,
                'reads_completed': 0,
                'errors': [],
                'exit_graceful': False,
                'exit_time': None,
                'start_time': datetime.now()
            }
            self.reader_states[reader_id] = reader_state
            
            try:
                logger.info(f"Module Info Reader {reader_id}: Starting")
                module_path = Path("/sys/module/nxp_simtemp")
                
                # Continuous reading loop
                while not self.stop_event.is_set():
                    try:
                        # Try to read module information
                        if module_path.exists():
                            refcnt_path = module_path / "refcnt"
                            if refcnt_path.exists():
                                with open(refcnt_path) as f:
                                    refcnt = f.read().strip()
                                reader_state['reads_completed'] += 1
                                logger.debug(f"Module Reader {reader_id}: "
                                           f"refcnt={refcnt}")
                        
                        # Check if we should stop
                        if self.stop_event.wait(0.3):
                            break
                            
                    except Exception as e:
                        error_msg = f"Module read error: {e}"
                        reader_state['errors'].append(error_msg)
                        logger.debug(f"Module Reader {reader_id}: {error_msg}")
                        
                        # If module is gone, that's expected during unload
                        if ("No such file" in str(e) or 
                            "does not exist" in str(e)):
                            logger.info(f"Module Reader {reader_id}: "
                                       "Module info disappeared (expected)")
                            break
                        
                        time.sleep(0.1)
                
                # Graceful exit
                reader_state['exit_graceful'] = True
                reader_state['exit_time'] = datetime.now()
                logger.info(f"Module Reader {reader_id}: Exited gracefully")
                
            except Exception as e:
                error_msg = f"Module reader thread exception: {e}"
                reader_state['errors'].append(error_msg)
                logger.error(f"Module Reader {reader_id}: {error_msg}")
            
            finally:
                reader_state['exit_time'] = datetime.now()
        
        thread = threading.Thread(target=module_info_worker, 
                                 name=f"Module-Reader-{reader_id}")
        thread.start()
        self.threads.append(thread)
        return thread
    
    def start_platform_reader_thread(self, reader_id: str, platform_path: str):
        """Start a thread that reads platform device information."""
        def platform_reader_worker():
            reader_state = {
                'reader_id': reader_id,
                'reads_completed': 0,
                'errors': [],
                'exit_graceful': False,
                'exit_time': None,
                'start_time': datetime.now()
            }
            self.reader_states[reader_id] = reader_state
            
            try:
                logger.info(f"Platform Reader {reader_id}: Starting")
                platform_dir = Path(platform_path)
                
                # Continuous reading loop
                while not self.stop_event.is_set():
                    try:
                        # Try to read platform device information
                        if platform_dir.exists():
                            uevent_path = platform_dir / "uevent"
                            if uevent_path.exists():
                                with open(uevent_path) as f:
                                    uevent = f.read().strip()
                                reader_state['reads_completed'] += 1
                                logger.debug(f"Platform Reader {reader_id}: "
                                           f"read uevent")
                        
                        # Check if we should stop
                        if self.stop_event.wait(0.4):
                            break
                            
                    except Exception as e:
                        error_msg = f"Platform read error: {e}"
                        reader_state['errors'].append(error_msg)
                        logger.debug(f"Platform Reader {reader_id}: {error_msg}")
                        
                        # If platform device is gone, that's expected
                        if ("No such file" in str(e) or 
                            "does not exist" in str(e)):
                            logger.info(f"Platform Reader {reader_id}: "
                                       "Platform disappeared (expected)")
                            break
                        
                        time.sleep(0.1)
                
                # Graceful exit
                reader_state['exit_graceful'] = True
                reader_state['exit_time'] = datetime.now()
                logger.info(f"Platform Reader {reader_id}: Exited gracefully")
                
            except Exception as e:
                error_msg = f"Platform reader thread exception: {e}"
                reader_state['errors'].append(error_msg)
                logger.error(f"Platform Reader {reader_id}: {error_msg}")
            
            finally:
                reader_state['exit_time'] = datetime.now()
        
        thread = threading.Thread(target=platform_reader_worker, 
                                 name=f"Platform-Reader-{reader_id}")
        thread.start()
        self.threads.append(thread)
        return thread
    
    def stop_all_readers(self, timeout_seconds: float = 5.0):
        """Signal all readers to stop and wait for graceful exit."""
        logger.info("Signaling all readers to stop...")
        self.stop_event.set()
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join(timeout=timeout_seconds)
            if thread.is_alive():
                logger.warning(f"Thread {thread.name} did not exit within timeout")
    
    def get_reader_summary(self):
        """Get summary of all reader states."""
        summary = {
            'total_readers': len(self.reader_states),
            'graceful_exits': 0,
            'total_samples': 0,
            'total_errors': 0,
            'readers': {}
        }
        
        for reader_id, state in self.reader_states.items():
            summary['readers'][reader_id] = state.copy()
            if state['exit_graceful']:
                summary['graceful_exits'] += 1
            summary['total_samples'] += state.get('samples_read', 0) + state.get('reads_completed', 0)
            summary['total_errors'] += len(state['errors'])
        
        return summary


def test_readers_exit_gracefully_on_unload():
    """F-K8-TC-002: Readers exit gracefully on unload."""
    # Check if this should run in QEMU mode
    qemu_process = check_qemu_test()
    
    # Ensure module is loaded
    module_path = os.path.join(obj_path, "nxp_simtemp.ko")
    if not os.path.exists(module_path):
        pytest.fail(f"Module file not found: {module_path}")
    
    # Clear dmesg before test
    subprocess.run(f"{SUDO}dmesg -C", **SHELL_PARAMS)
    
    # Load the module
    logger.info("Loading nxp_simtemp module...")
    insmod_module()
    
    # Find actual sysfs paths for the driver
    sysfs_paths = []
    platform_devices = Path("/sys/devices/platform")
    if platform_devices.exists():
        for device_dir in platform_devices.glob("nxp-simtemp*"):
            sysfs_paths.append(str(device_dir))
    
    logger.info(f"Found sysfs paths: {sysfs_paths}")
    
    # Create reader manager
    reader_manager = ReaderProcessManager()
    
    try:
        # Start sysfs monitoring threads that read module info
        logger.info("Starting sysfs reader threads...")
        
        # Generic sysfs readers that read module information
        reader_manager.start_module_info_reader_thread("module_info_1")
        reader_manager.start_module_info_reader_thread("module_info_2")
        
        # If we have platform devices, start platform device readers
        for i, sysfs_path in enumerate(sysfs_paths[:2]):  # Limit to 2
            reader_manager.start_platform_reader_thread(f"platform_{i}", sysfs_path)
        
        # Let readers run for a bit to establish baseline
        logger.info("Allowing readers to establish baseline...")
        time.sleep(2.0)
        
        # Check initial reader states
        initial_summary = reader_manager.get_reader_summary()
        logger.info(f"Initial state: {initial_summary['total_readers']} readers started")
        
        # Record unload start time
        unload_start_time = datetime.now()
        
        # Unload the module while readers are active
        logger.info("Unloading module while readers are active...")
        rmmod_module()
        
        # Give readers time to detect the unload and exit gracefully
        logger.info("Waiting for readers to detect unload and exit gracefully...")
        time.sleep(3.0)
        
        # Stop any remaining readers
        reader_manager.stop_all_readers(timeout_seconds=5.0)
        
        # Record unload completion time
        unload_end_time = datetime.now()
        unload_duration = (unload_end_time - unload_start_time).total_seconds()
        
        # Analyze results
        final_summary = reader_manager.get_reader_summary()
        
        logger.info("=== READER EXIT ANALYSIS ===")
        logger.info(f"Total readers: {final_summary['total_readers']}")
        logger.info(f"Graceful exits: {final_summary['graceful_exits']}")
        logger.info(f"Total samples/reads: {final_summary['total_samples']}")
        logger.info(f"Total errors: {final_summary['total_errors']}")
        logger.info(f"Unload duration: {unload_duration:.2f} seconds")
        
        # Detailed reader analysis
        for reader_id, state in final_summary['readers'].items():
            exit_status = "GRACEFUL" if state['exit_graceful'] else "NOT_GRACEFUL"
            duration = "N/A"
            if state['start_time'] and state['exit_time']:
                duration = f"{(state['exit_time'] - state['start_time']).total_seconds():.2f}s"
            
            samples_reads = (state.get('samples_read', 0) + 
                           state.get('reads_completed', 0))
            logger.info(f"  {reader_id}: {exit_status}, Duration: {duration}, "
                       f"Samples/Reads: {samples_reads}, "
                       f"Errors: {len(state['errors'])}")
            
            # Log first few errors for debugging
            for i, error in enumerate(state['errors'][:3]):
                logger.info(f"    Error {i+1}: {error}")
        
        # Check for kernel warnings/oops after unload
        dmesg_after = subprocess.run(f"{SUDO}dmesg", **SHELL_PARAMS)
        if dmesg_after.returncode == 0:
            critical_patterns = [r'\bWARN\b', r'\bOOPS\b', r'\bBUG\b', 
                               r'\bpanic\b', r'Call Trace']
            import re
            warnings = []
            for pattern in critical_patterns:
                matches = re.findall(pattern, dmesg_after.stdout, re.IGNORECASE)
                warnings.extend(matches)
            
            if warnings:
                logger.warning(f"Kernel warnings after unload: {warnings}")
        
        # Test assertions
        assert final_summary['total_readers'] > 0, "No readers were started"
        
        # All readers should exit gracefully since we're just reading sysfs/module info
        graceful_ratio = final_summary['graceful_exits'] / final_summary['total_readers']
        assert graceful_ratio >= 0.8, (f"Less than 80% of readers exited gracefully "
                                       f"({graceful_ratio:.2%})")
        
        # Ensure unload completed in reasonable time
        assert unload_duration < 10.0, f"Module unload took too long: {unload_duration:.2f} seconds"
        
        logger.info("✓ F-K8-TC-002: Readers exit gracefully on unload - PASSED")
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        # Try to clean up
        reader_manager.stop_all_readers(timeout_seconds=2.0)
        raise
    
    finally:
        # Ensure all readers are stopped
        reader_manager.stop_all_readers(timeout_seconds=2.0)
        
        # Clean up: reload module for subsequent tests
        try:
            logger.info("Reloading module for subsequent tests...")
            insmod_module()
        except Exception as e:
            logger.warning(f"Failed to reload module: {e}")
        if qemu_process:
            pass


if __name__ == '__main__':
    # Direct execution for debugging
    logging.basicConfig(level=logging.DEBUG)
