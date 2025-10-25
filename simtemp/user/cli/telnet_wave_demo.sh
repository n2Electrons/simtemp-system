#!/bin/bash

# SimTemp Continuous Wave Generator - Telnet Demo
# Este script demuestra cómo usar el generador de ondas vía Telnet

echo "=== SimTemp Telnet Wave Generator Demo ==="
echo

# Configuración por defecto
DEFAULT_HOST="192.168.1.100"
DEFAULT_PORT="23"

# Obtener parámetros
read -p "Host del sensor SimTemp [$DEFAULT_HOST]: " HOST
HOST=${HOST:-$DEFAULT_HOST}

read -p "Puerto Telnet [$DEFAULT_PORT]: " PORT
PORT=${PORT:-$DEFAULT_PORT}

echo
echo "Configuración:"
echo "  Host: $HOST"
echo "  Puerto: $PORT"
echo

# Verificar conectividad
echo "Verificando conectividad con el sensor..."
timeout 5 bash -c "echo >/dev/tcp/$HOST/$PORT" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Conexión exitosa a $HOST:$PORT"
else
    echo "✗ ERROR: No se puede conectar a $HOST:$PORT"
    echo "  Verificar que el sensor esté disponible en esa dirección"
    exit 1
fi

echo
echo "=== Demos Disponibles ==="
echo "1. Onda Seno (temperatura suave)"
echo "2. Onda Cuadrada (cambios bruscos)"
echo "3. Onda Triangular (rampa lineal)"
echo "4. Ruido (temperatura aleatoria)"
echo "5. Escalón (niveles discretos)"
echo

read -p "Seleccionar demo [1-5]: " DEMO

case $DEMO in
    1)
        echo "Iniciando onda seno..."
        echo "Frecuencia: 0.1 Hz (período 10s)"
        echo "Amplitud: ±8°C"
        echo "Offset: 30°C"
        echo "Duración: 60 segundos"
        echo
        python3 continuous_wave_generator.py \
            --host "$HOST" --port "$PORT" \
            --wave sine \
            --frequency 0.1 \
            --amplitude 8.0 \
            --offset 30.0 \
            --duration 60
        ;;
    
    2)
        echo "Iniciando onda cuadrada..."
        echo "Frecuencia: 0.05 Hz (período 20s)"
        echo "Amplitud: ±12°C"
        echo "Offset: 35°C"
        echo "Duración: 80 segundos"
        echo
        python3 continuous_wave_generator.py \
            --host "$HOST" --port "$PORT" \
            --wave square \
            --frequency 0.05 \
            --amplitude 12.0 \
            --offset 35.0 \
            --duration 80
        ;;
    
    3)
        echo "Iniciando onda triangular..."
        echo "Frecuencia: 0.08 Hz (período 12.5s)"
        echo "Amplitud: ±10°C"
        echo "Offset: 25°C"
        echo "Duración: 50 segundos"
        echo
        python3 continuous_wave_generator.py \
            --host "$HOST" --port "$PORT" \
            --wave triangle \
            --frequency 0.08 \
            --amplitude 10.0 \
            --offset 25.0 \
            --duration 50
        ;;
    
    4)
        echo "Iniciando ruido aleatorio..."
        echo "Amplitud: ±15°C"
        echo "Offset: 40°C"
        echo "Duración: 30 segundos"
        echo
        python3 continuous_wave_generator.py \
            --host "$HOST" --port "$PORT" \
            --wave noise \
            --amplitude 15.0 \
            --offset 40.0 \
            --duration 30
        ;;
    
    5)
        echo "Iniciando escalones..."
        echo "Frecuencia: 0.2 Hz (cambio cada 5s)"
        echo "Amplitud: ±20°C"
        echo "Offset: 50°C"
        echo "Duración: 40 segundos"
        echo
        python3 continuous_wave_generator.py \
            --host "$HOST" --port "$PORT" \
            --wave step \
            --frequency 0.2 \
            --amplitude 20.0 \
            --offset 50.0 \
            --duration 40
        ;;
    
    *)
        echo "Demo no válido. Mostrando ayuda..."
        python3 continuous_wave_generator.py --help
        ;;
esac

echo
echo "Demo completado."
echo
echo "=== Comandos de Ejemplo ==="
echo "# Onda seno básica:"
echo "python3 continuous_wave_generator.py --host $HOST --port $PORT --wave sine"
echo
echo "# Con parámetros personalizados:"
echo "python3 continuous_wave_generator.py --host $HOST --port $PORT \\"
echo "    --wave sine --frequency 0.1 --amplitude 10.0 --offset 30.0 --duration 60"
echo
echo "# Listar tipos de onda disponibles:"
echo "python3 continuous_wave_generator.py --list-waves"
echo
echo "# Usar patrón de Octave (si disponible):"
echo "python3 continuous_wave_generator.py --host $HOST --port $PORT --pattern thermal_test"
echo