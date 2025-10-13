# Temperature Simulator (simtemp) - Kernel Module

This project contains a Linux kernel module that simulates temperature sensors for i.MX8M Plus processors.

## Overview

The `nxp_simtemp` kernel module provides:
- Temperature simulation interface
- Device registration in `/dev/`
- Sysfs interface for temperature readings
- Support for multiple temperature zones

## Project Structure

```
simtemp/
├── docs/                    # Documentation
├── kernel/                  # Kernel module source
│   ├── nxp_simtemp.c       # Main module source
│   ├── Makefile            # Build configuration
│   ├── Kbuild              # Kernel build file
│   └── obj/                # Build artifacts (generated)
├── tests/                   # Test suite
│   ├── config/             # Test configuration
│   ├── results/            # Test results (generated)
│   ├── run_tests.sh        # Test runner script
│   └── test_kernel_driver.py  # Python test cases
├── scripts/                 # Utility scripts
│   └── test_jenkins_kernel_pipeline.py  # CI/CD simulation
├── pipeline_config.yml      # Jenkins pipeline configuration
└── README.md               # This file
```

## Requirements

### System Requirements

#### Required Packages
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y build-essential linux-headers-$(uname -r)

# Red Hat/CentOS/Fedora
sudo yum install -y gcc make kernel-devel kernel-headers
# or for newer versions:
sudo dnf install -y gcc make kernel-devel kernel-headers
```

#### Kernel Version Compatibility
- **Minimum**: Linux 5.4+
- **Tested**: Linux 6.14.x
- **Recommended**: Latest stable kernel with headers

#### Build Tools
- **GCC**: Version 7+ (recommended: same version used to build running kernel)
- **Make**: GNU Make 4.0+
- **Kernel Build System**: kbuild support

### Development Requirements

#### Python Environment (for testing)
```bash
# Python 3.8+ required
python3 --version

# Virtual environment (recommended)
cd simtemp
python3 -m venv .venv
source .venv/bin/activate

# Install test dependencies
pip install -r tests/requirements.txt
```

#### Jenkins/CI Requirements
```bash
# Jenkins agents must have:
    build-essential \
    linux-headers-$(uname -r) \
    python3 \
    python3-yaml \
    python3-requests \
    python3-pytest

```

## Building

### Quick Build
```bash
cd simtemp/kernel
make all
```

### Clean Build
```bash
cd simtemp/kernel
make clean
make all
```

### Build Output
Successful builds create:
- `obj/nxp_simtemp.ko` - Kernel module binary
- `obj/Module.symvers` - Symbol information
- `obj/modules.order` - Build order information

### Troubleshooting Build Issues

#### Missing Kernel Headers
```bash
# Error: /lib/modules/$(uname -r)/build: No such file or directory
sudo apt install linux-headers-$(uname -r)

# Verify installation
ls -la /lib/modules/$(uname -r)/build
```

#### Compiler Mismatch Warning
This warning is usually safe and can be ignored:
```
warning: the compiler differs from the one used to build the kernel
```

#### BTF Generation Skipped
This is normal in many environments:
```
Skipping BTF generation for nxp_simtemp.ko due to unavailability of vmlinux
```

## Testing

### Local Testing
```bash
# Run all tests
cd simtemp
./tests/run_tests.sh

# Run specific test
cd tests
python3 -m pytest test_kernel_driver.py::test_insmod_registers_driver -v
```

### CI/CD Pipeline Simulation
```bash
# Simulate Jenkins pipeline locally
python3 simtemp/scripts/test_jenkins_kernel_pipeline.py
```

### Expected Test Behavior
- **Build tests**: Should always pass
- **Module loading tests**: May fail due to:
  - Secure Boot restrictions
  - Module signing requirements
  - Permission restrictions in CI environments

## Installation (Optional)

⚠️ **Warning**: Only install if you understand kernel module implications!

### Manual Installation
```bash
# Load module (requires root)
sudo insmod simtemp/kernel/obj/nxp_simtemp.ko

# Verify loading
lsmod | grep nxp_simtemp
dmesg | tail

# Unload module
sudo rmmod nxp_simtemp
```

### Permanent Installation
```bash
# Copy to modules directory
sudo cp simtemp/kernel/obj/nxp_simtemp.ko /lib/modules/$(uname -r)/extra/

# Update module dependencies
sudo depmod -a

# Load automatically at boot (optional)
echo "nxp_simtemp" | sudo tee -a /etc/modules
```

## Configuration

### Pipeline Configuration
- **File**: `simtemp/pipeline_config.yml`
- **Purpose**: Jenkins CI/CD pipeline settings
- **Includes**: Build settings, test configuration, artifacts

### Test Configuration
- **File**: `simtemp/tests/config/simtemp_tests.yml`
- **Purpose**: Test suite configuration
- **Includes**: Test cases, timeouts, dependencies

## CI/CD Integration

### Jenkins Pipeline
The project includes a complete Jenkins pipeline configuration:

1. **Checkout**: Code validation and environment setup
2. **Build**: Kernel module compilation
3. **Test**: Automated testing with pytest
4. **Archive**: Artifact collection and storage

### GitHub Actions (Future)
Configuration templates available in `docs/` directory.

## Development Guidelines

### Code Style
- Follow Linux kernel coding standards
- Use `scripts/checkpatch.pl` for validation
- Maintain compatibility with target kernel versions

### Testing
- All code changes must include tests
- Tests must pass in CI environment
- Handle expected failures gracefully (module signing, etc.)

### Documentation
- Update README for significant changes
- Document new features in `docs/`
- Include inline code documentation

## Troubleshooting

### Common Issues

#### 1. Module Won't Load
```bash
# Check kernel logs
dmesg | tail

# Common causes:
# - Secure Boot enabled
# - Module signing required
# - Missing dependencies
# - Permission denied
```

#### 2. Build Failures
```bash
# Check kernel headers
ls /lib/modules/$(uname -r)/build

# Reinstall if missing
sudo apt install --reinstall linux-headers-$(uname -r)
```

#### 3. Test Failures in CI
Expected in secure environments due to:
- Module signing restrictions
- Secure Boot policies
- Container limitations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Ensure all tests pass locally
5. Submit a pull request

## License

This project is licensed under the GPL v2 (same as Linux kernel).

## Support

For issues and questions:
- Check existing GitHub issues
- Review troubleshooting section
- Create new issue with:
  - Kernel version (`uname -r`)
  - Distribution info (`lsb_release -a`)
  - Build output and error messages