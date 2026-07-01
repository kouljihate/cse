import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app import create_app
from app.socketio_server import socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
