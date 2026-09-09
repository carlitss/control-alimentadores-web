"""
db.py — Capa de acceso a datos para Control Alimentadores (version web).

Portado de app/database.py: mismo SQL, mismas reglas de negocio, unico
cambio real es de donde viene la conexion (Turso via HTTP en vez de un
archivo SQLite local) y como se manejan errores de restriccion UNIQUE.

get_alimentador_by_codigo() y get_instalacion_by_key() aceptan un `conn`
opcional porque bulk_upsert (en insert_engine.py) las llama dentro de un
bucle por fila y necesita reutilizar UNA sola conexion para todo el lote
en vez de abrir una nueva por cada fila (ver plan de migracion, Fase 2).
Las demas funciones se llaman siempre de a una (paginas normales de la
grilla), no hay beneficio en propagarles tambien el parametro.
"""
from datetime import datetime
from core.turso_http import get_conn, TursoError

__all__ = [
    'get_conn', 'rows_to_list',
    'buscar_alimentadores', 'get_alimentadores', 'get_alimentador',
    'get_alimentador_by_codigo', 'crear_alimentador', 'editar_alimentador',
    'get_sospecha_mt_by_key', 'get_sospechas_mt_all', 'get_sospechas_mt',
    'crear_sospecha_mt', 'editar_sospecha_mt',
    'get_sospecha_bt_by_key', 'get_sospechas_bt_filtradas', 'get_sospechas_bt',
    'crear_sospecha_bt', 'editar_sospecha_bt',
    'get_irregularidad_by_key', 'get_irregularidades_all', 'get_irregularidades',
    'crear_irregularidad', 'editar_irregularidad',
    'get_instalacion_by_key', 'get_instalaciones_all', 'get_instalaciones',
    'crear_instalacion', 'editar_instalacion',
    'get_lectura_by_key', 'get_lecturas_all', 'get_lecturas',
    'crear_lectura', 'editar_lectura',
    'get_kpis', 'get_dashboard_nodos_por_actividad',
    'get_dashboard_alimentadores_asignados_insp', 'get_dashboard_estados_nodos_insp',
    'get_dashboard_sed_data', 'get_dashboard_clientes_cerrado_con_imp',
    'get_dashboard_meses', 'get_dashboard_kpis',
    'get_dashboard_bt_kpis', 'get_dashboard_bt_focalizacion',
    'get_dashboard_bt_status_conteo', 'get_dashboard_irregularidades_bt',
    'get_dashboard_irregularidades_alimentador',
    'get_usuarios', 'get_usuario_by_username', 'crear_usuario',
    'actualizar_password', 'actualizar_usuario',
    'get_permisos_usuario', 'set_permisos_usuario',
]


def rows_to_list(rows):
    return [dict(r) for r in rows]


def _is_unique_violation(e):
    return 'UNIQUE constraint' in str(e)


# ─── ALIMENTADORES ────────────────────────────────────
def buscar_alimentadores(texto):
    conn = get_conn()
    if texto:
        rows = conn.execute(
            "SELECT * FROM ALIMENTADORES WHERE ALIMENTADOR=? COLLATE NOCASE ORDER BY ALIMENTADOR",
            (texto,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM ALIMENTADORES ORDER BY ALIMENTADOR").fetchall()
    conn.close()
    return rows_to_list(rows)


def get_sospechas_mt_all(alimentador=''):
    conn = get_conn()
    if alimentador:
        rows = conn.execute(
            "SELECT * FROM SOSPECHAS_MT WHERE ALIMENTADOR=? COLLATE NOCASE ORDER BY ALIMENTADOR, NODO",
            (alimentador,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM SOSPECHAS_MT ORDER BY ALIMENTADOR, NODO").fetchall()
    conn.close()
    return rows_to_list(rows)


def get_sospechas_bt_filtradas(alimentador='', sed=None):
    conn = get_conn()
    if alimentador:
        q = "SELECT * FROM SOSPECHAS_BT WHERE ALIMENTADOR=? COLLATE NOCASE"
        params = [alimentador]
        if sed:
            q += " AND SED=? COLLATE NOCASE"
            params.append(sed)
        q += " ORDER BY ALIMENTADOR, NODO, SED, PERIODO_PLANIF"
    else:
        if sed:
            q = "SELECT * FROM SOSPECHAS_BT WHERE SED=? COLLATE NOCASE ORDER BY ALIMENTADOR, NODO, SED, PERIODO_PLANIF"
            params = [sed]
        else:
            q = "SELECT * FROM SOSPECHAS_BT ORDER BY ALIMENTADOR, NODO, SED, PERIODO_PLANIF"
            params = []
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows_to_list(rows)


def get_irregularidades_all(alimentador=''):
    conn = get_conn()
    if alimentador:
        rows = conn.execute(
            'SELECT * FROM IRREGULARIDADES WHERE ALIMENTADOR=? COLLATE NOCASE ORDER BY ALIMENTADOR, "KEY"',
            (alimentador,)).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM IRREGULARIDADES ORDER BY ALIMENTADOR, "KEY"').fetchall()
    conn.close()
    return rows_to_list(rows)


def get_instalaciones_all(alimentador=''):
    conn = get_conn()
    if alimentador:
        rows = conn.execute(
            "SELECT * FROM INSTALACIONES_TOTAS WHERE ALIMENTADOR=? COLLATE NOCASE ORDER BY ALIMENTADOR, COD_PUNTO_MEDICION",
            (alimentador,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM INSTALACIONES_TOTAS ORDER BY ALIMENTADOR, COD_PUNTO_MEDICION").fetchall()
    conn.close()
    return rows_to_list(rows)


def get_lecturas_all(alimentador=''):
    conn = get_conn()
    if alimentador:
        rows = conn.execute(
            "SELECT * FROM LECTURAS WHERE ALIMENTADOR=? COLLATE NOCASE ORDER BY ALIMENTADOR, COD_PUNTO_MEDICION, PERIODO",
            (alimentador,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM LECTURAS ORDER BY ALIMENTADOR, COD_PUNTO_MEDICION, PERIODO").fetchall()
    conn.close()
    return rows_to_list(rows)


def get_alimentadores(busqueda='', solo_alta=True):
    conn = get_conn()
    q = "SELECT * FROM ALIMENTADORES WHERE 1=1"
    params = []
    if solo_alta:
        q += " AND ESTADO_REGISTRO='ALTA'"
    if busqueda:
        q += " AND (ALIMENTADOR=? COLLATE NOCASE OR SUBESTACION=? COLLATE NOCASE)"
        params += [busqueda, busqueda]
    q += " ORDER BY ALIMENTADOR"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows_to_list(rows)


def get_alimentador(alimentador_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM ALIMENTADORES WHERE id=?', (alimentador_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_alimentador_by_codigo(codigo, conn=None):
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        row = conn.execute('SELECT * FROM ALIMENTADORES WHERE ALIMENTADOR=? COLLATE NOCASE', (codigo,)).fetchone()
        return dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


def crear_alimentador(data, usuario):
    conn = get_conn()
    data['CREADO_POR'] = usuario
    data['FECHA_CREACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['ESTADO_REGISTRO'] = 'ALTA'
    cols = ', '.join(data.keys())
    ph = ', '.join(['?'] * len(data))
    try:
        cur = conn.execute(f'INSERT INTO ALIMENTADORES ({cols}) VALUES ({ph})', list(data.values()))
        _log(conn, 'ALIMENTADORES', cur.lastrowid, 'CREAR', f'Nuevo: {data.get("ALIMENTADOR")}', usuario)
        conn.commit()
        return cur.lastrowid, None
    except TursoError as e:
        if _is_unique_violation(e):
            return None, f'Ya existe un alimentador con ese código: {e}'
        raise
    finally:
        conn.close()


def editar_alimentador(alim_id, data, usuario):
    conn = get_conn()
    data['MODIFICADO_POR'] = usuario
    data['FECHA_MODIFICACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join([f'{k}=?' for k in data.keys()])
    try:
        conn.execute(f'UPDATE ALIMENTADORES SET {sets} WHERE id=?', list(data.values()) + [alim_id])
        _log(conn, 'ALIMENTADORES', alim_id, 'MODIFICAR', f'Campos: {list(data.keys())}', usuario)
        conn.commit()
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# ─── SOSPECHAS MT ─────────────────────────────────────
def get_sospecha_mt_by_key(alimentador, nodo):
    conn = get_conn()
    row = conn.execute('SELECT * FROM SOSPECHAS_MT WHERE ALIMENTADOR=? AND NODO=?', (alimentador, int(nodo))).fetchone()
    conn.close()
    return dict(row) if row else None


def get_sospechas_mt(alimentador):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM SOSPECHAS_MT
        WHERE ALIMENTADOR=? AND ESTADO_REGISTRO='ALTA'
        ORDER BY NODO
    """, (alimentador,)).fetchall()
    conn.close()
    return rows_to_list(rows)


def crear_sospecha_mt(data, usuario):
    conn = get_conn()
    data['CREADO_POR'] = usuario
    data['FECHA_CREACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['ESTADO_REGISTRO'] = 'ALTA'
    cols = ', '.join(data.keys())
    ph = ', '.join(['?'] * len(data))
    try:
        cur = conn.execute(f'INSERT INTO SOSPECHAS_MT ({cols}) VALUES ({ph})', list(data.values()))
        _log(conn, 'SOSPECHAS_MT', cur.lastrowid, 'CREAR', f'{data.get("ALIMENTADOR")}-{data.get("NODO")}', usuario)
        conn.commit()
        return cur.lastrowid, None
    except TursoError as e:
        if _is_unique_violation(e):
            return None, 'Ya existe una sospecha MT para ese ALIMENTADOR + NODO.'
        raise
    finally:
        conn.close()


def editar_sospecha_mt(sid, data, usuario):
    conn = get_conn()
    data['MODIFICADO_POR'] = usuario
    data['FECHA_MODIFICACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join([f'{k}=?' for k in data.keys()])
    conn.execute(f'UPDATE SOSPECHAS_MT SET {sets} WHERE id=?', list(data.values()) + [sid])
    _log(conn, 'SOSPECHAS_MT', sid, 'MODIFICAR', '', usuario)
    conn.commit()
    conn.close()


# ─── SOSPECHAS BT ─────────────────────────────────────
def get_sospecha_bt_by_key(alimentador, nodo, sed, periodo):
    conn = get_conn()
    row = conn.execute(
        'SELECT * FROM SOSPECHAS_BT WHERE ALIMENTADOR=? AND NODO=? AND SED=? AND PERIODO_PLANIF=?',
        (alimentador, int(nodo), sed, periodo)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_sospechas_bt(alimentador):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM SOSPECHAS_BT
        WHERE ALIMENTADOR=? AND ESTADO_REGISTRO='ALTA'
        ORDER BY NODO, SED
    """, (alimentador,)).fetchall()
    conn.close()
    return rows_to_list(rows)


def crear_sospecha_bt(data, usuario):
    conn = get_conn()
    data['CREADO_POR'] = usuario
    data['FECHA_CREACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['ESTADO_REGISTRO'] = 'ALTA'
    # PERIODO_PLANIF es NOT NULL en el schema y lo completa el trigger
    # trg_sbt_ins tras el INSERT (automatico desde ALIMENTADORES.MES_PLANIFICADO).
    data.setdefault('PERIODO_PLANIF', '')
    cols = ', '.join(data.keys())
    ph = ', '.join(['?'] * len(data))
    try:
        cur = conn.execute(f'INSERT INTO SOSPECHAS_BT ({cols}) VALUES ({ph})', list(data.values()))
        conn.commit()
        _log(conn, 'SOSPECHAS_BT', cur.lastrowid, 'CREAR', '', usuario)
        conn.commit()
        return cur.lastrowid, None
    except TursoError as e:
        if _is_unique_violation(e):
            return None, 'Ya existe una sospecha BT para ALIMENTADOR + NODO + SED + PERIODO.'
        raise
    finally:
        conn.close()


def editar_sospecha_bt(sid, data, usuario):
    conn = get_conn()
    data['MODIFICADO_POR'] = usuario
    data['FECHA_MODIFICACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join([f'{k}=?' for k in data.keys()])
    conn.execute(f'UPDATE SOSPECHAS_BT SET {sets} WHERE id=?', list(data.values()) + [sid])
    conn.commit()
    conn.close()


# ─── IRREGULARIDADES ──────────────────────────────────
def get_irregularidad_by_key(key):
    conn = get_conn()
    row = conn.execute('SELECT * FROM IRREGULARIDADES WHERE "KEY"=?', (key,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_irregularidades(alimentador):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM IRREGULARIDADES
        WHERE ALIMENTADOR=? AND ESTADO_REGISTRO='ALTA'
        ORDER BY NODO, "KEY"
    """, (alimentador,)).fetchall()
    conn.close()
    return rows_to_list(rows)


def crear_irregularidad(data, usuario):
    conn = get_conn()
    data['CREADO_POR'] = usuario
    data['FECHA_CREACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['ESTADO_REGISTRO'] = 'ALTA'
    cols = ', '.join(data.keys())
    ph = ', '.join(['?'] * len(data))
    try:
        cur = conn.execute(f'INSERT INTO IRREGULARIDADES ({cols}) VALUES ({ph})', list(data.values()))
        conn.commit()
        return cur.lastrowid, None
    except TursoError as e:
        if _is_unique_violation(e):
            return None, 'Ya existe una irregularidad con esa KEY.'
        raise
    finally:
        conn.close()


def editar_irregularidad(iid, data, usuario):
    conn = get_conn()
    data['MODIFICADO_POR'] = usuario
    data['FECHA_MODIFICACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join([f'{k}=?' for k in data.keys()])
    conn.execute(f'UPDATE IRREGULARIDADES SET {sets} WHERE id=?', list(data.values()) + [iid])
    conn.commit()
    conn.close()


# ─── INSTALACIONES ────────────────────────────────────
def get_instalacion_by_key(alimentador, cod, conn=None):
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        row = conn.execute(
            'SELECT * FROM INSTALACIONES_TOTAS WHERE ALIMENTADOR=? AND COD_PUNTO_MEDICION=?', (alimentador, cod)
        ).fetchone()
        return dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


def get_instalaciones(alimentador):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM INSTALACIONES_TOTAS
        WHERE ALIMENTADOR=? AND ESTADO_REGISTRO='ALTA'
        ORDER BY COD_PUNTO_MEDICION
    """, (alimentador,)).fetchall()
    conn.close()
    return rows_to_list(rows)


def crear_instalacion(data, usuario):
    conn = get_conn()
    data['CREADO_POR'] = usuario
    data['FECHA_CREACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['ESTADO_REGISTRO'] = 'ALTA'
    cols = ', '.join(data.keys())
    ph = ', '.join(['?'] * len(data))
    try:
        cur = conn.execute(f'INSERT INTO INSTALACIONES_TOTAS ({cols}) VALUES ({ph})', list(data.values()))
        conn.commit()
        return cur.lastrowid, None
    except TursoError as e:
        if _is_unique_violation(e):
            return None, 'Ya existe una instalación para ese ALIMENTADOR + COD_PUNTO_MEDICION.'
        raise
    finally:
        conn.close()


def editar_instalacion(iid, data, usuario):
    conn = get_conn()
    data['MODIFICADO_POR'] = usuario
    data['FECHA_MODIFICACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join([f'{k}=?' for k in data.keys()])
    conn.execute(f'UPDATE INSTALACIONES_TOTAS SET {sets} WHERE id=?', list(data.values()) + [iid])
    conn.commit()
    conn.close()


# ─── LECTURAS ─────────────────────────────────────────
def get_lectura_by_key(alimentador, cod, periodo):
    conn = get_conn()
    row = conn.execute(
        'SELECT * FROM LECTURAS WHERE ALIMENTADOR=? AND COD_PUNTO_MEDICION=? AND PERIODO=?', (alimentador, cod, periodo)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_lecturas(alimentador):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM LECTURAS
        WHERE ALIMENTADOR=? AND ESTADO_REGISTRO='ALTA'
        ORDER BY COD_PUNTO_MEDICION, PERIODO
    """, (alimentador,)).fetchall()
    conn.close()
    return rows_to_list(rows)


def crear_lectura(data, usuario):
    conn = get_conn()
    data['CREADO_POR'] = usuario
    data['FECHA_CREACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['ESTADO_REGISTRO'] = 'ALTA'
    cols = ', '.join(data.keys())
    ph = ', '.join(['?'] * len(data))
    try:
        cur = conn.execute(f'INSERT INTO LECTURAS ({cols}) VALUES ({ph})', list(data.values()))
        conn.commit()
        return cur.lastrowid, None
    except TursoError as e:
        if _is_unique_violation(e):
            return None, 'Ya existe una lectura para ese ALIMENTADOR + SED + PERIODO.'
        raise
    finally:
        conn.close()


def editar_lectura(lid, data, usuario):
    conn = get_conn()
    data['MODIFICADO_POR'] = usuario
    data['FECHA_MODIFICACION'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join([f'{k}=?' for k in data.keys()])
    conn.execute(f'UPDATE LECTURAS SET {sets} WHERE id=?', list(data.values()) + [lid])
    conn.commit()
    conn.close()


# ─── DASHBOARD KPIs ───────────────────────────────────
def get_kpis():
    conn = get_conn()
    kpis = {}
    kpis['total_alimentadores'] = conn.execute("SELECT COUNT(*) FROM ALIMENTADORES WHERE ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['mt_cerrado'] = conn.execute("SELECT COUNT(*) FROM ALIMENTADORES WHERE ESTADO_TRABAJO_MT='CERRADO' AND ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['mt_en_curso'] = conn.execute("SELECT COUNT(*) FROM ALIMENTADORES WHERE ESTADO_TRABAJO_MT='EN CURSO' AND ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['mt_por_trabajar'] = conn.execute("SELECT COUNT(*) FROM ALIMENTADORES WHERE ESTADO_TRABAJO_MT='POR TRABAJAR' AND ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['bt_cerrado'] = conn.execute("SELECT COUNT(*) FROM ALIMENTADORES WHERE ESTADO_TRABAJO_BT='CERRADO' AND ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['bt_en_curso'] = conn.execute("SELECT COUNT(*) FROM ALIMENTADORES WHERE ESTADO_TRABAJO_BT='EN CURSO' AND ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['total_sospechas_mt'] = conn.execute("SELECT COUNT(*) FROM SOSPECHAS_MT WHERE ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['total_sospechas_bt'] = conn.execute("SELECT COUNT(*) FROM SOSPECHAS_BT WHERE ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['total_irregularidades'] = conn.execute("SELECT COUNT(*) FROM IRREGULARIDADES WHERE ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['total_instalaciones'] = conn.execute("SELECT COUNT(*) FROM INSTALACIONES_TOTAS WHERE ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['instaladas'] = conn.execute("SELECT COUNT(*) FROM INSTALACIONES_TOTAS WHERE ESTADO_INSTALACION='INSTALADO' AND ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['total_lecturas'] = conn.execute("SELECT COUNT(*) FROM LECTURAS WHERE ESTADO_REGISTRO='ALTA'").fetchone()[0]
    kpis['lecturas_efectivas'] = conn.execute("SELECT COUNT(*) FROM LECTURAS WHERE ESTADO_LECTURA IN ('EFECTIVO LECTURA','EFECTIVO PINZADO') AND ESTADO_REGISTRO='ALTA'").fetchone()[0]
    conn.close()
    return kpis


# ─── DASHBOARD ────────────────────────────────────────
def get_dashboard_nodos_por_actividad(meses):
    """Pie: SOSPECHAS_MT agrupado por ESTADO_ACTIVIDAD para alimentadores con ESTADO_ANALISIS_CSG=CERRADO."""
    if not meses:
        return {}
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    rows = conn.execute(f"""
        SELECT s.ESTADO_ACTIVIDAD, COUNT(*) c
        FROM SOSPECHAS_MT s
        JOIN ALIMENTADORES a ON UPPER(s.ALIMENTADOR)=UPPER(a.ALIMENTADOR)
        WHERE a.MES_PLANIFICADO IN ({ph}) AND a.ESTADO_REGISTRO='ALTA'
        AND UPPER(a.ESTADO_ANALISIS_CSG)='CERRADO'
        GROUP BY s.ESTADO_ACTIVIDAD ORDER BY c DESC
    """, list(meses)).fetchall()
    conn.close()
    result = {}
    for act, cnt in rows:
        key = act.strip() if (act and str(act).strip()) else 'EN PROCESO DE VALIDACION'
        result[key] = result.get(key, 0) + cnt
    return result


def get_dashboard_alimentadores_asignados_insp(meses):
    """Lista de ALIMENTADOR distintos con ESTADO_ANALISIS_CSG=CERRADO y ESTADO_ACTIVIDAD=ASIGNADO INSP MT."""
    if not meses:
        return []
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    rows = conn.execute(f"""
        SELECT DISTINCT s.ALIMENTADOR
        FROM SOSPECHAS_MT s
        JOIN ALIMENTADORES a ON UPPER(s.ALIMENTADOR)=UPPER(a.ALIMENTADOR)
        WHERE a.MES_PLANIFICADO IN ({ph}) AND a.ESTADO_REGISTRO='ALTA'
        AND UPPER(a.ESTADO_ANALISIS_CSG)='CERRADO'
        AND UPPER(s.ESTADO_ACTIVIDAD)='ASIGNADO INSP MT'
        ORDER BY s.ALIMENTADOR
    """, list(meses)).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_dashboard_estados_nodos_insp(meses):
    """Tabla: ESTADO_INSP de SOSPECHAS_MT donde ESTADO_ACTIVIDAD=ASIGNADO INSP MT y ESTADO_ANALISIS_CSG=CERRADO."""
    if not meses:
        return {}
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    rows = conn.execute(f"""
        SELECT s.ESTADO_INSP, COUNT(*) c
        FROM SOSPECHAS_MT s
        JOIN ALIMENTADORES a ON UPPER(s.ALIMENTADOR)=UPPER(a.ALIMENTADOR)
        WHERE a.MES_PLANIFICADO IN ({ph}) AND a.ESTADO_REGISTRO='ALTA'
        AND UPPER(a.ESTADO_ANALISIS_CSG)='CERRADO'
        AND UPPER(s.ESTADO_ACTIVIDAD)='ASIGNADO INSP MT'
        GROUP BY s.ESTADO_INSP ORDER BY c DESC
    """, list(meses)).fetchall()
    conn.close()
    return {(r[0] or 'SIN ESTADO'): r[1] for r in rows}


def get_dashboard_sed_data(meses):
    """SED IMPEDIMENTOS y SED INSTALADOS desde INSTALACIONES_TOTAS donde ESTADO_CONTROL=CERRADO CON IMP."""
    if not meses:
        return {'imp': 0, 'inst': 0}
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    rows = conn.execute(f"""
        SELECT ESTADO_INSTALACION, COUNT(*) c
        FROM INSTALACIONES_TOTAS
        WHERE UPPER(ESTADO_CONTROL)='CERRADO CON IMP'
        AND MES_PLANIFICADO IN ({ph})
        GROUP BY ESTADO_INSTALACION
    """, list(meses)).fetchall()
    conn.close()
    result = {'imp': 0, 'inst': 0}
    for estado, cnt in rows:
        e = (estado or '').upper()
        if 'IMPED' in e:
            result['imp'] += cnt
        elif 'INSTAL' in e:
            result['inst'] += cnt
    return result


def get_dashboard_clientes_cerrado_con_imp(meses):
    """SUM(N_SEDS + CLIENTES_MAX_MT + CLIENTES_LIB_PEAJES + CLIENTES_NO_UBI)
    desde ALIMENTADORES donde ESTADO_INST_TOTAS=CERRADO CON IMP."""
    if not meses:
        return 0
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    r = conn.execute(f"""
        SELECT SUM(
            COALESCE(N_SEDS, 0) + COALESCE(CLIENTES_MAX_MT, 0) +
            COALESCE(CLIENTES_LIB_PEAJES, 0) + COALESCE(CLIENTES_NO_UBI, 0)
        ) FROM ALIMENTADORES
        WHERE MES_PLANIFICADO IN ({ph}) AND ESTADO_REGISTRO='ALTA'
        AND UPPER(ESTADO_INST_TOTAS)='CERRADO CON IMP'
    """, list(meses)).fetchone()
    conn.close()
    return (r[0] or 0) if r else 0


def get_dashboard_meses():
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT MES_PLANIFICADO FROM ALIMENTADORES "
        "WHERE MES_PLANIFICADO IS NOT NULL AND ESTADO_REGISTRO='ALTA' "
        "ORDER BY MES_PLANIFICADO"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]


def get_dashboard_kpis(meses):
    """meses: list of 'YYYY-MM-DD' strings (one or more)."""
    empty = {'planificado': 0, 'nodos': 0, 'pinzado': 0, 'analisis': 0,
             'inspecciones': 0, 'lecturas': 0, 'inst_cerrado': 0,
             'inst_con_imp': 0, 'inst_total': 0, 'inst_en_curso': 0}
    if not meses:
        return empty
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    vals = list(meses)

    def cnt(extra=''):
        sql = (f"SELECT COUNT(*) FROM ALIMENTADORES "
               f"WHERE MES_PLANIFICADO IN ({ph}) AND ESTADO_REGISTRO='ALTA'"
               + (f' {extra}' if extra else ''))
        r = conn.execute(sql, vals).fetchone()
        return (r[0] or 0) if r else 0

    planificado = cnt()
    nodos = cnt("AND UPPER(PLANO_NODOS)='SI'")
    pinzado = cnt("AND UPPER(ESTADO_PINZADO)='FINALIZADO'")
    analisis = cnt("AND UPPER(ESTADO_ANALISIS_CSG)='CERRADO'")
    lecturas = cnt("AND UPPER(ESTADO_LECTURAS)='CERRADO'")
    inst_cerrado = cnt("AND UPPER(ESTADO_INST_TOTAS)='CERRADO'")
    inst_con_imp = cnt("AND UPPER(ESTADO_INST_TOTAS)='CERRADO CON IMP'")
    inst_total = cnt("AND UPPER(ESTADO_INST_TOTAS) IN ('CERRADO','CERRADO CON IMP')")
    inst_en_curso = cnt("AND UPPER(ESTADO_INST_TOTAS)='EN CURSO'")

    r = conn.execute(f"""
        SELECT COUNT(DISTINCT a.ALIMENTADOR) FROM ALIMENTADORES a
        WHERE a.MES_PLANIFICADO IN ({ph}) AND a.ESTADO_REGISTRO='ALTA'
        AND UPPER(a.ESTADO_ANALISIS_CSG)='CERRADO'
        AND EXISTS (
            SELECT 1 FROM SOSPECHAS_BT b
            WHERE UPPER(b.ALIMENTADOR)=UPPER(a.ALIMENTADOR)
            AND UPPER(b.ESTADO_ACTIVIDAD)='ASIGNADO INSP'
        )
    """, vals).fetchone()
    insp = (r[0] or 0) if r else 0

    conn.close()
    return {
        'planificado': planificado,
        'nodos': nodos,
        'pinzado': pinzado,
        'analisis': analisis,
        'inspecciones': insp,
        'lecturas': lecturas,
        'inst_cerrado': inst_cerrado,
        'inst_con_imp': inst_con_imp,
        'inst_total': inst_total,
        'inst_en_curso': inst_en_curso,
    }


# ─── Dashboard: "Analisis de alimentadores por nodos BT" ──────────
# Filtro general de esta seccion (2.1-2.3 del pedido): SOSPECHAS_BT con
# ESTADO_ANALISIS_CSG='CERRADO' y ESTADO_ACTIVIDAD='ASIGNADO INSP', mismo
# patron de join a ALIMENTADORES (MES_PLANIFICADO + ESTADO_REGISTRO='ALTA')
# que el resto del Dashboard, para que el filtro global de meses aplique
# igual aqui.
_BT_JOIN_WHERE = """
    FROM SOSPECHAS_BT b
    JOIN ALIMENTADORES a ON UPPER(b.ALIMENTADOR)=UPPER(a.ALIMENTADOR)
    WHERE a.MES_PLANIFICADO IN ({ph}) AND a.ESTADO_REGISTRO='ALTA'
    AND UPPER(b.ESTADO_ANALISIS_CSG)='CERRADO'
    AND UPPER(b.ESTADO_ACTIVIDAD)='ASIGNADO INSP'
"""


def get_dashboard_bt_kpis(meses):
    """2.1: Numero de Nodos = DISTINCT COUNT de ALIMENTADOR+NODO (varias
    filas del mismo par cuentan como un solo nodo). Numero de SED = COUNT
    (no distinct) de SED: cada fila existente cuenta."""
    if not meses:
        return {'nodos': 0, 'sed': 0}
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    where = _BT_JOIN_WHERE.format(ph=ph)
    r = conn.execute(f"""
        SELECT COUNT(DISTINCT b.ALIMENTADOR || '|' || b.NODO), COUNT(b.SED)
        {where}
    """, list(meses)).fetchone()
    conn.close()
    return {'nodos': (r[0] or 0) if r else 0, 'sed': (r[1] or 0) if r else 0}


def get_dashboard_bt_focalizacion(meses):
    """2.2: 'Analisis por Estado de Focalizacion Nodo/SED' -- Cuenta de SED,
    % Cuenta de SED (participacion sobre el total de la tabla, calculado en
    Python), Suma de Perdida kWh, Suma de Energia kWh Rec/Mes."""
    if not meses:
        return []
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    where = _BT_JOIN_WHERE.format(ph=ph)
    rows = conn.execute(f"""
        SELECT COALESCE(NULLIF(TRIM(b.ESTADO_FOCALIZACION),''),'(sin dato)'),
               COUNT(b.SED), SUM(b.PERDIDA_KWH), SUM(b.ENERGIA_KWH_REC_MES)
        {where}
        GROUP BY 1 ORDER BY 2 DESC
    """, list(meses)).fetchall()
    conn.close()
    data = [{'estado': r[0], 'cuenta_sed': r[1] or 0,
             'perdida_kwh': r[2] or 0, 'energia_rec_mes': r[3] or 0} for r in rows]
    total_sed = sum(d['cuenta_sed'] for d in data) or 1
    for d in data:
        d['pct_sed'] = d['cuenta_sed'] / total_sed * 100
    return data


def get_dashboard_bt_status_conteo(meses):
    """2.3: 'Analisis por Status de Conteo SED' -- Conteo de SED, Suma de
    Perdida kWh, Suma de Energia kWh Rec/Mes, mas fila de total general."""
    if not meses:
        return [], {'conteo': 0, 'perdida_kwh': 0, 'energia_rec_mes': 0}
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    where = _BT_JOIN_WHERE.format(ph=ph)
    rows = conn.execute(f"""
        SELECT COALESCE(NULLIF(TRIM(b.STATUS_CONTEO_SED),''),'(sin dato)'),
               COUNT(b.SED), SUM(b.PERDIDA_KWH), SUM(b.ENERGIA_KWH_REC_MES)
        {where}
        GROUP BY 1 ORDER BY 2 DESC
    """, list(meses)).fetchall()
    conn.close()
    data = [{'status': r[0], 'conteo': r[1] or 0,
             'perdida_kwh': r[2] or 0, 'energia_rec_mes': r[3] or 0} for r in rows]
    total = {
        'conteo': sum(d['conteo'] for d in data),
        'perdida_kwh': sum(d['perdida_kwh'] for d in data),
        'energia_rec_mes': sum(d['energia_rec_mes'] for d in data),
    }
    return data, total


def get_dashboard_irregularidades_bt(meses):
    """Tabla v1 'Analisis de irregularidades BT' (por SED/cliente) --
    redefinida por completo (reemplaza la version anterior de esta funcion,
    que filtraba distinto). IRREGULARIDADES con TENSION='BT' o TENSION
    vacia (ambos casos incluidos), agrupado por ESTADO_CNR limitado a
    'NO PROCEDE' y 'VALORIZADO' (se excluye cualquier otro valor). Cuenta
    de COD_PUNTO_MEDICION (mostrado en el dashboard como 'SED_CLIENTE_MT' --
    es un rename de presentacion, la columna real sigue siendo
    COD_PUNTO_MEDICION; 'SED/CLIENTE MT' del Excel ya se migraba ahi, ver
    app/2_migrar_datos.py), y suma de RECUPERO_MWH."""
    if not meses:
        return []
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    rows = conn.execute(f"""
        SELECT i.ESTADO_CNR, COUNT(i.COD_PUNTO_MEDICION), SUM(i.RECUPERO_MWH)
        FROM IRREGULARIDADES i
        JOIN ALIMENTADORES a ON UPPER(i.ALIMENTADOR)=UPPER(a.ALIMENTADOR)
        WHERE a.MES_PLANIFICADO IN ({ph}) AND a.ESTADO_REGISTRO='ALTA'
        AND (UPPER(i.TENSION)='BT' OR i.TENSION IS NULL OR TRIM(i.TENSION)='')
        AND UPPER(i.ESTADO_CNR) IN ('NO PROCEDE', 'VALORIZADO')
        GROUP BY 1
    """, list(meses)).fetchall()
    conn.close()
    return [{'estado_cnr': r[0], 'sed_cliente_mt': r[1] or 0,
             'recupero_mwh': r[2] or 0} for r in rows]


def get_dashboard_irregularidades_alimentador(meses):
    """Tabla v2 'Analisis de irregularidades BT' (por alimentador) --
    IRREGULARIDADES con TIPO_CLIENTE='SED' o TIPO_CLIENTE vacio (ambos
    casos incluidos), pivotado ALIMENTADOR (filas) x ESTADO_CNR (columnas,
    SIN restringir a una lista fija -- a diferencia de la v1, aca se
    muestran todos los valores de ESTADO_CNR que existan en los datos).
    Conteo de SUM_CLIENTE y suma de RECUPERO_MWH por celda."""
    if not meses:
        return {}
    conn = get_conn()
    ph = ','.join(['?'] * len(meses))
    rows = conn.execute(f"""
        SELECT i.ALIMENTADOR, i.ESTADO_CNR, COUNT(i.SUM_CLIENTE), SUM(i.RECUPERO_MWH)
        FROM IRREGULARIDADES i
        JOIN ALIMENTADORES a ON UPPER(i.ALIMENTADOR)=UPPER(a.ALIMENTADOR)
        WHERE a.MES_PLANIFICADO IN ({ph}) AND a.ESTADO_REGISTRO='ALTA'
        AND (UPPER(i.TIPO_CLIENTE)='SED' OR i.TIPO_CLIENTE IS NULL OR TRIM(i.TIPO_CLIENTE)='')
        GROUP BY i.ALIMENTADOR, i.ESTADO_CNR
        ORDER BY i.ALIMENTADOR
    """, list(meses)).fetchall()
    conn.close()
    pivot = {}
    for alim, estado, cnt, suma in rows:
        estado_label = estado if (estado and str(estado).strip()) else '(sin dato)'
        pivot.setdefault(alim, {})[estado_label] = {'conteo': cnt or 0, 'recupero_mwh': suma or 0}
    return pivot


# ─── USUARIOS (login web) ─────────────────────────────
# Reemplaza a app/config/usuarios.json de la app de escritorio (que no
# tenia contrasena, confiaba en el usuario de Windows) -- ver Fase 3 del
# plan de migracion.
def get_usuarios(solo_activos=False):
    conn = get_conn()
    q = "SELECT * FROM usuarios"
    if solo_activos:
        q += " WHERE activo=1"
    q += " ORDER BY username"
    rows = conn.execute(q).fetchall()
    conn.close()
    return rows_to_list(rows)


def get_usuario_by_username(username):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE username=? COLLATE NOCASE", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def crear_usuario(username, nombre, rol, password_hash):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO usuarios (username, nombre, rol, password_hash) VALUES (?,?,?,?)",
            (username, nombre, rol, password_hash))
        conn.commit()
        return cur.lastrowid, None
    except TursoError as e:
        if _is_unique_violation(e):
            return None, f'Ya existe un usuario con ese nombre de usuario: {username}'
        raise
    finally:
        conn.close()


def actualizar_password(username, password_hash):
    conn = get_conn()
    conn.execute(
        "UPDATE usuarios SET password_hash=? WHERE username=? COLLATE NOCASE",
        (password_hash, username))
    conn.commit()
    conn.close()


def actualizar_usuario(username, nombre=None, rol=None, activo=None):
    conn = get_conn()
    sets, vals = [], []
    if nombre is not None:
        sets.append('nombre=?'); vals.append(nombre)
    if rol is not None:
        sets.append('rol=?'); vals.append(rol)
    if activo is not None:
        sets.append('activo=?'); vals.append(1 if activo else 0)
    if sets:
        vals.append(username)
        conn.execute(f"UPDATE usuarios SET {', '.join(sets)} WHERE username=? COLLATE NOCASE", vals)
        conn.commit()
    conn.close()


# ─── PERMISOS POR PAGINA/USUARIO ───────────────────────
def get_permisos_usuario(usuario_id):
    """{pagina_id: nivel_acceso} para un usuario -- paginas sin fila no
    aparecen en el dict (el default 'ninguno' lo aplica el caller, ver
    core.auth.get_permiso)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT pagina_id, nivel_acceso FROM permisos_usuario WHERE usuario_id=?",
        (usuario_id,)).fetchall()
    conn.close()
    return {r['pagina_id']: r['nivel_acceso'] for r in rows}


def set_permisos_usuario(usuario_id, permisos):
    """permisos: {pagina_id: nivel_acceso}. Upsert de todas las paginas de
    una sola vez (pedido explicito: un unico submit, no un UPDATE por
    fila) -- borra las filas del usuario y reinserta, mas simple y
    equivalente a un upsert masivo para esta tabla chica."""
    conn = get_conn()
    conn.execute("DELETE FROM permisos_usuario WHERE usuario_id=?", (usuario_id,))
    for pagina_id, nivel in permisos.items():
        conn.execute(
            "INSERT INTO permisos_usuario (usuario_id, pagina_id, nivel_acceso) VALUES (?,?,?)",
            (usuario_id, pagina_id, nivel))
    conn.commit()
    conn.close()


# ─── LOG ──────────────────────────────────────────────
def _log(conn, tabla, reg_id, accion, desc, usuario):
    try:
        conn.execute(
            'INSERT INTO LOG_ACCIONES (tabla, registro_id, accion, descripcion, usuario) VALUES (?,?,?,?,?)',
            (tabla, reg_id, accion, desc, usuario)
        )
    except Exception:
        pass
