#!/bin/bash
# verify-kernel-env.sh
# Script de verificación del entorno Docker para desarrollo de kernel
# Autor: Jorge Rodriguez Moreno

echo "🔍 Verificación del Entorno Docker Kernel Dev"
echo "=============================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar resultados
show_result() {
    if [ $1 -eq 0 ]; then
        echo -e "   ${GREEN}✅ $2${NC}"
    else
        echo -e "   ${RED}❌ $2${NC}"
    fi
}

show_warning() {
    echo -e "   ${YELLOW}⚠️  $1${NC}"
}

show_info() {
    echo -e "${BLUE}📋 $1${NC}"
}

ERRORS=0

# 1. Verificar Docker
show_info "Verificando Docker..."
docker --version &>/dev/null
show_result $? "Docker instalado y disponible"

# 2. Verificar contenedor jenkins-minimal
show_info "Verificando contenedor jenkins-minimal..."
if docker ps | grep -q jenkins-minimal; then
    show_result 0 "Contenedor jenkins-minimal ejecutándose"
    
    # Verificar modo privilegiado
    if docker inspect jenkins-minimal | grep -q '"Privileged": true'; then
        show_result 0 "Contenedor en modo privilegiado"
    else
        show_result 1 "Contenedor NO está en modo privilegiado"
        ((ERRORS++))
    fi
else
    show_result 1 "Contenedor jenkins-minimal NO está ejecutándose"
    ((ERRORS++))
    exit 1
fi

# 3. Verificar acceso al contenedor
show_info "Verificando acceso al contenedor..."
docker exec jenkins-minimal echo "test" &>/dev/null
show_result $? "Acceso al contenedor funcional"

# 4. Verificar kernel y sistema
show_info "Verificando kernel y sistema..."
HOST_KERNEL=$(uname -r)
CONTAINER_KERNEL=$(docker exec jenkins-minimal uname -r 2>/dev/null)

echo "   🐧 Kernel del host: $HOST_KERNEL"
echo "   🐧 Kernel del contenedor: $CONTAINER_KERNEL"

if [ "$HOST_KERNEL" = "$CONTAINER_KERNEL" ]; then
    show_result 0 "Kernels coinciden (compartido correctamente)"
else
    show_result 1 "Kernels NO coinciden"
    ((ERRORS++))
fi

# 5. Verificar headers del kernel
show_info "Verificando headers del kernel..."
HEADERS_32=$(docker exec -u root jenkins-minimal ls /usr/src/linux-headers-6.14.0-32-generic 2>/dev/null)
HEADERS_33=$(docker exec -u root jenkins-minimal ls /usr/src/linux-headers-6.14.0-33-generic 2>/dev/null)

if [ -n "$HEADERS_32" ]; then
    show_result 0 "Headers 6.14.0-32-generic disponibles"
else
    show_result 1 "Headers 6.14.0-32-generic NO disponibles"
    ((ERRORS++))
fi

if [ -n "$HEADERS_33" ]; then
    show_result 0 "Headers 6.14.0-33-generic disponibles"
else
    show_warning "Headers 6.14.0-33-generic NO disponibles (no crítico)"
fi

# 6. Verificar herramientas de compilación
show_info "Verificando herramientas de compilación..."
TOOLS=("make" "gcc" "gcc-13" "insmod" "rmmod" "modinfo" "lsmod")

for tool in "${TOOLS[@]}"; do
    if docker exec -u root jenkins-minimal which $tool &>/dev/null; then
        show_result 0 "$tool disponible"
    else
        show_result 1 "$tool NO disponible"
        ((ERRORS++))
    fi
done

# 7. Verificar glibc
show_info "Verificando glibc..."
GLIBC_VERSION=$(docker exec -u root jenkins-minimal ldd --version 2>/dev/null | head -1 | grep -o '2\.[0-9][0-9]')

echo "   📚 Versión glibc: $GLIBC_VERSION"
if [[ "$GLIBC_VERSION" > "2.37" ]]; then
    show_result 0 "glibc compatible (>= 2.38)"
else
    show_result 1 "glibc incompatible (necesita >= 2.38)"
    ((ERRORS++))
fi

# 8. Verificar workspace
show_info "Verificando workspace de Jenkins..."
WORKSPACE_PATH="/var/jenkins_home/workspace/lenge-from-Github_f-k1-reg-by-dt/simtemp/kernel"
if docker exec -u root jenkins-minimal ls "$WORKSPACE_PATH" &>/dev/null; then
    show_result 0 "Workspace del proyecto disponible"
    
    # Verificar Makefile
    if docker exec -u root jenkins-minimal ls "$WORKSPACE_PATH/Makefile" &>/dev/null; then
        show_result 0 "Makefile encontrado"
    else
        show_result 1 "Makefile NO encontrado"
        ((ERRORS++))
    fi
    
    # Verificar código fuente
    if docker exec -u root jenkins-minimal ls "$WORKSPACE_PATH/nxp_simtemp.c" &>/dev/null; then
        show_result 0 "Código fuente del driver encontrado"
    else
        show_result 1 "Código fuente del driver NO encontrado"
        ((ERRORS++))
    fi
else
    show_result 1 "Workspace del proyecto NO disponible"
    ((ERRORS++))
fi

# 9. Verificar claves de firmado
show_info "Verificando claves de firmado MOK..."
MOK_PRIV="/var/jenkins_home/kernel_enroll/MOK.priv"
MOK_DER="/var/jenkins_home/kernel_enroll/MOK.der"

if docker exec -u root jenkins-minimal ls "$MOK_PRIV" &>/dev/null; then
    show_result 0 "Clave privada MOK encontrada"
else
    show_warning "Clave privada MOK NO encontrada (se creará automáticamente)"
fi

if docker exec -u root jenkins-minimal ls "$MOK_DER" &>/dev/null; then
    show_result 0 "Certificado MOK encontrado"
else
    show_warning "Certificado MOK NO encontrado (se creará automáticamente)"
fi

# 10. Test de compilación básica
show_info "Realizando test de compilación..."
TEST_RESULT=$(docker exec -u root jenkins-minimal bash -c "
cd $WORKSPACE_PATH 2>/dev/null && 
make clean &>/dev/null && 
timeout 60 make deb-driver &>/dev/null
echo \$?")

if [ "$TEST_RESULT" = "0" ]; then
    show_result 0 "Test de compilación exitoso"
    
    # Verificar módulo compilado
    if docker exec -u root jenkins-minimal ls "$WORKSPACE_PATH/obj/nxp_simtemp.ko" &>/dev/null; then
        show_result 0 "Módulo .ko generado correctamente"
        
        # Verificar información del módulo
        MODULE_INFO=$(docker exec -u root jenkins-minimal modinfo "$WORKSPACE_PATH/obj/nxp_simtemp.ko" 2>/dev/null)
        if [ -n "$MODULE_INFO" ]; then
            show_result 0 "Módulo válido y con metadata correcta"
        else
            show_result 1 "Módulo inválido o corrupto"
            ((ERRORS++))
        fi
    else
        show_result 1 "Módulo .ko NO fue generado"
        ((ERRORS++))
    fi
else
    show_result 1 "Test de compilación falló"
    ((ERRORS++))
fi

# 11. Verificar capacidades de carga de módulos
show_info "Verificando capacidades de carga de módulos..."
# Verificar si ya hay un módulo cargado
LOADED_MODULE=$(docker exec -u root jenkins-minimal lsmod 2>/dev/null | grep nxp_simtemp || echo "")

if [ -n "$LOADED_MODULE" ]; then
    show_result 0 "Módulo nxp_simtemp ya está cargado en el kernel"
    echo "   📊 Info del módulo: $LOADED_MODULE"
else
    show_warning "Módulo nxp_simtemp no está cargado (normal)"
fi

# Verificar acceso a /proc/modules
if docker exec -u root jenkins-minimal cat /proc/modules &>/dev/null; then
    show_result 0 "Acceso a /proc/modules (puede listar módulos del kernel)"
else
    show_result 1 "NO puede acceder a /proc/modules"
    ((ERRORS++))
fi

# 12. Verificar Jenkins
show_info "Verificando Jenkins..."
JENKINS_STATUS=$(docker exec jenkins-minimal pgrep -f jenkins 2>/dev/null || echo "")
if [ -n "$JENKINS_STATUS" ]; then
    show_result 0 "Jenkins ejecutándose"
    echo "   🌐 Acceso web: http://localhost:8080"
else
    show_warning "Jenkins no está ejecutándose completamente"
fi

# Resumen final
echo ""
echo "📊 RESUMEN DE LA VERIFICACIÓN"
echo "============================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}🎉 ¡Entorno completamente funcional!${NC}"
    echo -e "${GREEN}   ✅ Listo para desarrollo de kernel modules${NC}"
    echo ""
    echo "🚀 Comandos principales:"
    echo "   🔧 Acceso al contenedor: docker exec -u root -it jenkins-minimal bash"
    echo "   🔨 Compilar: make deb-driver"
    echo "   📦 Cargar módulo: insmod obj/nxp_simtemp.ko"
    echo "   📋 Ver módulos: lsmod | grep nxp_simtemp"
    echo "   🗑️  Descargar: rmmod nxp_simtemp"
else
    echo -e "${RED}⚠️  Se encontraron $ERRORS errores${NC}"
    echo -e "${YELLOW}   🔧 Ejecutar setup-kernel-dev-docker.sh para corregir${NC}"
fi

echo ""
echo "📖 Documentación completa: deployment/docker/KERNEL_DEV_ENVIRONMENT.md"