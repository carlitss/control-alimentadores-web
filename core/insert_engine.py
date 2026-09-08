"""
insert_engine.py — Reglas de insercion centralizadas por tabla (version web).

Portado de app/insert_engine.py: CATALOGOS, CONFIGS, prepare_row y toda la
logica de validacion son IDENTICOS al original (no tocar sin revisar contra
la app de escritorio, que sigue siendo la referencia de comportamiento).

Unico cambio real: exists_in_db, get_row_by_key, _all_cols y prepare_row
ahora aceptan un `conn` opcional, y bulk_upsert abre UNA sola conexion
para todo el lote (antes abria una por fila, mas otra anidada por cada
llamada a get_row_by_key/exists_in_db) — contra una base remota como
Turso eso son decenas de conexiones nuevas por cada pegado o carga de
Excel; reutilizar una sola evita ese costo. Ver plan de migracion, Fase 2.
"""
import re
from datetime import datetime
import core.db as db

# ─── Columnas que NUNCA van en INSERT ────────────────────────────
AUDIT_COLS = frozenset({
    'id', 'alimentador_id',
    'CREADO_POR', 'FECHA_CREACION',
    'MODIFICADO_POR', 'FECHA_MODIFICACION',
    'DADO_DE_BAJA_POR', 'FECHA_BAJA', 'MOTIVO_BAJA',
    'ESTADO_REGISTRO',
})
DB_COMPUTED = frozenset({
    'PERDIDA_KWH', 'PERDIDA_PCT',
    'DIAS_CIERRE', 'RECUPERO_MWH_MES',
    'ESTADO_LECTURAS', 'ESTADO_INST_TOTAS',
    'RIESGO',
    'TOTAL_CLIENTES_MT',
})
TRIGGER_COLS = frozenset({
    'NODOS_SOSPECHOSOS', 'TOTAL_ASIGNADOS_TOTA', 'TOTAL_INSTALADOS_TOTA',
    'TOTAL_IMP_TOTA', 'TOTAL_LECTURAS_RECOGER', 'TOTAL_EFECTIVOS_LECTURA',
    'TOTAL_EFECTIVOS_PINZADO', 'TOTAL_IMPEDIMENTOS_LEC', 'TOTAL_IRREGULARIDADES',
    'TOTAL_CASOS_INST_TOTA',
    'ESTADO_CONTROL',
    'PERIODO_PLANIF',
})
NEVER_INSERT = AUDIT_COLS | DB_COMPUTED | TRIGGER_COLS

CATALOGOS = {
    'ESTADO_TRABAJO':      ['POR TRABAJAR', 'EN CURSO', 'CERRADO', 'SUSPENDIDO'],
    'ESTADO_PINZADO':      ['POR INICIAR', 'EN CURSO', 'FINALIZADO', 'SUSPENDIDO'],
    'DENSIDAD':            ['MD', 'BD', 'MBD', 'MAD', 'AD', 'SIN CLASIFICACION'],
    'ESTADO_ANALISIS':     ['POR TRABAJAR', 'EN ANALISIS', 'ANALIZADO', 'CERRADO'],
    'TIPO_HURTO':          ['ALP', 'CNX CLANDESTINA', 'MANIPULACION DE MEDIDOR'],
    'TENSION':             ['BT', 'MT'],
    'ESTADO_INST':         ['NO ASIGNADO', 'ASIGNADO', 'INSTALADO', 'IMPEDIMENTO', 'RECHAZADO'],
    'TIPO_FINAL':          ['SED', 'CLIENTE MT'],
    'CATEGORIA':           ['CLANDESTINO', 'MEDIDOR MANIPULADO', 'ALP', 'ACOMETIDA', 'OTRO'],
    'TIPO_CONST':          ['AEREA BIPOSTE', 'AEREA MONOPOSTE', 'COMPACTA BOVEDA',
                            'COMPACTA PEDESTAL', 'CONVENCIONAL DE SUPERFICIE',
                            'CONVENCIONAL SUBTERRANEA'],
    'SELECCION':           ['TOP 101', 'TOP 101 - NEW', 'PROP ADICIONAL'],
    'ESTADO_REG':          ['ALTA', 'BAJA'],
    'ESTADO_ACTIVIDAD_MT': ['', 'ASIGNADO INSP MT', 'EN ANALISIS RE MT', 'DESCARTADO MT',
                            'ASIGNADO RE MT', 'SOSPECHA DE HURTO MT', 'SEGUNDO PINZADO MT'],
    'ESTADO_ACTIVIDAD_BT': ['', 'ASIGNADO INSP', 'EN ANALISIS RE', 'DESCARTADO RE', 'ASIGNADO RE'],
    'ESTADO_RE':           ['DERIVADO A BT', 'DESCARTADO SIN PERD', 'SEGUNDO PINZADO MT',
                            'ASIGNADO INSP MT', 'ASIGNADO RE MT'],
    'ESTADO_FOCAL':        ['ASIGNADO', 'BARRIDO', 'IDENT SOSPECHOSO', 'CONF. HURTO', 'OPERATIVO',
                            'CIERRE CON REFORMA', 'CIERRE SIN REFORMA', 'DESCARTADO'],
    'ESTADO_LECTURA':      ['ASIGNADO', 'EFECTIVO LECTURA', 'EFECTIVO PINZADO', 'IMPEDIMENTO', 'NO ASIGNADO'],
    'ESTADO_CNR':          ['NO PROCEDE', 'VALORIZADO', 'EN PROCESO DE VALORIZACIÓN'],
    'STATUS_CONTEO_SED':   ['', 'SED CON CNR'],
}

CONFIGS = {
    'ALIMENTADORES': {
        'db_table':  'ALIMENTADORES',
        'key_cols':  ['ALIMENTADOR'],
        'mandatory': ['ALIMENTADOR'],
        'needs_alim': False,
        'auto_inst': False,
        'catalogos': {
            'SELECCION_PLUZ':      'SELECCION',
            'DENSIDAD':            'DENSIDAD',
            'ESTADO_TRABAJO_MT':   'ESTADO_TRABAJO',
            'ESTADO_TRABAJO_BT':   'ESTADO_TRABAJO',
            'ESTADO_ANALISIS_CSG': 'ESTADO_ANALISIS',
            'ESTADO_PINZADO':      'ESTADO_PINZADO',
        },
    },
    'SOSPECHAS_MT': {
        'db_table':  'SOSPECHAS_MT',
        'key_cols':  ['ALIMENTADOR', 'NODO'],
        'mandatory': ['ALIMENTADOR', 'NODO'],
        'needs_alim': True,
        'auto_inst': False,
        'catalogos': {
            'ESTADO_ACTIVIDAD': 'ESTADO_ACTIVIDAD_MT',
            'ESTADO_RE':        'ESTADO_RE',
            'ESTADO_INSP':      'ESTADO_FOCAL',
        },
    },
    'SOSPECHAS_BT': {
        'db_table':  'SOSPECHAS_BT',
        'key_cols':  ['ALIMENTADOR', 'NODO', 'SED'],
        'mandatory': ['ALIMENTADOR', 'NODO', 'SED'],
        'needs_alim': True,
        'auto_inst': False,
        'computed_cols': {'ESTADO_RE'},
        # PERIODO_PLANIF es NOT NULL en el esquema y lo completa recien
        # trg_sbt_ins DESPUES del INSERT (automatico desde
        # ALIMENTADORES.MES_PLANIFICADO) -- pero tambien esta en
        # TRIGGER_COLS (NEVER_INSERT), asi que bulk_upsert nunca lo
        # incluye en el INSERT. Sin este default explicito, un alta
        # nueva por pegado/Excel fallaba con "NOT NULL constraint
        # failed" (bug real, heredado de app/database.py.crear_sospecha_bt,
        # que tenia el mismo data.setdefault pero bulk_upsert nunca pasaba
        # por ahi -- encontrado durante las pruebas de la Fase 5).
        'insert_defaults': {'PERIODO_PLANIF': ''},
        'catalogos': {
            'ESTADO_ANALISIS_CSG': 'ESTADO_ANALISIS',
            'ESTADO_ACTIVIDAD':    'ESTADO_ACTIVIDAD_BT',
            'ESTADO_FOCALIZACION': 'ESTADO_FOCAL',
            'STATUS_CONTEO_SED':   'STATUS_CONTEO_SED',
        },
    },
    'IRREGULARIDADES': {
        'db_table':  'IRREGULARIDADES',
        'key_cols':  ['CONCA'],
        'mandatory': ['ALIMENTADOR', 'NODO', 'CONCA'],
        'needs_alim': True,
        'auto_inst': False,
        'catalogos': {
            'ESTADO_FOCALIZACION': 'ESTADO_FOCAL',
            'TENSION':             'TENSION',
            'ESTADO_CNR':          'ESTADO_CNR',
            'CATEGORIA':           'CATEGORIA',
            'TIPO_HURTO':          'TIPO_HURTO',
        },
    },
    'INSTALACIONES_TOTAS': {
        'db_table':  'INSTALACIONES_TOTAS',
        'key_cols':  ['ALIMENTADOR', 'COD_PUNTO_MEDICION'],
        'mandatory': ['ALIMENTADOR', 'COD_PUNTO_MEDICION'],
        'needs_alim': True,
        'auto_inst': False,
        'catalogos': {
            'TIPO_CONSTRUCCION': 'TIPO_CONST',
            'ESTADO_INSTALACION':'ESTADO_INST',
            'TIPO_FINAL':        'TIPO_FINAL',
        },
    },
    'LECTURAS': {
        'db_table':  'LECTURAS',
        'key_cols':  ['ALIMENTADOR', 'COD_PUNTO_MEDICION', 'PERIODO'],
        'mandatory': ['ALIMENTADOR', 'COD_PUNTO_MEDICION', 'PERIODO'],
        'needs_alim': True,
        'auto_inst': True,
        'catalogos': {
            'ESTADO_LECTURA': 'ESTADO_LECTURA',
        },
    },
}

TAB_TO_CFG = {
    'BD ALIMENTADORES':     'ALIMENTADORES',
    'BD SOSPECHA MT':       'SOSPECHAS_MT',
    'BD SOSPECHA BT':       'SOSPECHAS_BT',
    'BD IRREGULARIDADES':   'IRREGULARIDADES',
    'BD INSTALACION TOTAS': 'INSTALACIONES_TOTAS',
    'BD LECTURAS':          'LECTURAS',
}

INT_COLS = frozenset({
    'NODO', 'ORDEN_ATENCION', 'N_SEDS', 'CLIENTES_MAX_MT',
    'CLIENTES_LIB_PEAJES', 'CLIENTES_NO_UBI', 'PRIORIDAD', 'SUM_CLIENTE',
    'N_TOTAS', 'TOTAS_PENDIENTES',
})
FLOAT_COLS = frozenset({
    'CORRIENTE_A', 'CONSUMO_TOTALIZADOR', 'CONSUMO_CLIENTES',
    'PERDIDA_MT_REF', 'PERDIDA_COMERCIAL_PROM', 'A_LOSS',
    'RECUPERO_MWH', 'MESES_CNR', 'IMPACTO_ANO_MWH',
    'ENERGIA_KWH_REC_MES',
})
DATE_COLS = frozenset({
    'MES_PLANIFICADO', 'FECHA_INICIO_PINZADO', 'FECHA_FIN_PINZADO',
    'PERIODO_PLANIF', 'FECHA_CARGA', 'FECHA_ASIGNACION',
    'PLAZO_FINAL', 'FECHA_INTERVENCION', 'FECHA_ASIG_INSP',
    'FECHA_NORMALIZACION', 'FECHA_EXTRACCION', 'PERIODO',
})

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_DATE_ES = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})$')
_EMPTY   = frozenset({'', 'none', 'nan', 'nat', 'nattype', '#n/a', 'n/a', 'null'})


def _to_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return None if s.lower() in _EMPTY else s


def _to_int(v):
    s = _to_str(v)
    if s is None:
        return None, None
    try:
        return int(float(s)), None
    except Exception:
        return None, f'Entero invalido: "{v}"'


def _to_float(v):
    s = _to_str(v)
    if s is None:
        return None, None
    try:
        return float(s.replace(',', '.')), None
    except Exception:
        return None, f'Decimal invalido: "{v}"'


def _to_date(v):
    if hasattr(v, 'strftime'):
        return v.strftime('%Y-%m-%d'), None
    s = _to_str(v)
    if s is None:
        return None, None
    if _DATE_RE.match(s):
        try:
            datetime.strptime(s, '%Y-%m-%d')
            return s, None
        except Exception:
            pass
    m = _DATE_ES.match(s)
    if m:
        d, mo, y = m.groups()
        try:
            return datetime(int(y), int(mo), int(d)).strftime('%Y-%m-%d'), None
        except Exception:
            pass
    return None, f'Fecha invalida: "{v}" (use YYYY-MM-DD o DD/MM/YYYY)'


def _coerce_val(col, val):
    if col in INT_COLS:
        return _to_int(val)
    if col in FLOAT_COLS:
        return _to_float(val)
    if col in DATE_COLS:
        return _to_date(val)
    return _to_str(val), None


# ─── API pública ─────────────────────────────────────────────────

def get_cfg(tab_title):
    key = TAB_TO_CFG.get(tab_title)
    if not key:
        raise ValueError(f'No hay configuracion para la pestana: {tab_title}')
    return CONFIGS[key], key


def row_key_tuple(cfg_key, row):
    """OJO: no usar `row.get(k) or ''` acá — NODO puede legítimamente valer 0."""
    cfg = CONFIGS[cfg_key]
    return tuple(
        '' if row.get(k) is None else str(row.get(k)).strip().upper()
        for k in cfg['key_cols']
    )


_INT_KEY_COLS = frozenset({'NODO'})


def exists_in_db(cfg_key, row, conn=None):
    """True if a record with the same keys already exists in the DB."""
    cfg = CONFIGS[cfg_key]
    key_cols = cfg['key_cols']
    vals = [row.get(k) for k in key_cols]
    if any(v is None or str(v).strip() == '' for v in vals):
        return False
    where_parts = [
        f'{k}=?' if k in _INT_KEY_COLS else f'{k}=? COLLATE NOCASE'
        for k in key_cols
    ]
    where = ' AND '.join(where_parts)
    own_conn = conn is None
    conn = conn or db.get_conn()
    try:
        return conn.execute(
            f'SELECT 1 FROM {cfg["db_table"]} WHERE {where}', vals
        ).fetchone() is not None
    finally:
        if own_conn:
            conn.close()


def prepare_row(tab_title, raw, usuario='', caches=None, conn=None):
    """
    Validate and prepare a row dict for INSERT/UPDATE. Ver docstring
    original en app/insert_engine.py -- logica identica, unico agregado
    es el `conn` opcional que se propaga a las consultas de FK/auto_inst
    para que bulk_upsert pueda reutilizar una sola conexion por lote.
    """
    cfg, cfg_key = get_cfg(tab_title)
    if caches is None:
        caches = {}
    errors = []
    catalogos_cfg = cfg.get('catalogos', {})
    computed_cfg = cfg.get('computed_cols', ())

    for col in cfg['mandatory']:
        if not _to_str(raw.get(col)):
            errors.append(f'{col}: campo obligatorio faltante')

    cache_key = f'realcols|{cfg["db_table"]}'
    if cache_key not in caches:
        caches[cache_key] = set(_all_cols(cfg['db_table'], conn))
    real_cols = caches[cache_key]

    clean = {}
    for col, val in raw.items():
        if col in NEVER_INSERT or col in computed_cfg or col.startswith('__'):
            continue
        if col not in real_cols:
            if _to_str(val) is not None:
                errors.append(
                    f'{col}: esta columna no existe en "{tab_title}" — revise si '
                    'pegó o cargó datos de otra pestaña/tabla')
            continue
        coerced, err = _coerce_val(col, val)
        if err:
            errors.append(f'{col}: {err}')
            continue
        cat_key = catalogos_cfg.get(col)
        if cat_key and coerced not in (None, ''):
            permitidos = CATALOGOS.get(cat_key, [])
            if coerced not in permitidos:
                opciones = ', '.join(v for v in permitidos if v) or '(sin opciones)'
                errors.append(
                    f'{col}: valor "{coerced}" no está en la lista permitida ({opciones})'
                )
                continue
        clean[col] = coerced

    if cfg['needs_alim'] and 'ALIMENTADOR' not in [
        m.split(':', 1)[0] for m in errors
    ]:
        alim = clean.get('ALIMENTADOR')
        if alim:
            cache_key = f'alim|{alim}'
            if cache_key not in caches:
                caches[cache_key] = db.get_alimentador_by_codigo(alim, conn)
            alim_row = caches[cache_key]
            if not alim_row:
                errors.append(
                    f'ALIMENTADOR: "{alim}" no encontrado en el maestro de alimentadores'
                )
            else:
                clean['alimentador_id'] = alim_row['id']

    if errors:
        return None, errors

    warnings = []
    if cfg.get('auto_inst'):
        alim = clean.get('ALIMENTADOR')
        cod = clean.get('COD_PUNTO_MEDICION')
        cache_key = f'inst|{alim}|{cod}'
        if cache_key not in caches:
            caches[cache_key] = (
                db.get_instalacion_by_key(alim, cod, conn)
                if alim and cod else None
            )
        inst = caches[cache_key]
        if inst:
            clean['TIPO']       = _to_str(inst.get('TIPO_FINAL')) or clean.get('TIPO')
            clean['COD_TRAFO']  = _to_str(inst.get('COD_TRAFO'))  or clean.get('COD_TRAFO')
            clean['MEDIDOR_SB'] = _to_str(inst.get('MEDIDOR_SB')) or clean.get('MEDIDOR_SB')
            clean['MARCA']      = _to_str(inst.get('MARCA'))       or clean.get('MARCA')
        elif alim and cod:
            warnings.append(
                f'{alim}/{cod}: instalacion no encontrada en INSTALACIONES_TOTAS; '
                'TIPO/COD_TRAFO/MEDIDOR_SB/MARCA quedaran vacios'
            )

    if not clean.get('ESTADO_REGISTRO'):
        clean['ESTADO_REGISTRO'] = 'ALTA'

    return clean, warnings


def rows_from_dataframe(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return [
        {c: series.get(c) for c in df.columns}
        for _, series in df.iterrows()
    ]


def get_row_by_key(cfg_key, row, conn=None):
    """Full existing DB row matching row's key columns, or None."""
    cfg = CONFIGS[cfg_key]
    key_cols = cfg['key_cols']
    vals = [row.get(k) for k in key_cols]
    if any(v is None or str(v).strip() == '' for v in vals):
        return None
    where_parts = [
        f'{k}=?' if k in _INT_KEY_COLS else f'{k}=? COLLATE NOCASE'
        for k in key_cols
    ]
    where = ' AND '.join(where_parts)
    own_conn = conn is None
    conn = conn or db.get_conn()
    try:
        row_ = conn.execute(
            f'SELECT * FROM {cfg["db_table"]} WHERE {where}', vals
        ).fetchone()
        return dict(row_) if row_ else None
    finally:
        if own_conn:
            conn.close()


def _values_equal(col, old, new):
    if old is None and new is None:
        return True
    if old is None or new is None:
        return False
    if col in FLOAT_COLS:
        try:
            return abs(float(old) - float(new)) < 1e-9
        except Exception:
            return old == new
    if col in INT_COLS:
        try:
            return int(old) == int(new)
        except Exception:
            return old == new
    return str(old).strip() == str(new).strip()


_NEVER_UPDATE = frozenset({'ESTADO_REGISTRO'})


def missing_mandatory_cols(tab_title, pasted_col_names):
    cfg, _ = get_cfg(tab_title)
    pasted = set(pasted_col_names)
    return [c for c in cfg['mandatory'] if c not in pasted]


def _split_campo(msg):
    if ':' in msg:
        campo, desc = msg.split(':', 1)
        campo = campo.strip()
        if campo and ' ' not in campo.split('"')[0].strip():
            return campo, desc.strip()
    return 'General', msg


def bulk_upsert(tab_title, raw_rows, usuario, row_numbers=None):
    """
    Inserta o actualiza registros pegados/cargados, fila por fila. Misma
    logica que app/insert_engine.py -- unico cambio: abre UNA conexion al
    inicio y la reutiliza para todas las filas del lote (prepare_row,
    get_row_by_key, INSERT/UPDATE), en vez de abrir una nueva por fila.
    Contra Turso (remoto, via HTTP) eso evita decenas de handshakes TLS
    de mas en un pegado o carga de Excel de varias filas.
    """
    cfg, cfg_key = get_cfg(tab_title)
    caches = {}
    result = {
        'procesados': 0, 'insertados': 0, 'modificados': 0,
        'sin_cambios': 0, 'errores': [], 'detalle': [],
    }

    def _key_label(d):
        return ' / '.join(
            ('—' if d.get(k) is None else str(d.get(k)).strip()) or '—'
            for k in cfg['key_cols']
        )

    def _key_dict(d):
        return {k: d.get(k) for k in cfg['key_cols']}

    def _add_error(row_num, keyed_dict, mensajes):
        result['errores'].append({
            'tabla': cfg['db_table'],
            'fila': row_num,
            'clave': _key_label(keyed_dict),
            'claves': _key_dict(keyed_dict),
            'errores': [dict(zip(('campo', 'descripcion'), _split_campo(m))) for m in mensajes],
        })

    def _add_detalle(row_num, keyed_dict, tipo, columnas):
        result['detalle'].append({
            'tabla': cfg['db_table'],
            'fila': row_num,
            'clave': _key_label(keyed_dict),
            'claves': _key_dict(keyed_dict),
            'tipo': tipo,
            'columnas': columnas,
        })

    conn = db.get_conn()
    try:
        for idx, raw in enumerate(raw_rows):
            i = row_numbers[idx] if row_numbers is not None else idx + 1
            result['procesados'] += 1

            clean, msgs = prepare_row(tab_title, raw, usuario, caches, conn)
            if clean is None:
                _add_error(i, raw, msgs)
                continue

            kt = row_key_tuple(cfg_key, clean)
            if any(not part for part in kt):
                _add_error(i, raw, [
                    f'Campos clave incompletos ({", ".join(cfg["key_cols"])})'
                ])
                continue

            try:
                existing = get_row_by_key(cfg_key, clean, conn)

                if existing is None:
                    insert_vals = dict(clean)
                    insert_vals['CREADO_POR']     = usuario
                    insert_vals['FECHA_CREACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    insert_vals.setdefault('ESTADO_REGISTRO', 'ALTA')
                    for k, v in cfg.get('insert_defaults', {}).items():
                        insert_vals.setdefault(k, v)
                    cols = list(insert_vals.keys())
                    ph   = ', '.join(['?'] * len(cols))
                    conn.execute(
                        f'INSERT INTO {cfg["db_table"]} ({", ".join(cols)}) VALUES ({ph})',
                        [insert_vals[c] for c in cols])
                    conn.commit()
                    result['insertados'] += 1
                    _add_detalle(i, clean, 'Insertado', None)
                else:
                    changes = {}
                    for col, val in clean.items():
                        if col in cfg['key_cols'] or col in _NEVER_UPDATE:
                            continue
                        if not _values_equal(col, existing.get(col), val):
                            changes[col] = val
                    if changes:
                        columnas_reales = sorted(changes.keys())
                        changes['MODIFICADO_POR']     = usuario
                        changes['FECHA_MODIFICACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        sets = ', '.join(f'{c}=?' for c in changes)
                        conn.execute(
                            f'UPDATE {cfg["db_table"]} SET {sets} WHERE id=?',
                            list(changes.values()) + [existing['id']])
                        conn.commit()
                        result['modificados'] += 1
                        _add_detalle(i, clean, 'Modificado', columnas_reales)
                    else:
                        result['sin_cambios'] += 1
            except Exception as e:
                try: conn.rollback()
                except Exception: pass
                _add_error(i, raw, [str(e)])
    finally:
        conn.close()

    return result


def mandatory_cols_label(tab_title):
    cfg, _ = get_cfg(tab_title)
    return ', '.join(cfg['mandatory'])


def all_insertable_cols(tab_title):
    cfg, _ = get_cfg(tab_title)
    return [c for c in _all_cols(cfg['db_table'])
            if c not in NEVER_INSERT]


def _all_cols(table_name, conn=None):
    """Query column names from DB schema. PRAGMA table_info fue validado
    contra Turso en el spike de la Fase 1 (funciona igual que en SQLite
    local via HTTP)."""
    own_conn = conn is None
    conn = conn or db.get_conn()
    try:
        info = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
        return [row[1] for row in info]
    finally:
        if own_conn:
            conn.close()
