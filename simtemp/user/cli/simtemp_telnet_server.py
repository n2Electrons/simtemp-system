#!/usr/bin/env python3
"""
SimTemp Telnet Server Simulator
Simula un sensor de temperatura que acepta comandos vía Telnet
"""

import socket
import threading
import time
import signal
import sys

class SimTempTelnetServer:
    def __init__(self, host='0.0.0.0', port=23):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.current_temp = 25.0
        self.clients = []
        # F-K7 Configuration parameters
        self.sampling_ms = 100      # Default 100ms
        self.threshold_mC = 45000   # Default 45°C in milli-degrees
        
    def start(self):
        """Start the telnet server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"SimTemp Telnet Server listening on {self.host}:{self.port}")
            print("Comandos soportados:")
            print("  SET_TEMP <temperatura>  - Establecer temperatura")
            print("  GET_TEMP                - Obtener temperatura actual")
            print("  SET_SAMPLING <ms>       - Configurar período muestreo")
            print("  GET_SAMPLING            - Obtener período muestreo")
            print("  SET_THRESHOLD <mC>      - Configurar umbral (mili-°C)")
            print("  GET_THRESHOLD           - Obtener umbral")
            print("  STATUS                  - Estado del sensor")
            print("  QUIT                    - Cerrar conexión")
            print()
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"Nueva conexión desde {addr}")
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"Error aceptando conexión: {e}")
                        
        except Exception as e:
            print(f"Error iniciando servidor: {e}")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, addr):
        """Handle individual client connection"""
        try:
            self.clients.append(client_socket)
            
            # Send welcome message
            welcome = "SimTemp Sensor v1.0 - Telnet Interface\r\n"
            welcome += "Type 'HELP' for commands or 'QUIT' to exit\r\n"
            welcome += "simtemp> "
            client_socket.send(welcome.encode())
            
            buffer = ""
            while self.running:
                try:
                    data = client_socket.recv(1024).decode('ascii', errors='ignore')
                    if not data:
                        break
                        
                    buffer += data
                    
                    while '\n' in buffer or '\r' in buffer:
                        if '\r\n' in buffer:
                            line, buffer = buffer.split('\r\n', 1)
                        elif '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                        else:
                            line, buffer = buffer.split('\r', 1)
                        
                        if line.strip():
                            response = self.process_command(line.strip())
                            client_socket.send(f"{response}\r\nsimtemp> ".encode())
                            
                except socket.timeout:
                    continue
                except socket.error:
                    break
                    
        except Exception as e:
            print(f"Error manejando cliente {addr}: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
            print(f"Cliente {addr} desconectado")
    
    def process_command(self, command):
        """Process telnet commands"""
        parts = command.upper().split()
        cmd = parts[0] if parts else ""
        
        if cmd == "SET_TEMP" and len(parts) >= 2:
            try:
                temp = float(parts[1])
                old_temp = self.current_temp
                self.current_temp = temp
                print(f"Temperatura cambiada: {old_temp:.2f}°C -> {temp:.2f}°C")
                return f"OK: Temperature set to {temp:.2f}°C"
            except ValueError:
                return "ERROR: Invalid temperature value"
                
        elif cmd == "GET_TEMP":
            return f"TEMP: {self.current_temp:.2f}°C"
        
        elif cmd == "SET_SAMPLING" and len(parts) >= 2:
            try:
                sampling_ms = int(parts[1])
                if 1 <= sampling_ms <= 60000:  # 1ms to 60s
                    old_sampling = self.sampling_ms
                    self.sampling_ms = sampling_ms
                    print(f"Sampling cambiado: {old_sampling}ms -> {sampling_ms}ms")
                    return f"OK: Sampling period set to {sampling_ms} ms"
                else:
                    return "ERROR: Invalid sampling period (1-60000 ms)"
            except ValueError:
                return "ERROR: Invalid sampling period value"
        
        elif cmd == "GET_SAMPLING":
            return f"SAMPLING: {self.sampling_ms} ms"
        
        elif cmd == "SET_THRESHOLD" and len(parts) >= 2:
            try:
                threshold_mC = int(parts[1])
                if -50000 <= threshold_mC <= 150000:  # -50°C to 150°C
                    old_threshold = self.threshold_mC
                    self.threshold_mC = threshold_mC
                    temp_c = threshold_mC / 1000.0
                    old_temp_c = old_threshold / 1000.0
                    print(f"Threshold cambiado: {old_temp_c:.1f}°C -> {temp_c:.1f}°C")
                    return f"OK: Threshold set to {temp_c:.1f}°C ({threshold_mC} mC)"
                else:
                    return "ERROR: Invalid threshold (-50000 to 150000 mC)"
            except ValueError:
                return "ERROR: Invalid threshold value"
        
        elif cmd == "GET_THRESHOLD":
            temp_c = self.threshold_mC / 1000.0
            return f"THRESHOLD: {temp_c:.1f}°C ({self.threshold_mC} mC)"
            
        elif cmd == "STATUS":
            uptime = time.time() - getattr(self, 'start_time', time.time())
            temp_c = self.threshold_mC / 1000.0
            status = f"STATUS: OK, Temp={self.current_temp:.2f}°C, "
            status += f"Sampling={self.sampling_ms}ms, "
            status += f"Threshold={temp_c:.1f}°C, "
            status += f"Uptime={uptime:.0f}s, Clients={len(self.clients)}"
            return status
            
        elif cmd == "HELP":
            help_text = "Comandos disponibles:\r\n"
            help_text += "  SET_TEMP <valor>      - Establecer temperatura\r\n"
            help_text += "  GET_TEMP              - Obtener temperatura\r\n"
            help_text += "  SET_SAMPLING <ms>     - Configurar muestreo\r\n"
            help_text += "  GET_SAMPLING          - Obtener muestreo\r\n"
            help_text += "  SET_THRESHOLD <mC>    - Configurar umbral\r\n"
            help_text += "  GET_THRESHOLD         - Obtener umbral\r\n"
            help_text += "  STATUS                - Estado del sistema\r\n"
            help_text += "  HELP                  - Esta ayuda\r\n"
            help_text += "  QUIT                  - Cerrar conexión"
            return help_text
            
        elif cmd == "QUIT":
            return "BYE: Connection closed"
            
        else:
            return f"ERROR: Unknown command '{command}'. Type 'HELP' for help"
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # Close all client connections
        for client in self.clients[:]:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        print("Servidor telnet detenido")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global server
    print("\nDeteniendo servidor...")
    if server:
        server.stop()
    sys.exit(0)

def main():
    global server
    
    import argparse
    parser = argparse.ArgumentParser(description='SimTemp Telnet Server Simulator')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=23, help='Port to bind (default: 23)')
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server = SimTempTelnetServer(args.host, args.port)
    server.start_time = time.time()
    
    try:
        server.start()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()