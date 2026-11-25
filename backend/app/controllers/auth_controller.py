"""CONTROLADOR de autenticación: registro, login y perfil."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    HASH_FALSO, crear_token, get_current_user, hash_password, pwd_context, verificar_password,
)
from app.models.schemas import LoginRequest, RegisterRequest, UsuarioPublico

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Alta de CLIENTES. El rol nunca se recibe del cliente: siempre queda como 'cliente'."""
    email = req.email.lower()
    existe = db.execute(text("SELECT id FROM usuarios WHERE email = :e"), {"e": email}).first()
    if existe:
        raise HTTPException(status_code=409, detail="El correo electrónico ya está registrado")
    try:
        db.execute(
            text("INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (:n, :e, :p, 'cliente')"),
            {"n": req.nombre.strip(), "e": email, "p": hash_password(req.password)},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El correo electrónico ya está registrado")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo registrar al usuario")
    return {"mensaje": "Usuario cliente registrado exitosamente"}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    fila = db.execute(
        text("SELECT id, nombre, email, rol, password_hash FROM usuarios WHERE email = :e"),
        {"e": req.email.lower()},
    ).mappings().first()

    if fila is None:
        pwd_context.verify(req.password, HASH_FALSO)  # mismo tiempo de respuesta
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    if not verificar_password(req.password, fila["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    try:
        usuario = UsuarioPublico.model_validate(dict(fila))
    except ValidationError:
        raise HTTPException(status_code=403, detail="La cuenta tiene datos inválidos. Contacta al administrador.")

    token = crear_token({"sub": str(usuario.id), "rol": usuario.rol})
    return {"access_token": token, "token_type": "bearer", "user": usuario.model_dump()}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
