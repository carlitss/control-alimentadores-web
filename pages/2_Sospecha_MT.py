"""Pagina Sospecha MT — portada de TabSospechaMT en app/main.py."""
import streamlit as st
import core.auth as auth
import core.db as db
from core.grid import col, key, ro, cb, render_grid_page

auth.require_login()
auth.require_pagina('sospecha_mt')

with st.sidebar:
    st.write(f"**{st.session_state.get('nombre')}**")
    st.caption(f"Rol: {st.session_state.get('rol')}")
    auth.logout_button()

st.title('BD Sospecha MT')

COLS = [
    ro ('PERIODO_PLANIF',    'PERIODO PLANIF.'),
    key('ALIMENTADOR',       'ALIMENTADOR'),
    key('NODO',              'NODO', 'int'),
    col('CORRIENTE_A',       'CORRIENTE (A)', 'float'),
    col('FECHA_CARGA',       'FECHA CARGA', 'date'),
    col('OBVS_ANALISIS',     'OBS ANALISIS'),
    cb ('ESTADO_ACTIVIDAD',  'ACTIVIDAD', 'ESTADO_ACTIVIDAD_MT'),
    cb ('ESTADO_RE',         'ESTADO RE', 'ESTADO_RE'),
    cb ('ESTADO_INSP',       'ESTADO INSP.', 'ESTADO_FOCAL'),
    col('OBSERVACION',       'OBSERVACION'),
    cb ('ESTADO_REGISTRO',   'ESTADO', 'ESTADO_REG'),
    ro ('CREADO_POR',        'CREADO POR'),
    ro ('FECHA_CREACION',    'FECHA CREAC.'),
    ro ('MODIFICADO_POR',    'MODIF. POR'),
    ro ('FECHA_MODIFICACION','FECHA MODIF.'),
]


def _query(search):
    return db.get_sospechas_mt_all(search.get('ALIMENTADOR', ''))


render_grid_page(
    title='BD SOSPECHA MT',
    key_cols=['ALIMENTADOR', 'NODO'],
    cols=COLS,
    query_fn=_query,
    pagina_id='sospecha_mt',
    search_fields=[('ALIMENTADOR', 'Alimentador')],
)
