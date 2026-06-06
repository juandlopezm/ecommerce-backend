#!/usr/bin/env python3
"""Genera un dashboard agregado (HTML + Markdown) a partir de los artefactos de CI/CD.

Sin dependencias externas (solo stdlib). Es defensivo: cada parser va en su propio
try/except, de modo que un artefacto ausente o malformado NO rompe el dashboard.

Lee, de forma recursiva, un directorio de entrada y reconoce:
  - JUnit XML            : *junit*.xml, TEST-*.xml, report.xml  (suites de pruebas)
  - Cobertura XML        : coverage*.xml                        (% cobertura backend)
  - LCOV                 : lcov.info                            (% cobertura frontend)
  - Bandit JSON          : bandit*.json                         (hallazgos SAST)
  - ZAP JSON             : *zap*.json / report_json.json        (hallazgos DAST)
  - Locust CSV           : *_stats.csv                          (p95 de rendimiento)

Uso:
  python build_dashboard.py --input dashboard --html-out dashboard/index.html \
      --md-out dashboard/summary.md
"""

from __future__ import annotations

import argparse
import csv
import glob
import html
import json
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Salida UTF-8 robusta (los emojis fallan en consolas Windows cp1252; en runners Linux es UTF-8).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
except Exception:  # noqa: BLE001
    pass


# --------------------------------------------------------------------------- #
# Modelos de datos
# --------------------------------------------------------------------------- #
@dataclass
class SuiteResult:
    name: str
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    time: float = 0.0

    @property
    def passed(self) -> int:
        return max(self.tests - self.failures - self.errors - self.skipped, 0)

    @property
    def ok(self) -> bool:
        return (self.failures + self.errors) == 0


@dataclass
class Report:
    suites: list[SuiteResult] = field(default_factory=list)
    coverage_pct: float | None = None
    coverage_source: str = ""
    bandit: dict[str, int] = field(default_factory=dict)  # severidad -> count
    zap: dict[str, int] = field(default_factory=dict)  # riesgo -> count
    perf_p95_ms: float | None = None
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Parsers (cada uno tolerante a fallos)
# --------------------------------------------------------------------------- #
def _iter_files(root: str, *patterns: str) -> list[str]:
    found: list[str] = []
    for pat in patterns:
        found.extend(glob.glob(os.path.join(root, "**", pat), recursive=True))
    # Únicos, preservando orden estable.
    return sorted(set(found))


def parse_junit(root: str, rep: Report) -> None:
    files = _iter_files(root, "*junit*.xml", "TEST-*.xml", "report.xml", "*-results.xml")
    for path in files:
        try:
            tree = ET.parse(path)
            node = tree.getroot()
            suites = node.iter("testsuite") if node.tag != "testsuite" else [node]
            for s in suites:
                tests = int(s.get("tests", 0) or 0)
                if tests == 0 and not list(s):
                    continue
                name = s.get("name") or os.path.basename(path)
                rep.suites.append(
                    SuiteResult(
                        name=name,
                        tests=tests,
                        failures=int(s.get("failures", 0) or 0),
                        errors=int(s.get("errors", 0) or 0),
                        skipped=int(s.get("skipped", 0) or 0),
                        time=float(s.get("time", 0) or 0),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            rep.notes.append(f"JUnit no parseado ({os.path.basename(path)}): {exc}")


def parse_coverage_xml(root: str, rep: Report) -> None:
    if rep.coverage_pct is not None:
        return
    for path in _iter_files(root, "coverage*.xml"):
        try:
            node = ET.parse(path).getroot()
            line_rate = node.get("line-rate")
            if line_rate is not None:
                rep.coverage_pct = round(float(line_rate) * 100, 2)
                rep.coverage_source = "Cobertura XML"
                return
        except Exception as exc:  # noqa: BLE001
            rep.notes.append(f"coverage.xml no parseado: {exc}")


def parse_lcov(root: str, rep: Report) -> None:
    if rep.coverage_pct is not None:
        return
    for path in _iter_files(root, "lcov.info"):
        try:
            found = hit = 0
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith("LF:"):
                        found += int(line.strip().split(":", 1)[1] or 0)
                    elif line.startswith("LH:"):
                        hit += int(line.strip().split(":", 1)[1] or 0)
            if found:
                rep.coverage_pct = round(hit / found * 100, 2)
                rep.coverage_source = "LCOV"
                return
        except Exception as exc:  # noqa: BLE001
            rep.notes.append(f"lcov.info no parseado: {exc}")


def parse_bandit(root: str, rep: Report) -> None:
    for path in _iter_files(root, "bandit*.json"):
        try:
            data = json.load(open(path, encoding="utf-8-sig"))
            for issue in data.get("results", []):
                sev = (issue.get("issue_severity") or "UNDEFINED").upper()
                rep.bandit[sev] = rep.bandit.get(sev, 0) + 1
            return
        except Exception as exc:  # noqa: BLE001
            rep.notes.append(f"bandit.json no parseado: {exc}")


def parse_zap(root: str, rep: Report) -> None:
    _risk = {"3": "HIGH", "2": "MEDIUM", "1": "LOW", "0": "INFO"}
    for path in _iter_files(root, "*zap*.json", "report_json.json"):
        try:
            data = json.load(open(path, encoding="utf-8-sig"))
            sites = data.get("site") or data.get("sites") or []
            if isinstance(sites, dict):
                sites = [sites]
            for site in sites:
                for alert in site.get("alerts", []):
                    label = _risk.get(str(alert.get("riskcode", "0")), "INFO")
                    rep.zap[label] = rep.zap.get(label, 0) + 1
            return
        except Exception as exc:  # noqa: BLE001
            rep.notes.append(f"reporte ZAP no parseado: {exc}")


def parse_karate(root: str, rep: Report) -> None:
    """Karate standalone deja ``karate-summary-json.txt`` (estable) en target/karate-reports."""
    for path in _iter_files(root, "karate-summary-json.txt"):
        try:
            data = json.load(open(path, encoding="utf-8-sig"))
            passed = int(data.get("scenariosPassed", 0) or 0)
            failed = int(
                data.get("scenariosFailed", data.get("scenariosfailed", 0)) or 0
            )
            rep.suites.append(
                SuiteResult(
                    name="Karate (API, caja negra)",
                    tests=passed + failed,
                    failures=failed,
                    time=float(data.get("elapsedTime", 0) or 0) / 1000.0,
                )
            )
            return
        except Exception as exc:  # noqa: BLE001
            rep.notes.append(f"resumen Karate no parseado: {exc}")


def parse_locust(root: str, rep: Report) -> None:
    for path in _iter_files(root, "*_stats.csv"):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                rows = list(csv.DictReader(fh))
            agg = next((r for r in rows if (r.get("Name") or "").strip() == "Aggregated"), None)
            agg = agg or (rows[-1] if rows else None)
            if not agg:
                continue
            for key in ("95%", "95%ile", "P95", "95th percentile"):
                if key in agg and agg[key]:
                    rep.perf_p95_ms = float(agg[key])
                    return
        except Exception as exc:  # noqa: BLE001
            rep.notes.append(f"stats Locust no parseado: {exc}")


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def _badge(ok: bool) -> str:
    return "✅" if ok else "❌"


def render_markdown(rep: Report) -> str:
    lines: list[str] = ["## 📊 Dashboard de pruebas", ""]

    total = sum(s.tests for s in rep.suites)
    failed = sum(s.failures + s.errors for s in rep.suites)
    skipped = sum(s.skipped for s in rep.suites)
    passed = total - failed - skipped
    overall_ok = failed == 0

    lines.append(
        f"**Estado global:** {_badge(overall_ok)} "
        f"· {passed} ✓ / {failed} ✗ / {skipped} ⤼ de {total} pruebas"
    )
    if rep.coverage_pct is not None:
        gate = "✅" if rep.coverage_pct >= 70 else "⚠️"
        lines.append(f"**Cobertura:** {gate} {rep.coverage_pct:.2f}% ({rep.coverage_source})")
    if rep.perf_p95_ms is not None:
        lines.append(f"**Rendimiento (p95):** {rep.perf_p95_ms:.0f} ms")
    lines.append("")

    if rep.suites:
        lines += ["### Suites", "", "| Suite | Estado | ✓ | ✗ | ⤼ | Total | Tiempo |", "|---|---|--:|--:|--:|--:|--:|"]
        for s in rep.suites:
            lines.append(
                f"| {s.name} | {_badge(s.ok)} | {s.passed} | {s.failures + s.errors} "
                f"| {s.skipped} | {s.tests} | {s.time:.1f}s |"
            )
        lines.append("")

    if rep.bandit:
        detail = ", ".join(f"{k}: {v}" for k, v in sorted(rep.bandit.items()))
        lines.append(f"**SAST (Bandit):** {detail}")
    if rep.zap:
        detail = ", ".join(f"{k}: {v}" for k, v in sorted(rep.zap.items()))
        lines.append(f"**DAST (ZAP):** {detail}")
    if rep.notes:
        lines += ["", "<sub>" + " · ".join(html.escape(n) for n in rep.notes) + "</sub>"]
    return "\n".join(lines) + "\n"


def render_html(rep: Report) -> str:
    total = sum(s.tests for s in rep.suites)
    failed = sum(s.failures + s.errors for s in rep.suites)
    skipped = sum(s.skipped for s in rep.suites)
    passed = total - failed - skipped
    overall_ok = failed == 0

    sha = os.environ.get("GITHUB_SHA", "")[:7]
    ref = os.environ.get("GITHUB_REF_NAME", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    flow = os.environ.get("PIPELINE_FLOW", "")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def esc(x: object) -> str:
        return html.escape(str(x))

    rows = "".join(
        f"<tr class='{'ok' if s.ok else 'bad'}'><td>{esc(s.name)}</td>"
        f"<td>{'✅' if s.ok else '❌'}</td><td>{s.passed}</td>"
        f"<td>{s.failures + s.errors}</td><td>{s.skipped}</td>"
        f"<td>{s.tests}</td><td>{s.time:.1f}s</td></tr>"
        for s in rep.suites
    ) or "<tr><td colspan='7'>Sin suites reportadas</td></tr>"

    cov = ""
    if rep.coverage_pct is not None:
        color = "#22c55e" if rep.coverage_pct >= 70 else "#f59e0b"
        cov = (
            f"<div class='metric'><h3>Cobertura</h3>"
            f"<div class='bar'><span style='width:{min(rep.coverage_pct,100):.1f}%;"
            f"background:{color}'></span></div>"
            f"<p>{rep.coverage_pct:.2f}% <small>({esc(rep.coverage_source)})</small></p></div>"
        )

    def kv_block(title: str, data: dict[str, int]) -> str:
        if not data:
            return ""
        items = "".join(f"<li>{esc(k)}: <b>{v}</b></li>" for k, v in sorted(data.items()))
        return f"<div class='metric'><h3>{esc(title)}</h3><ul>{items}</ul></div>"

    perf = ""
    if rep.perf_p95_ms is not None:
        perf = f"<div class='metric'><h3>Rendimiento</h3><p>p95: <b>{rep.perf_p95_ms:.0f} ms</b></p></div>"

    notes = ""
    if rep.notes:
        notes = "<p class='notes'>" + " · ".join(esc(n) for n in rep.notes) + "</p>"

    status_txt = "PASÓ" if overall_ok else "FALLÓ"
    status_cls = "ok" if overall_ok else "bad"

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard CI/CD · {esc(repo)}</title>
<style>
  :root {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }}
  body {{ margin: 0; background: #0f172a; color: #e2e8f0; }}
  header {{ padding: 24px 32px; background: #1e293b; border-bottom: 1px solid #334155; }}
  h1 {{ margin: 0 0 4px; font-size: 22px; }}
  .meta {{ color: #94a3b8; font-size: 13px; }}
  .status {{ display: inline-block; padding: 4px 12px; border-radius: 999px; font-weight: 700; }}
  .status.ok {{ background: #14532d; color: #86efac; }}
  .status.bad {{ background: #7f1d1d; color: #fca5a5; }}
  main {{ padding: 24px 32px; max-width: 1100px; margin: 0 auto; }}
  .metrics {{ display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 24px; }}
  .metric {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px;
            padding: 16px 20px; min-width: 200px; flex: 1; }}
  .metric h3 {{ margin: 0 0 8px; font-size: 14px; color: #94a3b8; text-transform: uppercase; }}
  .metric ul {{ margin: 0; padding-left: 18px; }}
  .bar {{ background: #334155; border-radius: 6px; height: 12px; overflow: hidden; }}
  .bar span {{ display: block; height: 100%; }}
  table {{ width: 100%; border-collapse: collapse; background: #1e293b;
           border-radius: 12px; overflow: hidden; }}
  th, td {{ padding: 10px 14px; text-align: right; border-bottom: 1px solid #334155; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ background: #0f172a; color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
  tr.bad td {{ background: #2a1414; }}
  .notes {{ color: #64748b; font-size: 12px; margin-top: 16px; }}
</style></head>
<body>
<header>
  <h1>📊 Dashboard CI/CD — {esc(repo or 'proyecto')}</h1>
  <div class="meta">
    <span class="status {status_cls}">{status_txt}</span>
    &nbsp; {passed} ✓ / {failed} ✗ / {skipped} ⤼ de {total} pruebas
    &nbsp;·&nbsp; rama <code>{esc(ref)}</code>
    &nbsp;·&nbsp; commit <code>{esc(sha)}</code>
    &nbsp;·&nbsp; flujo <code>{esc(flow)}</code>
    &nbsp;·&nbsp; {esc(ts)}
  </div>
</header>
<main>
  <div class="metrics">{cov}{perf}{kv_block('SAST · Bandit', rep.bandit)}{kv_block('DAST · ZAP', rep.zap)}</div>
  <table>
    <thead><tr><th>Suite</th><th>Estado</th><th>✓</th><th>✗</th><th>⤼</th><th>Total</th><th>Tiempo</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  {notes}
</main>
</body></html>
"""


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build(input_dir: str) -> Report:
    rep = Report()
    parse_junit(input_dir, rep)
    parse_coverage_xml(input_dir, rep)
    parse_lcov(input_dir, rep)
    parse_bandit(input_dir, rep)
    parse_zap(input_dir, rep)
    parse_karate(input_dir, rep)
    parse_locust(input_dir, rep)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera el dashboard CI/CD agregado.")
    ap.add_argument("--input", default="dashboard", help="Directorio con artefactos descargados.")
    ap.add_argument("--html-out", default="dashboard/index.html")
    ap.add_argument("--md-out", default="dashboard/summary.md")
    args = ap.parse_args()

    rep = build(args.input)

    os.makedirs(os.path.dirname(args.html_out) or ".", exist_ok=True)
    with open(args.html_out, "w", encoding="utf-8") as fh:
        fh.write(render_html(rep))
    with open(args.md_out, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(rep))

    # Eco a stdout para depuración en el log de Actions.
    print(render_markdown(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
