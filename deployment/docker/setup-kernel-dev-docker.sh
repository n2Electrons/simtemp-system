#!/bin/bash
# setup-kernel-dev-docker.sh
# Script para configurar automáticamente el entorno Docker para desarrollo de kernel modules
# Autor: Jorge Rodriguez Moreno
# Proyecto: simtemp-system

set -e

echo "🔧 Configurando entorno Docker para desarrollo de kernel..."
echo "📋 Este script configurará:"
echo "   - Contenedor Jenkins privilegiado"
echo "   - Herramientas de compilación de kernel"
echo "   - glibc actualizada para compatibilidad"
echo "   - Claves de firmado MOK"
echo ""

# Verificar que Docker está disponible
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker no está instalado o no está en PATH"
    exit 1
fi

# Verificar que se ejecuta como usuario con acceso a Docker
if ! docker ps &> /dev/null; then
    echo "❌ Error: No tienes permisos para ejecutar Docker"
    echo "   Ejecuta: sudo usermod -aG docker $USER && newgrp docker"
    exit 1
fi

echo "✅ Docker disponible"

# 1. Crear contenedor privilegiado
echo ""
echo "📦 Creando contenedor jenkins-minimal privilegiado..."
docker stop jenkins-minimal 2>/dev/null || true
docker rm jenkins-minimal 2>/dev/null || true

docker run -d \
  --name jenkins-minimal \
  --privileged \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v jenkins_minimal_home:/var/jenkins_home \
  -p 8080:8080 \
  -p 50000:50000 \
  jenkins/jenkins:lts

if [ $? -eq 0 ]; then
    echo "✅ Contenedor jenkins-minimal creado exitosamente"
else
    echo "❌ Error al crear contenedor"
    exit 1
fi

# 2. Esperar a que Jenkins inicie
echo ""
echo "⏳ Esperando a que Jenkins inicie (30 segundos)..."
sleep 30

# Verificar que el contenedor está funcionando
if ! docker exec jenkins-minimal echo "Container is running" &> /dev/null; then
    echo "❌ Error: El contenedor no responde"
    exit 1
fi

echo "✅ Jenkins iniciado correctamente"

# 3. Instalar herramientas básicas
echo ""
echo "🔨 Instalando herramientas de desarrollo..."
docker exec -u root jenkins-minimal bash -c "
apt update -qq && 
apt install -y -qq build-essential make gcc kmod libelf1 libelf-dev bc flex bison zlib1g-dev" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Herramientas de desarrollo instaladas"
else
    echo "❌ Error al instalar herramientas de desarrollo"
    exit 1
fi

# 4. Actualizar glibc (CRÍTICO para compatibilidad)
echo ""
echo "📚 Actualizando glibc para compatibilidad con headers Ubuntu..."
echo "   (Esto resuelve el error 'GLIBC_2.38 not found')"
docker exec -u root jenkins-minimal bash -c "
echo 'deb http://deb.debian.org/debian sid main' >> /etc/apt/sources.list &&
apt update -qq 2>/dev/null &&
DEBIAN_FRONTEND=noninteractive apt install -y -qq libc6/sid libc-bin/sid libc-dev-bin/sid libc-devtools/sid libc6-dev/sid base-files/sid" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ glibc actualizada exitosamente"
else
    echo "❌ Error al actualizar glibc"
    exit 1
fi

# 5. Configurar gcc
echo ""
echo "⚙️  Configurando gcc-13 (requerido por headers Ubuntu)..."
docker exec -u root jenkins-minimal bash -c "ln -sf /usr/bin/gcc /usr/bin/gcc-13"

if [ $? -eq 0 ]; then
    echo "✅ gcc-13 configurado"
else
    echo "❌ Error al configurar gcc-13"
    exit 1
fi

# 6. Verificar instalación completa
echo ""
echo "🔍 Verificando configuración..."

# Verificar kernel y headers
KERNEL_VERSION=$(docker exec -u root jenkins-minimal uname -r)
HEADERS_AVAILABLE=$(docker exec -u root jenkins-minimal ls /usr/src/linux-headers-* 2>/dev/null | wc -l)
GLIBC_VERSION=$(docker exec -u root jenkins-minimal ldd --version 2>/dev/null | head -1)
GCC_VERSION=$(docker exec -u root jenkins-minimal gcc --version 2>/dev/null | head -1)

echo "📊 Resumen de la configuración:"
echo "   🐧 Kernel del host: $KERNEL_VERSION"
echo "   📁 Headers disponibles: $HEADERS_AVAILABLE conjuntos"
echo "   📚 glibc: $GLIBC_VERSION"
echo "   🔧 Compilador: $GCC_VERSION"

# Verificar herramientas críticas
echo ""
echo "🛠️  Verificando herramientas críticas..."
TOOLS_OK=true

for tool in make gcc insmod modinfo; do
    if docker exec -u root jenkins-minimal which $tool &>/dev/null; then
        echo "   ✅ $tool disponible"
    else
        echo "   ❌ $tool NO disponible"
        TOOLS_OK=false
    fi
done

# Verificar claves de firmado
if docker exec -u root jenkins-minimal ls /var/jenkins_home/kernel_enroll/ &>/dev/null; then
    echo "   ✅ Directorio de claves MOK disponible"
else
    echo "   ⚠️  Directorio de claves MOK no encontrado (se creará automáticamente)"
fi

# 7. Resultado final
echo ""
if [ "$TOOLS_OK" = true ]; then
    echo "🎉 ¡Entorno Docker para desarrollo de kernel configurado exitosamente!"
    echo ""
    echo "📍 Información de acceso:"
    echo "   🌐 Jenkins Web UI: http://localhost:8080"
    echo "   🔑 Contraseña inicial: docker exec jenkins-minimal cat /var/jenkins_home/secrets/initialAdminPassword"
    echo ""
    echo "🚀 Comandos principales:"
    echo "   📝 Acceso al contenedor: docker exec -u root -it jenkins-minimal bash"
    echo "   🔨 Compilar módulo: make deb-driver"
    echo "   📦 Cargar módulo: insmod obj/module.ko"
    echo "   📋 Ver módulos: lsmod | grep module_name"
    echo "   🗑️  Descargar módulo: rmmod module_name"
    echo ""
    echo "📖 Para más información, consultar: deployment/docker/KERNEL_DEV_ENVIRONMENT.md"
else
    echo "⚠️  Configuración completada con advertencias"
    echo "   Revisar los errores anteriores antes de continuar"
fi

# Mostrar contraseña inicial de Jenkins si está disponible
echo ""
echo "🔐 Obteniendo contraseña inicial de Jenkins..."
sleep 5  # Esperar un poco más para que Jenkins genere la contraseña
if JENKINS_PASSWORD=$(docker exec jenkins-minimal cat /var/jenkins_home/secrets/initialAdminPassword 2>/dev/null); then
    echo "   Contraseña inicial de Jenkins: $JENKINS_PASSWORD"
else
    echo "   ⏳ Contraseña aún no generada, espera unos minutos más"
fi

echo ""
echo "✨ Setup completado. ¡Happy kernel hacking! 🐧"