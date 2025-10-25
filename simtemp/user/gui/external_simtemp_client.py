#!/usr/bin/env python3
"""
External SimTemp Client for GUI
Copyright (c) 2025 Jorge Rodriguez Moreno

Client for receiving real-time temperature data from SimTemp sensor
via TCP socket connection to QEMU target ARM system.

This client is designed for external GUI applications that need to
monitor temperature data from a remote SimTemp sensor running on
an ARM target connected via QEMU.
"""

import socket
import threading
import time
import logging
from typing import Dict, Optional, Callable, Any

logger = logging.getLogger(__name__)


class ExternalSimTempClient:
    """
    External client for receiving real-time temperature data from SimTemp
    sensor via TCP socket connection.
    
    This client connects to the QEMU socket port that forwards data from
    the SimTemp sensor on the ARM target system.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 4445,
                 timeout: int = 5):
        """
        Initialize the external SimTemp client.
        
        Args:
            host: Target host IP address (QEMU host)
            port: TCP socket port (QEMU socket port for SimTemp)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False
        self.running = False
        
        # Threading for data reception
        self.data_thread = None
        self.data_callback = None
        
        # Data buffering
        self.latest_sample = None
        self.sample_count = 0
        
        # Connection status
        self.last_data_time = None
        self.connection_errors = 0
        
    def connect(self) -> bool:
        """
        Connect to the SimTemp sensor via TCP socket.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            # Try to read welcome message
            try:
                welcome = self.socket.recv(1024).decode('ascii', errors='ignore')
                logger.info(f"Connected to SimTemp sensor: {welcome.strip()}")
            except socket.timeout:
                logger.info(f"Connected to SimTemp sensor at {self.host}:{self.port}")
            
            self.connected = True
            self.connection_errors = 0
            logger.info(f"Successfully connected to {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.host}:{self.port}: {e}")
            self.connected = False
            self.connection_errors += 1
            return False
    
    def disconnect(self):
        """Disconnect from the SimTemp sensor."""
        self.connected = False
        self.running = False
        
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=2.0)
        
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        
        logger.info("Disconnected from SimTemp sensor")
    
    def send_command(self, command: str) -> Optional[str]:
        """
        Send a command to the SimTemp sensor.
        
        Args:
            command: Command string to send
            
        Returns:
            str: Response from sensor or None if error
        """
        if not self.connected:
            logger.error("Not connected to sensor")
            return None
        
        try:
            # Send command with newline
            self.socket.send(f"{command}\\n".encode('ascii'))
            
            # Receive response
            response = self.socket.recv(1024).decode('ascii', errors='ignore')
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            return None
    
    def get_temperature(self) -> Optional[float]:
        """
        Get current temperature from sensor.
        
        Returns:
            float: Temperature in Celsius or None if error
        """
        response = self.send_command("GET_TEMP")
        if response and response.startswith("TEMP:"):
            try:
                # Parse response like "TEMP: 25.50°C"
                temp_str = response.split(":")[1].strip().replace("°C", "")
                return float(temp_str)
            except (ValueError, IndexError):
                logger.error(f"Failed to parse temperature response: {response}")
        return None
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Get sensor status information.
        
        Returns:
            dict: Status dictionary or None if error
        """
        response = self.send_command("STATUS")
        if response and response.startswith("STATUS:"):
            try:
                # Parse status response
                status_str = response.split(":", 1)[1].strip()
                status = {"raw_status": status_str}
                
                # Try to extract key information
                if "Temp=" in status_str:
                    temp_part = status_str.split("Temp=")[1].split(",")[0]
                    temp_val = float(temp_part.replace("°C", ""))
                    status["temperature"] = temp_val
                
                if "Sampling=" in status_str:
                    sampling_part = status_str.split("Sampling=")[1].split(",")[0]
                    sampling_val = int(sampling_part.replace("ms", ""))
                    status["sampling_ms"] = sampling_val
                
                if "Threshold=" in status_str:
                    threshold_part = status_str.split("Threshold=")[1].split(",")[0]
                    threshold_val = float(threshold_part.replace("°C", ""))
                    status["threshold_celsius"] = threshold_val
                
                if "Uptime=" in status_str:
                    uptime_part = status_str.split("Uptime=")[1].split(",")[0]
                    uptime_val = float(uptime_part.replace("s", ""))
                    status["uptime_seconds"] = uptime_val
                
                return status
                
            except Exception as e:
                logger.error(f"Failed to parse status response: {e}")
        return None
    
    def set_data_callback(self, callback: Callable[[Dict], None]):
        """
        Set callback function for receiving temperature data.
        
        Args:
            callback: Function to call when new data arrives
        """
        self.data_callback = callback
    
    def start_monitoring(self) -> bool:
        """
        Start monitoring temperature data in background thread.
        
        Returns:
            bool: True if monitoring started successfully
        """
        if not self.connected:
            logger.error("Must be connected before starting monitoring")
            return False
        
        if self.running:
            logger.warning("Monitoring already running")
            return True
        
        self.running = True
        self.data_thread = threading.Thread(target=self._data_monitoring_loop, daemon=True)
        self.data_thread.start()
        
        logger.info("Started temperature monitoring")
        return True
    
    def stop_monitoring(self):
        """Stop temperature monitoring."""
        self.running = False
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=2.0)
        logger.info("Stopped temperature monitoring")
    
    def _data_monitoring_loop(self):
        """Background thread loop for monitoring temperature data."""
        logger.info("Temperature monitoring loop started")
        
        while self.running and self.connected:
            try:
                # Get current temperature and status
                temperature = self.get_temperature()
                status = self.get_status()
                
                if temperature is not None:
                    # Create sample data structure
                    sample = {
                        'timestamp_ns': int(time.time() * 1e9),
                        'temp_mC': int(temperature * 1000),
                        'temperature_celsius': temperature,
                        'gui_timestamp': time.time(),
                        'sample_id': self.sample_count,
                        'source': 'external_tcp'
                    }
                    
                    # Add status information if available
                    if status:
                        sample.update(status)
                    
                    # Update internal state
                    self.latest_sample = sample
                    self.sample_count += 1
                    self.last_data_time = time.time()
                    
                    # Call data callback if set
                    if self.data_callback:
                        try:
                            self.data_callback(sample)
                        except Exception as e:
                            logger.error(f"Error in data callback: {e}")
                    
                    # Log sample received
                    logger.debug(f"Sample {self.sample_count}: {temperature:.2f}°C")
                else:
                    logger.warning("No temperature data received")
                
                # Wait before next sample
                time.sleep(1.0)  # 1 second polling interval
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.connection_errors += 1
                if self.connection_errors > 5:
                    logger.error("Too many connection errors, stopping monitoring")
                    break
                time.sleep(2.0)  # Wait longer on error
        
        logger.info("Temperature monitoring loop stopped")
    
    def get_latest_sample(self) -> Optional[Dict]:
        """
        Get the latest temperature sample.
        
        Returns:
            dict: Latest sample data or None if no data available
        """
        return self.latest_sample
    
    def is_alive(self) -> bool:
        """
        Check if the connection is alive and receiving data.
        
        Returns:
            bool: True if receiving data recently
        """
        if not self.connected or not self.last_data_time:
            return False
        
        # Consider alive if data received within last 10 seconds
        return (time.time() - self.last_data_time) < 10.0
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information and statistics.
        
        Returns:
            dict: Connection information
        """
        return {
            'host': self.host,
            'port': self.port,
            'connected': self.connected,
            'running': self.running,
            'sample_count': self.sample_count,
            'connection_errors': self.connection_errors,
            'last_data_time': self.last_data_time,
            'is_alive': self.is_alive()
        }


def main():
    """Test the external SimTemp client."""
    import argparse
    
    parser = argparse.ArgumentParser(description='External SimTemp Client Test')
    parser.add_argument('--host', default='127.0.0.1', help='SimTemp host')
    parser.add_argument('--port', type=int, default=4445, help='SimTemp port')
    parser.add_argument('--test', action='store_true', help='Run test mode')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create client
    client = ExternalSimTempClient(args.host, args.port)
    
    # Test connection
    if not client.connect():
        print(f"Failed to connect to SimTemp sensor at {args.host}:{args.port}")
        return 1
    
    if args.test:
        # Test basic commands
        print("\\n=== Testing SimTemp External Client ===")
        
        temp = client.get_temperature()
        print(f"Current temperature: {temp}°C")
        
        status = client.get_status()
        print(f"Sensor status: {status}")
        
        # Test monitoring for a few seconds
        def data_handler(sample):
            print(f"Received sample: {sample['temperature_celsius']:.2f}°C "
                  f"(ID: {sample['sample_id']})")
        
        client.set_data_callback(data_handler)
        client.start_monitoring()
        
        print("\\nMonitoring for 10 seconds...")
        time.sleep(10)
        
        client.stop_monitoring()
        
        # Show connection info
        info = client.get_connection_info()
        print(f"\\nConnection info: {info}")
    
    client.disconnect()
    print("\\nTest completed successfully")
    return 0


if __name__ == "__main__":
    exit(main())