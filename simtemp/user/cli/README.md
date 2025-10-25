# SimTemp CLI - Pure C Implementation

CLI puro en C para configuración y monitoreo del sensor de temperatura SimTemp NXP.

## Características Principales

- 🌡️ **Monitoreo en Tiempo Real**: Temperatura en consola con timestamps
- 🔧 **Configuración de Thresholds**: Alertas configurables min/max
- 🌐 **Comunicación Remota**: SSH/Telnet para operación remota
- 📊 **Formatos de Salida**: Standard, JSON, CSV, binary
- 🎛️ **Generación de Ondas**: Integración con Python para ondas continuas
- ⚙️ **Sampling Configurable**: Períodos de muestreo ajustables

## 🚀 Uso Rápido

### Operación Local
```bash
# Compilar
make

# Monitorear temperatura
./simtemp_cli

# Con thresholds de alerta
./simtemp_cli --threshold-min 20.0 --threshold-max 40.0

# Salida JSON
./simtemp_cli --format json --output temp.json
```

### Operación Remota
```bash
# SSH remoto
./simtemp_cli --host 192.168.1.100 --user root

# Telnet
./simtemp_cli --host target.local --telnet --port 23
```

### Generación de Ondas
```bash
# Onda seno
python3 continuous_wave_generator.py --wave sine --frequency 0.1 --amplitude 10.0

# Via Telnet (SOLUCIÓN PRINCIPAL)
python3 continuous_wave_generator.py --host 192.168.1.100 --port 23 --wave sine

# Listar tipos de onda
python3 continuous_wave_generator.py --list-waves

# Usar patrón de Octave (si disponible)
python3 continuous_wave_generator.py --host sensor.local --port 23 --pattern thermal_test

# Demo interactivo
./telnet_wave_demo.sh
```

## 📋 Opciones Principales

### Conexión
- `--host HOST`: Host remoto (activa SSH)
- `--port PORT`: Puerto SSH/Telnet (def: 22)
- `--user USER`: Usuario SSH
- `--telnet`: Usar Telnet en lugar de SSH

### Configuración
- `--device PATH`: Ruta del dispositivo (def: /dev/simtemp)
- `--host HOST`: Host telnet para sensor remoto ⭐
- `--port PORT`: Puerto telnet (def: 23) ⭐
- `--threshold-min TEMP`: Threshold mínimo en °C
- `--threshold-max TEMP`: Threshold máximo en °C
- `--interval MS`: Intervalo de muestreo en ms (def: 1000)

### Monitoreo
- `--samples COUNT`: Número de muestras (0 = infinito)
- `--format FORMAT`: Formato: std|json|csv|raw
- `--output FILE`: Archivo de salida
- `--status`: Mostrar estado del dispositivo

## 📊 Formatos de Salida

### Standard
```
2025-10-24 15:30:45.123 - Temperature: 25.3°C
2025-10-24 15:30:46.123 - Temperature: 25.4°C [ALERT]
```

### JSON
```json
{"timestamp": "2025-10-24T15:30:45.123Z", "temperature": 25.3, "unit": "celsius"}
```

### CSV
```csv
timestamp,temperature,unit
2025-10-24T15:30:45.123Z,25.3,celsius
```

## 🌊 Generación de Ondas Continuas

### Tipos de Onda Disponibles
- **sine**: Onda sinusoidal suave
- **square**: Cambios escalonados
- **triangle**: Rampa triangular
- **sawtooth**: Rampa asimétrica
- **noise**: Variación aleatoria
- **step**: Niveles discretos
- **ramp**: Incremento/decremento lineal

### Configuración de Puerto
- **Local**: `/dev/simtemp`, interfaz sysfs
- **Telnet**: Host + puerto para sensor remoto ⭐ **RECOMENDADO**
- **SSH**: Puerto 22 (configurable), autenticación por clave

## 📁 Estructura de Archivos

```
simtemp/user/cli/
├── simtemp_cli.h                    # Header principal
├── main.c                           # Punto de entrada
├── device_ops.c                     # Operaciones locales
├── remote_ops.c                     # Operaciones remotas SSH/Telnet
├── sysfs_config.c                   # Configuración via sysfs
├── continuous_wave_generator.py     # Generación de ondas Python
├── wave_presets.py                  # Configuraciones predefinidas
├── Makefile                         # Sistema de compilación
└── README.md                        # Esta documentación
```

## ⚡ Características Técnicas

- **Tasa de Muestreo**: Hasta 100Hz (10ms)
- **Tiempo de Respuesta**: < 50ms local, 50-200ms remoto
- **Uso de Memoria**: < 2MB CLI, < 10MB generador de ondas
- **Protocolos**: SSH (puerto 22), Telnet (puerto 23)
- **Dependencias**: libc, libssh2, Python 3.6+ (opcional)

## 🔧 Compilación e Instalación

```bash
# Compilar
make

# Debug
make debug

# Limpiar
make clean

# Instalar (requiere root)
sudo make install
```

## ✅ Estado de Implementación

- [x] CLI puro en C completamente funcional
- [x] Comunicación SSH/Telnet remota
- [x] Monitoreo en tiempo real con timestamps
- [x] Configuración de thresholds de alerta
- [x] Múltiples formatos de salida
- [x] Generación de ondas continuas
- [x] Integración con patrones de Octave
- [x] Control directo del puerto del sensor
- [x] Sistema de compilación robusto