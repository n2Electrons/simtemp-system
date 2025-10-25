#!/usr/bin/env python3
"""
QEMU Telnet Orchestrator - Task Force CLI Agent
Copyright (c) 2025 SimTemp Task Force

Mission: Connect via telnet to QEMU console (port 2323) and bridge
temperature data from /dev/tempsensor to GUI clients.

Task Force Assignment:
- Comandante: QEMU Console Management + GUI Coordination  
- CLI Agent (this): Telnet Bridge + Data Flow Management
- Wave Agent: Continuous Wave Generator Management
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
from typing import Optional, List, Dict, Any


class QEMUTelnetBridge:
    """Bridge for communicating with QEMU console via telnet"""
    
    def __init__(self, host='127.0.0.1', port=2323, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.telnet = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """Establish telnet connection to QEMU console"""
        try:
            self.logger.info(f"🔌 Connecting to QEMU console: {self.host}:{self.port}")
            self.telnet = telnetlib.Telnet(self.host, self.port, self.timeout)
            self.connected = True
            self.logger.info("✅ QEMU telnet connection established")
            
            # Wait for console prompt
            time.sleep(1)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to QEMU console: {e}")
            self.connected = False
            return False
    
    def send_command(self, command: str) -> str:
        """Send command to QEMU console and get response"""
        if not self.connected or not self.telnet:
            self.logger.error("❌ Not connected to QEMU console")
            return ""
            
        try:
            # Send command
            self.telnet.write(f"{command}\n".encode('utf-8'))
            time.sleep(0.5)
            
            # Read response
            response = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Error sending command '{command}': {e}")
            return ""
    
    def start_temperature_monitoring(self):
        """Start continuous monitoring of /dev/tempsensor"""
        if not self.connected:
            self.logger.error("❌ Cannot start monitoring: not connected")
            return False
            
        try:
            self.logger.info("🌡️ Starting temperature monitoring on /dev/tempsensor")
            
            # Start cat command for continuous reading
            self.telnet.write(b"cat /dev/tempsensor\n")
            time.sleep(0.1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start temperature monitoring: {e}")
            return False
    
    def read_temperature_data(self) -> Optional[str]:
        """Read temperature data from the telnet connection"""
        if not self.connected or not self.telnet:
            return None
            
        try:
            # Read available data
            data = self.telnet.read_very_eager().decode('utf-8', errors='ignore')
            if data.strip():
                return data.strip()
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error reading temperature data: {e}")
            return None
    
    def disconnect(self):
        """Close telnet connection"""
        if self.telnet:
            try:
                self.telnet.close()
                self.logger.info("🔌 QEMU telnet connection closed")
            except:
                pass
        self.connected = False


class TemperatureDataParser:
    """Parse temperature data from QEMU sensor"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Pattern for SET_TEMP commands: SET_TEMP:XX.XX
        self.set_temp_pattern = re.compile(r'SET_TEMP:(\d+\.?\d*)')
    
    def parse_sensor_data(self, raw_data: str) -> Optional[Dict[str, Any]]:
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
                    'source': 'qemu_sensor',
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
                        'source': 'qemu_sensor',
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


class QEMUTelnetOrchestrator:
    """Main orchestrator for QEMU telnet bridge"""
    
    def __init__(self, qemu_host='127.0.0.1', qemu_port=2323, gui_port=4446):
        self.qemu_bridge = QEMUTelnetBridge(qemu_host, qemu_port)
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
        self.logger.info("🚀 Starting QEMU Telnet Orchestrator")
        
        # 1. Connect to QEMU console
        if not self.qemu_bridge.connect():
            self.logger.error("❌ Failed to connect to QEMU console")
            return False
        
        # 2. Start GUI server
        if not self.gui_server.start_server():
            self.logger.error("❌ Failed to start GUI server")
            return False
        
        # 3. Start temperature monitoring
        if not self.qemu_bridge.start_temperature_monitoring():
            self.logger.error("❌ Failed to start temperature monitoring")
            return False
        
        self.running = True
        self.logger.info("✅ QEMU Telnet Orchestrator started successfully")
        
        # 4. Start main data loop
        self._data_processing_loop()
        
        return True
    
    def _data_processing_loop(self):
        """Main loop for processing temperature data"""
        self.logger.info("🔄 Starting data processing loop")
        
        while self.running:
            try:
                # Read data from QEMU sensor
                raw_data = self.qemu_bridge.read_temperature_data()
                
                if raw_data:
                    # Parse the data
                    parsed_data = self.data_parser.parse_sensor_data(raw_data)
                    
                    if parsed_data:
                        self.logger.info(f"🌡️ Temperature: {parsed_data['temperature']}°C")
                        
                        # Send to GUI clients
                        self.gui_server.send_to_clients(parsed_data)
                
                # Small delay to prevent CPU overload
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"❌ Error in data processing loop: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop the orchestrator"""
        self.logger.info("🛑 Stopping QEMU Telnet Orchestrator")
        self.running = False
        
        # Stop components
        self.qemu_bridge.disconnect()
        self.gui_server.stop_server()
        
        self.logger.info("✅ QEMU Telnet Orchestrator stopped")


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/qemu_telnet_orchestrator.log')
        ]
    )


def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🎯 QEMU Telnet Orchestrator - Task Force CLI Agent")
    logger.info("📡 Mission: Bridge QEMU console (telnet:2323) to GUI (port:4446)")
    
    # Create and start orchestrator
    orchestrator = QEMUTelnetOrchestrator(
        qemu_host='127.0.0.1',
        qemu_port=2323,
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