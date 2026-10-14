import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _tempdb  # noqa: E402

# Base de datos temporal: este script NUNCA toca database/techloan.db.
_tempdb.preparar("security_test.db")

from app.database import init_database
from app.services.auth_service import AuthService
from app.services.usuario_service import UsuarioService
init_database()
username="security_admin"; email="security@techloan.local"
try:
    UsuarioService.create({"nombre":"Security","apellido":"Admin","username":username,"email":email,"password":"Secure123!","rol":"ADMINISTRADOR"})
except ValueError:
    pass
user=AuthService.authenticate(username,"Secure123!")
assert user["rol"]=="ADMINISTRADOR" and "password_hash" not in user
try: AuthService.authenticate(username,"' OR 1=1 --")
except ValueError: pass
else: raise AssertionError("Inyección aceptada")
operator=dict(user); operator["rol"]="OPERADOR"
assert AuthService.can(operator,"equipos.read")
assert not AuthService.can(operator,"equipos.delete")
assert not AuthService.can(operator,"usuarios.write")
print("SECURITY_TEST_OK")
