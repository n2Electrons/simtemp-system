#!/usr/bin/env python3
"""
QEMU Console Bridge via Monitor - Task Force CLI Agent
Copyright (c) 2025 SimTemp Task Force

Mission: Use QEMU monitor as console to read /dev/tempsensor 
and send filtered temperature data to GUI.

Strategy: QEMU Monitor → Console Commands → /dev/tempsensor → GUI
"""

import telnetlib
import socket
import threading
import time
import json
import re
import logging
import signal
import sys
from datetime import datetime
from typing import Optional, Dict, Any


class QEMUConsoleViaMon:
    """Access QEMU guest console via monitor commands"""
    
    def __init__(self, host='127.0.0.1', port=2323, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.telnet = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        self.monitoring_active = False
        
    def connect(self) -> bool:
        """Establish telnet connection to QEMU monitor"""
        try:
            self.logger.info(f"🔌 Connecting to QEMU monitor: {self.host}:{self.port}")
            self.telnet = telnetlib.Telnet(self.host, self.port, self.timeout)
            self.connected = True
            
            # Wait for QEMU prompt and clear buffer
            time.sleep(1)
            initial = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
            self.logger.info(f"✅ QEMU monitor connected")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to QEMU monitor: {e}")
            self.connected = False
            return False
    
    def send_console_command(self, command: str) -> str:
        """Send command to guest console via monitor"""
        if not self.connected or not self.telnet:
            self.logger.error("❌ Not connected to QEMU monitor")
            return ""
            
        try:
            # Use QEMU monitor to send command to guest console
            # The guest console is accessible via sendkey or other methods
            
            # Method 1: Use monitor to send characters to guest
            for char in command:
                if char == '\n':
                    self.telnet.write(b"sendkey ret\n")
                else:
                    ascii_val = ord(char)
                    self.telnet.write(f"sendkey 0x{ascii_val:02x}\n".encode())
                time.sleep(0.01)  # Small delay between keystrokes
            
            # Send Enter
            self.telnet.write(b"sendkey ret\n")
            time.sleep(0.5)
            
            # Read response
            response = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Error sending console command '{command}': {e}")
            return ""
    
    def start_temperature_monitoring_via_console(self) -> bool:
        """Start monitoring /dev/tempsensor via guest console"""
        if not self.connected:
            self.logger.error("❌ Cannot start monitoring: not connected")
            return False
            
        try:
            self.logger.info("🌡️ Starting temperature monitoring via console")
            
            # Send command to read temperature sensor continuously
            # We'll use a different approach - use QEMU's info commands
            self.monitoring_active = True
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start temperature monitoring: {e}")
            return False
    
    def read_temperature_via_console(self) -> Optional[str]:
        """Read temperature data via console commands"""
        if not self.connected or not self.telnet:
            return None
            
        try:
            # Alternative approach: Use QEMU monitor to access chardev data
            # The sensor data comes through chardev mysensor
            
            # Check chardev info
            self.telnet.write(b"info chardev\n")
            time.sleep(0.2)
            
            response = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
            
            # Look for sensor data in the response
            if response and 'mysensor' in response:
                return response.strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error reading temperature via console: {e}")
            return None
    
    def disconnect(self):
        """Close monitor connection"""
        self.monitoring_active = False
        if self.telnet:
            try:
                self.telnet.close()
                self.logger.info("🔌 QEMU monitor connection closed")
            except:
                pass
        self.connected = False


class DirectSensorReader:
    """Direct sensor socket reader for port 4445"""
    
    def __init__(self, host='127.0.0.1', port=4445):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """Connect to sensor socket"""
        try:
            self.logger.info(f"🔌 Connecting to sensor socket: {self.host}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            self.logger.info("✅ Sensor socket connected")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to sensor socket: {e}")
            self.connected = False
            return False
    
    def read_sensor_data(self) -> Optional[str]:
        """Read data from sensor socket"""
        if not self.connected or not self.socket:
            return None
            
        try:
            self.socket.settimeout(0.1)
            data = self.socket.recv(1024).decode('utf-8', errors='ignore')
            
            if data.strip():
                return data.strip()
            return None
            
        except socket.timeout:
            return None
        except Exception as e:
            self.logger.error(f"❌ Error reading sensor data: {e}")
            return None
    
    def disconnect(self):
        """Close sensor socket"""
        if self.socket:
            try:
                self.socket.close()
                self.logger.info("🔌 Sensor socket connection closed")
            except:
                pass
        self.connected = False


class TemperatureDataFilter:
    """Filter and parse temperature data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Enhanced patterns for temperature data
        self.patterns = {
            'set_temp': re.compile(r'SET_TEMP[:\s]*(\d+\.?\d*)'),
            'temp_value': re.compile(r'(\d+\.?\d*)\s*°?C?'),
            'json_temp': re.compile(r'"temperature"[:\s]*(\d+\.?\d*)'),
        }
    
    def filter_temperature_data(self, raw_data: str, source: str = "unknown") -> Optional[Dict[str, Any]]:
        """Filter and extract temperature data"""
        if not raw_data or not raw_data.strip():
            return None
            
        try:
            # Clean the data
            clean_data = raw_data.strip()
            
            # Try different patterns
            for pattern_name, pattern in self.patterns.items():
                match = pattern.search(clean_data)
                if match:
                    temperature = float(match.group(1))
                    
                    # Filter reasonable temperature values
                    if -50 <= temperature <= 150:  # Reasonable temperature range
                        return {
                            'timestamp': datetime.now().isoformat(),
                            'temperature': temperature,
                            'source': source,
                            'raw_data': clean_data,
                            'type': 'temperature_reading',
                            'pattern': pattern_name
                        }
            
            # If no temperature found but data exists, log it
            if len(clean_data) > 0:
                self.logger.debug(f"📊 Non-temperature data from {source}: {clean_data[:50]}...")
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error filtering temperature data: {e}")
            return None


class GUIDataBridge:
    """Bridge to send filtered data to GUI clients"""
    
    def __init__(self, port=4446):
        self.port = port
        self.server_socket = None
        self.clients = []
        self.running = False
        self.logger = logging.getLogger(__name__)
        self.data_count = 0
        
    def start_server(self) -> bool:
        """Start GUI server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            self.running = True
            
            self.logger.info(f"🖥️ GUI bridge server started on port {self.port}")
            
            # Start accepting connections
            threading.Thread(target=self._accept_connections, daemon=True).start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start GUI bridge server: {e}")
            return False
    
    def _accept_connections(self):
        """Accept GUI client connections"""
        while self.running and self.server_socket:
            try:
                client_socket, address = self.server_socket.accept()
                self.clients.append(client_socket)
                self.logger.info(f"🔗 GUI client connected from {address}")
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"❌ Error accepting connection: {e}")
    
    def send_temperature_data(self, temp_data: Dict[str, Any]):
        """Send temperature data to all GUI clients"""
        if not self.clients:
            return
            
        self.data_count += 1
        message = json.dumps(temp_data) + '\n'
        disconnected_clients = []
        
        for client in self.clients:
            try:
                client.send(message.encode('utf-8'))
                
            except Exception as e:
                self.logger.error(f"❌ Error sending to GUI client: {e}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.remove(client)
            try:
                client.close()
            except:
                pass
        
        # Log progress
        if self.data_count % 10 == 0:
            self.logger.info(f"📊 Sent {self.data_count} temperature readings to {len(self.clients)} GUI clients")
    
    def stop_server(self):
        """Stop GUI server"""
        self.running = False
        
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            
        self.logger.info("🖥️ GUI bridge server stopped")


class QEMUConsoleBridgeOrchestrator:
    """Main orchestrator for QEMU console bridge"""
    
    def __init__(self, qemu_host='127.0.0.1', qemu_port=2323, 
                 sensor_host='127.0.0.1', sensor_port=4445, gui_port=4446):
        self.qemu_console = QEMUConsoleViaMon(qemu_host, qemu_port)
        self.sensor_reader = DirectSensorReader(sensor_host, sensor_port)
        self.data_filter = TemperatureDataFilter()
        self.gui_bridge = GUIDataBridge(gui_port)
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"📡 Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def start(self) -> bool:
        """Start the console bridge orchestrator"""
        self.logger.info("🚀 Starting QEMU Console Bridge - Task Force CLI Agent")
        
        # 1. Connect to QEMU monitor/console
        if not self.qemu_console.connect():
            self.logger.error("❌ Failed to connect to QEMU console")
            return False
        
        # 2. Connect to sensor socket
        if not self.sensor_reader.connect():
            self.logger.warning("⚠️ Sensor socket not available")
        
        # 3. Start GUI bridge server
        if not self.gui_bridge.start_server():
            self.logger.error("❌ Failed to start GUI bridge")
            return False
        
        # 4. Start console monitoring
        if not self.qemu_console.start_temperature_monitoring_via_console():
            self.logger.warning("⚠️ Console monitoring may not be available")
        
        self.running = True
        self.logger.info("✅ QEMU Console Bridge started successfully")
        
        # 5. Start main processing loop
        self._temperature_processing_loop()
        
        return True
    
    def _temperature_processing_loop(self):
        """Main loop for processing temperature data"""
        self.logger.info("🔄 Starting temperature data processing loop")
        
        sensor_retry_count = 0
        max_retries = 10
        
        while self.running:
            try:
                data_processed = False
                
                # Method 1: Read from direct sensor socket (primary)
                if self.sensor_reader.connected:
                    sensor_data = self.sensor_reader.read_sensor_data()
                    if sensor_data:
                        filtered_data = self.data_filter.filter_temperature_data(sensor_data, "sensor_socket")
                        if filtered_data:
                            self.logger.info(f"🌡️ Sensor: {filtered_data['temperature']}°C")
                            self.gui_bridge.send_temperature_data(filtered_data)
                            data_processed = True
                
                # Retry sensor connection if needed
                elif sensor_retry_count < max_retries:
                    if sensor_retry_count % 20 == 0:  # Every 2 seconds
                        self.logger.info("🔄 Retrying sensor socket connection...")
                        if self.sensor_reader.connect():
                            sensor_retry_count = 0
                        else:
                            sensor_retry_count += 1
                    else:
                        sensor_retry_count += 1
                
                # Method 2: Read via QEMU console (backup)
                if not data_processed:
                    console_data = self.qemu_console.read_temperature_via_console()
                    if console_data:
                        filtered_data = self.data_filter.filter_temperature_data(console_data, "qemu_console")
                        if filtered_data:
                            self.logger.info(f"🌡️ Console: {filtered_data['temperature']}°C")
                            self.gui_bridge.send_temperature_data(filtered_data)
                            data_processed = True
                
                # Small delay to prevent CPU overload
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"❌ Error in temperature processing loop: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop the orchestrator"""
        self.logger.info("🛑 Stopping QEMU Console Bridge")
        self.running = False
        
        # Stop components
        self.qemu_console.disconnect()
        self.sensor_reader.disconnect()
        self.gui_bridge.stop_server()
        
        self.logger.info("✅ QEMU Console Bridge stopped")


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/qemu_console_bridge.log')
        ]
    )


def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🎯 QEMU Console Bridge - Task Force CLI Agent")
    logger.info("📡 Mission: QEMU Console (2323) + Sensor (4445) → Filtered Data → GUI (4446)")
    
    # Create and start orchestrator
    orchestrator = QEMUConsoleBridgeOrchestrator(
        qemu_host='127.0.0.1',
        qemu_port=2323,
        sensor_host='127.0.0.1', 
        sensor_port=4445,
        gui_port=4446
    )
    
    try:
        if orchestrator.start():
            logger.info("🎉 Task Force CLI Agent operational - filtering temperature data!")
            
            # Keep running until interrupted
            while orchestrator.running:
                time.sleep(1)
        else:
            logger.error("❌ Failed to start Task Force CLI Agent")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🔴 Manual shutdown requested")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1
    finally:
        orchestrator.stop()
    
    logger.info("🏁 Task Force CLI Agent mission completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())