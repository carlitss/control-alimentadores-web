"""
auth.py — Login y control de roles para la app web.

Reemplaza a la logica de Auth en app/main.py (que confiaba en el usuario
de Windows via getpass.getuser() contra app/config/usuarios.json, sin
contrasena -- eso no existe en un navegador). Aca:

  - streamlit-authenticator hace SOLO la autenticacion (verificar
    usuario+contrasena, cookie de sesion) -- nunca se le pide que maneje
    roles: la tabla `usuarios` en Turso es la unica fuente de verdad para
    el rol de cada quien, y `puede()` es la MISMA logica de permisos que
    ya tenia la app de escritorio (main.py, clase Auth), copiada tal cual.

  - El permiso se revisa DOS veces para cualquier accion que escribe en
    la base: una vez para decidir si se muestra/habilita el control, y
    otra vez justo antes de ejecutar la escritura -- un widget
    deshabilitado en Streamlit es solo una pista visual del lado del
    cliente, no una barrera real (cualquiera que sepa la URL de un
    callback podria intentar dispararlo igual).
"""
import streamlit as st
import streamlit_authenticator as stauth
import core.db as db

_PERMISOS = {
    'ADMIN':    {'ver', 'insertar', 'modificar', 'baja', 'admin'},
    'EDITOR':   {'ver', 'insertar', 'modificar'},
    'CONSULTA': {'ver'},
}


def puede(rol, accion):
    return accion in _PERMISOS.get(rol or '', set())


# ─── Permisos granulares por pagina/usuario ────────────
# Capa nueva, agregada junto al `rol` de arriba (no lo reemplaza): `rol`
# sigue siendo la identidad/etiqueta que se muestra, pero el acceso real a
# cada pagina (que aparezca en el menu, y si se puede editar o solo ver)
# pasa por esta lista + la tabla `permisos_usuario`. Agregar una pagina
# nueva a la app es agregarla ACA -- todo lo demas (menu dinamico, matriz
# de administracion) sale de esta lista, no hay nada mas hardcodeado.
PAGINAS = [
    {'id': 'dashboard',       'label': 'Dashboard',        'path': 'pages/0_Dashboard.py'},
    {'id': 'alimentadores',   'label': 'Alimentadores',    'path': 'pages/1_Alimentadores.py'},
    {'id': 'sospecha_mt',     'label': 'Sospecha MT',      'path': 'pages/2_Sospecha_MT.py'},
    {'id': 'sospecha_bt',     'label': 'Sospecha BT',      'path': 'pages/3_Sospecha_BT.py'},
    {'id': 'irregularidades', 'label': 'Irregularidades',  'path': 'pages/4_Irregularidades.py'},
    {'id': 'instalaciones',   'label': 'Instalaciones',    'path': 'pages/5_Instalaciones.py'},
    {'id': 'lecturas',        'label': 'Lecturas',         'path': 'pages/6_Lecturas.py'},
    {'id': 'admin_usuarios',  'label': 'Admin Usuarios',   'path': 'pages/7_Admin_Usuarios.py'},
]
NIVELES_ACCESO = ['ninguno', 'lectura', 'edicion']
_NIVEL_LABEL = {'ninguno': 'Sin acceso', 'lectura': 'Solo lectura', 'edicion': 'Editar'}


def get_permiso(pagina_id):
    """Nivel de acceso del usuario logueado a `pagina_id`
    ('ninguno'|'lectura'|'edicion'). Default 'ninguno' si no hay fila --
    principio de menor privilegio para paginas/usuarios sin permiso
    explicito. Cachea la consulta en session_state (se invalida al
    volver a loguear o al guardar cambios en Admin Usuarios) para no
    repetir el SELECT en cada rerun de Streamlit."""
    usuario_id = st.session_state.get('usuario_id')
    if usuario_id is None:
        return 'ninguno'
    if 'permisos' not in st.session_state:
        st.session_state['permisos'] = db.get_permisos_usuario(usuario_id)
    return st.session_state['permisos'].get(pagina_id, 'ninguno')


def require_pagina(pagina_id, para_editar=False):
    """Gate real (backend) de una pagina -- llamar justo despues de
    require_login() en cada pagina, y de nuevo con para_editar=True antes
    de cualquier escritura (mismo patron de doble chequeo que
    require_permiso). Corta con st.stop() si no corresponde: cubre tanto
    el caso de acceso directo por URL a una pagina sin permiso, como el
    intento de escritura con permiso de solo lectura."""
    nivel = get_permiso(pagina_id)
    if nivel == 'ninguno':
        st.error('No tenés acceso a esta página. Contactá a un administrador.')
        st.stop()
    if para_editar and nivel != 'edicion':
        st.error('Tu acceso a esta página es de solo lectura.')
        st.stop()


def _build_credentials():
    """Arma el dict {'usernames': {...}} que espera streamlit-authenticator,
    a partir de la tabla usuarios de Turso -- las contrasenas YA estan
    hasheadas con bcrypt en la base (nunca en texto plano), por eso
    auto_hash=False al crear Authenticate: no hace falta que la libreria
    las re-hashee ni las inspeccione en cada rerun."""
    usuarios = db.get_usuarios(solo_activos=True)
    usernames = {}
    for u in usuarios:
        usernames[u['username'].lower()] = {
            'name': u.get('nombre') or u['username'],
            'password': u['password_hash'],
            'email': f"{u['username']}@local",
        }
    return {'usernames': usernames}


def get_authenticator():
    if 'authenticator' not in st.session_state:
        credentials = _build_credentials()
        st.session_state['authenticator'] = stauth.Authenticate(
            credentials,
            cookie_name='control_alimentadores_auth',
            cookie_key=st.secrets.get('AUTH_COOKIE_KEY', 'cambiar-esta-clave'),
            cookie_expiry_days=7,
            auto_hash=False,
        )
    return st.session_state['authenticator']


def require_login():
    """Renderiza el formulario de login si hace falta y detiene la
    ejecucion de la pagina hasta que el usuario se autentique. Si ya esta
    autenticado, completa st.session_state['rol'] desde la tabla usuarios
    (no desde streamlit-authenticator) y sigue de largo sin bloquear."""
    authenticator = get_authenticator()
    authenticator.login()

    status = st.session_state.get('authentication_status')
    if status is False:
        st.error('Usuario o contraseña incorrectos.')
        st.stop()
    if status is not True:
        st.info('Ingresa tus credenciales para continuar.')
        st.stop()

    username = st.session_state.get('username')
    if not st.session_state.get('rol'):
        row = db.get_usuario_by_username(username)
        if not row or not row.get('activo'):
            st.error('Tu usuario ya no está activo. Contacta al administrador.')
            st.session_state['authentication_status'] = None
            st.stop()
        st.session_state['rol'] = row['rol']
        st.session_state['nombre'] = row.get('nombre') or username
        st.session_state['usuario_id'] = row['id']

    return username, st.session_state['rol'], st.session_state.get('nombre')


def logout_button(location='sidebar'):
    authenticator = get_authenticator()
    authenticator.logout('Cerrar sesión', location=location)


def require_permiso(accion, mensaje=None):
    """Re-chequeo justo antes de una escritura -- ver nota en el docstring
    del modulo. Corta la ejecucion con un error si el rol actual no
    alcanza; no confiar solo en ocultar/deshabilitar el boton."""
    rol = st.session_state.get('rol')
    if not puede(rol, accion):
        st.error(mensaje or f'Tu rol ({rol}) no tiene permiso para esta acción.')
        st.stop()
