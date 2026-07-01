from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, make_response
from flask_jwt_extended import JWTManager, decode_token
from config import settings, VERSION
from app.translations import t as translate
from app.socketio_server import socketio

jwt = JWTManager()


def create_app():
    app = Flask(__name__)
    app.secret_key = settings.jwt_secret_key

    app.config["JWT_SECRET_KEY"] = settings.jwt_secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = settings.jwt_access_token_expires
    app.config["MONGO_URI"] = settings.mongo_uri

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

    @app.context_processor
    def inject_globals():
        lang = request.args.get("lang") or request.cookies.get("lang") or "en"
        if lang not in ("en", "ar", "fr"):
            lang = "en"

        def _(key):
            return translate(key, lang)

        user = None
        token = request.cookies.get("access_token")
        if token:
            try:
                decoded = decode_token(token)
                from bson import ObjectId
                from app.database import get_db
                db = get_db()
                user = db.users.find_one({"_id": ObjectId(decoded["sub"])})
            except Exception:
                pass

        user_id = str(user["_id"]) if user else None

        return dict(
            _=_,
            lang=lang,
            user=user,
            user_id=user_id,
            now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            version=VERSION,
        )

    # ── Web Routes ──────────────────────────────────────────

    @app.route("/")
    def index():
        return redirect("/login")

    @app.route("/login")
    def login_page():
        lang = request.args.get("lang", "en")
        resp = make_response(render_template("login.html", lang=lang))
        resp.set_cookie("lang", lang, max_age=365*24*3600)
        return resp

    @app.route("/register")
    def register_page():
        lang = request.args.get("lang", "en")
        resp = make_response(render_template("register.html", lang=lang))
        resp.set_cookie("lang", lang, max_age=365*24*3600)
        return resp

    @app.route("/dashboard")
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
    def tasks_page():
        return render_template("tasks.html", active_page="tasks")

    @app.route("/tasks/create")
    def task_create_page():
        return render_template("task_create.html", active_page="tasks")

    @app.route("/affairs")
    def affairs_page():
        return render_template("affairs.html", active_page="affairs")

    @app.route("/services")
    def services_page():
        return render_template("services.html", active_page="services")

    @app.route("/users")
    def users_page():
        return render_template("users.html", active_page="users")

    @app.route("/reports")
    def reports_page():
        return render_template("reports.html", active_page="reports")

    @app.route("/audit")
    def audit_page():
        return render_template("audit.html", active_page="audit")

    @app.route("/activities")
    def activities_page():
        return render_template("activities.html", active_page="activities")

    @app.route("/notifications")
    def notifications_page():
        return render_template("notifications.html", active_page="notifications")

    @app.route("/employee-dashboard")
    def employee_dashboard_page():
        return render_template("employee_dashboard.html", active_page="employee_dashboard")

    @app.route("/messaging")
    def messaging_page():
        return render_template("messaging.html", active_page="messaging")

    @app.route("/customers")
    def customers_page():
        return render_template("customers.html", active_page="customers")

    @app.route("/customers/<customer_id>")
    def customer_detail_page(customer_id):
        return render_template("customer_detail.html", active_page="customers", customer_id=customer_id)

    socketio.init_app(app, cors_allowed_origins="*")

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    return app
