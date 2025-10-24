# QEMU Developer CLI Tools - Complete Documentation

This document provides comprehensive documentation for QEMU developer CLI tools, including usage guides, technical implementation details, and troubleshooting information.

## Table of Contents

1. [Overview and Quick Start](#overview-and-quick-start)
2. [Available Tools](#available-tools)
3. [Technical Implementation](#technical-implementation)
4. [Session Management](#session-management)
5. [Common Use Cases](#common-use-cases)
6. [Troubleshooting](#troubleshooting)
7. [Requirements and Setup](#requirements-and-setup)

## Overview and Quick Start

These tools are located in `simtemp/scripts/dev-cli/` and provide independent access to active QEMU sessions through both monitor commands and guest system interaction.

### Quick Start Commands

From the project root directory (`simtemp-system/`):

```bash
# List all active QEMU sessions
./simtemp/scripts/dev-cli/qemu-tool list

# Get detailed status of a session
./simtemp/scripts/dev-cli/qemu-tool status <PID>

# Access QEMU monitor interactively
./simtemp/scripts/dev-cli/qemu-tool monitor <PID>

# Execute commands in guest system
./simtemp/scripts/dev-cli/qemu-tool guest <PID> "lsmod"

# Open interactive guest shell
./simtemp/scripts/dev-cli/qemu-tool shell <PID>
```

## Available Tools

### Tool Overview

| Tool | Purpose | Type | Best For |
|------|---------|------|----------|
| `qemu-tool` | Unified QEMU session management | Shell script | **Recommended** - All operations |
| `qemu-connect` | Simple monitor connection | Shell script | Quick monitor access |
| `qemu_connect.py` | Python monitor interface | Python script | Scripting and automation |
| `qemu_guest_cmd.py` | Guest command execution | Python script | Automated guest operations |

### `qemu-tool` (Recommended)
Unified script that combines all functionalities:

```bash
# List active sessions
./qemu-tool list

# Complete session status
./qemu-tool status <PID>

# Interactive QEMU monitor
./qemu-tool monitor <PID>

# Specific monitor command
./qemu-tool monitor <PID> "info version"

# Command in guest (ARM emulated system)
./qemu-tool guest <PID> "lsmod"

# Interactive shell in guest
./qemu-tool shell <PID>
```

### `qemu-connect`
Simple script for QEMU monitor connection:

```bash
# List sessions
./qemu-connect

# Connect interactively
./qemu-connect <PID>

# Execute specific command
./qemu-connect <PID> "info status"
```

### Specialized Python Scripts

#### `qemu_connect.py`
Direct connection to QEMU telnet monitor:
```bash
python3 qemu_connect.py --list
python3 qemu_connect.py --connect <PID> --command "info version"
python3 qemu_connect.py --connect <PID> --interactive
```

#### `qemu_guest_cmd.py`
Send commands to guest system:
```bash
python3 qemu_guest_cmd.py --pid <PID> --command "lsmod"
python3 qemu_guest_cmd.py --pid <PID> --interactive
```

## Technical Implementation

### Architecture Overview

The system implements independent access to QEMU sessions through:

1. **Session Markers**: JSON files containing PID, monitor port, and metadata
2. **Monitor Interface**: Telnet connection to QEMU monitor for hypervisor commands
3. **Guest Interface**: Integration with existing `test_utils.py` for guest commands
4. **Dynamic Port Allocation**: Automatic port assignment to prevent conflicts

### Code Changes Made

#### Modified Functions in `test_utils.py`

**Function: `start_qemu_and_wait_for_boot()`**
- **Before**: Returned only the QEMU process
- **After**: Returns tuple `(qemu_process, monitor_port)`
- **Change**: Generates dynamic port for telnet monitor

**Function: `create_qemu_session_marker(qemu_process, monitor_port=None)`**
- **Before**: Saved only PID, timestamp, started_by, test_name
- **After**: Includes monitor_port and monitor_address
- **Purpose**: Enable independent process connection

**Function: `create_private_qemu_marker(qemu_process, monitor_port=None)`**
- Similar updates for private sessions
- Maintains session type isolation

### QEMU Configuration

QEMU processes are automatically started with monitor support:

```bash
qemu-system-arm \
    -M sabrelite \
    -cpu cortex-a9 \
    -m 1024 \
    -nographic \
    -kernel <kernel_path> \
    -dtb <dtb_path> \
    -initrd <rootfs_path> \
    -append "console=ttymxc0,115200 earlycon=imx,0x02020000,115200 ..." \
    -monitor telnet:127.0.0.1:<dynamic_port>,server,nowait \
    -no-reboot
```

Where `<dynamic_port>` is automatically generated to avoid conflicts.

## Session Management

### Session Markers

All tools work with session markers containing connection information:

**Shared Session Marker**: `/tmp/qemu_session_active.marker`
**Private Session Markers**: `/tmp/qemu_private_session_<UID>_<PID>.json`

### Marker Structure

```json
{
  "pid": 1234567,
  "started_at": 1761252095.6474056,
  "started_by": "test_utils.py",
  "test_name": "test_arm_f_k1_tc_002_boot.py::test_basic_qemu_boot (call)",
  "monitor_port": 43919,
  "monitor_address": "127.0.0.1:43919"
}
```

### Session Types

1. **Shared Sessions**: Reused across multiple tests (default behavior)
2. **Private Sessions**: Isolated sessions for specific tests (`force_new=True`)

### Port Management

- **Dynamic Allocation**: Ports automatically assigned using `socket.bind(('127.0.0.1', 0))`
- **Conflict Avoidance**: Each session gets unique port
- **Local Access Only**: Monitor bound to localhost (127.0.0.1) for security

## Common Use Cases

### 1. Check QEMU Status
```bash
./qemu-tool list                    # View all sessions
./qemu-tool status 1234             # Detailed status
```

### 2. Kernel Module Development and Debugging
```bash
# Check loaded modules
./qemu-tool guest 1234 "lsmod"

# Load simtemp module
./qemu-tool guest 1234 "insmod /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"

# Verify module loaded
./qemu-tool guest 1234 "lsmod | grep nxp"

# Check kernel messages
./qemu-tool guest 1234 "dmesg | tail -10"

# Verify driver binding
./qemu-tool guest 1234 "ls /sys/bus/platform/drivers/ | grep nxp"

# Check module information
./qemu-tool guest 1234 "cat /proc/modules | grep nxp"

# Unload module
./qemu-tool guest 1234 "rmmod nxp_simtemp"
```

### 3. QEMU Monitor Operations
```bash
# Check VM status
./qemu-tool monitor 1234 "info status"

# View CPU information
./qemu-tool monitor 1234 "info cpus"

# Get QEMU version
./qemu-tool monitor 1234 "info version"

# Memory information
./qemu-tool monitor 1234 "info memory"

# Interactive monitor session
./qemu-tool monitor 1234
```

### 4. Interactive Development Workflow
```bash
# Open interactive guest shell
./qemu-tool shell 1234

# Example interactive session:
guest# lsmod | head -5
guest# insmod /tmp/prebuild/simtemp-driver/nxp_simtemp.ko
guest# dmesg | tail -5
guest# ls /sys/bus/platform/drivers/ | grep nxp
guest# cat /sys/bus/platform/drivers/nxp_simtemp/uevent
guest# rmmod nxp_simtemp
guest# quit
```

### 5. Automated Testing Scripts
```bash
#!/bin/bash
# Example automation script

PID=$(./simtemp/scripts/dev-cli/qemu-tool list | grep "PID:" | head -1 | cut -d' ' -f2)

if [ -n "$PID" ]; then
    echo "Testing with QEMU PID: $PID"
    
    # Load module
    ./simtemp/scripts/dev-cli/qemu-tool guest $PID "insmod /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"
    
    # Verify loading
    if ./simtemp/scripts/dev-cli/qemu-tool guest $PID "lsmod | grep -q nxp"; then
        echo "Module loaded successfully"
        
        # Run tests...
        ./simtemp/scripts/dev-cli/qemu-tool guest $PID "echo 'Testing commands...'"
        
        # Clean up
        ./simtemp/scripts/dev-cli/qemu-tool guest $PID "rmmod nxp_simtemp"
    else
        echo "Module failed to load"
        exit 1
    fi
else
    echo "No active QEMU sessions found"
    exit 1
fi
```

### 6. Multi-Session Development
```bash
# Work with multiple sessions
./qemu-tool list

# Connect to specific sessions for different tasks
./qemu-tool monitor 1234 "info status"    # Check first session
./qemu-tool guest 5678 "lsmod"            # Test in second session
```

## Troubleshooting

### Common Issues

#### 1. No Active Sessions Found
```bash
# Symptoms
./qemu-tool list
# Output: "No active QEMU sessions found."

# Solutions
- Check if QEMU tests are running: `ps aux | grep qemu-system-arm`
- Verify marker files exist: `ls /tmp/qemu_*session*`
- Restart test suite to create new session
```

#### 2. Monitor Connection Failed
```bash
# Symptoms
Error: Session 1234 has no monitor port configured

# Solutions
- Check if session was created with new code (has monitor_port in marker)
- For old sessions, restart QEMU to get monitor support
- Verify port is not blocked: `netstat -tulpn | grep <port>`
```

#### 3. Guest Commands Not Working
```bash
# Symptoms
Error: Could not import test_utils

# Solutions
- Run from project root directory: `/path/to/simtemp-system/`
- Check Python path includes simtemp/tests/
- Verify test_utils.py exists: `ls simtemp/tests/test_utils.py`
```

#### 4. Permission Issues
```bash
# Symptoms
Permission denied accessing marker files

# Solutions
- Check file permissions: `ls -la /tmp/qemu_*session*`
- Verify running as same user who created session
- Clean stale markers: `rm /tmp/qemu_*session*` (careful!)
```

### Debug Commands

```bash
# Check QEMU processes
ps aux | grep qemu-system-arm

# Verify monitor ports
netstat -tulpn | grep 127.0.0.1

# Check marker files
cat /tmp/qemu_session_active.marker
ls /tmp/qemu_private_session_*

# Test telnet connection directly
telnet 127.0.0.1 <monitor_port>

# Check Python imports
python3 -c "import sys; sys.path.insert(0, 'simtemp/tests'); import test_utils; print('OK')"
```

## Requirements

### System Dependencies
- **Python 3.6+** with telnetlib support
- **QEMU ARM system emulation** (qemu-system-arm)
- **Linux environment** (tested on Ubuntu/Debian)
- **Bash shell** for script execution

### Project Dependencies
- **simtemp test infrastructure** (simtemp/tests/test_utils.py)
- **QEMU session management** system
- **Network access** to localhost for telnet connections

### Runtime Requirements
- Active QEMU ARM session (started via test suite)
- Session marker files in `/tmp/`
- Monitor telnet port available
- Appropriate user permissions

## File Structure

```
simtemp/scripts/dev-cli/
├── DEVELOPER_CLI_README.md          # This comprehensive guide
├── qemu-tool                        # Main CLI script (shell)
├── qemu_connect.py                  # Python monitor interface
└── qemu_guest_cmd.py                # Python guest command interface

Related Files:
simtemp/tests/test_utils.py          # Core QEMU session management
/tmp/qemu_session_active.marker      # Active session marker
/tmp/qemu_private_session_*          # Private session markers
```

### Script Dependencies

```
qemu-tool
├── depends on: qemu_connect.py (for monitor operations)
├── depends on: qemu_guest_cmd.py (for guest operations)
└── uses: /tmp/qemu_*session* (marker files)

qemu_connect.py
├── uses: telnetlib (Python standard library)
├── reads: /tmp/qemu_*session*.marker (JSON format)
└── connects to: 127.0.0.1:<monitor_port>

qemu_guest_cmd.py
├── imports: simtemp.tests.test_utils
├── reads: /tmp/qemu_*session*.marker (JSON format)  
└── calls: test_utils.execute_guest_command()
```

## Installation

### Quick Setup
1. Ensure you're in the project root directory:
   ```bash
   cd /path/to/simtemp-system/
   ```

2. Make scripts executable:
   ```bash
   chmod +x simtemp/scripts/dev-cli/qemu-tool
   chmod +x simtemp/scripts/dev-cli/qemu_connect.py
   chmod +x simtemp/scripts/dev-cli/qemu_guest_cmd.py
   ```

3. Verify Python dependencies:
   ```bash
   python3 -c "import telnetlib; print('telnetlib OK')"
   python3 -c "import sys; sys.path.insert(0, 'simtemp/tests'); import test_utils; print('test_utils OK')"
   ```

### Integration with Test Suite
The CLI tools integrate automatically with existing QEMU test sessions. No additional configuration needed - just start a test that launches QEMU and the CLI tools will discover and connect to it.

## Contributing

When modifying these tools:

1. **Maintain backward compatibility** with existing session marker format
2. **Update this documentation** when adding new features
3. **Test with active QEMU sessions** before committing
4. **Follow Python PEP 8** style guidelines
5. **Add error handling** for new failure modes

For questions or improvements, please refer to the simtemp project documentation or create an issue in the project repository.

## Session Information

All scripts work with session markers located at:
- Shared session: `/tmp/qemu_session_active.marker`
- Private sessions: `/tmp/qemu_private_session_<UID>_<PID>.json`

Each marker contains:
```json
{
  "pid": 1234567,
  "started_at": 1761252095.6474056,
  "started_by": "test_utils.py",
  "test_name": "test_name",
  "monitor_port": 43919,
  "monitor_address": "127.0.0.1:43919"
}
```

## Tool Overview

| Tool | Purpose | Type |
|------|---------|------|
| `qemu-tool` | Unified QEMU session management | Shell script (recommended) |
| `qemu-connect` | Simple monitor connection | Shell script |
| `qemu_connect.py` | Python monitor interface | Python script |
| `qemu_guest_cmd.py` | Guest command execution | Python script |

## Requirements

- Python 3.6+
- QEMU with telnet monitor enabled
- Access to session marker files
- Run from simtemp-system project root directory

## Quick Start

From the project root directory (`simtemp-system/`):

```bash
# List all active QEMU sessions
./simtemp/scripts/dev-cli/qemu-tool list

# Get detailed status of a session
./simtemp/scripts/dev-cli/qemu-tool status <PID>

# Access QEMU monitor interactively
./simtemp/scripts/dev-cli/qemu-tool monitor <PID>

# Execute commands in guest system
./simtemp/scripts/dev-cli/qemu-tool guest <PID> "lsmod"

# Open interactive guest shell
./simtemp/scripts/dev-cli/qemu-tool shell <PID>
```
./qemu-tool guest 1234 "lsmod"                                          # Módulos cargados
./qemu-tool guest 1234 "insmod /tmp/prebuild/simtemp-driver/nxp_simtemp.ko"  # Cargar módulo
./qemu-tool guest 1234 "dmesg | tail -5"                               # Mensajes del kernel
```

### 3. Monitoreo del Hypervisor
```bash
./qemu-tool monitor 1234 "info cpus"      # Info de CPUs
./qemu-tool monitor 1234 "info memory"    # Info de memoria
./qemu-tool monitor 1234 "info version"   # Versión de QEMU
```

### 4. Desarrollo Interactivo
```bash
./qemu-tool shell 1234                    # Shell del guest para pruebas manuales
./qemu-tool monitor 1234                  # Monitor para control del hypervisor
```

## Estructura de Marcadores

Los scripts leen información de sesiones desde archivos marker:

### Compartido: `/tmp/qemu_session_active.marker`
```json
{
  "pid": 1234567,
  "started_at": 1761252095.6474056,
  "started_by": "test_utils.py",
  "test_name": "test_name",
  "monitor_port": 43919,
  "monitor_address": "127.0.0.1:43919"
}
```

### Privados: `/tmp/qemu_private_session_<UID>_<PID>.json`
Similar al compartido con `"session_type": "private"`.

## Comandos Útiles

### Monitor QEMU
- `info version` - Versión de QEMU
- `info status` - Estado de la VM (running/paused/etc)
- `info cpus` - Información de CPUs virtuales
- `info memory` - Información de memoria
- `help` - Lista todos los comandos disponibles
- `quit` - Salir del monitor

### Guest (Sistema ARM)
- `lsmod` - Módulos del kernel cargados
- `insmod <path>` - Cargar módulo del kernel
- `rmmod <module>` - Descargar módulo
- `dmesg | tail -N` - Últimos N mensajes del kernel
- `ls /sys/bus/platform/drivers/` - Drivers de plataforma
- `cat /proc/modules` - Info detallada de módulos
- `uname -a` - Información del sistema

## Requisitos

- Python 3.6+
- Acceso a los archivos marker en `/tmp/`
- Procesos QEMU con monitor telnet habilitado
- Módulo `test_utils.py` para funcionalidad del guest

## Notas Técnicas

### Deprecation Warning
Los scripts usan `telnetlib` que está deprecado en Python 3.13+. En futuras versiones se migrará a `socket` directo.

### Seguridad
- Los puertos del monitor solo escuchan en localhost (127.0.0.1)
- Los marcadores incluyen UID del usuario para aislamiento
- Solo para uso en entornos de desarrollo

### Limitaciones
- Timeout fijo para comandos (configurable en algunos scripts)
- Output buffering puede afectar comandos largos
- Requiere que QEMU esté configurado con monitor telnet

## Ejemplos Avanzados

### Script de Automatización
```bash
#!/bin/bash
# Verificar módulo simtemp en todas las sesiones activas

for pid in $(./qemu-tool list | grep "PID:" | cut -d' ' -f2); do
    echo "=== Verificando sesión $pid ==="
    ./qemu-tool guest $pid "lsmod | grep nxp || echo 'No module loaded'"
done
```

### Monitoreo Continuo
```bash
#!/bin/bash
# Monitorear estado de QEMU cada 30 segundos

while true; do
    clear
    echo "=== Estado QEMU $(date) ==="
    ./qemu-tool list
    sleep 30
done
```

## Troubleshooting

### "No se encontraron sesiones activas"
- Verificar que hay procesos QEMU corriendo: `ps aux | grep qemu`
- Verificar marcadores: `ls -la /tmp/qemu_*`

### "Error conectando al monitor"
- Verificar que el puerto esté abierto: `netstat -ln | grep <puerto>`
- Verificar que QEMU tenga monitor habilitado

### "Error importando test_utils"
- Ejecutar desde el directorio raíz del proyecto
- Verificar que `simtemp/tests/test_utils.py` existe

Para más información, ver `docs/QEMU_SESSION_ACCESS.md`.