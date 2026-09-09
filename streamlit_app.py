"""
streamlit_app.py — Entrypoint de la app web: login + navegacion filtrada
por permisos.

Antes esta era la pagina del Dashboard directamente (Streamlit descubria
las demas paginas solo por convencion de carpeta en pages/). Ahora que el
acceso a cada pagina depende del usuario logueado (core.auth.PAGINAS +
tabla permisos_usuario), el menu lateral tiene que armarse a mano por
usuario -- Streamlit no filtra el auto-discovery de pages/ por usuario,
la unica forma soportada es st.navigation() con la lista de paginas
armada en runtime. El Dashboard se movio a pages/0_Dashboard.py para ser
una pagina mas de esa lista, gateada igual que el resto.
"""
import streamlit as st
import core.auth as auth

st.set_page_config(page_title='Control Alimentadores MT', layout='wide')

auth.require_login()

paginas_visibles = [
    st.Page(p['path'], title=p['label'], default=(p['id'] == 'dashboard'))
    for p in auth.PAGINAS
    if auth.get_permiso(p['id']) != 'ninguno'
]

if not paginas_visibles:
    with st.sidebar:
        st.write(f"**{st.session_state.get('nombre')}**")
        st.caption(f"Rol: {st.session_state.get('rol')}")
        auth.logout_button()
    st.warning('Tu usuario no tiene acceso a ninguna página todavía. Contactá a un administrador.')
    st.stop()

pg = st.navigation(paginas_visibles)
pg.run()
