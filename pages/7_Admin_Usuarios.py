"""
Pagina Admin Usuarios — solo ADMIN. Alta de usuarios, reseteo de clave,
cambio de rol y activo/inactivo. Reemplaza a app/config/usuarios.json de
la app de escritorio (ver Fase 3 del plan de migracion).
"""
import bcrypt
import streamlit as st
import core.auth as auth
import core.db as db

st.set_page_config(page_title='Admin Usuarios — Control Alimentadores MT', layout='wide')
auth.require_login()
auth.require_permiso('admin', 'Solo un administrador puede gestionar usuarios.')

with st.sidebar:
    st.write(f"**{st.session_state.get('nombre')}**")
    st.caption(f"Rol: {st.session_state.get('rol')}")
    auth.logout_button()

st.title('Administración de usuarios')

ROLES = ['ADMIN', 'EDITOR', 'CONSULTA']


def _hash(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


usuarios = db.get_usuarios()

st.subheader('Usuarios existentes')
if usuarios:
    st.dataframe(
        [{'Usuario': u['username'], 'Nombre': u['nombre'], 'Rol': u['rol'],
          'Activo': 'Sí' if u['activo'] else 'No'} for u in usuarios],
        use_container_width=True, hide_index=True,
    )
else:
    st.info('No hay usuarios registrados todavía.')

st.divider()

col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader('Crear usuario nuevo')
    with st.form('form_crear_usuario', clear_on_submit=True):
        n_username = st.text_input('Usuario (para iniciar sesión)')
        n_nombre = st.text_input('Nombre completo')
        n_rol = st.selectbox('Rol', ROLES, index=1)
        n_pass1 = st.text_input('Contraseña', type='password')
        n_pass2 = st.text_input('Confirmar contraseña', type='password')
        crear = st.form_submit_button('Crear usuario')

    if crear:
        if not n_username or not n_nombre or not n_pass1:
            st.error('Usuario, nombre y contraseña son obligatorios.')
        elif n_pass1 != n_pass2:
            st.error('Las contraseñas no coinciden.')
        elif len(n_pass1) < 6:
            st.error('La contraseña debe tener al menos 6 caracteres.')
        else:
            _id, error = db.crear_usuario(n_username.strip(), n_nombre.strip(), n_rol, _hash(n_pass1))
            if error:
                st.error(error)
            else:
                st.success(f'Usuario "{n_username}" creado correctamente.')
                st.rerun()

with col_der:
    st.subheader('Resetear contraseña / editar usuario')
    if usuarios:
        opciones = [u['username'] for u in usuarios]
        sel = st.selectbox('Usuario', opciones, key='sel_editar')
        actual = next(u for u in usuarios if u['username'] == sel)

        with st.form('form_editar_usuario'):
            e_nombre = st.text_input('Nombre completo', value=actual['nombre'] or '')
            e_rol = st.selectbox('Rol', ROLES, index=ROLES.index(actual['rol']))
            e_activo = st.checkbox('Activo', value=bool(actual['activo']))
            st.caption('Dejar en blanco si no querés cambiar la contraseña.')
            e_pass1 = st.text_input('Nueva contraseña', type='password')
            e_pass2 = st.text_input('Confirmar nueva contraseña', type='password')
            guardar = st.form_submit_button('Guardar cambios')

        if guardar:
            if e_pass1 and e_pass1 != e_pass2:
                st.error('Las contraseñas no coinciden.')
            elif e_pass1 and len(e_pass1) < 6:
                st.error('La contraseña debe tener al menos 6 caracteres.')
            elif sel == st.session_state.get('username') and not e_activo:
                st.error('No podés desactivarte a vos mismo.')
            else:
                db.actualizar_usuario(sel, nombre=e_nombre.strip(), rol=e_rol, activo=e_activo)
                if e_pass1:
                    db.actualizar_password(sel, _hash(e_pass1))
                st.success(f'Usuario "{sel}" actualizado correctamente.')
                st.rerun()
    else:
        st.info('Creá al menos un usuario primero.')
