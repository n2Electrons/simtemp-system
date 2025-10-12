#!/usr/bin/env python3
"""
Challenge 2025 Temperature Sensor CLI Application

This CLI application implements the Challenge 2025 system requirements:
- Configure sampling period & threshold (via sysfs and/or ioctl)
- Read from /dev/simtemp using select/poll/epoll
- Print formatted temperature readings with alerts
- Test mode: verify alert events occur within expected timeframe
"""

import argparse
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Import our custom modules
from simtemp_reader import SimtempReader
from sysfs_config import SysfsConfig
from test_mode import TestMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TemperatureSensorCLI:
    """Main CLI application for Challenge 2025 temperature sensor."""
    
    def __init__(self):
        self.device_path = "/dev/simtemp"
        self.sysfs_base = "/sys/class/misc/simtemp"
        self.reader = None
        self.config = None
        
    def setup(self):
        """Initialize the sensor interfaces."""
        try:
            self.config = SysfsConfig(self.sysfs_base)
            self.reader = SimtempReader(self.device_path)
            logger.info("Sensor interfaces initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize sensor interfaces: {e}")
            return False
    
    def configure_sensor(self, sampling_ms=None, threshold_mc=None, mode=None):
        """Configure sensor parameters via sysfs."""
        try:
            if sampling_ms is not None:
                self.config.set_sampling_period(sampling_ms)
                logger.info(f"Set sampling period to {sampling_ms} ms")
            
            if threshold_mc is not None:
                self.config.set_threshold(threshold_mc)
                logger.info(f"Set threshold to {threshold_mc/1000:.3f} °C")
            
            if mode is not None:
                self.config.set_mode(mode)
                logger.info(f"Set mode to {mode}")
                
            return True
        except Exception as e:
            logger.error(f"Failed to configure sensor: {e}")
            return False
    
    def read_sensor_data(self, duration=None, count=None):
        """
        Read sensor data and print formatted output.
        
        Format: 2025-09-22T20:15:04.123Z temp=44.1C alert=0
        """
        try:
            start_time = time.time()
            sample_count = 0
            
            logger.info("Starting sensor data reading...")
            
            while True:
                # Check exit conditions
                if duration and (time.time() - start_time) > duration:
                    break
                if count and sample_count >= count:
                    break
                
                # Read sample from device
                sample = self.reader.read_sample()
                if sample:
                    # Format timestamp
                    timestamp = datetime.fromtimestamp(
                        sample['timestamp_ns'] / 1e9
                    ).isoformat() + 'Z'
                    
                    # Format temperature
                    temp_c = sample['temp_mC'] / 1000.0
                    
                    # Check alert flags
                    alert = 1 if sample['flags'] & 0x02 else 0  # THRESHOLD_CROSSED bit
                    
                    # Print formatted output
                    print(f"{timestamp} temp={temp_c:.1f}C alert={alert}")
                    
                    sample_count += 1
                    
                    # Log alert events
                    if alert:
                        logger.warning(f"Alert triggered! Temperature: {temp_c:.1f}°C")
                
                # Small delay to prevent CPU spinning
                time.sleep(0.001)
                
        except KeyboardInterrupt:
            logger.info("Reading interrupted by user")
        except Exception as e:
            logger.error(f"Error reading sensor data: {e}")
            return False
        
        logger.info(f"Read {sample_count} samples")
        return True
    
    def show_status(self):
        """Display current sensor status and statistics."""
        try:
            stats = self.config.get_stats()
            config = self.config.get_current_config()
            
            print("\n=== Sensor Status ===")
            print(f"Sampling Period: {config['sampling_ms']} ms")
            print(f"Threshold: {config['threshold_mC']/1000:.3f} °C")
            print(f"Mode: {config['mode']}")
            print(f"Device: {self.device_path}")
            print(f"Sysfs: {self.sysfs_base}")
            
            print("\n=== Statistics ===")
            for key, value in stats.items():
                print(f"{key}: {value}")
            print()
            
        except Exception as e:
            logger.error(f"Failed to get sensor status: {e}")
    
    def run_test_mode(self):
        """
        Test mode: set a low threshold and verify alert occurs within 2 periods.
        Returns 0 on success, non-zero on failure.
        """
        logger.info("Running test mode...")
        
        test = TestMode(self.config, self.reader)
        result = test.run_threshold_test()
        
        if result:
            logger.info("Test mode PASSED")
            return 0
        else:
            logger.error("Test mode FAILED")
            return 1


def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        description="Challenge 2025 Temperature Sensor CLI Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --status                           # Show current status
  %(prog)s --config --sampling 100 --threshold 45000  # Configure sensor
  %(prog)s --read --duration 10               # Read for 10 seconds
  %(prog)s --read --count 50                  # Read 50 samples
  %(prog)s --test                             # Run test mode
        """
    )
    
    # Configuration options
    config_group = parser.add_argument_group('configuration')
    config_group.add_argument('--config', action='store_true',
                             help='Configure sensor parameters')
    config_group.add_argument('--sampling', type=int, metavar='MS',
                             help='Set sampling period in milliseconds')
    config_group.add_argument('--threshold', type=int, metavar='MILLIC',
                             help='Set threshold in milli-degrees Celsius')
    config_group.add_argument('--mode', choices=['normal', 'noisy', 'ramp'],
                             help='Set sensor mode')
    
    # Reading options
    read_group = parser.add_argument_group('reading')
    read_group.add_argument('--read', action='store_true',
                           help='Read sensor data')
    read_group.add_argument('--duration', type=float, metavar='SECONDS',
                           help='Read for specified duration')
    read_group.add_argument('--count', type=int, metavar='N',
                           help='Read specified number of samples')
    
    # Other options
    parser.add_argument('--status', action='store_true',
                       help='Show sensor status and statistics')
    parser.add_argument('--test', action='store_true',
                       help='Run test mode')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and setup CLI application
    cli = TemperatureSensorCLI()
    if not cli.setup():
        return 1
    
    # Handle different operations
    if args.test:
        return cli.run_test_mode()
    
    if args.config:
        if not cli.configure_sensor(args.sampling, args.threshold, args.mode):
            return 1
    
    if args.status:
        cli.show_status()
    
    if args.read:
        if not cli.read_sensor_data(args.duration, args.count):
            return 1
    
    # If no specific action, show status by default
    if not any([args.config, args.read, args.status, args.test]):
        cli.show_status()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())