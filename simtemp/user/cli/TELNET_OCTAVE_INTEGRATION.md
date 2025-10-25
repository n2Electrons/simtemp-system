# SimTemp - Telnet Integration with Octave

## Wave Generation via Telnet

The SimTemp system now supports sending signals directly to the temperature sensor's telnet port using Octave and the continuous wave generator.

## Telnet Port Configuration

### Specify Host and Port
```bash
# Basic telnet connection
python3 continuous_wave_generator.py --host 192.168.1.100 --port 23

# Custom port
python3 continuous_wave_generator.py --host sensor.local --port 9999

# With wave parameters
python3 continuous_wave_generator.py \
    --host 192.168.1.100 --port 23 \
    --wave sine --frequency 0.1 --amplitude 10.0 --offset 30.0
```

### If local device doesn't exist:
```
ERROR: Device /dev/simtemp not found
TIP: Use --host and --port for telnet connection to remote sensor
```

## Available Wave Types

| Type | Description | Usage |
|------|-------------|-----|
| `sine` | Smooth sinusoidal wave | Gradual temperature variations |
| `square` | Square wave | Abrupt temperature changes |
| `triangle` | Triangular wave | Linear ramps |
| `sawtooth` | Sawtooth wave | Asymmetric ramps |
| `noise` | Random noise | Random fluctuations |
| `step` | Steps | Discrete levels |
| `ramp` | Slow ramp | Gradual increment/decrement |

## Telnet Protocol

### Sensor Commands
```
SET_TEMP <temperature>  - Set temperature in °C
GET_TEMP                - Get current temperature
STATUS                  - Sensor status
HELP                    - Command help
QUIT                    - Close connection
```

### Telnet Session Example
```
$ telnet 192.168.1.100 23
SimTemp Sensor v1.0 - Telnet Interface
Type 'HELP' for commands or 'QUIT' to exit
simtemp> SET_TEMP 25.5
OK: Temperature set to 25.50°C
simtemp> GET_TEMP
TEMP: 25.50°C
simtemp> STATUS
STATUS: OK, Temp=25.50°C, Uptime=120s, Clients=1
```

## Wave Generation Examples

### Sine Wave for Gradual Tests
```bash
python3 continuous_wave_generator.py \
    --host 192.168.1.100 --port 23 \
    --wave sine \
    --frequency 0.1 \
    --amplitude 8.0 \
    --offset 30.0 \
    --duration 60
```
- Frequency: 0.1 Hz (10 second period)
- Temperature: 22°C to 38°C (30±8°C)
- Duración: 60 segundos

### Onda Cuadrada para Pruebas de Stress
```bash
python3 continuous_wave_generator.py \
    --host 192.168.1.100 --port 23 \
    --wave square \
    --frequency 0.05 \
    --amplitude 15.0 \
    --offset 35.0 \
    --duration 120
```
- Cambios bruscos cada 20 segundos
- Temperatura: 20°C ↔ 50°C
- Duración: 2 minutos

### Ruido Aleatorio para Pruebas de Robustez
```bash
python3 continuous_wave_generator.py \
    --host 192.168.1.100 --port 23 \
    --wave noise \
    --amplitude 12.0 \
    --offset 40.0 \
    --duration 30
```
- Variaciones aleatorias
- Rango: 28°C a 52°C
- Duración: 30 segundos

## 🐍 Integración con Octave

### Patrones Octave (si disponible)
```bash
# Listar patrones disponibles
python3 continuous_wave_generator.py --list-patterns

# Usar patrón específico
python3 continuous_wave_generator.py \
    --host 192.168.1.100 --port 23 \
    --pattern thermal_stress_test
```

### Fallback sin Octave
Si Octave no está disponible, el sistema usa generadores matemáticos Python nativos:
```
Warning: Octave temperature generator not available
✓ Using built-in waveform generators
```

## 🧪 Servidor de Pruebas

### Simulador Telnet Local
```bash
# Iniciar servidor simulado
python3 simtemp_telnet_server.py --port 9999

# Probar con el simulador
python3 continuous_wave_generator.py \
    --host localhost --port 9999 \
    --wave sine --frequency 0.2 --amplitude 5.0
```

### Demo Interactivo
```bash
# Script de demostración
./telnet_wave_demo.sh
```

## 🔧 Parámetros de Configuración

### Parámetros de Onda
```bash
--wave TYPE           # Tipo de onda (sine, square, triangle, etc.)
--frequency HZ        # Frecuencia en Hz (default: 0.1)
--amplitude TEMP      # Amplitud en °C (default: 10.0)
--offset TEMP         # Temperatura base en °C (default: 35.0)
--sampling MS         # Período de muestreo en ms (default: 200)
```

### Parámetros de Conexión
```bash
--host HOST           # Host del sensor (IP o hostname)
--port PORT           # Puerto telnet (default: 23)
--duration SECONDS    # Duración en segundos (opcional)
```

### Parámetros de Operación
```bash
--list-waves          # Listar tipos de onda disponibles
--list-patterns       # Listar patrones Octave disponibles
--status              # Mostrar estado del dispositivo
```

## 📊 Monitoreo en Tiempo Real

Durante la generación de ondas, el sistema muestra:
```
=== SimTemp Continuous Wave Generator ===
Configuring wave generation...
✓ Configured wave: sine
  Frequency: 0.1 Hz
  Amplitude: ±8.0°C
  Offset: 30.0°C
  Sampling: 200ms
Connecting to SimTemp sensor via telnet 192.168.1.100:23
✓ Connected to 192.168.1.100:23
✓ Started wave generation - Press Ctrl+C to stop
Wave sample 1, temp: 30.0°C
Wave sample 21, temp: 32.4°C
Wave sample 41, temp: 35.1°C
...
✓ Wave generation completed
  Total samples: 300
  Duration: 60.0s
  Errors: 0
```

## 🚨 Solución de Problemas

### Error: Connection refused
```bash
ERROR: Failed to connect to sensor: [Errno 111] Connection refused
```
**Solución:** Verificar que el sensor esté disponible en la dirección especificada.

### Error: Device not found
```bash
ERROR: Device /dev/simtemp not found
TIP: Use --host and --port for telnet connection to remote sensor
```
**Solución:** Usar `--host` y `--port` para conexión telnet remota.

### Warning: telnetlib deprecated
```bash
DeprecationWarning: 'telnetlib' is deprecated and slated for removal in Python 3.13
```
**Nota:** Advertencia informativa, no afecta la funcionalidad.

## 🎯 Casos de Uso

### 1. Calibración de Sensor
```bash
# Temperatura constante para calibración
python3 continuous_wave_generator.py \
    --host sensor.local --port 23 \
    --wave sine --frequency 0 --amplitude 0 --offset 25.0
```

### 2. Pruebas de Rango
```bash
# Barrido completo de temperatura
python3 continuous_wave_generator.py \
    --host sensor.local --port 23 \
    --wave ramp --frequency 0.01 --amplitude 25.0 --offset 37.5
```

### 3. Pruebas de Respuesta
```bash
# Cambios rápidos para medir respuesta
python3 continuous_wave_generator.py \
    --host sensor.local --port 23 \
    --wave square --frequency 1.0 --amplitude 10.0 --offset 30.0
```

Esta implementación permite que **Octave envíe señales directamente al puerto telnet del sensor de temperatura**, proporcionando control total sobre los patrones de temperatura para pruebas, calibración y validación del sistema SimTemp.