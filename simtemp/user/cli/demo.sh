#!/bin/bash
# SimTemp CLI Demo Script
# Demonstrates various CLI functionality

set -e

CLI_BINARY="./bin/simtemp-cli"
CONFIG_FILE="./simtemp-cli.conf.example"

echo "=================================================="
echo "SimTemp CLI Demonstration Script"
echo "=================================================="

# Check if binary exists
if [ ! -f "$CLI_BINARY" ]; then
    echo "Error: CLI binary not found. Please run 'make' first."
    exit 1
fi

echo
echo "1. Showing version information..."
$CLI_BINARY --version

echo
echo "2. Showing help..."
$CLI_BINARY --help | head -20
echo "... (help continues)"

echo
echo "3. Showing current sensor status (local)..."
$CLI_BINARY --status || echo "Note: Sensor may not be available on this system"

echo
echo "4. Example: Configure sensor with custom parameters..."
echo "Command: $CLI_BINARY --config --sampling 500 --threshold 40000 --mode normal"
echo "(This would configure sampling to 500ms, threshold to 40°C, mode to normal)"

echo
echo "5. Example: Monitor temperature for 10 seconds with JSON output..."
echo "Command: $CLI_BINARY --monitor --duration 10 --json"
echo "(This would monitor and output JSON format)"

echo
echo "6. Example: Remote monitoring via SSH..."
echo "Command: $CLI_BINARY -h 192.168.1.100 -u root --monitor --duration 30"
echo "(This would connect to remote host and monitor for 30 seconds)"

echo
echo "7. Example: Run test mode..."
echo "Command: $CLI_BINARY --test"
echo "(This would run automated threshold testing)"

echo
echo "8. Example: Configuration file usage..."
if [ -f "$CONFIG_FILE" ]; then
    echo "Using configuration file: $CONFIG_FILE"
    echo "Command: $CLI_BINARY --config-file $CONFIG_FILE --status"
    echo "(This would load settings from config file)"
else
    echo "Configuration file not found: $CONFIG_FILE"
fi

echo
echo "9. Example: CSV output for data logging..."
echo "Command: $CLI_BINARY --monitor --csv --count 100 > temperature_log.csv"
echo "(This would log 100 samples to CSV file)"

echo
echo "10. Example: Remote configuration..."
echo "Command: $CLI_BINARY -h target.local -u admin -k ~/.ssh/id_rsa --config --sampling 200"
echo "(This would configure remote sensor sampling period)"

echo
echo "=================================================="
echo "Demo completed successfully!"
echo ""
echo "To build and test the CLI:"
echo "  make                    # Build the binary"
echo "  make debug              # Build with debug symbols"
echo "  make test               # Run basic tests"
echo "  make install            # Install to system (requires root)"
echo ""
echo "For more information, see README.md"
echo "=================================================="