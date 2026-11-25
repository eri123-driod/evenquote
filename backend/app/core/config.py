"""Configuración del backend (lee el archivo .env)."""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_HORAS = 12

if not DATABASE_URL:
    raise RuntimeError(
        "Falta DATABASE_URL en backend/.env (copia .env.example como .env y pon tu contraseña de MySQL)."
    )
if not SECRET_KEY or len(SECRET_KEY) < 16:
    raise RuntimeError(
        "Falta SECRET_KEY en backend/.env o es muy corta (mínimo 16 caracteres)."
    )
