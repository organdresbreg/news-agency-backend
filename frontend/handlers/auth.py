"""Manejo de autenticación y gestión de usuarios."""

from typing import Optional

import chainlit as cl
import requests

BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
SESSION_URL = f"{BASE_URL}/auth/session"


async def authenticate_user(username: str, password: str) -> Optional[str]:
    """Maneja la autenticación contra el backend de la API."""
    try:
        response = requests.post(LOGIN_URL, data={"email": username, "password": password})

        if response.status_code == 200:
            data = response.json()
            user_token = data.get("access_token") or data.get("token")

            session_response = requests.post(SESSION_URL, headers={"Authorization": f"Bearer {user_token}"})

            if session_response.status_code == 200:
                session_data = session_response.json()
                token = session_data["token"]["access_token"]
                return token
            else:
                print(f"Error session: {session_response.status_code} - {session_response.text}")
                return None
        else:
            print(f"Error login: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Auth Exception: {e}")
        return None
