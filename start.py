import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from config import settings
from app import create_app
from app.socketio_server import socketio

parser = argparse.ArgumentParser()
parser.add_argument("--db_host", help="MongoDB host IP (e.g. 192.168.1.100)")
args, _ = parser.parse_known_args()

db_host = args.db_host or settings.mongo_host
if not db_host:
    parser.error("--db_host is required (set it in .env or pass as argument)")

settings.mongo_uri = f"mongodb://{db_host}:27017/cse"

app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
