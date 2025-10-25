#!/bin/bash
# Demo: SimTemp Configuration via QEMU Socket
# 
# This script demonstrates how to configure the SimTemp sensor 
# running in QEMU via socket port 4445

set -e

echo "=== Demo: SimTemp Sensor Configuration via QEMU Socket ==="
echo

# Sensor configuration
SENSOR_HOST="127.0.0.1"
SENSOR_PORT="4445"
CLIENT_SCRIPT="./simtemp_config_client.py"

echo "Connecting to SimTemp sensor at $SENSOR_HOST:$SENSOR_PORT..."
echo

# Verify client script exists
if [ ! -f "$CLIENT_SCRIPT" ]; then
    echo "ERROR: Client not found: $CLIENT_SCRIPT"
    echo "Run from: simtemp/user/cli/"
    exit 1
fi

echo "1. Getting current configuration..."
python3 "$CLIENT_SCRIPT" --host "$SENSOR_HOST" --port "$SENSOR_PORT" --get-config
echo

echo "2. Setting sampling period to 150ms..."
python3 "$CLIENT_SCRIPT" --host "$SENSOR_HOST" --port "$SENSOR_PORT" --set-sampling 150
echo

echo "3. Setting temperature threshold to 40°C (40000 mC)..."
python3 "$CLIENT_SCRIPT" --host "$SENSOR_HOST" --port "$SENSOR_PORT" --set-threshold 40000
echo

echo "4. Setting test temperature to 35.5°C..."
python3 "$CLIENT_SCRIPT" --host "$SENSOR_HOST" --port "$SENSOR_PORT" --set-temp 35.5
echo

echo "5. Verifying final configuration..."
python3 "$CLIENT_SCRIPT" --host "$SENSOR_HOST" --port "$SENSOR_PORT" --get-config
echo

echo "6. Getting available command help..."
python3 "$CLIENT_SCRIPT" --host "$SENSOR_HOST" --port "$SENSOR_PORT" --help-commands
echo

echo "=== Demo completed ==="
echo
echo "Example commands for manual usage:"
echo "  # Get configuration:"
echo "  python3 $CLIENT_SCRIPT --host $SENSOR_HOST --port $SENSOR_PORT --get-config"
echo
echo "  # Configure sampling:"
echo "  python3 $CLIENT_SCRIPT --host $SENSOR_HOST --port $SENSOR_PORT --set-sampling 200"
echo
echo "  # Configure threshold:"
echo "  python3 $CLIENT_SCRIPT --host $SENSOR_HOST --port $SENSOR_PORT --set-threshold 45000"
echo
echo "  # Generate sine wave:"
echo "  python3 continuous_wave_generator.py --host $SENSOR_HOST --port $SENSOR_PORT \\"
echo "          --wave sine --frequency 0.1 --amplitude 8.0 --offset 30.0 --duration 60"