# Challenge 2025 Temperature Sensor Driver Container
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV SENSOR_HOME=/opt/sensor

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    linux-headers-generic \
    kmod \
    curl \
    python3 \
    python3-pip \
    python3-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR $SENSOR_HOME

# Copy driver source code
COPY driver/src/ ./src/
COPY driver/config/ ./config/

# Install Python dependencies for API
RUN pip3 install flask flask-restful websocket-server

# Build the driver and API
RUN cd src && make all

# Create device nodes directory
RUN mkdir -p /dev/sensor

# Expose API port
EXPOSE 8080

# Start script
COPY start.sh ./
RUN chmod +x start.sh

CMD ["./start.sh"]