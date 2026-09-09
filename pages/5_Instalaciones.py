"""Pagina Inst. Totas — portada de TabInstalaciones en app/main.py."""
import streamlit as st
import core.auth as auth
import core.db as db
from core.grid import col, key, ro, cb, render_grid_page

auth.require_login()
auth.require_pagina('instalaciones')

with st.sidebar:
    st.write(f"**{st.session_state.get('nombre')}**")
    st.caption(f"Rol: {st.session_state.get('rol')}")
    auth.logout_button()

st.title('BD Instalación Totas')

COLS = [
    key('COD_PUNTO_MEDICION', 'COD PUNTO MED.'),
    cb ('TIPO_CONSTRUCCION',  'TIPO CONST.', 'TIPO_CONST'),
    ro ('ESTADO_CONTROL',     'CONTROL'),
    col('ZONA',               'ZONA'),
    key('ALIMENTADOR',        'ALIMENTADOR'),
    col('PRIORIDAD',          'PRIORIDAD', 'int'),
    col('MES_PLANIFICADO',    'MES PLANIF.', 'date'),
    col('PLAZO_FINAL',        'PLAZO FINAL', 'date'),
    col('COD_TRAFO',          'COD TRAFO'),
    col('MEDIDOR_SB',         'MEDIDOR SB'),
    col('MARCA',              'MARCA'),
    cb ('TIPO_FINAL',         'TIPO FINAL', 'TIPO_FINAL'),
    col('SUBESTADO',          'SUBESTADO'),
    cb ('ESTADO_INSTALACION', 'INSTALACION', 'ESTADO_INST'),
    col('FECHA_INTERVENCION', 'FECHA INTERV.', 'date'),
    col('MOTIVO_UNIFICADO',   'MOTIVO UNIF.'),
    col('DETALLE_CAMPO',      'DETALLE CAMPO'),
    cb ('ESTADO_REGISTRO',    'ESTADO', 'ESTADO_REG'),
    ro ('CREADO_POR',         'CREADO POR'),
    ro ('FECHA_CREACION',     'FECHA CREAC.'),
    ro ('MODIFICADO_POR',     'MODIF. POR'),
    ro ('FECHA_MODIFICACION', 'FECHA MODIF.'),
]


def _query(search):
    return db.get_instalaciones_all(search.get('ALIMENTADOR', ''))


render_grid_page(
    title='BD INSTALACION TOTAS',
    key_cols=['ALIMENTADOR', 'COD_PUNTO_MEDICION'],
    cols=COLS,
    query_fn=_query,
    pagina_id='instalaciones',
    search_fields=[('ALIMENTADOR', 'Alimentador')],
)
