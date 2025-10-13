"""
SimtempReader Module

Handles reading from /dev/simtemp device with poll/epoll support
for the Challenge 2025 temperature sensor system.
"""

import os
import select
import struct
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SimtempReader:
    """Reader for /dev/simtemp device with poll/epoll support."""
    
    # Binary record format: timestamp_ns (8 bytes) + temp_mC (4 bytes) + flags (4 bytes)
    RECORD_FORMAT = '<QiI'  # little-endian: uint64, int32, uint32
    RECORD_SIZE = struct.calcsize(RECORD_FORMAT)
    
    # Flag definitions
    FLAG_NEW_SAMPLE = 0x01
    FLAG_THRESHOLD_CROSSED = 0x02
    
    def __init__(self, device_path: str):
        """
        Initialize the simtemp reader.
        
        Args:
            device_path: Path to the simtemp device (e.g., "/dev/simtemp")
        """
        self.device_path = device_path
        self.fd = None
        self.poll_obj = None
        
    def open(self):
        """Open the device for reading."""
        try:
            if not os.path.exists(self.device_path):
                raise FileNotFoundError(f"Device {self.device_path} not found")
            
            self.fd = os.open(self.device_path, os.O_RDONLY)
            self.poll_obj = select.poll()
            self.poll_obj.register(self.fd, select.POLLIN)
            
            logger.debug(f"Opened device {self.device_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open device {self.device_path}: {e}")
            return False
    
    def close(self):
        """Close the device."""
        if self.poll_obj and self.fd is not None:
            self.poll_obj.unregister(self.fd)
        
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
            
        self.poll_obj = None
        logger.debug(f"Closed device {self.device_path}")
    
    def __enter__(self):
        """Context manager entry."""
        if not self.open():
            raise RuntimeError(f"Failed to open device {self.device_path}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def wait_for_data(self, timeout_ms: int = 1000) -> bool:
        """
        Wait for data to be available using poll().
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            True if data is available, False on timeout
        """
        if self.poll_obj is None:
            return False
        
        try:
            events = self.poll_obj.poll(timeout_ms)
            return len(events) > 0 and (events[0][1] & select.POLLIN)
        except Exception as e:
            logger.error(f"Poll error: {e}")
            return False
    
    def read_raw_sample(self) -> Optional[bytes]:
        """
        Read a raw binary sample from the device.
        
        Returns:
            Raw binary data or None if no data available
        """
        if self.fd is None:
            return None
        
        try:
            data = os.read(self.fd, self.RECORD_SIZE)
            if len(data) == self.RECORD_SIZE:
                return data
            elif len(data) > 0:
                logger.warning(f"Partial read: got {len(data)} bytes, expected {self.RECORD_SIZE}")
            return None
            
        except BlockingIOError:
            # No data available (non-blocking mode)
            return None
        except Exception as e:
            logger.error(f"Read error: {e}")
            return None
    
    def parse_sample(self, raw_data: bytes) -> Dict:
        """
        Parse raw binary sample into a dictionary.
        
        Args:
            raw_data: Raw binary data from device
            
        Returns:
            Dictionary with parsed sample data
        """
        try:
            timestamp_ns, temp_mC, flags = struct.unpack(self.RECORD_FORMAT, raw_data)
            
            return {
                'timestamp_ns': timestamp_ns,
                'temp_mC': temp_mC,
                'flags': flags,
                'new_sample': bool(flags & self.FLAG_NEW_SAMPLE),
                'threshold_crossed': bool(flags & self.FLAG_THRESHOLD_CROSSED),
                'temperature_celsius': temp_mC / 1000.0
            }
            
        except struct.error as e:
            logger.error(f"Failed to parse sample data: {e}")
            return None
    
    def read_sample(self, timeout_ms: int = 1000) -> Optional[Dict]:
        """
        Read and parse a temperature sample.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Parsed sample dictionary or None if no data
        """
        # Ensure device is open
        if self.fd is None:
            if not self.open():
                return None
        
        # Wait for data to be available
        if not self.wait_for_data(timeout_ms):
            return None
        
        # Read raw data
        raw_data = self.read_raw_sample()
        if raw_data is None:
            return None
        
        # Parse and return
        return self.parse_sample(raw_data)
    
    def read_samples_blocking(self, count: int, timeout_per_sample: int = 5000):
        """
        Read multiple samples in blocking mode.
        
        Args:
            count: Number of samples to read
            timeout_per_sample: Timeout per sample in milliseconds
            
        Yields:
            Parsed sample dictionaries
        """
        samples_read = 0
        
        while samples_read < count:
            sample = self.read_sample(timeout_per_sample)
            if sample is not None:
                yield sample
                samples_read += 1
            else:
                logger.warning(f"Timeout waiting for sample {samples_read + 1}/{count}")
                break
    
    def read_samples_continuous(self, duration_seconds: float = None):
        """
        Read samples continuously until stopped.
        
        Args:
            duration_seconds: Optional duration limit
            
        Yields:
            Parsed sample dictionaries
        """
        start_time = time.time()
        
        while True:
            # Check duration limit
            if duration_seconds and (time.time() - start_time) >= duration_seconds:
                break
            
            sample = self.read_sample(1000)  # 1 second timeout
            if sample is not None:
                yield sample
    
    def get_device_info(self) -> Dict:
        """
        Get information about the device.
        
        Returns:
            Dictionary with device information
        """
        info = {
            'device_path': self.device_path,
            'is_open': self.fd is not None,
            'record_size': self.RECORD_SIZE,
            'record_format': self.RECORD_FORMAT
        }
        
        if os.path.exists(self.device_path):
            stat = os.stat(self.device_path)
            info.update({
                'exists': True,
                'mode': oct(stat.st_mode),
                'uid': stat.st_uid,
                'gid': stat.st_gid,
                'size': stat.st_size,
                'mtime': stat.st_mtime
            })
        else:
            info['exists'] = False
        
        return info


# Convenience functions
def read_single_sample(device_path: str = "/dev/simtemp", timeout_ms: int = 5000) -> Optional[Dict]:
    """
    Read a single temperature sample.
    
    Args:
        device_path: Path to simtemp device
        timeout_ms: Timeout in milliseconds
        
    Returns:
        Parsed sample dictionary or None
    """
    try:
        with SimtempReader(device_path) as reader:
            return reader.read_sample(timeout_ms)
    except Exception as e:
        logger.error(f"Failed to read single sample: {e}")
        return None


def monitor_temperature(device_path: str = "/dev/simtemp", 
                       duration: float = None,
                       callback=None):
    """
    Monitor temperature with optional callback.
    
    Args:
        device_path: Path to simtemp device
        duration: Duration in seconds (None for infinite)
        callback: Function to call for each sample
    """
    try:
        with SimtempReader(device_path) as reader:
            for sample in reader.read_samples_continuous(duration):
                if callback:
                    callback(sample)
                else:
                    timestamp = time.strftime('%Y-%m-%dT%H:%M:%S', 
                                           time.gmtime(sample['timestamp_ns'] / 1e9))
                    print(f"{timestamp}Z temp={sample['temperature_celsius']:.1f}C "
                          f"alert={int(sample['threshold_crossed'])}")
                    
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")


if __name__ == "__main__":
    # Simple test when run directly
    logging.basicConfig(level=logging.INFO)
    
    print("Testing SimtempReader...")
    sample = read_single_sample()
    if sample:
        print(f"Sample: {sample}")
    else:
        print("No sample received")
    
    print("Starting 10-second monitoring...")
    monitor_temperature(duration=10.0)