# Makefile for SimTemp CLI C Implementation

# Compiler and flags
CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -D_POSIX_C_SOURCE=200809L
LDFLAGS = 
LIBS = 

# Directories
SRCDIR = .
OBJDIR = obj
BINDIR = bin

# Target binary
TARGET = simtemp-cli

# Source files
SOURCES = main.c device_ops.c sysfs_config.c remote_ops.c test_mode.c config_file.c
OBJECTS = $(SOURCES:%.c=$(OBJDIR)/%.o)

# Installation paths
PREFIX = /usr/local
BINDIR_INSTALL = $(PREFIX)/bin
MANDIR = $(PREFIX)/share/man/man1

# Build modes
DEBUG_CFLAGS = -g -O0 -DDEBUG
RELEASE_CFLAGS = -O2 -DNDEBUG

# Default to release build
CFLAGS += $(RELEASE_CFLAGS)

# Default target
all: $(BINDIR)/$(TARGET)

# Debug build
debug: CFLAGS = -Wall -Wextra -std=c99 -D_POSIX_C_SOURCE=200809L $(DEBUG_CFLAGS)
debug: $(BINDIR)/$(TARGET)

# Create directories
$(OBJDIR):
	mkdir -p $(OBJDIR)

$(BINDIR):
	mkdir -p $(BINDIR)

# Compile source files
$(OBJDIR)/%.o: $(SRCDIR)/%.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

# Link binary
$(BINDIR)/$(TARGET): $(OBJECTS) | $(BINDIR)
	$(CC) $(OBJECTS) $(LDFLAGS) $(LIBS) -o $@

# Generate dependencies
deps:
	$(CC) -MM $(SOURCES) > .depend

# Include dependencies if they exist
-include .depend

# Clean build artifacts
clean:
	rm -rf $(OBJDIR) $(BINDIR)
	rm -f .depend

# Install binary and documentation
install: $(BINDIR)/$(TARGET)
	install -d $(BINDIR_INSTALL)
	install -m 755 $(BINDIR)/$(TARGET) $(BINDIR_INSTALL)/
	install -d $(MANDIR)
	# install -m 644 $(TARGET).1 $(MANDIR)/ # Man page would go here

# Uninstall
uninstall:
	rm -f $(BINDIR_INSTALL)/$(TARGET)
	rm -f $(MANDIR)/$(TARGET).1

# Create source package
package: clean
	tar -czf simtemp-cli-src.tar.gz *.c *.h Makefile README.md

# Format source code
format:
	clang-format -i *.c *.h

# Static analysis
analyze:
	cppcheck --enable=all --std=c99 *.c

# Run tests (if test files exist)
test: $(BINDIR)/$(TARGET)
	@echo "Running basic functionality tests..."
	./$(BINDIR)/$(TARGET) --version
	./$(BINDIR)/$(TARGET) --help > /dev/null
	@echo "Basic tests passed"

# Show help
help:
	@echo "SimTemp CLI Build System"
	@echo ""
	@echo "Targets:"
	@echo "  all      - Build release binary (default)"
	@echo "  debug    - Build debug binary with symbols"
	@echo "  clean    - Remove build artifacts"
	@echo "  install  - Install binary to system"
	@echo "  uninstall- Remove binary from system"
	@echo "  package  - Create source package"
	@echo "  format   - Format source code"
	@echo "  analyze  - Run static analysis"
	@echo "  test     - Run basic tests"
	@echo "  deps     - Generate dependencies"
	@echo "  help     - Show this help"
	@echo ""
	@echo "Variables:"
	@echo "  CC       - Compiler (default: gcc)"
	@echo "  PREFIX   - Install prefix (default: /usr/local)"
	@echo "  CFLAGS   - Additional compiler flags"
	@echo ""
	@echo "Examples:"
	@echo "  make                    # Build release"
	@echo "  make debug              # Build debug"
	@echo "  make CC=clang           # Use clang compiler"
	@echo "  make PREFIX=/opt/local  # Install to /opt/local"

# Mark phony targets
.PHONY: all debug clean install uninstall package format analyze test help deps