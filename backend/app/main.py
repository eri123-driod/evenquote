"""Punto de entrada de la API EventQuote (FastAPI).

Arquitectura MC:
  app/models/       -> MODELOS: reglas y validación de datos (Pydantic)
  app/controllers/  -> CONTROLADORES: rutas, permisos y respuestas
  app/services/     -> servicio de Machine Learning
  app/core/         -> configuración, base de datos y seguridad
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.controllers import admin_controller, auth_controller, cotizaciones_controller
from app.core.database import SessionLocal
from app.services import ml_service

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("eventquote")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Al arrancar: carga el modelo ML (o lo entrena si todavía no existe)."""
    db = None
    try:
        db = SessionLocal()
        ml_service.cargar_o_entrenar(db)
    except Exception:
        log.exception("No se pudo leer MySQL al preparar el modelo; se usa solo el dataset base")
        try:
            ml_service.cargar_o_entrenar(None)
        except Exception:
            log.exception("No se pudo preparar el modelo ML")
    finally:
        if db is not None:
            db.close()
    yield


app = FastAPI(title="EventQuote API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_controller.router)
app.include_router(cotizaciones_controller.router)
app.include_router(admin_controller.router)


# ---------------------------------------------------------------- errores de validación en español
def _traducir(error: dict) -> str:
    tipo, ctx, msg = error.get("type", ""), error.get("ctx") or {}, error.get("msg", "")
    if tipo == "missing":
        return "es obligatorio"
    if tipo == "greater_than_equal":
        return f"debe ser mayor o igual a {ctx.get('ge')}"
    if tipo == "greater_than":
        return f"debe ser mayor que {ctx.get('gt')}"
    if tipo == "less_than_equal":
        return f"debe ser menor o igual a {ctx.get('le')}"
    if tipo == "less_than":
        return f"debe ser menor que {ctx.get('lt')}"
    if tipo == "string_too_short":
        return f"debe tener al menos {ctx.get('min_length')} caracteres"
    if tipo == "string_too_long":
        return f"debe tener máximo {ctx.get('max_length')} caracteres"
    if tipo in ("int_parsing", "int_type", "int_from_float"):
        return "debe ser un número entero"
    if tipo in ("float_parsing", "float_type"):
        return "debe ser un número"
    if tipo == "extra_forbidden":
        return "campo no permitido"
    if tipo in ("json_invalid", "model_attributes_type"):
        return "el cuerpo de la solicitud no es un JSON válido"
    if "email" in msg.lower() and "valid" in msg.lower():
        return "no es un correo electrónico válido"
    return msg.replace("Value error, ", "")


@app.exception_handler(RequestValidationError)
async def validacion_handler(request: Request, exc: RequestValidationError):
    errores = []
    for e in exc.errors():
        campo = ".".join(str(x) for x in e.get("loc", ()) if x not in ("body", "query", "path"))
        errores.append({"campo": campo, "mensaje": _traducir(e)})
    detalle = "; ".join(f"{x['campo']}: {x['mensaje']}" if x["campo"] else x["mensaje"] for x in errores)
    return JSONResponse(status_code=422, content={"detail": detalle, "errores": errores})


@app.get("/health", tags=["Sistema"])
def health():
    try:
        meta = ml_service.info(None)
        return {"status": "ok", "ml_model_loaded": True, "ml_version": meta["version"]}
    except ml_service.ModeloNoDisponible:
        return {"status": "ok", "ml_model_loaded": False}
