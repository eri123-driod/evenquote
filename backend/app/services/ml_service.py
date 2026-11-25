"""Servicio de Machine Learning (regresión del costo de un evento).

* Variables: tipo, ciudad, invitados, log(invitados), horas y 4 banderas de servicios.
* Datos: dataset base documentado + costos REALES confirmados por el administrador
  sobre eventos que capturaron los clientes (tabla costos_confirmados). Los registros
  inválidos se descartan antes de entrenar.
* Evaluación: validación cruzada (K pliegues) -> MAE y R². Se prueban varios modelos
  y se queda el de menor MAE.
* Cada reentrenamiento incrementa la versión (v1, v2, ...), que se guarda en cada
  cotización (cotizaciones.modelo_version).
"""
import json
import logging
import math
import os
import threading
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from pydantic import ValidationError
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import text

from app.ml.datos_base import DATOS_BASE
from app.models.schemas import EventoEntrenamiento

log = logging.getLogger("eventquote.ml")

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
MODEL_PATH = os.path.join(ML_DIR, "modelo.joblib")
META_PATH = os.path.join(ML_DIR, "metadata.json")

SERVICIOS = ["banquete", "dj", "decoracion", "fotografia"]
COLS_CAT = ["tipo", "ciudad"]
COLS_NUM = ["invitados", "duracion_horas", "log_invitados"] + [f"srv_{s}" for s in SERVICIOS]
VARIABLES = COLS_CAT + COLS_NUM

_lock = threading.Lock()
_estado = {"modelo": None, "meta": None}


class ModeloNoDisponible(Exception):
    pass


# ------------------------------------------------------------------ datos
def _features(tipo, ciudad, invitados, horas, servicios) -> dict:
    activos = set(servicios)
    fila = {
        "tipo": tipo,
        "ciudad": ciudad,
        "invitados": float(invitados),
        "duracion_horas": float(horas),
        "log_invitados": math.log(max(float(invitados), 1.0)),
    }
    for s in SERVICIOS:
        fila[f"srv_{s}"] = int(s in activos)
    return fila


def _cargar_reales(db):
    """Eventos con costo real validado en MySQL. Devuelve (filas_validas, descartadas)."""
    if db is None:
        return [], 0
    filas = db.execute(text("""
        SELECT e.tipo, e.ciudad, e.invitados, e.horas, cc.costo_real,
               GROUP_CONCAT(s.codigo) AS servicios
        FROM costos_confirmados cc
        JOIN eventos e ON e.id = cc.evento_id
        LEFT JOIN evento_servicios es ON es.evento_id = e.id
        LEFT JOIN servicios s ON s.id = es.servicio_id
        WHERE cc.validado = TRUE
        GROUP BY cc.id, e.tipo, e.ciudad, e.invitados, e.horas, cc.costo_real
    """)).mappings().all()

    validas, descartadas = [], 0
    for f in filas:
        try:
            ev = EventoEntrenamiento.model_validate(dict(f))
        except ValidationError:
            descartadas += 1
            continue
        servicios = [x for x in (f["servicios"] or "").split(",") if x in SERVICIOS]
        validas.append({
            "tipo": ev.tipo, "ciudad": ev.ciudad, "invitados": ev.invitados,
            "horas": ev.horas, "servicios": ",".join(servicios), "costo_real": ev.costo_real,
        })
    return validas, descartadas


def contar_reales(db) -> int:
    return len(_cargar_reales(db)[0])


# ------------------------------------------------------------------ modelos
def _preprocesador():
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), COLS_CAT),
        ("num", StandardScaler(), COLS_NUM),
    ])


def _candidatos():
    candidatos = {}
    for alpha in (0.1, 0.3, 1.0, 3.0):
        candidatos[f"Ridge sobre log(costo), alpha={alpha}"] = TransformedTargetRegressor(
            regressor=Pipeline([("pre", _preprocesador()), ("reg", Ridge(alpha=alpha))]),
            func=np.log, inverse_func=np.exp,
        )
    candidatos["Random Forest (150 arboles)"] = Pipeline([
        ("pre", _preprocesador()),
        ("reg", RandomForestRegressor(n_estimators=150, random_state=42)),
    ])
    return candidatos


def _siguiente_version() -> int:
    try:
        with open(META_PATH, encoding="utf-8") as f:
            return int(json.load(f).get("version_num", 0)) + 1
    except Exception:
        return 1


# ------------------------------------------------------------------ API del servicio
def entrenar(db=None) -> dict:
    """Entrena con dataset base + costos reales de MySQL, evalúa y guarda el modelo."""
    with _lock:
        base = [dict(f) for f in DATOS_BASE]
        reales, descartadas = _cargar_reales(db)
        todas = base + reales

        X = pd.DataFrame([
            _features(f["tipo"], f["ciudad"], f["invitados"], f["horas"],
                      [s for s in f["servicios"].split(",") if s])
            for f in todas
        ])[VARIABLES]
        y = pd.Series([float(f["costo_real"]) for f in todas])

        pliegues = max(2, min(5, len(todas)))
        kf = KFold(n_splits=pliegues, shuffle=True, random_state=42)

        mejor_nombre, mejor_mae, mejor_r2 = None, None, None
        for nombre, modelo in _candidatos().items():
            pred = cross_val_predict(clone(modelo), X, y, cv=kf)
            mae = float(mean_absolute_error(y, pred))
            r2 = float(r2_score(y, pred))
            log.info("Candidato %s -> MAE %.0f | R2 %.3f", nombre, mae, r2)
            if mejor_mae is None or mae < mejor_mae:
                mejor_nombre, mejor_mae, mejor_r2 = nombre, mae, r2

        final = clone(_candidatos()[mejor_nombre]).fit(X, y)

        version_num = _siguiente_version()
        meta = {
            "version_num": version_num,
            "version": f"v{version_num}",
            "modelo": mejor_nombre,
            "entrenado_en": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "muestras_base": len(base),
            "muestras_reales": len(reales),
            "muestras_total": len(todas),
            "descartados_invalidos": descartadas,
            "mae_cv": round(mejor_mae, 2),
            "r2_cv": round(mejor_r2, 4),
            "metodo_evaluacion": f"Validación cruzada de {pliegues} pliegues",
            "variables": VARIABLES,
        }

        os.makedirs(ML_DIR, exist_ok=True)
        joblib.dump(final, MODEL_PATH)
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        _estado["modelo"], _estado["meta"] = final, meta
        log.info("Modelo %s entrenado: %s (MAE %.0f, R2 %.3f)", meta["version"], mejor_nombre, mejor_mae, mejor_r2)
        return dict(meta)


def cargar_o_entrenar(db=None) -> dict:
    """Carga el modelo guardado; si no existe (o no se puede leer) lo entrena."""
    if os.path.exists(MODEL_PATH) and os.path.exists(META_PATH):
        try:
            with open(META_PATH, encoding="utf-8") as f:
                meta = json.load(f)
            _estado["modelo"], _estado["meta"] = joblib.load(MODEL_PATH), meta
            return dict(meta)
        except Exception as exc:
            log.warning("No se pudo cargar el modelo guardado (%s). Se reentrena.", exc)
    return entrenar(db)


def info(db=None) -> dict:
    meta = _estado["meta"]
    if meta is None:
        raise ModeloNoDisponible("El modelo todavía no está entrenado")
    datos = dict(meta)
    datos["reales_disponibles"] = contar_reales(db) if db is not None else meta["muestras_reales"]
    return datos


def predecir(tipo, invitados, horas, ciudad, servicios):
    """Devuelve (costo_estimado_MXN, version_del_modelo)."""
    modelo, meta = _estado["modelo"], _estado["meta"]
    if modelo is None or meta is None:
        raise ModeloNoDisponible("Modelo ML no disponible. Reinicia el servidor o reentrena desde el panel admin.")
    X = pd.DataFrame([_features(tipo, ciudad, invitados, horas, servicios)])[VARIABLES]
    costo = float(modelo.predict(X)[0])
    costo = min(max(1500.0, round(costo, 2)), 50_000_000.0)
    return costo, meta["version"]
