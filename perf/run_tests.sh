#!/bin/bash

# Script para ejecutar pruebas de rendimiento fácilmente

set -e

echo "====== PRUEBAS DE RENDIMIENTO - ECOMMERCE ======"
echo ""

# Verificar que el backend está corriendo
echo "✓ Verificando backend en http://localhost:8000..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "✗ Backend no está disponible. Inicia el servidor:"
    echo "  cd ecommerce-backend && uvicorn app.main:app --reload"
    exit 1
fi
echo "✓ Backend OK"
echo ""

# Opciones de prueba
PS3='Selecciona tipo de prueba: '
options=(
    "1. Rendimiento estándar (100 usuarios, 60s)"
    "2. Estrés moderado (300 usuarios, 60s)"
    "3. Estrés alto (500 usuarios, 60s)"
    "4. Solo visitantes (200 usuarios, 60s)"
    "5. Solo compradores (50 usuarios, 60s)"
    "6. Admin intenso (20 usuarios, 60s)"
    "7. Rápido (50 usuarios, 30s - desarrollo)"
    "8. Interfaz web (interactivo con gráficas)"
    "Salir"
)

select opt in "${options[@]}"
do
    case $opt in
        "1. Rendimiento estándar (100 usuarios, 60s)")
            echo "▶ Iniciando: 100 usuarios, 60s, todos los tipos"
            locust -f perf/locustfile.py --headless -u 100 -r 20 --run-time 60s --host http://localhost:8000
            ;;
        "2. Estrés moderado (300 usuarios, 60s)")
            echo "▶ Iniciando: 300 usuarios, 60s, todos los tipos"
            locust -f perf/locustfile.py --headless -u 300 -r 50 --run-time 60s --host http://localhost:8000
            ;;
        "3. Estrés alto (500 usuarios, 60s)")
            echo "▶ Iniciando: 500 usuarios, 60s, todos los tipos"
            locust -f perf/locustfile.py --headless -u 500 -r 50 --run-time 60s --host http://localhost:8000
            ;;
        "4. Solo visitantes (200 usuarios, 60s)")
            echo "▶ Iniciando: 200 usuarios solo lectura"
            locust -f perf/locustfile.py::VisitanteTienda --headless -u 200 -r 30 --run-time 60s --host http://localhost:8000
            ;;
        "5. Solo compradores (50 usuarios, 60s)")
            echo "▶ Iniciando: 50 usuarios realizando compras"
            locust -f perf/locustfile.py::Comprador --headless -u 50 -r 10 --run-time 60s --host http://localhost:8000
            ;;
        "6. Admin intenso (20 usuarios, 60s)")
            echo "▶ Iniciando: 20 admins creando/editando productos"
            locust -f perf/locustfile.py::UsuarioAutenticado --headless -u 20 -r 5 --run-time 60s --host http://localhost:8000
            ;;
        "7. Rápido (50 usuarios, 30s - desarrollo)")
            echo "▶ Iniciando: 50 usuarios, 30s (desarrollo rápido)"
            locust -f perf/locustfile.py --headless -u 50 -r 10 --run-time 30s --host http://localhost:8000
            ;;
        "8. Interfaz web (interactivo con gráficas)")
            echo "▶ Abriendo interfaz web en http://localhost:8089"
            echo "   Ajusta usuarios/spawn rate en vivo y presiona Shift+C para ver gráficas"
            locust -f perf/locustfile.py --host http://localhost:8000
            ;;
        "Salir")
            echo "Adiós!"
            break
            ;;
        *) echo "Opción inválida"; ;;
    esac
    echo ""
    break
done
