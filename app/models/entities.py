from dataclasses import dataclass
from typing import Optional


@dataclass
class Prestatario:
    id: Optional[int]
    cedula: str
    nombre: str
    apellido: str
    tipo: str
    edicion_id: int = 1
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
    edicion_id: int = 1
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
    edicion_id: int = 1
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serial: Optional[str] = None
    laboratorio_id: Optional[int] = None
    estado: str = "DISPONIBLE"


@dataclass
class Edicion:
    id: Optional[int]
    nombre: str
    slug: str
    descripcion: Optional[str] = None
    estado: str = "ACTIVA"
    version_actual: int = 1
    fecha_creacion: Optional[str] = None


@dataclass
class EdicionVersion:
    id: Optional[int]
    edicion_id: int
    numero_version: int
    estado: str = "ACTIVA"
    nombre_version: Optional[str] = None
    creado_por: Optional[int] = None
    notas_cambios: Optional[str] = None
    snapshot_json: str = "{}"
    fecha_creacion: Optional[str] = None


@dataclass
class EdicionConfig:
    id: Optional[int]
    edicion_id: int
    clave: str
    valor: Optional[str] = None


@dataclass
class UsuarioEdicion:
    id: Optional[int]
    usuario_sistema_id: int
    edicion_id: int
    rol_en_edicion: str = "OPERADOR"
    fecha_union: Optional[str] = None
