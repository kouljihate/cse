"""
Entry point for CSE Backend Server.
Works with both `python run.py` and PyInstaller-packaged builds.
"""
import os
import sys
import argparse
from pathlib import Path

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load .env from executable's directory when packaged
if getattr(sys, "frozen", False):
    env_path = Path(sys.executable).parent / ".env"
    if env_path.exists():
        os.environ.setdefault("CSE_ENV_FILE", str(env_path))
        from dotenv import load_dotenv
        load_dotenv(env_path)

from config import settings
from app import create_app
from app.socketio_server import socketio

parser = argparse.ArgumentParser(description="CSE Backend Server")
parser.add_argument("--db-host", help="MongoDB host IP (e.g. 192.168.1.100)")
parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
args, _ = parser.parse_known_args()

db_host = args.db_host or settings.mongo_host
if not db_host and not any("pytest" in a for a in sys.argv):
    print("ERROR: --db-host is required (set MONGO_HOST in .env or pass as argument)")
    print("Usage: python run.py --db-host 192.168.1.100")
    sys.exit(1)

if db_host:
    settings.mongo_uri = f"mongodb://{db_host}:27017/cse"

app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=args.debug or True, host="0.0.0.0", port=args.port, allow_unsafe_werkzeug=True)
