"""
dashboard_charts.py — Builders Plotly para el Dashboard, portados de
TabDashboard en app/main.py (matplotlib embebido -> Plotly).

Las queries (core/db.get_dashboard_*) son EXACTAMENTE las mismas que usaba
la app de escritorio -- ver Fase 2 del plan de migracion. Solo cambia la
capa de graficos: Plotly es responsive por defecto (use_container_width),
asi que no hace falta la logica de _chart_width_in/_on_resize que existia
en Tkinter para recalcular el ancho en pixeles a mano.
"""
import pandas as pd
import plotly.graph_objects as go

MESES = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
         7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}


def fmt_mes(db_val):
    try:
        y, m = int(db_val[:4]), int(db_val[5:7])
        return f'{MESES.get(m, m)} {y}'
    except Exception:
        return str(db_val)


def label_meses(meses_db):
    labels = [fmt_mes(m) for m in meses_db]
    if not labels:
        return '(ninguno)'
    if len(labels) <= 2:
        return ', '.join(labels)
    return f'{labels[0]} — {labels[-1]} ({len(labels)} meses)'


def kpi_table_df(k):
    """Misma tabla que _fill_kpi en main.py: filas de encabezado
    (ACTIVIDADES MT / ACTIVIDADES BT-TOTAS) intercaladas con filas de dato,
    todas en una sola columna 'Actividad' -- las de encabezado quedan con
    Ejec./% Avance en blanco (None), igual que en la version Tkinter."""
    p = k['planificado']
    rows = []

    def hdr(txt):
        rows.append({'Actividad': txt, 'Plan.': p, 'Ejec.': None, '% Avance': None})

    def row(txt, ej, pl=None):
        pl = p if pl is None else pl
        pct = None if not pl else round(100 * ej / pl, 1)
        rows.append({'Actividad': f'   {txt}', 'Plan.': pl, 'Ejec.': ej, '% Avance': pct})

    hdr('ACTIVIDADES MT')
    row('Selección de nodos', k['nodos'])
    row('Pinzado MT', k['pinzado'])
    row('Análisis de resultados CSG', k['analisis'])
    hdr('ACTIVIDADES BT / TOTAS')
    row('Seguimiento Inspecciones', k['inspecciones'])
    row('Lecturas', k['lecturas'])
    row('Instalación sin impedimentos', k['inst_cerrado'])
    row('Instalación con impedimentos', k['inst_con_imp'])
    row('Instalación (total)', k['inst_total'])
    return pd.DataFrame(rows)


_ACTS = ['Nodos', 'Pinzado', 'Análisis', 'Inspec.', 'Lecturas', 'Inst.']
_COLS6 = ['#89b4fa', '#cba6f7', '#f38ba8', '#fab387', '#a6e3a1', '#94e2d5']


def _ejec_list(k):
    return [k['nodos'], k['pinzado'], k['analisis'],
            k['inspecciones'], k['lecturas'], k['inst_total']]


def fig_avance_pct(k, mes_label):
    p = max(k['planificado'], 1)
    ejec = _ejec_list(k)
    pcts = [100 * e / p for e in ejec]
    fig = go.Figure(go.Bar(
        x=pcts, y=_ACTS, orientation='h', marker_color=_COLS6,
        text=[f'{v:.0f}%' for v in pcts], textposition='outside',
    ))
    fig.add_vline(x=100, line_dash='dash', line_color='#f38ba8')
    fig.update_layout(
        title=f'Avance (%) — {mes_label}', xaxis_range=[0, 120],
        xaxis_title='% Avance', height=320, margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def fig_planificado_vs_ejecutado(k):
    p = k['planificado']
    ejec = _ejec_list(k)
    fig = go.Figure([
        go.Bar(name='Planificado', x=_ACTS, y=[p] * len(_ACTS), marker_color='#b4befe'),
        go.Bar(name='Ejecutado', x=_ACTS, y=ejec, marker_color='#89b4fa'),
    ])
    fig.update_layout(
        title='Planificado vs Ejecutado', barmode='group', height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation='h', yanchor='bottom', y=-0.3, xanchor='center', x=0.5),
    )
    return fig


def fig_estado_instalacion(k):
    p = k['planificado']
    pendiente = max(0, p - k['inst_cerrado'] - k['inst_con_imp'] - k['inst_en_curso'])
    labels = ['Cerrado', 'Cerrado c/imp.', 'En curso', 'Pendiente']
    values = [k['inst_cerrado'], k['inst_con_imp'], k['inst_en_curso'], pendiente]
    colors = ['#a6e3a1', '#94e2d5', '#89b4fa', '#b4befe']
    nz = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if not nz:
        fig = go.Figure()
        fig.add_annotation(text='Sin datos', showarrow=False)
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        return fig
    ls, vs, cs = zip(*nz)
    fig = go.Figure(go.Pie(labels=ls, values=vs, marker_colors=cs, hole=0.0))
    fig.update_layout(title='Estado de Instalación', height=320,
                       margin=dict(l=10, r=10, t=40, b=10))
    return fig


def fig_nodos_por_actividad(nodos_act):
    if not nodos_act:
        fig = go.Figure()
        fig.add_annotation(text='Sin datos para el filtro seleccionado', showarrow=False)
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        return fig
    labels = list(nodos_act.keys())
    values = list(nodos_act.values())
    pal = ['#89b4fa', '#f38ba8', '#a6e3a1', '#cba6f7', '#fab387', '#94e2d5', '#eba0ac']
    colors = [pal[i % len(pal)] for i in range(len(labels))]
    fig = go.Figure(go.Pie(labels=labels, values=values, marker_colors=colors))
    fig.update_layout(title=f'Nodos por Actividad MT (total: {sum(values)})',
                       height=320, margin=dict(l=10, r=10, t=40, b=10))
    return fig
