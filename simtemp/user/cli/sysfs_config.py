"""
SysfsConfig Module

Handles sysfs configuration interface for the Challenge 2025 temperature sensor.
Provides methods to read and write sensor configuration via sysfs attributes.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SysfsConfig:
    """Configuration interface for simtemp sensor via sysfs."""
    
    def __init__(self, sysfs_base: str = "/sys/class/misc/simtemp"):
        """
        Initialize sysfs configuration interface.
        
        Args:
            sysfs_base: Base path to sysfs attributes
        """
        self.sysfs_base = Path(sysfs_base)
        self.attributes = {
            'sampling_ms': 'sampling_ms',
            'threshold_mC': 'threshold_mC', 
            'mode': 'mode',
            'stats': 'stats'
        }
        
    def _get_attribute_path(self, attr_name: str) -> Path:
        """Get the full path to a sysfs attribute."""
        if attr_name not in self.attributes:
            raise ValueError(f"Unknown attribute: {attr_name}")
        return self.sysfs_base / self.attributes[attr_name]
    
    def _read_attribute(self, attr_name: str) -> Optional[str]:
        """
        Read a sysfs attribute value.
        
        Args:
            attr_name: Name of the attribute
            
        Returns:
            Attribute value as string or None if error
        """
        try:
            attr_path = self._get_attribute_path(attr_name)
            if not attr_path.exists():
                logger.warning(f"Attribute {attr_name} does not exist at {attr_path}")
                return None
            
            with open(attr_path, 'r') as f:
                value = f.read().strip()
            
            logger.debug(f"Read {attr_name}: {value}")
            return value
            
        except Exception as e:
            logger.error(f"Failed to read attribute {attr_name}: {e}")
            return None
    
    def _write_attribute(self, attr_name: str, value: str) -> bool:
        """
        Write a sysfs attribute value.
        
        Args:
            attr_name: Name of the attribute
            value: Value to write as string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            attr_path = self._get_attribute_path(attr_name)
            if not attr_path.exists():
                logger.error(f"Attribute {attr_name} does not exist at {attr_path}")
                return False
            
            with open(attr_path, 'w') as f:
                f.write(str(value))
            
            logger.debug(f"Wrote {attr_name}: {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write attribute {attr_name}: {e}")
            return False
    
    def get_sampling_period(self) -> Optional[int]:
        """
        Get current sampling period in milliseconds.
        
        Returns:
            Sampling period in ms or None if error
        """
        value = self._read_attribute('sampling_ms')
        if value is not None:
            try:
                return int(value)
            except ValueError:
                logger.error(f"Invalid sampling period value: {value}")
        return None
    
    def set_sampling_period(self, period_ms: int) -> bool:
        """
        Set sampling period in milliseconds.
        
        Args:
            period_ms: Sampling period in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        if period_ms < 1 or period_ms > 60000:  # 1ms to 60s
            logger.error(f"Invalid sampling period: {period_ms} ms")
            return False
        
        return self._write_attribute('sampling_ms', str(period_ms))
    
    def get_threshold(self) -> Optional[int]:
        """
        Get current threshold in milli-degrees Celsius.
        
        Returns:
            Threshold in milli-degrees Celsius or None if error
        """
        value = self._read_attribute('threshold_mC')
        if value is not None:
            try:
                return int(value)
            except ValueError:
                logger.error(f"Invalid threshold value: {value}")
        return None
    
    def set_threshold(self, threshold_mc: int) -> bool:
        """
        Set threshold in milli-degrees Celsius.
        
        Args:
            threshold_mc: Threshold in milli-degrees Celsius
            
        Returns:
            True if successful, False otherwise
        """
        # Reasonable temperature range: -50°C to 150°C
        if threshold_mc < -50000 or threshold_mc > 150000:
            logger.error(f"Invalid threshold: {threshold_mc} milli-degrees C")
            return False
        
        return self._write_attribute('threshold_mC', str(threshold_mc))
    
    def get_mode(self) -> Optional[str]:
        """
        Get current sensor mode.
        
        Returns:
            Sensor mode ('normal', 'noisy', 'ramp') or None if error
        """
        return self._read_attribute('mode')
    
    def set_mode(self, mode: str) -> bool:
        """
        Set sensor mode.
        
        Args:
            mode: Sensor mode ('normal', 'noisy', 'ramp')
            
        Returns:
            True if successful, False otherwise
        """
        valid_modes = ['normal', 'noisy', 'ramp']
        if mode not in valid_modes:
            logger.error(f"Invalid mode: {mode}. Valid modes: {valid_modes}")
            return False
        
        return self._write_attribute('mode', mode)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get sensor statistics.
        
        Returns:
            Dictionary with statistics or empty dict if error
        """
        stats_str = self._read_attribute('stats')
        if stats_str is None:
            return {}
        
        # Parse stats format: "key1:value1,key2:value2,..."
        stats = {}
        try:
            for item in stats_str.split(','):
                if ':' in item:
                    key, value = item.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Try to convert to int, fall back to string
                    try:
                        stats[key] = int(value)
                    except ValueError:
                        stats[key] = value
            
        except Exception as e:
            logger.error(f"Failed to parse stats: {e}")
            return {}
        
        return stats
    
    def get_current_config(self) -> Dict[str, Any]:
        """
        Get all current configuration values.
        
        Returns:
            Dictionary with current configuration
        """
        config = {}
        
        sampling_ms = self.get_sampling_period()
        if sampling_ms is not None:
            config['sampling_ms'] = sampling_ms
        
        threshold_mc = self.get_threshold()
        if threshold_mc is not None:
            config['threshold_mC'] = threshold_mc
        
        mode = self.get_mode()
        if mode is not None:
            config['mode'] = mode
        
        return config
    
    def set_config(self, **kwargs) -> Dict[str, bool]:
        """
        Set multiple configuration values.
        
        Args:
            **kwargs: Configuration parameters (sampling_ms, threshold_mC, mode)
            
        Returns:
            Dictionary with results for each parameter
        """
        results = {}
        
        if 'sampling_ms' in kwargs:
            results['sampling_ms'] = self.set_sampling_period(kwargs['sampling_ms'])
        
        if 'threshold_mC' in kwargs:
            results['threshold_mC'] = self.set_threshold(kwargs['threshold_mC'])
        
        if 'mode' in kwargs:
            results['mode'] = self.set_mode(kwargs['mode'])
        
        return results
    
    def validate_sysfs_access(self) -> Dict[str, bool]:
        """
        Validate access to all sysfs attributes.
        
        Returns:
            Dictionary with access status for each attribute
        """
        access_status = {}
        
        for attr_name in self.attributes:
            attr_path = self._get_attribute_path(attr_name)
            
            exists = attr_path.exists()
            readable = False
            writable = False
            
            if exists:
                readable = os.access(attr_path, os.R_OK)
                # Don't check write access for read-only attributes like stats
                if attr_name != 'stats':
                    writable = os.access(attr_path, os.W_OK)
                else:
                    writable = True  # Stats is read-only, so mark as "writable" (accessible)
            
            access_status[attr_name] = {
                'exists': exists,
                'readable': readable,
                'writable': writable,
                'path': str(attr_path)
            }
        
        return access_status
    
    def reset_to_defaults(self) -> bool:
        """
        Reset sensor configuration to default values.
        
        Returns:
            True if all defaults were set successfully
        """
        defaults = {
            'sampling_ms': 100,      # 100ms default sampling
            'threshold_mC': 45000,   # 45°C default threshold
            'mode': 'normal'         # Normal mode
        }
        
        results = self.set_config(**defaults)
        success = all(results.values())
        
        if success:
            logger.info("Reset sensor configuration to defaults")
        else:
            logger.warning(f"Failed to reset some configuration values: {results}")
        
        return success
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        config = self.get_current_config()
        stats = self.get_stats()
        
        result = f"SysfsConfig({self.sysfs_base})\n"
        result += "Configuration:\n"
        for key, value in config.items():
            result += f"  {key}: {value}\n"
        
        if stats:
            result += "Statistics:\n"
            for key, value in stats.items():
                result += f"  {key}: {value}\n"
        
        return result


# Convenience functions
def get_sensor_config(sysfs_base: str = "/sys/class/misc/simtemp") -> Dict[str, Any]:
    """
    Get current sensor configuration.
    
    Args:
        sysfs_base: Base path to sysfs attributes
        
    Returns:
        Current configuration dictionary
    """
    config = SysfsConfig(sysfs_base)
    return config.get_current_config()


def set_sensor_config(sysfs_base: str = "/sys/class/misc/simtemp", **kwargs) -> bool:
    """
    Set sensor configuration parameters.
    
    Args:
        sysfs_base: Base path to sysfs attributes
        **kwargs: Configuration parameters
        
    Returns:
        True if all parameters were set successfully
    """
    config = SysfsConfig(sysfs_base)
    results = config.set_config(**kwargs)
    return all(results.values())


if __name__ == "__main__":
    # Simple test when run directly
    logging.basicConfig(level=logging.INFO)
    
    print("Testing SysfsConfig...")
    config = SysfsConfig()
    
    print("Validating sysfs access...")
    access = config.validate_sysfs_access()
    for attr, status in access.items():
        print(f"  {attr}: exists={status['exists']}, readable={status['readable']}, writable={status['writable']}")
    
    print("\nCurrent configuration:")
    current = config.get_current_config()
    for key, value in current.items():
        print(f"  {key}: {value}")
    
    print("\nCurrent statistics:")
    stats = config.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")