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

This project includes a comprehensive QEMU-based testing infrastructure for Device Tree overlay validation in i.MX6UL environment, specifically supporting F-K1-TC-002 test case execution with Jenkins CI/CD integration.

### Architecture Overview

- **Target Platform**: i.MX6UL (ARM Cortex-A7) emulated via QEMU mcimx6ul-evk machine
- **Test Framework**: F-K1-TC-002 Device Tree overlay driver binding validation
- **CI/CD Integration**: Jenkins automation with 9P filesystem sharing and XML/JSON reporting
- **Kernel Source**: Official NXP linux-imx repository (lf-6.6.52-2.2.1 tag)

### Prerequisites Installation

```bash
# Install required dependencies for QEMU ARM development
sudo apt update && sudo apt install -y \
    qemu-system-arm \
    gcc-arm-linux-gnueabihf \
    device-tree-compiler \
    git build-essential \
    libncurses-dev flex bison \
    libssl-dev bc
```

### i.MX6UL Kernel Compilation

#### **Automated Kernel Build from NXP Sources:**
```bash
# Download and compile official i.MX6UL kernel from NXP
./deployment/qemu/download-compile-imx6ul-kernel.sh
```

**What this script does:**
1. **Downloads**: Official NXP linux-imx repository (github.com/nxp-imx/linux-imx)
2. **Checks out**: Tag lf-6.6.52-2.2.1 (i.MX6UL compatible release)
3. **Configures**: imx_v6_v7_defconfig with i.MX6UL support
4. **Enables**: Device Tree overlay support (CONFIG_OF_OVERLAY, CONFIG_CONFIGFS_FS)
5. **Enables**: 9P filesystem for Jenkins workspace sharing (CONFIG_NET_9P*, CONFIG_9P_FS*)
6. **Compiles**: Cross-compiled zImage and Device Tree Blob (DTB)
7. **Generates**: Test script for QEMU validation

**Output files:**
- `deployment/qemu/zImage-imx6ul` - Compiled i.MX6UL kernel (6.6.52)
- `deployment/qemu/imx6ul-14x14-evk.dtb` - Official i.MX6UL Device Tree Blob
- `deployment/qemu/test-imx6ul-kernel.sh` - QEMU test script with new kernel

#### **Manual Testing of Compiled Kernel:**
```bash
# Test the newly compiled i.MX6UL kernel
cd deployment/qemu && ./test-imx6ul-kernel.sh
```

### Jenkins Integration with 9P Filesystem

#### **Production Jenkins Execution:**
```bash
# Execute F-K1-TC-002 test in QEMU with Jenkins automation
./deployment/qemu/run-f-k1-tc-002-jenkins.sh
```

**Jenkins automation features:**
- ✅ **9P virtfs**: Host workspace mounted in QEMU via `/mnt/host` for code sharing
- ✅ **Test execution**: F-K1-TC-002 runs inside QEMU with pytest framework
- ✅ **Result extraction**: XML and JSON test reports generated for Jenkins
- ✅ **Environment detection**: Automatic fallback to mock mode if needed
- ✅ **Error handling**: Proper exit codes and error reporting for CI/CD

#### **Development Testing:**
```bash
# Debug QEMU execution with verbose output  
./deployment/qemu/debug-qemu-test.sh
```

### F-K1-TC-002 Test Validation

The test validates Device Tree overlay driver binding infrastructure:

#### **Test Components:**
- **configfs support**: `/sys/kernel/config/device-tree/overlays/` directory structure
- **procfs DT access**: `/proc/device-tree` filesystem availability  
- **Overlay binding**: Mock and production overlay loading verification

#### **Execution Modes:**
```bash
# Production mode (should PASS with compiled i.MX6UL kernel)
pytest simtemp/tests/test_f_k1_tc_002.py -v

# Mock mode (for development without full DT overlay infrastructure)
pytest simtemp/tests/test_f_k1_tc_002.py -v --capture=no
```

#### **Expected Results:**
- ✅ **With i.MX6UL kernel**: Test should PASS (CONFIG_OF_OVERLAY enabled)
- ❌ **With incompatible kernel**: Test should FAIL (proper validation behavior)
- 🔄 **Mock mode**: Test runs with simulated infrastructure for development

### QEMU Machine Configuration

#### **Verified i.MX6UL Support:**
```bash
# Verify QEMU supports i.MX6UL machine with all options
qemu-system-arm -machine mcimx6ul-evk,help
```

**Available options:**
- ✅ `cortex-a7` CPU support
- ✅ Memory configuration (up to 512MB)
- ✅ Kernel and DTB loading
- ✅ initrd support for test environment
- ✅ Network and virtio device support

#### **9P Filesystem Configuration:**
```bash
# Example QEMU command with 9P workspace sharing
qemu-system-arm \
    -M mcimx6ul-evk -cpu cortex-a7 -m 256M \
    -kernel zImage-imx6ul \
    -dtb imx6ul-14x14-evk.dtb \
    -initrd initrd-with-python.img \
    -virtfs local,path=/workspace,mount_tag=host,security_model=passthrough \
    -append "console=ttymxc0,115200 root=/dev/ram0 rw" \
    -nographic
```

### Jenkins CI/CD Pipeline Integration Strategy

#### **Testing Strategy Overview:**
The Jenkins pipeline executes F-K1-TC-002 Device Tree overlay tests in a virtualized i.MX6UL environment using QEMU emulation. This provides consistent, reproducible testing without requiring physical hardware.

#### **Pipeline Workflow:**
```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  1. Git Trigger │──▶│  2. Build Stage │──▶│  3. Test Stage  │
│                 │   │                 │   │                 │
│ • PR Detection  │   │ • Compile Kernel│   │ • Launch QEMU   │
│ • Branch Mapping│   │ • Build DTBs    │   │ • Mount Workspace│
│ • Code Checkout │   │ • Create initrd │   │ • Run F-K1-TC-002│
└─────────────────┘   └─────────────────┘   └─────────────────┘
                                                       │
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ 6. Cleanup      │◀──│ 5. Artifact     │◀──│ 4. Result       │
│                 │   │    Collection   │   │    Processing   │
│ • Stop QEMU     │   │                 │   │                 │
│ • Archive Logs  │   │ • Test Reports  │   │ • XML/JSON Gen  │
│ • Status Report │   │ • Kernel Images │   │ • Exit Codes    │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

#### **Stage 1: Environment Setup**
```groovy
pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                // Install dependencies if not present
                sh 'sudo apt update && sudo apt install -y qemu-system-arm gcc-arm-linux-gnueabihf'
                
                // Verify QEMU supports i.MX6UL
                sh 'qemu-system-arm -machine help | grep mcimx6ul-evk || exit 1'
            }
        }
    }
}
```

#### **Stage 2: Kernel Compilation**
```groovy
stage('Build Kernel') {
    steps {
        // Use cached kernel if available, otherwise compile
        script {
            if (!fileExists('deployment/qemu/zImage-imx6ul')) {
                sh './deployment/qemu/download-compile-imx6ul-kernel.sh'
            }
        }
        
        // Verify kernel compilation success
        sh 'test -f deployment/qemu/zImage-imx6ul'
        sh 'test -f deployment/qemu/imx6ul-14x14-evk.dtb'
    }
}
```

#### **Stage 3: QEMU Test Execution**
```groovy
stage('Execute Tests') {
    steps {
        // Run F-K1-TC-002 in QEMU with 9P filesystem sharing
        sh '''
            cd deployment/qemu
            timeout 300 ./run-f-k1-tc-002-jenkins.sh || {
                echo "Test execution failed or timed out"
                exit 1
            }
        '''
    }
    post {
        always {
            // Collect test results regardless of outcome
            publishTestResults testResultsPattern: 'deployment/qemu/test-results.xml'
            archiveArtifacts artifacts: 'deployment/qemu/test-results.json', allowEmptyArchive: true
        }
    }
}
```

#### **9P Filesystem Strategy:**
The Jenkins workspace is shared with QEMU using 9P virtfs, enabling:
- **Code Access**: Test files accessible inside QEMU without copying
- **Result Export**: XML/JSON reports written directly to Jenkins workspace
- **Log Collection**: Real-time log access for debugging and monitoring
- **Artifact Preservation**: Build artifacts available for downstream stages

```bash
# 9P mount command used in QEMU
-virtfs local,path=${WORKSPACE},mount_tag=host,security_model=passthrough

# Inside QEMU guest
mount -t 9p -o trans=virtio host /mnt/host
cd /mnt/host && python -m pytest simtemp/tests/test_f_k1_tc_002.py --junit-xml=test-results.xml
```

#### **Pipeline Support:**
- **Test execution**: Automated F-K1-TC-002 validation in QEMU environment
- **Result reporting**: XML format for Jenkins test result parsing  
- **JSON output**: Detailed test metadata for advanced CI/CD analysis
- **Artifact collection**: Kernel images, DTBs, and test reports preserved
- **Error propagation**: Proper exit codes for pipeline success/failure detection
- **Timeout handling**: 5-minute timeout to prevent hanging builds
- **Parallel execution**: Multiple Jenkins agents can run simultaneously

#### **Jenkins Agent Requirements:**
```bash
# Minimum dependencies for Jenkins agents
sudo apt install -y qemu-system-arm gcc-arm-linux-gnueabihf git python3-pytest

# Verify agent capabilities
qemu-system-arm -version | grep "QEMU emulator version"
arm-linux-gnueabihf-gcc --version | grep "gcc"
python3 -m pytest --version
```

#### **Error Handling Strategy:**
- **Kernel compilation failure**: Use cached kernel or fail with clear message
- **QEMU boot failure**: Retry with different configurations, fallback to mock mode  
- **Test timeout**: Graceful termination with partial results collection
- **Network issues**: Repository caching and offline mode support
- **Resource constraints**: Memory and CPU limits with automatic scaling

#### **Advantages of QEMU + Jenkins Strategy:**
- ✅ **Hardware Independence**: No physical i.MX6UL boards required for testing
- ✅ **Parallel Execution**: Multiple test instances on different Jenkins agents
- ✅ **Consistent Environment**: Identical test conditions across all runs  
- ✅ **Cost Effective**: Virtualized testing reduces hardware costs
- ✅ **Rapid Iteration**: Fast boot times and immediate feedback
- ✅ **Scalability**: Easy to add more Jenkins agents as needed
- ✅ **Debugging**: QEMU provides detailed logging and debugging capabilities
- ✅ **Integration**: Seamless CI/CD pipeline integration with existing tools

#### **Example Jenkinsfile Configuration:**
```groovy
pipeline {
    agent { label 'linux-qemu' }
    
    environment {
        QEMU_SYSTEM_ARM = '/usr/bin/qemu-system-arm'
        CROSS_COMPILE = 'arm-linux-gnueabihf-'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git submodule update --init --recursive'
            }
        }
        
        stage('Setup QEMU Environment') {
            steps {
                sh '''
                    # Verify QEMU installation
                    qemu-system-arm -version
                    qemu-system-arm -machine help | grep mcimx6ul-evk
                    
                    # Verify cross-compilation tools
                    arm-linux-gnueabihf-gcc --version
                '''
            }
        }
        
        stage('Compile i.MX6UL Kernel') {
            steps {
                script {
                    if (!fileExists('deployment/qemu/zImage-imx6ul')) {
                        sh './deployment/qemu/download-compile-imx6ul-kernel.sh'
                    } else {
                        echo 'Using cached kernel image'
                    }
                }
            }
            post {
                success {
                    archiveArtifacts artifacts: 'deployment/qemu/zImage-imx6ul,deployment/qemu/imx6ul-14x14-evk.dtb'
                }
            }
        }
        
        stage('Run F-K1-TC-002 Tests') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    sh '''
                        cd deployment/qemu
                        ./run-f-k1-tc-002-jenkins.sh
                    '''
                }
            }
            post {
                always {
                    publishTestResults testResultsPattern: 'deployment/qemu/test-results.xml'
                    archiveArtifacts artifacts: 'deployment/qemu/test-results.*,deployment/qemu/qemu-console.log'
                }
                failure {
                    sh 'cat deployment/qemu/qemu-console.log || echo "No console log available"'
                }
            }
        }
    }
    
    post {
        cleanup {
            sh '''
                # Kill any remaining QEMU processes
                pkill -f qemu-system-arm || true
                
                # Clean up temporary files
                rm -f deployment/qemu/qemu-console.log
            '''
        }
    }
}
```

#### **Jenkins Global Configuration:**
```bash
# Add to Jenkins global tool configuration
QEMU_SYSTEM_ARM=/usr/bin/qemu-system-arm
ARM_CROSS_COMPILE=arm-linux-gnueabihf-

# Jenkins agent labels for QEMU-enabled nodes
linux-qemu
qemu-arm-capable
hardware-emulation
```

### Infrastructure Status

#### ✅ **Production Ready:**
- **QEMU ARM 8.2.2**: Confirmed mcimx6ul-evk machine support
- **NXP Kernel**: Official i.MX6UL kernel (lf-6.6.52-2.2.1) with DT overlay support
- **Cross-compilation**: gcc-arm-linux-gnueabihf toolchain functional
- **Test Framework**: F-K1-TC-002 fully implemented with environment detection
- **Jenkins Integration**: 9P filesystem sharing and XML/JSON reporting configured

#### 🔧 **Build Process:**
- **Source**: Official NXP repository (github.com/nxp-imx/linux-imx)
- **Configuration**: imx_v6_v7_defconfig + Device Tree overlay + 9P filesystem
- **Cross-compilation**: ARM Linux kernel build with proper configuration
- **Validation**: QEMU boot testing with i.MX6UL machine emulation

#### 📋 **Test Execution:**
```bash
# Complete workflow: compile kernel + run F-K1-TC-002 test
./deployment/qemu/download-compile-imx6ul-kernel.sh
cd deployment/qemu && ./test-imx6ul-kernel.sh

# Jenkins automation (includes 9P filesystem sharing)
./deployment/qemu/run-f-k1-tc-002-jenkins.sh
```

### Troubleshooting

#### **Common Issues:**
- **Kernel compatibility**: Use official i.MX6UL kernel, not RPI kernel
- **Missing dependencies**: Run dependency installation commands above
- **QEMU machine**: Ensure mcimx6ul-evk machine is available in QEMU version
- **9P filesystem**: Verify virtfs support in QEMU for Jenkins workspace sharing

#### **Validation Commands:**
```bash
# Verify QEMU machine support
qemu-system-arm -machine help | grep mcimx6ul

# Check kernel format and architecture  
file deployment/qemu/zImage-imx6ul

# Test kernel boot without full system
qemu-system-arm -M mcimx6ul-evk -kernel deployment/qemu/zImage-imx6ul -nographic -append "console=ttymxc0"
```

## Advantages of this Structure

- **Challenge 2025 Compliance**: Meets all system requirements
- **Modular Design**: Separate CLI, GUI, and processing components
- **Docker Integration**: Isolated development environment
- **Octave Processing**: Advanced data analysis capabilities
- **Seaborn Visualization**: Professional statistical plots
