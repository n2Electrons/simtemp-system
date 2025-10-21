# Kernel module build configuration
# Auto-detects: 1) NXP sysroot (hw), 2) Generic headers (dev), 3) linux-imx (qemu)
# Use ../scripts/nxp_prepare_headers_imx.sh for NXP hardware cross-compilation

# Check for NXP environment prepared by nxp_prepare_headers_imx.sh
-include ../scripts/imx-env.mk

# Due to specigic NXP implementation for embedded boards at Linux and header level,
# scripting was implemented to redirect to NXP cloned sources
#
# References:
# Yocto mailing, linux-imx-headers e ioctl mismatches, from https://lists.yoctoproject.org/g/meta-freescale/topic/linux_imx_headers_and_ioctl/72917920
# i.MX Linux kernel header installation (NXP forun) from https://community.nxp.com/t5/i-MX-Processors/iMX6-linux-kernel-header-installation/td-p/224713
NXP_KERNEL_SRC := $(shell \
	if [ -f "../scripts/imx-env.sh" ]; then \
		bash -c 'cd ../scripts && source ./imx-env.sh && echo "$$KDIR"'; \
	else \
		echo "/home/jorge/challenge-2509/simtemp-system/deployment/qemu/linux-imx-5.10"; \
	fi)

# Host kernel source detection - supports both Ubuntu host and Debian Jenkins container
HOST_KERNEL_SRC := $(shell \
	if [ -f "/.dockerenv" ]; then \
		echo "/usr/src/linux-headers-6.14.0-32-generic"; \
	elif [ -d "/lib/modules/6.14.0-32-generic/build" ]; then \
		echo "/lib/modules/6.14.0-32-generic/build"; \
	elif [ -d "/lib/modules/$$(uname -r)/build" ]; then \
		echo "/lib/modules/$$(uname -r)/build"; \
	else \
		find /lib/modules -name "build" -type d | head -1; \
	fi)

# Debian Docker build with Ubuntu headers (mounted from host)
# Force use of Ubuntu 6.14.0-32-generic headers for Docker compilation
DEBIAN_KERNEL_SRC := $(shell \
	if [ -f "/.dockerenv" ]; then \
		echo "/usr/src/linux-headers-6.14.0-32-generic"; \
	else \
		echo "/usr/src/linux-headers-generic"; \
	fi)
# Use Ubuntu headers mounted in Docker with Debian toolchain

# Legacy KERNEL_SRC for info display (uses NXP when available)
KERNEL_SRC := $(NXP_KERNEL_SRC)
OBJ_DIR := obj
SRC_FILE := nxp_simtemp.c

# MOK keys - common path for both host and container
SIGNING_PRIV := /var/jenkins_home/kernel_enroll/MOK.priv
SIGNING_DER := /var/jenkins_home/kernel_enroll/MOK.der

obj-m := nxp_simtemp.o

# Default target - Auto-detect environment (Docker vs Host)
all: $(shell if [ -f "/.dockerenv" ]; then echo "deb-driver"; else echo "host-driver"; fi)

# Use explicit targets: 'make host-driver' for native x86_64, 'make nxp-driver-arm' for cross-compilation
# All targets build signed kernel modules for production deployment

# NXP i.MX cross-compilation targets
prepare-nxp-driver-arm:
	@echo "Preparing NXP ARM (i.MX6/i.MX7) cross-compilation environment..."
	@bash -c 'cd ../scripts && ./nxp_prepare_headers_imx.sh --arch arm --modules'
	@echo "✅ NXP ARM environment ready. Use 'make nxp-driver-arm' to build."

nxp-driver-arm: prepare-nxp-driver-arm $(OBJ_DIR)
	@echo "Building and signing NXP ARM module..."
	bash -c 'cd ../scripts && source ./imx-env.sh && cd ../kernel && \
	$(MAKE) -C $$KDIR ARCH=$$ARCH CROSS_COMPILE=$$CROSS_COMPILE M=$(PWD) modules'
	@echo "Build completed - moving artifacts to $(OBJ_DIR)/"
	@if [ -f nxp_simtemp.ko ]; then \
		mv *.ko *.o *.mod *.mod.c .*.cmd Module.symvers modules.order $(OBJ_DIR)/ 2>/dev/null || true; \
		echo "✅ NXP ARM module built successfully in $(OBJ_DIR)/"; \
	else \
		echo "ERROR: nxp_simtemp.ko was not created"; \
		exit 1; \
	fi
	$(call sign_module_inline)
	@echo "✅ NXP ARM module built and signed successfully"

prepare-nxp-driver-arm64:
	@echo "Preparing NXP ARM64 (i.MX8) cross-compilation environment..."
	@echo "Note: ARM64 NXP setup not yet implemented"
	@false

nxp-driver-arm64: prepare-nxp-driver-arm64 $(OBJ_DIR)
	@echo "Building and signing NXP ARM64 module..."
	bash -c 'cd ../scripts && source ./imx-env.sh && cd ../kernel && \
	$(MAKE) -C $$KDIR ARCH=$$ARCH CROSS_COMPILE=$$CROSS_COMPILE M=$(PWD) modules'
	@echo "Build completed - moving artifacts to $(OBJ_DIR)/"
	@if [ -f nxp_simtemp.ko ]; then \
		mv *.ko *.o *.mod *.mod.c .*.cmd Module.symvers modules.order $(OBJ_DIR)/ 2>/dev/null || true; \
		echo "✅ NXP ARM64 module built successfully in $(OBJ_DIR)/"; \
	else \
		echo "ERROR: nxp_simtemp.ko was not created"; \
		exit 1; \
	fi
	$(call sign_module_inline)
	@echo "✅ NXP ARM64 module built and signed successfully"

# Debian Docker build for x86_64 testing
deb-driver: $(OBJ_DIR)
	@echo "Building Debian x86_64 driver for testing..."
	@echo "Using Ubuntu headers: $(DEBIAN_KERNEL_SRC)"
	@if [ ! -d "$(DEBIAN_KERNEL_SRC)" ]; then \
		echo "ERROR: Ubuntu headers not found at $(DEBIAN_KERNEL_SRC)"; \
		echo "Available headers:"; \
		find /usr/src -name "linux-headers-*" -type d | head -5; \
		exit 1; \
	else \
		echo "✅ Found Ubuntu headers at $(DEBIAN_KERNEL_SRC)"; \
	fi
	@echo "Compiling with Debian toolchain..."
	env -u ARCH -u CROSS_COMPILE -u KDIR $(MAKE) -C $(DEBIAN_KERNEL_SRC) M=$(PWD) ARCH=x86_64 modules
	@echo "Build completed - moving artifacts to $(OBJ_DIR)/"
	@if [ -f nxp_simtemp.ko ]; then \
		mv *.ko *.o *.mod *.mod.c .*.cmd Module.symvers modules.order $(OBJ_DIR)/ 2>/dev/null || true; \
		echo "✅ Debian x86_64 module built successfully for testing in $(OBJ_DIR)/"; \
	else \
		echo "ERROR: nxp_simtemp.ko was not created"; \
		exit 1; \
	fi
	$(call sign_module_inline)

# Create obj directory
$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

# Sign module inline (without recursive make call) - used by deb-driver and host-driver
define sign_module_inline
	@echo "Signing kernel module..."
	@if [ -f "$(SIGNING_PRIV)" ] && [ -f "$(SIGNING_DER)" ]; then \
		echo "Found signing keys: $(SIGNING_PRIV) and $(SIGNING_DER)"; \
		if [ -f "/.dockerenv" ]; then \
			echo "Signing kernel module in Docker container..."; \
		else \
			echo "Signing kernel module on host..."; \
		fi; \
		echo "Running sign-file as root..."; \
		if [ -f "/.dockerenv" ]; then \
			/usr/src/linux-headers-$$(uname -r)/scripts/sign-file sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/nxp_simtemp.ko; \
		else \
			if [ "$$(id -u)" = "0" ]; then \
				/usr/src/linux-headers-$$(uname -r)/scripts/sign-file sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/nxp_simtemp.ko; \
			else \
				sudo /usr/src/linux-headers-$$(uname -r)/scripts/sign-file sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/nxp_simtemp.ko; \
			fi; \
		fi; \
		echo "Kernel module built and signed successfully in $(OBJ_DIR)/"; \
	else \
		echo "Signing keys not found - module built WITHOUT signing in $(OBJ_DIR)/"; \
	fi
endef

# Host x86_64 native compilation with signing (production build)
host-driver: $(OBJ_DIR)
	@echo "Building and signing host x86_64 driver using native kernel headers..."
	@echo "Using host headers: $(HOST_KERNEL_SRC)"
	@if [ ! -d "$(HOST_KERNEL_SRC)" ]; then \
		echo "ERROR: Host headers not found at $(HOST_KERNEL_SRC)"; \
		echo "Available kernel modules:"; \
		ls -la /lib/modules/ | head -5 || echo "No modules found"; \
		exit 1; \
	else \
		echo "✅ Found host headers at $(HOST_KERNEL_SRC)"; \
	fi
	env -u ARCH -u CROSS_COMPILE -u KDIR $(MAKE) -C $(HOST_KERNEL_SRC) M=$(PWD) ARCH=x86_64 modules
	@echo "Build completed - moving artifacts to $(OBJ_DIR)/"
	@if [ -f nxp_simtemp.ko ]; then \
		mv *.ko *.o *.mod *.mod.c .*.cmd Module.symvers modules.order $(OBJ_DIR)/ 2>/dev/null || true; \
		echo "✅ Host x86_64 module built successfully in $(OBJ_DIR)/"; \
	else \
		echo "ERROR: nxp_simtemp.ko was not created"; \
		exit 1; \
	fi
	$(call sign_module_inline)

# Remove all generated files
clean:
	@echo "Cleaning build artifacts..."
	@if [ -d "$(OBJ_DIR)" ]; then \
		echo "Removing $(OBJ_DIR) directory and contents..."; \
		if [ -f "/.dockerenv" ]; then \
			echo "Docker environment detected - using root permissions"; \
			chmod -R u+w $(OBJ_DIR) 2>/dev/null || true; \
			rm -rf $(OBJ_DIR) 2>/dev/null || { \
				echo "ERROR: Failed to remove $(OBJ_DIR) in Docker"; \
				ls -la $(OBJ_DIR) 2>/dev/null || true; \
				exit 1; \
			}; \
		elif [ "$$(id -u)" = "0" ]; then \
			echo "Running as root - direct removal"; \
			chmod -R u+w $(OBJ_DIR) 2>/dev/null || true; \
			rm -rf $(OBJ_DIR) 2>/dev/null || { \
				echo "ERROR: Failed to remove $(OBJ_DIR) as root"; \
				ls -la $(OBJ_DIR) 2>/dev/null || true; \
				exit 1; \
			}; \
		else \
			echo "Running as user - trying with sudo"; \
			chmod -R u+w $(OBJ_DIR) 2>/dev/null || sudo chmod -R u+w $(OBJ_DIR) 2>/dev/null || true; \
			rm -rf $(OBJ_DIR) 2>/dev/null || sudo rm -rf $(OBJ_DIR) 2>/dev/null || { \
				echo "ERROR: Failed to remove $(OBJ_DIR) with user/sudo permissions"; \
				ls -la $(OBJ_DIR) 2>/dev/null || true; \
				echo "Manual cleanup required: sudo rm -rf $(OBJ_DIR)"; \
				exit 1; \
			}; \
		fi; \
		echo "Build artifacts cleaned successfully"; \
	else \
		echo "No build artifacts to clean"; \
	fi
	@# Also clean any stray files in current directory
	@rm -f *.ko *.o *.mod *.mod.c .*.cmd Module.symvers modules.order 2>/dev/null || true


info:
	@echo "=== Kernel Build Configuration ==="
	@echo "Environment: $(shell if [ -f "/.dockerenv" ]; then echo "Docker Container"; else echo "Host System"; fi)"
	@echo "Default target: $(shell if [ -f "/.dockerenv" ]; then echo "deb-driver (x86_64 for testing)"; else echo "host-driver (Ubuntu native)"; fi)"
	@echo ""
	@echo "Auto-detected paths:"
	@echo "  HOST_KERNEL_SRC: $(HOST_KERNEL_SRC)"
	@echo "  DEBIAN_KERNEL_SRC: $(DEBIAN_KERNEL_SRC)"
	@echo "  KERNEL_SRC (NXP): $(KERNEL_SRC)"
	@if [ -f "../scripts/imx-env.sh" ]; then \
		echo "NXP Environment: Available (source ../scripts/imx-env.sh)"; \
		bash -c 'cd ../scripts && source ./imx-env.sh && echo "  ARCH=$$ARCH, CROSS_COMPILE=$$CROSS_COMPILE"'; \
	else \
		echo "NXP Environment: Not prepared (run 'make prepare-nxp-arm' or 'make prepare-nxp-arm64')"; \
	fi
	@echo ""
	@echo "Available targets:"
	@echo "  make all               - Auto-detect environment (Docker=deb-driver, Host=host-driver)"
	@echo "  make host-driver       - Native x86_64 build with signing (Ubuntu host)"
	@echo "  make deb-driver        - Build x86_64 driver for testing (Docker container)"
	@echo "  make nxp-driver-arm    - Build and sign for NXP ARM devices (i.MX6/i.MX7)"
	@echo "  make nxp-driver-arm64  - Build and sign for NXP ARM64 devices (i.MX8)"
	@echo "  make info              - Show this information"

.PHONY: host-driver deb-driver clean prepare-nxp-driver-arm prepare-nxp-driver-arm64 nxp-driver-arm nxp-driver-arm64 info
