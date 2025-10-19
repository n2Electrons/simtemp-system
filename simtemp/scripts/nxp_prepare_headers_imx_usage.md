# Basic Usage — prepare_headers_imx.sh

This script automates setup of **linux-imx** kernel headers and environment variables for cross-compilation on Debian/Ubuntu hosts targeting ARM or ARM64 i.MX devices.

---

## 1. Make the script executable
```bash
chmod +x prepare_headers_imx.sh
```

---

## 2. Run for ARM (i.MX6 / i.MX7)
```bash
./prepare_headers_imx.sh --arch arm
```
- Clones the NXP `linux-imx` kernel (`lf-5.10.72-2.2.0` by default)  
- Installs kernel headers to `./sysroot-arm/usr/include`  
- Generates environment file `imx-env.sh`

---

## 3. Run for ARM64 (i.MX8)
```bash
./prepare_headers_imx.sh --arch arm64
```
- Uses 64-bit toolchain `aarch64-linux-gnu-`  
- Installs headers to `./sysroot-arm64`  

---

## 4. Optional parameters

| Option | Description |
|--------|--------------|
| `--kernel-tag TAG` | Select a specific git tag (default: `lf-5.10.72-2.2.0`) |
| `--kernel-src DIR` | Use an existing local linux-imx source tree |
| `--sysroot DIR` | Destination for header installation |
| `--toolchain-prefix PREFIX` | Override toolchain prefix |
| `--modules` | Also run `make modules_prepare` to allow out-of-tree module builds |
| `--jobs N` | Set parallel job count for build steps |

Example:
```bash
./prepare_headers_imx.sh --arch arm --modules --jobs 8
```

---

## 5. Load environment after setup
```bash
source ./imx-env.sh
```

Exports:
```bash
ARCH=arm
CROSS_COMPILE=arm-linux-gnueabihf-
SYSROOT=/path/to/sysroot-arm
KDIR=/path/to/linux-imx
```

---

## 6. Integration with simtemp project

### Quick start for NXP hardware
```bash
# Prepare environment for ARM (i.MX6/i.MX7)
cd simtemp/kernel
make prepare-nxp-arm

# Build nxp_simtemp.ko for ARM
make nxp-arm

# Or for ARM64 (i.MX8)
make prepare-nxp-arm64
make nxp-arm64
```

### Check configuration
```bash
make info    # Shows detected kernel source and NXP environment status
```

---

## 7. Manual build commands

### User-space binary
```bash
${CROSS_COMPILE}gcc -o hello.$ARCH hello.c --sysroot=$SYSROOT
```

### External kernel module
```bash
make -C $KDIR ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE M=$PWD modules
```

---

## 8. Workspace integration

The script automatically:
- **Detects existing linux-imx**: Uses `../../deployment/qemu/linux-imx-5.10` if available
- **Generates Makefile variables**: Creates `imx-env.mk` for automatic inclusion
- **Integrates with build system**: Makefile targets use prepared environment seamlessly

Generated files:
- `imx-env.sh` - Shell environment variables
- `imx-env.mk` - Makefile-compatible variables
