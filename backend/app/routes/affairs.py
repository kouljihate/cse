from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from app.database import get_db
from app.models.affair import AffairCreate, AffairUpdate, AffairResponse
from app.services.audit_service import AuditService
from functools import wraps

affairs_bp = Blueprint("affairs", __name__, url_prefix="/api/affairs")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@affairs_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_affair():
    db = get_db()
    data = request.get_json()
    try:
        affair_data = AffairCreate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if not db.users.find_one({"_id": ObjectId(affair_data.customer_id), "role": "customer"}):
        return jsonify({"error": "Customer not found"}), 404

    affair_dict = affair_data.model_dump(by_alias=True)
    affair_dict["customer_id"] = ObjectId(affair_dict["customer_id"])
    affair_dict["created_at"] = datetime.now(timezone.utc)
    affair_dict["updated_at"] = datetime.now(timezone.utc)

    result = db.affairs.insert_one(affair_dict)
    affair_dict["_id"] = str(result.inserted_id)

    AuditService.log(
        action="create",
        entity_type="affair",
        entity_id=str(result.inserted_id),
        performed_by=get_jwt_identity(),
        description=f"Affair '{affair_data.name}' created for customer",
    )

    return jsonify(AffairResponse(**affair_dict).model_dump(by_alias=True)), 201


@affairs_bp.route("/", methods=["GET"])
@jwt_required()
def list_affairs():
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    query = {}
    customer_id = request.args.get("customer_id")
    if customer_id:
        query["customer_id"] = ObjectId(customer_id)

    if role == "customer":
        query["customer_id"] = ObjectId(identity)

    pipeline = [
        {"$match": query},
        {"$sort": {"name": 1}},
        {
            "$lookup": {
                "from": "users",
                "localField": "customer_id",
                "foreignField": "_id",
                "as": "customer",
            }
        },
        {"$unwind": {"path": "$customer", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "customer_name": "$customer.full_name",
            }
        },
        {"$project": {"customer": 0}},
    ]

    affairs = list(db.affairs.aggregate(pipeline))
    return jsonify([AffairResponse(**a).model_dump(by_alias=True) for a in affairs]), 200


@affairs_bp.route("/<affair_id>", methods=["GET"])
@jwt_required()
def get_affair(affair_id):
    db = get_db()
    pipeline = [
        {"$match": {"_id": ObjectId(affair_id)}},
        {
            "$lookup": {
                "from": "users",
                "localField": "customer_id",
                "foreignField": "_id",
                "as": "customer",
            }
        },
        {"$unwind": {"path": "$customer", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "customer_name": "$customer.full_name",
            }
        },
        {"$project": {"customer": 0}},
    ]
    affairs = list(db.affairs.aggregate(pipeline))
    if not affairs:
        return jsonify({"error": "Affair not found"}), 404
    return jsonify(AffairResponse(**affairs[0]).model_dump(by_alias=True)), 200


@affairs_bp.route("/<affair_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_affair(affair_id):
    db = get_db()
    data = request.get_json()
    try:
        update_data = AffairUpdate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
    if not update_dict:
        return jsonify({"error": "No fields to update"}), 400

    update_dict["updated_at"] = datetime.now(timezone.utc)

    old = db.affairs.find_one({"_id": ObjectId(affair_id)})
    if not old:
        return jsonify({"error": "Affair not found"}), 404

    db.affairs.update_one({"_id": ObjectId(affair_id)}, {"$set": update_dict})

    AuditService.log(
        action="update",
        entity_type="affair",
        entity_id=affair_id,
        performed_by=get_jwt_identity(),
        changes={"before": {k: str(old.get(k)) for k in update_dict}, "after": {k: str(v) for k, v in update_dict.items()}},
        description=f"Affair '{old.get('name')}' updated",
    )

    updated = db.affairs.find_one({"_id": ObjectId(affair_id)})
    return jsonify(AffairResponse(**updated).model_dump(by_alias=True)), 200


@affairs_bp.route("/<affair_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_affair(affair_id):
    db = get_db()
    affair = db.affairs.find_one({"_id": ObjectId(affair_id)})
    if not affair:
        return jsonify({"error": "Affair not found"}), 404

    db.affairs.delete_one({"_id": ObjectId(affair_id)})

    AuditService.log(
        action="delete",
        entity_type="affair",
        entity_id=affair_id,
        performed_by=get_jwt_identity(),
        description=f"Affair '{affair.get('name')}' deleted",
    )

    return jsonify({"message": "Affair deleted"}), 200
