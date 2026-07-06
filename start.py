"""
Development entry point. Just runs backend/run.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

import run  # noqa: E402  (parses --db-host, creates app)

if __name__ == "__main__":
    run.socketio.run(run.app, debug=True, host="0.0.0.0", port=run.args.port, allow_unsafe_werkzeug=True)
