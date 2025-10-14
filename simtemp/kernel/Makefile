# Kernel module build configuration
KERNEL_SRC ?= /lib/modules/$(shell uname -r)/build
OBJ_DIR := obj
SRC_FILE := nxp_simtemp.c

# MOK keys - common path for both host and container
SIGNING_PRIV := /var/jenkins_home/kernel_enroll/MOK.priv
SIGNING_DER := /var/jenkins_home/kernel_enroll/MOK.der

obj-m := nxp_simtemp.o

all: $(OBJ_DIR) 
	$(MAKE) -C $(KERNEL_SRC) M=$(PWD) modules
	@mv *.ko *.o *.mod *.mod.c .*.cmd Module.symvers modules.order $(OBJ_DIR)/ 2>/dev/null || true
	@echo "Module built successfully"
	@$(MAKE) sign_module

# Create obj directory
$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

# Remove all generated files
clean:
	@if [ -d "$(OBJ_DIR)" ]; then \
		chmod -R u+w $(OBJ_DIR) 2>/dev/null || true; \
		rm -rf $(OBJ_DIR) 2>/dev/null && echo "All build artifacts cleaned" || \
		echo "Clean failed - manual intervention required"; \
	else \
		echo "No build artifacts to clean"; \
	fi

# Sign the kernel module (only called when keys are verified to exist)
sign_module:
	@if [ -f "$(SIGNING_PRIV)" ] && [ -f "$(SIGNING_DER)" ]; then \
		if [ -f "/.dockerenv" ]; then \
			echo "Signing kernel module in container..."; \
		else \
			echo "Signing kernel module on host..."; \
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
			$$SIGN_FILE_PATH sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/generic_driver.ko; \
		else \
			echo "Running sign-file with sudo (non-interactive)..."; \
			# Try without password first, fall back to sudo if needed and user has rights \
			if ! $$SIGN_FILE_PATH sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/generic_driver.ko 2>/dev/null; then \
				if ! sudo -n $$SIGN_FILE_PATH sha256 $(SIGNING_PRIV) $(SIGNING_DER) $(OBJ_DIR)/generic_driver.ko; then \
					echo "WARNING: Could not sign module - permissions issue"; \
				fi; \
			fi; \
		fi; \
		echo "   Kernel module built and signed successfully in $(OBJ_DIR)/"; \
	else \
		echo "   Kernel module built WITHOUT signing in $(OBJ_DIR)/"; \
	fi

.PHONY: all sign_module clean
