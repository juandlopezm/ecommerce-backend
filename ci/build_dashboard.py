"""
ci/build_dashboard.py — Dashboard con navegación por pestañas.

Uso:
  python ci/build_dashboard.py \
    --input dashboard-artifacts \
    --html-out dashboard/index.html \
    --md-out dashboard/summary.md

Sin dependencias externas (solo stdlib).
Procesa: JUnit, Cobertura XML, LCOV, Bandit, ZAP, Locust.
Incluye copia de reportes HTML de rendimiento.
"""
from __future__ import annotations
import argparse, csv, glob, html, json, os, shutil, sys, xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass


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
class FileCov:
    filename: str
    line_pct: float
    branch_pct: float | None = None
    lines_covered: int = 0
    lines_valid: int = 0
    @property
    def lines_missed(self): return self.lines_valid - self.lines_covered

@dataclass
class SecFinding:
    tool: str  # "bandit" | "zap"
    title: str
    severity: str
    desc: str = ""
    solution: str = ""
    filename: str = ""
    line: int = 0
    count: int = 1
    instances: list[dict] = field(default_factory=list)

@dataclass
class Report:
    suites: list[Suite] = field(default_factory=list)
    line_pct: float | None = None
    branch_pct: float | None = None
    cov_source: str = ""
    bandit: dict[str, int] = field(default_factory=dict)
    zap: dict[str, int] = field(default_factory=dict)
    sec_findings: list[SecFinding] = field(default_factory=list)
    perf_p95: float | None = None
    perf_files: list[str] = field(default_factory=list)
    suites_cov: dict[str, float] = field(default_factory=dict)
    files_cov: dict[str, list[FileCov]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# ── Parsers ───────────────────────────────────────────────────────────────────
def _files(root, *pats):
    found = []
    for p in pats: found.extend(glob.glob(os.path.join(root, "**", p), recursive=True))
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
                    tests=t, failures=int(s.get("failures", 0) or 0),
                    errors=int(s.get("errors", 0) or 0),
                    skipped=int(s.get("skipped", 0) or 0),
                    time=float(s.get("time", 0) or 0),
                ))
        except Exception as e:
            rep.notes.append(f"JUnit: {os.path.basename(path)}: {e}")

_COV_SUITES = {
    "coverage-unit.xml": "unitarias",
    "coverage-int.xml": "integracion",
    "coverage-e2e.xml": "E2E",
}

def parse_coverage(root, rep):
    for path in _files(root, "coverage*.xml"):
        try:
            node = ET.parse(path).getroot()
            lr = node.get("line-rate"); br = node.get("branch-rate")
            fname = os.path.basename(path)
            if fname == "coverage.xml" and lr:
                rep.line_pct = round(float(lr)*100, 1)
                if br: rep.branch_pct = round(float(br)*100, 1)
                rep.cov_source = "Cobertura XML"
            elif lr and fname in _COV_SUITES:
                rep.suites_cov[_COV_SUITES[fname]] = round(float(lr)*100, 1)

            for pkg in node.iter("package"):
                for cls in pkg.iter("class"):
                    fn = cls.get("filename", "")
                    clr = cls.get("line-rate")
                    cbr = cls.get("branch-rate")
                    if fn and clr:
                        total = cov = 0
                        for ln in cls.iter("line"):
                            total += 1
                            if int(ln.get("hits", 0)) > 0: cov += 1
                        fc = FileCov(filename=fn, line_pct=round(float(clr)*100, 1),
                                     branch_pct=round(float(cbr)*100, 1) if cbr else None,
                                     lines_covered=cov, lines_valid=total)
                        key = _COV_SUITES.get(fname, "combinada")
                        rep.files_cov.setdefault(key, []).append(fc)
        except Exception as e:
            rep.notes.append(f"coverage.xml: {e}")

def parse_lcov(root, rep):
    if rep.line_pct is not None: return
    for path in _files(root, "lcov.info"):
        try:
            found = hit = 0
            cur_file = ""
            file_lines = {}
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith("SF:"):
                        cur_file = line.strip().split(":",1)[1]
                    elif line.startswith("DA:"):
                        pass
                    elif line.startswith("LF:"):
                        val = int(line.strip().split(":",1)[1] or 0)
                        found += val
                        if cur_file: file_lines[cur_file] = [val, 0]
                    elif line.startswith("LH:"):
                        val = int(line.strip().split(":",1)[1] or 0)
                        hit += val
                        if cur_file and cur_file in file_lines:
                            file_lines[cur_file][1] = val
                    elif line.startswith("end_of_record"):
                        cur_file = ""
            if found:
                rep.line_pct = round(hit/found*100, 1); rep.cov_source = "LCOV"
                for fn, (total, hits) in file_lines.items():
                    if total:
                        rep.files_cov.setdefault("lcov", []).append(
                            FileCov(filename=fn, line_pct=round(hits/total*100, 1),
                                    lines_covered=hits, lines_valid=total))
            return
        except Exception as e:
            rep.notes.append(f"lcov.info: {e}")

def parse_bandit(root, rep):
    for path in _files(root, "bandit*.json"):
        try:
            data = json.load(open(path, encoding="utf-8-sig"))
            for issue in data.get("results", []):
                k = (issue.get("issue_severity") or "UNDEFINED").upper()
                rep.bandit[k] = rep.bandit.get(k, 0) + 1
                rep.sec_findings.append(SecFinding(
                    tool="bandit",
                    title=issue.get("test_name", issue.get("issue_text", "unknown")),
                    severity=k,
                    desc=issue.get("issue_text", ""),
                    filename=issue.get("filename", ""),
                    line=int(issue.get("line_number", 0) or 0),
                ))
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
                    instances = alert.get("instances", [])
                    rep.sec_findings.append(SecFinding(
                        tool="zap",
                        title=alert.get("alert", alert.get("name", "unknown")),
                        severity=k,
                        desc=alert.get("desc", ""),
                        solution=alert.get("solution", ""),
                        count=len(instances),
                        instances=instances,
                    ))
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
            rep.notes.append(f"locust: {e}")

def collect(input_dir):
    rep = Report()
    parse_junit(input_dir, rep)
    parse_coverage(input_dir, rep)
    parse_lcov(input_dir, rep)
    parse_bandit(input_dir, rep)
    parse_zap(input_dir, rep)
    parse_locust(input_dir, rep)
    return rep


# ── Copiar reportes HTML de rendimiento ─────────────────────────────────────
def copy_perf_reports(input_dir: str, output_dir: str, rep: Report) -> None:
    perf_dirs = [os.path.join(input_dir, d) for d in os.listdir(input_dir)
                 if os.path.isdir(os.path.join(input_dir, d)) and
                 (d == "cd-perf" or d.startswith("perf"))]
    if not perf_dirs:
        rep.notes.append("Sin reportes de rendimiento")
        return
    perf_out = os.path.join(output_dir, "perf")
    os.makedirs(perf_out, exist_ok=True)
    html_files = []
    for perf_dir in perf_dirs:
        for html_path in _files(perf_dir, "*.html", "*.csv"):
            dst = os.path.join(perf_out, os.path.basename(html_path))
            shutil.copy2(html_path, dst)
            if os.path.basename(html_path).endswith(".html"):
                html_files.append(os.path.basename(html_path))
    rep.perf_files = sorted(set(html_files))
    if rep.perf_files:
        rep.notes.append(f"Reportes rendimiento copiados ({len(rep.perf_files)})")


# ── HTML ──────────────────────────────────────────────────────────────────────
def _bar(pct, color, gate=None):
    gate_line = f"left:{gate}%;background:#B4B2A9;width:2px;height:100%;position:absolute;top:0;" if gate else ""
    gate_html = f'<span style="{gate_line}"></span>' if gate else ""
    return (f'<div style="height:6px;background:#e2e8f0;border-radius:3px;margin-top:10px;position:relative;">'
            f'<div style="height:100%;width:{min(pct,100):.1f}%;background:{color};border-radius:3px;"></div>'
            f'{gate_html}</div>')

ACCENTS = ["#6366f1","#8b5cf6","#10b981","#0ea5e9","#f59e0b","#ef4444"]

NAV_ITEMS = [
    ("tab-resumen", "📊 Resumen"),
    ("tab-pruebas", "🧪 Pruebas"),
    ("tab-cobertura", "📁 Cobertura"),
    ("tab-seguridad", "🔒 Seguridad"),
    ("tab-rendimiento", "⚡ Rendimiento"),
]

def render_html(rep: Report) -> str:
    total   = sum(s.tests for s in rep.suites)
    failed  = sum(s.failures + s.errors for s in rep.suites)
    skipped = sum(s.skipped for s in rep.suites)
    passed  = total - failed - skipped
    overall_ok = failed == 0

    sha  = os.environ.get("GITHUB_SHA","")[:7]
    ref  = os.environ.get("GITHUB_REF_NAME","")
    repo = os.environ.get("GITHUB_REPOSITORY","")
    flow = os.environ.get("PIPELINE_FLOW","")
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    e    = lambda x: html.escape(str(x))

    status_txt  = "Pipeline OK" if overall_ok else "Pipeline con errores"
    status_cls  = "ok" if overall_ok else "bad"
    total_time  = round(sum(s.time for s in rep.suites), 1)

    # ── Pestaña: Resumen ──────────────────────────────────────────────────
    lp  = rep.line_pct or 0
    bp  = rep.branch_pct or 0

    metric_cards = f"""
    <div class="grid-4">
      <div class="card" style="border-top:3px solid #10b981;">
        <div class="card-label">Tests pasados</div>
        <div class="card-value" style="color:#10b981;">{passed}</div>
        <div class="card-sub">de {total} · {failed} fallos · {skipped} omitidos</div>
        {_bar(passed/total*100 if total else 0, "#10b981")}
      </div>
      <div class="card" style="border-top:3px solid #6366f1;">
        <div class="card-label">Cobertura líneas</div>
        <div class="card-value" style="color:#6366f1;">{lp:.1f}%</div>
        <div class="card-sub">{rep.cov_source or "—"}</div>
        {_bar(lp, "#6366f1")}
      </div>
      <div class="card" style="border-top:3px solid #8b5cf6;">
        <div class="card-label">Cobertura ramas</div>
        <div class="card-value" style="color:#8b5cf6;">{bp:.1f}%</div>
        <div class="card-sub">branch coverage</div>
        {_bar(bp, "#8b5cf6")}
      </div>
      <div class="card" style="border-top:3px solid #f59e0b;">
        <div class="card-label">Tiempo total</div>
        <div class="card-value" style="color:#f59e0b;">{total_time}s</div>
        <div class="card-sub">suites de prueba</div>
      </div>
    </div>"""

    def _cov_card(label, pct, color, sub=""):
        if pct is None: return ""
        return f"""
        <div class="card" style="border-top:3px solid {color};">
          <div class="card-label">{e(label)}</div>
          <div class="card-value" style="color:{color};">{pct:.1f}%</div>
          <div class="card-sub">{e(sub) if sub else 'cobertura líneas'}</div>
          {_bar(pct, color)}
        </div>"""

    cov_cards = _cov_card("Cobertura unitarias", rep.suites_cov.get("unitarias"), "#a855f7")
    cov_cards += _cov_card("Cobertura integración", rep.suites_cov.get("integracion"), "#ec4899")
    cov_cards += _cov_card("Cobertura E2E", rep.suites_cov.get("E2E"), "#14b8a6")

    perf_card = ""
    if rep.perf_p95 is not None:
        perf_color = "#10b981" if rep.perf_p95 <= 1500 else "#ef4444"
        perf_card = f"""
        <div class="card" style="border-top:3px solid #0ea5e9;">
          <div class="card-label">Rendimiento p95</div>
          <div class="card-value" style="color:#0ea5e9;">{int(rep.perf_p95)}ms</div>
          <div class="card-sub">límite 1500ms</div>
          {_bar(min(rep.perf_p95/1500*100,100), perf_color)}
        </div>"""

    bandit_total = sum(rep.bandit.values())
    zap_total = sum(rep.zap.values())

    tab_resumen = f"""
    <div class="tab-content" id="tab-resumen">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
        <span class="status-badge {status_cls}">{status_txt}</span>
        <span style="font-size:13px;color:#94a3b8;">
          rama: <code>{e(ref)}</code> · commit: <code>{e(sha)}</code> · flujo: <code>{e(flow)}</code> · {e(ts)}
        </span>
      </div>
      {metric_cards}
      {"<div class='grid-4'>"+cov_cards+"</div>" if cov_cards.strip() else ""}
      <div class="grid-4">
        {perf_card}
        <div class="card" style="border-top:3px solid #ef4444;">
          <div class="card-label">Seguridad</div>
          <div class="card-value" style="color:#ef4444;">{bandit_total + zap_total}</div>
          <div class="card-sub">SAST: {bandit_total} · DAST: {zap_total} hallazgos</div>
        </div>
      </div>
    </div>"""

    # ── Pestaña: Pruebas ──────────────────────────────────────────────────
    def suite_card(s, accent, cov_pct):
        seg_pass = f'<div style="flex:{s.passed};background:#10b981;"></div>' if s.passed else ""
        seg_fail = f'<div style="flex:{s.failures+s.errors};background:#ef4444;"></div>' if (s.failures+s.errors) else ""
        seg_skip = f'<div style="flex:{s.skipped};background:#94a3b8;"></div>' if s.skipped else ""
        ok_badge = '<span class="badge pass">pass</span>' if s.ok else '<span class="badge fail">fail</span>'
        cov_html = ""
        if cov_pct is not None:
            cov_color = "#10b981" if cov_pct >= 70 else "#f59e0b" if cov_pct >= 50 else "#ef4444"
            cov_html = f"""
          <div style="margin-top:12px;padding-top:10px;border-top:1px solid #334155;">
            <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
              <span style="color:#94a3b8;">Cobertura</span>
              <span style="color:{cov_color};font-weight:600;">{cov_pct}%</span>
            </div>
            <div style="height:6px;background:#334155;border-radius:3px;overflow:hidden;">
              <div style="width:{cov_pct}%;height:100%;background:{cov_color};border-radius:3px;"></div>
            </div>
          </div>"""
        return f"""
        <div class="suite-card" style="border-left:3px solid {accent};">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            <span style="font-size:14px;font-weight:500;">{e(s.name)}</span>
            {ok_badge}
          </div>
          <div class="suite-stats">
            <div><span class="stat-label">Pasaron</span><span class="stat-val" style="color:#10b981;">{s.passed}</span></div>
            <div><span class="stat-label">Fallaron</span><span class="stat-val" style="color:{"#ef4444" if s.failures+s.errors else "#94a3b8"};">{s.failures+s.errors}</span></div>
            <div><span class="stat-label">Omitidos</span><span class="stat-val">{s.skipped}</span></div>
            <div><span class="stat-label">Tiempo</span><span class="stat-val">{s.time:.1f}s</span></div>
          </div>
          <div style="display:flex;gap:3px;height:6px;border-radius:3px;overflow:hidden;margin-top:10px;">
            {seg_pass}{seg_fail}{seg_skip}
          </div>
          {cov_html}
        </div>"""

    def _cov_name(n):
        nlow = n.lower().strip()
        if "unitar" in nlow: return "unitarias"
        if "integra" in nlow: return "integracion"
        if "e2e" in nlow: return "E2E"
        return n

    suites_html = "\n".join(
        suite_card(s, ACCENTS[i % len(ACCENTS)], rep.suites_cov.get(_cov_name(s.name)))
        for i, s in enumerate(rep.suites)
    ) or "<p style='color:#94a3b8;font-size:13px;'>Sin suites reportadas.</p>"

    tab_pruebas = f"""
    <div class="tab-content" id="tab-pruebas" style="display:none;">
      <div style="display:flex;flex-direction:column;gap:10px;">
        {suites_html}
      </div>
    </div>"""

    # ── Pestaña: Seguridad ────────────────────────────────────────────────
    def sec_list(data, order, empty_msg):
        if not data: return f'<div style="color:#94a3b8;font-size:13px;">{empty_msg}</div>'
        rows = ""
        for k in order:
            v = data.get(k, 0)
            color = {"HIGH":"#ef4444","MEDIUM":"#f59e0b","LOW":"#94a3b8","INFO":"#64748b"}.get(k, "#64748b")
            rows += f'<div class="sec-row"><span>{k}</span><span style="color:{color};font-weight:500;">{v}</span></div>'
        return rows

    def finding_card(f):
        sev_color = {"HIGH":"#ef4444","MEDIUM":"#f59e0b","LOW":"#94a3b8","INFO":"#64748b"}.get(f.severity, "#64748b")
        badge = f'<span style="display:inline-block;padding:1px 8px;border-radius:999px;font-size:10px;font-weight:600;background:{sev_color}20;color:{sev_color};">{f.severity}</span>'
        loc = ""
        if f.filename:
            loc = f'<span style="color:#64748b;font-size:12px;">{e(f.filename)}:{f.line}</span>'
        elif f.count > 1:
            loc = f'<span style="color:#64748b;font-size:12px;">{f.count} instancias</span>'
        inst_html = ""
        for inst in f.instances[:5]:
            uri = inst.get("uri", "")
            method = inst.get("method", "")
            inst_html += f'<div style="padding:4px 8px;background:#0f172a;border-radius:4px;margin:4px 0;font-size:12px;word-break:break-all;"><code style="background:transparent;padding:0;color:#64748b;">{e(method)}</code> {e(uri)}</div>'
        if len(f.instances) > 5:
            inst_html += f'<div style="color:#64748b;font-size:11px;padding:4px 8px;">... y {len(f.instances)-5} más</div>'
        desc = f.desc[:300] + ("…" if len(f.desc) > 300 else "") if f.desc else ""
        desc = desc.replace("<p>", "").replace("</p>", "").replace("<br>", "\n")
        sol = f.solution[:200] + ("…" if len(f.solution) > 200 else "") if f.solution else ""
        sol = sol.replace("<p>", "").replace("</p>", "").replace("<br>", "\n")

        return f"""
        <details class="sec-detail" style="margin-bottom:8px;">
          <summary style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 12px;background:#1e293b;border:1px solid #334155;border-radius:8px;font-size:13px;">
            <span style="flex:1;">{e(f.title[:80])}</span>
            {badge}{loc}
          </summary>
          <div style="padding:12px;background:#0f172a;border:1px solid #334155;border-top:none;border-radius:0 0 8px 8px;font-size:13px;">
            {f'<div style="margin-bottom:8px;color:#94a3b8;">{e(desc)}</div>' if desc else ''}
            {f'<div style="margin-bottom:8px;"><span style="color:#10b981;">Solución:</span> <span style="color:#94a3b8;">{e(sol)}</span></div>' if sol else ''}
            {f'<div><span style="color:#f59e0b;">Instancias:</span>{inst_html}</div>' if inst_html else ''}
          </div>
        </details>"""

    findings_bandit = [f for f in rep.sec_findings if f.tool == "bandit"]
    findings_zap = [f for f in rep.sec_findings if f.tool == "zap"]

    tab_seguridad = f"""
    <div class="tab-content" id="tab-seguridad" style="display:none;">
      <div class="security-grid">
        <div class="sec-card">
          <div class="sec-title">SAST · Bandit ({sum(rep.bandit.values())} hallazgos)</div>
          {sec_list(rep.bandit, ["HIGH","MEDIUM","LOW"], "Sin hallazgos")}
          <div style="margin-top:10px;max-height:500px;overflow-y:auto;">
            {''.join(finding_card(f) for f in findings_bandit)}
          </div>
        </div>
        <div class="sec-card">
          <div class="sec-title">DAST · ZAP ({sum(rep.zap.values())} alertas)</div>
          {sec_list(rep.zap, ["HIGH","MEDIUM","LOW","INFO"], "Sin alertas")}
          <div style="margin-top:10px;max-height:500px;overflow-y:auto;">
            {''.join(finding_card(f) for f in findings_zap)}
          </div>
        </div>
        <div class="sec-card">
          <div class="sec-title">SonarCloud</div>
          <div style="font-size:13px;color:#94a3b8;">Análisis enviado en CI.</div>
        </div>
      </div>
    </div>"""

    # ── Pestaña: Rendimiento ──────────────────────────────────────────────
    perf_content = ""
    if rep.perf_files:
        test_labels = {
            "locust-standard": ("Rendimiento Estándar", "100 visitantes"),
            "locust-checkout": ("Checkout", "20 compradores"),
            "locust-admin": ("Admin CRUD", "15 administradores"),
            "locust-stress": ("Estrés Combinado", "200 usuarios mixtos"),
        }
        cards = ""
        for fname in rep.perf_files:
            base = fname.replace(".html", "")
            info = test_labels.get(base, (base.replace("locust-","").replace("-"," ").title(), ""))
            cards += f"""
            <a href="perf/{fname}" class="perf-card">
              <div style="font-size:14px;font-weight:500;">{e(info[0])}</div>
              <div style="font-size:12px;color:#94a3b8;">{e(info[1])}</div>
              <div style="font-size:12px;color:#0ea5e9;margin-top:8px;">📈 Ver reporte →</div>
            </a>"""
        perf_content = f'<div class="perf-grid">{cards}</div>'
    else:
        perf_content = '<p style="color:#94a3b8;">Sin reportes de rendimiento disponibles.</p>'

    tab_rendimiento = f"""
    <div class="tab-content" id="tab-rendimiento" style="display:none;">
      {perf_content}
    </div>"""

    # ── Pestaña: Cobertura por archivo ──────────────────────────────────
    def cov_table(key, title):
        files = rep.files_cov.get(key)
        if not files: return ""
        rows = ""
        t_cov = t_valid = 0
        for f in sorted(files, key=lambda x: x.filename):
            lc = f.line_pct
            bc = f.branch_pct
            lcol = "#10b981" if lc >= 70 else "#f59e0b" if lc >= 50 else "#ef4444"
            t_cov += f.lines_covered; t_valid += f.lines_valid
            rows += f"""
            <tr>
              <td style="padding:6px 12px;color:#e2e8f0;font-size:13px;font-family:monospace;">{e(f.filename)}</td>
              <td style="padding:6px 12px;text-align:right;font-weight:600;color:{lcol};font-size:13px;">{lc:.1f}%</td>
              <td style="padding:6px 12px;width:140px;">
                <div style="height:6px;background:#334155;border-radius:3px;overflow:hidden;">
                  <div style="width:{lc}%;height:100%;background:{lcol};border-radius:3px;"></div>
                </div>
              </td>
              <td style="padding:6px 12px;text-align:right;color:#e2e8f0;font-size:13px;">{f.lines_covered}</td>
              <td style="padding:6px 12px;text-align:right;color:#94a3b8;font-size:13px;">{f.lines_valid}</td>
              <td style="padding:6px 12px;text-align:right;color:{'#10b981' if f.lines_missed==0 else '#ef4444'};font-size:13px;">{f.lines_missed}</td>
              <td style="padding:6px 12px;text-align:right;font-size:13px;color:{'#10b981' if (bc or 0) >= 70 else '#f59e0b' if (bc or 0) >= 50 else '#ef4444' if bc is not None else '#64748b'};">{f'{bc:.1f}%' if bc is not None else '—'}</td>
            </tr>"""
        t_pct = round(t_cov / t_valid * 100, 1) if t_valid else 0
        totals = f"""
            <tr style="background:#0f172a;border-top:2px solid #334155;">
              <td style="padding:8px 12px;font-weight:600;color:#e2e8f0;font-size:13px;">TOTAL</td>
              <td style="padding:8px 12px;text-align:right;font-weight:700;color:{'#10b981' if t_pct>=70 else '#f59e0b'};font-size:13px;">{t_pct:.1f}%</td>
              <td style="padding:8px 12px;width:140px;">
                <div style="height:8px;background:#334155;border-radius:4px;overflow:hidden;">
                  <div style="width:{t_pct}%;height:100%;background:{'#10b981' if t_pct>=70 else '#f59e0b' if t_pct>=50 else '#ef4444'};border-radius:4px;"></div>
                </div>
              </td>
              <td style="padding:8px 12px;text-align:right;font-weight:600;color:#e2e8f0;font-size:13px;">{t_cov}</td>
              <td style="padding:8px 12px;text-align:right;font-weight:600;color:#e2e8f0;font-size:13px;">{t_valid}</td>
              <td style="padding:8px 12px;text-align:right;font-weight:600;color:{'#10b981' if t_valid-t_cov==0 else '#ef4444'};font-size:13px;">{t_valid-t_cov}</td>
              <td style="padding:8px 12px;"></td>
            </tr>"""
        return f"""
        <div style="margin-bottom:20px;">
          <div style="font-size:14px;font-weight:500;color:#e2e8f0;margin-bottom:10px;">{e(title)} <span style="font-weight:400;color:#64748b;">({len(files)} archivos, {t_valid} líneas)</span></div>
          <div style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden;">
            <thead>
              <tr style="background:#0f172a;">
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Archivo</th>
                <th style="padding:8px 12px;text-align:right;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Cobertura</th>
                <th style="padding:8px 12px;width:140px;"></th>
                <th style="padding:8px 12px;text-align:right;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Cubiertas</th>
                <th style="padding:8px 12px;text-align:right;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Totales</th>
                <th style="padding:8px 12px;text-align:right;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Faltantes</th>
                <th style="padding:8px 12px;text-align:right;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Ramas</th>
              </tr>
            </thead>
            <tbody>{rows}{totals}</tbody>
          </table>
          </div>
        </div>"""

    tab_cobertura_parts = ""
    for key, title in [("unitarias", "Unitarias"), ("integracion", "Integración"), ("E2E", "E2E"), ("combinada", "Combinada"), ("lcov", "LCOV")]:
        tab_cobertura_parts += cov_table(key, title)

    tab_cobertura = f"""
    <div class="tab-content" id="tab-cobertura" style="display:none;">
      {tab_cobertura_parts if tab_cobertura_parts else '<p style="color:#94a3b8;">Sin datos de cobertura por archivo.</p>'}
    </div>"""

    # ── Notas ──────────────────────────────────────────────────────────────
    notes_html = ""
    if rep.notes:
        notes_html = f'<div style="margin-top:20px;padding:12px 16px;background:#1e293b;border-radius:8px;font-size:11px;color:#64748b;">{" · ".join(e(n) for n in rep.notes)}</div>'

    # ── Navegación ────────────────────────────────────────────────────────
    nav_links = "".join(
        f'<button class="tab-btn{" active" if i==0 else ""}" data-tab="{id_}">{label}</button>'
        for i, (id_, label) in enumerate(NAV_ITEMS)
    )

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard · {e(repo or "CI/CD")}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0f172a; color:#e2e8f0; min-height:100vh; }}
  .app {{ display:flex; min-height:100vh; }}
  .sidebar {{ width:220px; background:#1e293b; border-right:1px solid #334155; padding:20px 0; flex-shrink:0; }}
  .sidebar-title {{ font-size:14px; font-weight:600; padding:0 20px 16px; color:#e2e8f0; border-bottom:1px solid #334155; }}
  .sidebar-title small {{ display:block; font-size:11px; color:#64748b; font-weight:400; margin-top:2px; }}
  .tab-btn {{ display:block; width:100%; background:none; border:none; color:#94a3b8; font-size:13px; text-align:left; padding:10px 20px; cursor:pointer; transition:all .15s; }}
  .tab-btn:hover {{ background:#334155; color:#e2e8f0; }}
  .tab-btn.active {{ background:#334155; color:#6366f1; font-weight:500; border-right:2px solid #6366f1; }}
  .main {{ flex:1; padding:24px 32px; overflow-y:auto; }}
  .tab-content {{ animation:fade .2s ease; }}
  @keyframes fade {{ from{{opacity:0;transform:translateY(4px)}} to{{opacity:1;transform:translateY(0)}} }}
  .grid-4 {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:16px; }}
  .card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:16px 20px; }}
  .card-label {{ font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px; }}
  .card-value {{ font-size:28px; font-weight:600; line-height:1.2; }}
  .card-sub {{ font-size:12px; color:#64748b; margin-top:4px; }}
  .status-badge {{ display:inline-block; padding:4px 14px; border-radius:999px; font-size:13px; font-weight:600; }}
  .status-badge.ok {{ background:#064e3b; color:#6ee7b7; }}
  .status-badge.bad {{ background:#7f1d1d; color:#fca5a5; }}
  .badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:500; }}
  .badge.pass {{ background:#064e3b; color:#6ee7b7; }}
  .badge.fail {{ background:#7f1d1d; color:#fca5a5; }}
  .suite-card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:16px 20px; }}
  .suite-stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-top:8px; }}
  .suite-stats > div {{ background:#0f172a; border-radius:8px; padding:8px 10px; }}
  .stat-label {{ display:block; font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:.05em; }}
  .stat-val {{ display:block; font-size:18px; font-weight:500; margin-top:2px; color:#e2e8f0; }}
  .security-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
  .sec-card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:16px 20px; }}
  .sec-title {{ font-size:12px; font-weight:500; color:#94a3b8; text-transform:uppercase; letter-spacing:.06em; margin-bottom:10px; }}
  .sec-row {{ display:flex; justify-content:space-between; font-size:13px; padding:6px 0; border-bottom:1px solid #1e293b; }}
  .sec-detail summary {{ list-style:none; }}
  .sec-detail summary::-webkit-details-marker {{ display:none; }}
  .sec-detail summary::after {{ content:"▶"; margin-left:auto; color:#64748b; font-size:10px; transition:transform .15s; }}
  .sec-detail[open] summary::after {{ transform:rotate(90deg); }}
  .perf-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px; }}
  .perf-card {{ display:block; background:#1e293b; border:1px solid #334155; border-radius:12px; padding:16px 20px; text-decoration:none; color:inherit; border-left:3px solid #0ea5e9; transition:transform .15s,background .15s; }}
  .perf-card:hover {{ background:#334155; transform:translateY(-2px); }}
  code {{ font-size:12px; background:#1e293b; padding:1px 6px; border-radius:4px; }}
  @media (max-width:768px) {{ .app {{ flex-direction:column; }} .sidebar {{ width:100%; border-right:none; border-bottom:1px solid #334155; padding:12px 0; }} .tab-btn {{ display:inline-block; width:auto; border-right:none !important; }} .main {{ padding:16px; }} }}
</style></head>
<body>
<div class="app">
  <nav class="sidebar">
    <div class="sidebar-title">
      Pipeline Dashboard
      <small>{e(repo or "proyecto")}</small>
    </div>
    {nav_links}
  </nav>
  <main class="main">
    {tab_resumen}
    {tab_pruebas}
    {tab_cobertura}
    {tab_seguridad}
    {tab_rendimiento}
    {notes_html}
  </main>
</div>
<script>
(function() {{
  const btns = document.querySelectorAll('.tab-btn');
  const tabs = {{}};
  document.querySelectorAll('.tab-content').forEach(t => {{ tabs[t.id] = t; }});
  btns.forEach(btn => {{
    btn.addEventListener('click', function() {{
      btns.forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      Object.values(tabs).forEach(t => t.style.display = 'none');
      const tab = tabs[this.dataset.tab];
      if (tab) tab.style.display = '';
    }});
  }});
}})();
</script>
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
        lines.append(f"| Cobertura líneas    | ℹ️ | {rep.line_pct:.1f}% ({rep.cov_source}) |")
    if rep.branch_pct is not None:
        lines.append(f"| Cobertura ramas     | ℹ️ | {rep.branch_pct:.1f}% |")
    for s in rep.suites:
        lines.append(f"| {s.name} | {ok(s.ok)} | {s.passed}/{s.tests} en {s.time:.1f}s |")
    if rep.perf_p95 is not None:
        lines.append(f"| Rendimiento p95     | {ok(rep.perf_p95<=1500)} | {int(rep.perf_p95)} ms |")
    if rep.perf_files:
        links = ", ".join(f"[{f}](perf/{f})" for f in rep.perf_files)
        lines.append(f"| Reportes rendimiento | 📊 | {links} |")
    if rep.bandit:
        lines.append(f"| SAST (Bandit)       | ℹ️ | {sum(rep.bandit.values())} hallazgos |")
    if rep.zap:
        lines.append(f"| DAST (ZAP)          | ℹ️ | {sum(rep.zap.values())} alertas |")
    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",    default="dashboard-artifacts")
    ap.add_argument("--html-out", default="dashboard/index.html")
    ap.add_argument("--md-out",   default="dashboard/summary.md")
    args = ap.parse_args()

    rep = collect(args.input)
    html_dir = os.path.dirname(args.html_out) or "."
    os.makedirs(html_dir, exist_ok=True)

    copy_perf_reports(args.input, html_dir, rep)

    with open(args.html_out, "w", encoding="utf-8") as f: f.write(render_html(rep))
    with open(args.md_out,   "w", encoding="utf-8") as f: f.write(render_markdown(rep))
    print(render_markdown(rep))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
