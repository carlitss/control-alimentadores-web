"""
Pagina Dashboard — portada de TabDashboard en app/main.py (Fase 6), con la
capa visual rediseñada segun el diseño ejecutivo entregado por el usuario
(HTML/CSS puro, sin Plotly/Chart.js/canvas) -- ver core/dashboard_html.py.

Extraida de streamlit_app.py (que ahora es solo el entrypoint de login +
navegacion filtrada por permisos) para poder ser una pagina mas de
core.auth.PAGINAS, gateada igual que el resto.

Las queries (core/db.get_dashboard_*) son las mismas que en la app de
escritorio, sin cambios; solo cambio la presentacion.
"""
import streamlit as st
import streamlit.components.v1 as components
import core.auth as auth
import core.db as db
import core.dashboard_charts as dc
import core.dashboard_html as dh

auth.require_login()
auth.require_pagina('dashboard')

with st.sidebar:
    st.write(f"**{st.session_state.get('nombre')}**")
    st.caption(f"Rol: {st.session_state.get('rol')}")
    auth.logout_button()

meses_db = db.get_dashboard_meses()
if not meses_db:
    st.title('Control Alimentadores MT')
    st.warning('No hay datos de ALIMENTADORES con MES_PLANIFICADO para mostrar en el Dashboard.')
    st.stop()

opciones = {m: dc.fmt_mes(m) for m in meses_db}
meses_sel = st.multiselect(
    'Meses', options=list(opciones.keys()), default=list(opciones.keys()),
    format_func=lambda m: opciones[m],
)
if not meses_sel:
    st.info('Seleccione al menos un mes.')
    st.stop()

k = db.get_dashboard_kpis(meses_sel)
sed = db.get_dashboard_sed_data(meses_sel)
clientes = db.get_dashboard_clientes_cerrado_con_imp(meses_sel)
nodos_act = db.get_dashboard_nodos_por_actividad(meses_sel)
alim_list = db.get_dashboard_alimentadores_asignados_insp(meses_sel)
estados = db.get_dashboard_estados_nodos_insp(meses_sel)

# Segmento independiente "Analisis de alimentadores por nodos BT": mismo
# filtro global de meses (meses_sel), pero sin ninguna dependencia de los
# datos MT de arriba.
kbt = db.get_dashboard_bt_kpis(meses_sel)
focal = db.get_dashboard_bt_focalizacion(meses_sel)
status_data, status_total = db.get_dashboard_bt_status_conteo(meses_sel)
irreg_bt = db.get_dashboard_irregularidades_bt(meses_sel)
irreg_alim_pivot = db.get_dashboard_irregularidades_alimentador(meses_sel)

html = dh.render_dashboard(
    k, sed, clientes, nodos_act, alim_list, estados,
    period_label=dc.label_meses(meses_sel),
    kbt=kbt, focal=focal, status_data=status_data, status_total=status_total,
    irreg_bt=irreg_bt, irreg_alim_pivot=irreg_alim_pivot,
)
# components.html renderiza en un <iframe> aislado -- a diferencia de
# st.markdown, no pasa el contenido por el parser de Markdown (que rompe
# bloques de HTML muy anidados, mostrando parte como texto crudo en vez
# de renderizarlo). El alto es fijo (el iframe no se autoajusta al
# contenido), con scroll de respaldo por si la altura real varia con los
# datos (mas filas de actividades, mas alimentadores, etc.).
altura = dh.estimate_height(
    k, alim_list, nodos_act, estados,
    focal=focal, status_data=status_data, irreg_bt=irreg_bt, irreg_alim_pivot=irreg_alim_pivot,
)
components.html(html, height=altura, scrolling=True)
