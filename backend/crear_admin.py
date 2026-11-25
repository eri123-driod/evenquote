"""Inicialización documentada del PRIMER administrador (se ejecuta una sola vez).

Usa exactamente las mismas reglas que el resto del sistema:
  * mismas validaciones de nombre/correo/contraseña (app/models/schemas.py)
  * misma función de hash: Argon2id (app/core/security.py)
Uso:  python crear_admin.py     (Enter x3 acepta los valores por defecto)
"""
import sys

from pydantic import ValidationError
from sqlalchemy import text

from app.core.database import engine
from app.core.security import hash_password
from app.models.schemas import RegisterRequest


def crear_admin():
    nombre = input("Nombre del Administrador [Admin Principal]: ").strip() or "Admin Principal"
    email = input("Correo del Administrador [admin@eventquote.com]: ").strip() or "admin@eventquote.com"
    password = input("Contraseña [Admin123!]: ").strip() or "Admin123!"

    try:
        datos = RegisterRequest(nombre=nombre, email=email, password=password)
    except ValidationError as exc:
        print("Datos inválidos:")
        for e in exc.errors():
            print(f" - {'.'.join(str(x) for x in e['loc'])}: {e['msg']}")
        sys.exit(1)

    correo = datos.email.lower()
    hashed = hash_password(datos.password)
    with engine.begin() as conn:
        existe = conn.execute(text("SELECT id FROM usuarios WHERE email = :e"), {"e": correo}).first()
        if existe:
            conn.execute(
                text("UPDATE usuarios SET rol = 'admin', password_hash = :p WHERE email = :e"),
                {"p": hashed, "e": correo},
            )
            print(f"Usuario existente {correo} actualizado a Administrador.")
        else:
            conn.execute(
                text("INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (:n, :e, :p, 'admin')"),
                {"n": datos.nombre, "e": correo, "p": hashed},
            )
            print(f"Administrador creado exitosamente: {correo}")


if __name__ == "__main__":
    crear_admin()
