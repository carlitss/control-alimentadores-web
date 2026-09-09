"""Pagina Irregularidades — portada de TabIrregularidades en app/main.py.
Clave real (KEY, ex CONCA) no coincide con ambas columnas 'key' mostradas
(ALIMENTADOR tambien se marca key por consistencia visual con la app de
escritorio, pero insert_engine.CONFIGS['IRREGULARIDADES']['key_cols'] es
solo ['KEY'])."""
import streamlit as st
import core.auth as auth
import core.db as db
from core.grid import col, key, ro, cb, render_grid_page

auth.require_login()
auth.require_pagina('irregularidades')

with st.sidebar:
    st.write(f"**{st.session_state.get('nombre')}**")
    st.caption(f"Rol: {st.session_state.get('rol')}")
    auth.logout_button()

st.title('BD Irregularidades')

COLS = [
    key('ALIMENTADOR',         'ALIMENTADOR'),
    col('NODO',                'NODO', 'int'),
    key('KEY',                 'KEY'),
    col('SUM_CLIENTE',         'SUM', 'int'),
    col('CONDICION_CLIENTE',   'CONDICION'),
    col('FECHA_NORMALIZACION', 'FECHA NORMAL.', 'date'),
    col('FECHA_ASIG_INSP',     'FECHA ASIG INSP.', 'date'),
    ro ('DIAS_CIERRE',         'DIAS CIERRE'),
    col('COD_PUNTO_MEDICION',  'COD PUNTO MED.'),
    cb ('ESTADO_FOCALIZACION', 'FOCALIZACION', 'ESTADO_FOCAL'),
    cb ('TENSION',             'TENSION', 'TENSION'),
    col('TIPO_CLIENTE',        'TIPO CLIENTE'),
    col('RECUPERO_MWH',        'RECUP MWh', 'float'),
    col('MESES_CNR',           'MESES CNR', 'float'),
    ro ('RECUPERO_MWH_MES',    'RECUP/MES'),
    cb ('ESTADO_CNR',          'ESTADO CNR', 'ESTADO_CNR'),
    cb ('CATEGORIA',           'CATEGORIA', 'CATEGORIA'),
    cb ('TIPO_HURTO',          'TIPO HURTO', 'TIPO_HURTO'),
    col('MOTIVO_RECHAZO',      'MOT. RECHAZO'),
    col('OBSERVACIONES',       'OBSERVACIONES'),
    col('IMPACTO_ANO_MWH',     'IMPACTO MWh/A', 'float'),
    cb ('ESTADO_REGISTRO',     'ESTADO', 'ESTADO_REG'),
    ro ('CREADO_POR',          'CREADO POR'),
    ro ('FECHA_CREACION',      'FECHA CREAC.'),
    ro ('MODIFICADO_POR',      'MODIF. POR'),
    ro ('FECHA_MODIFICACION',  'FECHA MODIF.'),
]


def _query(search):
    return db.get_irregularidades_all(search.get('ALIMENTADOR', ''))


render_grid_page(
    title='BD IRREGULARIDADES',
    key_cols=['KEY'],
    cols=COLS,
    query_fn=_query,
    pagina_id='irregularidades',
    search_fields=[('ALIMENTADOR', 'Alimentador')],
)
