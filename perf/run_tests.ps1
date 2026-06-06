# Script para ejecutar pruebas de rendimiento en Windows

Write-Host "====== PRUEBAS DE RENDIMIENTO - ECOMMERCE ======" -ForegroundColor Cyan
Write-Host ""

# Verificar que el backend está corriendo
Write-Host "✓ Verificando backend en http://localhost:8000..."
try {
    $null = Invoke-WebRequest -Uri http://localhost:8000/health -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ Backend OK" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend no está disponible. Inicia el servidor:" -ForegroundColor Red
    Write-Host "  cd ecommerce-backend && uvicorn app.main:app --reload"
    exit 1
}
Write-Host ""

# Menú de opciones
$options = @(
    "Rendimiento estándar (100 usuarios, 60s)",
    "Estrés moderado (300 usuarios, 60s)",
    "Estrés alto (500 usuarios, 60s)",
    "Solo visitantes (200 usuarios, 60s)",
    "Solo compradores (50 usuarios, 60s)",
    "Admin intenso (20 usuarios, 60s)",
    "Rápido (50 usuarios, 30s)",
    "Interfaz web (interactivo con gráficas)"
)

$selection = 0
do {
    Write-Host "Selecciona tipo de prueba:" -ForegroundColor Yellow
    for ($i = 0; $i -lt $options.Count; $i++) {
        Write-Host "$($i + 1). $($options[$i])"
    }
    Write-Host "$($options.Count + 1). Salir"
    
    $choice = Read-Host "Opción"
    
    switch ($choice) {
        "1" {
            Write-Host "▶ Iniciando: 100 usuarios, 60s, todos los tipos" -ForegroundColor Cyan
            .\.venv\Scripts\activate; locust -f perf/locustfile.py --headless -u 100 -r 20 --run-time 60s --host http://localhost:8000
            break
        }
        "2" {
            Write-Host "▶ Iniciando: 300 usuarios, 60s, todos los tipos" -ForegroundColor Cyan
            .\.venv\Scripts\activate; locust -f perf/locustfile.py --headless -u 300 -r 50 --run-time 60s --host http://localhost:8000
            break
        }
        "3" {
            Write-Host "▶ Iniciando: 500 usuarios, 60s, todos los tipos" -ForegroundColor Cyan
            .\.venv\Scripts\activate; locust -f perf/locustfile.py --headless -u 500 -r 50 --run-time 60s --host http://localhost:8000
            break
        }
        "4" {
            Write-Host "▶ Iniciando: 200 usuarios solo lectura" -ForegroundColor Cyan
            .\.venv\Scripts\activate; locust -f perf/locustfile.py::VisitanteTienda --headless -u 200 -r 30 --run-time 60s --host http://localhost:8000
            break
        }
        "5" {
            Write-Host "▶ Iniciando: 50 usuarios realizando compras" -ForegroundColor Cyan
            .\.venv\Scripts\activate; locust -f perf/locustfile.py::Comprador --headless -u 50 -r 10 --run-time 60s --host http://localhost:8000
            break
        }
        "6" {
            Write-Host "▶ Iniciando: 20 admins creando/editando productos" -ForegroundColor Cyan
            .\.venv\Scripts\activate; locust -f perf/locustfile.py::UsuarioAutenticado --headless -u 20 -r 5 --run-time 60s --host http://localhost:8000
            break
        }
        "7" {
            Write-Host "▶ Iniciando: 50 usuarios, 30s (desarrollo rápido)" -ForegroundColor Cyan
            .\.venv\Scripts\activate; locust -f perf/locustfile.py --headless -u 50 -r 10 --run-time 30s --host http://localhost:8000
            break
        }
        "8" {
            Write-Host "▶ Abriendo interfaz web en http://localhost:8089" -ForegroundColor Cyan
            Write-Host "   Ajusta usuarios/spawn rate en vivo"
            .\.venv\Scripts\activate; locust -f perf/locustfile.py --host http://localhost:8000
            break
        }
        { $_ -eq ($options.Count + 1).ToString() } {
            Write-Host "¡Adiós!" -ForegroundColor Cyan
            exit 0
        }
        default {
            Write-Host "Opción inválida" -ForegroundColor Red
        }
    }
} while ($true)
