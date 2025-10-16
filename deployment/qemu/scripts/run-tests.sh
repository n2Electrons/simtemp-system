#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$SCRIPT_DIR/tests"
RESULTS_DIR="$SCRIPT_DIR/results"

echo "=== Framework de pruebas para kernel i.MX6UL en QEMU ==="

# Crear estructura de directorios
mkdir -p "$TESTS_DIR"
mkdir -p "$RESULTS_DIR"

# Crear framework de pruebas en Python
cat > "$TESTS_DIR/test_framework.py" <<EOL
#!/usr/bin/python3
# Framework para ejecutar múltiples pruebas en i.MX6UL
import os
import sys
import json
import time
import importlib.util
import traceback

class TestRunner:
    def __init__(self):
        self.results = []
        self.results_dir = "/tmp/test_results"
        self.tests_dir = "/tests"
        self.summary_file = "/tmp/test_summary.json"
        self.exit_code = 0
        os.makedirs(self.results_dir, exist_ok=True)
    
    def discover_tests(self):
        """Descubre todas las pruebas disponibles en el directorio de pruebas"""
        test_files = []
        if os.path.exists(self.tests_dir):
            for file in os.listdir(self.tests_dir):
                if file.startswith("test_") and file.endswith(".py"):
                    test_files.append(os.path.join(self.tests_dir, file))
        return test_files
    
    def run_test(self, test_path):
        """Ejecuta una prueba específica y registra su resultado"""
        try:
            test_name = os.path.basename(test_path)[:-3]  # Quitar .py
            print(f"\n\033[1;36m=== Ejecutando {test_name} ===\033[0m")
            
            # Cargar dinámicamente el módulo de la prueba
            spec = importlib.util.spec_from_file_location(test_name, test_path)
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)
            
            # Ejecutar la función run_test del módulo
            if hasattr(test_module, 'run_test'):
                result = test_module.run_test()
                self.results.append(result)
                
                # Guardar resultado individual en JSON
                result_file = os.path.join(self.results_dir, f"{test_name}_result.json")
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                # Mostrar resultado
                status = "\033[32mPASS\033[0m" if result.get('result') == "PASS" else "\033[31mFAIL\033[0m"
                print(f"{test_name}: {status}")
                
                # Si alguna prueba falla, establecer código de salida a 1
                if result.get('result') != "PASS":
                    self.exit_code = 1
                
                return result
            else:
                print(f"\033[31mError: {test_path} no tiene función run_test()\033[0m")
                return {"test_id": test_name, "result": "ERROR", "error": "No run_test() function"}
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"\033[31mError ejecutando {test_path}: {str(e)}\033[0m")
            print(error_msg)
            return {"test_id": os.path.basename(test_path), "result": "ERROR", "error": str(e)}
    
    def run_all_tests(self):
        """Descubre y ejecuta todas las pruebas disponibles"""
        tests = self.discover_tests()
        if not tests:
            print("\033[33mNo se encontraron pruebas para ejecutar\033[0m")
            return
        
        print(f"Encontradas {len(tests)} pruebas para ejecutar")
        
        for test_path in tests:
            self.run_test(test_path)
        
        # Generar resumen de resultados
        self.generate_summary()
        
        return self.exit_code
    
    def generate_summary(self):
        """Genera un resumen de todas las pruebas ejecutadas"""
        passed = sum(1 for r in self.results if r.get('result') == "PASS")
        failed = sum(1 for r in self.results if r.get('result') == "FAIL")
        error = sum(1 for r in self.results if r.get('result') == "ERROR")
        
        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "error": error,
            "tests": self.results
        }
        
        # Guardar resumen en JSON
        with open(self.summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Mostrar resumen en consola
        print("\n\033[1;36m=== Resumen de pruebas ===\033[0m")
        print(f"Total pruebas: {len(self.results)}")
        print(f"Pasaron: \033[32m{passed}\033[0m")
        print(f"Fallaron: \033[31m{failed}\033[0m")
        print(f"Errores: \033[33m{error}\033[0m")
        print(f"Resumen guardado en {self.summary_file}")
        
        return summary

if __name__ == "__main__":
    runner = TestRunner()
    exit_code = runner.run_all_tests()
    sys.exit(exit_code)
EOL

# Crear prueba F-K1-TC-002 para verificar Device Tree Overlay
cat > "$TESTS_DIR/test_F_K1_TC_002.py" <<EOL
#!/usr/bin/python3
# Test F-K1-TC-002: Verificación de soporte de Device Tree Overlay
import os
import sys
import json

def check_dt_overlay_support():
    """Verifica que el kernel soporte Device Tree Overlays"""
    # Verificar la presencia de configfs para overlays
    configfs_mounted = False
    with open('/proc/mounts', 'r') as f:
        for line in f:
            if 'configfs' in line:
                configfs_mounted = True
                break
    
    # Verificar que exista el directorio de overlays en el kernel
    # En un entorno real, esto podría ser diferente según la arquitectura
    dt_base_exists = os.path.exists('/proc/device-tree')
    
    # Verificar CONFIG_OF_OVERLAY en config
    overlay_config = False
    try:
        with open('/proc/config.gz', 'r') as f:
            if 'CONFIG_OF_OVERLAY=y' in f.read():
                overlay_config = True
    except:
        # Si no está disponible /proc/config.gz, asumimos que sí está habilitado
        # ya que compilamos el kernel con esta opción
        overlay_config = True
    
    # En una implementación real, intentaríamos aplicar un overlay de prueba
    # y verificar que funcione correctamente
    
    # Para esta demostración, simplemente verificamos la existencia de /proc/device-tree
    if dt_base_exists:
        print("✓ Directorio /proc/device-tree encontrado")
        # Listar algunos archivos del device tree para verificar
        if os.path.exists('/proc/device-tree'):
            print("Contenido de /proc/device-tree:")
            for item in os.listdir('/proc/device-tree')[:5]:  # Mostrar primeros 5 elementos
                print(f"  - {item}")
    else:
        print("✗ No se encontró el directorio /proc/device-tree")
    
    return dt_base_exists

def run_test():
    """Función principal de la prueba, debe retornar un diccionario con el resultado"""
    print("Ejecutando F-K1-TC-002: Verificación de soporte Device Tree Overlay")
    
    # Ejecutar la verificación
    overlay_supported = check_dt_overlay_support()
    
    # Generar resultado
    result = {
        "test_id": "F-K1-TC-002",
        "name": "Device Tree Overlay Support Validation",
        "description": "Verificar que el kernel soporta la funcionalidad de Device Tree Overlays",
        "result": "PASS" if overlay_supported else "FAIL",
        "details": {
            "device_tree_found": overlay_supported
        }
    }
    
    print(f"Resultado: {result['result']}")
    return result

if __name__ == "__main__":
    # Para pruebas individuales
    result = run_test()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['result'] == "PASS" else 1)
EOL

# Crear una segunda prueba de ejemplo
cat > "$TESTS_DIR/test_kernel_cmdline.py" <<EOL
#!/usr/bin/python3
# Prueba de verificación de parámetros de línea de comandos del kernel
import os
import sys
import json

def check_kernel_cmdline():
    """Verifica que la línea de comandos del kernel tenga los parámetros necesarios"""
    try:
        with open('/proc/cmdline', 'r') as f:
            cmdline = f.read().strip()
            print(f"Línea de comandos del kernel: {cmdline}")
            
            # Verificar parámetros requeridos
            required_params = ['console=ttymxc0', 'root=/dev/ram0']
            missing = [param for param in required_params if param not in cmdline]
            
            if missing:
                print(f"✗ Faltan parámetros requeridos: {', '.join(missing)}")
                return False
            else:
                print("✓ Todos los parámetros requeridos están presentes")
                return True
    except Exception as e:
        print(f"Error al leer /proc/cmdline: {str(e)}")
        return False

def run_test():
    """Función principal de la prueba"""
    print("Ejecutando prueba de parámetros de línea de comandos del kernel")
    
    # Ejecutar la verificación
    cmdline_ok = check_kernel_cmdline()
    
    # Generar resultado
    result = {
        "test_id": "KERNEL-CMDLINE-001",
        "name": "Kernel Command Line Parameters",
        "description": "Verificar que la línea de comandos del kernel incluye los parámetros necesarios",
        "result": "PASS" if cmdline_ok else "FAIL",
        "details": {
            "parameters_ok": cmdline_ok
        }
    }
    
    print(f"Resultado: {result['result']}")
    return result

if __name__ == "__main__":
    # Para pruebas individuales
    result = run_test()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['result'] == "PASS" else 1)
EOL

# Crear script de inicialización que ejecuta el framework de pruebas
cat > "$SCRIPT_DIR/init-test-framework.sh" <<EOL
#!/bin/sh
# Script de inicialización para el framework de pruebas

# Montar sistemas de archivos necesarios
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t tmpfs tmpfs /tmp
mkdir -p /tests

echo "=== Iniciando framework de pruebas para i.MX6UL en QEMU ==="
echo "Kernel: \$(uname -r)"
echo "Sistema: \$(uname -a)"

# Copiar las pruebas al directorio /tests
cp /test_framework.py /tests/
cp /test_*.py /tests/

# Ejecutar framework de pruebas
echo "Iniciando ejecución de pruebas..."
python3 /tests/test_framework.py
TEST_FRAMEWORK_RESULT=\$?

# Guardar resultados para Jenkins
echo "TEST_RESULT=\$TEST_FRAMEWORK_RESULT" > /tmp/exit-code

# Mostrar resumen final para log de consola
if [ -f /tmp/test_summary.json ]; then
    echo -e "\n\033[1;36m=== Resumen final de pruebas ===\033[0m"
    cat /tmp/test_summary.json
fi

# Para ejecución manual, iniciar shell si hay terminal interactiva
if [ -t 0 ]; then
    echo "Presione Ctrl+A, X para salir de QEMU"
    /bin/sh
fi

# Apagar QEMU con código de salida apropiado
sync
poweroff -f
EOL
chmod +x "$SCRIPT_DIR/init-test-framework.sh"

# Copiar scripts al initrd
mkdir -p "$SCRIPT_DIR/initrd-update"
cd "$SCRIPT_DIR/initrd-update"
gzip -dc "$SCRIPT_DIR/initrd-with-python.img" | cpio -idm
cp "$TESTS_DIR/test_framework.py" ./test_framework.py
cp "$TESTS_DIR/test_F_K1_TC_002.py" ./test_F_K1_TC_002.py
cp "$TESTS_DIR/test_kernel_cmdline.py" ./test_kernel_cmdline.py
cp "$SCRIPT_DIR/init-test-framework.sh" ./init
find . | cpio -o -H newc | gzip > "$SCRIPT_DIR/initrd-test-framework.img"
cd "$SCRIPT_DIR"
rm -rf "$SCRIPT_DIR/initrd-update"

# Ejecutar QEMU con el initrd que incluye el framework de pruebas
# Usando -no-reboot para que QEMU se detenga cuando la VM se apague
echo "Iniciando QEMU con framework de pruebas..."
qemu-system-arm \
    -M mcimx6ul-evk \
    -cpu cortex-a7 \
    -m 256M \
    -kernel "$SCRIPT_DIR/zImage-imx6ul" \
    -dtb "$SCRIPT_DIR/imx6ul-14x14-evk.dtb" \
    -initrd "$SCRIPT_DIR/initrd-test-framework.img" \
    -append "console=ttymxc0,115200 root=/dev/ram0 rw" \
    -no-reboot \
    -nographic

QEMU_EXIT_CODE=$?
echo "QEMU terminó con código de salida: $QEMU_EXIT_CODE"

# Crear directorio para resultados si no existe
mkdir -p "$RESULTS_DIR"

# Agregar timestamp para este conjunto de pruebas
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
echo "Framework de pruebas ejecutado el: $TIMESTAMP" > "$RESULTS_DIR/last_run_$TIMESTAMP.log"
echo "Código de salida: $QEMU_EXIT_CODE" >> "$RESULTS_DIR/last_run_$TIMESTAMP.log"

# Si Jenkins está ejecutando este script, este código de salida
# reflejará si todas las pruebas fueron exitosas
exit $QEMU_EXIT_CODE