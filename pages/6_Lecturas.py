"""Pagina Lecturas — portada de TabLecturas en app/main.py.
Unica pestana con clave compuesta de 3 columnas (ALIMENTADOR + COD_PUNTO_
MEDICION + PERIODO) y auto-relleno cruzado desde INSTALACIONES_TOTAS
(TIPO/COD_TRAFO/MEDIDOR_SB/MARCA los pisa prepare_row igual que en la app
de escritorio, via CONFIGS['LECTURAS']['auto_inst']=True)."""
import streamlit as st
import core.auth as auth
import core.db as db
from core.grid import col, key, ro, cb, render_grid_page

auth.require_login()
auth.require_pagina('lecturas')

with st.sidebar:
    st.write(f"**{st.session_state.get('nombre')}**")
    st.caption(f"Rol: {st.session_state.get('rol')}")
    auth.logout_button()

st.title('BD Lecturas')

COLS = [
    key('COD_PUNTO_MEDICION', 'COD PUNTO MED.'),
    key('ALIMENTADOR',        'ALIMENTADOR'),
    key('PERIODO',            'PERIODO', 'date'),
    col('COD_TRAFO',          'COD TRAFO'),
    col('MEDIDOR_SB',         'MEDIDOR SB'),
    col('MARCA',              'MARCA'),
    col('TIPO',               'TIPO'),
    cb ('ESTADO_LECTURA',     'ESTADO LECTURA', 'ESTADO_LECTURA'),
    col('FECHA_EXTRACCION',   'FECHA EXTRAC.', 'date'),
    col('MOTIVO_UNIFICADO',   'MOTIVO UNIF.'),
    col('DETALLE_CAMPO',      'DETALLE CAMPO'),
    col('EECC',               'EECC'),
    cb ('ESTADO_REGISTRO',    'ESTADO', 'ESTADO_REG'),
    ro ('CREADO_POR',         'CREADO POR'),
    ro ('FECHA_CREACION',     'FECHA CREAC.'),
    ro ('MODIFICADO_POR',     'MODIF. POR'),
    ro ('FECHA_MODIFICACION', 'FECHA MODIF.'),
]


def _query(search):
    return db.get_lecturas_all(search.get('ALIMENTADOR', ''))


render_grid_page(
    title='BD LECTURAS',
    key_cols=['ALIMENTADOR', 'COD_PUNTO_MEDICION', 'PERIODO'],
    cols=COLS,
    query_fn=_query,
    pagina_id='lecturas',
    search_fields=[('ALIMENTADOR', 'Alimentador')],
)
