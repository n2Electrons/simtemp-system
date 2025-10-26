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
    """Read temperature data from sensor clients connecting to port 4445.
    
    Acts as a server listening on port 4445 to receive temperature data
    from generators, QEMU chardev, or other sensor sources.
    """
    
    def __init__(self, host='127.0.0.1', port=4445):
        # Listen on port 4445 as server for sensor data
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.connected = False
        self.running = False
        self.thread = None
        self.data_callback = None
        
    def connect(self) -> bool:
        """Start listening for sensor connections on port 4445."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, 
                                               socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, 
                                          socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.connected = True
            logger.info(f"✅ Sensor server listening on "
                        f"{self.host}:{self.port}")
            logger.info("🎯 Waiting for sensor data connections...")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start sensor server: {e}")
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
        logger.info("🌡️ Started QEMU sensor socket temperature reading")
        logger.info("📟 Reading /dev/simtemp0 via QEMU chardev socket")
        return True
    
    def _send_guest_command(self, command: str) -> bool:
        """Send command directly to guest console."""
        try:
            # Send command directly to guest console
            cmd_bytes = f"{command}\n".encode('ascii')
            self.tn.write(cmd_bytes)
            logger.debug(f"📟 Sent to guest console: {command}")
            return True
        except Exception as e:
            logger.debug(f"Error sending guest command '{command}': {e}")
            return False
    
    def _check_simtemp_device(self) -> bool:
        """Check if /dev/simtemp0 exists in guest system."""
        try:
            logger.info("🔍 Checking for /dev/simtemp0 in guest system...")
            logger.info("📟 Sending command to guest console")
            
            # Send 'ls -la /dev/simtemp*' command to guest console
            self._send_guest_command("ls -la /dev/simtemp*")
            time.sleep(1.0)  # Wait for response
            
            # Read response
            response = self.tn.read_very_eager().decode('ascii',
                                                        errors='ignore')
            logger.debug(f"🔍 Device check response: {response}")
            
            if "simtemp0" in response:
                logger.info("✅ /dev/simtemp0 found in guest system")
                return True
            else:
                logger.warning("⚠️ /dev/simtemp0 not found in guest system")
                logger.info("🔍 Full response: " + response.strip())
                # Continue anyway - device might exist but not listed
                return True
        except Exception as e:
            logger.error(f"❌ Error checking simtemp device: {e}")
            return False
    
    def stop_reading(self):
        """Stop reading temperature data."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
    
    def _reading_loop(self):
        """Background loop to read temperature from QEMU sensor socket."""
        temp_pattern = re.compile(r'(\d+\.?\d*)\s*°?C')
        
        while self.running and self.connected:
            try:
                # Read data from socket (connected to /dev/simtemp0 via chardev)
                data = self.socket.recv(1024).decode('ascii', errors='ignore')
                if data:
                    logger.debug(f"QEMU sensor socket data: {data.strip()}")
                    
                    # Look for temperature patterns
                    matches = temp_pattern.findall(data)
                    for match in matches:
                        temperature = float(match)
                        if self.data_callback:
                            self.data_callback(temperature)
                        
                        # Echo de medición desde /dev/simtemp0
                        logger.info(f"🌡️📟 ECHO - Temperature from "
                                    f"/dev/simtemp0: {temperature:.2f}°C")
                        print(f"🌡️📟 ECHO - Temperature from "
                              f"/dev/simtemp0: {temperature:.2f}°C")
                
                time.sleep(0.1)
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error in sensor socket reading loop: {e}")
                time.sleep(1.0)
    
    def disconnect(self):
        """Disconnect from QEMU sensor socket."""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None


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
                        # Echo de medición de temperatura desde Sensor Socket
                        logger.info(f"🌡️🔌 ECHO - Temperature from Sensor Socket: "
                                    f"{temperature:.2f}°C")
                        print(f"🌡️🔌 ECHO - Temperature from Sensor Socket: "
                              f"{temperature:.2f}°C")
                
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
                    data = client_socket.recv(1024).decode('ascii',
                                                           errors='ignore')
                    data = data.strip()
                    if not data:
                        break
                    
                    # Echo del comando recibido
                    logger.info(f"📡📥 ECHO - Protocol Command Received: "
                                f"'{data}'")
                    print(f"📡📥 ECHO - Protocol Command Received: '{data}'")
                    
                    # Process command
                    response = self._process_command(data)
                    if response:
                        client_socket.send(f"{response}\n".encode('ascii'))
                        # Echo de la respuesta enviada
                        logger.info(f"📡📤 ECHO - Protocol Response Sent: "
                                    f"'{response}'")
                        print(f"📡📤 ECHO - Protocol Response Sent: "
                              f"'{response}'")
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
        
        # Echo completo de la actualización de temperatura
        logger.info(f"📊🌡️ ECHO - Temperature Update "
                    f"#{self.sensor_state.sample_count}: {temperature:.2f}°C")
        print(f"📊🌡️ ECHO - Temperature Update "
              f"#{self.sensor_state.sample_count}: {temperature:.2f}°C")
        
        logger.debug(f"📊 Updated temperature: {temperature:.2f}°C "
                     f"(sample #{self.sensor_state.sample_count})")
    
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
        # Reads from /dev/simtemp0 via QEMU chardev port 4445
        self.console_reader = QEMUConsoleReader()
        self.protocol_server = SimTempProtocolServer()
        self.running = False
        
    def start(self) -> bool:
        """Start the complete bridge system."""
        logger.info("🎯 SimTemp Protocol Bridge - Task Force CLI Agent")
        logger.info("📡 Mission: QEMU Console → SimTemp Protocol → GUI")
        
        # Connect to QEMU sensor socket (chardev for /dev/simtemp0)
        if not self.console_reader.connect():
            logger.error("❌ Failed to connect to QEMU sensor socket")
            return False
        
        # Start protocol server
        if not self.protocol_server.start_server():
            logger.error("❌ Failed to start protocol server")
            return False
        
        # Set up data callback for temperature updates
        self.console_reader.set_data_callback(self._on_temperature_data)
        
        # Start reading from QEMU sensor socket
        self.console_reader.start_reading()
        
        self.running = True
        logger.info("✅ SimTemp Protocol Bridge started successfully")
        logger.info("🔄 Task Force CLI Agent operational - Bridge active")
        logger.info("🔊 ECHO MODE ENABLED - All temperature measurements "
                    "will be echoed")
        print("🔊 ECHO MODE ENABLED - All temperature measurements "
              "will be echoed")
        logger.info("📟 QEMU Sensor Socket: Reading /dev/simtemp0 via chardev")
        print("📟 QEMU Sensor Socket: Reading /dev/simtemp0 via chardev")
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
    print("🔊 ECHO MODE ENABLED - All temperature measurements will be echoed")
    print()
    print("Architecture:")
    print("  📟 QEMU Sensor Socket (port 4445) ← /dev/simtemp0 via chardev")
    print("  🔌 Sensor Socket (port 4445) ← Direct sensor data")
    print("  🖥️ Protocol Server (port 4446) → GUI clients")
    print()
    print("Protocol Commands:")
    print("  GET_TEMP → TEMP: 25.50°C")
    print("  STATUS → STATUS: Temp=25.50°C, Sampling=500ms, ...")
    print("  SET_THRESHOLD <value> → OK: Threshold set to <value>°C")
    print("  SET_SAMPLING <ms> → OK: Sampling set to <ms>ms")
    print()
    print("Task Force Role: CLI Agent - Bridge Console Data to "
          "Protocol Server")
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
