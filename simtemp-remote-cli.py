#!/usr/bin/env python3
"""
SimTemp Remote CLI - SSH-based Driver Configuration Tool
Copyright (c) 2025 Jorge Rodriguez Moreno

Remote CLI that uses SSH to interact with the SimTemp driver:
- Configure sample rate via /sys/devices/platform/simtemp/sampling_ms
- Configure threshold via /sys/devices/platform/simtemp/threshold_mC
- Read continuously from /dev/simtemp0
- Control Octave generator for temperature signals (writes to QEMU socket)

Uses SSH implementation from test_utils.py to communicate with QEMU.
"""

import sys
import os
import time
import argparse
import subprocess
import signal
import tempfile
import socket
import json
from typing import Optional

# Add simtemp tests directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simtemp', 'tests'))

try:
    from test_utils import (start_qemu_and_wait_for_boot, wait_for_ssh_ready,
                            execute_ssh_command, cleanup_qemu_processes)
except ImportError as e:
    print(f"Error importing test_utils: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class GUIClient:
    """Client to send temperature data to GUI"""
    
    def __init__(self, host="127.0.0.1", port=4446):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        
    def connect(self):
        """Try to connect to GUI"""
        print(f"[INFO] Attempting to connect to GUI at {self.host}:{self.port}...")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2.0)  # 2 second timeout
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[INFO] ✓ Successfully connected to GUI at {self.host}:{self.port}")
            return True
        except ConnectionRefusedError:
            self.connected = False
            print(f"[WARNING] ✗ Connection refused - GUI not listening on {self.host}:{self.port}")
            return False
        except socket.timeout:
            self.connected = False
            print(f"[WARNING] ✗ Connection timeout - GUI not responding on {self.host}:{self.port}")
            return False
        except socket.error as e:
            self.connected = False
            print(f"[WARNING] ✗ Connection error: {e}")
            return False
            
    def send_temperature(self, temp_c, temp_mc=None):
        """Send temperature data to GUI"""
        if not self.connected:
            return False
            
        try:
            if temp_mc is None:
                temp_mc = int(temp_c * 1000)
                
            # Send data in the format the GUI expects
            data = json.dumps({
                "temperature_c": temp_c,
                "temperature_mc": temp_mc,
                "timestamp": time.time()
            }) + "\n"
            
            self.socket.send(data.encode('utf-8'))
            return True
        except (socket.error, BrokenPipeError):
            self.connected = False
            return False
            
    def disconnect(self):
        """Disconnect from GUI"""
        if self.socket:
            try:
                self.socket.close()
                if self.connected:
                    print(f"[INFO] ✗ Disconnected from GUI at {self.host}:{self.port}")
            except:
                pass
        self.connected = False


class SSHRemoteCommand:
    """Simple wrapper for SSH commands using test_utils functions"""
    
    def __init__(self, port=2222):
        self.port = port
    
    def check_connection(self):
        """Check if SSH connection is available"""
        success, _ = execute_ssh_command("echo 'test'", self.port, timeout=5)
        return success
    
    def execute_command(self, command):
        """Execute SSH command and return result object"""
        success, output = execute_ssh_command(command, self.port)
        
        class Result:
            def __init__(self, success, output):
                self.return_code = 0 if success else 1
                self.stdout = '\n'.join(output) if output else ''
                self.stderr = '' if success else 'Command failed'
        
        return Result(success, output)
    
    def cleanup(self):
        """Cleanup SSH resources"""
        pass


class SimTempRemoteCLI:
    """Remote CLI to configure SimTemp via SSH with Octave generator"""
    
    def __init__(self, ssh_port=2222, auto_start_qemu=True, disable_auto_generator=False):
        """Initialize the remote CLI with SSH configuration and Octave generator."""
        self.ssh_port = ssh_port
        self.auto_start_qemu = auto_start_qemu
        self.disable_auto_generator = disable_auto_generator
        self.sysfs_base = "/sys/devices/platform/simtemp"
        self.device_path = "/dev/simtemp0"
        self.octave_process = None
        self.temp_script_file = None
        
        # GUI client for sending temperature data
        self.gui_client = GUIClient()
        self.gui_enabled = True  # Always enabled
        print("[INFO] GUI client initialized - attempting connection...")
        
        # Try to connect to GUI proactively
        if self.gui_client.connect():
            print("[INFO] ✓ Connected to GUI - ready for data transmission")
        else:
            print("[INFO] GUI not available - will retry when sending data")
        
        # Default Octave generator configuration
        self.octave_config = {
            "sample_rate": 5.0,  # Update every 200ms (1/0.2 = 5.0 Hz)
            "duration": 200.0
        }
        
        # Check QEMU and SSH
        if self.auto_start_qemu:
            print("[INFO] Starting QEMU with SSH support...")
            qemu_result = start_qemu_and_wait_for_boot()
            if qemu_result and len(qemu_result) == 2:
                self.qemu_process, self.socket_port = qemu_result
            else:
                self.qemu_process = qemu_result
                self.socket_port = None
                
            if self.qemu_process:
                print(f"[INFO] QEMU started with PID: {self.qemu_process.pid}")
                if self.socket_port:
                    print(f"[INFO] Socket port: {self.socket_port}")
                
                # Wait for SSH to be ready
                print("[INFO] Waiting for SSH service...")
                wait_for_ssh_ready(self.ssh_port)
                print(f"[INFO] SSH ready on port {self.ssh_port}")
            else:
                print("[ERROR] Failed to start QEMU")
                sys.exit(1)
        else:
            self.qemu_process = None
            self.socket_port = self.get_socket_port_from_marker()
            msg = f"[INFO] Using existing SSH connection on port {self.ssh_port}"
            print(msg)
        
        self.ssh_remote = SSHRemoteCommand(port=self.ssh_port)
        
        # Auto-start Octave generator (unless disabled)
        if not self.disable_auto_generator:
            self.start_octave_generator()

    def get_socket_port_from_marker(self):
        """Get socket port from QEMU session marker"""
        try:
            import json
            marker_path = '/tmp/qemu_session_active.marker'
            if os.path.exists(marker_path):
                with open(marker_path, 'r') as f:
                    data = json.loads(f.read())
                    socket_port = data.get('socket_port')
                    if socket_port:
                        print(f"[DEBUG] Found QEMU socket port: {socket_port}")
                        return socket_port
            
            # Default port if marker not found
            print("[INFO] No QEMU socket port found, using default 4446 for GUI connection")
            return 4446
        except Exception as e:
            print(f"[WARNING] Error getting socket port: {e}")
            return 5555

    def start_octave_generator(self):
        """Start Octave generator with default sine wave."""
        print("[INFO] Starting Octave generator automatically...")
        try:
            # Generate sine wave: DOUBLED amplitude for wider range
            # Range: 10-45°C → -7.5-62.5°C, Center: 27.5°C, Amplitude: ±35°C, Frequency: 2.0 Hz
            self.generate_signal("sine", {"frequency": 2.0, "amplitude": 35.0, "offset": 27.5})
            print("[INFO] Octave generator started with sine wave (27.5C ±35C, 2.0 Hz, -7.5 to 62.5°C range)")
        except Exception as e:
            print(f"[ERROR] Failed to start Octave generator: {e}")

    def send_temp_to_gui(self, temp_c, temp_mc=None):
        """Send temperature data to GUI if connected."""
        # Try to connect if not connected
        if not self.gui_client.connected:
            print("[INFO] GUI not connected, attempting to establish connection...")
            if not self.gui_client.connect():
                # connect() method already prints detailed error messages
                return
            else:
                print("[INFO] ✓ Ready to send temperature data to GUI")
        
        # Send data
        if not self.gui_client.send_temperature(temp_c, temp_mc):
            print("[WARNING] ✗ Failed to send temperature data to GUI - connection lost")
            self.gui_client.connected = False  # Mark as disconnected for retry

    def generate_signal(self, signal_type, params=None):
        """Generate temperature signal using Octave - writes to QEMU socket.
        
        Supported signal types: sine, ramp, noise, step
        """
        self.stop_octave_generator()
        
        if params is None:
            params = {}
        
        # Default configuration by signal type - doubled amplitude for wider range
        default_configs = {
            "sine": {"frequency": 2.0, "amplitude": 35.0, "offset": 27.5},
            "ramp": {"slope": 8.0, "start": 10, "end": 40},
            "noise": {"mean": 25, "deviation": 20},
            "step": {"low_level": 10, "high_level": 40, "transition_time": 25}
        }
        
        if signal_type not in default_configs:
            print(f"[ERROR] Unsupported signal type: {signal_type}")
            return False
        
        # Merge default configuration with user parameters
        config = {**default_configs[signal_type], **params}
        
        try:
            octave_script = self.create_octave_script(signal_type, config)
            script_file = "/tmp/generate_signal.m"
            
            # Write script to remote system
            write_command = f'cat > {script_file} << \'EOF\'\n{octave_script}\nEOF'
            result = self.ssh_remote.execute_command(write_command)
            
            if result.return_code != 0:
                print(f"[ERROR] Error writing Octave script: {result.stderr}")
                return False
            
            # Execute Octave in background
            # octave_command = f"nohup octave {script_file} > /tmp/octave.log 2>&1 &"
            octave_command = f"nohup octave {script_file} > /tmp/octave.log"
            result = self.ssh_remote.execute_command(octave_command)
            
            if result.return_code != 0:
                print(f"[ERROR] Error executing Octave: {result.stderr}")
                return False
                
            # Wait a moment for script to start
            time.sleep(2)
            
            print(f"[INFO] Signal {signal_type} generator started successfully")
            print(f"[INFO] Writing to QEMU socket port: {self.socket_port}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error generating signal: {e}")
            return False

    def create_octave_script(self, signal_type, params):
        """Create Octave script to generate temperature signal - writes to QEMU socket."""
        sample_rate = self.octave_config["sample_rate"]
        duration = self.octave_config["duration"]
        socket_port = self.socket_port or 4446
        
        base_script = f"""
% Signal configuration
fs = {sample_rate};  % Sample rate (Hz)
duration = {duration};   % Duration (seconds)
t = 0:1/fs:duration;     % Time vector
socket_port = {socket_port};  % QEMU chardev:mysensor socket port

% Function to write temperature to QEMU socket
function write_temperature_to_socket(temp, socket_port)
    try
        % For simplicity, write to netcat (nc) which connects to socket
        temp_str = sprintf('%d\\n', round(temp));
        cmd = sprintf('echo "%s" | nc 127.0.0.1 %d', temp_str, socket_port);
        system(cmd);
        
        % Also log to debug file
        fid = fopen('/tmp/tempsensor_debug.txt', 'a');
        if fid != -1
            fprintf(fid, '[%s] Sent to socket %d: %d°C\\n', 
                    datestr(now), socket_port, round(temp));
            fclose(fid);
        endif
    catch err
        % Log errors to debug file
        fid = fopen('/tmp/tempsensor_debug.txt', 'a');
        if fid != -1
            fprintf(fid, '[%s] Socket error: %s\\n', datestr(now), err.message);
            fclose(fid);
        endif
    end_try_catch
endfunction

"""
        
        if signal_type == "sine":
            freq = params.get("frequency", 1.0)
            amplitude = params.get("amplitude", 25)
            offset = params.get("offset", 25)
            signal_script = f"""
% Sine wave signal
freq = {freq};      % Signal frequency (Hz)
amplitude = {amplitude};  % Amplitude (C)
offset = {offset};       % Offset (C)

fprintf('Generating sine wave: %.2f Hz, amplitude %.1f°C, offset %.1f°C\\n', freq, amplitude, offset);
for i = 1:length(t)
    temp = offset + amplitude * sin(2 * pi * freq * t(i));
    write_temperature_to_socket(temp, socket_port);
    pause(1/fs);
endfor
"""
            
        elif signal_type == "ramp":
            slope = params.get("slope", 8.0)
            start = params.get("start", 10)
            signal_script = f"""
% Ramp signal
slope = {slope};     % Slope (C/s)
start_val = {start};    % Initial value (C)

fprintf('Generating ramp signal: slope %.2f°C/s, start %.1f°C\\n', slope, start_val);
for i = 1:length(t)
    temp = start_val + slope * t(i);
    write_temperature_to_socket(temp, socket_port);
    pause(1/fs);
endfor
"""
            
        elif signal_type == "noise":
            mean = params.get("mean", 25)
            deviation = params.get("deviation", 20)
            signal_script = f"""
% Noise signal
mean_val = {mean};      % Mean (C)
std_dev = {deviation};  % Standard deviation (C)

fprintf('Generating noise signal: mean %.1f°C, std dev %.1f°C\\n', mean_val, std_dev);
randn('seed', round(time()));
for i = 1:length(t)
    temp = mean_val + std_dev * randn();
    write_temperature_to_socket(temp, socket_port);
    pause(1/fs);
endfor
"""
            
        elif signal_type == "step":
            low_level = params.get("low_level", 10)
            high_level = params.get("high_level", 40)
            transition_time = params.get("transition_time", 25)
            signal_script = f"""
% Step signal
low_level = {low_level};      % Low level (C)
high_level = {high_level};     % High level (C)
step_time = {transition_time}; % Transition time (% of duration)

fprintf('Generating step signal: %.1f°C -> %.1f°C at %.0f%% duration\\n', 
        low_level, high_level, step_time);
step_index = round(length(t) * step_time / 100);
for i = 1:length(t)
    if i < step_index
        temp = low_level;
    else
        temp = high_level;
    endif
    write_temperature_to_socket(temp, socket_port);
    pause(1/fs);
endfor
"""
        
        output_script = f"""
fprintf('Signal generation completed. Check /tmp/tempsensor_debug.txt for details.\\n');
"""
        
        return base_script + signal_script + output_script

    def stop_octave_generator(self):
        """Stop any running Octave process."""
        try:
            # Kill Octave processes
            kill_command = "pkill -f octave || true"
            result = self.ssh_remote.execute_command(kill_command)
            
            # Clean temporary files
            clean_command = "rm -f /tmp/generate_signal.m /tmp/octave.log || true"
            self.ssh_remote.execute_command(clean_command)
            
        except Exception as e:
            print(f"[WARNING] Error stopping Octave generator: {e}")

    def show_current_config(self):
        """Show current system configuration."""
        print("\n=== Current SimTemp Configuration ===")
        
        try:
            # Read sample rate
            result = self.ssh_remote.execute_command(f"cat {self.sysfs_base}/sampling_ms")
            if result.return_code == 0:
                freq_ms = int(result.stdout.strip())
                print(f"Sample Rate: {freq_ms}ms ({1000/freq_ms:.1f} Hz)")
            else:
                print("Sample Rate: Not available")
            
            # Read threshold
            result = self.ssh_remote.execute_command(f"cat {self.sysfs_base}/threshold_mC")
            if result.return_code == 0:
                threshold = int(result.stdout.strip())
                print(f"Threshold: {threshold/1000:.1f} C milliCelsius ({threshold})")
            else:
                print("Threshold: Not available")
            
            # Check device status
            result = self.ssh_remote.execute_command(f"ls -l {self.device_path}")
            if result.return_code == 0:
                print(f"Device: {self.device_path} [OK]")
            else:
                print(f"Device: {self.device_path} [ERROR]")
            
            # Octave generator status
            result = self.ssh_remote.execute_command("pgrep -f octave")
            if result.return_code == 0:
                print("Octave Generator: [RUNNING]")
                print(f"Socket Port: {self.socket_port}")
            else:
                print("Octave Generator: [NOT RUNNING]")
                
        except Exception as e:
            print(f"[ERROR] Error getting configuration: {e}")
        
        print("="*40)

    def set_sample_rate(self, frequency_ms: int):
        """Set system sample rate in milliseconds."""
        try:
            command = f"echo {frequency_ms} > {self.sysfs_base}/sampling_ms"
            result = self.ssh_remote.execute_command(command)
            
            if result.return_code == 0:
                print(f"[INFO] Sample rate set: {frequency_ms}ms ({1000/frequency_ms:.1f} Hz)")
                return True
            else:
                print(f"[ERROR] Error setting sample rate: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error setting sample rate: {e}")
            return False

    def set_threshold(self, threshold_mc: int):
        """Set temperature threshold in milliCelsius."""
        try:
            command = f"echo {threshold_mc} > {self.sysfs_base}/threshold_mC"
            result = self.ssh_remote.execute_command(command)
            
            if result.return_code == 0:
                print(f"[INFO] Threshold set: {threshold_mc} mC ({threshold_mc/1000:.1f} C)")
                return True
            else:
                print(f"[ERROR] Error setting threshold: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error setting threshold: {e}")
            return False

    def generate_random_noise_to_gui(self):
        """Generate random temperature noise data from 20-60°C at maximum rate and send to sensor port 4445"""
        import random
        import threading
        import time
        import socket
        
        print("[INFO] Starting HIGH-SPEED random noise generator: 20-60°C")
        print("[INFO] Sending random data to sensor port 4445 at MAXIMUM RATE")
        print("[INFO] Use 'run' command to read the generated data")
        print("[INFO] Press Ctrl+C or use 'stop' command to stop")
        
        def noise_generator():
            try:
                while True:
                    # Generate random temperature between 20-60°C with high variability
                    # Add some more dramatic swings for better visual noise
                    if random.random() < 0.8:  # 10% chance of extreme values
                        temp = random.choice([20, 60])  # Extreme values
                    else:
                        temp = random.uniform(20, 60)  # Normal range
                    
                    # Send to sensor port 4445 (like other signal generators)
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.05)  # Very short timeout for maximum speed
                        sock.connect(("127.0.0.1", 4445))
                        # Convert to milliCelsius for sensor compatibility
                        temp_mc = int(round(temp * 1000))  # Convert °C to mC
                        temp_str = f"{temp_mc}\n"
                        sock.send(temp_str.encode())
                        sock.close()
                    except Exception:
                        pass  # Silent fail, keep generating at maximum speed
                    
                    # No delay for absolute maximum rate
                    
            except Exception as e:
                print(f"[INFO] Noise generator stopped: {e}")
        
        # Start noise generator in background thread
        noise_thread = threading.Thread(target=noise_generator, daemon=True)
        noise_thread.start()

    def read_temperature_continuous(self, duration: int = 0, count: int = 0):
        """Read temperature continuously."""
        print(f"[INFO] Starting continuous temperature reading...")
        if duration > 0:
            print(f"[INFO] Duration: {duration} seconds")
        if count > 0:
            print(f"[INFO] Maximum {count} readings")
        print("[INFO] Press Ctrl+C to stop")
        
        try:
            start_time = time.time()
            readings_done = 0
            
            while True:
                # Check stop conditions
                if duration > 0 and (time.time() - start_time) >= duration:
                    break
                if count > 0 and readings_done >= count:
                    break
                
                # Read temperature
                result = self.ssh_remote.execute_command(f"cat {self.device_path}")
                if result.return_code == 0:
                    temp_str = result.stdout.strip()
                    try:
                        temp_mc = int(temp_str)
                        temp_c = temp_mc / 1000.0
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"[{timestamp}] Temperature: {temp_c:.3f} C ({temp_mc} mC)   ===>")
                        
                        # Send to GUI if enabled
                        self.send_temp_to_gui(temp_c, temp_mc)
                        
                        readings_done += 1
                    except ValueError:
                        print(f"[ERROR] Invalid temperature value: {temp_str}")
                else:
                    print(f"[ERROR] Error reading temperature: {result.stderr}")
                
                time.sleep(0.1)  # Wait 100ms between readings
                
        except KeyboardInterrupt:
            print(f"\n[INFO] Reading stopped by user")
            print(f"[INFO] Total readings done: {readings_done}")

    def interactive_mode(self):
        """Interactive mode with voice commands."""
        print("\nSimTemp Remote CLI - Interactive Mode")
        print("=" * 50)
        print("Available commands:")
        print("  status                    - Show current configuration")
        print("  samples <ms>              - Set sample rate in milliseconds")
        print("  thr <C>                   - Set temperature threshold")
        print("  run [duration] [count]    - Run temperature reading (duration in sec, count max readings)")
        print("  gui on/off                - Enable/disable GUI connection")
        print("  gen sine [samples] [amp] [offset] - Sine wave (default: 20 samples, 27.5±35°C)")
        print("  gen ramp [samples] [start]       - Ramp signal (default: 80 samples, from 10°C)")
        print("  gen noise                        - Noise signal (20-60°C at maximum rate)")
        print("  gen step [low] [high] [time]     - Step signal (default: 10→40°C at 25%)")
        print("  stop                      - Stop generator")
        print("  help                      - Show this help")
        print("  exit, quit, q             - Exit")
        print("=" * 50)
        print("\n[INFO] Sine wave ready. Type 'run' to start reading temperatures.")
        
        while True:
            try:
                input_text = input("\nsimtemp> ").strip().lower()
                
                if input_text in ["exit", "quit", "q"]:
                    break
                elif input_text == "status":
                    self.show_current_config()
                elif input_text.startswith("samples "):
                    try:
                        parts = input_text.split()
                        if len(parts) >= 2:
                            freq_ms = int(parts[1])
                            self.set_sample_rate(freq_ms)
                        else:
                            print("[ERROR] Usage: samples <ms>")
                    except ValueError:
                        print("[ERROR] Sample rate must be an integer")
                elif input_text.startswith("thr "):
                    try:
                        parts = input_text.split()
                        if len(parts) >= 2:
                            threshold_c = float(parts[1])
                            threshold_mc = int(threshold_c * 1000)
                            self.set_threshold(threshold_mc)
                        else:
                            print("[ERROR] Usage: thr <C>")
                    except ValueError:
                        print("[ERROR] Threshold must be a number")
                elif input_text.startswith("run"):
                    parts = input_text.split()
                    duration = int(parts[1]) if len(parts) > 1 else 0
                    count = int(parts[2]) if len(parts) > 2 else 0
                    self.read_temperature_continuous(duration, count)
                elif input_text.startswith("gen "):
                    self.process_gen_command(input_text)
                elif input_text == "stop":
                    self.stop_octave_generator()
                    print("[INFO] Generator stopped")
                elif input_text == "help":
                    print("\nAvailable commands:")
                    print("  status                    - Show current configuration")
                    print("  samples <ms>              - Set sample rate in milliseconds")
                    print("  thr <C>                   - Set temperature threshold")
                    print("  run [duration] [count]    - Run temperature reading")
                    print("  gen sine [samples] [amp] [offset] - Sine wave (default: 20 samples, 27.5±35°C)")
                    print("  gen ramp [samples] [start]       - Ramp signal (default: 80 samples, from 10°C)")
                    print("  gen noise                        - Noise signal (20-60°C at maximum rate)")
                    print("  gen step [low] [high] [time]     - Step signal (default: 10→40°C at 25%)")
                    print("  stop                      - Stop generator")
                    print("  exit, quit, q             - Exit")
                elif input_text == "":
                    continue  # Empty line, continue
                else:
                    print(f"[ERROR] Unrecognized command: {input_text}")
                    print("Type 'help' to see available commands")
                    
            except KeyboardInterrupt:
                print("\n")
                continue  # Don't exit on Ctrl+C, just new prompt
            except EOFError:
                break
        
        print("\nExiting SimTemp Remote CLI")
        print("Thank you for using SimTemp!")

    def process_gen_command(self, command):
        """Process signal generation commands."""
        parts = command.split()
        if len(parts) < 2:
            print("[ERROR] Usage: gen <type> [parameters]")
            return
            
        signal_type = parts[1]
        
        try:
            if signal_type == "sine":
                # gen sine [samples] [amp] [offset] - defaults for doubled amplitude range
                samples = float(parts[2]) if len(parts) > 2 else 20  # 2.0 Hz default
                amp = float(parts[3]) if len(parts) > 3 else 35.0    # ±35°C (doubled)
                offset = float(parts[4]) if len(parts) > 4 else 27.5  # 27.5°C center
                # Convert samples to frequency: higher samples = higher frequency
                freq = samples / 10.0  # samples/10 gives reasonable frequency range
                params = {"frequency": freq, "amplitude": amp, "offset": offset}
                self.generate_signal("sine", params)
                print(f"[INFO] Generating sine wave: {samples} samples/period, +/-{amp}C, offset {offset}C")
                
            elif signal_type == "ramp":
                # gen ramp [samples] [start]
                samples = float(parts[2]) if len(parts) > 2 else 80
                start = float(parts[3]) if len(parts) > 3 else 10
                # Convert samples to slope: higher samples = faster ramp
                slope = samples / 10.0  # samples/10 gives reasonable slope range
                params = {"slope": slope, "start": start}
                self.generate_signal("ramp", params)
                print(f"[INFO] Generating ramp signal: {samples} samples/step, start {start}C")
                
            elif signal_type == "noise":
                # gen noise - generates random data from 20-60°C at maximum rate
                self.generate_random_noise_to_gui()
                print("[INFO] Generating random noise: 20-60°C at maximum rate")
                
            elif signal_type == "step":
                # gen step [low] [high] [time]
                low = float(parts[2]) if len(parts) > 2 else 10
                high = float(parts[3]) if len(parts) > 3 else 40
                time_pct = float(parts[4]) if len(parts) > 4 else 25
                params = {"low_level": low, "high_level": high, "transition_time": time_pct}
                self.generate_signal("step", params)
                print(f"[INFO] Generating step signal: {low}C -> {high}C at {time_pct}% duration")
                
            else:
                print(f"[ERROR] Unsupported signal type: {signal_type}")
                print("Available types: sine, ramp, noise, step")
                
        except ValueError:
            print("[ERROR] Invalid parameters. Must be numbers.")
        except Exception as e:
            print(f"[ERROR] Error processing command: {e}")
            return
        
        # Inform user that wave is ready, but don't auto-start reading
        print("[INFO] Wave generated. Type 'run' to start reading temperatures.")

    def cleanup(self):
        """Clean up resources when finishing."""
        self.stop_octave_generator()
        if hasattr(self, 'gui_client'):
            self.gui_client.disconnect()
        if hasattr(self, 'ssh_remote'):
            self.ssh_remote.cleanup()
        if hasattr(self, 'qemu_process') and self.qemu_process:
            cleanup_qemu_processes()


def main():
    parser = argparse.ArgumentParser(
        description="SimTemp Remote CLI - Interactive Driver Configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default - uses existing SSH)
  %(prog)s
  
  # Interactive mode with auto-start QEMU
  %(prog)s --auto-start
  
  # Show configuration
  %(prog)s --status
  
  # Set sample rate to 500ms
  %(prog)s --set-rate 500
  
  # Set threshold to 40C
  %(prog)s --set-threshold 40.0
  
  # Read temperature for 30 seconds
  %(prog)s --read --duration 30
  
  # Read 100 samples
  %(prog)s --read --count 100
        """
    )
    
    # Connection options
    parser.add_argument('--ssh-port', type=int, default=2222,
                       help='SSH port (default: 2222)')
    parser.add_argument('--auto-start', action='store_true',
                       help='Auto-start QEMU (default: use existing SSH)')
    
    # Actions
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode (default behavior)')
    parser.add_argument('--status', action='store_true',
                       help='Show current configuration')
    parser.add_argument('--set-rate', type=int, metavar='MS',
                       help='Set sample rate in milliseconds')
    parser.add_argument('--set-threshold', type=float, metavar='CELSIUS',
                       help='Set threshold in Celsius')
    parser.add_argument('--read', action='store_true',
                       help='Read temperature continuously')
    parser.add_argument('--duration', type=int, metavar='SECONDS',
                       help='Duration for continuous reading (0=infinite)')
    parser.add_argument('--count', type=int, metavar='SAMPLES',
                       help='Number of samples to read (0=infinite)')
    
    args = parser.parse_args()
    
    # Create CLI instance
    cli = SimTempRemoteCLI(
        ssh_port=args.ssh_port,
        auto_start_qemu=args.auto_start,
        disable_auto_generator=False  # Keep generator always available
    )
    
    try:
        # Execute actions
        if args.status:
            cli.show_current_config()
        
        elif args.set_rate is not None:
            cli.set_sample_rate(args.set_rate)
        
        elif args.set_threshold is not None:
            threshold_mc = int(args.set_threshold * 1000)
            cli.set_threshold(threshold_mc)
        
        elif args.read:
            duration = args.duration or 0
            count = args.count or 0
            cli.read_temperature_continuous(duration, count)
        
        elif args.interactive:
            cli.interactive_mode()
        
        else:
            # Default: interactive mode if no specific action
            cli.interactive_mode()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1
    
    finally:
        cli.cleanup()


if __name__ == "__main__":
    sys.exit(main())