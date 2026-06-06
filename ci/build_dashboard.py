"""
ci/build_dashboard.py — Dashboard ejecutivo con tarjetas coloridas.

Uso:
  python ci/build_dashboard.py \
    --input dashboard-artifacts \
    --html-out dashboard/index.html \
    --md-out dashboard/summary.md

Sin dependencias externas (solo stdlib).
"""
from __future__ import annotations
import argparse, csv, glob, html, json, os, sys, xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ── Modelos ──────────────────────────────────────────────────────────────────
@dataclass
class Suite:
    name: str
    tests: int = 0; failures: int = 0; errors: int = 0; skipped: int = 0; time: float = 0.0
    @property
    def passed(self): return max(self.tests - self.failures - self.errors - self.skipped, 0)
    @property
    def ok(self): return (self.failures + self.errors) == 0

@dataclass
class Report:
    suites: list[Suite] = field(default_factory=list)
    line_pct: float | None = None
    branch_pct: float | None = None
    cov_source: str = ""
    bandit: dict[str, int] = field(default_factory=dict)
    zap: dict[str, int] = field(default_factory=dict)
    perf_p95: float | None = None
    notes: list[str] = field(default_factory=list)


# ── Parsers ───────────────────────────────────────────────────────────────────
def _files(root, *pats):
    found = []
    for p in pats:
        found.extend(glob.glob(os.path.join(root, "**", p), recursive=True))
    return sorted(set(found))

def parse_junit(root, rep):
    for path in _files(root, "*junit*.xml", "TEST-*.xml", "report.xml", "*-results.xml"):
        try:
            node = ET.parse(path).getroot()
            suites = list(node.iter("testsuite")) if node.tag != "testsuite" else [node]
            for s in suites:
                t = int(s.get("tests", 0) or 0)
                if t == 0 and not list(s): continue
                rep.suites.append(Suite(
                    name=s.get("name") or os.path.basename(path),
                    tests=t,
                    failures=int(s.get("failures", 0) or 0),
                    errors=int(s.get("errors", 0) or 0),
                    skipped=int(s.get("skipped", 0) or 0),
                    time=float(s.get("time", 0) or 0),
                ))
        except Exception as e:
            rep.notes.append(f"JUnit no parseado ({os.path.basename(path)}): {e}")

def parse_coverage(root, rep):
    for path in _files(root, "coverage*.xml"):
        try:
            node = ET.parse(path).getroot()
            lr = node.get("line-rate"); br = node.get("branch-rate")
            if lr: rep.line_pct = round(float(lr)*100, 1)
            if br: rep.branch_pct = round(float(br)*100, 1)
            rep.cov_source = "Cobertura XML"; return
        except Exception as e:
            rep.notes.append(f"coverage.xml: {e}")

def parse_lcov(root, rep):
    if rep.line_pct is not None: return
    for path in _files(root, "lcov.info"):
        try:
            found = hit = 0
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith("LF:"): found += int(line.strip().split(":",1)[1] or 0)
                    elif line.startswith("LH:"): hit += int(line.strip().split(":",1)[1] or 0)
            if found: rep.line_pct = round(hit/found*100, 1); rep.cov_source = "LCOV"; return
        except Exception as e:
            rep.notes.append(f"lcov.info: {e}")

def parse_bandit(root, rep):
    for path in _files(root, "bandit*.json"):
        try:
            data = json.load(open(path, encoding="utf-8-sig"))
            for issue in data.get("results", []):
                k = (issue.get("issue_severity") or "UNDEFINED").upper()
                rep.bandit[k] = rep.bandit.get(k, 0) + 1
            return
        except Exception as e:
            rep.notes.append(f"bandit.json: {e}")

def parse_zap(root, rep):
    _risk = {"3":"HIGH","2":"MEDIUM","1":"LOW","0":"INFO"}
    for path in _files(root, "*zap*.json", "report_json.json"):
        try:
            data = json.load(open(path, encoding="utf-8-sig"))
            sites = data.get("site") or data.get("sites") or []
            if isinstance(sites, dict): sites = [sites]
            for site in sites:
                for alert in site.get("alerts", []):
                    k = _risk.get(str(alert.get("riskcode","0")), "INFO")
                    rep.zap[k] = rep.zap.get(k, 0) + 1
            return
        except Exception as e:
            rep.notes.append(f"zap.json: {e}")

def parse_locust(root, rep):
    for path in _files(root, "*_stats.csv"):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                rows = list(csv.DictReader(fh))
            agg = next((r for r in rows if (r.get("Name") or "").strip() == "Aggregated"), None) or (rows[-1] if rows else None)
            if not agg: continue
            for k in ("95%","95%ile","P95"):
                if agg.get(k): rep.perf_p95 = float(agg[k]); return
        except Exception as e:
            rep.notes.append(f"locust stats: {e}")

def collect(input_dir):
    rep = Report()
    parse_junit(input_dir, rep)
    parse_coverage(input_dir, rep)
    parse_lcov(input_dir, rep)
    parse_bandit(input_dir, rep)
    parse_zap(input_dir, rep)
    parse_locust(input_dir, rep)
    return rep


# ── HTML ──────────────────────────────────────────────────────────────────────
def _bar(pct, color, gate=None):
    gate_line = f"left:{gate}%;background:#B4B2A9;width:2px;height:100%;position:absolute;top:0;" if gate else ""
    gate_html = f'<span style="{gate_line}"></span>' if gate else ""
    return (
        f'<div style="height:6px;background:#e2e8f0;border-radius:3px;margin-top:10px;position:relative;">'
        f'<div style="height:100%;width:{min(pct,100):.1f}%;background:{color};border-radius:3px;"></div>'
        f'{gate_html}</div>'
    )

def _badge(ok, skip=False):
    if skip: return '<span style="background:#f1f5f9;color:#64748b;font-size:11px;font-weight:500;padding:2px 8px;border-radius:999px;">skip</span>'
    if ok:   return '<span style="background:#dcfce7;color:#16a34a;font-size:11px;font-weight:500;padding:2px 8px;border-radius:999px;">pass</span>'
    return       '<span style="background:#fee2e2;color:#dc2626;font-size:11px;font-weight:500;padding:2px 8px;border-radius:999px;">fail</span>'

ACCENTS = ["#185FA5","#534AB7","#3B6D11","#0F6E56","#854F0B","#A32D2D"]

def render_html(rep: Report) -> str:
    total   = sum(s.tests for s in rep.suites)
    failed  = sum(s.failures + s.errors for s in rep.suites)
    skipped = sum(s.skipped for s in rep.suites)
    passed  = total - failed - skipped
    overall_ok = failed == 0

    sha   = os.environ.get("GITHUB_SHA","")[:7]
    ref   = os.environ.get("GITHUB_REF_NAME","develop")
    repo  = os.environ.get("GITHUB_REPOSITORY","tu-proyecto")
    flow  = os.environ.get("PIPELINE_FLOW","ci")
    ts    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    e = lambda x: html.escape(str(x))

    status_style = "background:#dcfce7;color:#16a34a;" if overall_ok else "background:#fee2e2;color:#dc2626;"
    status_txt   = "Pipeline OK" if overall_ok else "Pipeline con errores"

    # ── Tarjetas de métricas ─────────────────────────────────────────────────
    lp = rep.line_pct or 0
    bp = rep.branch_pct or 0
    lc = "#185FA5"  # informativo: la cobertura ya no es gate
    bc = "#534AB7"
    total_time = round(sum(s.time for s in rep.suites), 1)

    metric_cards = f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px;">
      <div style="background:#fff;border:0.5px solid #e2e8f0;border-radius:12px;padding:1rem 1.25rem;border-top:3px solid #3B6D11;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Tests pasados</div>
        <div style="font-size:28px;font-weight:500;color:#27500A;line-height:1;">{passed}</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px;">de {total} en total</div>
        {_bar(passed/total*100 if total else 0, "#3B6D11")}
      </div>
      <div style="background:#fff;border:0.5px solid #e2e8f0;border-radius:12px;padding:1rem 1.25rem;border-top:3px solid {lc};">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Cobertura líneas</div>
        <div style="font-size:28px;font-weight:500;color:{lc};line-height:1;">{lp:.1f}%</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px;">informativa (sin gate)</div>
        {_bar(lp, lc)}
      </div>
      <div style="background:#fff;border:0.5px solid #e2e8f0;border-radius:12px;padding:1rem 1.25rem;border-top:3px solid {bc};">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Cobertura ramas</div>
        <div style="font-size:28px;font-weight:500;color:{bc};line-height:1;">{bp:.1f}%</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px;">branch coverage</div>
        {_bar(bp, bc)}
      </div>
      <div style="background:#fff;border:0.5px solid #e2e8f0;border-radius:12px;padding:1rem 1.25rem;border-top:3px solid #854F0B;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Tiempo total</div>
        <div style="font-size:28px;font-weight:500;color:#633806;line-height:1;">{total_time}s</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px;">unit + integración</div>
      </div>
      {"" if rep.perf_p95 is None else f'''
      <div style="background:#fff;border:0.5px solid #e2e8f0;border-radius:12px;padding:1rem 1.25rem;border-top:3px solid #0F6E56;">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Rendimiento p95</div>
        <div style="font-size:28px;font-weight:500;color:#085041;line-height:1;">{int(rep.perf_p95)}ms</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px;">límite: 1500ms</div>
        {_bar(min(rep.perf_p95/1500*100,100), "#0F6E56")}
      </div>'''}
    </div>"""

    # ── Suites ───────────────────────────────────────────────────────────────
    def suite_card(s: Suite, accent: str) -> str:
        seg_pass = f'<div style="flex:{s.passed};background:#3B6D11;"></div>' if s.passed else ""
        seg_fail = f'<div style="flex:{s.failures+s.errors};background:#A32D2D;"></div>' if (s.failures+s.errors) else ""
        seg_skip = f'<div style="flex:{s.skipped};background:#B4B2A9;"></div>' if s.skipped else ""
        return f"""
        <div style="background:#fff;border:0.5px solid #e2e8f0;border-radius:12px;padding:1rem 1.25rem;border-left:3px solid {accent};">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            <span style="font-size:13px;font-weight:500;color:#1e293b;">{e(s.name)}</span>
            {_badge(s.ok)}
          </div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            <div style="background:#f8fafc;border-radius:8px;padding:8px 10px;">
              <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Pasaron</div>
              <div style="font-size:18px;font-weight:500;color:#16a34a;margin-top:2px;">{s.passed}</div>
            </div>
            <div style="background:#f8fafc;border-radius:8px;padding:8px 10px;">
              <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Fallaron</div>
              <div style="font-size:18px;font-weight:500;color:{"#dc2626" if (s.failures+s.errors) else "#94a3b8"};margin-top:2px;">{s.failures+s.errors}</div>
            </div>
            <div style="background:#f8fafc;border-radius:8px;padding:8px 10px;">
              <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Omitidos</div>
              <div style="font-size:18px;font-weight:500;color:#94a3b8;margin-top:2px;">{s.skipped}</div>
            </div>
            <div style="background:#f8fafc;border-radius:8px;padding:8px 10px;">
              <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Tiempo</div>
              <div style="font-size:18px;font-weight:500;color:#64748b;margin-top:2px;">{s.time:.1f}s</div>
            </div>
          </div>
          <div style="display:flex;gap:3px;height:6px;border-radius:3px;overflow:hidden;margin-top:10px;">
            {seg_pass}{seg_fail}{seg_skip}
          </div>
        </div>"""

    suites_html = "\n".join(
        suite_card(s, ACCENTS[i % len(ACCENTS)])
        for i, s in enumerate(rep.suites)
    ) or "<p style='color:#94a3b8;font-size:13px;'>Sin suites reportadas.</p>"

    # ── Seguridad ─────────────────────────────────────────────────────────────
    def sec_rows(data, order):
        rows = ""
        for k in order:
            v = data.get(k, 0)
            color = "#dc2626" if k in ("HIGH","CRITICAL") and v else "#ca8a04" if k == "MEDIUM" and v else "#64748b"
            rows += f'<div style="display:flex;justify-content:space-between;font-size:13px;padding:4px 0;border-bottom:0.5px solid #f1f5f9;"><span style="color:#64748b;">{k}</span><span style="font-weight:500;color:{color};">{v}</span></div>'
        return rows

    bandit_html = sec_rows(rep.bandit, ["HIGH","MEDIUM","LOW"]) or '<div style="font-size:13px;color:#94a3b8;">Sin hallazgos</div>'
    zap_html    = sec_rows(rep.zap, ["HIGH","MEDIUM","LOW","INFO"]) if rep.zap else '<div style="font-size:13px;color:#94a3b8;">Solo flujo CD</div>'

    notes_html = f'<p style="color:#94a3b8;font-size:11px;margin-top:16px;">{" · ".join(e(n) for n in rep.notes)}</p>' if rep.notes else ""

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pipeline dashboard · {e(repo)}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f8fafc; color:#1e293b; padding:2rem; }}
  .sec-title {{ font-size:11px; font-weight:500; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; margin:1.5rem 0 .75rem; }}
  .security-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; }}
  .sec-card {{ background:#fff; border:0.5px solid #e2e8f0; border-radius:12px; padding:1rem 1.25rem; }}
  .sec-card-title {{ font-size:12px; font-weight:500; color:#64748b; text-transform:uppercase; letter-spacing:.06em; margin-bottom:10px; }}
</style></head>
<body>

<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;flex-wrap:wrap;gap:8px;">
  <div>
    <div style="font-size:16px;font-weight:500;color:#1e293b;">Pipeline dashboard</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:2px;">flujo: {e(flow)} &nbsp;·&nbsp; rama: {e(ref)} &nbsp;·&nbsp; commit: {e(sha)} &nbsp;·&nbsp; {e(ts)}</div>
  </div>
  <span style="display:inline-flex;align-items:center;gap:6px;padding:5px 16px;border-radius:999px;font-size:13px;font-weight:500;{status_style}">{status_txt}</span>
</div>

<div class="sec-title">resumen general</div>
{metric_cards}

<div class="sec-title">suites de pruebas</div>
<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:16px;">
{suites_html}
</div>

<div class="sec-title">seguridad y calidad</div>
<div class="security-grid">
  <div class="sec-card">
    <div class="sec-card-title">SAST · Bandit</div>
    {bandit_html}
  </div>
  <div class="sec-card">
    <div class="sec-card-title">DAST · ZAP</div>
    {zap_html}
  </div>
  <div class="sec-card">
    <div class="sec-card-title">SonarCloud</div>
    <div style="font-size:13px;color:#64748b;padding:4px 0;">Análisis enviado en flujo CI.</div>
  </div>
</div>

{notes_html}
</body></html>"""


# ── Markdown ──────────────────────────────────────────────────────────────────
def render_markdown(rep: Report) -> str:
    total = sum(s.tests for s in rep.suites)
    failed = sum(s.failures+s.errors for s in rep.suites)
    passed = total - failed - sum(s.skipped for s in rep.suites)
    ok = lambda b: "✅" if b else "❌"
    flow = os.environ.get("PIPELINE_FLOW","ci")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"## Dashboard CI/CD — {flow.upper()}",
        f"_{ts}_", "",
        "| Check | Estado | Detalle |",
        "|---|---|---|",
        f"| Tests pasados       | {ok(failed==0)} | {passed}/{total} |",
    ]
    if rep.line_pct is not None:
        lines.append(f"| Cobertura líneas    | ℹ️ | {rep.line_pct:.1f}% (informativa) |")
    if rep.branch_pct is not None:
        lines.append(f"| Cobertura ramas     | ℹ️ | {rep.branch_pct:.1f}% |")
    for s in rep.suites:
        lines.append(f"| {s.name} | {ok(s.ok)} | {s.passed}/{s.tests} en {s.time:.1f}s |")
    if rep.perf_p95 is not None:
        lines.append(f"| Rendimiento p95     | {ok(rep.perf_p95<=1500)} | {int(rep.perf_p95)} ms |")
    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",    default="dashboard-artifacts")
    ap.add_argument("--html-out", default="dashboard/index.html")
    ap.add_argument("--md-out",   default="dashboard/summary.md")
    args = ap.parse_args()

    rep = collect(args.input)

    os.makedirs(os.path.dirname(args.html_out) or ".", exist_ok=True)
    with open(args.html_out, "w", encoding="utf-8") as f: f.write(render_html(rep))
    with open(args.md_out,   "w", encoding="utf-8") as f: f.write(render_markdown(rep))

    print(render_markdown(rep))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())