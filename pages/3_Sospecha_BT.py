"""
Pagina Sospecha BT — portada de TabSospechaBT en app/main.py.
Unica pestana con busqueda compuesta (Alimentador + SED opcional).
"""
import streamlit as st
import core.auth as auth
import core.db as db
from core.grid import col, key, ro, cb, render_grid_page

auth.require_login()
auth.require_pagina('sospecha_bt')

with st.sidebar:
    st.write(f"**{st.session_state.get('nombre')}**")
    st.caption(f"Rol: {st.session_state.get('rol')}")
    auth.logout_button()

st.title('BD Sospecha BT')

COLS = [
    col('FECHA_ASIGNACION',    'FECHA ASIG.', 'date'),
    ro ('PERIODO_PLANIF',      'PERIODO PLANIF.'),
    cb ('ESTADO_ANALISIS_CSG', 'ANALISIS CSG', 'ESTADO_ANALISIS'),
    ro ('ESTADO_RE',           'ESTADO RE'),
    key('SED',                 'SED'),
    key('ALIMENTADOR',         'ALIMENTADOR'),
    key('NODO',                'NODO', 'int'),
    col('MEDIDOR_TOTALIZADOR', 'MEDIDOR TOT.'),
    col('CONSUMO_TOTALIZADOR', 'CONS TOT.', 'float'),
    col('CONSUMO_CLIENTES',    'CONS CLIENTES', 'float'),
    ro ('PERDIDA_KWH',         'PERD kWh'),
    ro ('PERDIDA_PCT',         'PERD %'),
    ro ('RIESGO',              'RIESGO'),
    cb ('ESTADO_ACTIVIDAD',    'ACTIVIDAD', 'ESTADO_ACTIVIDAD_BT'),
    col('RESPONSABLE_INSP',    'RESPONSABLE'),
    cb ('ESTADO_FOCALIZACION', 'FOCALIZACION', 'ESTADO_FOCAL'),
    cb ('STATUS_CONTEO_SED',   'STATUS CONTEO SED', 'STATUS_CONTEO_SED'),
    col('ENERGIA_KWH_REC_MES', 'ENERGIA kWh REC/MES', 'float'),
    col('OBSERVACIONES',       'OBSERVACIONES'),
    col('RESUMEN_HURTO',       'RESUMEN HURTO'),
    cb ('ESTADO_REGISTRO',     'ESTADO', 'ESTADO_REG'),
    ro ('CREADO_POR',          'CREADO POR'),
    ro ('FECHA_CREACION',      'FECHA CREAC.'),
    ro ('MODIFICADO_POR',      'MODIF. POR'),
    ro ('FECHA_MODIFICACION',  'FECHA MODIF.'),
]


def _query(search):
    sed = search.get('SED') or None
    return db.get_sospechas_bt_filtradas(search.get('ALIMENTADOR', ''), sed)


render_grid_page(
    title='BD SOSPECHA BT',
    key_cols=['ALIMENTADOR', 'NODO', 'SED'],
    cols=COLS,
    query_fn=_query,
    pagina_id='sospecha_bt',
    search_fields=[('ALIMENTADOR', 'Alimentador'), ('SED', 'SED (opcional)')],
)
