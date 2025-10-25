#!/usr/bin/env python3
"""
SimTemp Wave Configuration Presets
Copyright (c) 2025 Jorge Rodriguez Moreno

Predefined wave configurations for different testing scenarios
"""

import json
from typing import Dict, List

# Wave configuration presets
WAVE_PRESETS = {
    "thermal_cycling": {
        "description": "Thermal cycling test - rapid temperature changes",
        "wave_type": "square",
        "frequency": 0.5,  # 2-second periods
        "amplitude": 25.0,  # ±25°C
        "offset": 50.0,     # 25°C to 75°C
        "sampling_ms": 100,
        "duration": 300,    # 5 minutes
        "use_case": "Thermal stress testing of components"
    },
    
    "environmental_sim": {
        "description": "Environmental temperature simulation",
        "wave_type": "sine", 
        "frequency": 0.0028,  # 6-minute period (360s)
        "amplitude": 12.0,    # ±12°C
        "offset": 28.0,       # 16°C to 40°C
        "sampling_ms": 1000,  # 1-second sampling
        "duration": 1800,     # 30 minutes
        "use_case": "Simulating daily temperature variations"
    },
    
    "hvac_response": {
        "description": "HVAC system response simulation",
        "wave_type": "step",
        "frequency": 0.05,    # 20-second steps
        "amplitude": 8.0,     # ±8°C steps
        "offset": 24.0,       # 16°C to 32°C
        "sampling_ms": 500,   # 0.5-second sampling
        "duration": 600,      # 10 minutes
        "use_case": "Testing temperature control system response"
    },
    
    "sensor_noise": {
        "description": "Sensor noise simulation",
        "wave_type": "noise",
        "frequency": 1.0,     # Not used for noise
        "amplitude": 0.5,     # ±0.5°C noise
        "offset": 25.0,       # Around room temperature
        "sampling_ms": 50,    # Fast sampling
        "duration": 120,      # 2 minutes
        "use_case": "Testing noise filtering algorithms"
    },
    
    "heating_ramp": {
        "description": "Gradual heating simulation",
        "wave_type": "ramp",
        "frequency": 0.0083,  # 2-minute ramp period
        "amplitude": 30.0,    # 30°C ramp
        "offset": 40.0,       # 10°C to 70°C
        "sampling_ms": 200,   # 200ms sampling
        "duration": 480,      # 8 minutes
        "use_case": "Simulating gradual heating processes"
    },
    
    "oscillation_test": {
        "description": "High-frequency temperature oscillation",
        "wave_type": "sine",
        "frequency": 1.0,     # 1 Hz
        "amplitude": 5.0,     # ±5°C
        "offset": 35.0,       # 30°C to 40°C
        "sampling_ms": 100,   # Fast sampling needed
        "duration": 60,       # 1 minute
        "use_case": "Testing sensor response to rapid changes"
    },
    
    "sawtooth_sweep": {
        "description": "Linear temperature sweep",
        "wave_type": "sawtooth",
        "frequency": 0.0167,  # 1-minute sweeps
        "amplitude": 20.0,    # ±20°C
        "offset": 45.0,       # 25°C to 65°C
        "sampling_ms": 250,   # 250ms sampling
        "duration": 360,      # 6 minutes
        "use_case": "Linear temperature characterization"
    },
    
    "triangle_test": {
        "description": "Symmetric temperature ramping",
        "wave_type": "triangle",
        "frequency": 0.033,   # 30-second periods
        "amplitude": 15.0,    # ±15°C
        "offset": 30.0,       # 15°C to 45°C
        "sampling_ms": 150,   # 150ms sampling
        "duration": 240,      # 4 minutes
        "use_case": "Symmetric heating/cooling cycles"
    }
}

# Octave pattern integration presets
OCTAVE_PRESETS = {
    "realistic_env": {
        "description": "Realistic environmental pattern from Octave",
        "pattern_name": "realistic",
        "duration": 300,
        "use_case": "Real-world temperature simulation"
    },
    
    "linear_heating": {
        "description": "Linear heating ramp from Octave",
        "pattern_name": "linear_ramp", 
        "duration": 240,
        "use_case": "Controlled heating simulation"
    },
    
    "exponential_thermal": {
        "description": "Exponential thermal response from Octave",
        "pattern_name": "exponential_ramp",
        "duration": 300,
        "use_case": "Thermal mass heating simulation"
    },
    
    "noisy_environment": {
        "description": "Noisy temperature environment from Octave",
        "pattern_name": "noisy_ramp",
        "duration": 600,
        "use_case": "Realistic noisy environment testing"
    },
    
    "sinusoidal_daily": {
        "description": "Daily temperature cycle from Octave",
        "pattern_name": "sinusoidal",
        "duration": 480,
        "use_case": "Daily temperature variation simulation"
    },
    
    "step_changes": {
        "description": "Step response pattern from Octave",
        "pattern_name": "step_response",
        "duration": 180,
        "use_case": "Step response characterization"
    }
}

def get_wave_preset(preset_name: str) -> Dict:
    """Get a wave configuration preset"""
    return WAVE_PRESETS.get(preset_name, {})

def get_octave_preset(preset_name: str) -> Dict:
    """Get an Octave pattern preset"""
    return OCTAVE_PRESETS.get(preset_name, {})

def list_wave_presets() -> List[str]:
    """List available wave presets"""
    return list(WAVE_PRESETS.keys())

def list_octave_presets() -> List[str]:
    """List available Octave presets"""
    return list(OCTAVE_PRESETS.keys())

def print_preset_info(preset_type: str = "all"):
    """Print detailed information about presets"""
    
    if preset_type in ["all", "wave"]:
        print("=== Wave Configuration Presets ===")
        for name, config in WAVE_PRESETS.items():
            print(f"\n{name}:")
            print(f"  Description: {config['description']}")
            print(f"  Wave Type: {config['wave_type']}")
            print(f"  Frequency: {config['frequency']} Hz")
            print(f"  Temperature: {config['offset'] - config['amplitude']:.1f}°C to "
                  f"{config['offset'] + config['amplitude']:.1f}°C")
            print(f"  Duration: {config['duration']}s")
            print(f"  Use Case: {config['use_case']}")
    
    if preset_type in ["all", "octave"]:
        print("\n=== Octave Pattern Presets ===")
        for name, config in OCTAVE_PRESETS.items():
            print(f"\n{name}:")
            print(f"  Description: {config['description']}")
            print(f"  Pattern: {config['pattern_name']}")
            print(f"  Duration: {config['duration']}s")
            print(f"  Use Case: {config['use_case']}")

def save_preset_to_file(preset_name: str, filename: str) -> bool:
    """Save a preset configuration to a JSON file"""
    try:
        preset = get_wave_preset(preset_name)
        if not preset:
            preset = get_octave_preset(preset_name)
        
        if not preset:
            print(f"ERROR: Preset '{preset_name}' not found")
            return False
        
        with open(filename, 'w') as f:
            json.dump(preset, f, indent=2)
        
        print(f"✓ Saved preset '{preset_name}' to {filename}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to save preset: {e}")
        return False

def load_preset_from_file(filename: str) -> Dict:
    """Load a preset configuration from a JSON file"""
    try:
        with open(filename, 'r') as f:
            preset = json.load(f)
        
        print(f"✓ Loaded preset from {filename}")
        return preset
        
    except Exception as e:
        print(f"ERROR: Failed to load preset: {e}")
        return {}

def generate_preset_commands():
    """Generate shell commands for all presets"""
    print("=== Generated Commands for Wave Presets ===\n")
    
    for name, config in WAVE_PRESETS.items():
        cmd = (f"python3 continuous_wave_generator.py "
               f"--wave {config['wave_type']} "
               f"--frequency {config['frequency']} "
               f"--amplitude {config['amplitude']} "
               f"--offset {config['offset']} "
               f"--sampling {config['sampling_ms']} "
               f"--duration {config['duration']}")
        
        print(f"# {config['description']}")
        print(f"{cmd}")
        print()
    
    print("=== Generated Commands for Octave Presets ===\n")
    
    for name, config in OCTAVE_PRESETS.items():
        cmd = (f"python3 continuous_wave_generator.py "
               f"--pattern {config['pattern_name']} "
               f"--duration {config['duration']}")
        
        print(f"# {config['description']}")
        print(f"{cmd}")
        print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SimTemp Wave Configuration Presets")
    parser.add_argument("--list", choices=["all", "wave", "octave"], 
                       default="all", help="List available presets")
    parser.add_argument("--info", choices=["all", "wave", "octave"],
                       default="all", help="Show detailed preset information")
    parser.add_argument("--save", nargs=2, metavar=("PRESET", "FILE"),
                       help="Save preset to file")
    parser.add_argument("--load", metavar="FILE",
                       help="Load preset from file")
    parser.add_argument("--commands", action="store_true",
                       help="Generate shell commands for all presets")
    
    args = parser.parse_args()
    
    if args.commands:
        generate_preset_commands()
    elif args.save:
        save_preset_to_file(args.save[0], args.save[1])
    elif args.load:
        preset = load_preset_from_file(args.load)
        if preset:
            print("Loaded preset configuration:")
            for key, value in preset.items():
                print(f"  {key}: {value}")
    elif args.list:
        if args.list in ["all", "wave"]:
            print("Wave Presets:", ", ".join(list_wave_presets()))
        if args.list in ["all", "octave"]:
            print("Octave Presets:", ", ".join(list_octave_presets()))
    else:
        print_preset_info(args.info)