"""
grid.py — Helper de grilla compartido por las 6 paginas de datos.

Reemplaza a GridTab (main.py, Tkinter): mismo concepto de columnas
(col/key/ro/cb) y mismo flujo (consultar -> editar -> guardar), pero
sobre st.data_editor en vez de un ttk.Treeview. Pegado (Ctrl+V nativo del
navegador) y edicion manual quedan UNIFICADOS: ambos terminan como un
diff de st.data_editor que se resuelve en un solo llamado a
ie.bulk_upsert al presionar "Guardar cambios" (antes, pegar escribia a
la base al instante; ver plan de migracion, Fase 4, punto 5 -- cambio de
comportamiento ya confirmado con el usuario).

Limitacion conocida y aceptada (ver plan, Fase 4 punto 6): el pegado
nativo de st.data_editor matchea por POSICION de columna, no detecta un
encabezado pegado para reordenar por nombre como hacia _match_header en
la app de escritorio. Si el usuario pega un rango con columnas en otro
orden, "Cargar desde Excel" sigue matcheando por nombre sin este problema
-- esa es la via recomendada para pegados con columnas reordenadas.
"""
from collections import namedtuple
from datetime import datetime, date
import io

import pandas as pd
import streamlit as st

import core.db as db
import core.insert_engine as ie
import core.auth as auth

GCol = namedtuple('GCol', ['name', 'label', 'ftype', 'opts'])


def col(name, label, ftype='text'):
    return GCol(name, label, ftype, None)


def key(name, label, ftype='text'):
    """Columna clave: mismo GCol que col(), simplemente documenta la
    intencion (ver nota en _column_config sobre por que no se marca
    disabled). Acepta ftype igual que col() -- p.ej. NODO es 'int',
    PERIODO es 'date' -- para que la columna se vea/edite con el widget
    correcto aunque sea parte de la clave."""
    return GCol(name, label, ftype, None)


def ro(name, label):
    return GCol(name, label, 'ro', None)


def cb(name, label, opts_key):
    return GCol(name, label, 'combo', opts_key)


def _clean_val(v):
    """NaN/NaT de pandas -> None (bulk_upsert/prepare_row esperan None,
    no NaN, para 'valor vacio')."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _column_config(cols):
    """
    OJO con las columnas 'key': se probo marcarlas disabled=True (para
    imitar que en la app de escritorio solo se pueden tipear en una fila
    NUEVA, nunca en una existente) y result que st.data_editor bloquea
    la escritura tambien en filas recien agregadas -- no hay forma de
    deshabilitar una columna solo para filas existentes en este
    componente. Por eso quedan editables siempre; es seguro porque
    bulk_upsert ya ignora el valor de las columnas clave al hacer UPDATE
    de una fila existente (solo las usa para buscarla, nunca las escribe)
    -- ver Fase 4 del plan de migracion.
    """
    cfg = {}
    for c in cols:
        if c.ftype == 'ro':
            cfg[c.name] = st.column_config.TextColumn(c.label, disabled=True)
        elif c.ftype == 'combo':
            opciones = list(ie.CATALOGOS.get(c.opts, []))
            if '' not in opciones:
                opciones = [''] + opciones
            cfg[c.name] = st.column_config.SelectboxColumn(c.label, options=opciones)
        elif c.ftype == 'date':
            cfg[c.name] = st.column_config.DateColumn(c.label, format='YYYY-MM-DD')
        elif c.ftype == 'int':
            cfg[c.name] = st.column_config.NumberColumn(c.label, step=1)
        elif c.ftype == 'float':
            cfg[c.name] = st.column_config.NumberColumn(c.label, format='%.2f')
        else:
            cfg[c.name] = st.column_config.TextColumn(c.label)
    return cfg


def _rows_to_df(rows, cols):
    """list[dict] de la DB -> DataFrame con TODAS las columnas de la
    grilla en orden, y las columnas de fecha convertidas a date() real
    (mejora de UX real sobre el texto plano de la app de escritorio;
    _to_date en insert_engine ya sabe leer objetos date/datetime de vuelta,
    asi que no hace falta reconvertir a texto antes de bulk_upsert)."""
    col_names = [c.name for c in cols]
    date_cols = {c.name for c in cols if c.ftype == 'date'}
    if not rows:
        return pd.DataFrame(columns=col_names)
    df = pd.DataFrame(rows)
    for c in col_names:
        if c not in df.columns:
            df[c] = None
    df = df[col_names]
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors='coerce').dt.date
    return df


def _df_to_excel_bytes(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return buf.getvalue()


@st.dialog('Resultado')
def _show_result_dialog(result):
    n_err = len(result['errores'])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Insertados', result['insertados'])
    c2.metric('Modificados', result['modificados'])
    c3.metric('Sin cambios', result['sin_cambios'])
    c4.metric('Con errores', n_err, delta_color='inverse' if n_err else 'off')

    filas = []
    for entry in result['errores']:
        for err in entry['errores']:
            filas.append({'Tipo': 'Error', 'Clave': entry['clave'], 'Fila': entry['fila'],
                          'Campo': err['campo'], 'Descripción': err['descripcion']})
    for entry in result['detalle']:
        desc = ', '.join(entry['columnas']) if entry['tipo'] == 'Modificado' else '(alta nueva)'
        filas.append({'Tipo': entry['tipo'], 'Clave': entry['clave'], 'Fila': entry['fila'],
                      'Campo': '', 'Descripción': desc})

    if filas:
        detalle_df = pd.DataFrame(filas)
        st.dataframe(detalle_df, use_container_width=True, hide_index=True)
        st.download_button(
            'Descargar Excel de detalle', data=_df_to_excel_bytes(detalle_df),
            file_name='detalle_resultado.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        st.success('Sin cambios.')

    if st.button('Cerrar'):
        st.rerun()


def _inject_search_css():
    """Marco visible en los cuadros de texto de busqueda (pedido explicito
    del usuario: costaba ubicarlos porque el borde por defecto de
    st.text_input es muy sutil). Apunta a TODOS los stTextInput de la app
    -- hoy son unicamente los campos de busqueda de estas 6 paginas, asi
    que es seguro; si mas adelante se agregan otros st.text_input (p.ej.
    en la pagina de administracion de usuarios) tambien se veran con el
    mismo marco, lo cual es consistente."""
    st.markdown("""
        <style>
        div[data-testid="stTextInput"] input {
            border: 2px solid #4b8bf5 !important;
            border-radius: 6px !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_grid_page(title, key_cols, cols, query_fn, search_fields=(('ALIMENTADOR', 'Alimentador'),)):
    """
    title        : TITLE de insert_engine (p.ej. 'BD ALIMENTADORES')
    key_cols     : lista de columnas clave (para mostrar en encabezados)
    cols         : lista de GCol (col/key/ro/cb) en el orden a mostrar
    query_fn     : dict(search) -> list[dict]; ejecuta la consulta real
    search_fields: [(nombre_columna, etiqueta)] para el formulario de busqueda
    """
    _inject_search_css()
    rol = st.session_state.get('rol')
    editor_key = f'editor_{title}'
    df_key = f'df_{title}'

    with st.form(key=f'form_busqueda_{title}', clear_on_submit=False):
        cols_form = st.columns(len(search_fields) + 1)
        valores = {}
        for i, (colname, label) in enumerate(search_fields):
            valores[colname] = cols_form[i].text_input(label, key=f'busq_{title}_{colname}')
        buscar = cols_form[-1].form_submit_button('Consultar')

    if buscar:
        rows = query_fn(valores)
        st.session_state[df_key] = _rows_to_df(rows, cols)
        st.session_state.pop(editor_key, None)

    if df_key not in st.session_state:
        st.info('Ingrese un criterio y pulse "Consultar".')
        return

    df = st.session_state[df_key]
    st.caption(f'{len(df)} registro(s) encontrado(s). '
               f'Clave ({", ".join(key_cols)}): solo se usa para altas nuevas — '
               'si la edita en una fila existente, el cambio se ignora.')

    edited = st.data_editor(
        df, key=editor_key, num_rows='dynamic', hide_index=True,
        use_container_width=True, column_config=_column_config(cols),
    )

    c1, c2, c3, c4 = st.columns(4)
    guardar = c1.button('Guardar cambios', type='primary')
    descartar = c2.button('Descartar')
    with c3:
        excel_file = st.file_uploader('Cargar desde Excel', type=['xlsx', 'xls', 'xlsm'],
                                       key=f'upload_{title}', label_visibility='collapsed')
    c4.download_button(
        'Descargar', data=_df_to_excel_bytes(df), file_name=f'{title.replace(" ", "_")}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    if descartar:
        st.session_state.pop(editor_key, None)
        st.rerun()

    if guardar:
        auth.require_permiso('modificar', 'Tu rol no permite insertar o modificar registros.')
        state = st.session_state[editor_key]
        raw_rows, row_numbers = [], []
        fila_num = 1

        for idx_str, changes in state.get('edited_rows', {}).items():
            idx = int(idx_str)
            full = df.iloc[idx].to_dict()
            full.update(changes)
            raw_rows.append({k: _clean_val(v) for k, v in full.items()})
            row_numbers.append(fila_num); fila_num += 1

        for new_row in state.get('added_rows', []):
            raw_rows.append({k: _clean_val(v) for k, v in new_row.items()})
            row_numbers.append(fila_num); fila_num += 1

        deleted_idx = state.get('deleted_rows', [])
        if deleted_idx:
            auth.require_permiso('baja', 'Tu rol no permite dar de baja registros.')
            for idx in deleted_idx:
                row = df.iloc[idx].to_dict()
                _, cfg_key = ie.get_cfg(title)
                existing = ie.get_row_by_key(cfg_key, row)
                if existing:
                    db_update_fn = _UPDATE_FNS.get(cfg_key)
                    if db_update_fn:
                        db_update_fn(existing['id'], {
                            'ESTADO_REGISTRO': 'BAJA',
                            'DADO_DE_BAJA_POR': st.session_state.get('username'),
                            'FECHA_BAJA': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        }, st.session_state.get('username'))

        if raw_rows:
            result = ie.bulk_upsert(title, raw_rows, st.session_state.get('username'), row_numbers)
        else:
            result = {'procesados': 0, 'insertados': 0, 'modificados': 0,
                      'sin_cambios': 0, 'errores': [], 'detalle': []}

        rows = query_fn(valores)
        st.session_state[df_key] = _rows_to_df(rows, cols)
        st.session_state.pop(editor_key, None)
        _show_result_dialog(result)

    if excel_file is not None:
        try:
            xdf = pd.read_excel(excel_file)
        except Exception as e:
            st.error(f'Error al leer el Excel: {e}')
            return
        xdf.columns = [str(c).strip() for c in xdf.columns]
        faltantes = ie.missing_mandatory_cols(title, list(xdf.columns))
        if faltantes:
            st.error('El Excel debe incluir estas columnas obligatorias: ' + ', '.join(faltantes))
            return
        raw_rows = ie.rows_from_dataframe(xdf)
        st.warning(f'Se van a procesar {len(raw_rows)} fila(s) de "{excel_file.name}".')
        if st.button(f'Confirmar carga de {len(raw_rows)} fila(s)', key=f'confirmar_excel_{title}'):
            auth.require_permiso('modificar', 'Tu rol no permite insertar o modificar registros.')
            result = ie.bulk_upsert(title, raw_rows, st.session_state.get('username'))
            rows = query_fn(valores)
            st.session_state[df_key] = _rows_to_df(rows, cols)
            st.session_state.pop(editor_key, None)
            _show_result_dialog(result)


# Mapeo cfg_key -> funcion de UPDATE de core/db.py, usado solo para la
# baja (borrado logico) de filas via el "-" de st.data_editor -- todo lo
# demas (alta/edicion normal) pasa por ie.bulk_upsert.
_UPDATE_FNS = {
    'ALIMENTADORES': db.editar_alimentador,
    'SOSPECHAS_MT': db.editar_sospecha_mt,
    'SOSPECHAS_BT': db.editar_sospecha_bt,
    'IRREGULARIDADES': db.editar_irregularidad,
    'INSTALACIONES_TOTAS': db.editar_instalacion,
    'LECTURAS': db.editar_lectura,
}
