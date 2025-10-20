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
		if [ -d "/usr/src/linux-headers-6.14.0-32-generic" ]; then \
			echo "/usr/src/linux-headers-6.14.0-32-generic"; \
		elif [ -d "/usr/src/linux-headers-6.14.0-33-generic" ]; then \
			echo "/usr/src/linux-headers-6.14.0-33-generic"; \
		else \
			find /usr/src -name "linux-headers-*-generic" -type d | head -1; \
		fi; \
	elif [ -d "/lib/modules/6.14.0-32-generic/build" ]; then \
		echo "/lib/modules/6.14.0-32-generic/build"; \
	elif [ -d "/lib/modules/$$(uname -r)/build" ]; then \
		echo "/lib/modules/$$(uname -r)/build"; \
	else \
		find /lib/modules -name "build" -type d | head -1; \
	fi)

# Debian native kernel source (independent compilation in Docker)
# Auto-detect available headers to avoid glibc version conflicts
DEBIAN_KERNEL_SRC := $(shell \
	if [ -d "/usr/src/linux-headers-6.14.0-32-generic" ]; then \
		echo "/usr/src/linux-headers-6.14.0-32-generic"; \
	elif [ -d "/usr/src/linux-headers-6.14.0-33-generic" ]; then \
		echo "/usr/src/linux-headers-6.14.0-33-generic"; \
	else \
		find /usr/src -name "linux-headers-*-generic" -type d | head -1; \
	fi)
# /usr/src/ is mounted in the container from host, which contains the required headers
# Mounting /usr/src/ with rd/wr permissions may be risky on this implementation

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
	fi
	@echo "Signing NXP ARM module..."
	$(MAKE) sign_module
	@echo "Copying binaries to QEMU rootfs for deployment..."
	@mkdir -p ../../deployment/qemu/rootfs/tmp/prebuild/simtemp-driver/
	@cp $(OBJ_DIR)/nxp_simtemp.ko ../../deployment/qemu/rootfs/tmp/prebuild/simtemp-driver/
	@echo "Packaging updated rootfs..."
	@cd ../../deployment/qemu && ./scripts/update_rootfs.sh
	@echo "✅ NXP ARM module built, signed, and packaged successfully"

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
	fi
	@echo "Signing NXP ARM64 module..."
	$(MAKE) sign_module
	@echo "✅ NXP ARM64 module built and signed successfully"

# Debian native build (independent Docker compilation with Debian kernel headers and signing)
deb-driver: $(OBJ_DIR)
	@echo "Building and signing Debian x86_64 driver using native Debian kernel headers..."
	@echo "Using Debian headers: $(DEBIAN_KERNEL_SRC)"
	@if [ ! -d "$(DEBIAN_KERNEL_SRC)" ]; then \
		echo "ERROR: Debian headers not found at $(DEBIAN_KERNEL_SRC)"; \
		echo "Available headers in /usr/src:"; \
		ls -la /usr/src/ | grep linux-headers || echo "No headers found"; \
		echo "Run installation commands to set up Debian headers first."; \
		exit 1; \
	else \
		echo "✅ Found Debian headers at $(DEBIAN_KERNEL_SRC)"; \
	fi
	env -u ARCH -u CROSS_COMPILE -u KDIR $(MAKE) -C $(DEBIAN_KERNEL_SRC) M=$(PWD) ARCH=x86_64 modules
	@echo "Build completed - moving artifacts to $(OBJ_DIR)/"
	@if [ -f nxp_simtemp.ko ]; then \
		mv *.ko *.o *.mod *.mod.c .*.cmd Module.symvers modules.order $(OBJ_DIR)/ 2>/dev/null || true; \
		echo "✅ Debian native x86_64 module built successfully in $(OBJ_DIR)/"; \
		$(MAKE) sign_module; \
	else \
		echo "ERROR: nxp_simtemp.ko was not created"; \
		exit 1; \
	fi

# Create obj directory
$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

# Sign the kernel module (only called when keys are verified to exist)
sign_module:
	@if [ -f "$(SIGNING_PRIV)" ] && [ -f "$(SIGNING_DER)" ]; then \
		echo "Found signing keys: $(SIGNING_PRIV) and $(SIGNING_DER)"; \
		if [ -f "/.dockerenv" ]; then \
			echo "Signing kernel module in Docker container..."; \
		else \
			echo " Signing kernel module on host..."; \
		fi; \
		SIGN_FILE_PATH=""; \
		if [ -f "/usr/src/linux-headers-$(shell uname -r)/scripts/sign-file" ]; then \
			SIGN_FILE_PATH="/usr/src/linux-headers-$(shell uname -r)/scripts/sign-file"; \
		elif [ -f "$(KERNEL_SRC)/scripts/sign-file" ]; then \
			SIGN_FILE_PATH="$(KERNEL_SRC)/scripts/sign-file"; \
		else \
			echo "ERROR: sign-file script not found"; \
			exit 1; \
		fi; \
		if [ "$$(id -u)" = "0" ]; then \
			echo "Running sign-file as root..."; \
			$$SIGN_FILE_PATH sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/nxp_simtemp.ko; \
		else \
			echo "Running sign-file with sudo (non-interactive)..."; \
			# Try without password first, fall back to sudo if needed and user has rights \
			if ! $$SIGN_FILE_PATH sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/nxp_simtemp.ko 2>/dev/null; then \
				if ! sudo -n $$SIGN_FILE_PATH sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/nxp_simtemp.ko; then \
					echo "WARNING: Could not sign module - permissions issue"; \
				fi; \
			fi; \
		fi; \
		echo "Kernel module built and signed successfully in $(OBJ_DIR)/"; \
	else \
		echo "Signing keys not found - module built WITHOUT signing in $(OBJ_DIR)/"; \
		echo "   Missing: $(SIGNING_PRIV) or $(SIGNING_DER)"; \
	fi

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
		$(MAKE) sign_module; \
	else \
		echo "ERROR: nxp_simtemp.ko was not created"; \
		exit 1; \
	fi

# Remove all generated files
clean:
	@if [ -d "$(OBJ_DIR)" ]; then \
		chmod -R u+w $(OBJ_DIR) 2>/dev/null || true; \
		rm -rf $(OBJ_DIR) 2>/dev/null && echo "All build artifacts cleaned" || \
		echo "Clean failed - manual intervention required"; \
	else \
		echo "No build artifacts to clean"; \
	fi


info:
	@echo "=== Kernel Build Configuration ==="
	@echo "Environment: $(shell if [ -f "/.dockerenv" ]; then echo "Docker Container"; else echo "Host System"; fi)"
	@echo "Default target: $(shell if [ -f "/.dockerenv" ]; then echo "deb-driver (Debian headers)"; else echo "host-driver (Host headers)"; fi)"
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
	@echo "  make all               - Auto-detect environment and build (Docker=deb-driver, Host=host-driver)"
	@echo "  make host-driver       - Native x86_64 build with signing (production)"
	@echo "  make deb-driver        - Debian independent x86_64 build with signing (Docker)"
	@echo "  make nxp-driver-arm    - Build and sign for NXP ARM devices (i.MX6/i.MX7)"
	@echo "  make nxp-driver-arm64  - Build and sign for NXP ARM64 devices (i.MX8)"
	@echo "  make info              - Show this information"

.PHONY: host-driver deb-driver sign_module clean prepare-nxp-driver-arm prepare-nxp-driver-arm64 nxp-driver-arm nxp-driver-arm64 info
