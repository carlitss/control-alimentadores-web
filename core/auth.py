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
