# Test Monitor - Integración Híbrida con Manejo QEMU

## 🎯 Descripción

`test_monitor.py` es una **integración híbrida** que combina:

- ✅ **Funcionalidad completa** de `driver_tester.py` (reportes HTML, GitHub, traceabilidad)
- ✅ **Manejo avanzado de sesiones QEMU** compartidas  
- ✅ **Compatibilidad total** con Jenkins pipeline existente
- ✅ **Sin cambios disruptivos** - funciona como drop-in replacement

## 🏗️ Arquitectura de Integración

```
Jenkins Pipeline
       ↓
test_monitor.py (wrapper con QEMU management)
       ↓
driver_tester.py (funcionalidad original)
       ↓
pytest + reports + GitHub integration
```

### Flujo de Ejecución:

1. **Jenkins llama** `test_monitor.py` (configurado en `pipeline_config.yml`)
2. **Test Monitor** inicializa manejo de sesiones QEMU
3. **Ejecuta** `driver_tester.py` con todos los argumentos originales
4. **Driver Tester** ejecuta tests, genera reportes, integra GitHub
5. **Test Monitor** limpia sesiones QEMU al finalizar

## 🚀 Uso

### Jenkins (Automático)
```yaml
# pipeline_config.yml - Ya configurado
testing:
  test_composer: "simtemp/tests/test_monitor.py"
```

Jenkins ejecutará automáticamente con manejo QEMU.

### Manual/Local
```bash
cd simtemp/tests

# Ejecutar tests completos (igual que antes)
python3 test_monitor.py

# Con verbose output
python3 test_monitor.py --verbose

# Con directorio específico de reportes
python3 test_monitor.py --output-dir ../reports

# Solo manejo QEMU
python3 test_monitor.py --qemu-status      # Ver estado
python3 test_monitor.py --cleanup-qemu     # Limpiar sesiones
```

## 🎛️ Funcionalidades

### Heredadas de `driver_tester.py`:
- ✅ Ejecución completa de pytest
- ✅ Generación de reportes HTML detallados
- ✅ Reportes JSON estructurados  
- ✅ Integración con GitHub Issues
- ✅ Traceabilidad de requirements
- ✅ Manejo de múltiples test suites
- ✅ Configuración YAML flexible

### Nuevas funcionalidades QEMU:
- ✅ **Sesiones compartidas** entre tests
- ✅ **Startup optimizado** - QEMU boot una sola vez
- ✅ **Cleanup automático** al terminar test suite
- ✅ **Manejo de señales** (Ctrl+C, SIGTERM)
- ✅ **Estado de sesión** verificable
- ✅ **Limpieza manual** cuando sea necesario

## 🔄 Comparación de Funcionamiento

### Antes (driver_tester.py directamente):
```
Test 1: F-K1-TC-003 (QEMU)
├── 🚀 Start QEMU (30s boot)
├── ✅ Execute test  
└── 🛑 Terminate QEMU

Test 2: F-K8-TC-001 (QEMU)  
├── 🚀 Start QEMU (30s boot)
├── ✅ Execute test
└── 🛑 Terminate QEMU

Total: ~60s + test time
```

### Después (test_monitor.py):
```
Test Suite:
├── 🎯 Initialize QEMU session management
├── Test 1: F-K1-TC-003 (QEMU)
│   ├── 🚀 Start QEMU (30s boot) + Create marker
│   └── ✅ Execute test (QEMU stays running)
├── Test 2: F-K8-TC-001 (QEMU)
│   ├── 🔄 Reuse existing QEMU session  
│   └── ✅ Execute test (instant start)
├── Other tests...
└── 🧹 Cleanup QEMU session + Remove marker

Total: ~30s + test time (fixed overhead)
```

## 📊 Output Example

```bash
$ python3 test_monitor.py --verbose

🚀 Starting Test Monitor with Enhanced QEMU Management
✅ QEMU session management initialized  
🎯 QEMU sessions will be managed automatically
Executing: python3 driver_tester.py --verbose
============================================================

=== Driver Testing Orchestrator ===
Reading configuration from: simtemp_tests.yml
Found 5 test suites...
Executing pytest with enhanced reporting...

[... driver_tester.py output ...]

=== Test Reports Generated ===
- HTML Report: ../reports/test_report_detailed.html
- JSON Report: ../reports/test_report_detailed.json
- GitHub Integration: 3 issues linked

============================================================
📊 Test execution completed with exit code: 0
✅ All tests completed successfully!

🧹 Performing final QEMU session cleanup...
✅ QEMU sessions cleaned up
```

## 🛠️ Configuración

### Pipeline Integration (ya configurado):
```yaml
# simtemp/pipeline_config.yml
testing:
  test_composer: "simtemp/tests/test_monitor.py"  # Changed from driver_tester.py
  test_config_file: "simtemp/tests/config/simtemp_tests.yml"
  reports_directory: "simtemp/reports"
```

### QEMU Test Detection:
```yaml  
# simtemp/tests/config/simtemp_tests.yml
tests:
  qemu_integration:
    enabled: true
    test_cases:
      - test_id: "F-K1-TC-003-QEMU"
        enabled: true
        qemu_specific:
          expects_boot: true  # Trigger for shared session
```

## 🐛 Troubleshooting

### Ver estado QEMU:
```bash
python3 test_monitor.py --qemu-status
# Output: 🟢 QEMU session is ACTIVE | 🔴 No active QEMU sessions
```

### Limpiar sesiones atoradas:
```bash
python3 test_monitor.py --cleanup-qemu
# Output: ✅ QEMU sessions cleaned up
```

### Debug manual:
```bash
# Ver marker file
cat /tmp/qemu_session_active.marker

# Verificar procesos QEMU
ps aux | grep qemu
```

## 📈 Beneficios de la Integración Híbrida

### ✅ **Ventajas**:
- **Sin disrupción**: Drop-in replacement para Jenkins
- **Funcionalidad completa**: Mantiene todas las características existentes
- **Optimización QEMU**: Reduce tiempo de tests significativamente  
- **Backward compatible**: Funciona con configuraciones existentes
- **Flexible**: Permite uso manual y automatizado

### ✅ **Compatibilidad**:
- ✅ Jenkins Pipeline (sin cambios en Jenkinsfile)
- ✅ Configuración YAML existente
- ✅ Reportes HTML/JSON existentes
- ✅ GitHub Issues integration
- ✅ Test suites configurados

### ✅ **Evolución gradual**:
- Si QEMU management falla → funciona como `driver_tester.py` normal
- Tests no-QEMU → sin cambios en comportamiento
- Tests QEMU → automáticamente optimizados

## 🔄 Migración

### Para el pipeline:
✅ **Ya está configurado** - solo usar el nuevo `test_composer`

### Para desarrollo local:
```bash
# Antes
python3 driver_tester.py --verbose

# Después  
python3 test_monitor.py --verbose  # Misma funcionalidad + QEMU management
```

### Rollback si es necesario:
```yaml
# Simplemente cambiar de vuelta en pipeline_config.yml
testing:
  test_composer: "simtemp/tests/driver_tester.py"  # Rollback
```