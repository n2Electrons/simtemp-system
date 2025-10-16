## Cómo Jenkins Identifica y Ejecuta Tests QEMU

### Resumen de la Solución

La configuración propuesta permite a Jenkins identificar automáticamente que los tests de `qemu_integration` deben ejecutarse en QEMU y recolectar los resultados de manera estructurada.

### 1. Identificación de Tests QEMU

Jenkins identifica que un test suite debe ejecutarse en QEMU mediante la configuración en `simtemp_tests.yml`:

```yaml
qemu_integration:
  execution_environment:
    type: "qemu"  # ← Esto indica a Jenkins que use QEMU
    platform: "arm"
    machine: "virt"
    timeout_minutes: 10
```

### 2. Configuración de Ejecución

La sección `qemu_config` especifica cómo ejecutar QEMU:

```yaml
qemu_config:
  runner_script: "deployment/qemu/run-f-k1-tc-002-jenkins.sh"  # Script principal
  results_mount_path: "/mnt/workspace"  # Punto de montaje en QEMU
  auto_shutdown: true  # QEMU se cierra automáticamente
  console_output: true  # Capturar salida de consola
```

### 3. Recolección de Resultados

La configuración `results_collection` define cómo Jenkins obtendrá los resultados:

```yaml
results_collection:
  type: "shared_filesystem"  # Resultados via filesystem 9P compartido
  output_formats: ["junit_xml", "json_report", "console_log"]
  results_base_path: "simtemp/tests/results"
  patterns:
    junit_xml: "*-qemu-results.xml"    # Para publishTestResults()
    json_report: "*-qemu-report.json"  # Reportes detallados
    console_log: "*-qemu-console.log"  # Logs de QEMU
    artifacts: "test-results/*"        # Artefactos adicionales
```

### 4. Flujo de Ejecución en Jenkins

1. **Identificación**: Jenkins lee `simtemp_tests.yml` y encuentra `execution_environment.type: "qemu"`

2. **Preparación**: Jenkins ejecuta `setupQemuTestEnvironment()` para verificar QEMU

3. **Ejecución**: Jenkins ejecuta el script definido en `qemu_config.runner_script`

4. **Recolección**: Jenkins busca archivos según los `patterns` definidos

5. **Publicación**: Jenkins publica resultados usando:
   - `publishTestResults()` para XML JUnit
   - `archiveArtifacts()` para JSON y logs

### 5. Scripts de Integración

#### jenkins_qemu_integration.py
```bash
# Listar suites QEMU
python3 simtemp/tests/jenkins_qemu_integration.py list_qemu_suites

# Ejecutar suite específico
python3 simtemp/tests/jenkins_qemu_integration.py execute qemu_integration

# Recolectar resultados
python3 simtemp/tests/jenkins_qemu_integration.py collect qemu_integration
```

#### En el Jenkinsfile
```groovy
// Cargar configuración
def testConfig = readYaml file: 'simtemp/tests/config/simtemp_tests.yml'

// Encontrar suites QEMU
testConfig.tests.each { suiteName, suiteConfig ->
    if (suiteConfig.execution_environment?.type == 'qemu') {
        // Ejecutar en QEMU
        sh "python3 simtemp/tests/jenkins_qemu_integration.py execute ${suiteName}"
        
        // Recolectar resultados
        publishTestResults(testResultsPattern: "${resultsDir}/*-qemu-results.xml")
        archiveArtifacts(artifacts: "${resultsDir}/*-qemu-report.json")
    }
}
```

### 6. Resultados y Reportes

Los resultados se recolectan automáticamente en:

- **XML JUnit**: Para integración con Jenkins UI de tests
- **JSON Reports**: Para análisis detallado y métricas
- **Console Logs**: Para debugging de ejecución QEMU
- **Artifacts**: Archivos adicionales generados por tests

### 7. Ventajas de esta Aproximación

✅ **Automática**: Jenkins detecta automáticamente tests QEMU
✅ **Configurable**: Timeouts, patterns y configuración específica por suite  
✅ **Robust**: Manejo de errores y timeouts
✅ **Trazable**: Resultados estructurados para reportes
✅ **Escalable**: Fácil añadir nuevos suites QEMU
✅ **Debuggable**: Logs de consola y artefactos preservados

### 8. Ejemplo de Uso en Pipeline

```groovy
pipeline {
    stages {
        stage('QEMU Tests') {
            steps {
                script {
                    // Automáticamente ejecuta todos los suites tipo 'qemu'
                    load('deployment/jenkins/jenkins-qemu-integration.groovy').runQemuIntegrationTests()
                }
            }
        }
    }
    post {
        always {
            // Resultados automáticamente publicados por el script
            echo "QEMU test results published automatically"
        }
    }
}
```

Esta solución permite que Jenkins maneje transparentemente la ejecución de tests en QEMU y recolecte todos los resultados necesarios para generar reportes comprehensivos.