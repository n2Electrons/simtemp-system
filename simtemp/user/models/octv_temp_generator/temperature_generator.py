#!/usr/bin/env python3
"""
Temperature Pattern Generator and Loader
Copyright (c) 2025 Jorge Rodriguez Moreno

This script:
1. Runs GNU Octave to generate temperature patterns
2. Loads the generated patterns into the kernel driver
3. Provides runtime control of temperature simulation modes

Usage:
    python3 temperature_generator.py [--pattern PATTERN] [--octave-path PATH]
"""

import os
import sys
import csv
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class TemperaturePatternGenerator:
    """Generate and manage temperature patterns using GNU Octave"""
    
    def __init__(self, octave_path: str = "octave"):
        self.octave_path = octave_path
        self.script_dir = Path(__file__).parent
        self.patterns_dir = self.script_dir / "temperature_patterns"
        self.octave_script = self.script_dir / "temperature_model.m"
        self.patterns: Dict[str, List[Tuple[int, int]]] = {}
        
    def check_octave_available(self) -> bool:
        """Check if GNU Octave is available"""
        try:
            result = subprocess.run([self.octave_path, "--version"],
                                    capture_output=True, text=True,
                                    timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✓ Found GNU Octave: {version_line}")
                return True
            else:
                print(f"✗ Octave not working: {result.stderr}")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print(f"✗ GNU Octave not found at: {self.octave_path}")
            return False
    
    def generate_patterns(self) -> bool:
        """Run Octave script to generate temperature patterns"""
        print("=== Generating Temperature Patterns with GNU Octave ===")
        
        if not self.check_octave_available():
            print("ERROR: GNU Octave is required but not available")
            print("Install with: sudo apt install octave")
            return False
        
        if not self.octave_script.exists():
            print(f"ERROR: Octave script not found: {self.octave_script}")
            return False
        
        try:
            print(f"Running Octave script: {self.octave_script}")
            
            # Change to script directory to run Octave
            original_cwd = os.getcwd()
            os.chdir(self.script_dir)
            
            # Run Octave script
            octave_cmd = f"run('{self.octave_script.name}')"
            cmd = [self.octave_path, "--silent", "--eval", octave_cmd]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=60)
            
            os.chdir(original_cwd)
            
            if result.returncode == 0:
                print("✓ Octave script completed successfully")
                print("Octave output:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print(f"  {line}")
                return True
            else:
                print(f"✗ Octave script failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("✗ Octave script timed out")
            return False
        except Exception as e:
            print(f"✗ Error running Octave: {e}")
            return False
    
    def load_patterns(self) -> bool:
        """Load generated CSV patterns into memory"""
        print("=== Loading Generated Temperature Patterns ===")
        
        if not self.patterns_dir.exists():
            print(f"ERROR: Patterns directory not found: {self.patterns_dir}")
            return False
        
        csv_files = list(self.patterns_dir.glob("*.csv"))
        if not csv_files:
            print(f"ERROR: No CSV files found in {self.patterns_dir}")
            return False
        
        self.patterns.clear()
        
        for csv_file in csv_files:
            pattern_name = csv_file.stem
            try:
                pattern_data = []
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f, skipinitialspace=True)
                    for row in reader:
                        if 'time_ms' in row and 'temp_mC' in row:
                            time_ms = int(row['time_ms'])
                            temp_mC = int(row['temp_mC'])
                            pattern_data.append((time_ms, temp_mC))
                
                if pattern_data:
                    self.patterns[pattern_name] = pattern_data
                    print(f"✓ Loaded pattern '{pattern_name}': "
                          f"{len(pattern_data)} samples")
                else:
                    print(f"✗ No valid data in {csv_file}")
                    
            except Exception as e:
                print(f"✗ Error loading {csv_file}: {e}")
        
        if self.patterns:
            print(f"✓ Successfully loaded {len(self.patterns)} "
                  f"temperature patterns")
            return True
        else:
            print("✗ No patterns loaded")
            return False
    
    def list_patterns(self) -> List[str]:
        """List available temperature patterns"""
        return list(self.patterns.keys())
    
    def get_pattern_info(self, pattern_name: str) -> Optional[Dict]:
        """Get information about a specific pattern"""
        if pattern_name not in self.patterns:
            return None
        
        data = self.patterns[pattern_name]
        if not data:
            return None
        
        temps_mC = [temp for _, temp in data]
        times_ms = [time for time, _ in data]
        
        return {
            'name': pattern_name,
            'samples': len(data),
            'duration_ms': max(times_ms) - min(times_ms),
            'temp_range_mC': (min(temps_mC), max(temps_mC)),
            'temp_range_C': (min(temps_mC)/1000.0, max(temps_mC)/1000.0),
            'sampling_period_ms': (times_ms[1] - times_ms[0]
                                   if len(times_ms) > 1 else 0)
        }
    
    def export_kernel_data(self, pattern_name: str, output_file: str) -> bool:
        """Export pattern data for kernel module consumption"""
        if pattern_name not in self.patterns:
            print(f"ERROR: Pattern '{pattern_name}' not found")
            return False
        
        data = self.patterns[pattern_name]
        
        try:
            with open(output_file, 'w') as f:
                # Write C-style array initialization
                f.write(f"/* Generated temperature pattern: "
                        f"{pattern_name} */\n")
                f.write(f"/* Samples: {len(data)} */\n\n")
                f.write("static const struct {\n")
                f.write("    unsigned int time_ms;\n")
                f.write("    int temp_mC;\n")
                f.write(f"}} temp_pattern_{pattern_name}[] = {{\n")
                
                for i, (time_ms, temp_mC) in enumerate(data):
                    f.write(f"    {{{time_ms:6d}, {temp_mC:6d}}}")
                    if i < len(data) - 1:
                        f.write(",")
                    f.write(f"  /* {temp_mC/1000.0:.1f}°C */\n")
                
                f.write("};\n\n")
                f.write(f"#define TEMP_PATTERN_{pattern_name.upper()}_SIZE "
                        f"{len(data)}\n")
            
            print(f"✓ Exported kernel data to {output_file}")
            return True
            
        except Exception as e:
            print(f"✗ Error exporting kernel data: {e}")
            return False


class KernelTemperatureController:
    """Control temperature simulation in the kernel driver"""
    
    def __init__(self):
        self.sysfs_paths = self._find_simtemp_devices()
    
    def _find_simtemp_devices(self) -> List[str]:
        """Find all simtemp sysfs devices"""
        devices = []
        for i in range(4):  # Driver supports up to 4 devices
            paths = [
                f"/sys/devices/platform/nxp-simtemp.{i}.auto",
                f"/sys/devices/platform/nxp-simtemp.{i}"
            ]
            for path in paths:
                if os.path.exists(path):
                    devices.append(path)
                    break
        return devices
    
    def set_sampling_period(self, period_ms: int) -> bool:
        """Set sampling period for all devices"""
        success = True
        for device_path in self.sysfs_paths:
            sampling_file = os.path.join(device_path, "sampling_ms")
            try:
                with open(sampling_file, 'w') as f:
                    f.write(str(period_ms))
                print(f"✓ Set sampling period to {period_ms}ms for "
                      f"{device_path}")
            except Exception as e:
                print(f"✗ Failed to set sampling period for "
                      f"{device_path}: {e}")
                success = False
        return success
    
    def get_device_status(self) -> List[Dict]:
        """Get status of all simtemp devices"""
        devices_status = []
        for device_path in self.sysfs_paths:
            try:
                stats_file = os.path.join(device_path, "stats")
                if os.path.exists(stats_file):
                    with open(stats_file, 'r') as f:
                        stats_content = f.read()
                    
                    status = {'path': device_path, 'stats': {}}
                    for line in stats_content.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            status['stats'][key.strip()] = value.strip()
                    
                    devices_status.append(status)
            except Exception as e:
                print(f"Warning: Could not read stats for {device_path}: {e}")
        
        return devices_status


def main():
    parser = argparse.ArgumentParser(
        description="Temperature Pattern Generator for SimTemp Driver")
    parser.add_argument("--pattern",
                        help="Generate specific pattern "
                             "(or 'all' for all patterns)")
    parser.add_argument("--octave-path", default="octave",
                        help="Path to GNU Octave executable")
    parser.add_argument("--list", action="store_true",
                        help="List available patterns")
    parser.add_argument("--info",
                        help="Show information about a specific pattern")
    parser.add_argument("--export-kernel",
                        help="Export pattern for kernel "
                             "(pattern_name:output_file)")
    parser.add_argument("--set-sampling", type=int,
                        help="Set sampling period in ms")
    parser.add_argument("--status", action="store_true",
                        help="Show kernel device status")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = TemperaturePatternGenerator(args.octave_path)
    controller = KernelTemperatureController()
    
    # Handle kernel control commands
    if args.status:
        print("=== SimTemp Kernel Device Status ===")
        devices = controller.get_device_status()
        if devices:
            for device in devices:
                print(f"\nDevice: {device['path']}")
                for key, value in device['stats'].items():
                    print(f"  {key}: {value}")
        else:
            print("No simtemp devices found")
        return
    
    if args.set_sampling:
        print(f"Setting sampling period to {args.set_sampling}ms...")
        controller.set_sampling_period(args.set_sampling)
        return
    
    # Generate patterns if needed
    if args.pattern or not generator.patterns_dir.exists():
        if not generator.generate_patterns():
            print("ERROR: Failed to generate temperature patterns")
            sys.exit(1)
    
    # Load patterns
    if not generator.load_patterns():
        print("ERROR: Failed to load temperature patterns")
        sys.exit(1)
    
    # Handle commands
    if args.list:
        print("=== Available Temperature Patterns ===")
        for pattern in generator.list_patterns():
            info = generator.get_pattern_info(pattern)
            if info:
                print(f"  {pattern}:")
                print(f"    Samples: {info['samples']}")
                print(f"    Duration: {info['duration_ms']/1000:.1f}s")
                temp_min, temp_max = info['temp_range_C']
                print(f"    Temperature: {temp_min:.1f}°C to "
                      f"{temp_max:.1f}°C")
                print(f"    Sampling: {info['sampling_period_ms']}ms")
    
    elif args.info:
        info = generator.get_pattern_info(args.info)
        if info:
            print(f"=== Pattern Information: {args.info} ===")
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print(f"Pattern '{args.info}' not found")
    
    elif args.export_kernel:
        if ':' in args.export_kernel:
            pattern_name, output_file = args.export_kernel.split(':', 1)
            generator.export_kernel_data(pattern_name, output_file)
        else:
            print("ERROR: Use format --export-kernel pattern_name:output_file")
    
    else:
        print("=== Temperature Pattern Generator Ready ===")
        print(f"Generated {len(generator.patterns)} patterns")
        print("Use --list to see available patterns")
        print("Use --export-kernel pattern:file to export for kernel")
        print("Use --status to check kernel device status")


if __name__ == "__main__":
    main()