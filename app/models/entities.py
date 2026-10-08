from dataclasses import dataclass
from typing import Optional


@dataclass
class Prestatario:
    id: Optional[int]
    cedula: str
    nombre: str
    apellido: str
    tipo: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    estado: str = "ACTIVO"


@dataclass
class Laboratorio:
    id: Optional[int]
    codigo: str
    nombre: str
    ubicacion: str
    capacidad: int
    duracion_estandar_minutos: int = 70
    estado: str = "DISPONIBLE"


@dataclass
class Categoria:
    id: Optional[int]
    nombre: str
    descripcion: Optional[str] = None


@dataclass
class Equipo:
    id: Optional[int]
    codigo: str
    nombre: str
    categoria_id: Optional[int]
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serial: Optional[str] = None
    laboratorio_id: Optional[int] = None
    estado: str = "DISPONIBLE"
