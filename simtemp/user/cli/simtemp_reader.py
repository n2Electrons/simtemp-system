"""
SimtempReader Module - Minimal temperature monitoring
"""

import os
import struct
import time
from typing import Optional


class SimtempReader:
    """Minimal reader for /dev/simtemp device."""
    
    RECORD_FORMAT = '<QiI'  # timestamp_ns (8), temp_mC (4), flags (4)
    RECORD_SIZE = struct.calcsize(RECORD_FORMAT)
    
    def __init__(self, device_path: str = "/dev/simtemp"):
        self.device_path = device_path
        self.fd = None
        
    def open(self):
        """Open device for reading."""
        try:
            if not os.path.exists(self.device_path):
                raise FileNotFoundError(f"Device {self.device_path} not found")
            self.fd = os.open(self.device_path, os.O_RDONLY)
            return True
        except Exception:
            return False
    
    def close(self):
        """Close device."""
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def read_temperature(self) -> Optional[float]:
        """
        Read current temperature in Celsius.
        
        Returns:
            Temperature in Celsius or None if no data
        """
        if self.fd is None:
            return None
            
        try:
            data = os.read(self.fd, self.RECORD_SIZE)
            if len(data) == self.RECORD_SIZE:
                _, temp_mC, _ = struct.unpack(self.RECORD_FORMAT, data)
                return temp_mC / 1000.0
        except Exception:
            pass
        return None
    
    def read_sample(self, timeout_ms: int = 1000) -> Optional[dict]:
        """
        Read and parse a temperature sample (for compatibility).
        
        Args:
            timeout_ms: Timeout in milliseconds (ignored in simple version)
            
        Returns:
            Dictionary with sample data or None if no data
        """
        if self.fd is None:
            return None
            
        try:
            data = os.read(self.fd, self.RECORD_SIZE)
            if len(data) == self.RECORD_SIZE:
                timestamp_ns, temp_mC, flags = struct.unpack(
                    self.RECORD_FORMAT, data)
                return {
                    'timestamp_ns': timestamp_ns,
                    'temp_mC': temp_mC,
                    'flags': flags,
                    'temperature_celsius': temp_mC / 1000.0,
                    'threshold_crossed': bool(flags & 0x02)
                }
        except Exception:
            pass
        return None
    
    def get_device_info(self) -> dict:
        """
        Get information about the device (for compatibility).
        
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
            try:
                stat = os.stat(self.device_path)
                info.update({
                    'exists': True,
                    'mode': oct(stat.st_mode),
                    'size': stat.st_size
                })
            except OSError:
                info['exists'] = True  # File exists but may not be accessible
        else:
            info['exists'] = False
        
        return info


def read_temperature(device_path: str = "/dev/simtemp") -> Optional[float]:
    """
    Read a single temperature value.
    
    Returns:
        Temperature in Celsius or None
    """
    try:
        with SimtempReader(device_path) as reader:
            return reader.read_temperature()
    except Exception:
        return None


def monitor_temperature(device_path: str = "/dev/simtemp",
                        duration: float = None):
    """
    Monitor temperature continuously.
    
    Args:
        device_path: Path to simtemp device
        duration: Duration in seconds (None for infinite)
    """
    start_time = time.time()
    
    try:
        with SimtempReader(device_path) as reader:
            while True:
                if duration and (time.time() - start_time) >= duration:
                    break
                    
                temp = reader.read_temperature()
                if temp is not None:
                    timestamp = time.strftime('%H:%M:%S', time.localtime())
                    print(f"{timestamp} Temperature: {temp:.1f}°C")
                
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nMonitoring stopped")


if __name__ == "__main__":
    print("Reading temperature...")
    temp = read_temperature()
    if temp is not None:
        print(f"Current temperature: {temp:.1f}°C")
    else:
        print("No temperature data available")
    
    print("\nStarting monitoring (Ctrl+C to stop)...")
    monitor_temperature()
