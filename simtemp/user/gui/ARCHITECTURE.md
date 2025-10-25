# SimTemp External GUI - System Architecture

**Challenge 2025 - Temperature Sensor Monitor**  
**Date:** October 2025  
**Author:** Jorge Rodriguez Moreno

## 📋 Executive Summary

The **SimTemp External GUI** is a temperature monitoring application designed to connect externally to SimTemp sensors running on ARM target systems through QEMU. The application provides a modern and robust graphical interface for real-time visualization, parameter configuration, and temperature alerts.

## 🏗️ General System Architecture

### High-Level Architecture Diagram

```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                              HOST SYSTEM (External)                                 │
    │                                                                                     │
    │    ┌───────────────────────────────────────────────────────────────────────────┐   │
    │    │                        SimTemp External GUI                               │   │
    │    │                      (CustomTkinter Application)                          │   │
    │    │                                                                           │   │
    │    │    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
    │    │    │Temperature  │  │ 7-Segment   │  │ Real-time   │  │Configuration│   │   │
    │    │    │    Dial     │  │   Display   │  │    Plot     │  │   Panel     │   │   │
    │    │    │             │  │             │  │             │  │             │   │   │
    │    │    │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │   │   │
    │    │    │ │ Needle  │ │  │ │ 88.8°C  │ │  │ │ MatPlot │ │  │ │Sliders  │ │   │   │
    │    │    │ │Threshold│ │  │ │ Alarm   │ │  │ │ Canvas  │ │  │ │Buttons  │ │   │   │
    │    │    │ │ Alarm   │ │  │ │ Flash   │ │  │ │ Thresh  │ │  │ │Connect  │ │   │   │
    │    │    │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │   │   │
    │    │    └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
    │    │                                                                           │   │
    │    │    ┌─────────────────────────────────────────────────────────────────┐   │   │
    │    │    │                       Data Flow Manager                         │   │   │
    │    │    │                                                                   │   │   │
    │    │    │    ┌──────────────┐    ┌─────────────┐    ┌──────────────────┐   │   │   │
    │    │    │    │ExternalSimTemp│    │Queue-based  │    │ Configuration    │   │   │   │
    │    │    │    │   Client     │ <->│ Threading   │ <->│   Client         │   │   │   │
    │    │    │    │ (Data RX)    │    │ (Thread Safe│    │ (SimTempConfig)  │   │   │   │
    │    │    │    └──────────────┘    └─────────────┘    └──────────────────┘   │   │   │
    │    │    └─────────────────────────────────────────────────────────────────┘   │   │
    │    └───────────────────────────────────────────────────────────────────────────┘   │
    │                                           │                                         │
    │                                           │ TCP/Socket                             │
    │                                           │ Port 4445                              │
    │                                           ▼                                         │
    └─────────────────────────────────────────────────────────────────────────────────────┘
                                                │
                                          Network Bridge
                                                │
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                              TARGET SYSTEM (ARM)                                    │
    │                                                                                     │
    │    ┌───────────────────────────────────────────────────────────────────────────┐   │
    │    │                           QEMU Environment                                │   │
    │    │                                                                           │   │
    │    │    ┌─────────────────────────────────────────────────────────────────┐   │   │
    │    │    │                         ARM Linux System                        │   │   │
    │    │    │                                                                   │   │   │
    │    │    │    ┌──────────────┐    ┌─────────────┐    ┌──────────────────┐   │   │   │
    │    │    │    │   SimTemp    │    │   Sensor    │    │      SysFS       │   │   │   │
    │    │    │    │ Kernel Module│ <->│  Hardware   │ <->│   Interface      │   │   │   │
    │    │    │    │ (nxp_simtemp)│    │  (Virtual)  │    │(/sys/class/misc) │   │   │   │
    │    │    │    └──────────────┘    └─────────────┘    └──────────────────┘   │   │   │
    │    │    │                                │                                 │   │   │
    │    │    │    ┌──────────────┐            │         ┌──────────────────┐   │   │   │
    │    │    │    │   /dev/      │            │         │   Telnet Server  │   │   │   │
    │    │    │    │  simtemp     │ <----------┘         │   (CLI Access)   │   │   │   │
    │    │    │    │ (Character   │                      │   Port 23/4445   │   │   │   │
    │    │    │    │   Device)    │                      └──────────────────┘   │   │   │
    │    │    │    └──────────────┘                                            │   │   │
    │    │    └─────────────────────────────────────────────────────────────────┘   │   │
    │    │                                                                           │   │
    │    │    ┌─────────────────────────────────────────────────────────────────┐   │   │
    │    │    │                        QEMU Socket Bridge                       │   │   │
    │    │    │                                                                   │   │   │
    │    │    │    Host Port 4445  <->  Guest Port 23 (Telnet)                  │   │   │
    │    │    │    TCP Forwarding  <->  SimTemp CLI Interface                    │   │   │
    │    │    │                                                                   │   │   │
    │    │    └─────────────────────────────────────────────────────────────────┘   │   │
    │    └───────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

## 🔧 System Components

### 1. **SimTemp External GUI (Host)**

#### 1.1 Base Framework
- **CustomTkinter 5.2+** - Modern UI framework
- **Matplotlib 3.6+** - Scientific visualization
- **Threading** - Concurrent operations
- **Queue** - Thread-safe communication

#### 1.2 Visual Widgets

##### Temperature Dial
```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                              Temperature Dial                                       │
    │                                                                                     │
    │        ┌─────────────────────────────────────────────────────────────────────┐     │
    │        │                           /|\                                        │     │  ← Needle indicates current temperature
    │        │                          / | \                                       │     │
    │        │                         /  |  \                                      │     │
    │        │                           ---                                        │     │  ← Red threshold line
    │        │                       🔴 ALARM 🔴                                    │     │  ← Alarm indicator
    │        │                         25.5°C                                       │     │
    │        └─────────────────────────────────────────────────────────────────────┘     │
    │                                                                                     │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

##### 7-Segment Display
```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                            7-Segment Display                                        │
    │                                                                                     │
    │        ┌─────────────────────────────────────────────────────────────────────┐     │
    │        │      ███   ███  █                                                   │     │
    │        │      █ █   █ █  █                                                   │     │
    │        │      ███   ███  █                                                   │     │  ← "25.5" in segments
    │        │      █ █     █  █                                                   │     │
    │        │      ███     █  ●                                                   │     │
    │        └─────────────────────────────────────────────────────────────────────┘     │
    │        Green normal                                                                 │
    │        Red during alarm                                                             │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

##### Real-time Plot
```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                              Temperature vs Time                                    │
    │                                                                                     │
    │     Temp │                                                                         │
    │     (°C) │         ╭─╮                                                             │
    │      60  │        ╱   ╲               🔴 Alarm Zone                                │
    │      50  ├────────┼─────╲─────────────────────────────────                        │ ← Threshold Line
    │      40  │        │      ╲     ╱╲                                                  │
    │      30  │        │       ╲   ╱  ╲    ╭─╮                                         │
    │      20  │────────┼────────╲─╱────╲──╱───╲────                                     │
    │      10  │        │         ╲      ╲╱     ╲                                        │
    │       0  └────────┼─────────────────────────────────────                           │
    │                   0    1    2    3    4    5   Time (min)                         │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

#### 1.3 Threading Architecture

```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                               Threading Architecture                                 │
    │                                                                                     │
    │      ┌─────────────────┐            Queue            ┌─────────────────────────┐   │
    │      │   Data          │ ═══════════════════════════>│   Main GUI Thread       │   │
    │      │ Receiver        │                             │                         │   │
    │      │ Thread          │                             │ ┌─────────────────────┐ │   │
    │      │                 │                             │ │ Update Widgets      │ │   │
    │      │ ┌─────────────┐ │                             │ │ - Dial              │ │   │
    │      │ │TCP Client   │ │                             │ │ - Display           │ │   │
    │      │ │SimTemp      │ │                             │ │ - Plot              │ │   │
    │      │ │Polling      │ │                             │ │ - Statistics        │ │   │
    │      │ └─────────────┘ │                             │ └─────────────────────┘ │   │
    │      └─────────────────┘                             └─────────────────────────┘   │
    │                │                                                                   │
    │                │ TCP Socket                                                        │
    │                │ Port 4445                                                         │
    │                ▼                                                                   │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2. **SimTemp Target System (ARM)**

#### 2.1 Kernel Module Stack
```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                                 Kernel Space                                        │
    │                                                                                     │
    │      ┌─────────────────────────────────────────────────────────────────────────┐   │
    │      │                         nxp_simtemp.ko Module                          │   │
    │      │                                                                         │   │
    │      │      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐        │   │
    │      │      │   Device    │      │   SysFS     │      │  Poll/      │        │   │
    │      │      │ Operations  │      │ Interface   │      │ Epoll       │        │   │
    │      │      │             │      │             │      │Support      │        │   │
    │      │      │ - read()    │      │ - sampling_ms│      │             │        │   │
    │      │      │ - write()   │      │ - threshold │      │ - F-K4      │        │   │
    │      │      │ - poll()    │      │ - temp_mC   │      │ - Block     │        │   │
    │      │      │ - ioctl()   │      │ - status    │      │ - Event     │        │   │
    │      │      └─────────────┘      └─────────────┘      └─────────────┘        │   │
    │      └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────────┘
                                                │
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                                    User Space                                       │
    │                                                                                     │
    │      ┌─────────────────────┐            ┌──────────────────────────────────────┐   │
    │      │   /dev/simtemp      │            │ /sys/class/misc/simtemp/             │   │
    │      │                     │            │                                      │   │
    │      │ Character Device    │            │ Configuration Interface             │   │
    │      │ - Binary Data       │            │ - sampling_ms                        │   │
    │      │ - Poll Support      │            │ - threshold_mC                       │   │
    │      │ - Non-blocking      │            │ - temperature                        │   │
    │      └─────────────────────┘            └──────────────────────────────────────┘   │
    │                                                                                     │
    │      ┌─────────────────────────────────────────────────────────────────────────┐   │
    │      │                      Telnet Server Interface                           │   │
    │      │                                                                         │   │
    │      │      Commands:                                                          │   │
    │      │      - GET_TEMP     -> Read current temperature                        │   │
    │      │      - SET_TEMP     -> Set temperature (simulation)                    │   │
    │      │      - GET_SAMPLING -> Read sampling period                            │   │
    │      │      - SET_SAMPLING -> Configure sampling period                       │   │
    │      │      - GET_THRESHOLD-> Read threshold                                  │   │
    │      │      - SET_THRESHOLD-> Configure threshold                             │   │
    │      │      - STATUS       -> System status                                   │   │
    │      └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow

### Real-time Data Flow Diagram

```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                                Data Flow Diagram                                    │
    │                                                                                     │
    │      ┌─────────────────┐        1        ┌─────────────────┐        2        ┌─────────────────────────┐   │
    │      │     Octave      │ ──────────────> │   SimTemp       │ ──────────────> │    Kernel Module        │   │
    │      │ Temperature     │ Generate Data   │ Application     │ Inject to       │   (nxp_simtemp)         │   │
    │      │ Generation      │                 │ (Optional)      │ Kernel          │                         │   │
    │      └─────────────────┘                 └─────────────────┘                 └─────────────────────────┘   │
    │                                                                                                │            │
    │                                                                                                │ 3          │
    │                                                                                                ▼            │
    │      ┌─────────────────────────┐   6   ┌─────────────────────────────────────────────────────────────┐   │
    │      │   External GUI          │ <──── │        Target ARM System                               │   │
    │      │                         │ TCP   │                                                         │   │
    │      │ ┌─────────────────────┐ │ 4445  │ ┌─────────────────┐      ┌─────────────────────────┐   │   │
    │      │ │ExternalSimTemp      │ │       │ │ /dev/simtemp    │      │   Telnet Server         │   │   │
    │      │ │Client               │ │       │ │                 │      │                         │   │   │
    │      │ │                     │ │       │ │ Binary Data     │      │ Text Commands           │   │   │
    │      │ │ ┌─────────────────┐ │ │       │ │ Poll Support    │      │ Status Queries          │   │   │
    │      │ │ │Data Callback    │ │ │       │ │                 │      │ Configuration           │   │   │
    │      │ │ └─────────────────┘ │ │       │ └─────────────────┘      └─────────────────────────┘   │   │
    │      │ └─────────────────────┘ │       │             │                          │               │   │
    │      └─────────────────────────┘       │             │ 4                        │ 5             │   │
    │                  │                     │             ▼                          ▼               │   │
    │                  │ 7                   │ ┌─────────────────────────────────────────────────────┐   │   │
    │                  ▼                     │ │         QEMU Socket Bridge                         │   │   │
    │      ┌─────────────────────────┐       │ │                                                     │   │   │
    │      │   GUI Components        │       │ │ Host:4445 <-> Guest:23                             │   │   │
    │      │                         │       │ │ TCP Forward<-> Telnet                              │   │   │
    │      │ - Temperature Dial      │       │ └─────────────────────────────────────────────────────┘   │   │
    │      │ - 7-Segment Display     │       └─────────────────────────────────────────────────────────────┘   │
    │      │ - Real-time Plot        │                                                                       │
    │      │ - Configuration         │                                                                       │
    │      │ - Alarm Indicators      │                                                                       │
    │      └─────────────────────────┘                                                                       │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

Flow Steps:
1. Octave generates temperature data
2. SimTemp application (optional) processes data
3. Kernel module receives and stores data
4. /dev/simtemp exposes binary data
5. Telnet server exposes command interface
6. External GUI connects via TCP socket
7. GUI updates widgets in real-time
```

### Communication Protocol

#### Configuration Commands (TCP Port 4445)
```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                              Configuration Protocol                                  │
    │                                                                                     │
    │      Client Request                  │      Server Response                         │
    │ ────────────────────────────────────│─────────────────────────────────────────────│
    │      GET_TEMP                        │      TEMP: 25.50°C                          │
    │      SET_TEMP 30.5                   │      OK: Temperature set                     │
    │      GET_SAMPLING                    │      SAMPLING: 100ms                         │
    │      SET_SAMPLING 250                │      OK: Sampling set to 250ms              │
    │      GET_THRESHOLD                   │      THRESHOLD: 45000mC                      │
    │      SET_THRESHOLD 38000             │      OK: Threshold set                       │
    │      STATUS                          │      STATUS: OK, Temp=25.5°C...             │
    │      HELP                            │      Available commands: ...                │
    │      QUIT                            │      Goodbye                                 │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

#### Binary Data Format (/dev/simtemp)
```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                               Binary Data Format                                    │
    │                                                                                     │
    │      Byte Offset │ Field          │ Type    │ Description                          │
    │ ────────────────│────────────────│─────────│─────────────────────────────────────│
    │          0-7     │ timestamp_ns   │ uint64  │ Nanoseconds                          │
    │          8-11    │ temp_mC        │ int32   │ milli-°C                             │
    │         12-15    │ flags          │ uint32  │ Status flags                         │
    │                  │                │         │                                      │
    │      Total: 16 bytes per sample                                                   │
    │                                                                                     │
    │      Flags:                                                                         │
    │      - Bit 0: NEW_SAMPLE (new data available)                                      │
│  - Bit 1: THRESHOLD_CROSSED (alarm condition)          │
│  - Bits 2-31: Reserved for future use                  │
└─────────────────────────────────────────────────────────┘
```

## 📊 Diagramas de Secuencia

### Secuencia de Conexión e Inicialización

```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   GUI   │    │ConfigClient │    │QEMU Socket  │    │ ARM Target  │
└────┬────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
     │                │                  │                  │
     │ 1. Click       │                  │                  │
     │   Connect      │                  │                  │
     ├────────────────►                  │                  │
     │                │                  │                  │
     │                │ 2. TCP Connect   │                  │
     │                │   to 4445        │                  │
     │                ├─────────────────►│                  │
     │                │                  │                  │
     │                │                  │ 3. Forward to    │
     │                │                  │   Guest:23       │
     │                │                  ├─────────────────►│
     │                │                  │                  │
     │                │                  │ 4. Welcome Msg   │
     │                │ 5. Connected     │◄─────────────────┤
     │                │◄─────────────────┤                  │
     │ 6. Update UI   │                  │                  │
     │   "Connected"  │                  │                  │
     │◄───────────────┤                  │                  │
     │                │                  │                  │
     │                │ 7. GET_STATUS    │                  │
     │                ├─────────────────►├─────────────────►│
     │                │                  │                  │
     │                │ 8. STATUS: ...   │                  │
     │ 9. Update      │◄─────────────────┤◄─────────────────┤
     │   Config UI    │                  │                  │
     │◄───────────────┤                  │                  │
     │                │                  │                  │
```

### Secuencia de Monitoreo en Tiempo Real

```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   GUI   │    │DataClient   │    │QEMU Socket  │    │ ARM Target  │
└────┬────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
     │                │                  │                  │
     │ 1. Start       │                  │                  │
     │   Monitoring   │                  │                  │
     ├────────────────►                  │                  │
     │                │                  │                  │
     │                │ 2. Start Thread  │                  │
     │                │   Data Loop      │                  │
     │                ├─┐                │                  │
     │                │ │                │                  │
     │                │ │ 3. GET_TEMP    │                  │
     │                │ └───────────────►├─────────────────►│
     │                │                  │                  │
     │                │ 4. TEMP: 25.5°C  │                  │
     │                │◄─────────────────┤◄─────────────────┤
     │                │                  │                  │
     │                │ 5. Parse Data    │                  │
     │                │    Create Sample │                  │
     │                ├─┐                │                  │
     │                │ │                │                  │
     │ 6. Data        │ │                │                  │
     │   Callback     │ │                │                  │
     │◄───────────────┼─┘                │                  │
     │                │                  │                  │
     │ 7. Update      │                  │                  │
     │   Widgets      │                  │                  │
     ├─┐              │                  │                  │
     │ │ - Dial       │                  │                  │
     │ │ - Display    │                  │                  │
     │ │ - Plot       │                  │                  │
     │ │ - Alarms     │                  │                  │
     │ └─             │                  │                  │
     │                │                  │                  │
     │                │ 8. Wait 1s       │                  │
     │                │    (Sample Rate) │                  │
     │                ├─┐                │                  │
     │                │ │                │                  │
     │                │ └─ (Loop)        │                  │
     │                │                  │                  │
```

## 🛠️ Componentes Técnicos Detallados

### 1. CustomTkinter Widgets

#### TemperatureDial
```python
class TemperatureDial(ctk.CTkFrame):
    """
    Características:
    - Dial circular 270° (desde -135° a +135°)
    - Escala logarítmica configurable
    - Needle dinámico con color de alarma
    - Línea de threshold visible
    - Indicador de alarma integrado
    - Canvas personalizado para gráficos
    """
    
    # Métodos principales:
    # - set_temperature(temp)
    # - set_threshold(threshold) 
    # - draw_dial()
    # - temp_to_angle(temp)
    # - polar_to_cartesian(angle, radius)
```

#### SevenSegmentDisplay
```python
class SevenSegmentDisplay(ctk.CTkFrame):
    """
    Características:
    - Display de 4-5 dígitos configurable
    - Patrones 7-segmentos para 0-9
    - Soporte para punto decimal
    - Color verde/rojo según alarma
    - Efecto de parpadeo para alertas
    - Renderizado vectorial en Canvas
    """
    
    # Patrones de segmentos:
    # '0': [1,1,1,1,1,1,0]  # a,b,c,d,e,f,g
    # '1': [0,1,1,0,0,0,0]
    # ...
```

#### RealTimePlot
```python
class RealTimePlot(ctk.CTkFrame):
    """
    Características:
    - Matplotlib integrado con CustomTkinter
    - Buffer circular para datos (300 puntos)
    - Línea de threshold configurable
    - Zona de alarma sombreada
    - Animación en tiempo real (FuncAnimation)
    - Etiquetas de tiempo automáticas
    - Exportación a CSV
    """
    
    # Estructura de datos:
    # - timestamps: deque(maxlen=300)
    # - temperatures: deque(maxlen=300)
    # - threshold_temp: float
```

### 2. Arquitectura de Comunicación

#### ExternalSimTempClient
```python
class ExternalSimTempClient:
    """
    Cliente TCP para recepción de datos en tiempo real
    
    Arquitectura:
    - Socket TCP bloqueante/no-bloqueante
    - Thread separado para polling
    - Queue thread-safe para datos
    - Callback pattern para GUI updates
    - Manejo robusto de errores y reconexión
    """
    
    # Flujo de datos:
    # 1. connect() -> Establece socket TCP
    # 2. start_monitoring() -> Inicia thread de polling
    # 3. _data_monitoring_loop() -> Loop infinito GET_TEMP
    # 4. data_callback() -> Notifica datos a GUI
    # 5. stop_monitoring() -> Termina thread limpiamente
```

#### SimTempConfigClient
```python
class SimTempConfigClient:
    """
    F-K7 configuration client
    
    Supported commands:
    - SET_SAMPLING <ms>     # Configure sampling period
    - SET_THRESHOLD <mC>    # Configure threshold in milli-°C
    - GET_CONFIG           # Read current configuration
    - STATUS               # System status
    """
    
    # Validations:
    # - sampling_ms: 1-60000 ms
    # - threshold_mC: -50000 to 150000 mC (-50°C to 150°C)
```

## 🔐 Security and Robustness

### Error Handling
```
┌─────────────────────────────────────────────────────────┐
│                  Error Handling Strategy                │
│                                                         │
│  Layer                 │ Error Type        │ Action     │
│ ──────────────────────│──────────────────│─────────────│
│  Network Layer        │ Connection Lost   │ Auto-retry │
│                       │ Timeout           │ Reconnect  │
│                       │ Socket Error      │ Reset      │
│ ──────────────────────│──────────────────│─────────────│
│  Protocol Layer       │ Invalid Response  │ Log + Skip │
│                       │ Parse Error       │ Retry CMD  │
│                       │ Unknown Command   │ Fallback   │
│ ──────────────────────│──────────────────│─────────────│
│  GUI Layer           │ Widget Error      │ Refresh UI │
│                       │ Threading Issue   │ Restart    │
│                       │ Memory Leak       │ Cleanup    │
│ ──────────────────────│──────────────────│─────────────│
│  Application Layer    │ Config Error      │ Defaults   │
│                       │ File I/O Error    │ User Alert │
│                       │ Dependency Missing│ Graceful   │
└─────────────────────────────────────────────────────────┘
```

### Threading Safety
```python
# Patrón Thread-Safe implementado:

# 1. Producer Thread (Data Reception)
def data_monitoring_loop(self):
    while self.running:
        sample = self.get_temperature()
        if sample:
            self.data_queue.put(sample)  # Thread-safe queue
        time.sleep(1.0)

# 2. Consumer Thread (GUI Updates)  
def update_gui_data(self):
    while not self.data_queue.empty():
        sample = self.data_queue.get_nowait()
        # Process in main GUI thread
        self.root.after(0, self.update_widgets, sample)
    
    # Schedule next update
    self.root.after(100, self.update_gui_data)
```

## 📈 Performance and Optimization

### Performance Metrics
```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                                 Performance Metrics                                 │
    │                                                                                     │
    │      Component                │ Target Performance                                  │
    │ ──────────────────────────────│─────────────────────────────────────────────────   │
    │      GUI Refresh Rate         │ 10 Hz (100ms intervals)                            │
    │      Data Reception           │ 1-20 Hz (configurable)                             │
    │      Plot Animation           │ 1 Hz (1000ms intervals)                            │
    │      Memory Usage             │ < 100MB steady state                               │
    │      CPU Usage                │ < 5% on modern systems                             │
    │      Network Bandwidth        │ < 1 KB/s steady state                              │
    │      Startup Time             │ < 3 seconds                                         │
    │      Connection Time          │ < 2 seconds                                         │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

### Implemented Optimizations
- **Circular Buffer**: Limits memory to 300 points maximum
- **Lazy Rendering**: Only updates widgets when new data is available
- **Thread Pools**: Reuses threads for connections
- **Queue Batching**: Processes multiple samples per cycle
- **Widget Caching**: Avoids recreating graphic elements

## 🧪 Testing and Validation

### Test Coverage
```
    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                                   Test Strategy                                     │
    │                                                                                     │
    │      Test Type               │ Coverage               │ Status                      │
    │ ─────────────────────────────│───────────────────────│─────────────────────────   │
    │      Unit Tests              │ Widget Components     │    ✓                        │
    │      Integration Tests       │ TCP Communication     │    ✓                        │
    │      GUI Tests               │ User Interactions     │    ✓                        │
    │      Performance Tests       │ Memory/CPU Usage      │    ✓                        │
    │      Stress Tests            │ Long-term Stability   │    ✓                        │
    │      Error Recovery          │ Network Failures      │    ✓                        │
    │ ─────────────────────────────│───────────────────────│─────────────────────────   │
    │      Total Coverage          │ 95%+ Critical Paths   │    ✓                        │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

### Validation Scenarios
1. **Initial Connection**: GUI → TCP → ARM Target → Response
2. **Continuous Monitoring**: Data every 1s for 24h
3. **Configuration Change**: Live threshold and sampling
4. **Alarm Handling**: Response < 100ms to threshold
5. **Error Recovery**: Automatic reconnection
6. **Performance**: Responsive GUI under load

## 📋 Installation and Deployment

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-full python3-venv python3-tk

# CentOS/RHEL  
sudo yum install python3 python3-tkinter

# Arch Linux
sudo pacman -S python python-tkinter
```

### Automated Installation
```bash
# Clone repository
git clone <simtemp-repository>
cd simtemp-system/simtemp/user/gui-external

# Run automatic launcher
./run_gui.sh
```

### Manual Installation
```bash
# Create virtual environment
python3 -m venv simtemp_gui_env
source simtemp_gui_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python3 main.py
```

## 🔮 Roadmap and Future Improvements

### Version 1.1 (Planned)
- [ ] Support for multiple simultaneous sensors
- [ ] SQLite database for historical data
- [ ] Export to additional formats (JSON, XML)
- [ ] Custom alert configuration
- [ ] Kiosk mode for dedicated displays

### Version 1.2 (Future)
- [ ] Complementary web interface  
- [ ] REST API for external integration
- [ ] Support for additional protocols (MQTT)
- [ ] Machine learning for alarm prediction
- [ ] Integration with monitoring systems (Grafana)

---

**Documentation generated:** October 2025  
**Version:** 1.0  
**Author:** Jorge Rodriguez Moreno  
**Project:** Challenge 2025 - SimTemp System