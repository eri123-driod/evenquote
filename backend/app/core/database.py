"""Conexión a MySQL con SQLAlchemy."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

_ca = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ca.pem")
_args = {"ssl": {"ca": _ca}} if os.path.exists(_ca) else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()