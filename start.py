"""Arranque portable de TechLoan.

No requiere activar manualmente el entorno virtual. Usa un .venv local al
proyecto, por lo que la ruta absoluta de Python cambia libremente entre PCs.
Solo requiere que Python 3.10+ esté instalado y disponible en PATH.
"""

from __future__ import annotations

import ast
import os
import platform
import shutil
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / ".venv"
REQUIREMENTS = BASE_DIR / "requirements.txt"
DATABASE = BASE_DIR / "database" / "techloan.db"
READY_MARKER = VENV_DIR / ".techloan_ready"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _find_system_python() -> str:
    candidates = ["python", "python3"]
    if os.name == "nt":
        candidates.insert(0, "py")

    for command in candidates:
        path = shutil.which(command)
        if path:
            if command == "py":
                probe = [path, "-3", "-c", "import sys; print(sys.version_info[:2])"]
            else:
                probe = [path, "-c", "import sys; print(sys.version_info[:2])"]

            try:
                result = subprocess.run(
                    probe,
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=BASE_DIR,
                )
                version = ast.literal_eval(result.stdout.strip())
                if tuple(version) >= (3, 10):
                    return path
            except Exception:
                continue

    raise SystemExit(
        "No se encontró Python 3.10+ en el PATH. "
        "Instala Python 3.10 o superior y vuelve a ejecutar este archivo."
    )


def _run(command: list[str]) -> None:
    print("> " + " ".join(f'"{x}"' if " " in x else x for x in command))
    subprocess.run(command, cwd=BASE_DIR, check=True)


def _create_venv() -> Path:
    python = _venv_python()

    if python.exists():
        try:
            subprocess.run(
                [str(python), "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                check=True,
            )
            return python
        except (OSError, subprocess.CalledProcessError):
            print("El .venv existente no es utilizable en esta PC. Se reconstruirá.")
            shutil.rmtree(VENV_DIR, ignore_errors=True)

    system_python = _find_system_python()

    if os.name == "nt" and Path(system_python).name.lower() == "py.exe":
        command = [system_python, "-3", "-m", "venv", str(VENV_DIR)]
    else:
        command = [system_python, "-m", "venv", str(VENV_DIR)]

    print("Creando entorno virtual local .venv...")
    _run(command)

    if not python.exists():
        raise SystemExit("No se pudo crear el entorno virtual .venv.")
    return python


def _prepare_environment(python: Path) -> None:
    if not REQUIREMENTS.exists():
        raise SystemExit(f"No se encontró {REQUIREMENTS}")

    if READY_MARKER.exists():
        return

    print("Instalando dependencias del proyecto...")
    _run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    READY_MARKER.write_text(
        f"TechLoan preparado con Python {platform.python_version()}\n",
        encoding="utf-8",
    )


def _prepare_database(python: Path) -> None:
    if DATABASE.exists():
        return

    print("No existe la base de datos. Inicializándola desde schema.sql...")
    _run([str(python), str(BASE_DIR / "init_db.py")])


def main() -> None:
    os.chdir(BASE_DIR)
    print("=" * 62)
    print(" TechLoan - arranque portable")
    print("=" * 62)
    print(f"Proyecto: {BASE_DIR}")

    python = _create_venv()
    _prepare_environment(python)
    _prepare_database(python)

    print()
    print("Servidor iniciando en http://127.0.0.1:5000")
    print("No es necesario activar .venv manualmente.")
    print("Presiona Ctrl+C para detener el servidor.")
    print()

    _run([str(python), str(BASE_DIR / "run_server.py")])


if __name__ == "__main__":
    main()
