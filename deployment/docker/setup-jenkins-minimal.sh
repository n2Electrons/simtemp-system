#!/bin/bash

# Minimal Jenkins Container Setup Script
# Creates a Jenkins container with ARM cross-compilation and essential tools

set -e

# Configuration
CONTAINER_NAME="jenkins-minimal"
IMAGE_NAME="jenkins-minimal"  
HOST_PORT="8083"
AGENT_PORT="50003"
VOLUME_NAME="jenkins_minimal_home"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Minimal Jenkins Container Setup ===${NC}"

# Stop and remove existing container
echo -e "${GREEN}[INFO]${NC} Stopping existing container..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Build the Docker image
echo -e "${GREEN}[INFO]${NC} Building minimal Jenkins image..."
cd "$(dirname "$0")"

docker build -f Dockerfile.jenkins-minimal -t "$IMAGE_NAME" .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[INFO]${NC} Image built successfully!"
else
    echo "Failed to build image"
    exit 1
fi

# Get workspace path
WORKSPACE_PATH="$(cd ../.. && pwd)"

# Create and start container
echo -e "${GREEN}[INFO]${NC} Creating Jenkins container..."

docker run -d \
    --name "$CONTAINER_NAME" \
    --restart=unless-stopped \
    -p "${HOST_PORT}:8080" \
    -p "${AGENT_PORT}:50000" \
    -v "${VOLUME_NAME}:/var/jenkins_home" \
    -v "${WORKSPACE_PATH}:/workspace:rw" \
    -v "/lib/modules:/lib/modules:ro" \
    -v "/usr/src:/usr/src:ro" \
    "$IMAGE_NAME"

# Wait and get admin password
echo -e "${GREEN}[INFO]${NC} Waiting for Jenkins startup..."
sleep 15

ADMIN_PASSWORD=$(docker exec "$CONTAINER_NAME" cat /var/jenkins_home/secrets/initialAdminPassword 2>/dev/null || echo "Not ready yet")

echo
echo -e "${BLUE}=== Jenkins Container Ready ===${NC}"
echo -e "Container: ${GREEN}$CONTAINER_NAME${NC}"
echo -e "URL: ${GREEN}http://localhost:$HOST_PORT${NC}"
echo -e "Password: ${GREEN}$ADMIN_PASSWORD${NC}"
echo
echo -e "${BLUE}=== Available Tools ===${NC}"
echo "✅ ARM Cross-Compiler (arm-linux-gnueabihf-gcc)"
echo "✅ Host Compiler (gcc)"  
echo "✅ QEMU ARM System Emulation"
echo "✅ Build Tools (make)"
echo "✅ Jenkins with full workspace access"
echo
echo -e "${GREEN}Ready for kernel module builds and QEMU testing!${NC}"