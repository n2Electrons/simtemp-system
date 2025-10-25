# SimTemp Continuous Wave Generator Integration

## Overview

Esta integración combina el generador de temperatura Octave (`octv_temp_generator`) con el sensor SimTemp para generar ondas continuas directamente al puerto del dispositivo. Permite simular patrones de temperatura complejos y realistas para pruebas y validación.

## Características Principales

### 🌊 Generación de Ondas Continuas
- **Tipos de onda**: Seno, cuadrada, triangular, diente de sierra, ruido, escalón, rampa
- **Parámetros configurables**: Frecuencia, amplitud, offset, período de muestreo
- **Control en tiempo real**: Inicio/parada, monitoreo de estado

### 🎛️ Integración con Octave
- **Patrones precalculados**: Utiliza patrones generados por GNU Octave
- **Modelos realistas**: Incluye ruido ambiental, respuestas térmicas exponenciales
- **Reproducción fiel**: Mantiene timing y precisión de los patrones originales

### 📊 Configuraciones Predefinidas
- **Presets listos**: 8 configuraciones de onda + 6 patrones Octave
- **Casos de uso específicos**: Ciclos térmicos, simulación ambiental, ruido de sensor
- **Fácil personalización**: Modificación de parámetros via línea de comandos

## Arquitectura del Sistema

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Octave Generator  │    │  Continuous Wave     │    │   SimTemp Device    │
│                     │───▶│      Generator       │───▶│     /dev/simtemp    │
│ temperature_model.m │    │                      │    │                     │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
                                      │                           │
                           ┌──────────▼──────────┐    ┌─────────▼──────────┐
                           │   Wave Presets      │    │  Sysfs Interface   │
                           │  - thermal_cycling  │    │ /sys/class/misc/   │
                           │  - environmental    │    │      simtemp       │
                           │  - hvac_response    │    │                    │
                           └─────────────────────┘    └────────────────────┘
```

## Instalación y Configuración

### Dependencias
```bash
# Instalar NumPy para generación de ondas
pip3 install numpy --user

# Instalar GNU Octave (opcional, para patrones avanzados)
sudo apt install octave

# Verificar que el módulo SimTemp esté cargado
lsmod | grep simtemp
```

### Archivos Principales
```
simtemp/user/cli/
├── continuous_wave_generator.py    # Generador principal
├── wave_presets.py                 # Configuraciones predefinidas  
├── wave_demo.sh                    # Script de demostración
└── models/octv_temp_generator/     # Generador Octave
    ├── temperature_generator.py
    ├── temperature_model.m
    └── temperature_patterns/        # Patrones CSV generados
```

## Uso Básico

### 1. Generación de Ondas Simples

```bash
# Onda senoidal: 0.1 Hz, ±10°C alrededor de 35°C
python3 continuous_wave_generator.py --wave sine --frequency 0.1 --amplitude 10 --offset 35 --duration 60

# Onda cuadrada: cambios rápidos para pruebas térmicas
python3 continuous_wave_generator.py --wave square --frequency 0.5 --amplitude 25 --offset 50 --duration 120

# Ruido: simulación de perturbaciones del sensor
python3 continuous_wave_generator.py --wave noise --amplitude 2 --offset 25 --duration 30
```

### 2. Uso de Patrones Octave

```bash
# Generar patrones con Octave primero
cd models/octv_temp_generator
python3 temperature_generator.py --pattern all

# Usar patrón realista generado
cd ../../
python3 continuous_wave_generator.py --pattern realistic --duration 300

# Usar patrón de rampa exponencial
python3 continuous_wave_generator.py --pattern exponential_ramp --duration 240
```

### 3. Configuraciones Predefinidas

```bash
# Ver configuraciones disponibles
python3 wave_presets.py --info

# Generar comandos para todas las configuraciones
python3 wave_presets.py --commands

# Ejemplo: Ciclos térmicos para pruebas de estrés
python3 continuous_wave_generator.py --wave square --frequency 0.5 --amplitude 25 --offset 50 --sampling 100 --duration 300
```

## Configuraciones Predefinidas

### Ondas Continuas

| Preset | Descripción | Rango Temp | Duración | Uso |
|--------|-------------|------------|----------|-----|
| `thermal_cycling` | Ciclos térmicos rápidos | 25°C - 75°C | 5 min | Pruebas de estrés |
| `environmental_sim` | Simulación ambiental | 16°C - 40°C | 30 min | Variaciones diarias |
| `hvac_response` | Respuesta HVAC | 16°C - 32°C | 10 min | Sistemas de control |
| `sensor_noise` | Ruido del sensor | 24.5°C - 25.5°C | 2 min | Filtrado de ruido |
| `heating_ramp` | Calentamiento gradual | 10°C - 70°C | 8 min | Procesos térmicos |
| `oscillation_test` | Oscilación rápida | 30°C - 40°C | 1 min | Respuesta dinámica |

### Patrones Octave

| Preset | Descripción | Patrón | Duración | Uso |
|--------|-------------|---------|----------|-----|
| `realistic_env` | Ambiente realista | realistic | 5 min | Simulación real |
| `linear_heating` | Calentamiento lineal | linear_ramp | 4 min | Caracterización |
| `exponential_thermal` | Respuesta exponencial | exponential_ramp | 5 min | Masa térmica |
| `noisy_environment` | Ambiente ruidoso | noisy_ramp | 10 min | Condiciones reales |

## Monitoreo y Control

### Monitoreo en Tiempo Real

```bash
# Iniciar generación en background
python3 continuous_wave_generator.py --wave sine --frequency 0.1 --amplitude 15 --offset 40 &

# Monitorear con el CLI
./simtemp-cli --monitor --duration 60 --json

# Ver estado del dispositivo
python3 continuous_wave_generator.py --status
```

### Control Interactivo

```bash
# Script de demostración interactivo
./wave_demo.sh

# Ejecutar demostración automática
./wave_demo.sh --auto
```

## Integración con CLI SimTemp

### Configuración Combinada

```bash
# Terminal 1: Configurar sensor
./simtemp-cli --config --sampling 200 --threshold 45000

# Terminal 2: Iniciar generación de ondas
python3 continuous_wave_generator.py --wave triangle --frequency 0.05 --amplitude 20 --offset 50

# Terminal 3: Monitorear con alertas
./simtemp-cli --monitor --json | grep '"threshold_crossed": true'
```

### Pruebas Automatizadas

```bash
# Prueba completa: configuración + generación + monitoreo
function test_simtemp_integration() {
    echo "Configurando sensor..."
    ./simtemp-cli --config --sampling 100 --threshold 40000
    
    echo "Iniciando generación de onda..."
    python3 continuous_wave_generator.py --wave square --frequency 0.2 --amplitude 15 --offset 45 --duration 30 &
    WAVE_PID=$!
    
    echo "Monitoreando temperatura..."
    ./simtemp-cli --monitor --duration 35 --csv > test_results.csv
    
    echo "Deteniendo generación..."
    kill $WAVE_PID 2>/dev/null
    
    echo "Analizando resultados..."
    python3 -c "
import pandas as pd
df = pd.read_csv('test_results.csv')
alerts = df['threshold_crossed'].sum()
print(f'Alertas detectadas: {alerts}')
print(f'Rango de temperatura: {df[\"temperature_celsius\"].min():.1f}°C - {df[\"temperature_celsius\"].max():.1f}°C')
"
}
```

## Ejemplos Avanzados

### 1. Simulación de Ambiente Realista

```bash
# Generar patrón ambiental complejo con Octave
cd models/octv_temp_generator
python3 temperature_generator.py --pattern realistic

# Reproducir patrón durante 1 hora
cd ../../
python3 continuous_wave_generator.py --pattern realistic --duration 3600

# Monitorear y guardar datos
./simtemp-cli --monitor --csv --duration 3700 > environmental_data.csv
```

### 2. Caracterización de Respuesta del Sensor

```bash
# Barrido de frecuencias para caracterización
for freq in 0.01 0.05 0.1 0.2 0.5 1.0; do
    echo "Probando frecuencia: ${freq} Hz"
    python3 continuous_wave_generator.py --wave sine --frequency $freq --amplitude 10 --offset 35 --duration 60 &
    WAVE_PID=$!
    
    ./simtemp-cli --monitor --csv --duration 65 > "response_${freq}Hz.csv"
    
    kill $WAVE_PID 2>/dev/null
    sleep 5
done
```

### 3. Prueba de Estrés Térmico

```bash
# Ciclos térmicos extremos
python3 continuous_wave_generator.py --wave square --frequency 1.0 --amplitude 30 --offset 50 --sampling 50 --duration 600

# Con monitoreo de alertas
./simtemp-cli --monitor --verbose --duration 610 | tee thermal_stress.log
```

## Troubleshooting

### Problemas Comunes

1. **Dispositivo no encontrado**
   ```bash
   # Verificar que el módulo esté cargado
   lsmod | grep simtemp
   
   # Cargar módulo si es necesario
   sudo modprobe nxp_simtemp
   ```

2. **Permisos insuficientes**
   ```bash
   # Verificar permisos del dispositivo
   ls -la /dev/simtemp
   
   # Verificar permisos de sysfs
   ls -la /sys/class/misc/simtemp/
   ```

3. **Octave no disponible**
   ```bash
   # Instalar Octave
   sudo apt install octave
   
   # Verificar instalación
   octave --version
   ```

4. **NumPy no encontrado**
   ```bash
   # Instalar NumPy
   pip3 install numpy --user
   
   # Verificar instalación
   python3 -c "import numpy; print(numpy.__version__)"
   ```

### Debug y Logging

```bash
# Ejecutar con verbose para debug
python3 continuous_wave_generator.py --wave sine --frequency 0.1 --amplitude 10 --offset 35 --duration 10 2>&1 | tee debug.log

# Verificar estado del kernel
dmesg | grep simtemp | tail -10

# Monitorear estadísticas en tiempo real
watch -n 1 'cat /sys/class/misc/simtemp/stats'
```

## Performance y Limitaciones

### Rendimiento Típico
- **Frecuencia máxima**: ~10 Hz (limitado por sampling del kernel)
- **Precisión de timing**: ±10ms (dependiente del sistema)
- **Rango de temperatura**: -40°C a +125°C
- **Resolución**: 0.001°C (milliCelsius)

### Limitaciones
- Requiere permisos de escritura en sysfs
- La frecuencia está limitada por el período de muestreo del kernel
- Los patrones Octave requieren GNU Octave instalado
- El rendimiento puede variar según la carga del sistema

## Desarrollo y Extensión

### Agregar Nuevos Tipos de Onda

```python
# En WaveformGenerator class
def _custom_wave(self, t: float, frequency: float, amplitude: float, offset: float) -> float:
    """Implementar nueva forma de onda"""
    # Tu implementación aquí
    return custom_value

# Registrar en __init__
self.wave_functions['custom'] = self._custom_wave
```

### Nuevos Presets

```python
# En wave_presets.py
WAVE_PRESETS["new_preset"] = {
    "description": "Nueva configuración personalizada",
    "wave_type": "sine",
    "frequency": 0.2,
    "amplitude": 12.0,
    "offset": 30.0,
    "sampling_ms": 150,
    "duration": 180,
    "use_case": "Caso de uso específico"
}
```

## Conclusión

La integración del generador de ondas continuas con SimTemp proporciona una herramienta poderosa para:

- ✅ **Pruebas exhaustivas** de sensores de temperatura
- ✅ **Simulación realista** de condiciones ambientales  
- ✅ **Caracterización precisa** de respuesta del sistema
- ✅ **Validación automatizada** de algoritmos de control
- ✅ **Generación reproducible** de condiciones de prueba

Esta herramienta es esencial para el desarrollo, validación y caracterización de sistemas de temperatura en entornos controlados.