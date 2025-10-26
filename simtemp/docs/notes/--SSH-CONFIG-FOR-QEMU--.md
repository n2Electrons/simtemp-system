# SSH Configuration for QEMU i.MX6 Guest

This document describes the complete SSH setup for remote access to the QEMU i.MX6 (ARM Cortex-A9) guest system, replacing telnet-based access with secure SSH connectivity.

## Overview

The SSH implementation uses Dropbear SSH server with the following features:
- **Authentication**: Public key authentication only (no passwords)
- **PTY Support**: Both UNIX98 and legacy BSD PTY support for interactive sessions
- **Network**: QEMU user networking with port forwarding (host:2222 → guest:22)
- **Security**: Host key verification and secure key management

## SSH Keys Configuration

### Host Key Generation (for Host Machine)
Generate SSH key pair on the host machine for authenticating to the QEMU guest:

```bash
# Generate RSA key pair (recommended)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/qemu_dropbear -C "QEMU-Dropbear-Access"

# Alternative: Generate Ed25519 key pair (more secure, smaller)
ssh-keygen -t ed25519 -f ~/.ssh/qemu_dropbear_ed25519 -C "QEMU-Dropbear-Ed25519"

# Set proper permissions
chmod 600 ~/.ssh/qemu_dropbear
chmod 644 ~/.ssh/qemu_dropbear.pub
```

### Guest authorized_keys Setup
Copy the public key to the guest's authorized_keys file:

```bash
# Create SSH directory in rootfs
mkdir -p deployment/qemu/rootfs/root/.ssh

# Copy public key to guest authorized_keys
cp ~/.ssh/qemu_dropbear.pub deployment/qemu/rootfs/root/.ssh/authorized_keys

# Set proper permissions (will be applied via fakeroot during rootfs build)
chmod 700 deployment/qemu/rootfs/root/.ssh
chmod 600 deployment/qemu/rootfs/root/.ssh/authorized_keys
```

### SSH Key Formats
The `authorized_keys` file should contain one public key per line in OpenSSH format:

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQA... user@hostname
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@hostname
```

### Multiple Key Support
To support multiple users or key types, add multiple lines to authorized_keys:

```bash
# Example authorized_keys with multiple keys
cat >> deployment/qemu/rootfs/root/.ssh/authorized_keys << 'EOF'
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQA... developer1@workstation
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... developer2@laptop
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... ci-system@jenkins
EOF
```

### SSH Client Configuration
Create or update `~/.ssh/config` for convenient access:

```bash
# Add to ~/.ssh/config
cat >> ~/.ssh/config << 'EOF'
Host qemu-guest
    HostName localhost
    Port 2222
    User root
    IdentityFile ~/.ssh/qemu_dropbear
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel QUIET
EOF
```

Then connect simply with: `ssh qemu-guest`

## 2. Dropbear SSH Server Setup

### Cross-Compilation
Dropbear v2022.83 is cross-compiled for ARM architecture as a static binary:

```bash
# Build environment
CROSS_COMPILE=arm-linux-gnueabihf-
export CC="${CROSS_COMPILE}gcc"
export STRIP="${CROSS_COMPILE}strip"

# Configure and build
./configure --host=arm-linux-gnueabihf \
            --disable-zlib \
            --enable-static \
            --disable-wtmp \
            --disable-lastlog
make PROGRAMS="dropbear dropbearkey"
```

### Installation Location
- **Binary**: `deployment/qemu/rootfs/usr/sbin/dropbear`
- **Key Generator**: `deployment/qemu/rootfs/usr/bin/dropbearkey`
- **Host Keys**: Generated at boot in `/etc/dropbear/`
- **Authorized Keys**: `deployment/qemu/rootfs/root/.ssh/authorized_keys`

### Authentication Configuration
- **Public Key Auth**: Enabled
- **Password Auth**: Disabled (`-s` flag)
- **Root Login**: Allowed via SSH keys
- **Host Keys**: RSA, ECDSA, and Ed25519 generated at first boot

## 3. Kernel Configuration

### Required PTY Support
The kernel must support both modern and legacy PTY systems:

```bash
# In build_kernel_imx6_5.10.sh
./scripts/config --enable CONFIG_UNIX98_PTYS
./scripts/config --enable CONFIG_DEVPTS_FS
./scripts/config --enable CONFIG_DEVPTS_MULTIPLE_INSTANCES
./scripts/config --enable CONFIG_LEGACY_PTYS  # Critical for Dropbear
```

### Key Configuration Values
```
CONFIG_UNIX98_PTYS=y
CONFIG_DEVPTS_FS=y
CONFIG_DEVPTS_MULTIPLE_INSTANCES=y
CONFIG_LEGACY_PTYS=y
CONFIG_LEGACY_PTY_COUNT=256
```

---
## **CRITICAL CONFIGURATION REQUIREMENT**

```
┌─────────────────────────────────────┐
│  ⚠️  PTY REQUIRED FOR DROPBEAR      │
│                                     │
│   CONFIG_LEGACY_PTYS=y              │
│   ABSOLUTELY ESSENTIAL!             │
└─────────────────────────────────────┘
```

### **CONFIG_LEGACY_PTYS=y IS ABSOLUTELY ESSENTIAL**

**Dropbear SSH server REQUIRES legacy BSD PTY devices (`/dev/ptyp*`, `/dev/ttyp*`) for PTY allocation.**
**Without this kernel configuration, interactive SSH sessions will FAIL with "No pty was allocated" errors.**

---

## 4. Init Script Configuration (`/init`)

### Device Filesystem Setup
```bash
# Mount devtmpfs first
mount -t devtmpfs devtmpfs /dev 2>/dev/null || mount -t tmpfs -o mode=0755 none /dev

# Mount devpts for SSH pseudo-terminal support
mkdir -p /dev/pts
if ! mount -t devpts devpts /dev/pts -o ptmxmode=0666,mode=620,gid=5,newinstance 2>/dev/null; then
  mount -t devpts devpts /dev/pts -o ptmxmode=0666,mode=620,gid=5 2>/dev/null || mount -t devpts devpts /dev/pts
fi
```

### PTY Device Creation
```bash
# Set up /dev/ptmx as the classic char device
rm -f /dev/ptmx 2>/dev/null || true
mknod -m 666 /dev/ptmx c 5 2 2>/dev/null || true

# Create legacy BSD PTY devices for Dropbear compatibility
# Master devices (ptyp0-ptyp9)
for i in 0 1 2 3 4 5 6 7 8 9; do
  mknod -m 666 /dev/ptyp$i c 2 $i 2>/dev/null || true
done

# Slave devices (ttyp0-ttyp9)
for i in 0 1 2 3 4 5 6 7 8 9; do
  mknod -m 666 /dev/ttyp$i c 3 $i 2>/dev/null || true
done
```

### SSH Host Key Generation
```bash
# Generate RSA host key
if [ ! -f /etc/dropbear/dropbear_rsa_host_key ]; then
    echo "Generating RSA host key..."
    dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key -s 2048
fi

# Generate ECDSA host key
if [ ! -f /etc/dropbear/dropbear_ecdsa_host_key ]; then
    echo "Generating ECDSA host key..."
    dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key -s 256
fi

# Generate Ed25519 host key
if [ ! -f /etc/dropbear/dropbear_ed25519_host_key ]; then
    echo "Generating Ed25519 host key..."
    dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key
fi
```

### Dropbear Service Startup
```bash
# Start dropbear SSH server on port 22
if command -v dropbear >/dev/null 2>&1; then
    mkdir -p /etc/dropbear
    dropbear -p 22 -s
    echo "dropbear started on port 22"
fi
```

## 5. Rootfs and Permissions Setup

### Fakeroot Usage
The rootfs must be built with proper ownership using fakeroot:

```bash
# In update_rootfs.sh
fakeroot bash -c 'cd rootfs && chown -R root:root . && find . | cpio -H newc -o | gzip > ../rootfs.cpio.gz'
```

### Required File Structure
```
rootfs/
├── etc/
│   ├── passwd          # Root user entry
│   ├── shadow          # Root password (disabled)
│   ├── group           # tty:x:5: group for PTY permissions
│   └── dropbear/       # Host keys directory (created at runtime)
├── root/
│   └── .ssh/
│       └── authorized_keys  # SSH public keys for root access
└── usr/
    ├── sbin/
    │   └── dropbear     # SSH server binary
    └── bin/
        └── dropbearkey  # Key generation utility
```

### Key File Permissions
- `/root/.ssh/authorized_keys`: 600 (root:root)
- `/etc/dropbear/`: 755 (root:root)
- Host keys: 600 (root:root, generated at boot)

## 6. SSH Client Configuration

### Quick Connection Commands
Using the SSH keys configured in section 1:

```bash
# Standard options for connecting
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet"

# Interactive session with PTY
ssh -t $SSH_OPTS -p 2222 root@localhost

# Non-interactive command execution
ssh $SSH_OPTS -p 2222 root@localhost "command"

# Using specific key file
ssh -t -i ~/.ssh/qemu_dropbear $SSH_OPTS -p 2222 root@localhost
```

### Alternative Connection Methods
```bash
# Using SSH config (if configured as shown in section 1)
ssh qemu-guest

# Direct connection with embedded options
ssh -t -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 root@localhost
```

### SSH Key Troubleshooting
```bash
# Test SSH key authentication
ssh -v -p 2222 root@localhost  # Verbose output for debugging

# Check key fingerprint
ssh-keygen -lf ~/.ssh/qemu_dropbear.pub

# Verify key is in authorized_keys
cat deployment/qemu/rootfs/root/.ssh/authorized_keys
```

## 7. QEMU Network Configuration

### Port Forwarding Setup
```bash
# In run_qemu.ssh.sh
QEMU_NET_ARGS="-netdev user,id=net0,hostfwd=tcp::2222-:22 -device lan9118,netdev=net0"
```

### Guest Network Configuration
```bash
# Static IP for QEMU user networking
ifconfig eth0 10.0.2.15 up
route add default gw 10.0.2.2
```

## 8. Helper Scripts

### run_qemu.ssh.sh Options
```bash
./scripts/run_qemu.ssh.sh [OPTIONS]

Options:
  --ssh           Enable SSH port forwarding (default: enabled)
  --no-ssh        Disable SSH port forwarding
  --interactive   Use stdio for serial console (default: enabled)
  --no-interactive Use telnet for serial console on port 45455
  --help          Show help message

Default behavior: --ssh --interactive (both SSH and interactive console enabled)
```

### remote_ssh_exec.sh Usage
```bash
# Interactive mode with PTY
./scripts/remote_ssh_exec.sh --interactive

# Execute single command
./scripts/remote_ssh_exec.sh "command"

# Multiple commands with context preservation
./scripts/remote_ssh_exec.sh "cd /tmp && ls -la && pwd"
```

## 9. Troubleshooting

### Common Issues and Solutions

#### PTY Allocation Failures
**Symptom**: "Failed to open any /dev/pty?? devices"
**Solution**: Ensure `CONFIG_LEGACY_PTYS=y` in kernel and legacy PTY devices are created in `/init`

#### Authentication Failures
**Symptom**: "Permission denied (publickey)"
**Solution**: Verify authorized_keys file exists with correct permissions and public key content

#### Connection Refused
**Symptom**: "Connection refused" on port 2222
**Solution**: Check QEMU port forwarding and ensure Dropbear is running on guest port 22

#### Host Key Warnings
**Symptom**: "WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED"
**Solution**: Use `-o UserKnownHostsFile=/dev/null` or clear known_hosts

### Debug Commands
```bash
# Check PTY devices on guest
ls -la /dev/pty* /dev/tty*

# Verify kernel PTY configuration
zcat /proc/config.gz | grep -E 'CONFIG_.*PTY'

# Check Dropbear process
ps aux | grep dropbear

# Monitor SSH connections
# (Dropbear logs appear in kernel messages/dmesg)
```

## 10. Security Considerations

### Best Practices
- **No Password Auth**: Only public key authentication enabled
- **Key Management**: Unique keys per environment/user
- **Host Key Verification**: Disable only for development environments
- **Network Isolation**: QEMU user networking provides NAT isolation
- **Minimal Attack Surface**: Dropbear compiled with minimal features

### Production Recommendations
- Use proper host key verification in production
- Implement key rotation policies
- Consider certificate-based authentication for larger deployments
- Enable logging and monitoring for SSH access

## 11. Testing and Validation

### Verification Steps
1. **Basic Connectivity**: `ssh -p 2222 root@localhost "echo 'SSH working'"`
2. **Interactive PTY**: `ssh -t -p 2222 root@localhost`
3. **Command Execution**: `ssh -p 2222 root@localhost "uname -a"`
4. **Helper Scripts**: `./scripts/remote_ssh_exec.sh --interactive`

### Expected Results
- Exit code 0 for successful connections
- No "Failed to open any /dev/pty?? devices" in logs
- Interactive shell with proper terminal support
- Command output properly captured and returned

---

**Note**: This configuration provides secure, reliable SSH access to the QEMU i.MX6 guest system, supporting both interactive terminal sessions and automated command execution for development and testing workflows.