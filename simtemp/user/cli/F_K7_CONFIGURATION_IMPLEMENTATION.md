# SimTemp CLI Configuration System

## 🎯 **Implementation Summary**

This document describes the complete CLI configuration system for the SimTemp sensor, enabling remote configuration of F-K7 parameters (sampling_ms and threshold_mC) via QEMU socket connection.

## 🏗️ **System Architecture**

```
┌─────────────────┐    Socket 4445    ┌─────────────────┐
│   Host CLI      │ ◄─────────────────► │  QEMU ARM       │
│                 │                    │  SimTemp Sensor │
│ - Configuration │                    │  - Driver       │
│ - Monitoring    │                    │  - /dev/simtemp │
│ - Wave Control  │                    │  - sysfs attrs  │
└─────────────────┘                    └─────────────────┘
```

## 📁 **Component Files**

### **1. Configuration Client**
- **File**: `simtemp_config_client.py`
- **Purpose**: TCP socket client for F-K7 parameter configuration
- **Features**:
  - Connect to QEMU sensor via port 4445
  - Configure sampling period (ms)
  - Configure temperature threshold (milli-°C)
  - Set/get current temperature
  - Get complete sensor status

### **2. Telnet Server Simulator**
- **File**: `simtemp_telnet_server.py` 
- **Purpose**: SimTemp sensor simulator with F-K7 configuration support
- **Features**:
  - F-K7 configuration parameters (sampling_ms, threshold_mC)
  - Command protocol compatible with QEMU socket
  - Real-time temperature control
  - Status monitoring

### **3. Wave Generator**
- **File**: `continuous_wave_generator.py`
- **Purpose**: Generate temperature waveforms for sensor testing
- **Features**:
  - Multiple wave types (sine, square, triangle, sawtooth, noise, step, ramp)
  - Configurable frequency, amplitude, offset
  - Real-time injection via socket connection
  - Integration with Octave patterns

### **4. Demo Script**
- **File**: `demo_config_socket.sh`
- **Purpose**: Demonstration of complete configuration workflow
- **Features**:
  - Step-by-step configuration examples
  - F-K7 parameter testing
  - Wave generation examples

## 🔧 **F-K7 Configuration Commands**

### **Available Commands:**
```
SET_TEMP <temperature>    - Set current temperature in °C
GET_TEMP                  - Get current temperature
SET_SAMPLING <ms>         - Configure sampling period (1-60000 ms)
GET_SAMPLING              - Get sampling period
SET_THRESHOLD <mC>        - Configure threshold (-50000 to 150000 mC)
GET_THRESHOLD             - Get threshold
STATUS                    - Get complete sensor status
HELP                      - Show command help
QUIT                      - Close connection
```

## 🚀 **Usage Examples**

### **Configuration Client:**
```bash
# Get current configuration
python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --get-config

# Configure F-K7 sampling period to 200ms
python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --set-sampling 200

# Configure F-K7 threshold to 35°C (35000 mC)
python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --set-threshold 35000

# Set test temperature
python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --set-temp 28.5
```

### **Wave Generation:**
```bash
# Generate sine wave for F-K7 testing
python3 continuous_wave_generator.py --host 127.0.0.1 --port 4445 \
        --wave sine --frequency 0.1 --amplitude 8.0 --offset 30.0 --duration 60

# Generate square wave for threshold testing
python3 continuous_wave_generator.py --host 127.0.0.1 --port 4445 \
        --wave square --frequency 0.05 --amplitude 15.0 --offset 35.0 --duration 120
```

### **Demo Script:**
```bash
# Run complete configuration demonstration
./demo_config_socket.sh
```

## 🔌 **QEMU Integration**

### **QEMU Configuration:**
The SimTemp sensor in QEMU is exposed via socket on port 4445:
```bash
qemu-system-arm -M sabrelite \
  -chardev socket,id=mysensor,server=on,host=127.0.0.1,port=4445,wait=off \
  -serial chardev:mysensor
```

### **Connection Protocol:**
- **Transport**: TCP socket
- **Port**: 4445 (configurable)
- **Protocol**: Text-based command/response
- **Encoding**: ASCII
- **Terminator**: `\r\n`

## 📊 **F-K7 Parameter Validation**

### **Sampling Period (sampling_ms):**
- **Range**: 1 to 60000 milliseconds
- **Default**: 100 ms
- **Validation**: Integer within range
- **Usage**: Controls driver polling frequency

### **Temperature Threshold (threshold_mC):**
- **Range**: -50000 to 150000 milli-degrees Celsius (-50°C to 150°C)
- **Default**: 45000 mC (45°C)
- **Validation**: Integer within range
- **Usage**: Alert trigger threshold

## 🧪 **Testing Workflow**

### **1. Start Sensor Simulator:**
```bash
python3 simtemp_telnet_server.py --port 4445
```

### **2. Configure F-K7 Parameters:**
```bash
python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --set-sampling 150
python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --set-threshold 40000
```

### **3. Generate Test Waveforms:**
```bash
python3 continuous_wave_generator.py --host 127.0.0.1 --port 4445 \
        --wave sine --frequency 0.2 --amplitude 5.0 --offset 30.0 --duration 30
```

### **4. Verify Configuration:**
```bash
python3 simtemp_config_client.py --host 127.0.0.1 --port 4445 --get-config
```

## ✅ **Implementation Status**

### **Completed Features:**
- ✅ TCP socket client for F-K7 configuration
- ✅ SimTemp sensor simulator with F-K7 support
- ✅ Wave generator with socket integration
- ✅ Complete command protocol implementation
- ✅ Parameter validation and error handling
- ✅ Real-time temperature control
- ✅ Status monitoring and reporting
- ✅ Demo scripts and documentation

### **F-K7 Configuration Support:**
- ✅ **sampling_ms**: Configurable via SET_SAMPLING command
- ✅ **threshold_mC**: Configurable via SET_THRESHOLD command
- ✅ **Parameter validation**: Range checking and error reporting
- ✅ **Real-time updates**: Immediate configuration changes
- ✅ **Status reporting**: Complete configuration visibility

## 🎯 **Integration with QEMU**

The CLI system is designed to work seamlessly with the QEMU SimTemp sensor:

1. **QEMU exposes sensor** on socket port 4445
2. **Host CLI connects** via TCP to configure F-K7 parameters
3. **Real-time configuration** of sampling_ms and threshold_mC
4. **Wave generation** for comprehensive testing
5. **Status monitoring** for validation

This implementation provides **complete F-K7 configuration capability** for the SimTemp sensor running in QEMU, enabling the host CLI to configure both `sampling_ms` and `threshold_mC` parameters as required.