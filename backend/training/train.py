"""Entrena (o reentrena) el modelo de ML desde la terminal.

Usa el dataset base + los costos reales confirmados en MySQL, evalúa con validación
cruzada y guarda app/ml/modelo.joblib y app/ml/metadata.json.
Uso (dentro de backend/):  python training/train.py
Si el servidor ya está encendido, reinícialo o usa el botón 'Reentrenar' del panel admin.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.database import SessionLocal  # noqa: E402
from app.services import ml_service  # noqa: E402


def main():
    db = None
    try:
        db = SessionLocal()
        print(f"Costos reales válidos en MySQL: {ml_service.contar_reales(db)}")
    except Exception as exc:
        print(f"(No se pudo leer MySQL: {exc}). Se entrena solo con el dataset base.")
        db = None
    meta = ml_service.entrenar(db)
    if db is not None:
        db.close()
    print(f"Modelo {meta['version']} -> {meta['modelo']}")
    print(f"Muestras: {meta['muestras_total']} ({meta['muestras_base']} base + {meta['muestras_reales']} reales)")
    print(f"{meta['metodo_evaluacion']}: MAE ${meta['mae_cv']:,.2f} MXN | R2 {meta['r2_cv']:.3f}")


if __name__ == "__main__":
    main()
