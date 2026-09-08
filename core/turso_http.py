"""
Cliente Turso via API HTTP (protocolo Hrana sobre /v2/pipeline), usando
solo `requests`. Se eligio esta via en vez del paquete oficial `libsql`
porque este ultimo requiere compilar una extension Rust (via maturin) y
en el entorno de desarrollo no hay Visual Studio Build Tools ni permisos
de administrador para instalarlos; ademas, al ser HTTP puro, esta misma
libreria funciona igual en Streamlit Community Cloud sin depender de que
exista un wheel prearmado para la version de Python del hosting.

Expone una interfaz deliberadamente parecida a la de `sqlite3` (conn.execute
-> cursor con .fetchall()/.fetchone()/.lastrowid, filas indexables por
posicion O por nombre de columna como sqlite3.Row) para que el resto del
codigo portado desde app/database.py e app/insert_engine.py necesite el
minimo de cambios posible.
"""
import os
import re
import base64
import requests


def _to_https(url):
    """libsql://xxx.turso.io -> https://xxx.turso.io"""
    return re.sub(r'^libsql://', 'https://', url)


class TursoError(Exception):
    """Reemplaza a sqlite3.IntegrityError / sqlite3.Error en el codigo
    portado. `code` trae el codigo SQLite tal cual lo informa Turso
    (p.ej. 'SQLITE_CONSTRAINT' para violaciones de UNIQUE/NOT NULL)."""
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code


class Row(tuple):
    """Imita a sqlite3.Row: indexable por posicion (row[0]) o por nombre
    de columna (row['ALIMENTADOR']), iterable como tupla de VALORES (no de
    claves, a diferencia de un dict comun) para soportar `a, b = row`, y
    soporta dict(row) porque expone .keys()."""
    def __new__(cls, cols, values):
        obj = super().__new__(cls, values)
        obj._cols = cols
        return obj

    def keys(self):
        return list(self._cols)

    def __getitem__(self, key):
        if isinstance(key, str):
            return tuple.__getitem__(self, self._cols.index(key))
        return tuple.__getitem__(self, key)

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, ValueError, IndexError):
            return default


class Cursor:
    def __init__(self, cols, rows, lastrowid=None, rows_affected=0):
        self._cols = cols
        self._rows = [Row(cols, r) for r in rows]
        self.lastrowid = lastrowid
        self.rowcount = rows_affected

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


def _to_hrana_arg(v):
    if v is None:
        return {'type': 'null'}
    if isinstance(v, bool):
        return {'type': 'integer', 'value': str(int(v))}
    if isinstance(v, int):
        return {'type': 'integer', 'value': str(v)}
    if isinstance(v, float):
        return {'type': 'float', 'value': v}
    if isinstance(v, (bytes, bytearray)):
        return {'type': 'blob', 'base64': base64.b64encode(v).decode('ascii')}
    return {'type': 'text', 'value': str(v)}


def _from_hrana_cell(cell):
    t = cell.get('type')
    if t == 'null':
        return None
    if t == 'integer':
        return int(cell['value'])
    if t == 'float':
        return float(cell['value'])
    if t == 'text':
        return cell['value']
    if t == 'blob':
        return base64.b64decode(cell['base64'])
    return cell.get('value')


class TursoConn:
    """Conexion a una base Turso via HTTP. No hay una conexion TCP
    persistente real (cada .execute() es una llamada HTTP independiente al
    endpoint /v2/pipeline), pero reutiliza un unico requests.Session (keep-
    alive) para evitar el costo de un nuevo handshake TLS en cada llamada
    -- el objetivo practico de "una sola conexion por bulk_upsert" del plan
    de migracion, adaptado a un cliente HTTP en vez de un socket persistente.

    .commit()/.rollback() son no-ops: cada sentencia se aplica y confirma
    de forma sincrona en el propio POST, no hay una transaccion diferida
    del lado del cliente que confirmar o deshacer (a diferencia de
    sqlite3, que por defecto abre una transaccion implicita en la primera
    escritura y la deja pendiente hasta el .commit() explicito)."""

    def __init__(self, database_url, auth_token):
        self.base = _to_https(database_url).rstrip('/')
        self.token = auth_token
        self.session = requests.Session()

    def execute(self, sql, params=()):
        args = [_to_hrana_arg(p) for p in params]
        payload = {'requests': [
            {'type': 'execute', 'stmt': {'sql': sql, 'args': args}},
            {'type': 'close'},
        ]}
        resp = self.session.post(
            f'{self.base}/v2/pipeline',
            headers={'Authorization': f'Bearer {self.token}',
                     'Content-Type': 'application/json'},
            json=payload, timeout=30,
        )
        if resp.status_code != 200:
            raise TursoError(f'HTTP {resp.status_code}: {resp.text}')
        body = resp.json()
        r0 = body['results'][0]
        if r0['type'] == 'error':
            err = r0['error']
            raise TursoError(err.get('message', str(err)), code=err.get('code'))
        res = r0['response']['result']
        cols = [c['name'] for c in res.get('cols', [])]
        rows = [[_from_hrana_cell(c) for c in row] for row in res.get('rows', [])]
        lastrowid = res.get('last_insert_rowid')
        if lastrowid is not None:
            lastrowid = int(lastrowid)
        return Cursor(cols, rows, lastrowid, res.get('affected_row_count', 0))

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.session.close()


def _get_credentials():
    """Busca credenciales primero en st.secrets (app Streamlit real),
    despues en variables de entorno (scripts standalone: spikes, smoke
    tests, migracion) -- asi el mismo core/db.py sirve para ambos casos
    sin depender de que streamlit este instalado/en ejecucion."""
    try:
        import streamlit as st
        return st.secrets['TURSO_DATABASE_URL'], st.secrets['TURSO_AUTH_TOKEN']
    except Exception:
        pass
    url = os.environ.get('TURSO_DATABASE_URL')
    token = os.environ.get('TURSO_AUTH_TOKEN')
    if url and token:
        return url, token
    raise RuntimeError(
        'No se encontraron credenciales de Turso: defina TURSO_DATABASE_URL '
        'y TURSO_AUTH_TOKEN (variables de entorno para scripts, o st.secrets '
        'dentro de la app Streamlit).'
    )


def get_conn():
    url, token = _get_credentials()
    return TursoConn(url, token)
