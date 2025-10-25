# SimTemp External GUI - Visual Diagrams

This file contains Mermaid format diagrams to visualize the system architecture.

## General System Architecture

```mermaid
graph TB
    subgraph "HOST SYSTEM (External)"
        subgraph "SimTemp External GUI"
            GUI[CustomTkinter Application]
            subgraph "Visual Components"
                DIAL[Temperature Dial]
                DISPLAY[7-Segment Display]
                PLOT[Real-time Plot]
                CONFIG[Configuration Panel]
            end
            subgraph "Data Management"
                CLIENT[ExternalSimTempClient]
                QUEUE[Queue Threading]
                CONFIGCLIENT[SimTempConfigClient]
            end
        end
    end
    
    subgraph "NETWORK"
        TCP[TCP/Socket<br/>Port 4445]
    end
    
    subgraph "TARGET SYSTEM (ARM)"
        subgraph "QEMU Environment"
            subgraph "ARM Linux System"
                KERNEL[SimTemp Kernel Module<br/>nxp_simtemp.ko]
                DEVICE[/dev/simtemp<br/>Character Device]
                SYSFS[SysFS Interface<br/>/sys/class/misc/simtemp]
                TELNET[Telnet Server<br/>CLI Access]
            end
            subgraph "QEMU Bridge"
                SOCKET[Socket Bridge<br/>Host:4445 ↔ Guest:23]
            end
        end
    end
    
    GUI --> CLIENT
    CLIENT --> TCP
    TCP --> SOCKET
    SOCKET --> TELNET
    TELNET --> KERNEL
    KERNEL --> DEVICE
    KERNEL --> SYSFS
    
    CONFIG --> CONFIGCLIENT
    CONFIGCLIENT --> TCP
    
    CLIENT --> QUEUE
    QUEUE --> DIAL
    QUEUE --> DISPLAY
    QUEUE --> PLOT
```

## Real-time Data Flow

```mermaid
sequenceDiagram
    participant O as Octave
    participant ARM as ARM Target
    participant K as Kernel Module
    participant T as Telnet Server
    participant Q as QEMU Socket
    participant C as GUI Client
    participant G as GUI Widgets
    
    Note over O,G: Data Generation and Flow
    
    O->>ARM: Generate Temperature Data
    ARM->>K: Inject to Kernel Module
    K->>K: Store in /dev/simtemp
    K->>T: Expose via Telnet
    
    Note over C,G: Monitoring Loop (1Hz)
    
    loop Every 1 second
        C->>Q: GET_TEMP command
        Q->>T: Forward to Telnet
        T->>K: Read from kernel
        K-->>T: Temperature data
        T-->>Q: TEMP: 25.5°C
        Q-->>C: Response
        C->>C: Parse data
        C->>G: Update widgets
        G->>G: Refresh display
    end
    
    Note over C,G: Configuration Changes
    
    G->>C: User changes threshold
    C->>Q: SET_THRESHOLD 38000
    Q->>T: Forward command
    T->>K: Update SysFS
    K-->>T: OK response
    T-->>Q: OK: Threshold set
    Q-->>C: Confirmation
    C->>G: Update UI feedback
```

## Threading Architecture

```mermaid
graph LR
    subgraph "Main GUI Thread"
        MAIN[Main Event Loop]
        WIDGETS[Widget Updates]
        EVENTS[User Events]
    end
    
    subgraph "Data Thread"
        POLL[TCP Polling Loop]
        PARSE[Data Parsing]
        CALLBACK[Data Callback]
    end
    
    subgraph "Thread Communication"
        QUEUE[Thread-Safe Queue]
    end
    
    MAIN --> EVENTS
    EVENTS --> MAIN
    
    POLL --> PARSE
    PARSE --> CALLBACK
    CALLBACK --> QUEUE
    
    QUEUE --> WIDGETS
    WIDGETS --> MAIN
    
    MAIN -.->|after(100ms)| WIDGETS
```

## CustomTkinter Component Diagram

```mermaid
classDiagram
    class SimTempExternalGUI {
        +CTk root
        +ExternalSimTempClient data_client
        +bool monitoring_active
        +float current_temperature
        +float current_threshold
        +setup_gui()
        +toggle_monitoring()
        +on_new_data(sample)
        +run()
    }
    
    class TemperatureDial {
        +Canvas canvas
        +float current_temp
        +float threshold_temp
        +bool alarm_active
        +set_temperature(temp)
        +set_threshold(threshold)
        +draw_dial()
    }
    
    class SevenSegmentDisplay {
        +Canvas canvas
        +str value
        +bool alarm_state
        +dict digit_patterns
        +set_value(value, alarm)
        +draw_display()
    }
    
    class RealTimePlot {
        +Figure fig
        +Axes ax
        +deque timestamps
        +deque temperatures
        +float threshold_temp
        +add_data_point(temp, time)
        +set_threshold(threshold)
        +start_animation()
    }
    
    class ConfigurationPanel {
        +SimTempConfigClient config_client
        +CTkSlider threshold_slider
        +CTkSlider sample_rate_slider
        +apply_threshold()
        +apply_sample_rate()
    }
    
    class ExternalSimTempClient {
        +socket socket
        +queue data_queue
        +bool connected
        +callable data_callback
        +connect()
        +start_monitoring()
        +send_command(cmd)
    }
    
    SimTempExternalGUI --> TemperatureDial
    SimTempExternalGUI --> SevenSegmentDisplay
    SimTempExternalGUI --> RealTimePlot
    SimTempExternalGUI --> ConfigurationPanel
    SimTempExternalGUI --> ExternalSimTempClient
    ConfigurationPanel --> SimTempConfigClient
```

## Communication Protocol

```mermaid
stateDiagram-v2
    [*] --> Disconnected
    
    Disconnected --> Connecting: User clicks Connect
    Connecting --> Connected: TCP handshake OK
    Connecting --> Disconnected: Connection failed
    
    Connected --> Configured: Send configuration
    Connected --> Monitoring: Start monitoring
    Connected --> Disconnected: Connection lost
    
    Configured --> Monitoring: Start monitoring
    Configured --> Connected: Stop configuration
    
    Monitoring --> Connected: Stop monitoring
    Monitoring --> Disconnected: Connection lost
    Monitoring --> Monitoring: Receive data
    
    state Monitoring {
        [*] --> Polling
        Polling --> Waiting: GET_TEMP sent
        Waiting --> Processing: Response received
        Processing --> Polling: Data processed
    }
```

## Alarm State Diagram

```mermaid
stateDiagram-v2
    [*] --> Normal
    
    Normal --> Warning: Temp > Threshold - 5°C
    Warning --> Normal: Temp < Threshold - 5°C
    Warning --> Alarm: Temp >= Threshold
    
    Alarm --> Warning: Temp < Threshold
    Alarm --> Critical: Temp > Threshold + 10°C
    
    Critical --> Alarm: Temp <= Threshold + 10°C
    
    state Normal {
        [*] --> GreenDisplay
        GreenDisplay --> NormalDial
        NormalDial --> NoAlarmLamp
    }
    
    state Warning {
        [*] --> YellowDisplay
        YellowDisplay --> WarningDial
    }
    
    state Alarm {
        [*] --> RedDisplay
        RedDisplay --> AlarmDial
        AlarmDial --> RedLampOn
        RedLampOn --> FlashingDisplay
    }
    
    state Critical {
        [*] --> FlashingRed
        FlashingRed --> CriticalDial
        CriticalDial --> FastFlashing
    }
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        DEV[Developer Machine]
        GIT[Git Repository]
        TEST[Local Testing]
    end
    
    subgraph "Deployment Package"
        VENV[Python Virtual Env]
        DEPS[Dependencies<br/>requirements.txt]
        SCRIPTS[Launch Scripts]
        DOCS[Documentation]
    end
    
    subgraph "Target Deployment"
        HOST[Host System]
        GUI_APP[SimTemp GUI App]
        CONFIG[Configuration Files]
        LOGS[Log Files]
    end
    
    subgraph "External Systems"
        ARM_TARGET[ARM Target<br/>QEMU + SimTemp]
        NETWORK[Network Connection<br/>TCP Port 4445]
        MONITORING[External Monitoring<br/>Optional]
    end
    
    DEV --> GIT
    GIT --> TEST
    TEST --> VENV
    VENV --> DEPS
    DEPS --> SCRIPTS
    SCRIPTS --> DOCS
    
    DOCS --> HOST
    HOST --> GUI_APP
    GUI_APP --> CONFIG
    GUI_APP --> LOGS
    
    GUI_APP <--> NETWORK
    NETWORK <--> ARM_TARGET
    GUI_APP -.-> MONITORING
```

## Performance and Scalability

```mermaid
graph LR
    subgraph "Performance Metrics"
        CPU[CPU Usage<br/>< 5%]
        MEM[Memory<br/>< 100MB]
        NET[Network<br/>< 1KB/s]
        RESP[Response<br/>< 100ms]
    end
    
    subgraph "Scalability Factors"
        SENSORS[Multiple Sensors<br/>1-10 concurrent]
        FREQ[Sample Frequency<br/>0.2-20 Hz]
        HISTORY[Data History<br/>300-1800 points]
        CLIENTS[GUI Clients<br/>1-5 concurrent]
    end
    
    subgraph "Optimization Strategies"
        CIRCULAR[Circular Buffers]
        LAZY[Lazy Rendering]
        BATCH[Batch Processing]
        CACHE[Widget Caching]
    end
    
    SENSORS --> CIRCULAR
    FREQ --> LAZY
    HISTORY --> BATCH
    CLIENTS --> CACHE
    
    CIRCULAR --> CPU
    LAZY --> MEM
    BATCH --> NET
    CACHE --> RESP
```