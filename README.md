# Challenge 2025 Temperature Sensor System with Octave Integration

## Quick Setup

### For New Team Members

After cloning this repository, **it's recommended** to set up Git hooks for automatic PR mapping:

```bash
# One-time setup for Git hooks (recommended)
./infra_ext/git-hooks/configure-hooks.sh && gh auth login
```

**Why use Git hooks?**
- **Automatic PR mapping**: Keeps `simtemp/tests/config/github_issue_mappings.json` updated
- **CI/CD integration**: Ensures Jenkins can detect correct PR numbers
- **Zero maintenance**: No manual mapping file updates needed
- **Team consistency**: Everyone uses the same workflow

The hooks automatically discover and map branch names to GitHub PR numbers, enabling accurate CI/CD pipeline integration.

## Git Hooks for PR Mapping (Recommended)

This repository includes **automated Git hooks** that maintain the GitHub issue mappings file (`simtemp/tests/config/github_issue_mappings.json`) required for CI/CD integration.

### Why Use Git Hooks?

- **Automatic Discovery**: Uses GitHub CLI to find PR numbers for your branches
- **Auto-Update Mappings**: Keeps mapping file synchronized across team
- **Never Blocks**: Gracefully handles missing PRs or authentication issues
- **Zero Maintenance**: No manual JSON file editing required

### Setup (One-time per developer)

```bash
# Configure hooks to run automatically
./infra_ext/git-hooks/configure-hooks.sh

# Install GitHub CLI for auto-discovery (recommended)
gh auth login
```

### How It Works

1. **Before each commit**: Pre-commit hook runs automatically
2. **Check mappings**: Looks for existing branch to PR mapping
3. **Auto-discover**: Uses `gh pr list --head <branch>` to find PR number
4. **Update & stage**: Adds mapping to JSON file and stages it
5. **Commit proceeds**: Mapping included in your commit

**Example mapping file:**
```json
{
  "req-trigger-jenkins": 5,
  "feature-new-sensor": 42,
  "F-K1-TC-001": 61
}
```

**See [infra_ext/git-hooks/README.md](infra_ext/git-hooks/README.md) for detailed documentation.**

## Project Structure

```
simtemp-system/
│
├── deployment/                       # Deployment and infrastructure
│   ├── docker/                       # Docker configuration for development
│   │   ├── driver/                   # Linux kernel driver container
│   │   │   ├── Dockerfile            # Driver container image
│   │   │   ├── src/                  # simtemp driver source
│   │   │   │   ├── simtemp.c         # Main kernel module
│   │   │   │   ├── simtemp.h         # Header definitions
│   │   │   │   ├── simtemp_ioctl.h   # IOCTL interface
│   │   │   │   ├── Makefile          # Kernel build configuration
│   │   │   │   └── Kbuild            # Kernel build rules
│   │   │   ├── dts/                  # Device Tree Source
│   │   │   │   └── simtemp.dtsi      # DT binding definition
│   │   │   └── config/               # Container configuration
│   │   │
│   │   ├── docker-compose.yml        # Container orchestration
│   │   └── .env                      # Environment variables
│   │
│   ├── jenkins/                      # Jenkins CI/CD configurations
│   │   ├── diagnostics.groovy        # Jenkins diagnostics script
│   │   └── pipeline_helpers/         # Pipeline utility scripts
│   │
│   └── qemu/                         # QEMU infrastructure for DT overlay testing
│       ├── dtb/                      # Device Tree binaries
│       │   ├── imx6ul-simtemp.dts    # Base Device Tree source
│       │   └── imx6ul-simtemp.dtb    # Compiled Device Tree binary
│       ├── overlay/                  # Device Tree overlays
│       │   ├── simtemp-test-overlay.dts   # Test overlay source
│       │   └── simtemp-test-overlay.dtbo  # Compiled overlay binary
│       ├── images/                   # QEMU system images
│       ├── kernel/                   # Kernel files for emulation
│       └── simtemp-dt-overlay.sh     # DT overlay testing script
│
├── user/                             # User space applications
│   ├── cli/                          # CLI application (required by Challenge 2025)
│   │   ├── main.py                   # CLI app for configuration and reading
│   │   ├── simtemp_reader.py         # /dev/simtemp reader with poll/epoll
│   │   ├── sysfs_config.py           # sysfs configuration interface
│   │   ├── test_mode.py              # Test mode implementation
│   │   └── requirements.txt          # Python dependencies
│   │
│   └── gui/                          # GUI application with Seaborn (optional)
│       ├── main.py                   # Main GUI application
│       ├── temperature_dashboard.py  # Real-time temperature dashboard
│       ├── seaborn_plots.py          # Seaborn visualization components
│       ├── control_panel.py          # Sampling/threshold controls
│       ├── alert_monitor.py          # Alert visualization
│       └── requirements.txt          # GUI dependencies (Seaborn, tkinter)
│
├── octave-modules/                   # Octave processing modules
│   ├── cli-processing-modules/       # CLI data processing modules
│   │   ├── threshold_analyzer.m      # Threshold crossing analysis
│   │   ├── sampling_optimizer.m      # Optimal sampling period calculation
│   │   ├── alert_predictor.m         # Alert prediction algorithm
│   │   └── data_validator.m          # Data validation and filtering
│   │
│   ├── gui-visualization-modules/    # GUI visualization processing modules
│   │   ├── real_time_filter.m        # Real-time data filtering for Seaborn
│   │   ├── trend_analyzer.m          # Temperature trend analysis
│   │   ├── statistical_processor.m   # Statistical data processing
│   │   ├── heatmap_generator.m       # Heatmap data for Seaborn
│   │   └── alert_pattern_detector.m  # Alert pattern detection
│   │
│   └── shared-modules/               # Shared utility functions
│       ├── simtemp_interface.m       # Interface to /dev/simtemp data
│       ├── sysfs_helper.m            # sysfs interaction helpers
│       ├── signal_processing.m       # Signal processing utilities
│       └── data_converter.m          # Data format converters
│
├── communication/                    # Communication interfaces
│   ├── kernel-interface/             # Kernel driver communication
│   │   ├── device_reader.py          # /dev/simtemp device reader
│   │   ├── sysfs_interface.py        # sysfs control interface
│   │   ├── ioctl_interface.py        # ioctl control interface
│   │   └── poll_manager.py           # poll/epoll event management
│   │
│   ├── octave-bridge/                # Octave integration bridge
│   │   ├── octave_runner.py          # Octave script executor
│   │   ├── data_converter.py         # Data format converter
│   │   └── module_loader.py          # Dynamic module loading
│   │
│   └── protocols/                    # Data protocols and formats
│       ├── simtemp_protocol.py       # simtemp_sample struct handling
│       ├── data_formats.py           # Data format definitions
│       └── event_types.py            # Event type definitions
│
├── scripts/                          # Build and automation scripts (Challenge 2025 requirement)
│   ├── build.sh                      # Build kernel module and user apps
│   ├── run_demo.sh                   # Demo script: insmod → test → rmmod
│   ├── lint.sh                       # Code linting (optional)
│   ├── setup/                        # Setup scripts
│   │   ├── install_dependencies.sh   # Dependencies installation
│   │   └── setup_environment.sh      # Environment setup
│   │
│   └── testing/                      # Test scripts
│       ├── test_kernel_module.py     # Kernel module tests
│       ├── test_cli_integration.py   # CLI integration tests
│       └── test_octave_modules.py    # Octave modules tests
│
├── config/                           # System configurations
│   ├── simtemp_config.json           # Sensor configuration
│   ├── gui_settings.json             # GUI settings
│   └── octave_paths.json             # Octave modules paths
│
├── data/                             # System data
│   ├── logs/                         # System logs
│   ├── temp_readings/                # Temperature data files
│   └── exports/                      # Exported data
│
├── docs/                             # Documentation (Challenge 2025 requirement)
│   ├── README.md                     # Build/run instructions + repo/video links
│   ├── DESIGN.md                     # Architecture, API, threading model
│   ├── TESTPLAN.md                   # Test plan documentation
│   └── AI_NOTES.md                   # AI prompts and validation notes
│
└── .vscode/                          # VS Code configuration
    ├── settings.json                 # Settings
    ├── tasks.json                    # Build and run tasks
    ├── launch.json                   # Debug configuration
    └── extensions.json               # Recommended extensions
```

## Challenge 2025 System Compliance

This project structure implements the Challenge 2025 Systems Software requirements:

### Kernel Module: `simtemp`

- Platform driver with Device Tree binding (`compatible = "challenge2025,simtemp"`)
- Character device `/dev/simtemp` with binary record output
- sysfs controls: `sampling_ms`, `threshold_mC`, `mode`, `stats`
- poll/epoll support for NEW_SAMPLE and THRESHOLD_CROSSED events

### User Space Applications

- **CLI (Required)**: Configure via sysfs/ioctl, read from `/dev/simtemp`, test mode
- **GUI (Optional)**: Real-time visualization with Seaborn, threshold controls

### Binary Record Format

```c
struct simtemp_sample {
    __u64 timestamp_ns;   // monotonic timestamp
    __s32 temp_mC;        // milli-degree Celsius
    __u32 flags;          // bit0=NEW_SAMPLE, bit1=THRESHOLD_CROSSED
} __attribute__((packed));
```

## Data Flow

1. **Kernel Driver** ↔ **CLI App**:
   - Configuration via sysfs (`/sys/class/.../simtemp/`)
   - Data reading from `/dev/simtemp` with poll/epoll
   - Processing with Octave modules in `cli-processing-modules/`

2. **CLI Data** ↔ **GUI App**:
   - Real-time data sharing for visualization
   - Processing with Octave modules in `gui-visualization-modules/`

3. **Octave Integration**:
   - Modules called from Python via `oct2py` or `subprocess`
   - Data analysis for threshold optimization and trend prediction

4. **Seaborn Visualization**:
   - Statistical plots for sensor configuration analysis
   - Real-time temperature charts and trend visualization
   - Alarm threshold visualization and heatmaps

## Docker Development Environment

- **Containerized kernel development**: Isolated Linux environment
- **Module compilation**: Out-of-tree build with proper headers
- **Device simulation**: `/dev/simtemp` and sysfs in container

## QEMU Infrastructure for Device Tree Overlay Testing

This project includes a comprehensive QEMU-based testing infrastructure for Device Tree overlay validation, specifically supporting F-K1-TC-002 test case development.

### QEMU Environment

- **QEMU ARM installed**: With mcimx6ul-evk machine support for i.MX6UL emulation
- **Cross-compilation toolchain**: gcc-arm-linux-gnueabihf for ARM development  
- **Device Tree compiler**: dtc for compiling .dts files to .dtb binaries
- **Host kernel headers**: Using linux-headers-6.14.0-33-generic for compatibility

### Device Tree Files

- **Base DT**: `deployment/qemu/dtb/imx6ul-simtemp.dts` - i.MX6UL board with simtemp sensor node
- **Overlay DT**: `deployment/qemu/overlay/simtemp-test-overlay.dts` - Test overlay for F-K1-TC-002 validation  
- **Compiled binaries**: Both .dtb and .dtbo files generated successfully with minor warnings

### Test Infrastructure Script

- **Script**: `deployment/qemu/simtemp-dt-overlay.sh` - Management script for DT overlay testing
- **Normal mode**: `./deployment/qemu/simtemp-dt-overlay.sh test` - Test fails correctly (expected behavior)
- **Development mode**: `./deployment/qemu/simtemp-dt-overlay.sh test-dev` - Mock infrastructure for testing test logic
- **Purpose**: Verify F-K1-TC-002 can detect DT overlay infrastructure when present vs absent

### QEMU Installation

```bash
sudo apt install -y qemu-system-arm qemu-user-static gcc-arm-linux-gnueabihf device-tree-compiler
```

### Available i.MX6 Machines

- `mcimx6ul-evk` - Freescale i.MX6UL Evaluation Kit (Cortex-A7)
- Support for Device Tree overlay infrastructure

### Test Execution Modes

```bash
# Normal mode - test should FAIL (correct behavior)
./deployment/qemu/simtemp-dt-overlay.sh test

# Development mode - with mock infrastructure  
./deployment/qemu/simtemp-dt-overlay.sh test-dev
```

**Note**: F-K1-TC-002 test is designed to fail without real Device Tree overlay infrastructure. This is the correct behavior and validates that the test can properly detect the presence or absence of DT overlay support.

## Advantages of this Structure

- **Challenge 2025 Compliance**: Meets all system requirements
- **Modular Design**: Separate CLI, GUI, and processing components
- **Docker Integration**: Isolated development environment
- **Octave Processing**: Advanced data analysis capabilities
- **Seaborn Visualization**: Professional statistical plots
