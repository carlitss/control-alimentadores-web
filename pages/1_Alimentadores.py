"""
Pagina Alimentadores — portada de TabAlimentadores en app/main.py.
Mismo orden y mismas 39 columnas que la app de escritorio (ver
CONTROL ALIMENTADORES MT.xlsx / auditoria de migracion).
"""
import streamlit as st
import core.auth as auth
import core.db as db
from core.grid import col, key, ro, cb, render_grid_page

st.set_page_config(page_title='Alimentadores — Control Alimentadores MT', layout='wide')
auth.require_login()

with st.sidebar:
    st.write(f"**{st.session_state.get('nombre')}**")
    st.caption(f"Rol: {st.session_state.get('rol')}")
    auth.logout_button()

st.title('BD Alimentadores')

COLS = [
    key('ALIMENTADOR',            'ALIMENTADOR'),
    col('SUBESTACION',            'SUBESTACION'),
    col('MES_PLANIFICADO',        'MES PLANIF.', 'date'),
    col('ORDEN_ATENCION',         'ORDEN', 'int'),
    col('PLANO_NODOS',            'PLANO NODOS'),
    ro ('TOTAL_EFECTIVOS_LECTURA','EFECT LEC'),
    ro ('TOTAL_LECTURAS_RECOGER', 'TOT LECT'),
    ro ('ESTADO_LECTURAS',        'LECTURAS'),
    ro ('TOTAL_ASIGNADOS_TOTA',   'ASIG TOTAS'),
    ro ('TOTAL_IMP_TOTA',         'IMP TOTAS'),
    ro ('TOTAL_INSTALADOS_TOTA',  'INST TOTAS (cant.)'),
    ro ('TOTAL_CASOS_INST_TOTA',  'CASOS INST TOTA'),
    ro ('ESTADO_INST_TOTAS',      'INST TOTAS (estado)'),
    cb ('ESTADO_ANALISIS_CSG',    'ANALISIS CSG', 'ESTADO_ANALISIS'),
    cb ('ESTADO_TRABAJO_MT',      'TRABAJO MT', 'ESTADO_TRABAJO'),
    cb ('ESTADO_TRABAJO_BT',      'TRABAJO BT', 'ESTADO_TRABAJO'),
    col('TIPO_ALIMENTADOR',       'TIPO'),
    col('A_LOSS',                 'A-LOSS', 'float'),
    col('PERDIDA_MT_REF',         'PERD MT REF', 'float'),
    col('PERDIDA_COMERCIAL_PROM', 'PERD COM PROM', 'float'),
    cb ('DENSIDAD',               'DENSIDAD', 'DENSIDAD'),
    col('N_SEDS',                 'N SEDS', 'int'),
    col('N_TOTAS',                'N TOTAS', 'int'),
    col('TOTAS_PENDIENTES',       'TOTAS PEND.', 'int'),
    col('CLIENTES_MAX_MT',        'CLIENTES MT', 'int'),
    col('CLIENTES_LIB_PEAJES',    'LIB/PEAJES', 'int'),
    col('CLIENTES_NO_UBI',        'NO UBIC.', 'int'),
    ro ('TOTAL_CLIENTES_MT',      'TOTAL CLIENTES MT'),
    cb ('SELECCION_PLUZ',         'SELECCION', 'SELECCION'),
    cb ('ESTADO_PINZADO',         'PINZADO', 'ESTADO_PINZADO'),
    col('FECHA_INICIO_PINZADO',   'INI PINZADO', 'date'),
    col('FECHA_FIN_PINZADO',      'FIN PINZADO', 'date'),
    ro ('NODOS_SOSPECHOSOS',      'NODOS SOSP.'),
    ro ('TOTAL_IRREGULARIDADES',  'IRREGUL.'),
    cb ('ESTADO_REGISTRO',        'ESTADO', 'ESTADO_REG'),
    ro ('CREADO_POR',             'CREADO POR'),
    ro ('FECHA_CREACION',         'FECHA CREAC.'),
    ro ('MODIFICADO_POR',         'MODIF. POR'),
    ro ('FECHA_MODIFICACION',     'FECHA MODIF.'),
]


def _query(search):
    return db.buscar_alimentadores(search.get('ALIMENTADOR', ''))


render_grid_page(
    title='BD ALIMENTADORES',
    key_cols=['ALIMENTADOR'],
    cols=COLS,
    query_fn=_query,
    search_fields=[('ALIMENTADOR', 'Alimentador')],
)
