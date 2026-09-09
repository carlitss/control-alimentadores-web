"""
dashboard_html.py — Dashboard ejecutivo en HTML/CSS puro (sin Plotly, sin
Chart.js, sin canvas), segun el diseño de referencia entregado por el
usuario (Dashboard_Ejecutivo_Actividades_MT_BT.html). Reemplaza a
dashboard_charts.py (Fase 6) como capa de presentacion del Dashboard.

Los datos siguen viniendo de las mismas queries de core/db.get_dashboard_*
(sin cambios) -- esto es SOLO la capa visual: se arma un string HTML con
estilos con alcance acotado al contenedor `.exec-dash` (para no pisar los
estilos propios de Streamlit) y se inyecta con st.markdown(unsafe_allow_
html=True).
"""
import html as _html

TEAL, AMBER, CORAL, GREY = '#2E9E8F', '#E8A33D', '#D6564C', '#8A95A1'
NAVY, NAVY_SOFT = '#16324F', '#3D5877'
DONUT_PALETTE = [NAVY, AMBER, GREY, TEAL, CORAL, NAVY_SOFT, '#5B8DBE']

CSS = """
<style>
/* Se renderiza dentro de un <iframe> aislado (components.html), asi que
tocar body es seguro aca -- no hay riesgo de pisar los estilos del resto
de la app Streamlit como si fuera st.markdown. */
body{margin:0; background:#F6F7F9;}
.exec-dash{
  --navy:#16324F; --navy-soft:#3D5877; --ink:#22303F; --muted:#6B7684;
  --line:#E3E7EC; --bg:#F6F7F9; --card:#FFFFFF;
  --teal:#2E9E8F; --teal-bg:#E7F4F2; --amber:#E8A33D; --amber-bg:#FBF1E1;
  --coral:#D6564C; --grey:#8A95A1; --grey-bg:#EEF0F2;
  background:var(--bg); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;
  padding:24px; border-radius:12px;
}
.exec-dash *{box-sizing:border-box;}
.exec-dash .header{display:flex; justify-content:space-between; align-items:flex-end; gap:24px;
  padding-bottom:18px; border-bottom:1px solid var(--line); margin-bottom:24px;}
.exec-dash .header h1{margin:0 0 6px; font-size:24px; font-weight:700; color:var(--navy); letter-spacing:-0.01em;}
.exec-dash .header p{margin:0; font-size:13.5px; color:var(--muted);}
.exec-dash .period-tag{font-size:13px; color:var(--navy); background:var(--teal-bg);
  border:1px solid #cfe8e3; padding:6px 14px; border-radius:6px; font-weight:600; white-space:nowrap;}
.exec-dash .section-title{font-size:15px; font-weight:700; color:var(--navy); margin:0 0 12px;}
.exec-dash .grid-2{display:grid; grid-template-columns:1.3fr 1fr; gap:16px; margin-bottom:16px; align-items:stretch;}
.exec-dash .card{background:var(--card); border:1px solid var(--line); border-radius:10px; padding:20px 22px;}
.exec-dash .card-head{display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px;}
.exec-dash .card-head h3{margin:0; font-size:14.5px; font-weight:700; color:var(--ink);}
.exec-dash .card-head span{font-size:12px; color:var(--muted);}
.exec-dash .stat-strip{display:grid; grid-template-columns:repeat(4,1fr); gap:0;
  background:var(--grey-bg); border-radius:8px; margin-bottom:18px; overflow:hidden;}
.exec-dash .stat-strip .stat{padding:11px 14px; border-right:1px solid #E1E5E9;}
.exec-dash .stat-strip .stat:last-child{border-right:none;}
.exec-dash .stat-strip .stat .k{font-size:11px; color:var(--muted); font-weight:500; margin-bottom:3px;}
.exec-dash .stat-strip .stat .v{font-size:18px; font-weight:700; color:var(--navy); line-height:1.1;}
.exec-dash .stat-strip .stat .v small{font-size:11.5px; font-weight:500; color:var(--muted);}
.exec-dash table{width:100%; border-collapse:collapse; font-size:13px;}
.exec-dash thead th{text-align:left; font-weight:600; color:var(--muted); font-size:11.5px;
  padding:0 8px 8px; border-bottom:1px solid var(--line);}
.exec-dash thead th.num{text-align:right;}
.exec-dash tbody td{padding:7px 8px; border-bottom:1px solid #EEF1F3; vertical-align:middle;}
.exec-dash tbody td.num{text-align:right; color:var(--ink); font-variant-numeric:tabular-nums;}
.exec-dash tr.group td{padding-top:13px; font-weight:700; color:var(--navy-soft); font-size:11px; border-bottom:none;}
.exec-dash tr.group:first-child td{padding-top:2px;}
.exec-dash .bar-cell{display:flex; align-items:center; gap:8px; min-width:130px;}
.exec-dash .bar-track{flex:1; height:6px; background:var(--grey-bg); border-radius:4px; overflow:hidden;}
.exec-dash .bar-fill{height:100%; border-radius:4px;}
.exec-dash .pct{width:34px; text-align:right; font-weight:600; font-size:12.5px;}
.exec-dash .hbar-list{display:flex; flex-direction:column; gap:11px;}
.exec-dash .hbar-row{display:grid; grid-template-columns:76px 1fr 34px; align-items:center; gap:10px; font-size:12.5px;}
.exec-dash .hbar-row .name{color:var(--ink);}
.exec-dash .hbar-track{height:8px; background:var(--grey-bg); border-radius:4px; overflow:hidden; position:relative;}
.exec-dash .hbar-fill{height:100%; border-radius:4px;}
.exec-dash .hbar-row .pctv{text-align:right; font-weight:600;}
.exec-dash .gbar-chart{display:flex; justify-content:space-between; align-items:flex-end; height:110px; padding:0 4px; margin-bottom:10px;}
.exec-dash .gbar-cat{display:flex; flex-direction:column; align-items:center; gap:6px; flex:1;}
.exec-dash .gbar-bars{display:flex; align-items:flex-end; gap:3px; height:90px;}
.exec-dash .gbar-bars .bp{width:11px; background:#DCE2E8; border-radius:3px 3px 0 0;}
.exec-dash .gbar-bars .be{width:11px; background:var(--navy); border-radius:3px 3px 0 0;}
.exec-dash .gbar-cat .lbl{font-size:11px; color:var(--muted); text-align:center;}
.exec-dash .gbar-legend{display:flex; gap:16px; font-size:11.5px; color:var(--muted); justify-content:center;}
.exec-dash .gbar-legend span{display:inline-flex; align-items:center; gap:6px;}
.exec-dash .donut-row{display:flex; align-items:center; gap:14px;}
.exec-dash .donut{width:76px; height:76px; border-radius:50%; flex:none; position:relative;}
.exec-dash .donut::after{content:''; position:absolute; top:11px; left:11px; right:11px; bottom:11px;
  background:var(--card); border-radius:50%;}
.exec-dash .donut-legend{display:flex; flex-direction:column; gap:6px; font-size:12px; color:var(--muted);}
.exec-dash .donut-legend span{display:inline-flex; align-items:center; gap:7px;}
.exec-dash .dot{display:inline-block; width:7px; height:7px; border-radius:50%; flex:none;}
.exec-dash .section-divider{margin:6px 0 16px; padding-top:18px; border-top:1px solid var(--line);}
.exec-dash .section-divider .filter{font-size:12px; color:var(--muted); background:var(--grey-bg);
  display:inline-block; padding:3px 10px; border-radius:5px; margin-bottom:14px;}
.exec-dash .grid-3{display:grid; grid-template-columns:1fr 1fr 1.1fr; gap:16px;}
.exec-dash .stat-line{display:flex; justify-content:space-between; align-items:center;
  padding:9px 0; border-bottom:1px solid #EEF1F3; font-size:13px;}
.exec-dash .stat-line:last-child{border-bottom:none;}
.exec-dash .stat-line .k{color:var(--muted);}
.exec-dash .stat-line .v{font-weight:600; color:var(--ink);}
.exec-dash .code-list{display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;}
.exec-dash .code-chip{font-size:12px; font-weight:600; color:var(--navy); background:var(--teal-bg);
  border:1px solid #cfe8e3; padding:4px 10px; border-radius:5px;}
.exec-dash .empty-state{display:flex; align-items:center; justify-content:center; height:100%;
  min-height:100px; color:var(--muted); font-size:12.5px; text-align:center; padding:14px;
  background:var(--grey-bg); border-radius:8px;}
.exec-dash .foot-note{margin-top:10px; font-size:11.5px; color:var(--muted);}
.exec-dash .stat-strip.cols-2{grid-template-columns:repeat(2,1fr);}
.exec-dash .grid-2b{display:grid; grid-template-columns:1fr 1.6fr; gap:16px; margin-bottom:16px; align-items:start;}
.exec-dash tr.total-row td{font-weight:700; color:var(--navy); border-top:2px solid var(--line); border-bottom:none;}
.exec-dash .table-scroll{overflow-x:auto;}
.exec-dash .pivot-table{min-width:520px;}
.exec-dash .pivot-table th, .exec-dash .pivot-table td{text-align:right; white-space:nowrap;}
.exec-dash .pivot-table th:first-child, .exec-dash .pivot-table td:first-child{text-align:left;}
.exec-dash .pivot-table thead th{background:var(--grey-bg); border-bottom:1px solid var(--line);}
.exec-dash .pivot-table tbody tr:nth-child(even){background:#F7F9FA;}
@media (max-width:960px){
  .exec-dash .grid-2{grid-template-columns:1fr;}
  .exec-dash .grid-2b{grid-template-columns:1fr;}
  .exec-dash .grid-3{grid-template-columns:1fr;}
  .exec-dash .stat-strip{grid-template-columns:repeat(2,1fr);}
}
</style>
"""


def _esc(v):
    return _html.escape(str(v))


def _color_for_pct(pct):
    if pct >= 80:
        return TEAL
    if pct >= 50:
        return AMBER
    return CORAL


def _pct(ejec, plan):
    return round(100 * ejec / plan) if plan else 0


def _stat(label, value, sub=None):
    sub_html = f' <small>{_esc(sub)}</small>' if sub else ''
    return f'<div class="stat"><div class="k">{_esc(label)}</div><div class="v">{_esc(value)}{sub_html}</div></div>'


def _activity_row(name, ejec, plan):
    pct = _pct(ejec, plan)
    color = _color_for_pct(pct)
    return f"""<tr>
        <td>{_esc(name)}</td>
        <td class="num">{plan}</td>
        <td class="num">{ejec}</td>
        <td>
          <div class="bar-cell">
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%; background:{color};"></div></div>
            <div class="pct" style="color:{color};">{pct}%</div>
          </div>
        </td>
      </tr>"""


def _group_header(name):
    return f'<tr class="group"><td colspan="4">{_esc(name)}</td></tr>'


def _hbar_row(name, pct):
    color = _color_for_pct(pct)
    return f"""<div class="hbar-row">
      <div class="name">{_esc(name)}</div>
      <div class="hbar-track"><div class="hbar-fill" style="width:{pct}%; background:{color};"></div></div>
      <div class="pctv" style="color:{color};">{pct}%</div>
    </div>"""


def _gbar_cat(name, plan, ejec, max_v, max_px=90):
    hp = round((plan / max_v) * max_px) if max_v else 0
    he = round((ejec / max_v) * max_px) if max_v else 0
    return f"""<div class="gbar-cat">
      <div class="gbar-bars">
        <div class="bp" style="height:{hp}px;"></div>
        <div class="be" style="height:{he}px;"></div>
      </div>
      <div class="lbl">{_esc(name)}</div>
    </div>"""


def _donut(segments):
    """segments: list[(label, value, color)], value > 0. Devuelve el div
    donut (conic-gradient) + su leyenda, ya armados como HTML."""
    total = sum(v for _, v, _ in segments)
    if total <= 0:
        return '<div class="empty-state">Sin datos</div>'
    stops, acc = [], 0.0
    for _, v, color in segments:
        start = acc
        acc += 100 * v / total
        stops.append(f'{color} {start:.2f}% {acc:.2f}%')
    gradient = ', '.join(stops)
    legend_items = ''.join(
        f'<span><span class="dot" style="background:{color};"></span>{_esc(label)} — {round(100*v/total)}%</span>'
        for label, v, color in segments
    )
    return f"""<div class="donut-row">
      <div class="donut" style="background:conic-gradient({gradient});"></div>
      <div class="donut-legend">{legend_items}</div>
    </div>"""


def _focal_table(data):
    if not data:
        return '<div class="empty-state">Sin datos</div>'
    rows = ''.join(
        f"""<tr><td>{_esc(d['estado'])}</td>
        <td class="num">{d['cuenta_sed']}</td>
        <td class="num">{d['pct_sed']:.1f}%</td>
        <td class="num">{d['perdida_kwh']:,.0f}</td>
        <td class="num">{d['energia_rec_mes']:,.0f}</td></tr>"""
        for d in data
    )
    return f"""<div class="table-scroll"><table>
      <thead><tr><th>Estado focalización</th><th class="num">Cuenta SED</th>
      <th class="num">% SED</th><th class="num">Pérdida kWh</th><th class="num">Energía kWh/mes</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>"""


def _status_conteo_table(data, total):
    if not data:
        return '<div class="empty-state">Sin datos</div>'
    rows = ''.join(
        f"""<tr><td>{_esc(d['status'])}</td>
        <td class="num">{d['conteo']}</td>
        <td class="num">{d['perdida_kwh']:,.0f}</td>
        <td class="num">{d['energia_rec_mes']:,.0f}</td></tr>"""
        for d in data
    )
    total_row = f"""<tr class="total-row"><td>Total general</td>
      <td class="num">{total['conteo']}</td>
      <td class="num">{total['perdida_kwh']:,.0f}</td>
      <td class="num">{total['energia_rec_mes']:,.0f}</td></tr>"""
    return f"""<div class="table-scroll"><table>
      <thead><tr><th>Status conteo SED</th><th class="num">Conteo SED</th>
      <th class="num">Pérdida kWh</th><th class="num">Energía kWh/mes</th></tr></thead>
      <tbody>{rows}{total_row}</tbody>
    </table></div>"""


def _irreg_bt_table(data):
    """v1 'Analisis de irregularidades BT' (por SED/cliente): filas =
    ESTADO_CNR (limitado a NO PROCEDE/VALORIZADO en la query de origen),
    medidas = cuenta de SED_CLIENTE_MT (rename de presentacion de
    COD_PUNTO_MEDICION) y suma de RECUPERO_MWH."""
    if not data:
        return '<div class="empty-state">Sin datos</div>'
    rows = ''.join(
        f"""<tr><td>{_esc(d['estado_cnr'])}</td>
        <td class="num">{d['sed_cliente_mt']}</td>
        <td class="num">{d['recupero_mwh']:,.2f}</td></tr>"""
        for d in data
    )
    return f"""<div class="table-scroll"><table>
      <thead><tr><th>Estado CNR</th><th class="num">Cuenta SED/cliente MT</th>
      <th class="num">Recupero [MWh]</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>"""


def _irreg_alim_table(pivot):
    """v2 'Analisis de irregularidades BT' (por alimentador): filas =
    ALIMENTADOR, columnas = ESTADO_CNR (dinamicas -- todos los valores
    presentes en los datos, sin restringir a una lista fija), con Cuenta
    de SUM_CLIENTE y Suma de RECUPERO_MWH por estado, mas columnas de
    total y fila de total general."""
    if not pivot:
        return '<div class="empty-state">Sin datos</div>'
    estados = sorted({e for cells in pivot.values() for e in cells})
    alimentadores = sorted(pivot.keys())
    tot_conteo = {e: 0 for e in estados}
    tot_recup = {e: 0.0 for e in estados}
    rows_html = []
    for alim in alimentadores:
        cells = pivot[alim]
        conteos = [cells.get(e, {}).get('conteo', 0) for e in estados]
        recups = [cells.get(e, {}).get('recupero_mwh', 0.0) for e in estados]
        for e, c, r in zip(estados, conteos, recups):
            tot_conteo[e] += c
            tot_recup[e] += r
        tds = ''.join(f'<td class="num">{c}</td>' for c in conteos)
        tds += ''.join(f'<td class="num">{r:,.2f}</td>' for r in recups)
        tds += f'<td class="num">{sum(conteos)}</td><td class="num">{sum(recups):,.2f}</td>'
        rows_html.append(f'<tr><td>{_esc(alim)}</td>{tds}</tr>')

    gt_conteo = sum(tot_conteo.values())
    gt_recup = sum(tot_recup.values())
    total_tds = ''.join(f'<td class="num">{tot_conteo[e]}</td>' for e in estados)
    total_tds += ''.join(f'<td class="num">{tot_recup[e]:,.2f}</td>' for e in estados)
    total_tds += f'<td class="num">{gt_conteo}</td><td class="num">{gt_recup:,.2f}</td>'

    sub_conteo = ''.join(f'<th class="num">{_esc(e)}</th>' for e in estados)
    sub_recup = ''.join(f'<th class="num">{_esc(e)}</th>' for e in estados)

    return f"""<div class="table-scroll">
    <table class="pivot-table">
      <thead>
        <tr>
          <th rowspan="2" style="vertical-align:bottom;">Alimentador</th>
          <th colspan="{len(estados)}">Cuenta de SUM</th>
          <th colspan="{len(estados)}">Suma de RECUPERO [MWh]</th>
          <th rowspan="2" style="vertical-align:bottom;">Total cuenta SUM</th>
          <th rowspan="2" style="vertical-align:bottom;">Total recup. [MWh]</th>
        </tr>
        <tr>{sub_conteo}{sub_recup}</tr>
      </thead>
      <tbody>
        {''.join(rows_html)}
        <tr class="total-row"><td>Total general</td>{total_tds}</tr>
      </tbody>
    </table>
    </div>"""


def render_bt_segment(kbt, focal, status_data, status_total, irreg_bt, irreg_alim_pivot):
    """Segmento independiente "Análisis de alimentadores por nodos BT"
    (2.1-2.5 del pedido). No depende de nada calculado para el segmento MT;
    reutiliza unicamente clases CSS ya existentes en .exec-dash.

    kbt              : dict de core.db.get_dashboard_bt_kpis(meses)
    focal            : list de core.db.get_dashboard_bt_focalizacion(meses)
    status_data,
    status_total     : de core.db.get_dashboard_bt_status_conteo(meses)
    irreg_bt         : list de core.db.get_dashboard_irregularidades_bt(meses)
    irreg_alim_pivot : dict de core.db.get_dashboard_irregularidades_alimentador(meses)
    """
    stat_strip_bt = ''.join([
        _stat('Número de Nodos', kbt['nodos']),
        _stat('Número de SED', kbt['sed']),
    ])
    return f"""
  <div class="section-divider">
    <div class="section-title">Análisis de alimentadores por nodos BT</div>
    <div class="filter">Base de sospecha BT · análisis CSG = cerrado · actividad = asignado insp.</div>

    <div class="card" style="margin-bottom:16px;">
      <div class="stat-strip cols-2">{stat_strip_bt}</div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-head"><h3>Análisis por Estado de Focalización Nodo/SED</h3></div>
        {_focal_table(focal)}
      </div>
      <div class="card">
        <div class="card-head"><h3>Análisis por Status de Conteo SED</h3></div>
        {_status_conteo_table(status_data, status_total)}
      </div>
    </div>

    <div class="grid-2b">
      <div class="card">
        <div class="card-head"><h3>Análisis de irregularidades BT</h3><span>Tensión BT · CNR: no procede/valorizado</span></div>
        {_irreg_bt_table(irreg_bt)}
      </div>
      <div class="card">
        <div class="card-head"><h3>Análisis de irregularidades por alimentador</h3><span>Tipo cliente = SED</span></div>
        {_irreg_alim_table(irreg_alim_pivot)}
      </div>
    </div>
  </div>
"""


def estimate_bt_segment_height(focal, status_data, irreg_bt, irreg_alim_pivot):
    """Alto aproximado en px del segmento BT, para sumar al total del
    <iframe> (ver estimate_height)."""
    focal_h = 90 + max(1, len(focal)) * 30
    status_h = 90 + (max(1, len(status_data)) + 1) * 30  # +1 por fila de total
    row1_h = max(focal_h, status_h)

    irreg_bt_h = 90 + max(1, len(irreg_bt)) * 30
    n_alim = max(1, len(irreg_alim_pivot))
    irreg_alim_h = 110 + (n_alim + 1) * 30  # +1 por fila de total general
    row2_h = max(irreg_bt_h, irreg_alim_h)

    return 90 + row1_h + row2_h + 32


def estimate_height(k, alim_list, nodos_act, estados,
                     focal=None, status_data=None, irreg_bt=None, irreg_alim_pivot=None):
    """Alto aproximado en px para el <iframe> de components.html (que no
    se autoajusta al contenido). No hace falta que sea exacto: el iframe
    queda con scrolling=True como red de seguridad si el contenido real
    (mas alimentadores en la lista de chips, mas meses, etc.) termina
    siendo mas alto que esta estimacion.

    Los 4 parametros del segmento BT son opcionales: si se omiten (None),
    no se suma nada por ese segmento (compatibilidad con quien solo quiera
    el alto del segmento MT)."""
    n_rows = 8  # filas de actividad, fijas (no dependen de los datos)
    n_groups = 2
    activities_h = 140 + n_groups * 30 + n_rows * 32
    avance_h = 140 + 6 * 33
    top_row_h = max(activities_h, avance_h)

    mid_row_h = 300

    n_chip_lines = max(1, -(-len(alim_list) // 6))  # ceil
    n_estado_rows = max(1, len(estados))
    bottom_h = 200 + n_chip_lines * 28 + n_estado_rows * 26

    total = 110 + top_row_h + mid_row_h + bottom_h + 40

    if focal is not None:
        total += estimate_bt_segment_height(focal, status_data, irreg_bt, irreg_alim_pivot)

    return total


_ACTS = [
    ('Nodos', 'nodos'), ('Pinzado', 'pinzado'), ('Análisis', 'analisis'),
    ('Inspec.', 'inspecciones'), ('Lecturas', 'lecturas'), ('Inst.', 'inst_total'),
]


def render_dashboard(k, sed, clientes, nodos_act, alim_list, estados, period_label,
                      kbt=None, focal=None, status_data=None, status_total=None,
                      irreg_bt=None, irreg_alim_pivot=None):
    """
    k          : dict de core.db.get_dashboard_kpis(meses)
    sed        : dict de core.db.get_dashboard_sed_data(meses) -> {'imp','inst'}
    clientes   : int, core.db.get_dashboard_clientes_cerrado_con_imp(meses)
    nodos_act  : dict de core.db.get_dashboard_nodos_por_actividad(meses)
    alim_list  : list de core.db.get_dashboard_alimentadores_asignados_insp(meses)
    estados    : dict de core.db.get_dashboard_estados_nodos_insp(meses)
    period_label: str, p.ej. "Julio 2026" o "May 2026 — Sep 2026 (5 meses)"

    kbt, focal, status_data, status_total, irreg_bt, irreg_alim_pivot: datos
    del segmento independiente "Análisis de alimentadores por nodos BT" (ver
    render_bt_segment). Si se omiten (None), el segmento BT no se agrega —
    asi esta funcion sigue sirviendo tal cual para quien solo necesite el
    segmento MT.

    Devuelve el HTML completo (incluye <style>) listo para
    st.components.v1.html(html, height=..., scrolling=True).
    """
    p = k['planificado']
    sed_imp, sed_inst = sed.get('imp', 0), sed.get('inst', 0)
    cobertura = (1 - sed_imp / clientes) * 100 if clientes else None

    # ── tabla de actividades agrupadas ──────────────────────────────
    groups = [
        ('Actividades MT', [
            ('Selección de nodos', k['nodos']),
            ('Pinzado MT', k['pinzado']),
            ('Análisis de resultados CSG', k['analisis']),
        ]),
        ('Actividades BT / Totas', [
            ('Seguimiento inspecciones', k['inspecciones']),
            ('Lecturas', k['lecturas']),
            ('Instalación sin impedimentos', k['inst_cerrado']),
            ('Instalación con impedimentos', k['inst_con_imp']),
            ('Instalación (total)', k['inst_total']),
        ]),
    ]
    all_pcts = [_pct(ejec, p) for _, rows in groups for _, ejec in rows]
    avance_global = round(sum(all_pcts) / len(all_pcts)) if all_pcts else 0

    table_rows = ''.join(
        _group_header(gname) + ''.join(_activity_row(name, ejec, p) for name, ejec in rows)
        for gname, rows in groups
    )

    stat_strip = ''.join([
        _stat('Avance global', f'{avance_global}%'),
        _stat('Cobertura', f'{cobertura:.1f}%' if cobertura is not None else '—'),
        _stat('Clientes MT cerr. c/imp.', clientes),
        _stat('SED instalados', sed_inst),
    ])

    # ── avance por actividad (barras horizontales) ──────────────────
    hbars = ''.join(_hbar_row(label, _pct(k[key], p)) for label, key in _ACTS)

    # ── planificado vs ejecutado (barras css) ───────────────────────
    ejec_vals = [k[key] for _, key in _ACTS]
    max_v = max([p] + ejec_vals + [1])
    gbars = ''.join(_gbar_cat(label, p, k[key], max_v) for label, key in _ACTS)

    # ── donut estado de instalación ──────────────────────────────────
    pendiente = max(0, p - k['inst_cerrado'] - k['inst_con_imp'] - k['inst_en_curso'])
    inst_segments = [
        ('Cerrado', k['inst_cerrado'], TEAL),
        ('Cerrado c/imp.', k['inst_con_imp'], AMBER),
        ('En curso', k['inst_en_curso'], NAVY_SOFT),
        ('Pendiente', pendiente, GREY),
    ]
    inst_segments = [s for s in inst_segments if s[1] > 0]
    donut_instalacion = _donut(inst_segments)

    # ── donut nodos por actividad MT ─────────────────────────────────
    nodos_segments = [
        (label, val, DONUT_PALETTE[i % len(DONUT_PALETTE)])
        for i, (label, val) in enumerate(nodos_act.items()) if val > 0
    ]
    donut_nodos = _donut(nodos_segments)
    total_nodos = sum(nodos_act.values())

    # ── alimentadores asignados a inspección ─────────────────────────
    chips = ''.join(f'<span class="code-chip">{_esc(a)}</span>' for a in alim_list) or \
        '<span style="color:var(--muted); font-size:12.5px;">(ninguno)</span>'

    # ── estados de los nodos ──────────────────────────────────────────
    total_estados = sum(estados.values())
    pct_estados = round(100 * total_estados / p) if p else 0
    if estados:
        estados_rows = ''.join(
            f'<tr><td>{_esc(e)}</td><td class="num">{c}</td></tr>'
            for e, c in sorted(estados.items(), key=lambda x: -x[1])
        )
        estados_table = f"""<table>
          <thead><tr><th>Estado inspección</th><th class="num">Q nodos</th></tr></thead>
          <tbody>{estados_rows}</tbody>
        </table>
        <div class="foot-note">Total de nodos asignados a inspección: {total_estados} ({pct_estados}% de {p}).</div>"""
    else:
        estados_table = '<div class="empty-state">Sin datos</div>'

    bt_segment_html = ''
    if kbt is not None:
        bt_segment_html = render_bt_segment(
            kbt, focal, status_data, status_total, irreg_bt, irreg_alim_pivot)

    html = CSS + f"""
<div class="exec-dash">
  <div class="header">
    <div>
      <h1>Panel de seguimiento — Actividades MT / BT</h1>
      <p>Instalación de nodos, pinzado, lecturas e inspecciones. Reporte generado a partir de la base de sospecha MT.</p>
    </div>
    <div class="period-tag">{_esc(period_label)}</div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-head"><h3>Actividades MT y BT</h3><span>Plan. vs. ejecutado</span></div>
      <div class="stat-strip">{stat_strip}</div>
      <table>
        <thead><tr><th>Actividad</th><th class="num">Plan.</th><th class="num">Ejec.</th>
          <th style="text-align:left; padding-left:14px;">% Avance</th></tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-head"><h3>Avance por actividad</h3><span>Meta: 100%</span></div>
      <div class="hbar-list">{hbars}</div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-head"><h3>Planificado vs. ejecutado</h3><span>Unidades</span></div>
      <div class="gbar-chart">{gbars}</div>
      <div class="gbar-legend">
        <span><span class="dot" style="background:#DCE2E8;"></span>Planificado</span>
        <span><span class="dot" style="background:var(--navy);"></span>Ejecutado</span>
      </div>
    </div>

    <div class="card">
      <div class="card-head"><h3>Estado de instalación</h3><span>Total {p} alimentadores</span></div>
      {donut_instalacion}
    </div>
  </div>

  <div class="section-divider">
    <div class="section-title">Análisis de alimentadores por nodos MT</div>
    <div class="filter">Base de sospecha MT · estado análisis CSG = cerrado</div>

    <div class="grid-3">
      <div class="card">
        <div class="card-head"><h3>Nodos por actividad MT</h3><span>Total: {total_nodos}</span></div>
        {donut_nodos}
      </div>

      <div class="card">
        <div class="card-head"><h3>Alimentadores a inspección</h3><span>Asignado insp. MT</span></div>
        <div class="stat-line"><span class="k">Alimentadores asignados</span><span class="v">{len(alim_list)}</span></div>
        <div class="code-list">{chips}</div>
      </div>

      <div class="card">
        <div class="card-head"><h3>Estados de los nodos</h3><span>Asignado insp. MT</span></div>
        {estados_table}
      </div>
    </div>
  </div>
  {bt_segment_html}
</div>
"""
    return html
