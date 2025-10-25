#!/usr/bin/env python3
"""
QEMU Monitor Orchestrator - Task Force CLI Agent
Copyright (c) 2025 SimTemp Task Force

Mission: Use QEMU monitor (telnet:2323) to access guest system
and read /dev/tempsensor data for GUI bridge.

Strategy: QEMU Monitor Commands
- info registers: System status
- x/10i $pc: Memory inspection  
- monitor commands to interact with guest
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


class QEMUMonitorBridge:
    """Bridge for communicating with QEMU monitor via telnet"""
    
    def __init__(self, host='127.0.0.1', port=2323, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.telnet = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """Establish telnet connection to QEMU monitor"""
        try:
            self.logger.info(f"🔌 Connecting to QEMU monitor: {self.host}:{self.port}")
            self.telnet = telnetlib.Telnet(self.host, self.port, self.timeout)
            self.connected = True
            
            # Wait for QEMU prompt
            time.sleep(1)
            
            # Read initial prompt
            initial = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
            self.logger.info(f"✅ QEMU monitor connected: {initial.strip()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to QEMU monitor: {e}")
            self.connected = False
            return False
    
    def send_monitor_command(self, command: str) -> str:
        """Send command to QEMU monitor and get response"""
        if not self.connected or not self.telnet:
            self.logger.error("❌ Not connected to QEMU monitor")
            return ""
            
        try:
            # Send command to QEMU monitor
            self.telnet.write(f"{command}\n".encode('utf-8'))
            time.sleep(0.5)
            
            # Read response
            response = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Error sending monitor command '{command}': {e}")
            return ""
    
    def check_guest_system(self) -> bool:
        """Check if guest system is running"""
        try:
            # Check system status via QEMU monitor
            response = self.send_monitor_command("info status")
            
            if "running" in response.lower():
                self.logger.info("✅ Guest system is running")
                return True
            else:
                self.logger.warning(f"⚠️ Guest system status: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error checking guest system: {e}")
            return False
    
    def read_guest_memory(self, address: str, size: int = 16) -> str:
        """Read guest memory via QEMU monitor"""
        try:
            command = f"x/{size}b {address}"
            response = self.send_monitor_command(command)
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Error reading guest memory: {e}")
            return ""
    
    def get_guest_info(self) -> Dict[str, str]:
        """Get guest system information"""
        info = {}
        
        try:
            # Get various system info
            commands = {
                'status': 'info status',
                'registers': 'info registers',
                'network': 'info network',
                'chardev': 'info chardev'
            }
            
            for key, cmd in commands.items():
                response = self.send_monitor_command(cmd)
                info[key] = response.strip()
                
        except Exception as e:
            self.logger.error(f"❌ Error getting guest info: {e}")
            
        return info
    
    def disconnect(self):
        """Close monitor connection"""
        if self.telnet:
            try:
                self.telnet.close()
                self.logger.info("🔌 QEMU monitor connection closed")
            except:
                pass
        self.connected = False


class SensorSocketReader:
    """Read sensor data from QEMU sensor socket (port 4445)"""
    
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
            self.socket.settimeout(5)
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
            # Set socket to non-blocking for reading
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


class TemperatureDataParser:
    """Parse temperature data from various sources"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Pattern for SET_TEMP commands: SET_TEMP:XX.XX
        self.set_temp_pattern = re.compile(r'SET_TEMP:(\d+\.?\d*)')
    
    def parse_sensor_data(self, raw_data: str, source: str = "unknown") -> Optional[Dict[str, Any]]:
        """Parse raw sensor data into structured format"""
        if not raw_data:
            return None
            
        try:
            # Look for SET_TEMP commands
            match = self.set_temp_pattern.search(raw_data)
            if match:
                temperature = float(match.group(1))
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'temperature': temperature,
                    'source': source,
                    'raw_data': raw_data.strip(),
                    'type': 'set_temp_command'
                }
            
            # Check for other temperature patterns
            temp_patterns = [
                r'(\d+\.?\d*)\s*°?C',  # XX.XX°C or XX.XX C
                r'temp[erature]*:\s*(\d+\.?\d*)',  # temperature: XX.XX
                r'(\d+\.?\d*)',  # Just numbers
            ]
            
            for pattern in temp_patterns:
                match = re.search(pattern, raw_data, re.IGNORECASE)
                if match:
                    temperature = float(match.group(1))
                    
                    return {
                        'timestamp': datetime.now().isoformat(),
                        'temperature': temperature,
                        'source': source,
                        'raw_data': raw_data.strip(),
                        'type': 'temperature_reading'
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing sensor data '{raw_data}': {e}")
            return None


class GUIServerBridge:
    """Bridge to send data to GUI clients"""
    
    def __init__(self, port=4446):
        self.port = port
        self.server_socket = None
        self.clients = []
        self.running = False
        self.logger = logging.getLogger(__name__)
        
    def start_server(self) -> bool:
        """Start GUI server to accept client connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            self.running = True
            
            self.logger.info(f"🖥️ GUI server started on port {self.port}")
            
            # Start accepting connections in background
            threading.Thread(target=self._accept_connections, daemon=True).start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start GUI server: {e}")
            return False
    
    def _accept_connections(self):
        """Accept new GUI client connections"""
        while self.running and self.server_socket:
            try:
                client_socket, address = self.server_socket.accept()
                self.clients.append(client_socket)
                self.logger.info(f"🔗 GUI client connected from {address}")
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"❌ Error accepting connection: {e}")
    
    def send_to_clients(self, data: Dict[str, Any]):
        """Send data to all connected GUI clients"""
        if not self.clients:
            return
            
        message = json.dumps(data) + '\n'
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
    
    def stop_server(self):
        """Stop GUI server"""
        self.running = False
        
        # Close all client connections
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            
        self.logger.info("🖥️ GUI server stopped")


class QEMUMonitorOrchestrator:
    """Main orchestrator using QEMU monitor for system access"""
    
    def __init__(self, qemu_host='127.0.0.1', qemu_port=2323, 
                 sensor_host='127.0.0.1', sensor_port=4445, gui_port=4446):
        self.qemu_monitor = QEMUMonitorBridge(qemu_host, qemu_port)
        self.sensor_reader = SensorSocketReader(sensor_host, sensor_port)
        self.data_parser = TemperatureDataParser()
        self.gui_server = GUIServerBridge(gui_port)
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
        """Start the orchestrator"""
        self.logger.info("🚀 Starting QEMU Monitor Orchestrator - Task Force CLI Agent")
        
        # 1. Connect to QEMU monitor
        if not self.qemu_monitor.connect():
            self.logger.error("❌ Failed to connect to QEMU monitor")
            return False
        
        # 2. Check guest system
        if not self.qemu_monitor.check_guest_system():
            self.logger.warning("⚠️ Guest system may not be ready")
        
        # 3. Connect to sensor socket
        if not self.sensor_reader.connect():
            self.logger.warning("⚠️ Sensor socket not available, will retry")
        
        # 4. Start GUI server
        if not self.gui_server.start_server():
            self.logger.error("❌ Failed to start GUI server")
            return False
        
        self.running = True
        self.logger.info("✅ QEMU Monitor Orchestrator started successfully")
        
        # 5. Start main data loop
        self._data_processing_loop()
        
        return True
    
    def _data_processing_loop(self):
        """Main loop for processing data from multiple sources"""
        self.logger.info("🔄 Starting data processing loop")
        
        sensor_retry_count = 0
        max_sensor_retries = 5
        
        while self.running:
            try:
                data_found = False
                
                # Try to read from sensor socket
                if self.sensor_reader.connected:
                    sensor_data = self.sensor_reader.read_sensor_data()
                    if sensor_data:
                        parsed_data = self.data_parser.parse_sensor_data(sensor_data, "sensor_socket")
                        if parsed_data:
                            self.logger.info(f"🌡️ Sensor: {parsed_data['temperature']}°C")
                            self.gui_server.send_to_clients(parsed_data)
                            data_found = True
                
                # If no sensor connection, try to reconnect periodically
                elif sensor_retry_count < max_sensor_retries:
                    if sensor_retry_count % 10 == 0:  # Every 10 cycles
                        self.logger.info("🔄 Retrying sensor socket connection...")
                        if self.sensor_reader.connect():
                            sensor_retry_count = 0
                        else:
                            sensor_retry_count += 1
                
                # Get QEMU system status periodically
                if not data_found:
                    # Check guest system every few cycles
                    if int(time.time()) % 5 == 0:  # Every 5 seconds
                        guest_info = self.qemu_monitor.get_guest_info()
                        
                        # Send system status to GUI
                        status_data = {
                            'timestamp': datetime.now().isoformat(),
                            'type': 'system_status',
                            'source': 'qemu_monitor',
                            'data': guest_info
                        }
                        self.gui_server.send_to_clients(status_data)
                
                # Small delay to prevent CPU overload
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"❌ Error in data processing loop: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop the orchestrator"""
        self.logger.info("🛑 Stopping QEMU Monitor Orchestrator")
        self.running = False
        
        # Stop components
        self.qemu_monitor.disconnect()
        self.sensor_reader.disconnect()
        self.gui_server.stop_server()
        
        self.logger.info("✅ QEMU Monitor Orchestrator stopped")


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/qemu_monitor_orchestrator.log')
        ]
    )


def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🎯 QEMU Monitor Orchestrator - Task Force CLI Agent")
    logger.info("📡 Mission: QEMU Monitor (port:2323) + Sensor (port:4445) → GUI (port:4446)")
    
    # Create and start orchestrator
    orchestrator = QEMUMonitorOrchestrator(
        qemu_host='127.0.0.1',
        qemu_port=2323,
        sensor_host='127.0.0.1', 
        sensor_port=4445,
        gui_port=4446
    )
    
    try:
        if orchestrator.start():
            logger.info("🎉 Task Force CLI Agent operational!")
            
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