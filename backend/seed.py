import sys
from pathlib import Path
from datetime import datetime, timezone
from bcrypt import hashpw, gensalt

sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db
from app import create_app

app = create_app()

with app.app_context():
    db = get_db()

    password = hashpw("admin123".encode("utf-8"), gensalt()).decode("utf-8")
    admin = {
        "username": "admin",
        "email": "admin@cse.com",
        "password": password,
        "role": "admin",
        "full_name": "System Administrator",
        "phone": "+1-555-0100",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    existing = db.users.find_one({"username": "admin"})
    if not existing:
        db.users.insert_one(admin)
        print("Admin user created (username: admin, password: admin123)")
    else:
        print("Admin user already exists")

    print("Seed complete!")
