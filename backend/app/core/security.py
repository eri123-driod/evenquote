"""Contraseñas (Argon2id), tokens JWT y control de acceso por rol."""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM, SECRET_KEY, TOKEN_HORAS
from app.core.database import get_db
from app.models.schemas import UsuarioPublico

# passlib usa Argon2id por defecto (argon2.type = "ID").
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Hash falso para que el login tarde lo mismo exista o no el correo.
HASH_FALSO = pwd_context.hash("contrasena-falsa-para-igualar-tiempos-1")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(plano: str, hash_guardado: str) -> bool:
    try:
        return pwd_context.verify(plano, hash_guardado)
    except Exception:  # hash corrupto o con formato desconocido
        return False


def crear_token(datos: dict) -> str:
    payload = datos.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HORAS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> dict:
    """Identidad y rol salen SIEMPRE de la base de datos, no de lo que diga el cliente."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Sesión expirada o token inválido. Inicia sesión de nuevo.")

    fila = db.execute(
        text("SELECT id, nombre, email, rol FROM usuarios WHERE id = :id"), {"id": user_id}
    ).mappings().first()
    if not fila:
        raise HTTPException(status_code=401, detail="El usuario ya no existe. Inicia sesión de nuevo.")
    try:
        return UsuarioPublico.model_validate(dict(fila)).model_dump()
    except ValidationError:
        raise HTTPException(status_code=401, detail="La cuenta tiene datos inválidos. Contacta al administrador.")


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado: requiere rol Administrador")
    return user
