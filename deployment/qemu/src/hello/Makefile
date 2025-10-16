# Makefile for Hello World ARM application
# Copyright (c) Jorge Rodriguez Moreno

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
STRIP = $(CROSS_COMPILE)strip

# Compiler flags
CFLAGS = -Wall -Wextra -O2 -static
LDFLAGS = -static

# Source and target
SRC = hello_world.c
TARGET = hello_world
TARGET_STRIPPED = hello_world_stripped

# Build directories
BUILD_DIR = build
DEPLOY_DIR = ../../deployment/qemu

.PHONY: all clean install verify help

# Default target
all: $(TARGET)

# Build the ARM binary
$(TARGET): $(SRC)
	@echo "Building Hello World for ARM..."
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC) $(LDFLAGS)
	@echo "ARM binary created: $(TARGET)"

# Create stripped version for deployment
stripped: $(TARGET)
	@echo "Creating stripped version..."
	$(STRIP) -o $(TARGET_STRIPPED) $(TARGET)
	@echo "Stripped binary created: $(TARGET_STRIPPED)"

# Install to deployment directory
install: $(TARGET)
	@echo "Installing to deployment directory..."
	@mkdir -p $(DEPLOY_DIR)
	cp $(TARGET) $(DEPLOY_DIR)/
	@echo "Installed: $(DEPLOY_DIR)/$(TARGET)"

# Verify ARM binary
verify: $(TARGET)
	@echo "Verifying ARM binary..."
	file $(TARGET)
	ls -lh $(TARGET)

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(TARGET) $(TARGET_STRIPPED)
	rm -rf $(BUILD_DIR)

# Help target
help:
	@echo "Available targets:"
	@echo "  all      - Build the Hello World ARM binary (default)"
	@echo "  stripped - Create stripped version of the binary"
	@echo "  install  - Install binary to deployment directory"
	@echo "  verify   - Verify the ARM binary architecture"
	@echo "  clean    - Remove build artifacts"
	@echo "  help     - Show this help message"
	@echo ""
	@echo "Environment variables:"
	@echo "  CROSS_COMPILE - Cross-compiler prefix (default: arm-linux-gnueabihf-)"