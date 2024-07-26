from app import app
from config import server

if __name__ == '__main__':
    app.run(host=server.SERVER_DOMAIN, port=server.SERVER_PORT, debug=True)
