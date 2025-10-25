# SimTemp CLI - Pure C Implementation

Pure C CLI for NXP SimTemp temperature sensor configuration and monitoring.

## Main Features

- **Real-time Monitoring**: Temperature in console with timestamps
- **Threshold Configuration**: Configurable min/max alerts
- **Remote Communication**: SSH/Telnet for remote operation
- **Output Formats**: Standard, JSON, CSV, binary
- **Wave Generation**: Python integration for continuous waves
- **Configurable Sampling**: Adjustable sampling periods

## Quick Usage

### Local Operation
```bash
# Compile
make

# Monitor temperature
./simtemp_cli

# With alert thresholds
./simtemp_cli --threshold-min 20.0 --threshold-max 40.0

# JSON output
./simtemp_cli --format json --output temp.json
```

### Remote Operation
```bash
# Remote SSH
./simtemp_cli --host 192.168.1.100 --user root

# Telnet
./simtemp_cli --host target.local --telnet --port 23
```

### Wave Generation
```bash
# Sine wave
python3 continuous_wave_generator.py --wave sine --frequency 0.1 --amplitude 10.0

# Via Telnet (MAIN SOLUTION)
python3 continuous_wave_generator.py --host 192.168.1.100 --port 23 --wave sine

# List wave types
python3 continuous_wave_generator.py --list-waves

# Use Octave pattern (if available)
python3 continuous_wave_generator.py --host sensor.local --port 23 --pattern thermal_test

# Interactive demo
./telnet_wave_demo.sh
```

## Main Options

### Connection
- `--host HOST`: Remote host (enables SSH)
- `--port PORT`: SSH/Telnet port (default: 22)
- `--user USER`: SSH username
- `--telnet`: Use Telnet instead of SSH

### Configuration
- `--device PATH`: Device path (default: /dev/simtemp)
- `--host HOST`: Telnet host for remote sensor (MAIN FEATURE)
- `--port PORT`: Telnet port (default: 23) (MAIN FEATURE)
- `--threshold-min TEMP`: Minimum threshold in °C
- `--threshold-max TEMP`: Maximum threshold in °C
- `--interval MS`: Sampling interval in ms (default: 1000)

### Monitoring
- `--samples COUNT`: Number of samples (0 = infinite)
- `--format FORMAT`: Format: std|json|csv|raw
- `--output FILE`: Output file
- `--status`: Show device status

## Output Formats

### Standard
```
2025-10-24 15:30:45.123 - Temperature: 25.3°C
2025-10-24 15:30:46.123 - Temperature: 25.4°C [ALERT]
```

### JSON
```json
{"timestamp": "2025-10-24T15:30:45.123Z", "temperature": 25.3, "unit": "celsius"}
```

### CSV
```csv
timestamp,temperature,unit
2025-10-24T15:30:45.123Z,25.3,celsius
```

## Continuous Wave Generation

### Available Wave Types
- **sine**: Smooth sinusoidal wave
- **square**: Step changes
- **triangle**: Triangular ramp
- **sawtooth**: Asymmetric ramp
- **noise**: Random variation
- **step**: Discrete levels
- **ramp**: Linear increment/decrement

### Port Configuration
- **Local**: `/dev/simtemp`, sysfs interface
- **Telnet**: Host + port for remote sensor (RECOMMENDED)
- **SSH**: Port 22 (configurable), key authentication

## File Structure

```
simtemp/user/cli/
├── simtemp_cli.h                    # Main header
├── main.c                           # Entry point
├── device_ops.c                     # Local operations
├── remote_ops.c                     # Remote SSH/Telnet operations
├── sysfs_config.c                   # Configuration via sysfs
├── continuous_wave_generator.py     # Python wave generation
├── wave_presets.py                  # Predefined configurations
├── Makefile                         # Build system
└── README.md                        # This documentation
```

## ⚡ Características Técnicas

- **Tasa de Muestreo**: Hasta 100Hz (10ms)
- **Tiempo de Respuesta**: < 50ms local, 50-200ms remoto
- **Uso de Memoria**: < 2MB CLI, < 10MB generador de ondas
- **Protocolos**: SSH (puerto 22), Telnet (puerto 23)
- **Dependencias**: libc, libssh2, Python 3.6+ (opcional)

## 🔧 Compilación e Instalación

```bash
# Compilar
make

# Debug
make debug

# Clean
make clean

# Install (requires root)
sudo make install
```

## Implementation Status

- [x] Pure C CLI fully functional
- [x] Remote SSH/Telnet communication
- [x] Real-time monitoring with timestamps
- [x] Alert threshold configuration
- [x] Multiple output formats
- [x] Continuous wave generation
- [x] Octave pattern integration
- [x] Direct sensor port control
- [x] Robust build system