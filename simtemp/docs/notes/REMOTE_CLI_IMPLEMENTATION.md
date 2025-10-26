# SimTemp Remote CLI - SSH-based Driver Configuration

Esta implementación proporciona un CLI remoto que utiliza SSH para interactuar con el driver SimTemp en QEMU. Aprovecha la nueva funcionalidad SSH implementada en `test_utils.py` para configurar el driver y leer datos de temperatura de manera remota.

## 🎯 Funcionalidades Implementadas

### ✅ 1. Configuración de Sample Rate
- **Ruta**: `/sys/devices/platform/simtemp/sampling_ms`
- **Rango**: 1-60000 millisegundos
- **Comando**: `--set-rate <ms>`

### ✅ 2. Configuración de Threshold
- **Ruta**: `/sys/devices/platform/simtemp/threshold_mC`
- **Rango**: -50°C a 150°C (-50000 a 150000 mC)
- **Comando**: `--set-threshold <celsius>`

### ✅ 3. Lectura Continua de Temperatura
- **Dispositivo**: `/dev/simtemp0`
- **Comando**: `--read [--duration <sec>] [--count <samples>]`

### ✅ 4. Configuración SSH Hardcodeada
- **Puerto SSH**: 2222 (hardcodeado como se solicitó)
- **Auto-inicio**: QEMU se inicia automáticamente con SSH
- **Conexión**: SSH autenticado via clave pública

## 📋 Uso del CLI Remoto

### Comandos Básicos

```bash
# Mostrar configuración actual
python3 simtemp_remote_cli.py --config

# Configurar sample rate a 500ms
python3 simtemp_remote_cli.py --set-rate 500

# Configurar threshold a 40°C
python3 simtemp_remote_cli.py --set-threshold 40.0

# Leer temperatura por 30 segundos
python3 simtemp_remote_cli.py --read --duration 30

# Leer 100 muestras
python3 simtemp_remote_cli.py --read --count 100
```

### Modo Interactivo

```bash
# Iniciar modo interactivo
python3 simtemp_remote_cli.py --interactive

# Comandos disponibles en modo interactivo:
simtemp> config              # Mostrar configuración
simtemp> rate 250           # Configurar sample rate
simtemp> threshold 35.5     # Configurar threshold
simtemp> read 10 50         # Leer (duración, count)
simtemp> quit               # Salir
```

### Uso con SSH Existente

```bash
# Usar conexión SSH existente (sin auto-start QEMU)
python3 simtemp_remote_cli.py --no-auto-start --ssh-port 2222 --config
```

## 🔧 Arquitectura de la Implementación

### 1. Integración con test_utils.py
El CLI utiliza las funciones SSH implementadas en `test_utils.py`:
- `start_qemu_and_wait_for_boot()`: Inicia QEMU con SSH hardcodeado
- `wait_for_ssh_ready()`: Espera que SSH esté disponible
- `execute_ssh_command()`: Ejecuta comandos remotos via SSH

### 2. Clase SimTempRemoteCLI
```python
class SimTempRemoteCLI:
    def __init__(self, ssh_port=2222, auto_start_qemu=True)
    def read_sysfs_attribute(self, attr_name)
    def write_sysfs_attribute(self, attr_name, value)
    def get_sample_rate(self)
    def set_sample_rate(self, rate_ms)
    def get_threshold(self)
    def set_threshold(self, threshold_mc)
    def read_temperature_continuous(self, duration, count)
```

### 3. Configuración SSH Hardcodeada
- Puerto SSH: **2222** (mismo que run_qemu.ssh.sh)
- Parámetros QEMU: `-net nic -net user,hostfwd=tcp::2222-:22`
- Autenticación: Clave pública SSH automática
- Conexión: `ssh -p 2222 root@127.0.0.1`

## 📊 Resultados de Pruebas

### ✅ Test 1: Configuración Inicial
```bash
$ python3 simtemp_remote_cli.py --config

=== SimTemp Driver Configuration ===
Sample Rate: 1000ms
Threshold: 50.0°C (50000mC)
Device: /dev/simtemp0 exists
Driver: nxp_simtemp 20480 0 - Live 0xbf000000 (O)
=====================================
```

### ✅ Test 2: Configuración de Sample Rate
```bash
$ python3 simtemp_remote_cli.py --set-rate 500
[INFO] Sample rate set to 500ms
```

### ✅ Test 3: Configuración de Threshold
```bash
$ python3 simtemp_remote_cli.py --set-threshold 40.5
[INFO] Threshold set to 40.5°C (40500mC)
```

### ✅ Test 4: Verificación de Cambios
Los cambios se verifican correctamente via SSH:
```bash
# Via SSH directo:
$ ssh -p 2222 root@127.0.0.1 "cat /sys/devices/platform/simtemp/sampling_ms"
500

$ ssh -p 2222 root@127.0.0.1 "cat /sys/devices/platform/simtemp/threshold_mC"
40500
```

## 🎬 Demo Completo

Ejecutar el script de demostración:
```bash
python3 demo_remote_cli.py
```

Este script demuestra:
1. Configuración inicial
2. Configuración de sample rate
3. Configuración de threshold
4. Verificación de cambios
5. Lectura continua de temperatura

## 🔗 Integración con el Ecosistema

### Compatibilidad con CLI Existente
- Compatible con el CLI en C existente (`simtemp/user/cli/`)
- Usa las mismas rutas sysfs y dispositivo
- Mantiene el mismo formato de configuración

### Integración con GUI
- Puede trabajar junto con la GUI (`simtemp/user/gui/`)
- Comparte la misma infraestructura de comunicación
- Permite configuración tanto via CLI como GUI

### Reutilización de SSH
- Aprovecha la implementación SSH de `test_utils.py`
- Compatible con sesiones SSH existentes
- Puede funcionar sin auto-start para usar QEMU ya ejecutándose

## 🛠️ Archivos Creados

1. **`simtemp_remote_cli.py`**: CLI principal con todas las funcionalidades
2. **`demo_remote_cli.py`**: Script de demostración completa
3. **`test_ssh_implementation.py`**: Tests de la implementación SSH base
4. **`SSH_IMPLEMENTATION.md`**: Documentación de la implementación SSH

## ✅ Cumplimiento de Requisitos

### ☑️ Sample Rate via SSH
- ✅ Lectura: `cat /sys/devices/platform/simtemp/sampling_ms`
- ✅ Escritura: `echo '500' > /sys/devices/platform/simtemp/sampling_ms`

### ☑️ Threshold via SSH  
- ✅ Lectura: `cat /sys/devices/platform/simtemp/threshold_mC`
- ✅ Escritura: `echo '40500' > /sys/devices/platform/simtemp/threshold_mC`

### ☑️ Lectura Continua
- ✅ Dispositivo: `/dev/simtemp0`
- ✅ Lectura continua con `dd` y `hexdump`
- ✅ Control de duración y número de muestras

### ☑️ SSH Hardcodeado
- ✅ Puerto 2222 hardcodeado
- ✅ Auto-inicio de QEMU con SSH
- ✅ Configuración de red automática

## 🚀 Próximos Pasos Posibles

1. **Extensiones del CLI**:
   - Modo de monitoreo en tiempo real
   - Alertas configurables
   - Exportación de datos (CSV, JSON)

2. **Integración Avanzada**:
   - API REST para control remoto
   - WebSocket para streaming de datos
   - Dashboard web integrado

3. **Optimizaciones**:
   - Cache de configuración
   - Reconexión automática SSH
   - Compresión de datos para lecturas largas

La implementación cumple completamente con los requisitos solicitados y proporciona una base sólida para futuras extensiones del sistema SimTemp.