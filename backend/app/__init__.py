import os
import sys
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import quote
from flask import Flask, render_template, request, redirect, make_response
from flask_jwt_extended import JWTManager, decode_token
from config import settings, VERSION
from app.translations import t as translate
from app.socketio_server import socketio

jwt = JWTManager()


def _app_root():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "app")
    return os.path.dirname(os.path.abspath(__file__))


def current_user():
    """Return the logged-in user document, or None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        decoded = decode_token(token)
        from bson import ObjectId
        from app.database import get_db
        return get_db().users.find_one({"_id": ObjectId(decoded["sub"])})
    except Exception:
        return None


def login_required_page(view):
    """Send anonymous visitors to the login page instead of rendering a shell."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            target = request.path
            if request.query_string:
                target += "?" + request.query_string.decode()
            return redirect("/login?next=" + quote(target, safe="/?=&"))
        return view(*args, **kwargs)
    return wrapper


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(_app_root(), "templates"),
        static_folder=os.path.join(_app_root(), "static"),
        static_url_path="/static",
    )
    app.secret_key = settings.jwt_secret_key

    app.config["JWT_SECRET_KEY"] = settings.jwt_secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = settings.jwt_access_token_expires
    app.config["MONGO_URI"] = settings.mongo_uri
    # The session token lives in an HttpOnly cookie. Bearer headers stay
    # accepted so existing API clients keep working.
    app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token"
    app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"
    app.config["JWT_COOKIE_SECURE"] = settings.cookie_secure
    # SameSite=Lax plus a same-origin app covers CSRF, and the double-submit
    # header would need client changes on every mutating request.
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False

    jwt.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.affairs import affairs_bp
    from app.routes.services import services_bp
    from app.routes.tasks import tasks_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.reports import reports_bp
    from app.routes.audit import audit_bp
    from app.routes.customers import customers_bp
    from app.routes.activities import activities_bp
    from app.routes.requests import requests_bp
    from app.routes.documents import documents_bp
    from app.routes.company import company_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(affairs_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(company_bp)

    @app.context_processor
    def inject_globals():
        lang = request.args.get("lang") or request.cookies.get("lang") or "en"
        if lang not in ("en", "ar", "fr"):
            lang = "en"

        def _(key):
            return translate(key, lang)

        user = current_user()
        token = request.cookies.get("access_token")

        user_id = str(user["_id"]) if user else None

        company = None
        if token:
            try:
                from app.database import get_db
                db = get_db()
                company = db.company_settings.find_one()
            except Exception:
                pass

        return dict(
            _=_,
            lang=lang,
            user=user,
            user_id=user_id,
            now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            version=VERSION,
            company=company,
        )

    # ── Web Routes ──────────────────────────────────────────

    @app.route("/")
    def index():
        return redirect("/login")

    @app.route("/login")
    def login_page():
        if current_user() is not None:
            return redirect("/dashboard")
        lang = request.args.get("lang", "en")
        nxt = request.args.get("next", "")
        if not nxt.startswith("/") or nxt.startswith("//"):
            nxt = ""
        company = None
        try:
            from app.database import get_db
            db = get_db()
            company = db.company_settings.find_one()
        except Exception:
            pass
        resp = make_response(render_template("login.html", lang=lang, company=company, next_url=nxt))
        resp.set_cookie("lang", lang, max_age=365*24*3600)
        return resp

    @app.route("/register")
    def register_page():
        lang = request.args.get("lang", "en")
        company = None
        try:
            from app.database import get_db
            db = get_db()
            company = db.company_settings.find_one()
        except Exception:
            pass
        resp = make_response(render_template("register.html", lang=lang, company=company))
        resp.set_cookie("lang", lang, max_age=365*24*3600)
        return resp

    @app.route("/dashboard")
    @login_required_page
    def dashboard_page():
        token = request.cookies.get("access_token")
        if token:
            try:
                decoded = decode_token(token)
                claims = decoded
                if claims.get("role") == "employee":
                    return redirect("/employee-dashboard")
            except Exception:
                pass
        return render_template("dashboard.html", active_page="dashboard")

    @app.route("/tasks")
    @login_required_page
    def tasks_page():
        return render_template("tasks.html", active_page="tasks")

    @app.route("/tasks/create")
    @login_required_page
    def task_create_page():
        return render_template("task_create.html", active_page="tasks")

    @app.route("/affairs")
    @login_required_page
    def affairs_page():
        return render_template("affairs.html", active_page="affairs")

    @app.route("/services")
    @login_required_page
    def services_page():
        return render_template("services.html", active_page="services")

    @app.route("/users")
    @login_required_page
    def users_page():
        return render_template("users.html", active_page="users")

    @app.route("/reports")
    @login_required_page
    def reports_page():
        return render_template("reports.html", active_page="reports")

    @app.route("/audit")
    @login_required_page
    def audit_page():
        return render_template("audit.html", active_page="audit")

    @app.route("/activities")
    @login_required_page
    def activities_page():
        return render_template("activities.html", active_page="activities")

    @app.route("/notifications")
    @login_required_page
    def notifications_page():
        return render_template("notifications.html", active_page="notifications")

    @app.route("/employee-dashboard")
    @login_required_page
    def employee_dashboard_page():
        return render_template("employee_dashboard.html", active_page="employee_dashboard")

    @app.route("/messaging")
    @login_required_page
    def messaging_page():
        return render_template("messaging.html", active_page="messaging")

    @app.route("/customers")
    @login_required_page
    def customers_page():
        return render_template("customers.html", active_page="customers")

    @app.route("/customers/<customer_id>")
    @login_required_page
    def customer_detail_page(customer_id):
        return render_template("customer_detail.html", active_page="customers", customer_id=customer_id)

    @app.route("/requests")
    @login_required_page
    def requests_page():
        return render_template("requests.html", active_page="requests")

    @app.route("/documents")
    @login_required_page
    def documents_page():
        return render_template("documents.html", active_page="documents")

    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    @app.route("/api/health")
    def health():
        from app.database import get_db
        try:
            get_db().command("ping")
            return {"status": "ok", "db": "connected", "version": VERSION}
        except Exception:
            return {"status": "error", "db": "disconnected", "version": VERSION}, 503

    return app
