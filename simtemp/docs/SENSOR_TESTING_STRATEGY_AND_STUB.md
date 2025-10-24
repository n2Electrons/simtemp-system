# Sensor Testing Strategy and Stub Module Documentation

## Overview

The NXP SimTemp driver system is designed to support **multiple temperature sensors** through a dual-module architecture. This document explains the testing strategy, device configuration, and how the stub module enables comprehensive validation of the driver framework.

## Multi-Sensor Architecture

### Device 0 (Main Driver)
```
Location: /sys/devices/platform/nxp-simtemp.0
Device File: /dev/simtemp0
Configuration:
- sampling_ms=1000 (samples every 1 second)
- threshold_mC=50000 (alert at 50°C)
- mode=default (default operating mode)
```

### Device 1 (Stub/Lab Sensor)
```
Location: /sys/devices/platform/nxp-simtemp.1.auto
Device File: /dev/simtemp1
Configuration:
- sampling_ms=200 (samples every 200ms - higher frequency)
- threshold_mC=60000 (alert at 60°C)
- mode=lab (laboratory testing mode)
```

## Module Architecture

### Core Modules

1. **nxp_simtemp.ko** - Main driver module
   - Registers the platform driver framework
   - Provides core temperature monitoring functionality
   - Creates Device 0 with default configuration
   - Implements F-K5 alert logic for threshold monitoring

2. **nxp_simtemp_stub.ko** - Test/development module
   - Creates additional test devices via Device Tree simulation
   - Provides Device 1 with custom laboratory configuration
   - Enables comprehensive testing without physical hardware
   - Configured for high-frequency sampling and lab scenarios

### Module Dependencies

```bash
# Loading order (handled automatically by load_simtemp_modules())
1. insmod nxp_simtemp.ko      # Main driver first
2. insmod nxp_simtemp_stub.ko # Stub creates additional devices
```

## Testing Strategy

### Why Multiple Sensors?

The dual-sensor approach enables:

1. **Default vs Custom Configuration Testing**
   - Device 0: Tests conservative production settings
   - Device 1: Tests aggressive laboratory settings

2. **Different Operating Modes**
   - Device 0: "default" mode for production validation
   - Device 1: "lab" mode for development and testing

3. **Threshold Validation**
   - Device 0: Lower threshold (50°C) for safety testing
   - Device 1: Higher threshold (60°C) for stress testing

4. **Sampling Rate Validation**
   - Device 0: Standard rate (1000ms) for normal operation
   - Device 1: High frequency (200ms) for real-time testing

### Test Validation Matrix

| Aspect | Device 0 (Main) | Device 1 (Stub) | Purpose |
|--------|-----------------|------------------|---------|
| **Threshold** | 50°C | 60°C | Different alert levels |
| **Sampling** | 1000ms | 200ms | Performance testing |
| **Mode** | default | lab | Operating mode validation |
| **Configuration** | Hardcoded | Device Tree | Config flexibility |

## Device Tree Configuration

The stub module simulates Device Tree properties:

```c
// Simulated Device Tree properties for Device 1
.threshold_mC = 60000,    // 60°C in milli-Celsius
.sampling_ms = 200,       // 200ms sampling rate
.mode = "lab"             // Laboratory mode
```

## Real-World Use Cases

This architecture supports typical embedded scenarios:

### Production Systems
- **CPU Temperature Sensor**: Device 0 with conservative settings
- **GPU Temperature Sensor**: Device 1 with custom thresholds
- **Power Management Sensor**: Additional devices with specific configs
- **Safety Critical Sensors**: Lower thresholds for immediate alerts

### Development Environment
- **Stress Testing**: High-frequency sampling on Device 1
- **Threshold Calibration**: Different alert levels for validation
- **Mode Testing**: Different operational modes (default, lab, production)
- **Performance Benchmarking**: Multiple sensors with varying loads

## Testing Implementation

### Comprehensive Validation Tests

The test suite (`test_x86_f_k8_tc_004_validation.py`) validates:

1. **Device Creation**: Both sensors appear in sysfs
2. **Configuration Validation**: Correct values for each device
3. **Independent Operation**: Each sensor operates with its settings
4. **Alert Functionality**: F-K5 threshold alerts work per device
5. **Module Dependencies**: Proper loading and unloading sequence

### Key Test Assertions

```python
# Device 0 (Main) - Conservative settings
assert sampling_ms_0 == "1000"
assert threshold_mC_0 == "50000"
assert mode_0 == "default"

# Device 1 (Stub) - Laboratory settings
assert sampling_ms_1 == "200"
assert threshold_mC_1 == "60000"
assert mode_1 == "lab"
```

## Development Benefits

### Stub Module Advantages

1. **No Physical Hardware Required**: Test without actual temperature sensors
2. **Predictable Behavior**: Known configurations for repeatable tests
3. **Multiple Scenarios**: Different operating modes and thresholds
4. **CI/CD Compatibility**: Automated testing in virtual environments
5. **Development Flexibility**: Easy modification of test parameters

### Testing Coverage

- ✅ Multi-sensor registration
- ✅ Independent device configuration
- ✅ sysfs attribute validation
- ✅ Device Tree property simulation
- ✅ Driver bind/unbind operations
- ✅ Module dependency management
- ✅ F-K5 alert functionality per device
- ✅ Different sampling rates and thresholds

## Expanding the System

### Adding More Sensors

To add additional sensors:

1. **Modify Stub Module**: Add more device registrations
2. **Update Device Tree**: Configure additional properties
3. **Extend Tests**: Validate new sensor configurations
4. **Document Parameters**: Update threshold and sampling specifications

### Custom Configurations

Each sensor can have unique:
- Temperature thresholds
- Sampling frequencies
- Operating modes
- Alert behaviors
- Device Tree properties

## Conclusion

The dual-module architecture provides a robust foundation for:
- Multi-sensor temperature monitoring systems
- Comprehensive driver validation
- Development and testing flexibility
- Production deployment readiness

This strategy ensures that the NXP SimTemp driver can handle complex multi-sensor scenarios while maintaining individual device independence and configuration flexibility.