# QEMU SSH Infrastructure for Remote Command Execution

## Overview

This document describes the multi-channel communication protocol implemented for QEMU ARM environment to enable real command execution in automated tests, replacing simulation-based approaches with actual remote command execution.

## Communication Channels

### 1. Primary Channel: Telnet (Port 2323)
```
Host (Tests) ←→ telnet:2323 ←→ QEMU Guest Shell
```
- **Purpose**: Remote command execution
- **Protocol**: Telnet over TCP
- **Port Mapping**: 2323 (host) → 23 (guest)
- **Implementation**: `QemuSshCommandExecutor._execute_via_telnet()`

### 2. Fallback Channel: SSH (Port 2222)
```
Host (Tests) ←→ ssh:2222 ←→ QEMU Guest (if available)
```
- **Purpose**: Secure command execution
- **Protocol**: SSH over TCP
- **Port Mapping**: 2222 (host) → 22 (guest)
- **Implementation**: `QemuSshCommandExecutor._execute_via_ssh()`

### 3. Monitor Channel: Telnet (Dynamic Port)
```
Host ←→ telnet:monitor_port ←→ QEMU Monitor
```
- **Purpose**: QEMU control and debugging
- **Protocol**: QEMU Monitor via Telnet
- **Port**: Dynamically allocated (free port detection)

### 4. Sensor Channel: Socket (Dynamic Port)
```
Host ←→ socket:socket_port ←→ /dev/ttymxc1 ←→ SimTemp Driver
```
- **Purpose**: Direct communication with temperature driver
- **Protocol**: Raw TCP socket
- **Port**: Dynamically allocated (free port detection)

## Command Execution Protocol

### Connection Sequence
```python
1. SSH attempt → timeout(5s) → fallback
2. Telnet attempt → timeout(30s) → fallback  
3. Simulation fallback → synthetic responses
```

### Telnet Protocol Implementation
```python
def _execute_via_telnet(command, timeout):
    # 1. Establish telnet connection
    tn = telnetlib.Telnet('127.0.0.1', 2323, timeout=5)
    
    # 2. Send command with newline terminator
    tn.write(command.encode('ascii') + b'\n')
    
    # 3. Read response until shell prompt '#'
    response = tn.read_until(b'# ', timeout=timeout)
    
    # 4. Process response
    output = response.decode('utf-8', errors='ignore')
    lines = [line.strip() for line in output.split('\n') if line.strip()]
    
    # 5. Clean command echo and prompt
    if lines and command in lines[0]: 
        lines = lines[1:]
    if lines and lines[-1].endswith('#'): 
        lines = lines[:-1]
    
    return True, lines
```

### SSH Protocol Implementation
```python
def _execute_via_ssh(command, timeout):
    result = subprocess.run([
        'ssh', '-o', 'ConnectTimeout=5',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'LogLevel=QUIET',
        '-p', str(self.ssh_port),
        'root@127.0.0.1',
        command
    ], capture_output=True, text=True, timeout=timeout)
    
    if result.returncode == 0:
        return True, result.stdout.splitlines()
    else:
        return False, result.stderr.splitlines()
```

## QEMU Network Architecture

### QEMU Configuration
```bash
qemu-system-arm \
  -netdev user,id=net0,hostfwd=tcp::2323-:23 \    # Telnet forwarding
  -device e1000,netdev=net0 \                     # Network device
  -serial telnet:127.0.0.1:2323,server,nowait \   # Console via telnet
  -monitor telnet:127.0.0.1:monitor,server,nowait # Monitor access
```

### Guest Configuration (init script)
```bash
# Configure network interfaces
ifconfig lo 127.0.0.1 up
ifconfig eth0 up

# Start telnet daemon
telnetd -p 23 -l /bin/sh  # Listen on port 23, exec shell
echo "telnetd started on port 23"
```

## Protocol Selection

### Environment Variable Control
```bash
QEMU_CONSOLE_TELNET=1  # Enable telnet communication (default)
QEMU_CONSOLE_TELNET=0  # Use simulation only
```

### Selection Logic
```python
class UnifiedCommandExecutor:
    def _initialize_qemu_executor(self):
        use_telnet = os.environ.get('QEMU_CONSOLE_TELNET', '1') \
            in ['1', 'true', 'True']
        
        if use_telnet:
            # Real command execution via telnet/SSH
            self.qemu_executor = QemuSshCommandExecutor(qemu_process)
        else:
            # Simulation mode
            self.qemu_executor = QemuCommandExecutor(qemu_process)
```

## Complete Communication Flow

```
Test Case (Python)
       ↓
UnifiedCommandExecutor
       ↓
QemuSshCommandExecutor
       ↓
1. SSH attempt (port 2222) → FAIL
       ↓
2. Telnet attempt (port 2323) → SUCCESS
       ↓
telnetlib connection
       ↓
QEMU network bridge
       ↓
Guest telnetd (port 23)
       ↓
BusyBox shell (/bin/sh)
       ↓
Linux command execution
       ↓
Response back through telnet
       ↓
Parsed output to Test Case
```

## Implementation Files

### Core Infrastructure
- `simtemp/tests/test_ucommand_exec.py`: Command execution abstraction
- `simtemp/tests/test_utils.py`: QEMU session management
- `deployment/qemu/rootfs/init`: Guest initialization script

### Key Classes
- `UnifiedCommandExecutor`: Main command execution interface
- `QemuSshCommandExecutor`: Real SSH/Telnet command execution
- `QemuCommandExecutor`: Simulation fallback

## Protocol Advantages

1. **Resilient**: Multiple fallback mechanisms (SSH → Telnet → Simulation)
2. **Real-time**: Actual command execution in QEMU ARM environment
3. **Transparent**: ARM tests use same API as x86 tests
4. **Debuggable**: Monitor channel and multiple communication paths
5. **Robust**: Comprehensive timeout and error handling at each layer
6. **Testable**: F-K2 ARM tests execute real commands instead of simulations

## Usage Example

```python
# Enable telnet-based execution
os.environ['QEMU_CONSOLE_TELNET'] = '1'

# Execute command in QEMU ARM
from test_ucommand_exec import execute_command
success, output = execute_command("cat /proc/version")

if success:
    print("Real command executed:", output)
else:
    print("Command failed:", output)
```

## Testing Integration

The infrastructure enables ARM F-K2 tests to perform real command execution:

```python
# ARM test using real commands
def test_sampling_jitter_within_10_percent_arm(self):
    # Set sampling rate via real sysfs write
    success, output = execute_command("echo 500 > /sys/.../sampling_ms")
    
    # Read actual device data via real dd command  
    success, output = execute_command("dd if=/dev/simtemp0 bs=20 count=1")
    
    # Parse real hexdump output
    success, output = execute_command("hexdump -C /tmp/sample.bin")
```

This replaces simulation with actual ARM environment validation, ensuring driver functionality works correctly on the target platform.