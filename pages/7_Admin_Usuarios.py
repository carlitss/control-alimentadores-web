"""
Pagina Admin Usuarios — solo ADMIN. Alta de usuarios, reseteo de clave,
cambio de rol y activo/inactivo. Reemplaza a app/config/usuarios.json de
la app de escritorio (ver Fase 3 del plan de migracion).
"""
import bcrypt
import streamlit as st
import core.auth as auth
import core.db as db

auth.require_login()
auth.require_pagina('admin_usuarios', para_editar=True)

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

st.divider()
st.subheader('Permisos por página')

if not usuarios:
    st.info('Creá al menos un usuario primero.')
else:
    sel_permisos = st.selectbox('Usuario', [u['username'] for u in usuarios], key='sel_permisos')
    usuario_permisos = next(u for u in usuarios if u['username'] == sel_permisos)
    permisos_actuales = db.get_permisos_usuario(usuario_permisos['id'])

    def _aplicar_a_todas():
        """on_change de 'Aplicar a todas': pre-carga el mismo nivel en el
        session_state de cada radio ANTES de que la matriz se vuelva a
        dibujar -- asi el admin puede fijar un nivel comun de una vez y
        despues ajustar excepciones fila por fila, sin tener que marcar
        pagina por pagina el caso comun."""
        nivel = st.session_state.get('aplicar_todas_sel')
        if nivel == '(sin cambio masivo)':
            return
        uid = next(u for u in usuarios if u['username'] == st.session_state['sel_permisos'])['id']
        for pagina in auth.PAGINAS:
            st.session_state[f'perm_{uid}_{pagina["id"]}'] = nivel

    st.selectbox(
        'Aplicar a todas las páginas',
        ['(sin cambio masivo)'] + auth.NIVELES_ACCESO,
        format_func=lambda n: n if n == '(sin cambio masivo)' else auth._NIVEL_LABEL[n],
        key='aplicar_todas_sel', on_change=_aplicar_a_todas,
    )

    with st.form('form_permisos'):
        nuevos_permisos = {}
        for pagina in auth.PAGINAS:
            widget_key = f'perm_{usuario_permisos["id"]}_{pagina["id"]}'
            default_nivel = permisos_actuales.get(pagina['id'], 'ninguno')
            if widget_key not in st.session_state:
                st.session_state[widget_key] = default_nivel
            nuevos_permisos[pagina['id']] = st.radio(
                pagina['label'], auth.NIVELES_ACCESO,
                format_func=lambda n: auth._NIVEL_LABEL[n],
                horizontal=True, key=widget_key,
            )
        guardar_permisos = st.form_submit_button('Guardar permisos', type='primary')

    if guardar_permisos:
        db.set_permisos_usuario(usuario_permisos['id'], nuevos_permisos)
        if usuario_permisos['id'] == st.session_state.get('usuario_id'):
            st.session_state.pop('permisos', None)
        st.success(f'Permisos de "{sel_permisos}" actualizados.')
        st.rerun()
