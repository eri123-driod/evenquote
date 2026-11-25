"""CONTROLADOR del cliente: predecir, guardar y consultar SUS cotizaciones."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schemas import CotizacionOut, EventoCotizacionRequest
from app.services import ml_service

log = logging.getLogger("eventquote")
router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones (cliente)"])

SQL_COTIZACION = """
    SELECT c.id, c.evento_id, e.cliente_id, e.tipo, e.ciudad, e.invitados, e.horas,
           c.costo_estimado, c.modelo_version, c.fecha
    FROM cotizaciones c
    JOIN eventos e ON c.evento_id = e.id
"""


def serializar(cot: CotizacionOut) -> dict:
    datos = cot.model_dump()
    datos["fecha"] = cot.fecha.strftime("%Y-%m-%d %H:%M")
    return datos


def _predecir(req: EventoCotizacionRequest):
    try:
        costo, version = ml_service.predecir(req.tipo, req.invitados, req.duracion_horas, req.ciudad, req.servicios)
    except ml_service.ModeloNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"costo_estimado": costo, "moneda": "MXN", "modelo_version": version}


@router.post("/predecir")
def predecir_costo(req: EventoCotizacionRequest, user: dict = Depends(get_current_user)):
    return _predecir(req)


@router.post("", status_code=201)
def crear_cotizacion(req: EventoCotizacionRequest, user: dict = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    prediccion = _predecir(req)
    try:
        res_ev = db.execute(
            text("""INSERT INTO eventos (cliente_id, tipo, invitados, horas, ciudad, fecha)
                    VALUES (:cid, :tipo, :inv, :hrs, :ciu, :fec)"""),
            {"cid": user["id"], "tipo": req.tipo, "inv": req.invitados,
             "hrs": req.duracion_horas, "ciu": req.ciudad, "fec": req.fecha},
        )
        evento_id = res_ev.lastrowid
        for codigo in req.servicios:
            srv = db.execute(text("SELECT id FROM servicios WHERE codigo = :c"), {"c": codigo}).first()
            if srv:
                db.execute(
                    text("INSERT INTO evento_servicios (evento_id, servicio_id) VALUES (:e, :s)"),
                    {"e": evento_id, "s": srv[0]},
                )
        res_cot = db.execute(
            text("INSERT INTO cotizaciones (evento_id, costo_estimado, modelo_version) VALUES (:e, :c, :v)"),
            {"e": evento_id, "c": prediccion["costo_estimado"], "v": prediccion["modelo_version"]},
        )
        db.commit()  # evento + servicios + cotización se guardan juntos o no se guarda nada
    except SQLAlchemyError:
        db.rollback()
        log.exception("Error guardando cotización")
        raise HTTPException(status_code=500, detail="No se pudo guardar la cotización. Intenta de nuevo.")
    return {"cotizacion_id": res_cot.lastrowid, "evento_id": evento_id, **prediccion}


@router.get("/mias")
def mis_cotizaciones(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Solo las del usuario autenticado; los registros inválidos de la BD se excluyen."""
    filas = db.execute(
        text(SQL_COTIZACION + " WHERE e.cliente_id = :uid ORDER BY c.fecha DESC"), {"uid": user["id"]}
    ).mappings().all()
    validas = []
    for fila in filas:
        try:
            validas.append(serializar(CotizacionOut.model_validate(dict(fila))))
        except ValidationError:
            log.warning("Cotización %s excluida por datos inválidos", fila["id"])
    return validas


@router.get("/{cotizacion_id}")
def detalle_cotizacion(cotizacion_id: int = Path(..., gt=0), user: dict = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Consulta individual. Un cliente solo puede ver las suyas (cambiar el id no sirve)."""
    fila = db.execute(text(SQL_COTIZACION + " WHERE c.id = :cid"), {"cid": cotizacion_id}).mappings().first()
    if fila is None or (fila["cliente_id"] != user["id"] and user["rol"] != "admin"):
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    try:
        return serializar(CotizacionOut.model_validate(dict(fila)))
    except ValidationError:
        raise HTTPException(status_code=409, detail="El registro de esta cotización es inválido y no puede mostrarse")
