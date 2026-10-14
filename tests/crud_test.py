import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _tempdb  # noqa: E402

# Base de datos temporal: este script NUNCA toca database/techloan.db.
_tempdb.preparar("crud_test.db")

from app.database import init_database, get_connection
from app.services.prestatario_service import PrestatarioService
from app.services.laboratorio_service import LaboratorioService
from app.services.categoria_service import CategoriaService
from app.services.equipo_service import EquipoService

init_database()

# Crear
p = PrestatarioService.create({
    "cedula":"CRUD-P01","nombre":"Ana","apellido":"Prueba",
    "tipo":"ESTUDIANTE","email":"ana.crud@test.local"
})
l = LaboratorioService.create({
    "codigo":"CRUD-L01","nombre":"Lab CRUD","ubicacion":"Aula 2","capacidad":20
})
c = CategoriaService.create({"nombre":"CRUD Categoria","descripcion":"Prueba"})
e = EquipoService.create({
    "codigo":"CRUD-E01","nombre":"Equipo CRUD","categoria_id":c,
    "laboratorio_id":l,"marca":"Demo","modelo":"M1","serial":"CRUD-S01"
})

assert PrestatarioService.get(p)
assert LaboratorioService.get(l)
assert CategoriaService.get(c)
assert EquipoService.get(e)

# Leer
assert len(PrestatarioService.list_all()) >= 1
assert len(LaboratorioService.list_all()) >= 1
assert len(CategoriaService.list_all()) >= 1
assert len(EquipoService.list_all()) >= 1

# Actualizar
PrestatarioService.update(p, {
    "cedula":"CRUD-P01","nombre":"Ana","apellido":"Actualizada",
    "tipo":"PROFESOR","email":"ana2.crud@test.local"
})
LaboratorioService.update(l, {
    "codigo":"CRUD-L01","nombre":"Lab CRUD 2","ubicacion":"Aula 3","capacidad":25
})
CategoriaService.update(c, {"nombre":"CRUD Categoria 2","descripcion":"Actualizada"})
EquipoService.update(e, {
    "codigo":"CRUD-E01","nombre":"Equipo CRUD 2","categoria_id":c,
    "laboratorio_id":l,"marca":"Demo","modelo":"M2","serial":"CRUD-S01"
})

assert PrestatarioService.get(p)["tipo"] == "PROFESOR"
assert LaboratorioService.get(l)["capacidad"] == 25
assert CategoriaService.get(c)["nombre"] == "CRUD Categoria 2"
assert EquipoService.get(e)["modelo"] == "M2"

# Eliminar
EquipoService.delete(e)
CategoriaService.delete(c)
LaboratorioService.delete(l)
PrestatarioService.delete(p)

assert EquipoService.get(e) is None
assert CategoriaService.get(c) is None
assert LaboratorioService.get(l) is None
assert PrestatarioService.get(p) is None

print("CRUD_TEST_OK")
