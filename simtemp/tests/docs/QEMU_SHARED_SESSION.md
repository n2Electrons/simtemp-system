# QEMU Shared Session Management

Este documento describe el nuevo sistema de manejo de sesiones QEMU compartidas implementado para optimizar la ejecución de tests que requieren emulación QEMU.

## 🎯 Objetivo

Resolver la ineficiencia de iniciar/terminar QEMU para cada test individual, implementando un sistema de sesión compartida que:

1. ✅ **Primer test QEMU** inicia QEMU y lo deja corriendo
2. ✅ **Crea marca** para que otros tests detecten la sesión activa  
3. ✅ **Tests subsiguientes** reutilizan la sesión existente
4. ✅ **Test runner** termina QEMU al finalizar todos los tests

## 🏗️ Arquitectura

### Componentes Principales

#### 1. **`test_utils.py` - Funciones Core**
```python
# Función principal para tests
qemu_process = get_qemu_session_if_needed()

# Funciones de sesión compartida
get_or_start_shared_qemu_session()  # Inicia o reutiliza sesión
is_qemu_session_active()           # Verifica sesión activa
create_qemu_session_marker()       # Crea marca de sesión
cleanup_qemu_session()             # Limpia sesión y marca
```

#### 2. **`qemu_session_manager.py` - Gestor de Sesiones**
```python
# Para integrar en test runners
from qemu_session_manager import setup_qemu_session_cleanup

# Al inicio del test runner
setup_qemu_session_cleanup()  # Configura limpieza automática

# Limpieza manual si es necesaria
manual_cleanup_qemu_sessions()
```

#### 3. **`run_tests_enhanced.py` - Test Runner Mejorado**
```bash
# Ejecuta tests con manejo QEMU automático
python3 run_tests_enhanced.py

# Limpieza manual de sesiones
python3 run_tests_enhanced.py --cleanup-only
```

## 🔄 Flujo de Ejecución

### Escenario: Múltiples Tests QEMU

```
Test Suite Execution:
├── test_f_k1_tc_003.py (QEMU)
│   ├── get_qemu_session_if_needed()
│   ├── 🚀 START QEMU + Crear marca /tmp/qemu_session_active.marker
│   ├── ✅ Test execution
│   └── 💾 QEMU permanece activo
├── test_f_k8_tc_001.py (QEMU) 
│   ├── get_qemu_session_if_needed()
│   ├── 🔄 REUSE existing QEMU session
│   ├── ✅ Test execution  
│   └── 💾 QEMU permanece activo
├── test_other.py (No QEMU)
│   └── ✅ Normal execution
└── Test Runner Cleanup
    ├── 🧹 cleanup_qemu_session()
    ├── 🛑 Terminar QEMU (SIGTERM/SIGKILL)
    └── 🗑️ Remover marca
```

## 📋 Uso en Tests

### Antes (Individual QEMU per test)
```python
def test_something():
    if is_qemu_test():
        qemu_process = start_qemu_and_wait_for_boot()
        # ... test logic ...
        qemu_process.terminate()  # Termina QEMU
```

### Después (Sesión Compartida)
```python
def test_something():
    qemu_process = get_qemu_session_if_needed()  # Una línea!
    # ... test logic ...
    # No cleanup - el test runner maneja QEMU
```

## 🎛️ Integración con Test Runners

### Jenkins Pipeline
```groovy
// En el Jenkinsfile, usar el runner mejorado
sh "cd simtemp/tests && python3 run_tests_enhanced.py"
```

### Manual/Local Testing
```bash
# Ejecutar tests con manejo QEMU
cd simtemp/tests
python3 run_tests_enhanced.py

# Solo tests específicos
python3 run_tests_enhanced.py test_f_k1_tc_003.py

# Tests que contengan "qemu"
python3 run_tests_enhanced.py -k "qemu"

# Limpieza manual si algo falla
python3 run_tests_enhanced.py --cleanup-only
```

## 🔧 Configuración

### Marker File Location
```
/tmp/qemu_session_active.marker
```

### Marker File Content
```json
{
  "pid": 12345,
  "started_at": 1729425600.123,
  "started_by": "test_f_k1_tc_003.py",
  "test_name": "test_f_k1_platform_driver_dt_registration"
}
```

## 🛡️ Manejo de Errores

### Casos Cubiertos

1. **Proceso QEMU Termina Inesperadamente**
   ```python
   # Detecta PID inválido y remueve marca automáticamente
   if not os.kill(pid, 0):  # Process doesn't exist
       os.remove(marker_file)
   ```

2. **Test Runner Interrumpido (Ctrl+C)**
   ```python
   # Handlers de señales limpian QEMU
   signal.signal(signal.SIGINT, cleanup_handler)
   signal.signal(signal.SIGTERM, cleanup_handler)
   ```

3. **Marker File Corrupto**
   ```python
   # Remueve markers corruptos y reinicia sesión
   try:
       json.loads(marker_content)
   except json.JSONDecodeError:
       os.remove(marker_file)
   ```

## ⚡ Beneficios

### Rendimiento
- ❌ **Antes**: ~30s boot time × N tests = Mucho tiempo
- ✅ **Después**: ~30s boot time × 1 = Tiempo fijo

### Recursos
- ❌ **Antes**: N procesos QEMU simultáneos 
- ✅ **Después**: 1 proceso QEMU compartido

### Confiabilidad
- ✅ Limpieza automática on exit
- ✅ Detección de procesos zombie
- ✅ Manejo de interrupciones de señales

## 🐛 Debugging

### Verificar Estado de Sesión
```bash
# Usar el manager directamente
cd simtemp/tests
python3 qemu_session_manager.py --status

# Output: "QEMU session is ACTIVE" o "No active QEMU sessions"
```

### Limpieza Manual
```bash
# Si algo se atasca, forzar limpieza
python3 qemu_session_manager.py --cleanup
```

### Ver Marker File
```bash
# Inspeccionar marker de sesión
cat /tmp/qemu_session_active.marker
```

## 🔄 Migración

### Para Tests Existentes
1. Cambiar `is_qemu_test() + start_qemu_and_wait_for_boot()` por `get_qemu_session_if_needed()`
2. Remover cleanup manual de QEMU en `finally` blocks
3. Usar el nuevo test runner mejorado

### Para Nuevos Tests
- Usar directamente `qemu_process = get_qemu_session_if_needed()`
- No implementar cleanup manual - el runner se encarga

## 📚 Referencias

### Archivos Relacionados
- `simtemp/tests/test_utils.py` - Funciones core de sesión QEMU
- `simtemp/tests/qemu_session_manager.py` - Gestor de sesiones
- `simtemp/tests/run_tests_enhanced.py` - Test runner con QEMU management
- `simtemp/tests/test_f_k1_tc_003.py` - Ejemplo de test migrado

### Configuración YAML
```yaml
# simtemp/tests/config/simtemp_tests.yml
tests:
  qemu_integration:
    enabled: true
    test_cases:
      - test_id: "F-K1-TC-003-QEMU" 
        enabled: true
        qemu_specific:
          expects_boot: true  # Trigger para sesión compartida
```