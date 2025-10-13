# Simtemp Scripts

This directory contains scripts specific to the Temperature Simulator (simtemp) kernel module project.

## Scripts

| Script | Description |
|--------|-------------|
| **test_jenkins_kernel_pipeline.py** | Simulates Jenkins pipeline execution for simtemp kernel module testing locally |

## Usage

### Test Jenkins Pipeline Locally
```bash
# From the repository root
python3 examples/kernel_module/scripts/test_jenkins_kernel_pipeline.py
```

This script simulates the exact same pipeline steps as defined in the Jenkinsfile:
1. **Checkout** - Validates git repository and environment
2. **Build** - Compiles the kernel module using the examples/kernel_module/kernel/Makefile
3. **Test** - Runs examples/kernel_module/tests/run_tests.sh with pytest
4. **Archive** - Simulates artifact collection

### Features

- **Configuration-aware**: Uses `examples/kernel_module/pipeline_config.yml` for settings
- **Path validation**: Ensures all required files and directories exist
- **Build simulation**: Runs actual make commands in examples/kernel_module/kernel/
- **Test execution**: Executes real pytest tests via run_tests.sh
- **Artifact checking**: Validates that kernel module (.ko) files are created
- **Error handling**: Provides detailed error messages and exit codes

### Expected Behavior

- **Build**: Should succeed and create `examples/kernel_module/kernel/obj/nxp_simtemp.ko`
- **Tests**: May fail due to module signing restrictions (this is expected in CI environments)
- **Exit codes**: Non-zero exit code indicates pipeline failure

### Dependencies

The script automatically detects the repository root and uses:
- `examples/kernel_module/pipeline_config.yml` - Pipeline configuration
- `examples/kernel_module/tests/config/generic_driver_tests.yml` - Test configuration  
- `examples/kernel_module/kernel/Makefile` - Build system
- `simtemp/tests/run_tests.sh` - Test runner

### Notes

- Test failures due to module signing are expected in secure environments
- The script must be run from within the git repository
- All paths are calculated relative to the repository root
- Requires Python 3.6+ with PyYAML support