from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from app.database import get_db
from app.models.user import UserCreate, UserUpdate, UserResponse
from app.services.audit_service import AuditService
from bcrypt import hashpw, gensalt
from functools import wraps

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@users_bp.route("/", methods=["GET"])
@jwt_required()
def list_users():
    db = get_db()
    role = request.args.get("role")
    status = request.args.get("status")
    query = {}
    if role:
        query["role"] = role
    if status == "active":
        query["is_active"] = True
    elif status == "inactive":
        query["is_active"] = False
    users = list(db.users.find(query).sort("created_at", -1))
    return jsonify([UserResponse(**u).model_dump(by_alias=True) for u in users]), 200


@users_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_user():
    db = get_db()
    data = request.get_json()
    try:
        user_data = UserCreate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
        performed_by=get_jwt_identity(),
        description=f"User {user_data.username} created",
    )

    return jsonify(UserResponse(**user_dict).model_dump(by_alias=True)), 201


@users_bp.route("/<user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    db = get_db()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(UserResponse(**user).model_dump(by_alias=True)), 200


@users_bp.route("/<user_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_user(user_id):
    db = get_db()
    data = request.get_json()
    try:
        update_data = UserUpdate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    update_dict = {k: v for k, v in update_data.model_dump(by_alias=True).items() if v is not None}
    if not update_dict:
        return jsonify({"error": "No fields to update"}), 400

    update_dict["updated_at"] = datetime.now(timezone.utc)

    old_user = db.users.find_one({"_id": ObjectId(user_id)})
    if not old_user:
        return jsonify({"error": "User not found"}), 404

    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_dict})

    AuditService.log(
        action="update",
        entity_type="user",
        entity_id=user_id,
        performed_by=get_jwt_identity(),
        changes={"before": {k: str(old_user.get(k)) for k in update_dict}, "after": {k: str(v) for k, v in update_dict.items()}},
        description=f"User {old_user.get('username')} updated",
    )

    updated = db.users.find_one({"_id": ObjectId(user_id)})
    return jsonify(UserResponse(**updated).model_dump(by_alias=True)), 200


@users_bp.route("/<user_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_user(user_id):
    db = get_db()
    current_user_id = get_jwt_identity()
    if current_user_id == user_id:
        return jsonify({"error": "Cannot delete yourself"}), 400

    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.users.delete_one({"_id": ObjectId(user_id)})

    AuditService.log(
        action="delete",
        entity_type="user",
        entity_id=user_id,
        performed_by=current_user_id,
        description=f"User {user.get('username')} deleted",
    )

    return jsonify({"message": "User deleted"}), 200


@users_bp.route("/employees", methods=["GET"])
@jwt_required()
def list_employees():
    db = get_db()
    employees = list(db.users.find({"role": "employee", "is_active": True}).sort("full_name", 1))
    return jsonify([UserResponse(**e).model_dump(by_alias=True) for e in employees]), 200



