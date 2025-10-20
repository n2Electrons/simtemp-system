# Entorno Docker para Desarrollo de Módulos de Kernel

## Descripción General

Este documento detalla la configuración completa del entorno Docker privilegiado para desarrollo, compilación y carga de módulos del kernel Linux con soporte para Jenkins CI/CD.

## Características del Entorno

- **Contenedor Base**: jenkins/jenkins:lts (Debian Bookworm)
- **Modo**: Privilegiado (`--privileged`) para acceso completo al kernel
- **Capacidades**: Compilación, firmado digital y carga de módulos del kernel
- **Compatibilidad**: Headers Ubuntu 6.14.0-32/33-generic con glibc actualizada
- **Signing**: MOK (Machine Owner Keys) para Secure Boot

## Configuración del Contenedor

### 1. Crear y Ejecutar Contenedor Privilegiado

```bash
# Detener contenedor existente si existe
docker stop jenkins-minimal 2>/dev/null || true
docker rm jenkins-minimal 2>/dev/null || true

# Crear contenedor privilegiado con acceso completo al kernel
docker run -d \
  --name jenkins-minimal \
  --privileged \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v jenkins_minimal_home:/var/jenkins_home \
  -p 8080:8080 \
  -p 50000:50000 \
  jenkins/jenkins:lts

# Verificar que está ejecutándose
docker ps | grep jenkins-minimal
```

### 2. Configuración Inicial del Sistema

```bash
# Actualizar repositorios
docker exec -u root jenkins-minimal bash -c "apt update"

# Instalar herramientas de desarrollo básicas
docker exec -u root jenkins-minimal bash -c "
apt install -y build-essential make gcc kmod libelf1 libelf-dev \
bc flex bison zlib1g-dev"
```

### 3. Resolución de Conflictos glibc (CRÍTICO)

El problema principal es la incompatibilidad entre glibc del contenedor Debian y las herramientas del kernel Ubuntu:

```bash
# Agregar repositorio Debian Sid para glibc más reciente
docker exec -u root jenkins-minimal bash -c "
echo 'deb http://deb.debian.org/debian sid main' >> /etc/apt/sources.list"

# Actualizar glibc a versión compatible (2.41+)
docker exec -u root jenkins-minimal bash -c "
apt update && apt install -y libc6/sid libc-bin/sid libc-dev-bin/sid \
libc-devtools/sid libc6-dev/sid base-files/sid"
```

### 4. Configuración del Compilador

```bash
# Crear enlace simbólico para gcc-13 (requerido por headers Ubuntu)
docker exec -u root jenkins-minimal bash -c "
ln -sf /usr/bin/gcc /usr/bin/gcc-13"

# Verificar instalación
docker exec -u root jenkins-minimal bash -c "
gcc --version && gcc-13 --version"
```

## Estructura de Directorios Montados

```
Contenedor privilegiado:
├── /lib/modules/          # Módulos del kernel (read-only desde host)
│   └── 6.14.0-33-generic/ # Kernel actual del host
├── /usr/src/              # Headers del kernel (read-only desde host)  
│   ├── linux-headers-6.14.0-32-generic/  # Headers compatibles
│   └── linux-headers-6.14.0-33-generic/  # Headers actuales
└── /var/jenkins_home/     # Workspace de Jenkins (persistente)
    └── workspace/
        └── lenge-from-Github_f-k1-reg-by-dt/
            └── simtemp/kernel/    # Código fuente del driver
```

## Compilación de Módulos

### Makefile Configurado

El `Makefile` debe usar los headers correctos:

```makefile
# Debian native kernel source (independent compilation in Docker)
# Force use of 6.14.0-32-generic headers to avoid glibc version conflicts
DEBIAN_KERNEL_SRC := /usr/src/linux-headers-6.14.0-32-generic
```

### Comandos de Compilación

```bash
# Navegar al workspace del kernel
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel"

# Limpiar compilación anterior
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
make clean"

# Compilar y firmar módulo
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
make deb-driver"
```

### Verificación de Compilación

```bash
# Verificar módulo compilado
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
ls -la obj/nxp_simtemp.ko && 
modinfo obj/nxp_simtemp.ko"
```

## Carga de Módulos

### Cargar Módulo en Kernel

```bash
# Cargar módulo (requiere contenedor privilegiado)
docker exec -u root jenkins-minimal bash -c "
cd /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel && 
insmod obj/nxp_simtemp.ko"

# Verificar que se cargó
docker exec -u root jenkins-minimal bash -c "lsmod | grep nxp_simtemp"

# Ver mensajes del kernel
docker exec -u root jenkins-minimal bash -c "dmesg | tail -5"
```

### Descargar Módulo

```bash
# Descargar módulo del kernel
docker exec -u root jenkins-minimal bash -c "rmmod nxp_simtemp"
```

## Configuración de Firmado Digital

### Claves MOK (Machine Owner Keys)

Las claves de firmado están ubicadas en:
- **Clave privada**: `/var/jenkins_home/kernel_enroll/MOK.priv`
- **Certificado**: `/var/jenkins_home/kernel_enroll/MOK.der`

### Verificar Firmado

```bash
# Verificar que el módulo está firmado
docker exec -u root jenkins-minimal bash -c "
modinfo /var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel/obj/nxp_simtemp.ko | 
grep -E 'sig_id|signer|sig_key'"
```

## Solución de Problemas Comunes

### 1. Error "Operation not permitted" al cargar módulo

**Causa**: Contenedor sin privilegios
**Solución**: Usar `--privileged` al crear el contenedor

### 2. Error "GLIBC_2.38 not found"

**Causa**: Incompatibilidad entre glibc del contenedor y herramientas del kernel
**Solución**: Actualizar glibc como se indica en la sección 3

### 3. Error "objtool: command not found"

**Causa**: Faltan dependencias de compilación del kernel
**Solución**: Instalar `libelf-dev`, `bc`, `flex`, `bison`

### 4. Módulo no se firma automáticamente

**Causa**: Claves MOK no encontradas o permisos incorrectos
**Solución**: Verificar que existen las claves en `/var/jenkins_home/kernel_enroll/`

## Verificación del Entorno Completo

### Script de Verificación

```bash
#!/bin/bash
echo "=== Verificación del Entorno Docker Kernel Dev ==="

# Verificar contenedor
docker exec jenkins-minimal uname -r
docker exec jenkins-minimal ls -la /.dockerenv

# Verificar herramientas
docker exec -u root jenkins-minimal which make gcc kmod insmod modinfo

# Verificar headers
docker exec -u root jenkins-minimal ls -la /usr/src/linux-headers-6.14.0-32-generic/

# Verificar glibc
docker exec -u root jenkins-minimal ldd --version | head -1

# Verificar claves de firmado
docker exec -u root jenkins-minimal ls -la /var/jenkins_home/kernel_enroll/

echo "✅ Verificación completa"
```

## Información Técnica

### Versiones Confirmadas

- **Sistema Host**: Ubuntu 24.04 LTS
- **Kernel Host**: 6.14.0-33-generic
- **Contenedor**: jenkins/jenkins:lts (Debian Bookworm)
- **glibc Contenedor**: 2.41-12 (actualizada desde Debian Sid)
- **gcc**: 12.2.0 (con enlace simbólico a gcc-13)
- **Headers Utilizados**: linux-headers-6.14.0-32-generic

### Capacidades del Entorno

✅ **Compilación**: Módulos del kernel con headers Ubuntu  
✅ **Firmado Digital**: Automático con claves MOK  
✅ **Carga de Módulos**: Directa en kernel del host  
✅ **Desarrollo Iterativo**: Ciclo completo compile-load-test  
✅ **Jenkins Integration**: Workspace persistente y CI/CD ready  
✅ **Secure Boot**: Compatible con sistemas que requieren módulos firmados  

### Limitaciones Conocidas

- Requiere contenedor privilegiado (implicaciones de seguridad)
- Dependiente de versiones específicas de headers del kernel
- glibc debe actualizarse manualmente para nuevas versiones de headers
- Los módulos se cargan en el kernel del host (no aislados)

## Regeneración Rápida del Entorno

### Script de Setup Automático

```bash
#!/bin/bash
# setup-kernel-dev-docker.sh

set -e

echo "🔧 Configurando entorno Docker para desarrollo de kernel..."

# 1. Crear contenedor privilegiado
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

# 2. Esperar a que Jenkins inicie
echo "⏳ Esperando a que Jenkins inicie..."
sleep 30

# 3. Instalar herramientas básicas
echo "🔨 Instalando herramientas de desarrollo..."
docker exec -u root jenkins-minimal bash -c "
apt update && 
apt install -y build-essential make gcc kmod libelf1 libelf-dev bc flex bison zlib1g-dev"

# 4. Actualizar glibc
echo "📚 Actualizando glibc para compatibilidad con headers Ubuntu..."
docker exec -u root jenkins-minimal bash -c "
echo 'deb http://deb.debian.org/debian sid main' >> /etc/apt/sources.list &&
apt update &&
apt install -y libc6/sid libc-bin/sid libc-dev-bin/sid libc-devtools/sid libc6-dev/sid base-files/sid"

# 5. Configurar gcc
echo "⚙️  Configurando gcc-13..."
docker exec -u root jenkins-minimal bash -c "ln -sf /usr/bin/gcc /usr/bin/gcc-13"

# 6. Verificar instalación
echo "✅ Verificando configuración..."
docker exec -u root jenkins-minimal bash -c "
echo 'Kernel version:' && uname -r &&
echo 'Headers available:' && ls /usr/src/linux-headers-* &&
echo 'glibc version:' && ldd --version | head -1 &&
echo 'gcc version:' && gcc --version | head -1"

echo "🎉 ¡Entorno Docker para desarrollo de kernel configurado exitosamente!"
echo "📍 Jenkins disponible en: http://localhost:8080"
echo "🔧 Para compilar módulos, usar: make deb-driver"
echo "🚀 Para cargar módulos, usar: insmod obj/module.ko"
```

## Contacto y Mantenimiento

**Autor**: Jorge Rodriguez Moreno  
**Proyecto**: simtemp-system  
**Fecha**: Octubre 2025  
**Versión**: 1.0  

Para actualizaciones y soporte, consultar el repositorio del proyecto.