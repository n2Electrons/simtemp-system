#!/bin/bash
# SimTemp Continuous Wave Generator Demo Script
# Demonstrates integration with octv_temp_generator

set -e

WAVE_GENERATOR="./continuous_wave_generator.py"
OCTAVE_DIR="./models/octv_temp_generator"

echo "=================================================="
echo "SimTemp Continuous Wave Generator Demo"
echo "=================================================="

# Check dependencies
echo "1. Checking dependencies..."

if ! python3 -c "import numpy" 2>/dev/null; then
    echo "Installing NumPy..."
    pip3 install numpy --user
fi

if ! command -v octave &> /dev/null; then
    echo "WARNING: Octave not found. Install with:"
    echo "  sudo apt install octave"
fi

echo "✓ Dependencies checked"

# List available waves
echo
echo "2. Available waveform types:"
python3 $WAVE_GENERATOR --list-waves

# Generate Octave patterns if available
echo
echo "3. Generating Octave temperature patterns..."
if command -v octave &> /dev/null; then
    cd $OCTAVE_DIR 2>/dev/null || echo "Octave directory not found at expected location"
    python3 temperature_generator.py --pattern all || echo "Pattern generation skipped"
    cd - >/dev/null
    
    echo
    echo "4. Available Octave patterns:"
    python3 $WAVE_GENERATOR --list-patterns
else
    echo "Octave not available - skipping pattern generation"
fi

# Demo configurations
echo
echo "5. Demo configurations:"
echo

echo "=== Sine Wave Configuration ==="
echo "Command: python3 $WAVE_GENERATOR --wave sine --frequency 0.05 --amplitude 15 --offset 40 --duration 30"
echo "Description: 20-second period sine wave, 25°C to 55°C range"
echo

echo "=== Square Wave Configuration ==="
echo "Command: python3 $WAVE_GENERATOR --wave square --frequency 0.1 --amplitude 10 --offset 35 --duration 30"
echo "Description: 10-second period square wave, 25°C to 45°C range"
echo

echo "=== Triangle Wave Configuration ==="
echo "Command: python3 $WAVE_GENERATOR --wave triangle --frequency 0.2 --amplitude 8 --offset 42 --duration 30"
echo "Description: 5-second period triangle wave, 34°C to 50°C range"
echo

echo "=== Noise Configuration ==="
echo "Command: python3 $WAVE_GENERATOR --wave noise --amplitude 3 --offset 37 --duration 30"
echo "Description: Random noise around 37°C ±3°C"
echo

echo "=== Octave Pattern Configuration ==="
echo "Command: python3 $WAVE_GENERATOR --pattern realistic --duration 60"
echo "Description: Realistic environmental pattern from Octave"
echo

# Interactive demo selection
echo
echo "6. Interactive Demo"
echo "=================="

if [ "$1" = "--auto" ]; then
    echo "Running automatic demo with sine wave..."
    python3 $WAVE_GENERATOR --wave sine --frequency 0.1 --amplitude 10 --offset 35 --duration 10
else
    echo "Select a demo to run:"
    echo "1) Sine wave (10 seconds)"
    echo "2) Square wave (10 seconds)" 
    echo "3) Triangle wave (10 seconds)"
    echo "4) Noise (10 seconds)"
    echo "5) Octave realistic pattern (if available)"
    echo "6) Show device status only"
    echo "0) Exit"
    
    read -p "Enter choice [0-6]: " choice
    
    case $choice in
        1)
            echo "Running sine wave demo..."
            python3 $WAVE_GENERATOR --wave sine --frequency 0.1 --amplitude 10 --offset 35 --duration 10
            ;;
        2)
            echo "Running square wave demo..."
            python3 $WAVE_GENERATOR --wave square --frequency 0.1 --amplitude 10 --offset 35 --duration 10
            ;;
        3)
            echo "Running triangle wave demo..."
            python3 $WAVE_GENERATOR --wave triangle --frequency 0.1 --amplitude 10 --offset 35 --duration 10
            ;;
        4)
            echo "Running noise demo..."
            python3 $WAVE_GENERATOR --wave noise --amplitude 3 --offset 37 --duration 10
            ;;
        5)
            echo "Running Octave pattern demo..."
            python3 $WAVE_GENERATOR --pattern realistic --duration 20 || echo "Pattern not available"
            ;;
        6)
            echo "Device status:"
            python3 $WAVE_GENERATOR --status
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac
fi

echo
echo "=================================================="
echo "Demo completed!"
echo ""
echo "To run manual configurations:"
echo "  python3 $WAVE_GENERATOR --help"
echo ""
echo "Example custom wave:"
echo "  python3 $WAVE_GENERATOR --wave sine --frequency 0.05 --amplitude 20 --offset 50 --duration 60"
echo ""
echo "Example with monitoring:"
echo "  python3 $WAVE_GENERATOR --wave triangle --frequency 0.1 --amplitude 15 --offset 40 &"
echo "  sleep 2"
echo "  ./simtemp-cli --monitor --duration 30 --json"
echo "=================================================="