# SimTemp CLI C Implementation

This directory contains a pure C implementation of the SimTemp CLI tool for configuring and monitoring the NXP SimTemp temperature sensor driver.

## Features

- **Local Operation**: Direct access to `/dev/simtemp` device and sysfs configuration
- **Remote Operation**: SSH/Telnet support for remote sensor management
- **Real-time Monitoring**: Live temperature display with threshold alerts
- **Configuration Management**: Set sampling period, thresholds, and sensor modes
- **Multiple Output Formats**: Standard, JSON, CSV, and raw binary output
- **Test Mode**: Automated testing of sensor alert functionality
- **Configuration Files**: Persistent settings via configuration files

## Building

```bash
# Build the CLI tool
make

# Build with debug symbols
make debug

# Clean build artifacts
make clean

# Install to system (requires root)
make install
```

## Usage Examples

### Local Operations

```bash
# Show sensor status
./simtemp-cli --status

# Configure sensor locally
./simtemp-cli --config --sampling 500 --threshold 45000 --mode normal

# Monitor temperature for 30 seconds
./simtemp-cli --monitor --duration 30

# Monitor with JSON output
./simtemp-cli --monitor --json --count 100

# Run test mode
./simtemp-cli --test
```

### Remote Operations (SSH)

```bash
# Configure remote sensor
./simtemp-cli -h 192.168.1.100 -u root --config --sampling 1000 --threshold 50000

# Monitor remote temperature
./simtemp-cli -h target.local -u admin -k ~/.ssh/id_rsa --monitor --duration 60

# Show remote status
./simtemp-cli -h 192.168.1.100 -u root --status

# Remote test mode
./simtemp-cli -h target.local -u admin --test
```

### Configuration Files

```bash
# Load configuration from file
./simtemp-cli --config-file /etc/simtemp-cli.conf --monitor

# Create sample configuration file
./simtemp-cli --status > /dev/null
# Edit the generated config as needed
```

## Command Line Options

### Connection Options
- `-h, --host HOST`: Remote host (enables SSH mode)
- `-p, --port PORT`: SSH port (default: 22)
- `-u, --user USER`: SSH username
- `-k, --keyfile FILE`: SSH private key file
- `-t, --telnet`: Use telnet instead of SSH

### Device Options
- `-d, --device PATH`: Device path (default: /dev/simtemp)
- `-s, --sysfs PATH`: Sysfs base path (default: /sys/class/misc/simtemp)

### Configuration Commands
- `--config`: Configure sensor parameters
- `--sampling MS`: Set sampling period in milliseconds
- `--threshold TEMP`: Set threshold in milli-degrees Celsius
- `--mode MODE`: Set sensor mode (normal, noisy, ramp)
- `--status`: Show current sensor status

### Monitoring Commands
- `--monitor`: Monitor temperature in real-time
- `--duration SECONDS`: Monitor for specified duration
- `--count SAMPLES`: Read specified number of samples
- `--timeout MS`: Poll timeout in milliseconds

### Output Options
- `--json`: Output in JSON format
- `--csv`: Output in CSV format
- `--raw`: Output raw binary data
- `-v, --verbose`: Enable verbose output

### Other Options
- `--test`: Run test mode
- `--config-file FILE`: Load configuration from file
- `--help`: Show help message
- `--version`: Show version information

## Configuration File Format

Configuration files use a simple key=value format:

```ini
# SimTemp CLI Configuration File

# Connection settings
connection_type = ssh
remote_host = 192.168.1.100
remote_port = 22
username = root
keyfile = /home/user/.ssh/id_rsa

# Device paths
device_path = /dev/simtemp
sysfs_base = /sys/class/misc/simtemp

# Sensor configuration
sampling_ms = 1000
threshold_mc = 45000
mode = normal

# Operation settings
poll_timeout_ms = 5000
verbose = true
json_output = false
csv_output = false
```

## Output Formats

### Standard Format
```
2025-10-24T15:30:45.123Z temp=44.1C alert=0
2025-10-24T15:30:46.123Z temp=45.2C alert=1
```

### JSON Format
```json
{
  "timestamp": "2025-10-24T15:30:45.123Z",
  "timestamp_ns": 1729783845123456789,
  "temperature_celsius": 44.123,
  "temperature_millicelsius": 44123,
  "flags": 3,
  "new_sample": true,
  "threshold_crossed": true
}
```

### CSV Format
```csv
timestamp_ns,temperature_celsius,temperature_millicelsius,flags,new_sample,threshold_crossed
1729783845123456789,44.123,44123,3,true,true
```

## Files

- `simtemp_cli.h`: Main header file with all data structures and function prototypes
- `main.c`: Main program entry point and argument parsing
- `device_ops.c`: Local device operations (open, read, poll)
- `sysfs_config.c`: Sysfs configuration interface
- `remote_ops.c`: Remote connection and command execution
- `test_mode.c`: Test mode implementation
- `config_file.c`: Configuration file parsing and saving
- `Makefile`: Build system configuration
- `README.md`: This documentation file

## Dependencies

- Standard C library (libc)
- POSIX system calls (poll, signal handling)
- SSH client (`ssh` command) for remote operations
- Optional: Telnet client for telnet operations

## Error Handling

The CLI tool provides comprehensive error handling:

- Network connection failures are reported with specific error messages
- Device access errors include errno descriptions
- Configuration validation prevents invalid parameter values
- Remote command failures are detected and reported
- Signal handling allows graceful shutdown with Ctrl+C

## Security Considerations

- SSH key-based authentication is recommended over password authentication
- Configuration files may contain sensitive information (SSH keys, passwords)
- Remote operations should use encrypted connections (SSH) when possible
- File permissions should be set appropriately for configuration files

## Performance

- Efficient polling mechanism minimizes CPU usage during monitoring
- Binary data structures match kernel driver format for optimal performance
- Remote operations are batched where possible to reduce network overhead
- Memory usage is minimal with fixed-size buffers and structures

## Troubleshooting

### Common Issues

1. **Device not found**: Ensure the SimTemp kernel module is loaded
2. **Permission denied**: Check device file permissions or run as root
3. **SSH connection failed**: Verify SSH configuration and key files
4. **No samples received**: Check if sensor is properly configured and active
5. **Remote commands fail**: Ensure remote system has required tools installed

### Debug Information

Use the `--verbose` flag to enable detailed debug output:

```bash
./simtemp-cli --verbose --monitor --duration 10
```

This will show:
- Connection establishment details
- Device operation status
- Configuration changes
- Sample processing information
- Error details and stack traces