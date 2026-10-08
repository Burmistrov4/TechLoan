from app.server import create_app
from app.config import HOST, PORT

if __name__ == "__main__":
    create_app().run(host=HOST, port=PORT, debug=False)
