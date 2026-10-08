# Guía rápida de levantamiento — TechLoan

## Windows — método recomendado

1. Instala **Python 3.10 o superior**.
2. Descomprime el proyecto.
3. Entra en la carpeta del proyecto.
4. Haz doble clic en:

`iniciar.bat`

El lanzador crea automáticamente el entorno virtual local, instala las dependencias y prepara
SQLite si todavía no existe.

Abre:

`http://127.0.0.1:5000`

## Windows — PowerShell

Desde la raíz del proyecto:

```powershell
.\iniciar.ps1
```

## Linux / macOS

```bash
chmod +x iniciar.sh
./iniciar.sh
```

## Arranque manual

Si se desea controlar cada paso:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python init_db.py
python run_server.py
```

## Credenciales de demostración

- `admin` / `Admin123!`
- `operador` / `Operador123!`

## Importante

- No copies el `.venv` de otra computadora.
- No ejecutes `init_db.py` sobre una base de datos con información que quieras conservar:
  reconstruye las tablas.
- Si solo quieres levantar el proyecto y la base de datos ya existe, utiliza `iniciar.bat`.
- Si cambias de PC, el lanzador reconstruye el entorno Python local automáticamente.

## Producción

Consulta la sección **14. Despliegue en producción** del `README.md`.

Para la arquitectura actual, la opción más sencilla es **Flask + Jinja2 completo en Render**.
GitHub Pages y Cloudflare Pages requieren convertir el frontend en un cliente HTML/CSS/JS
estático que consuma la API Flask mediante HTTPS; no pueden ejecutar directamente los templates
Jinja2 ni Python.

Para producción real también se recomienda migrar SQLite a PostgreSQL.
