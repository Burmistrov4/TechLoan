"""Punto de entrada WSGI para producción.

Los servidores de producción (gunicorn, uWSGI, waitress, PythonAnywhere) buscan
un objeto importable —normalmente llamado ``app`` o ``application``— en lugar de
ejecutar un script. En local se sigue usando ``run_server.py`` o ``start.py``.

Con gunicorn::

    gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2

En PythonAnywhere, el archivo WSGI de la pestaña «Web» debe importar
``create_app`` desde aquí (ver ``deploy/pythonanywhere_wsgi.py``).
"""

from app.server import create_app

# Objeto que importan los servidores WSGI.
app = create_app()
application = app  # alias que espera PythonAnywhere


if __name__ == "__main__":
    from app.config import HOST, PORT

    app.run(host=HOST, port=PORT, debug=False)
