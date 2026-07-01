from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from app.database import get_db
from app.models.user import UserCreate, UserUpdate, UserResponse
from app.services.audit_service import AuditService
from functools import wraps

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@customers_bp.route("/", methods=["GET"])
@jwt_required()
def list_customers():
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    query = {"role": "customer"}
    if role == "customer":
        query["_id"] = ObjectId(identity)

    customers = list(
        db.users.find(query).sort("full_name", 1)
    )

    result = []
    for c in customers:
        affair_count = db.affairs.count_documents({"customer_id": c["_id"]})

        resp = UserResponse(**c).model_dump(by_alias=True)
        resp["affair_count"] = affair_count
        result.append(resp)

    return jsonify(result), 200


@customers_bp.route("/<customer_id>", methods=["GET"])
@jwt_required()
def get_customer(customer_id):
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    query = {"_id": ObjectId(customer_id), "role": "customer"}
    if role == "customer" and identity != customer_id:
        return jsonify({"error": "Forbidden"}), 403

    customer = db.users.find_one(query)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    affairs = list(db.affairs.find({"customer_id": customer["_id"]}))
    affair_ids = [a["_id"] for a in affairs]

    task_stats = {}
    if affair_ids:
        task_stats = {
            "total": db.tasks.count_documents({"affair_id": {"$in": affair_ids}}),
            "open": db.tasks.count_documents({"affair_id": {"$in": affair_ids}, "status": {"$in": ["pending", "in_progress"]}}),
            "completed": db.tasks.count_documents({"affair_id": {"$in": affair_ids}, "status": "completed"}),
        }

    resp = UserResponse(**customer).model_dump(by_alias=True)
    resp["affair_count"] = len(affairs)
    resp["task_stats"] = task_stats
    return jsonify(resp), 200


@customers_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_customer():
    db = get_db()
    data = request.get_json()
    try:
        user_data = UserCreate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    user_data.role = "customer"

    if db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]}):
        return jsonify({"error": "Username or email already exists"}), 409

    user_dict = user_data.model_dump(by_alias=True)
    from bcrypt import hashpw, gensalt
    user_dict["password"] = hashpw(user_dict["password"].encode("utf-8"), gensalt()).decode("utf-8")
    user_dict["created_at"] = datetime.now(timezone.utc)
    user_dict["updated_at"] = datetime.now(timezone.utc)

    result = db.users.insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)

    AuditService.log(
        action="create",
        entity_type="customer",
        entity_id=str(result.inserted_id),
        performed_by=get_jwt_identity(),
        description=f"Customer {user_data.username} created",
    )

    return jsonify(UserResponse(**user_dict).model_dump(by_alias=True)), 201


@customers_bp.route("/bulk", methods=["POST"])
@jwt_required()
@admin_required
def bulk_create_customers():
    db = get_db()
    data = request.get_json()

    if not isinstance(data, list):
        return jsonify({"error": "Expected a JSON array of customers"}), 400

    if len(data) > 500:
        return jsonify({"error": "Maximum 500 customers per bulk import"}), 400

    from bcrypt import hashpw, gensalt

    results = {"created": 0, "skipped": [], "errors": []}
    now = datetime.now(timezone.utc)

    for i, item in enumerate(data):
        try:
            username = item.get("username", "").strip()
            email = item.get("email", "").strip()
            full_name = item.get("full_name", "").strip()
            password = item.get("password", "customer123")
            phone = item.get("phone", "").strip()

            if not username or not email or not full_name:
                results["errors"].append({"row": i, "reason": "Missing required fields (username, email, full_name)", "data": item})
                continue

            if db.users.find_one({"$or": [{"username": username}, {"email": email}]}):
                results["skipped"].append({"row": i, "reason": "Username or email already exists", "username": username})
                continue

            user_dict = {
                "username": username,
                "email": email,
                "password": hashpw(password.encode("utf-8"), gensalt()).decode("utf-8"),
                "role": "customer",
                "full_name": full_name,
                "phone": phone or None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }

            result = db.users.insert_one(user_dict)

            AuditService.log(
                action="create",
                entity_type="customer",
                entity_id=str(result.inserted_id),
                performed_by=get_jwt_identity(),
                description=f"Customer {username} created (bulk import)",
            )

            results["created"] += 1

        except Exception as e:
            results["errors"].append({"row": i, "reason": str(e), "data": item})

    return jsonify(results), 201


@customers_bp.route("/<customer_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_customer(customer_id):
    db = get_db()
    data = request.get_json()

    customer = db.users.find_one({"_id": ObjectId(customer_id), "role": "customer"})
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    update_dict = {}
    if "full_name" in data:
        update_dict["full_name"] = data["full_name"]
    if "email" in data:
        update_dict["email"] = data["email"]
    if "phone" in data:
        update_dict["phone"] = data["phone"]
    if "is_active" in data:
        update_dict["is_active"] = data["is_active"]

    if not update_dict:
        return jsonify({"error": "No fields to update"}), 400

    update_dict["updated_at"] = datetime.now(timezone.utc)
    db.users.update_one({"_id": ObjectId(customer_id)}, {"$set": update_dict})

    AuditService.log(
        action="update",
        entity_type="customer",
        entity_id=customer_id,
        performed_by=get_jwt_identity(),
        description=f"Customer {customer.get('username')} updated",
    )

    updated = db.users.find_one({"_id": ObjectId(customer_id)})
    return jsonify(UserResponse(**updated).model_dump(by_alias=True)), 200


@customers_bp.route("/<customer_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_customer(customer_id):
    db = get_db()
    customer = db.users.find_one({"_id": ObjectId(customer_id), "role": "customer"})
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    affairs = list(db.affairs.find({"customer_id": ObjectId(customer_id)}))
    for affair in affairs:
        AuditService.log(
            action="delete",
            entity_type="affair",
            entity_id=str(affair["_id"]),
            performed_by=get_jwt_identity(),
            description=f"Affair '{affair.get('name')}' deleted (customer cascade)",
        )
    db.affairs.delete_many({"customer_id": ObjectId(customer_id)})
    db.users.delete_one({"_id": ObjectId(customer_id)})

    AuditService.log(
        action="delete",
        entity_type="customer",
        entity_id=customer_id,
        performed_by=get_jwt_identity(),
        description=f"Customer {customer.get('username')} deleted",
    )

    return jsonify({"message": "Customer deleted"}), 200
