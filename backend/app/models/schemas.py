"""MODELOS (capa M de la arquitectura MC).

Aquí vive TODA la validación de datos:
  * *Request  -> lo que llega del cliente (app móvil, Postman, curl...). Rechazan campos extra.
  * *Out      -> lo que se LEE de MySQL. Se valida antes de responder; si un registro
                 no cumple las reglas se excluye (listas/estadísticas) o se devuelve un
                 error controlado (consulta individual).
"""
import re
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CIUDADES_PERMITIDAS = {"Queretaro", "San Juan del Rio", "CDMX", "Guadalajara", "Monterrey"}
TIPOS_PERMITIDOS = {"boda", "xv", "cumpleanos", "corporativo"}
SERVICIOS_PERMITIDOS = {"banquete", "dj", "decoracion", "fotografia"}

COSTO_MAXIMO = 100_000_000


# ------------------------------------------------------------------ reglas reutilizables
def _validar_tipo(v: str) -> str:
    v = v.strip().lower()
    if v not in TIPOS_PERMITIDOS:
        raise ValueError(f"Tipo inválido. Permitidos: {sorted(TIPOS_PERMITIDOS)}")
    return v


def _validar_ciudad(v: str) -> str:
    v = v.strip()
    if v not in CIUDADES_PERMITIDAS:
        raise ValueError(f"Ciudad no válida. Permitidas: {sorted(CIUDADES_PERMITIDAS)}")
    return v


def _validar_nombre(v: str) -> str:
    v = v.strip()
    if len(v) < 2:
        raise ValueError("El nombre debe tener al menos 2 caracteres")
    if not any(c.isalpha() for c in v):
        raise ValueError("El nombre debe contener letras")
    return v


class _Entrada(BaseModel):
    """Base de las solicitudes: cualquier campo no declarado (por ejemplo 'rol') se rechaza."""
    model_config = ConfigDict(extra="forbid")


class _Salida(BaseModel):
    """Base de lo que se lee de la base de datos."""
    model_config = ConfigDict(extra="ignore")


# ------------------------------------------------------------------ SOLICITUDES
class RegisterRequest(_Entrada):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("nombre")
    @classmethod
    def nombre_valido(cls, v: str):
        return _validar_nombre(v)

    @field_validator("password")
    @classmethod
    def password_fuerte(cls, v: str):
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("La contraseña debe incluir letras y números")
        return v


class LoginRequest(_Entrada):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class EventoCotizacionRequest(_Entrada):
    tipo: str
    invitados: int = Field(..., ge=1, le=2000)
    duracion_horas: float = Field(..., ge=1, le=24)
    ciudad: str
    servicios: List[str] = Field(default_factory=list, max_length=4)
    fecha: Optional[date] = None

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str):
        return _validar_tipo(v)

    @field_validator("ciudad")
    @classmethod
    def validar_ciudad(cls, v: str):
        return _validar_ciudad(v)

    @field_validator("servicios")
    @classmethod
    def validar_servicios(cls, v: List[str]):
        if len(v) != len(set(v)):
            raise ValueError("No se permiten servicios duplicados")
        for s in v:
            if s not in SERVICIOS_PERMITIDOS:
                raise ValueError(f"Servicio inválido: {s}")
        return v


class CostoRealRequest(_Entrada):
    evento_id: int = Field(..., gt=0)
    costo_real: float = Field(..., gt=0, le=10_000_000)
    fuente: str = Field(..., min_length=3, max_length=150)


# ------------------------------------------------------------------ LECTURAS DE LA BD
class UsuarioPublico(_Salida):
    id: int = Field(..., gt=0)
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    rol: Literal["cliente", "admin"]

    @field_validator("nombre")
    @classmethod
    def nombre_valido(cls, v: str):
        return _validar_nombre(v)


class UsuarioOut(UsuarioPublico):
    creado_en: Optional[datetime] = None


class CotizacionOut(_Salida):
    id: int = Field(..., gt=0)
    evento_id: int = Field(..., gt=0)
    tipo: str
    ciudad: str
    invitados: int = Field(..., ge=1, le=2000)
    horas: float = Field(..., ge=1, le=24)
    costo_estimado: float = Field(..., gt=0, le=COSTO_MAXIMO)
    modelo_version: str = Field(..., min_length=1, max_length=20)
    fecha: datetime

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str):
        return _validar_tipo(v)

    @field_validator("ciudad")
    @classmethod
    def validar_ciudad(cls, v: str):
        return _validar_ciudad(v)


class AdminCotizacionOut(CotizacionOut):
    cliente: str = Field(..., min_length=2, max_length=100)
    email: EmailStr


class EventoEntrenamiento(_Salida):
    """Evento con costo real confirmado que el modelo ML puede usar para aprender."""
    tipo: str
    ciudad: str
    invitados: int = Field(..., ge=1, le=2000)
    horas: float = Field(..., ge=1, le=24)
    costo_real: float = Field(..., gt=0, le=10_000_000)

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str):
        return _validar_tipo(v)

    @field_validator("ciudad")
    @classmethod
    def validar_ciudad(cls, v: str):
        return _validar_ciudad(v)
