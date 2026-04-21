"""Frontend Module."""

import json

import requests
import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Web Assistant", page_icon="🤖")
st.title("🤖 Web Assistant")

# URLs del backend
BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
CHAT_URL = f"{BASE_URL}/chatbot/chat"

# Inicializar estado de sesión
if "token" not in st.session_state:
    st.session_state.token = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Pestañas para Login y Chat ---
tab1, tab2 = st.tabs(["🔐 Autenticación", "💬 Chat"])

with tab1:
    st.header("Iniciar Sesión / Registro")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        try:
            # Nota: Ajusta esto según cómo espere los datos tu endpoint de login.
            # Usualmente es JSON: {"username": "...", "password": "..."}
            response = requests.post(LOGIN_URL, data={"email": username, "password": password})

            if response.status_code == 200:
                data = response.json()
                # Asumiendo que el token viene en 'access_token' o similar.
                # Revisa en /docs qué devuelve exactamente /auth/login
                st.session_state.token = data.get("access_token") or data.get("token")
                st.success("¡Autenticado con éxito!")
                st.rerun()
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Error de conexión: {str(e)}")

with tab2:
    if not st.session_state.token:
        st.warning("⚠️ Por favor, autentícate en la pestaña 'Autenticación' primero.")
    else:
        # Mostrar historial
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Input del usuario
        if prompt := st.chat_input("Escribe tu mensaje aquí..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""

                try:
                    # Preparar headers con el token
                    headers = {"Authorization": f"Bearer {st.session_state.token}", "Content-Type": "application/json"}

                    # Estructura del mensaje para LangGraph/FastAPI
                    # Ajusta 'messages' según lo que espere ChatRequest en el backend
                    payload = {"messages": [{"role": "user", "content": prompt}]}

                    response = requests.post(CHAT_URL, json=payload, headers=headers)

                    if response.status_code == 200:
                        data = response.json()
                        # Ajusta esto según la respuesta de ChatResponse
                        # Usualmente devuelve una lista de mensajes o un objeto con 'messages'
                        assistant_msg = data.get("messages", [])[-1].get("content", str(data))

                        message_placeholder.markdown(assistant_msg)
                        st.session_state.messages.append({"role": "assistant", "content": assistant_msg})
                    else:
                        st.error(f"Error del servidor: {response.status_code} - {response.text}")

                except Exception as e:
                    st.error(f"Error de conexión: {str(e)}")
