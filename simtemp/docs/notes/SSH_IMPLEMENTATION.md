# SSH Implementation in test_utils.py

This document describes the hardcoded SSH configuration + serial console implementation added to the `start_qemu_and_wait_for_boot()` function in `test_utils.py`.

## Implementation Summary

The SSH configuration has been successfully implemented with the following features:

### 1. Hardcoded SSH Configuration
- **SSH Port**: 2222 (hardcoded, same as `run_qemu.ssh.sh`)
- **Network Setup**: Uses QEMU user networking with port forwarding
- **QEMU Parameters**: `-net nic -net user,hostfwd=tcp::2222-:22`

### 2. Serial Console Support
- **Telnet Console**: Available on port 2323 when `QEMU_CONSOLE_TELNET=1`
- **Stdio Console**: Direct terminal access when telnet is disabled
- **Kernel Command Line**: `console=ttymxc0,115200 earlycon=imx,0x02020000,115200 rdinit=/init`

### 3. New Utility Functions

#### `wait_for_ssh_ready(ssh_port=2222, timeout=30)`
- Waits for SSH service to become available in the QEMU guest
- Tests SSH connectivity without authentication
- Returns `True` when SSH is ready, `False` on timeout

#### `execute_ssh_command(command, ssh_port=2222, timeout=10)`
- Executes commands via SSH in the QEMU guest
- Handles SSH connection parameters automatically
- Returns `(success: bool, output_lines: list)`

### 4. Enhanced Boot Process
The `start_qemu_and_wait_for_boot()` function now:
- Enables SSH networking by default (hardcoded configuration)
- Provides debug output showing SSH port and connection details
- Maintains compatibility with existing socket-based communication
- Supports both telnet and stdio console modes

## Usage Examples

### Basic SSH Command Execution
```python
from test_utils import start_qemu_and_wait_for_boot, wait_for_ssh_ready, execute_ssh_command

# Start QEMU with SSH support
qemu_process, socket_port = start_qemu_and_wait_for_boot()

# Wait for SSH to be ready
if wait_for_ssh_ready():
    # Execute commands via SSH
    success, output = execute_ssh_command("lsmod | grep nxp_simtemp")
    if success:
        print(f"Module status: {output[0]}")
```

### Manual SSH Access
When QEMU is running, you can manually connect via SSH:
```bash
ssh -p 2222 root@127.0.0.1
```

## Configuration Details

### QEMU Command Line Changes
The implementation adds these parameters to the QEMU command:
```bash
-net nic \
-net user,hostfwd=tcp::2222-:22
```

### Rootfs Configuration
The SSH functionality relies on the existing `rootfs/init` script which:
- Starts dropbear SSH server on port 22
- Configures network interface (10.0.2.15)
- Generates SSH host keys automatically
- Sets up PTY devices for SSH sessions

## Testing

### Automated Test
Run the test script to verify SSH functionality:
```bash
python3 test_ssh_implementation.py
```

### Expected Output
- ✓ QEMU starts with SSH configuration
- ✓ SSH service becomes ready within timeout
- ✓ SSH commands can be executed successfully
- ✓ Module and driver operations accessible via SSH

## Compatibility

This implementation:
- ✅ Maintains backward compatibility with existing test_utils functions
- ✅ Works with existing socket-based communication (sensor port)
- ✅ Supports both telnet and stdio console modes
- ✅ Preserves existing QEMU session management
- ✅ Uses the same SSH configuration as `run_qemu.ssh.sh`

## Integration

The SSH configuration is now hardcoded and automatically enabled in `test_utils.py`, making it available to all tests that use `start_qemu_and_wait_for_boot()` without requiring any changes to existing test code.