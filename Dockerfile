# Imagen de producción de TechLoan (Flask + SQLite3 + gunicorn).
#
#   docker build -t techloan .
#   docker run -p 8000:8000 -v techloan_data:/app/database techloan
#
# El volumen es importante: SQLite es un archivo dentro de /app/database. Sin
# volumen, al recrear el contenedor se pierde la base de datos.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TECHLOAN_HOST=0.0.0.0 \
    TECHLOAN_PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Crea la base de datos SOLO si no existe (init_db.py reconstruye y borraría
# datos) y arranca gunicorn.
CMD ["sh", "-c", "[ -f database/techloan.db ] || python init_db.py; exec gunicorn wsgi:app --bind 0.0.0.0:${TECHLOAN_PORT} --workers 2 --timeout 60"]
