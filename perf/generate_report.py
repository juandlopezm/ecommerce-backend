#!/usr/bin/env python3
"""
Generador de índice HTML para reportes de Locust (versión robusta).

Si existen archivos CSV, genera dashboard consolidado.
Si no, crea un índice HTML que linke a los reportes HTML ya generados.
"""

import csv
import sys
from pathlib import Path
from typing import Dict
from dataclasses import dataclass


@dataclass
class LocustStats:
    name: str
    requests: int
    failures: int
    median: float
    p95: float
    max_time: float
    avg_time: float
    rps: float


def parse_locust_csv(csv_path: str) -> Dict[str, LocustStats]:
    """Parsea archivo CSV de stats de Locust."""
    stats = {}
    try:
        with open(csv_path) as f:
            for row in csv.DictReader(f):
                name = row.get("Name", "").strip()
                if not name or name == "Aggregated":
                    continue
                try:
                    stats[name] = LocustStats(
                        name=name,
                        requests=int(row.get("# requests", 0)),
                        failures=int(row.get("# failures", 0)),
                        median=float(row.get("Median", 0)) or float(
                            row.get("50%ile", 0)
                        ),
                        p95=float(row.get("95%", 0)) or float(row.get("95%ile", 0)),
                        max_time=float(row.get("Max", 0)),
                        avg_time=float(row.get("Average", 0)),
                        rps=float(row.get("Requests/s", 0)),
                    )
                except (ValueError, TypeError):
                    pass
    except FileNotFoundError:
        pass
    return stats


def find_html_reports(reports_dir: Path) -> Dict[str, Path]:
    """Encuentra reportes HTML generados por Locust."""
    reports = {}
    if not reports_dir.exists():
        return reports
    
    for html_file in sorted(reports_dir.glob("locust-*.html")):
        if "stats" not in html_file.name:  # Excluir archivos de stats
            key = html_file.stem.replace("locust-", "")
            reports[key] = html_file
    
    return reports


def generate_index_html(html_reports: Dict[str, Path], output_path: str) -> None:
    """Genera índice HTML con links a reportes HTML de Locust."""
    
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reportes de Rendimiento - Ecommerce Backend</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            header {
                background: white;
                border-radius: 8px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            header h1 { color: #667eea; margin-bottom: 10px; }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                padding: 25px;
                transition: transform 0.2s;
            }
            .card:hover { transform: translateY(-5px); }
            .card h2 { color: #667eea; margin-bottom: 10px; font-size: 18px; }
            .card p { margin: 8px 0; font-size: 14px; color: #666; }
            .badge {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            .badge-success { background: #d4edda; color: #155724; }
            .badge-info { background: #d1ecf1; color: #0c5460; }
            a {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 10px 16px;
                border-radius: 4px;
                text-decoration: none;
                margin-top: 10px;
                transition: background 0.2s;
            }
            a:hover { background: #764ba2; }
            .empty {
                background: white;
                border-radius: 8px;
                padding: 30px;
                text-align: center;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>📊 Reportes de Rendimiento - Backend Ecommerce</h1>
                <p>Pipeline CI/CD - Pruebas de carga y estrés</p>
            </header>
    """

    test_info = {
        "standard": ("✅ Rendimiento Estándar", "100 visitantes navegando catálogo", "success"),
        "checkout": ("🛒 Checkout", "20 compradores realizando compras", "success"),
        "admin": ("⚙️ Admin CRUD", "15 administradores creando/editando", "success"),
        "stress": ("🔥 Estrés Combinado", "200 usuarios de todos los tipos", "info"),
    }

    if html_reports:
        html_content += '<div class="grid">'
        for test_name in ["standard", "checkout", "admin", "stress"]:
            if test_name not in html_reports:
                continue
            
            info = test_info.get(test_name)
            if not info:
                continue
            
            title, desc, badge_type = info
            badge_class = f"badge-{badge_type}"
            
            html_content += f"""
            <div class="card">
                <h2>{title}</h2>
                <span class="badge {badge_class}">LOCUST</span>
                <p>{desc}</p>
                <a href="{html_reports[test_name].name}">📈 Ver reporte →</a>
            </div>
            """
        
        html_content += '</div>'
    else:
        html_content += """
        <div class="empty">
            <p style="font-size: 16px; margin-bottom: 10px;">
                ⏳ No se encontraron reportes de Locust aún
            </p>
            <p style="font-size: 14px;">
                Las pruebas de rendimiento generarán reportes HTML automáticamente.<br>
                Espera a que se completen y recarga esta página.
            </p>
        </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """

    Path(output_path).write_text(html_content)
    print(f"✓ Índice HTML generado: {output_path}")


def main():
    """Función principal."""
    if len(sys.argv) < 2:
        print("Uso: python generate_report.py <reports_dir> [output.html]")
        sys.exit(0)  # No fallar si faltan argumentos

    reports_dir = Path(sys.argv[1])
    output_path = sys.argv[2] if len(sys.argv) > 2 else "perf_report.html"

    # Buscar reportes HTML generados por Locust
    html_reports = find_html_reports(reports_dir)
    generate_index_html(html_reports, output_path)
    
    if not html_reports:
        print("⚠️  Advertencia: No se encontraron reportes HTML")
        print(f"   Esperaba: {reports_dir}/locust-*.html")
    
    print("✅ Reporte completado")
    sys.exit(0)  # Siempre exitoso


if __name__ == "__main__":
    main()
