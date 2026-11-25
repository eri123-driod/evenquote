"""CONTROLADOR del administrador: estadísticas, usuarios, costos reales y modelo ML.
Todos los endpoints exigen rol admin (require_admin) y leen solo datos VÁLIDOS."""
import logging
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.schemas import AdminCotizacionOut, CostoRealRequest, EventoEntrenamiento, UsuarioOut
from app.services import ml_service

log = logging.getLogger("eventquote")
router = APIRouter(prefix="/admin", tags=["Administrador"], dependencies=[Depends(require_admin)])


# ------------------------------------------------------------------ lecturas validadas
def _usuarios_validos(db: Session):
    filas = db.execute(
        text("SELECT id, nombre, email, rol, creado_en FROM usuarios ORDER BY id ASC")
    ).mappings().all()
    validos = []
    for fila in filas:
        try:
            validos.append(UsuarioOut.model_validate(dict(fila)))
        except ValidationError:
            log.warning("Usuario %s excluido por datos inválidos", fila["id"])
    return validos


def _cotizaciones_validas(db: Session):
    filas = db.execute(text("""
        SELECT c.id, c.evento_id, e.tipo, e.ciudad, e.invitados, e.horas, c.costo_estimado,
               c.modelo_version, c.fecha, u.nombre AS cliente, u.email
        FROM cotizaciones c
        JOIN eventos e ON c.evento_id = e.id
        JOIN usuarios u ON e.cliente_id = u.id
        ORDER BY c.fecha DESC
    """)).mappings().all()
    validas = []
    for fila in filas:
        try:
            validas.append(AdminCotizacionOut.model_validate(dict(fila)))
        except ValidationError:
            log.warning("Cotización %s excluida por datos inválidos", fila["id"])
    return validas


def _serializar_usuario(u: UsuarioOut) -> dict:
    datos = u.model_dump()
    datos["creado_en"] = u.creado_en.strftime("%Y-%m-%d") if u.creado_en else ""
    return datos


def _serializar_cotizacion(c: AdminCotizacionOut) -> dict:
    datos = c.model_dump()
    datos["fecha"] = c.fecha.strftime("%Y-%m-%d %H:%M")
    return datos


# ------------------------------------------------------------------ estadísticas
@router.get("/estadisticas")
def estadisticas(db: Session = Depends(get_db)):
    cotizaciones = _cotizaciones_validas(db)

    por_tipo, por_ciudad, por_cliente, por_mes = defaultdict(list), defaultdict(list), {}, defaultdict(int)
    for c in cotizaciones:
        por_tipo[c.tipo].append(c.costo_estimado)
        por_ciudad[c.ciudad].append(c.costo_estimado)
        acum = por_cliente.setdefault(c.email, {"cliente": c.cliente, "email": c.email, "total_cotizaciones": 0, "volumen": 0.0})
        acum["total_cotizaciones"] += 1
        acum["volumen"] += c.costo_estimado
        por_mes[c.fecha.strftime("%Y-%m")] += 1

    def resumen(grupos, clave):
        return [
            {clave: k, "total_cotizaciones": len(v), "costo_promedio": round(sum(v) / len(v), 2)}
            for k, v in sorted(grupos.items())
        ]

    return {
        "total_eventos": len(cotizaciones),
        "volumen_cotizado": round(sum(c.costo_estimado for c in cotizaciones), 2),
        "resumen_por_tipo": resumen(por_tipo, "tipo"),
        "resumen_por_ciudad": resumen(por_ciudad, "ciudad"),
        "resumen_por_cliente": sorted(
            [{**v, "volumen": round(v["volumen"], 2)} for v in por_cliente.values()],
            key=lambda x: (-x["total_cotizaciones"], x["cliente"]),
        ),
        "actividad_por_mes": [{"periodo": k, "total_cotizaciones": v} for k, v in sorted(por_mes.items())],
    }


@router.get("/cotizaciones")
def todas_las_cotizaciones(db: Session = Depends(get_db)):
    return [_serializar_cotizacion(c) for c in _cotizaciones_validas(db)]


# ------------------------------------------------------------------ usuarios
@router.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db)):
    return [_serializar_usuario(u) for u in _usuarios_validos(db)]


def _usuario_o_error(db: Session, user_id: int) -> UsuarioOut:
    fila = db.execute(
        text("SELECT id, nombre, email, rol, creado_en FROM usuarios WHERE id = :id"), {"id": user_id}
    ).mappings().first()
    if fila is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        return UsuarioOut.model_validate(dict(fila))
    except ValidationError:
        raise HTTPException(status_code=409, detail="El registro de este usuario es inválido y no puede mostrarse")


@router.get("/usuarios/{user_id}")
def detalle_usuario(user_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    return _serializar_usuario(_usuario_o_error(db, user_id))


@router.patch("/usuarios/{user_id}/promover")
def promover_usuario(user_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    usuario = _usuario_o_error(db, user_id)
    if usuario.rol == "admin":
        return {"mensaje": "El usuario ya tiene rol de Administrador"}
    try:
        db.execute(text("UPDATE usuarios SET rol = 'admin' WHERE id = :id"), {"id": user_id})
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo promover al usuario")
    return {"mensaje": f"Usuario #{user_id} promovido a Administrador"}


# ------------------------------------------------------------------ costos reales + ML
@router.post("/costos-confirmados", status_code=201)
def registrar_costo_real(req: CostoRealRequest, db: Session = Depends(get_db)):
    fila = db.execute(
        text("SELECT tipo, ciudad, invitados, horas FROM eventos WHERE id = :id"), {"id": req.evento_id}
    ).mappings().first()
    if fila is None:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    try:
        EventoEntrenamiento.model_validate({**dict(fila), "costo_real": req.costo_real})
    except ValidationError:
        raise HTTPException(status_code=409, detail="El evento tiene datos inválidos; no se puede usar para entrenar")
    try:
        db.execute(
            text("""INSERT INTO costos_confirmados (evento_id, costo_real, fuente, validado)
                    VALUES (:e, :c, :f, TRUE)
                    ON DUPLICATE KEY UPDATE costo_real = :c, fuente = :f, validado = TRUE"""),
            {"e": req.evento_id, "c": req.costo_real, "f": req.fuente},
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo guardar el costo real")
    return {"mensaje": "Costo real confirmado. Reentrena el modelo para que aprenda de este dato."}


@router.get("/ml/info")
def ml_info(db: Session = Depends(get_db)):
    try:
        return ml_service.info(db)
    except ml_service.ModeloNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/ml/reentrenar")
def ml_reentrenar(db: Session = Depends(get_db)):
    try:
        meta = ml_service.entrenar(db)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="No se pudo leer la base de datos para reentrenar")
    meta["reales_disponibles"] = meta["muestras_reales"]
    return meta
