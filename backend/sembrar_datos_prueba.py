"""Crea cuentas y datos de prueba para reproducir la demostración (se puede ejecutar varias veces).

Cuentas (contraseñas guardadas con Argon2id):
  admin    -> admin@eventquote.com    / Admin123!
  cliente  -> cliente1@eventquote.com / Cliente123!
  cliente  -> cliente2@eventquote.com / Cliente123!
Uso:  python sembrar_datos_prueba.py
"""
from datetime import datetime, timedelta

from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.services import ml_service

USUARIOS = [
    ("Admin Principal", "admin@eventquote.com", "Admin123!", "admin"),
    ("Cliente Uno", "cliente1@eventquote.com", "Cliente123!", "cliente"),
    ("Cliente Dos", "cliente2@eventquote.com", "Cliente123!", "cliente"),
]

# (cliente, tipo, ciudad, invitados, horas, servicios)
EVENTOS = [
    ("cliente1@eventquote.com", "boda", "Queretaro", 140, 6, ["banquete", "dj", "decoracion"]),
    ("cliente1@eventquote.com", "xv", "CDMX", 110, 5, ["banquete", "dj"]),
    ("cliente1@eventquote.com", "cumpleanos", "Guadalajara", 70, 4, ["banquete"]),
    ("cliente1@eventquote.com", "corporativo", "Monterrey", 180, 5, ["banquete", "fotografia"]),
    ("cliente1@eventquote.com", "boda", "San Juan del Rio", 90, 5, ["banquete", "fotografia"]),
    ("cliente2@eventquote.com", "boda", "CDMX", 220, 7, ["banquete", "dj", "decoracion", "fotografia"]),
    ("cliente2@eventquote.com", "xv", "Queretaro", 160, 6, ["banquete", "dj", "decoracion"]),
    ("cliente2@eventquote.com", "cumpleanos", "Queretaro", 55, 3, ["banquete", "dj"]),
    ("cliente2@eventquote.com", "corporativo", "CDMX", 130, 4, ["banquete"]),
    ("cliente2@eventquote.com", "corporativo", "Guadalajara", 250, 6, ["banquete", "dj", "fotografia"]),
]
# Factor que simula el costo real confirmado respecto al estimado (para los primeros eventos)
FACTORES_REALES = [0.96, 1.05, 1.02, 0.94, 1.08, 0.97, 1.04, 1.01]


def main():
    db = SessionLocal()
    try:
        ml_service.cargar_o_entrenar(db)

        ids = {}
        for nombre, email, password, rol in USUARIOS:
            fila = db.execute(text("SELECT id FROM usuarios WHERE email = :e"), {"e": email}).first()
            if fila:
                ids[email] = fila[0]
                print(f"= Ya existe {email}")
                continue
            res = db.execute(
                text("INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (:n, :e, :p, :r)"),
                {"n": nombre, "e": email, "p": hash_password(password), "r": rol},
            )
            ids[email] = res.lastrowid
            print(f"+ Creado {rol}: {email} / {password}")
        db.commit()

        ya = db.execute(
            text("SELECT COUNT(*) FROM eventos WHERE cliente_id IN (:a, :b)"),
            {"a": ids["cliente1@eventquote.com"], "b": ids["cliente2@eventquote.com"]},
        ).scalar()
        if ya:
            print("= Los eventos de ejemplo ya existen; no se duplican.")
            return

        ahora = datetime.now()
        for i, (email, tipo, ciudad, invitados, horas, servicios) in enumerate(EVENTOS):
            costo, version = ml_service.predecir(tipo, invitados, horas, ciudad, servicios)
            fecha = ahora - timedelta(days=i * 9)
            ev = db.execute(
                text("""INSERT INTO eventos (cliente_id, tipo, invitados, horas, ciudad)
                        VALUES (:c, :t, :i, :h, :ci)"""),
                {"c": ids[email], "t": tipo, "i": invitados, "h": horas, "ci": ciudad},
            )
            evento_id = ev.lastrowid
            for codigo in servicios:
                srv = db.execute(text("SELECT id FROM servicios WHERE codigo = :c"), {"c": codigo}).first()
                db.execute(
                    text("INSERT INTO evento_servicios (evento_id, servicio_id) VALUES (:e, :s)"),
                    {"e": evento_id, "s": srv[0]},
                )
            db.execute(
                text("""INSERT INTO cotizaciones (evento_id, costo_estimado, modelo_version, fecha)
                        VALUES (:e, :c, :v, :f)"""),
                {"e": evento_id, "c": costo, "v": version, "f": fecha},
            )
            if i < len(FACTORES_REALES):
                db.execute(
                    text("""INSERT INTO costos_confirmados (evento_id, costo_real, fuente, validado)
                            VALUES (:e, :c, :f, TRUE)"""),
                    {"e": evento_id, "c": round(costo * FACTORES_REALES[i], 2),
                     "f": "Cotización final del proveedor (dato de prueba)"},
                )
        db.commit()
        print(f"+ {len(EVENTOS)} eventos con cotización y {len(FACTORES_REALES)} costos reales confirmados.")
        print("Listo. Entra al panel admin y pulsa 'Reentrenar' para que el modelo aprenda de los costos reales.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
