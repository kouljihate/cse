from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from app.database import get_db
from app.models.user import UserUpdate, UserResponse
from app.services.audit_service import AuditService
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
@admin_required
def list_users():
    db = get_db()
    role = request.args.get("role")
    query = {}
    if role:
        query["role"] = role
    users = list(db.users.find(query).sort("created_at", -1))
    return jsonify([UserResponse(**u).model_dump(by_alias=True) for u in users]), 200


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
