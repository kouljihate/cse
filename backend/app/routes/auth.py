from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from bcrypt import hashpw, gensalt, checkpw
from bson import ObjectId
from app.database import get_db
from app.models.user import UserCreate, UserLogin, UserResponse
from app.services.audit_service import AuditService
from config import settings

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    try:
        user_data = UserCreate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    db = get_db()

    if db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]}):
        return jsonify({"error": "Username or email already exists"}), 409

    user_dict = user_data.model_dump(by_alias=True)
    user_dict["password"] = hashpw(user_dict["password"].encode("utf-8"), gensalt()).decode("utf-8")
    user_dict["created_at"] = datetime.now(timezone.utc)
    user_dict["updated_at"] = datetime.now(timezone.utc)

    result = db.users.insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)

    AuditService.log(
        action="create",
        entity_type="user",
        entity_id=str(result.inserted_id),
        performed_by=str(result.inserted_id),
        description=f"User {user_data.username} registered",
    )

    return jsonify(UserResponse(**user_dict).model_dump(by_alias=True)), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    try:
        login_data = UserLogin(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    db = get_db()
    user = db.users.find_one({"username": login_data.username})

    if not user or not checkpw(login_data.password.encode("utf-8"), user["password"].encode("utf-8")):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.get("is_active", True):
        return jsonify({"error": "Account is disabled"}), 403

    access_token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={"role": user["role"], "username": user["username"]},
    )

    resp = jsonify({
        "access_token": access_token,
        "user": UserResponse(**user).model_dump(by_alias=True),
    })
    resp.set_cookie(
        "access_token", access_token,
        max_age=settings.jwt_access_token_expires,
        httponly=False,
        samesite="Lax",
        path="/",
    )
    return resp, 200


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    db = get_db()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(UserResponse(**user).model_dump(by_alias=True)), 200
