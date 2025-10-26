# SimTemp External GUI Application

**Challenge 2025 - Temperature Sensor Monitor**

Complete external GUI application for monitoring and configuring SimTemp sensor running on ARM target system via QEMU.

## 🎯 Features

### Visual Elements
- **🌡️ Temperature Dial** - Circular dial with threshold visualization and red alarm indicator
- **🔢 7-Segment Display** - Digital temperature display in classic 7-segment style
- **📈 Real-time Plot** - Live temperature plotting with threshold line and alarm zones
- **🔴 Red Alarm Lamp** - Visual alarm indicator in title bar

### Configuration Controls
- **🎚️ Threshold Slider** - Adjustable temperature threshold (0-100°C)
- **⏱️ Sample Rate Slider** - Predefined sample rates (50ms to 5s)
- **🔌 Connection Panel** - TCP connection to SimTemp sensor
- **📊 Statistics Display** - Min/Max/Average temperature statistics

### Connectivity
- **🌐 TCP Connection** - Connects to SimTemp CLI for configuration
- **📡 Real-time Data** - Receives temperature data from Octave/sensor
- **🔄 Auto-reconnect** - Robust connection management

## 🏗️ Architecture

```
┌─────────────────┐    TCP/Socket    ┌──────────────────┐
│   External GUI  │ ←──────────────→ │  SimTemp Sensor  │
│   (This App)    │     Port 4445    │   (ARM Target)   │
└─────────────────┘                  └──────────────────┘
         ↑                                      ↑
         │                                      │
    CustomTkinter                          QEMU Bridge
    + Matplotlib                           + Telnet
```

📚 **Documentación Técnica Completa:**
- 📖 [**ARCHITECTURE.md**](ARCHITECTURE.md) - Documentación técnica detallada del sistema
- 📊 [**DIAGRAMS.md**](DIAGRAMS.md) - Diagramas visuales Mermaid de la arquitectura
- 🔧 [**Componentes técnicos**](ARCHITECTURE.md#-componentes-técnicos-detallados) - Detalles de implementación
- 🔄 [**Flujo de datos**](ARCHITECTURE.md#-flujo-de-datos) - Secuencias y protocolos de comunicación

## 🚀 Quick Start

### 1. Launch GUI
```bash
# Simple launcher (handles everything automatically)
./run_gui.sh

# OR manual activation
source simtemp_gui_env/bin/activate
python3 main.py
```

### 2. Connect to Sensor
1. Enter SimTemp sensor host IP (e.g., `192.168.1.100`)
2. Enter TCP port (default: `4445`)
3. Click **Connect** button
4. Wait for "Connected" status

### 3. Start Monitoring
1. Click **Start Monitoring** in plot controls
2. Observe real-time temperature data
3. Configure threshold and sample rate as needed

## 📋 Requirements

### System Dependencies
- Python 3.8+
- tkinter (usually included with Python)
- Virtual environment support

### Python Dependencies (auto-installed)
- `customtkinter >= 5.2.0` - Modern UI framework
- `matplotlib >= 3.6.0` - Plotting and visualization
- `numpy >= 1.26.0` - Numerical operations

## 🗂️ Project Structure

```
gui-external/
├── main.py                      # Main application
├── temperature_dial.py          # Circular temperature dial widget
├── seven_segment_display.py     # 7-segment digital display
├── realtime_plot.py            # Real-time plotting component
├── configuration_panel.py      # Configuration controls
├── external_simtemp_client.py  # TCP client for data reception
├── requirements.txt            # Python dependencies
├── run_gui.sh                  # Launch script
└── simtemp_gui_env/            # Virtual environment (auto-created)
```

## 🎮 User Interface Guide

### Main Window Layout
```
┌─────────────────────────────────────────────────────────────────────┐
│ SimTemp External Monitor                           ● Connected  🔴   │
├─────────────────┬───────────────────────────┬─────────────────────────┤
│   Instruments   │     Real-time Plot        │    Configuration       │
│                 │                           │                         │
│  ┌───────────┐  │  ┌─────────────────────┐  │  Connection:           │
│  │Temperature│  │  │                     │  │  Host: 192.168.1.100   │
│  │   Dial    │  │  │   Live Temperature  │  │  Port: 4445            │
│  │           │  │  │      Chart         │  │  [Connect]             │
│  └───────────┘  │  │                     │  │                         │
│                 │  └─────────────────────┘  │  Threshold: 45.0°C     │
│  ┌───────────┐  │                           │  ═══════════════       │
│  │  88.8°C   │  │  [Start] [Clear] [Export] │                         │
│  │ 7-Segment │  │                           │  Sample Rate: 100ms    │
│  └───────────┘  │                           │  ═══════════════       │
│                 │                           │                         │
│  Statistics:    │                           │  [Apply Threshold]     │
│  Min: 22.1°C    │                           │  [Apply Sample Rate]   │
│  Max: 48.7°C    │                           │                         │
│  Avg: 35.2°C    │                           │  Status:               │
│                 │                           │  [Connected, monitoring]│
└─────────────────┴───────────────────────────┴─────────────────────────┘
│ Status: Monitoring active - Receiving data            Data Rate: 1.2 Hz │
└─────────────────────────────────────────────────────────────────────────┘
```

### Control Elements

#### Temperature Dial
- Shows current temperature with needle indicator
- Red threshold line marks alarm temperature
- Turns red when temperature exceeds threshold
- Displays "ALARM" text and red circle during alarms

#### 7-Segment Display
- Digital temperature reading (XX.X°C format)
- Green segments for normal operation
- Red segments during alarm conditions
- Can flash for alarm indication

#### Real-time Plot
- Live temperature data with timestamp
- Horizontal threshold line (red dashed)
- Red shaded alarm zone above threshold
- Configurable time window (1-30 minutes)
- Export functionality to CSV

#### Configuration Panel
- **Connection**: Host/port settings and connect button
- **Threshold**: Slider (0-100°C) with live preview
- **Sample Rate**: Stepped slider with predefined rates
- **Status**: Real-time status messages and logs

## 🔧 Configuration Options

### Connection Settings
- **Host**: IP address of SimTemp sensor (ARM target)
- **Port**: TCP port for sensor communication (default: 4445)
- **Timeout**: Connection timeout in seconds

### Temperature Threshold
- **Range**: 0°C to 100°C
- **Precision**: 0.1°C increments
- **Real-time**: Updates dial and plot immediately
- **Apply**: Sends configuration to sensor

### Sample Rates
- **50ms** - Very fast (20 Hz)
- **100ms** - Fast (10 Hz) 
- **250ms** - Medium (4 Hz)
- **500ms** - Slow (2 Hz)
- **1s** - Very slow (1 Hz)
- **2s** - Minimal (0.5 Hz)
- **5s** - Ultra slow (0.2 Hz)

## 🔍 Troubleshooting

### Common Issues

#### Connection Problems
```
❌ Connection Failed
```
**Solutions:**
- Verify SimTemp sensor is running on target
- Check IP address and port number
- Ensure QEMU socket forwarding is active
- Verify network connectivity

#### Missing Dependencies
```
❌ ModuleNotFoundError: No module named 'customtkinter'
```
**Solutions:**
- Run `./run_gui.sh` (auto-installs dependencies)
- Or manually: `source simtemp_gui_env/bin/activate && pip install -r requirements.txt`

#### No Data Reception
```
⚠ Monitoring active but no data received
```
**Solutions:**
- Check sensor is generating data
- Verify Octave integration is running
- Check network connection stability
- Restart monitoring

### Debug Mode
Enable detailed logging:
```bash
export SIMTEMP_DEBUG=1
python3 main.py
```

### Performance Tips
- Use longer sample rates (1-5s) for extended monitoring
- Clear plot data periodically for better performance
- Close other resource-intensive applications
- Monitor on dedicated display for best experience

## 🔗 Integration

### SimTemp CLI Integration
The GUI uses `SimTempConfigClient` to:
- Configure threshold temperature
- Set sampling period
- Get sensor status
- Send control commands

### Octave Data Reception
Real-time data flows through:
- Octave generates temperature values
- ARM target receives via QEMU
- GUI connects via TCP socket
- Data displayed in real-time

### QEMU Socket Bridge
```
Octave → ARM Target → QEMU Socket → External GUI
         (SimTemp)    (Port 4445)   (This App)
```

## 📚 API Reference

### Main Application Class
```python
class SimTempExternalGUI:
    def __init__(self)              # Initialize GUI
    def setup_gui(self)             # Create UI elements
    def on_new_data(self, sample)   # Handle temperature data
    def toggle_monitoring(self)     # Start/stop monitoring
    def run(self)                   # Start application
```

### Widget Classes
- `TemperatureDial` - Circular temperature gauge
- `SevenSegmentDisplay` - Digital temperature display  
- `RealTimePlot` - Live temperature plotting
- `ConfigurationPanel` - Control and configuration UI
- `ExternalSimTempClient` - TCP data client

## 🤝 Contributing

To extend or modify the GUI:

1. **Add new widgets** in separate files
2. **Integrate in main.py** via import and setup
3. **Follow CustomTkinter patterns** for consistency
4. **Test with SimTemp telnet server** for development
5. **Document new features** in this README

## 📜 License

Copyright (c) 2025 Jorge Rodriguez Moreno  
Challenge 2025 Temperature Sensor Project

---

**🚀 Happy Monitoring!** 

For support, check logs in the Status panel or run with debug mode enabled.