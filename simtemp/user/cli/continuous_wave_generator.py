#!/usr/bin/env python3
"""
SimTemp Continuous Wave Generator Integration
Copyright (c) 2025 Jorge Rodriguez Moreno

Integrates octv_temp_generator with the nxp_simtemp sensor port
to generate continuous wave patterns directly to the device.

Features:
- Real-time continuous wave generation
- Multiple wave types (sine, square, triangle, sawtooth)
- Configurable frequency, amplitude, and offset
- Direct writing to SimTemp device port
- Octave pattern integration
- Real-time monitoring and control
"""

import os
import sys
import time
import math
import threading
import argparse
import signal
import random
from pathlib import Path
from typing import Dict, List

# Import the existing temperature generator
sys.path.append(str(Path(__file__).parent / "models" / "octv_temp_generator"))
try:
    from temperature_generator import (TemperaturePatternGenerator, 
                                     KernelTemperatureController)
except ImportError:
    print("Warning: Octave temperature generator not available")
    TemperaturePatternGenerator = None
    KernelTemperatureController = None


class WaveformGenerator:
    """Generate various continuous waveforms for temperature simulation"""
    
    def __init__(self):
        self.wave_functions = {
            'sine': self._sine_wave,
            'square': self._square_wave,
            'triangle': self._triangle_wave,
            'sawtooth': self._sawtooth_wave,
            'noise': self._noise_wave,
            'step': self._step_wave,
            'ramp': self._ramp_wave
        }
    
    def _sine_wave(self, t: float, frequency: float, amplitude: float, offset: float) -> float:
        """Generate sine wave: A * sin(2π * f * t) + offset"""
        return amplitude * math.sin(2.0 * math.pi * frequency * t) + offset
    
    def _square_wave(self, t: float, frequency: float, amplitude: float, offset: float) -> float:
        """Generate square wave"""
        sine_val = math.sin(2.0 * math.pi * frequency * t)
        return amplitude * (1.0 if sine_val >= 0 else -1.0) + offset
    
    def _triangle_wave(self, t: float, frequency: float, amplitude: float, offset: float) -> float:
        """Generate triangle wave"""
        period = 1.0 / frequency
        t_mod = t % period
        if t_mod < period / 2:
            return amplitude * (4 * t_mod / period - 1) + offset
        else:
            return amplitude * (3 - 4 * t_mod / period) + offset
    
    def _sawtooth_wave(self, t: float, frequency: float, amplitude: float, offset: float) -> float:
        """Generate sawtooth wave"""
        period = 1.0 / frequency
        t_mod = t % period
        return amplitude * (2 * t_mod / period - 1) + offset
    
    def _noise_wave(self, t: float, frequency: float, amplitude: float, offset: float) -> float:
        """Generate random noise (frequency parameter ignored)"""
        return amplitude * (random.random() * 2 - 1) + offset
    
    def _step_wave(self, t: float, frequency: float, amplitude: float, offset: float) -> float:
        """Generate step function that changes every period"""
        period = 1.0 / frequency
        step_number = int(t / period) % 4
        steps = [-1, -0.3, 0.3, 1]
        return amplitude * steps[step_number] + offset
    
    def _ramp_wave(self, t: float, frequency: float, amplitude: float, offset: float) -> float:
        """Generate slow ramp wave over long period"""
        period = 1.0 / frequency
        ramp_period = period * 10  # 10x longer than base frequency
        t_mod = t % ramp_period
        return amplitude * (2 * t_mod / ramp_period - 1) + offset
    
    def generate_sample(self, wave_type: str, t: float, frequency: float, 
                       amplitude: float, offset: float) -> float:
        """Generate a single waveform sample at time t"""
        if wave_type not in self.wave_functions:
            raise ValueError(f"Unknown wave type: {wave_type}")
        
        return self.wave_functions[wave_type](t, frequency, amplitude, offset)
    
    def get_available_waves(self) -> List[str]:
        """Get list of available waveform types"""
        return list(self.wave_functions.keys())


class SimTempPortController:
    """Controller for direct SimTemp sensor port communication via Telnet"""
    
    def __init__(self, device_path: str = "/dev/simtemp", 
                 telnet_host: str = None, telnet_port: int = 23):
        self.device_path = device_path
        self.sysfs_base = "/sys/class/misc/simtemp"
        self.device_fd = None
        self.telnet_host = telnet_host
        self.telnet_port = telnet_port
        self.telnet_connection = None
        
        # Initialize kernel controller if available
        if KernelTemperatureController:
            self.kernel_controller = KernelTemperatureController()
        else:
            self.kernel_controller = None
        
    def open_device(self) -> bool:
        """Open the device (local or remote via telnet)"""
        try:
            if self.telnet_host:
                # Use telnet connection
                import telnetlib
                print(f"Connecting to SimTemp sensor via telnet {self.telnet_host}:{self.telnet_port}")
                self.telnet_connection = telnetlib.Telnet(self.telnet_host, self.telnet_port, timeout=10)
                print(f"✓ Connected to {self.telnet_host}:{self.telnet_port}")
                return True
            else:
                # Use local device
                if not os.path.exists(self.device_path):
                    print(f"ERROR: Device {self.device_path} not found")
                    print("TIP: Use --host and --port for telnet connection to remote sensor")
                    return False
                
                # We'll use sysfs for temperature control instead of direct device write
                # as the device is primarily for reading
                print(f"✓ Device {self.device_path} is available")
                return True
                
        except Exception as e:
            print(f"ERROR: Failed to connect to sensor: {e}")
            return False
    
    def close_device(self):
        """Close the device"""
        if self.telnet_connection:
            self.telnet_connection.close()
            self.telnet_connection = None
        if self.device_fd:
            os.close(self.device_fd)
            self.device_fd = None

    def write_temperature(self, temp_celsius: float) -> bool:
        """Write temperature to the SimTemp sensor (local or telnet)"""
        try:
            if self.telnet_connection:
                # Send temperature via telnet
                temp_command = f"SET_TEMP {temp_celsius:.2f}\r\n"
                self.telnet_connection.write(temp_command.encode('ascii'))
                return True
            else:
                # Write to local sysfs
                temp_mc = int(temp_celsius * 1000)  # Convert to milliCelsius
                
                # Write to sysfs temperature attribute
                temp_file = os.path.join(self.sysfs_base, "temperature")
                if os.path.exists(temp_file):
                    with open(temp_file, 'w') as f:
                        f.write(str(temp_mc))
                    return True
                else:
                    # Alternative path - write to mode with custom value
                    mode_file = os.path.join(self.sysfs_base, "mode")
                    if os.path.exists(mode_file):
                        # Set mode to allow custom temperature injection
                        with open(mode_file, 'w') as f:
                            f.write("custom")
                        
                        # Use a custom method to inject temperature
                        return self._inject_temperature_via_proc(temp_mc)
                
        except Exception as e:
            print(f"ERROR: Failed to write temperature {temp_celsius}°C: {e}")
            return False
        
        return False
    
    def _inject_temperature_via_proc(self, temp_mc: int) -> bool:
        """Alternative method to inject temperature via procfs or debugfs"""
        try:
            # Try debugfs path (if available)
            debugfs_paths = [
                "/sys/kernel/debug/simtemp/inject_temp",
                "/proc/simtemp/inject_temp"
            ]
            
            for path in debugfs_paths:
                if os.path.exists(path):
                    with open(path, 'w') as f:
                        f.write(str(temp_mc))
                    return True
            
            print("WARNING: No direct temperature injection interface found")
            return False
            
        except Exception as e:
            print(f"ERROR: Failed to inject temperature: {e}")
            return False
    
    def set_sampling_period(self, period_ms: int) -> bool:
        """Set the sampling period for the sensor"""
        if self.kernel_controller:
            return self.kernel_controller.set_sampling_period(period_ms)
        else:
            print("Warning: Kernel controller not available")
            return False
    
    def get_device_status(self) -> Dict:
        """Get current device status"""
        if self.kernel_controller:
            devices = self.kernel_controller.get_device_status()
            if devices:
                return devices[0]  # Return first device
        return {"stats": {"status": "kernel_controller_unavailable"}}


class ContinuousWaveGenerator:
    """Main continuous wave generator for SimTemp integration"""
    
    def __init__(self, device_path: str = "/dev/simtemp", 
                 telnet_host: str = None, telnet_port: int = 23):
        self.device_controller = SimTempPortController(device_path, telnet_host, telnet_port)
        self.waveform_generator = WaveformGenerator()
        
        # Initialize pattern generator if available
        if TemperaturePatternGenerator:
            self.pattern_generator = TemperaturePatternGenerator()
        else:
            self.pattern_generator = None
        
        # Wave parameters
        self.wave_type = "sine"
        self.frequency = 0.1  # Hz (10 second period)
        self.amplitude = 10.0  # °C
        self.offset = 35.0     # °C (center temperature)
        self.sampling_period_ms = 200  # 200ms sampling
        
        # Control variables
        self.running = False
        self.generation_thread = None
        self.start_time = None
        
        # Statistics
        self.samples_generated = 0
        self.errors_count = 0
        
    def configure_wave(self, wave_type: str, frequency: float, 
                      amplitude: float, offset: float, sampling_ms: int):
        """Configure wave generation parameters"""
        if wave_type not in self.waveform_generator.get_available_waves():
            raise ValueError(f"Invalid wave type: {wave_type}")
        
        self.wave_type = wave_type
        self.frequency = frequency
        self.amplitude = amplitude
        self.offset = offset
        self.sampling_period_ms = sampling_ms
        
        print(f"✓ Configured wave: {wave_type}")
        print(f"  Frequency: {frequency} Hz")
        print(f"  Amplitude: ±{amplitude}°C")
        print(f"  Offset: {offset}°C")
        print(f"  Sampling: {sampling_ms}ms")
    
    def start_generation(self) -> bool:
        """Start continuous wave generation"""
        if self.running:
            print("WARNING: Wave generation already running")
            return False
        
        if not self.device_controller.open_device():
            return False
        
        # Set sampling period in the device
        self.device_controller.set_sampling_period(self.sampling_period_ms)
        
        self.running = True
        self.start_time = time.time()
        self.samples_generated = 0
        self.errors_count = 0
        
        # Start generation thread
        self.generation_thread = threading.Thread(target=self._generation_loop)
        self.generation_thread.daemon = True
        self.generation_thread.start()
        
        print(f"✓ Started continuous wave generation: {self.wave_type}")
        print(f"  Target range: {self.offset - self.amplitude:.1f}°C to "
              f"{self.offset + self.amplitude:.1f}°C")
        
        return True
    
    def stop_generation(self):
        """Stop continuous wave generation"""
        if not self.running:
            return
        
        self.running = False
        
        if self.generation_thread and self.generation_thread.is_alive():
            self.generation_thread.join(timeout=2.0)
        
        self.device_controller.close_device()
        
        duration = time.time() - self.start_time if self.start_time else 0
        
        print(f"✓ Stopped wave generation")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Samples generated: {self.samples_generated}")
        print(f"  Errors: {self.errors_count}")
        print(f"  Average rate: {self.samples_generated/duration:.1f} samples/sec")
    
    def _generation_loop(self):
        """Main generation loop running in separate thread"""
        print("Starting generation loop...")
        
        while self.running:
            try:
                # Calculate current time relative to start
                current_time = time.time() - self.start_time
                
                # Generate temperature sample
                temperature = self.waveform_generator.generate_sample(
                    self.wave_type, current_time, self.frequency,
                    self.amplitude, self.offset
                )
                
                # Write to device
                if self.device_controller.write_temperature(temperature):
                    self.samples_generated += 1
                    
                    # Print periodic status
                    if self.samples_generated % 50 == 0:
                        print(f"Generated {self.samples_generated} samples, "
                              f"current: {temperature:.1f}°C")
                else:
                    self.errors_count += 1
                
                # Sleep for sampling period
                time.sleep(self.sampling_period_ms / 1000.0)
                
            except Exception as e:
                print(f"ERROR in generation loop: {e}")
                self.errors_count += 1
                time.sleep(0.1)  # Short delay on error
    
    def load_octave_pattern(self, pattern_name: str) -> bool:
        """Load and use an Octave-generated pattern"""
        if not self.pattern_generator:
            print("ERROR: Octave pattern generator not available")
            return False
            
        print(f"Loading Octave pattern: {pattern_name}")
        
        # Generate patterns if needed
        if not self.pattern_generator.generate_patterns():
            return False
        
        # Load patterns
        if not self.pattern_generator.load_patterns():
            return False
        
        # Get pattern info
        pattern_info = self.pattern_generator.get_pattern_info(pattern_name)
        if not pattern_info:
            print(f"ERROR: Pattern '{pattern_name}' not found")
            return False
        
        print(f"✓ Loaded pattern: {pattern_name}")
        print(f"  Samples: {pattern_info['samples']}")
        print(f"  Duration: {pattern_info['duration_ms']/1000:.1f}s")
        temp_min = pattern_info['temp_range_C'][0]
        temp_max = pattern_info['temp_range_C'][1]
        print(f"  Temperature range: {temp_min:.1f}°C to {temp_max:.1f}°C")
        
        # Start pattern playback
        return self._start_pattern_playback(pattern_name)
    
    def _start_pattern_playback(self, pattern_name: str) -> bool:
        """Start playback of an Octave pattern"""
        if self.running:
            print("WARNING: Generation already running")
            return False
        
        if not self.device_controller.open_device():
            return False
        
        # Get pattern data
        pattern_data = self.pattern_generator.patterns[pattern_name]
        
        self.running = True
        self.start_time = time.time()
        self.samples_generated = 0
        self.errors_count = 0
        
        # Start pattern playback thread
        self.generation_thread = threading.Thread(
            target=self._pattern_playback_loop,
            args=(pattern_data,)
        )
        self.generation_thread.daemon = True
        self.generation_thread.start()
        
        print(f"✓ Started pattern playback: {pattern_name}")
        return True
    
    def _pattern_playback_loop(self, pattern_data: List):
        """Playback loop for Octave patterns"""
        print("Starting pattern playback loop...")
        
        pattern_index = 0
        
        while self.running:
            try:
                if pattern_index >= len(pattern_data):
                    print("Pattern completed, restarting...")
                    pattern_index = 0
                
                # Get next sample
                time_ms, temp_mc = pattern_data[pattern_index]
                temperature = temp_mc / 1000.0  # Convert to Celsius
                
                # Write to device
                if self.device_controller.write_temperature(temperature):
                    self.samples_generated += 1
                    
                    if self.samples_generated % 20 == 0:
                        samples_info = f"{pattern_index}/{len(pattern_data)}"
                        print(f"Pattern sample {samples_info}, "
                              f"temp: {temperature:.1f}°C")
                else:
                    self.errors_count += 1
                
                pattern_index += 1
                
                # Use pattern timing or fall back to sampling period
                sleep_time = self.sampling_period_ms / 1000.0
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"ERROR in pattern playback: {e}")
                self.errors_count += 1
                time.sleep(0.1)
    
    def get_status(self) -> Dict:
        """Get current generator status"""
        device_status = self.device_controller.get_device_status()
        
        duration = time.time() - self.start_time if self.start_time else 0
        
        return {
            'running': self.running,
            'wave_type': self.wave_type,
            'frequency': self.frequency,
            'amplitude': self.amplitude,
            'offset': self.offset,
            'sampling_ms': self.sampling_period_ms,
            'duration': duration,
            'samples_generated': self.samples_generated,
            'errors_count': self.errors_count,
            'device_status': device_status
        }


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutdown signal received...")
    global generator
    if generator:
        generator.stop_generation()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="SimTemp Continuous Wave Generator Integration"
    )
    
    # Wave configuration
    parser.add_argument("--wave", default="sine",
                       help="Wave type (sine, square, triangle, sawtooth, noise, step, ramp)")
    parser.add_argument("--frequency", type=float, default=0.1,
                       help="Frequency in Hz (default: 0.1)")
    parser.add_argument("--amplitude", type=float, default=10.0,
                       help="Amplitude in °C (default: 10.0)")
    parser.add_argument("--offset", type=float, default=35.0,
                       help="Offset temperature in °C (default: 35.0)")
    parser.add_argument("--sampling", type=int, default=200,
                       help="Sampling period in ms (default: 200)")
    
    # Device configuration
    parser.add_argument("--device", default="/dev/simtemp",
                       help="SimTemp device path")
    parser.add_argument("--host", 
                       help="Telnet host for remote SimTemp sensor")
    parser.add_argument("--port", type=int, default=23,
                       help="Telnet port (default: 23)")
    
    # Operation modes
    parser.add_argument("--duration", type=int,
                       help="Run for specified duration in seconds")
    parser.add_argument("--pattern",
                       help="Use Octave-generated pattern instead of wave")
    parser.add_argument("--list-patterns", action="store_true",
                       help="List available Octave patterns")
    parser.add_argument("--list-waves", action="store_true",
                       help="List available wave types")
    parser.add_argument("--status", action="store_true",
                       help="Show current device status")
    
    args = parser.parse_args()
    
    global generator
    generator = ContinuousWaveGenerator(args.device, args.host, args.port)
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Handle list commands
    if args.list_waves:
        print("Available wave types:")
        for wave in generator.waveform_generator.get_available_waves():
            print(f"  - {wave}")
        return
    
    if args.list_patterns:
        if generator.pattern_generator.load_patterns():
            print("Available Octave patterns:")
            for pattern in generator.pattern_generator.list_patterns():
                info = generator.pattern_generator.get_pattern_info(pattern)
                if info:
                    print(f"  - {pattern}: {info['samples']} samples, "
                          f"{info['duration_ms']/1000:.1f}s, "
                          f"{info['temp_range_C'][0]:.1f}°C to {info['temp_range_C'][1]:.1f}°C")
        return
    
    if args.status:
        status = generator.get_status()
        print("SimTemp Generator Status:")
        for key, value in status.items():
            if key == 'device_status':
                print(f"  {key}:")
                for dk, dv in value.get('stats', {}).items():
                    print(f"    {dk}: {dv}")
            else:
                print(f"  {key}: {value}")
        return
    
    # Main operation
    try:
        if args.pattern:
            # Use Octave pattern
            print(f"=== SimTemp Octave Pattern Generator ===")
            print(f"Loading pattern: {args.pattern}")
            
            if not generator.load_octave_pattern(args.pattern):
                print("ERROR: Failed to load Octave pattern")
                return 1
                
        else:
            # Use continuous wave
            print(f"=== SimTemp Continuous Wave Generator ===")
            print(f"Configuring wave generation...")
            
            generator.configure_wave(
                args.wave, args.frequency, args.amplitude, 
                args.offset, args.sampling
            )
            
            if not generator.start_generation():
                print("ERROR: Failed to start wave generation")
                return 1
        
        # Run for specified duration or until interrupted
        if args.duration:
            print(f"Running for {args.duration} seconds...")
            time.sleep(args.duration)
            generator.stop_generation()
        else:
            print("Running continuously... Press Ctrl+C to stop")
            while generator.running:
                time.sleep(1)
                
                # Print periodic status
                status = generator.get_status()
                if status['samples_generated'] % 100 == 0 and status['samples_generated'] > 0:
                    print(f"Status: {status['samples_generated']} samples, "
                          f"{status['duration']:.1f}s runtime, "
                          f"{status['errors_count']} errors")
    
    except KeyboardInterrupt:
        print("\nStopping generation...")
        generator.stop_generation()
    
    except Exception as e:
        print(f"ERROR: {e}")
        generator.stop_generation()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())