# NXP i.MX Cross-Compilation Integration

This document explains how to build the `nxp_simtemp.ko` kernel module for NXP i.MX hardware using the integrated cross-compilation system.

---

## 🎯 **Quick Start**

### For i.MX6 / i.MX7 (ARM 32-bit)
```bash
cd simtemp/kernel
make prepare-nxp-arm    # Setup cross-compilation environment
make nxp-arm           # Build nxp_simtemp.ko for ARM
```

### For i.MX8 (ARM 64-bit)  
```bash
cd simtemp/kernel
make prepare-nxp-arm64  # Setup cross-compilation environment
make nxp-arm64         # Build nxp_simtemp.ko for ARM64
```

---

## 📋 **Available Make Targets**

| Target | Description |
|--------|-------------|
| `make info` | Show current build configuration and available targets |
| `make simple` | Native x86_64 build for development/testing |
| `make all` | Native build with module signing |
| `make prepare-nxp-arm` | Setup ARM cross-compilation (i.MX6/i.MX7) |
| `make prepare-nxp-arm64` | Setup ARM64 cross-compilation (i.MX8) |
| `make nxp-arm` | Build module for NXP ARM devices |
| `make nxp-arm64` | Build module for NXP ARM64 devices |
| `make clean` | Clean build artifacts |

---

## 🔍 **Build Priority & Auto-Detection**

The Makefile automatically detects the best kernel source in this order:

1. **NXP Environment** (`$KDIR` from `../scripts/imx-env.sh`)
2. **Generic Headers** (`6.14.0-32-generic`, `6.8.0-85-generic`)  
3. **Workspace linux-imx** (`../../deployment/qemu/linux-imx-5.10`)
4. **Current kernel** (`uname -r`)

Use `make info` to see which source is currently detected.

---

## 🛠️ **Cross-Compilation Details**

### What `prepare-nxp-arm` does:
1. **Detects workspace**: Uses existing `linux-imx-5.10` if available
2. **Installs headers**: `make headers_install` for userspace 
3. **Prepares modules**: `make modules_prepare` for kernel development
4. **Generates environment**: Creates `../scripts/imx-env.sh` and `imx-env.mk`
5. **Configures toolchain**: Uses `arm-linux-gnueabihf-` automatically

### Generated files:
- `../scripts/imx-env.sh` - Shell environment variables
- `../scripts/imx-env.mk` - Makefile-compatible variables  
- `../scripts/sysroot-arm/` - Cross-compilation sysroot

---

## 🎯 **Development Workflow**

### 1. Daily Development (Native)
```bash
make simple          # Fast native build for testing
make info           # Check configuration
```

### 2. NXP Hardware Testing (Cross-compilation)
```bash
make prepare-nxp-arm    # One-time setup
make nxp-arm           # Build for target hardware
# Deploy nxp_simtemp.ko to i.MX device
```

### 3. Multi-architecture Builds
```bash
make simple          # x86_64 for development  
make nxp-arm        # ARM for i.MX6/i.MX7
make nxp-arm64      # ARM64 for i.MX8
```

---

## 🔧 **Manual Cross-Compilation**

If you need manual control:

```bash
# Setup environment
cd ../scripts
source ./imx-env.sh

# Manual build
cd ../kernel
make -C $KDIR ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE M=$PWD modules
```

---

## ✅ **Verification**

Check successful cross-compilation:

```bash
make nxp-arm
file nxp_simtemp.ko
# Expected: ELF 32-bit LSB relocatable, ARM, EABI5, version 1 (SYSV)

make nxp-arm64  
file nxp_simtemp.ko
# Expected: ELF 64-bit LSB relocatable, ARM aarch64, version 1 (SYSV)
```

---

## 📚 **Related Documentation**

- `../scripts/nxp_prepare_headers_imx_usage.md` - Detailed script usage
- `../../deployment/qemu/QEMU_FOR_I.MX6.md` - QEMU testing with linux-imx
- `Makefile` - Build system implementation

---

## 🚨 **Prerequisites**

### ARM Cross-compilation:
```bash
sudo apt install gcc-arm-linux-gnueabihf
```

### ARM64 Cross-compilation:
```bash  
sudo apt install gcc-aarch64-linux-gnu
```

### Build tools:
```bash
sudo apt install build-essential git make
```

The `prepare-nxp-*` targets will check and report missing dependencies.