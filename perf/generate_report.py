#!/usr/bin/env python3
"""
Generador de reportes consolidados de rendimiento (Locust).

Combina múltiples reportes CSV de Locust en un único dashboard HTML
con gráficas comparativas, métricas clave y análisis de resultados.
"""

import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
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


def generate_html(
    perf_results: Dict[str, Dict[str, LocustStats]], output_path: str
) -> None:
    """Genera reporte HTML consolidado de todas las pruebas."""

    # Calcular agregados y estadísticas
    total_requests = 0
    total_failures = 0
    all_p95_values = []

    for test_name, endpoints in perf_results.items():
        for endpoint, stats in endpoints.items():
            total_requests += stats.requests
            total_failures += stats.failures
            if stats.p95 > 0:
                all_p95_values.append(stats.p95)

    avg_p95 = sum(all_p95_values) / len(all_p95_values) if all_p95_values else 0
    failure_rate = (total_failures / total_requests * 100) if total_requests else 0

    # Badge de estado
    status = "✅ PASS" if avg_p95 <= 1500 and failure_rate < 5 else "⚠️ WARNING"
    status_color = "#28a745" if status == "✅ PASS" else "#ffc107"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte de Rendimiento - Ecommerce Backend</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{ max-width: 1400px; margin: 0 auto; }}
            header {{
                background: white;
                border-radius: 8px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            header h1 {{ color: #667eea; margin-bottom: 10px; }}
            .status-badge {{
                display: inline-block;
                background: {status_color};
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 10px;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }}
            .metric-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }}
            .metric-value {{
                font-size: 28px;
                font-weight: bold;
                color: #667eea;
            }}
            .metric-label {{
                font-size: 14px;
                color: #666;
                margin-top: 5px;
            }}
            .section {{
                background: white;
                border-radius: 8px;
                padding: 30px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .section h2 {{
                color: #667eea;
                margin-bottom: 20px;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background: #f8f9fa;
                font-weight: bold;
                color: #333;
            }}
            tr:hover {{ background: #f8f9fa; }}
            .chart-container {{
                position: relative;
                height: 400px;
                margin: 20px 0;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            .badge-success {{ background: #d4edda; color: #155724; }}
            .badge-warning {{ background: #fff3cd; color: #856404; }}
            .badge-danger {{ background: #f8d7da; color: #721c24; }}
            .success {{ color: #28a745; }}
            .warning {{ color: #ffc107; }}
            .danger {{ color: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>📊 Reporte de Rendimiento - Backend Ecommerce</h1>
                <p>Pipeline CI/CD - Pruebas de carga y estrés</p>
                <div class="status-badge">{status}</div>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{total_requests}</div>
                        <div class="metric-label">Peticiones totales</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{failure_rate:.1f}%</div>
                        <div class="metric-label">Tasa de fallos</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{avg_p95:.0f}ms</div>
                        <div class="metric-label">P95 promedio</div>
                    </div>
                </div>
            </header>
"""

    # Sección por cada tipo de prueba
    test_order = [
        "standard",
        "checkout",
        "admin",
        "stress",
    ]
    test_labels = {
        "standard": "✅ Rendimiento Estándar",
        "checkout": "🛒 Checkout",
        "admin": "⚙️ Admin CRUD",
        "stress": "🔥 Estrés",
    }

    for test_key in test_order:
        if test_key not in perf_results:
            continue

        endpoints = perf_results[test_key]
        total_req = sum(s.requests for s in endpoints.values())
        total_fail = sum(s.failures for s in endpoints.values())
        fail_pct = (
            (total_fail / total_req * 100) if total_req else 0
        )
        p95_vals = [s.p95 for s in endpoints.values() if s.p95 > 0]
        avg_p95_test = sum(p95_vals) / len(p95_vals) if p95_vals else 0

        html_content += f"""
            <div class="section">
                <h2>{test_labels.get(test_key, test_key)}</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Endpoint</th>
                            <th>Requests</th>
                            <th>Fallos</th>
                            <th>Mediana (ms)</th>
                            <th>P95 (ms)</th>
                            <th>Max (ms)</th>
                            <th>RPS</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for name, stats in sorted(endpoints.items()):
            status_icon = (
                "✅" if stats.failures == 0 else f"⚠️ ({stats.failures})"
            )
            html_content += f"""
                        <tr>
                            <td><strong>{name}</strong></td>
                            <td>{stats.requests}</td>
                            <td>{status_icon}</td>
                            <td>{stats.median:.0f}</td>
                            <td><strong>{stats.p95:.0f}</strong></td>
                            <td>{stats.max_time:.0f}</td>
                            <td>{stats.rps:.2f}</td>
                        </tr>
            """

        html_content += f"""
                    </tbody>
                </table>
                <div style="margin-top: 15px; font-size: 13px; color: #666;">
                    <strong>Resumen:</strong> {total_req} peticiones | 
                    {fail_pct:.1f}% fallos | 
                    P95 promedio: {avg_p95_test:.0f}ms
                </div>
            </div>
        """

    html_content += """
            <div class="section" style="background: #f8f9fa; color: #333;">
                <h2>ℹ️ Guía de interpretación</h2>
                <ul style="margin-left: 20px;">
                    <li><strong>Latencia mediana:</strong> Tiempo típico de respuesta. Objetivo: &lt;500ms</li>
                    <li><strong>P95:</strong> 95% de peticiones responden bajo este tiempo. Objetivo: &lt;1500ms</li>
                    <li><strong>RPS:</strong> Peticiones procesadas por segundo</li>
                    <li><strong>Fallos:</strong> Peticiones que resultaron en error (&lt;5% es aceptable)</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """

    Path(output_path).write_text(html_content)
    print(f"✓ Reporte HTML generado: {output_path}")


def main():
    """Función principal."""
    import sys

    if len(sys.argv) < 2:
        print(
            "Uso: python perf_report.py <reports_dir> [output.html]"
        )
        sys.exit(1)

    reports_dir = Path(sys.argv[1])
    output_path = sys.argv[2] if len(sys.argv) > 2 else "perf_report.html"

    perf_results = {
        "standard": parse_locust_csv(
            reports_dir / "locust-standard_stats.csv"
        ),
        "checkout": parse_locust_csv(
            reports_dir / "locust-checkout_stats.csv"
        ),
        "admin": parse_locust_csv(reports_dir / "locust-admin_stats.csv"),
        "stress": parse_locust_csv(reports_dir / "locust-stress_stats.csv"),
    }

    # Filtrar vacíos
    perf_results = {k: v for k, v in perf_results.items() if v}

    if not perf_results:
        print("⚠️  No se encontraron archivos CSV de Locust")
        sys.exit(1)

    generate_html(perf_results, output_path)
    print(f"✅ Reporte completado")


if __name__ == "__main__":
    main()
