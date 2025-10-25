#!/usr/bin/env python3
"""
SimTemp Protocol Bridge - Task Force CLI Agent
Copyright (c) 2025 Jorge Rodriguez Moreno

🎯 MISSION: Bridge QEMU Console + Sensor Data → SimTemp Protocol → GUI

This bridge implements the SimTemp sensor protocol to serve GUI clients.
The bridge reads temperature data from QEMU console and sensor socket,
then serves it using the expected SimTemp command protocol.

Architecture:
- QEMU Console (telnet 2323) ← Monitor access
- Sensor Socket (port 4445) ← Direct sensor data  
- Protocol Server (port 4446) → GUI clients with SimTemp protocol

Protocol Commands:
- GET_TEMP → TEMP: 25.50°C
- STATUS → STATUS: Temp=25.50°C, Sampling=500ms, Threshold=45.0°C, Uptime=123s
- SET_THRESHOLD <value> → OK: Threshold set to <value>°C
- SET_SAMPLING <ms> → OK: Sampling set to <ms>ms

Task Force Role: CLI Agent - Bridge Console Data to Protocol Server
"""

import telnetlib
import socket
import threading
import time
import re
import logging
import signal
import sys
from typing import Optional, Dict, List
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SensorState:
    """Current sensor state data."""
    temperature: float = 127.0  # Default temperature from generator
    threshold: float = 45.0
    sampling_ms: int = 500
    uptime_start: float = 0.0
    last_update: float = 0.0
    sample_count: int = 0


class QEMUConsoleReader:
    """Read temperature data from QEMU console via telnet monitor."""
    
    def __init__(self, host='127.0.0.1', port=2323):
        self.host = host
        self.port = port
        self.tn = None
        self.connected = False
        self.running = False
        self.thread = None
        self.data_callback = None
        
    def connect(self) -> bool:
        """Connect to QEMU monitor via telnet."""
        try:
            self.tn = telnetlib.Telnet(self.host, self.port, timeout=5)
            # Read initial prompt
            self.tn.read_until(b"(qemu)", timeout=2)
            self.connected = True
            logger.info(f"✅ QEMU monitor connected via telnet {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to QEMU monitor: {e}")
            return False
    
    def set_data_callback(self, callback):
        """Set callback for new temperature data."""
        self.data_callback = callback
    
    def start_reading(self):
        """Start reading temperature data in background."""
        if not self.connected:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._reading_loop, daemon=True)
        self.thread.start()
        logger.info("🌡️ Started QEMU console temperature reading")
        return True
    
    def stop_reading(self):
        """Stop reading temperature data."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
    
    def _reading_loop(self):
        """Background loop to read temperature from console."""
        temp_pattern = re.compile(r'(\d+\.?\d*)\s*°?C')
        
        while self.running and self.connected:
            try:
                # Read any available output from console
                try:
                    output = self.tn.read_very_eager().decode('ascii', errors='ignore')
                    
                    if output.strip():
                        logger.debug(f"Console output: {output.strip()}")
                        
                        # Look for temperature patterns in output
                        matches = temp_pattern.findall(output)
                        if matches:
                            # Get the last (most recent) temperature
                            temp_str = matches[-1]
                            temperature = float(temp_str)
                            
                            if self.data_callback:
                                self.data_callback(temperature)
                            
                            logger.debug(f"🌡️ Console temp: {temperature:.1f}°C")
                
                except Exception as e:
                    logger.debug(f"Console read error: {e}")
                
                time.sleep(0.2)  # Read every 200ms
                
            except Exception as e:
                logger.error(f"Error in console reading loop: {e}")
                time.sleep(1.0)
    
    def disconnect(self):
        """Disconnect from QEMU monitor."""
        self.running = False
        self.connected = False
        if self.tn:
            try:
                self.tn.close()
            except:
                pass
            self.tn = None


class SensorSocketReader:
    """Read temperature data directly from sensor socket."""
    
    def __init__(self, host='127.0.0.1', port=4445):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.running = False
        self.thread = None
        self.data_callback = None
        
    def connect(self) -> bool:
        """Connect to sensor socket."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"✅ Sensor socket connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to sensor socket: {e}")
            return False
    
    def set_data_callback(self, callback):
        """Set callback for new temperature data."""
        self.data_callback = callback
    
    def start_reading(self):
        """Start reading temperature data in background."""
        if not self.connected:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._reading_loop, daemon=True)
        self.thread.start()
        logger.info("🔌 Started sensor socket temperature reading")
        return True
    
    def stop_reading(self):
        """Stop reading temperature data."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
    
    def _reading_loop(self):
        """Background loop to read temperature from sensor socket."""
        temp_pattern = re.compile(r'(\d+\.?\d*)\s*°?C')
        
        while self.running and self.connected:
            try:
                # Read data from socket
                data = self.socket.recv(1024).decode('ascii', errors='ignore')
                if data:
                    # Look for temperature patterns
                    matches = temp_pattern.findall(data)
                    for match in matches:
                        temperature = float(match)
                        if self.data_callback:
                            self.data_callback(temperature)
                        logger.debug(f"🔌 Socket temp: {temperature:.1f}°C")
                
                time.sleep(0.1)
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error in socket reading loop: {e}")
                time.sleep(1.0)
    
    def disconnect(self):
        """Disconnect from sensor socket."""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None


class SimTempProtocolServer:
    """SimTemp protocol server for GUI clients."""
    
    def __init__(self, port=4446):
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        self.sensor_state = SensorState()
        self.sensor_state.uptime_start = time.time()
        
    def start_server(self) -> bool:
        """Start the protocol server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.port))
            self.server_socket.listen(5)
            self.running = True
            
            # Start accepting connections
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            logger.info(f"✅ SimTemp protocol server started on port {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start protocol server: {e}")
            return False
    
    def _accept_connections(self):
        """Accept new client connections."""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"🔗 GUI client connected from {address}")
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
    
    def _handle_client(self, client_socket, address):
        """Handle individual client connection."""
        self.clients.append(client_socket)
        
        try:
            # Send welcome message
            welcome = f"SimTemp Protocol Bridge v1.0 - Connected to sensor\n"
            client_socket.send(welcome.encode('ascii'))
            
            while self.running:
                try:
                    # Receive command from client
                    data = client_socket.recv(1024).decode('ascii', errors='ignore').strip()
                    if not data:
                        break
                    
                    # Process command
                    response = self._process_command(data)
                    if response:
                        client_socket.send(f"{response}\n".encode('ascii'))
                        logger.debug(f"📤 Sent to {address}: {response}")
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error handling client {address}: {e}")
                    break
        
        finally:
            # Cleanup client
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass
            logger.info(f"🔌 Client {address} disconnected")
    
    def _process_command(self, command: str) -> str:
        """Process SimTemp protocol command."""
        command = command.strip().upper()
        
        if command == "GET_TEMP":
            # Send temperature in milli-Celsius (integer)
            temp_mc = int(self.sensor_state.temperature * 1000)
            return f"TEMP: {temp_mc}"
        
        elif command == "STATUS":
            uptime = time.time() - self.sensor_state.uptime_start
            # Send temperature in milli-Celsius, threshold in milli-Celsius
            temp_mc = int(self.sensor_state.temperature * 1000)
            threshold_mc = int(self.sensor_state.threshold * 1000)
            uptime_ms = int(uptime * 1000)
            return (f"STATUS: TempMC={temp_mc}, "
                   f"SamplingMS={self.sensor_state.sampling_ms}, "
                   f"ThresholdMC={threshold_mc}, "
                   f"UptimeMS={uptime_ms}")
        
        elif command.startswith("SET_THRESHOLD"):
            try:
                parts = command.split()
                if len(parts) >= 2:
                    threshold = float(parts[1])
                    self.sensor_state.threshold = threshold
                    return f"OK: Threshold set to {threshold:.1f}"
                else:
                    return "ERROR: Invalid threshold value"
            except ValueError:
                return "ERROR: Invalid threshold format"
        
        elif command.startswith("SET_SAMPLING"):
            try:
                parts = command.split()
                if len(parts) >= 2:
                    sampling = int(parts[1])
                    self.sensor_state.sampling_ms = sampling
                    return f"OK: Sampling set to {sampling}ms"
                else:
                    return "ERROR: Invalid sampling value"
            except ValueError:
                return "ERROR: Invalid sampling format"
        
        else:
            return f"ERROR: Unknown command '{command}'"
    
    def update_temperature(self, temperature: float):
        """Update sensor temperature."""
        self.sensor_state.temperature = temperature
        self.sensor_state.last_update = time.time()
        self.sensor_state.sample_count += 1
        logger.debug(f"📊 Updated temperature: {temperature:.2f}°C (sample #{self.sensor_state.sample_count})")
    
    def stop_server(self):
        """Stop the protocol server."""
        self.running = False
        
        # Close all client connections
        for client in self.clients[:]:
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
        
        logger.info("🛑 SimTemp protocol server stopped")


class SimTempProtocolBridge:
    """Main bridge coordinator."""
    
    def __init__(self):
        self.console_reader = QEMUConsoleReader()
        self.socket_reader = SensorSocketReader()
        self.protocol_server = SimTempProtocolServer()
        self.running = False
        
    def start(self) -> bool:
        """Start the complete bridge system."""
        logger.info("🎯 SimTemp Protocol Bridge - Task Force CLI Agent")
        logger.info("📡 Mission: QEMU Console → SimTemp Protocol → GUI")
        
        # Connect to QEMU console
        if not self.console_reader.connect():
            logger.error("❌ Failed to connect to QEMU console")
            return False
        
        # Start protocol server
        if not self.protocol_server.start_server():
            logger.error("❌ Failed to start protocol server")
            return False
        
        # Set up data callbacks (only console, not socket)
        self.console_reader.set_data_callback(self._on_temperature_data)
        
        # Start reading from console only
        self.console_reader.start_reading()
        
        self.running = True
        logger.info("✅ SimTemp Protocol Bridge started successfully")
        logger.info("🔄 Task Force CLI Agent operational - Bridge active")
        return True
    
    def _on_temperature_data(self, temperature: float):
        """Handle new temperature data from any source."""
        self.protocol_server.update_temperature(temperature)
    
    def stop(self):
        """Stop the bridge system."""
        logger.info("🛑 Stopping SimTemp Protocol Bridge")
        self.running = False
        
        self.console_reader.stop_reading()
        self.console_reader.disconnect()
        
        self.protocol_server.stop_server()
        
        logger.info("✅ SimTemp Protocol Bridge stopped")
    
    def run(self):
        """Run the bridge (blocking)."""
        if not self.start():
            return False
        
        try:
            while self.running:
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("📡 Received interrupt signal")
        finally:
            self.stop()
        
        return True


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"📡 Received signal {signum}, shutting down...")
    global bridge
    if bridge:
        bridge.stop()
    sys.exit(0)


def main():
    """Main entry point."""
    global bridge
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("🎯 SimTemp Protocol Bridge - Task Force CLI Agent")
    print("📡 Mission: QEMU Console + Sensor → SimTemp Protocol → GUI")
    print("=" * 60)
    print()
    print("Architecture:")
    print("  📟 QEMU Console (telnet 2323) ← Monitor commands")
    print("  🔌 Sensor Socket (port 4445) ← Direct sensor data")
    print("  🖥️ Protocol Server (port 4446) → GUI clients")
    print()
    print("Protocol Commands:")
    print("  GET_TEMP → TEMP: 25.50°C")
    print("  STATUS → STATUS: Temp=25.50°C, Sampling=500ms, ...")
    print("  SET_THRESHOLD <value> → OK: Threshold set to <value>°C")
    print("  SET_SAMPLING <ms> → OK: Sampling set to <ms>ms")
    print()
    print("Task Force Role: CLI Agent - Bridge Console Data to Protocol Server")
    print("=" * 60)
    print()
    
    # Create and run bridge
    bridge = SimTempProtocolBridge()
    
    try:
        success = bridge.run()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    bridge = None
    exit(main())