#!/bin/bash

# Jenkins Container Setup Script with QEMU ARM Emulation Support
# This script creates a Jenkins container configured for embedded ARM Linux testing
# 
# Author: Jorge Rodriguez Moreno
# Date: October 17, 2025
# Repository: simtemp-system
# Branch: f-k1-tc-002-qemu-dt

set -e  # Exit on any error

# Configuration
CONTAINER_NAME="jenkins-3"
JENKINS_IMAGE="jenkins/jenkins:lts"
JENKINS_PORT="8080"
JENKINS_AGENT_PORT="50000"
VOLUME_NAME="jenkins_home-2"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is available"
    
    # Check QEMU
    if ! command -v qemu-system-arm &> /dev/null; then
        print_error "QEMU ARM system emulation is not installed."
        print_error "Install with: sudo apt install qemu-system-arm"
        exit 1
    fi
    print_success "QEMU ARM emulation is available"
    
    # Check QEMU version
    QEMU_VERSION=$(qemu-system-arm --version | head -1)
    print_status "QEMU Version: $QEMU_VERSION"
    
    # Check required directories
    if [ ! -d "/lib/modules" ]; then
        print_error "Kernel modules directory not found: /lib/modules"
        exit 1
    fi
    
    if [ ! -d "/usr/src" ]; then
        print_warning "Kernel source directory not found: /usr/src"
        print_warning "Kernel module compilation may not work properly"
    fi
    
    if [ ! -f "/usr/bin/qemu-system-arm" ]; then
        print_error "QEMU binary not found: /usr/bin/qemu-system-arm"
        exit 1
    fi
    
    if [ ! -d "/lib/x86_64-linux-gnu" ]; then
        print_error "System libraries directory not found: /lib/x86_64-linux-gnu"
        exit 1
    fi
    
    print_success "All prerequisites checked"
}

# Function to verify QEMU functionality
verify_qemu() {
    print_status "Verifying QEMU functionality..."
    
    # Test QEMU can list machines
    if ! qemu-system-arm -M help | grep -q "sabrelite"; then
        print_error "QEMU does not support sabrelite machine type"
        exit 1
    fi
    print_success "QEMU supports required ARM machine types"
    
    # Test QEMU can start (timeout after 2 seconds)
    if timeout 2 qemu-system-arm -M sabrelite -nographic 2>/dev/null; then
        print_success "QEMU can start ARM emulation"
    else
        # Timeout is expected, check exit code
        if [ $? -eq 124 ]; then
            print_success "QEMU can start ARM emulation (timed out as expected)"
        else
            print_error "QEMU failed to start ARM emulation"
            exit 1
        fi
    fi
}

# Function to stop and remove existing container
cleanup_existing() {
    print_status "Cleaning up existing container..."
    
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_status "Stopping existing container: $CONTAINER_NAME"
        docker stop $CONTAINER_NAME 2>/dev/null || true
        
        print_status "Removing existing container: $CONTAINER_NAME"
        docker rm $CONTAINER_NAME 2>/dev/null || true
        
        print_success "Existing container cleaned up"
    else
        print_status "No existing container found"
    fi
}

# Function to create Jenkins volume if it doesn't exist
create_volume() {
    print_status "Checking Jenkins volume..."
    
    if ! docker volume ls --format '{{.Name}}' | grep -q "^${VOLUME_NAME}$"; then
        print_status "Creating Jenkins volume: $VOLUME_NAME"
        docker volume create $VOLUME_NAME
        print_success "Jenkins volume created"
    else
        print_status "Jenkins volume already exists: $VOLUME_NAME"
    fi
}

# Function to create Jenkins container
create_container() {
    print_status "Creating Jenkins container with QEMU support..."
    
    # Prepare mount command
    MOUNT_ARGS=(
        -v "${VOLUME_NAME}:/var/jenkins_home"
        -v "/lib/modules:/lib/modules:ro"
        -v "/usr/src:/usr/src:ro"
        -v "/usr/bin/qemu-system-arm:/usr/bin/qemu-system-arm:ro"
        -v "/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:ro"
        -v "/usr/share/qemu:/usr/share/qemu:ro"
    )
    
    # Add custom kernel enrollment directory if it exists
    KERNEL_ENROLL_DIR="/home/jorge/challenge-2509/kernel_enroll"
    if [ -d "$KERNEL_ENROLL_DIR" ]; then
        MOUNT_ARGS+=(-v "${KERNEL_ENROLL_DIR}:/var/jenkins_home/kernel_enroll:ro")
        print_status "Added kernel enrollment directory mount"
    fi
    
    # Create container
    CONTAINER_ID=$(docker run -d \
        --name $CONTAINER_NAME \
        --restart=unless-stopped \
        -p ${JENKINS_PORT}:8080 \
        -p ${JENKINS_AGENT_PORT}:50000 \
        "${MOUNT_ARGS[@]}" \
        $JENKINS_IMAGE)
    
    print_success "Jenkins container created: $CONTAINER_ID"
}

# Function to wait for Jenkins to start
wait_for_jenkins() {
    print_status "Waiting for Jenkins to start..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec $CONTAINER_NAME curl -s http://localhost:8080/login > /dev/null 2>&1; then
            print_success "Jenkins is running and accessible"
            return 0
        fi
        
        if [ $((attempt % 5)) -eq 0 ]; then
            print_status "Still waiting for Jenkins... (attempt $attempt/$max_attempts)"
        fi
        
        sleep 2
        ((attempt++))
    done
    
    print_error "Jenkins failed to start within expected time"
    return 1
}

# Function to verify container setup
verify_container() {
    print_status "Verifying container setup..."
    
    # Check container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_error "Container is not running"
        return 1
    fi
    print_success "Container is running"
    
    # Check QEMU binary access
    if ! docker exec $CONTAINER_NAME which qemu-system-arm > /dev/null 2>&1; then
        print_error "QEMU binary not accessible in container"
        return 1
    fi
    print_success "QEMU binary is accessible"
    
    # Check QEMU version in container
    CONTAINER_QEMU_VERSION=$(docker exec $CONTAINER_NAME qemu-system-arm --version | head -1)
    print_status "Container QEMU Version: $CONTAINER_QEMU_VERSION"
    
    # Check QEMU can list machines
    if ! docker exec $CONTAINER_NAME qemu-system-arm -M help | grep -q "sabrelite"; then
        print_error "QEMU in container does not support sabrelite machine"
        return 1
    fi
    print_success "QEMU in container supports required machine types"
    
    # Test QEMU functionality
    if docker exec $CONTAINER_NAME timeout 2 qemu-system-arm -M sabrelite -nographic 2>/dev/null; then
        print_success "QEMU functional test passed"
    else
        if [ $? -eq 124 ]; then
            print_success "QEMU functional test passed (timed out as expected)"
        else
            print_error "QEMU functional test failed"
            return 1
        fi
    fi
    
    print_success "Container verification completed successfully"
}

# Function to display connection information
display_info() {
    echo
    print_success "Jenkins container setup completed successfully!"
    echo
    echo "Container Information:"
    echo "  Name: $CONTAINER_NAME"
    echo "  Image: $JENKINS_IMAGE"
    echo "  Status: $(docker inspect --format='{{.State.Status}}' $CONTAINER_NAME)"
    echo
    echo "Access Information:"
    echo "  Jenkins Web UI: http://localhost:${JENKINS_PORT}"
    echo "  Agent Port: ${JENKINS_AGENT_PORT}"
    echo
    echo "Initial Setup:"
    echo "  1. Open http://localhost:${JENKINS_PORT} in your browser"
    echo "  2. Get initial admin password with:"
    echo "     docker exec $CONTAINER_NAME cat /var/jenkins_home/secrets/initialAdminPassword"
    echo "  3. Follow the Jenkins setup wizard"
    echo
    echo "QEMU Testing:"
    echo "  Test QEMU in container:"
    echo "    docker exec $CONTAINER_NAME qemu-system-arm --version"
    echo "    docker exec $CONTAINER_NAME qemu-system-arm -M help | grep sabrelite"
    echo
    echo "Container Management:"
    echo "  View logs: docker logs $CONTAINER_NAME"
    echo "  Stop container: docker stop $CONTAINER_NAME"
    echo "  Start container: docker start $CONTAINER_NAME"
    echo "  Remove container: docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME"
    echo
    print_status "For detailed documentation, see: docs/JENKINS_QEMU_CONTAINER_SETUP.md"
}

# Main execution
main() {
    echo "=================================="
    echo "Jenkins QEMU Container Setup"
    echo "=================================="
    echo
    
    check_prerequisites
    verify_qemu
    cleanup_existing
    create_volume
    create_container
    wait_for_jenkins
    verify_container
    display_info
    
    echo
    print_success "Setup completed successfully!"
    echo
}

# Handle script interruption
trap 'print_error "Script interrupted"; exit 1' INT TERM

# Run main function
main "$@"