# QEMU Tests Organization

This directory structure organizes QEMU-related scripts by their purpose and execution context.

## Directory Structure

```
deployment/qemu/
├── scripts/                  # Execution and orchestration scripts
│   ├── run-f-k1-tc-002-jenkins.sh # Main QEMU test runner for Jenkins
│   ├── run-tests.sh              # Complete testing framework with embedded tests
│   └── initramfs/                # InitRamFS scripts
├── infra/tests/              # Infrastructure validation scripts
│   ├── test-simple-qemu.sh        # Basic QEMU + 9P filesystem test
│   └── test-qemu-dt.sh             # Device Tree validation test
└── tests/                    # Jenkins pipeline test scripts  
    ├── test-mcimx6ul.sh            # i.MX6UL platform validation
    └── test-imx6ul-configs.sh      # Detailed configuration testing
```

## Script Categories

### 🏗️ Infrastructure Tests (`infra/tests/`)

**Purpose**: Validate QEMU infrastructure and dependencies on Jenkins nodes
**Execution**: Run directly on Jenkins nodes during setup phases
**When**: Before executing any QEMU-based tests

#### `test-simple-qemu.sh`
- **Function**: Basic QEMU functionality test with 9P filesystem
- **Usage**: Infrastructure setup validation
- **Duration**: ~15 seconds
- **Pipeline Stage**: "Setup QEMU Environment"

#### `test-qemu-dt.sh`  
- **Function**: Device Tree compilation and loading validation
- **Usage**: DTB syntax validation and QEMU compatibility check
- **Duration**: ~5 seconds  
- **Pipeline Stage**: "Validate Device Tree"

### 🧪 Jenkins Pipeline Tests (`tests/`)

**Purpose**: Platform validation and debugging within CI/CD pipeline
**Execution**: Run as part of automated test suites
**When**: During test execution phases

#### `test-mcimx6ul.sh`
- **Function**: i.MX6UL platform-specific validation 
- **Usage**: Platform compatibility verification
- **Duration**: ~30 seconds
- **Pipeline Stage**: "Platform Validation"
- **Test Suite**: `platform_validation` in `simtemp_tests.yml`

#### `test-imx6ul-configs.sh`
- **Function**: Detailed QEMU configuration testing
- **Usage**: Debugging when other tests fail
- **Duration**: ~2 minutes
- **Pipeline Stage**: "Debug Analysis" (conditional)
- **Test Suite**: `qemu_debug` in `simtemp_tests.yml`

## Integration Points

### In Jenkins Pipeline (jenkins-qemu-integration.groovy)

```groovy
// Infrastructure validation
stage('Setup QEMU Environment') {
    sh 'deployment/qemu/infra/tests/test-simple-qemu.sh'
    sh 'deployment/qemu/infra/tests/test-qemu-dt.sh'
}

// Platform validation  
stage('Platform Validation') {
    sh 'deployment/qemu/tests/test-mcimx6ul.sh'
}

// Debug analysis (conditional)
stage('Debug Analysis') {
    when { currentBuild.result == 'UNSTABLE' }
    sh 'deployment/qemu/tests/test-imx6ul-configs.sh'
}
```

### In Test Configuration (simtemp_tests.yml)

```yaml
# Platform validation test suite
platform_validation:
  execution_environment:
    type: "shell"  # Runs on Jenkins node
  scripts:
    - "deployment/qemu/tests/test-mcimx6ul.sh"

# Debug test suite  
qemu_debug:
  enabled: false  # Only enabled in debug mode
  scripts:
    - "deployment/qemu/tests/test-imx6ul-configs.sh"
```

## Execution Flow

1. **Infrastructure Setup** → `infra/tests/` scripts validate environment
2. **Platform Validation** → `tests/test-mcimx6ul.sh` validates i.MX6UL
3. **Integration Tests** → Main `qemu_integration` suite runs in QEMU
4. **Debug Analysis** → `tests/test-imx6ul-configs.sh` if issues detected

This organization ensures clear separation between infrastructure validation and actual test execution, improving pipeline reliability and debugging capabilities.