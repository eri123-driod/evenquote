"""Verifica automáticamente las pruebas de la rúbrica del 3er parcial.

Antes: MySQL encendido, `uvicorn` corriendo y `python sembrar_datos_prueba.py` ejecutado.
Uso (dentro de backend/, con el venv activo):   python pruebas/verificar_rubrica.py
Variables opcionales: API_URL (por defecto http://127.0.0.1:8000)
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")
ADMIN = ("admin@eventquote.com", "Admin123!")
C1 = ("cliente1@eventquote.com", "Cliente123!")
C2 = ("cliente2@eventquote.com", "Cliente123!")
RESULTADOS = []


def http(metodo, ruta, cuerpo=None, token=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            crudo = r.read()
            return r.status, (json.loads(crudo) if crudo else None)
    except urllib.error.HTTPError as e:
        crudo = e.read()
        try:
            return e.code, json.loads(crudo)
        except Exception:
            return e.code, crudo.decode(errors="ignore")


def check(nombre, condicion, detalle=""):
    RESULTADOS.append((nombre, bool(condicion)))
    print(f"[{'OK ' if condicion else 'FALLA'}] {nombre}" + (f"  -> {detalle}" if (detalle and not condicion) else ""))


def login(cuenta):
    estado, cuerpo = http("POST", "/auth/login", {"email": cuenta[0], "password": cuenta[1]})
    return (cuerpo["access_token"] if estado == 200 else None), estado, cuerpo


def cotizacion_valida(**cambios):
    base = {"tipo": "boda", "invitados": 100, "duracion_horas": 5, "ciudad": "Queretaro", "servicios": ["banquete"]}
    base.update(cambios)
    return base


def main():
    try:
        estado, _ = http("GET", "/health")
    except Exception as exc:
        print(f"No se pudo conectar a {BASE}: {exc}\nEnciende uvicorn primero.")
        sys.exit(2)

    # ---------------------------------------------------------------- 1. Login
    tok_admin, e1, _ = login(ADMIN)
    tok_c1, e2, _ = login(C1)
    tok_c2, e3, _ = login(C2)
    check("1a. Login administrador", tok_admin, f"HTTP {e1}; ¿ejecutaste sembrar_datos_prueba.py?")
    check("1b. Login cliente", tok_c1 and tok_c2, f"HTTP {e2}/{e3}")
    _, e4, _ = login((ADMIN[0], "contraseña-incorrecta-1"))
    check("1c. Contraseña incorrecta rechazada (401)", e4 == 401, f"HTTP {e4}")
    if not (tok_admin and tok_c1 and tok_c2):
        print("Sin cuentas de prueba no se puede continuar.")
        sys.exit(2)

    # ---------------------------------------------------------------- permisos por rol
    e, _ = http("GET", "/admin/usuarios")
    check("2a. Sin token no entra a rutas protegidas (401)", e == 401, f"HTTP {e}")
    e, _ = http("GET", "/admin/usuarios", token=tok_c1)
    check("2b. Cliente NO puede usar endpoints de admin (403)", e == 403, f"HTTP {e}")
    _, yo = http("GET", "/auth/me", token=tok_c1)
    e, _ = http("PATCH", f"/admin/usuarios/{yo['id']}/promover", token=tok_c1)
    _, yo2 = http("GET", "/auth/me", token=tok_c1)
    check("2c. Cliente no puede auto-promoverse (403 y rol intacto)", e == 403 and yo2["rol"] == "cliente", f"HTTP {e}")
    e, _ = http("POST", "/auth/register", {"nombre": "Hacker", "email": f"h{uuid.uuid4().hex[:6]}@mail.com",
                                            "password": "Clave1234", "rol": "admin"})
    check("2d. Registro con campo 'rol' rechazado (422)", e == 422, f"HTTP {e}")

    # ---------------------------------------------------------------- 3 y 4. Validación
    _, antes = http("GET", "/cotizaciones/mias", token=tok_c1)
    casos = {
        "invitados negativos": cotizacion_valida(invitados=-5),
        "horas fuera de rango": cotizacion_valida(duracion_horas=99),
        "ciudad inexistente": cotizacion_valida(ciudad="Narnia"),
        "servicio inventado": cotizacion_valida(servicios=["unicornios"]),
        "tipo inválido": cotizacion_valida(tipo="fiesta-loca"),
        "invitados como texto": cotizacion_valida(invitados="muchos"),
    }
    for nombre, cuerpo in casos.items():
        e, _ = http("POST", "/cotizaciones", cuerpo, tok_c1)
        check(f"3. API rechaza dato inválido directo ({nombre}) -> 422", e == 422, f"HTTP {e}")
    _, despues = http("GET", "/cotizaciones/mias", token=tok_c1)
    check("3. Los datos inválidos NO se guardaron", len(antes) == len(despues))
    e, _ = http("POST", "/auth/register", {"nombre": "A", "email": "no-es-correo", "password": "123"})
    check("3. Registro inválido rechazado (422)", e == 422, f"HTTP {e}")
    e, _ = http("GET", "/admin/usuarios/0", token=tok_admin)
    check("3. Parámetro de ruta inválido (id=0) rechazado (422)", e == 422, f"HTTP {e}")

    # ---------------------------------------------------------------- ML
    e, pred = http("POST", "/cotizaciones/predecir", cotizacion_valida(), tok_c1)
    check("7a. ML: predicción generada por el backend", e == 200 and pred and pred["costo_estimado"] > 0, f"HTTP {e}")
    e, nueva = http("POST", "/cotizaciones", cotizacion_valida(invitados=130), tok_c1)
    check("7b. ML: cotización guardada en MySQL", e == 201 and nueva and "cotizacion_id" in nueva, f"HTTP {e}")
    if e == 201:
        cid = nueva["cotizacion_id"]
        e, _ = http("GET", f"/cotizaciones/{cid}", token=tok_c1)
        check("5a. Cliente ve su propia cotización", e == 200, f"HTTP {e}")
        e, _ = http("GET", f"/cotizaciones/{cid}", token=tok_c2)
        check("5b. Otro cliente NO puede ver mi cotización cambiando el id (404)", e == 404, f"HTTP {e}")
        e, _ = http("POST", "/admin/costos-confirmados",
                    {"evento_id": nueva["evento_id"], "costo_real": nueva["costo_estimado"] * 1.03,
                     "fuente": "Prueba automática"}, tok_admin)
        check("7c. Admin confirma costo real", e == 201, f"HTTP {e}")
    _, info1 = http("GET", "/admin/ml/info", token=tok_admin)
    e, info2 = http("POST", "/admin/ml/reentrenar", token=tok_admin)
    check("7d. Reentrenamiento con datos de MySQL (nueva versión y métricas)",
          e == 200 and info2 and info2["version_num"] > info1["version_num"] and "mae_cv" in info2, f"HTTP {e}")

    # ---------------------------------------------------------------- 2. Promoción persistente
    correo = f"temp{uuid.uuid4().hex[:6]}@mail.com"
    e, _ = http("POST", "/auth/register", {"nombre": "Temporal Prueba", "email": correo, "password": "Temporal123"})
    tok_t, _, _ = login((correo, "Temporal123"))
    e_antes, _ = http("GET", "/admin/usuarios", token=tok_t)
    _, usuarios = http("GET", "/admin/usuarios", token=tok_admin)
    objetivo = next((u for u in usuarios if u["email"] == correo), None)
    e_prom, _ = http("PATCH", f"/admin/usuarios/{objetivo['id']}/promover", token=tok_admin) if objetivo else (0, None)
    tok_t2, _, cuerpo = login((correo, "Temporal123"))
    e_despues, _ = http("GET", "/admin/usuarios", token=tok_t2)
    check("2e. Promover cliente -> admin persiste y obtiene acceso al iniciar sesión de nuevo",
          e_antes == 403 and e_prom == 200 and (cuerpo.get("user") or {}).get("rol") == "admin" and e_despues == 200,
          f"antes={e_antes} promover={e_prom} despues={e_despues}")

    # ---------------------------------------------------------------- 6. Registros inválidos en la BD
    from sqlalchemy import text
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM usuarios WHERE nombre = 'PRUEBA INVALIDA'"))
        db.execute(text("DELETE FROM eventos WHERE ciudad LIKE 'PRUEBA-INVALIDA%'"))
        db.commit()
        uid = db.execute(text("SELECT id FROM usuarios WHERE email = :e"), {"e": C1[0]}).scalar()
        db.execute(text("""INSERT INTO usuarios (nombre, email, password_hash, rol)
                           VALUES ('PRUEBA INVALIDA', 'correo-invalido', 'hash-falso', 'cliente')"""))
        bad_user = db.execute(text("SELECT id FROM usuarios WHERE nombre = 'PRUEBA INVALIDA'")).scalar()
        db.execute(text("""INSERT INTO eventos (cliente_id, tipo, invitados, horas, ciudad)
                           VALUES (:u, 'boda', -5, 5, 'PRUEBA-INVALIDA')"""), {"u": uid})
        ev = db.execute(text("SELECT id FROM eventos WHERE ciudad = 'PRUEBA-INVALIDA'")).scalar()
        db.execute(text("INSERT INTO cotizaciones (evento_id, costo_estimado, modelo_version) VALUES (:e, 99999, 'v1')"),
                   {"e": ev})
        bad_cot = db.execute(text("SELECT id FROM cotizaciones WHERE evento_id = :e"), {"e": ev}).scalar()
        db.commit()

        _, lista_u = http("GET", "/admin/usuarios", token=tok_admin)
        check("6a. Usuario inválido en BD NO aparece en /admin/usuarios",
              all(u["email"] != "correo-invalido" for u in lista_u))
        _, lista_c = http("GET", "/admin/cotizaciones", token=tok_admin)
        check("6b. Cotización inválida en BD NO aparece en /admin/cotizaciones",
              all(c["ciudad"] != "PRUEBA-INVALIDA" for c in lista_c))
        _, mias = http("GET", "/cotizaciones/mias", token=tok_c1)
        check("6c. Cotización inválida NO aparece en /cotizaciones/mias",
              all(c["ciudad"] != "PRUEBA-INVALIDA" for c in mias))
        e, _ = http("GET", f"/admin/usuarios/{bad_user}", token=tok_admin)
        check("6d. Consulta individual de usuario inválido -> error controlado (409)", e == 409, f"HTTP {e}")
        e, _ = http("GET", f"/cotizaciones/{bad_cot}", token=tok_c1)
        check("6e. Consulta individual de cotización inválida -> error controlado (409)", e == 409, f"HTTP {e}")

        # ------------------------------------------------------------ 5. Panel coherente
        e, est = http("GET", "/admin/estadisticas", token=tok_admin)
        suma_tabla = sum(t["total_cotizaciones"] for t in est["resumen_por_tipo"])
        volumen = round(sum(c["costo_estimado"] for c in lista_c), 2)
        check("5. Panel: totales y gráfica coherentes con los registros VÁLIDOS",
              e == 200 and est["total_eventos"] == len(lista_c) == suma_tabla
              and abs(est["volumen_cotizado"] - volumen) < 0.05,
              f"total={est['total_eventos']} lista={len(lista_c)} tabla={suma_tabla}")
    finally:
        db.execute(text("DELETE FROM usuarios WHERE nombre = 'PRUEBA INVALIDA'"))
        db.execute(text("DELETE FROM eventos WHERE ciudad LIKE 'PRUEBA-INVALIDA%'"))
        db.execute(text("DELETE FROM usuarios WHERE email = :e"), {"e": correo})
        db.commit()
        db.close()

    ok = sum(1 for _, r in RESULTADOS if r)
    print(f"\nResultado: {ok}/{len(RESULTADOS)} pruebas correctas")
    sys.exit(0 if ok == len(RESULTADOS) else 1)


if __name__ == "__main__":
    main()
