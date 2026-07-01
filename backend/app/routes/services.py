from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from app.database import get_db
from app.models.service import ServiceCreate, ServiceUpdate, ServiceResponse
from app.services.audit_service import AuditService
from functools import wraps

services_bp = Blueprint("services", __name__, url_prefix="/api/services")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


def _update_task_assignments(service_id, task_ids, performed_by):
    """Assign/unassign tasks to/from a service. Keeps service doc task_ids in sync."""
    db = get_db()
    old_tasks = list(db.tasks.find({"service_id": ObjectId(service_id)}, {"_id": 1}))
    old_ids = {str(t["_id"]) for t in old_tasks}
    new_ids = set(task_ids or [])

    to_add = new_ids - old_ids
    to_remove = old_ids - new_ids

    if to_add:
        tasks = list(db.tasks.find({"_id": {"$in": [ObjectId(tid) for tid in to_add]}}, {"title": 1}))
        db.tasks.update_many(
            {"_id": {"$in": [ObjectId(tid) for tid in to_add]}},
            {"$set": {"service_id": ObjectId(service_id), "updated_at": datetime.now(timezone.utc)}},
        )
        for task in tasks:
            AuditService.log(
                action="update",
                entity_type="task",
                entity_id=str(task["_id"]),
                performed_by=performed_by,
                description=f"Task '{task.get('title')}' assigned to service",
            )
    if to_remove:
        tasks = list(db.tasks.find({"_id": {"$in": [ObjectId(tid) for tid in to_remove]}}, {"title": 1}))
        db.tasks.update_many(
            {"_id": {"$in": [ObjectId(tid) for tid in to_remove]}},
            {"$unset": {"service_id": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        )
        for task in tasks:
            AuditService.log(
                action="update",
                entity_type="task",
                entity_id=str(task["_id"]),
                performed_by=performed_by,
                description=f"Task '{task.get('title')}' unassigned from service",
            )

    # Keep the service document's task_ids array in sync
    db.services.update_one(
        {"_id": ObjectId(service_id)},
        {"$set": {"task_ids": [ObjectId(tid) for tid in new_ids], "updated_at": datetime.now(timezone.utc)}},
    )


@services_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_service():
    db = get_db()
    data = request.get_json()
    task_ids = data.pop("task_ids", None)
    if not task_ids or len(task_ids) < 1:
        return jsonify({"error": "At least one task must be assigned to the service"}), 400
    try:
        service_data = ServiceCreate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    service_dict = service_data.model_dump()
    service_dict["task_ids"] = [ObjectId(tid) for tid in (task_ids or [])]
    service_dict["created_at"] = datetime.now(timezone.utc)
    service_dict["updated_at"] = datetime.now(timezone.utc)

    result = db.services.insert_one(service_dict)
    sid = str(result.inserted_id)
    service_dict["_id"] = sid

    if task_ids:
        _update_task_assignments(sid, task_ids, get_jwt_identity())

    AuditService.log(
        action="create",
        entity_type="service",
        entity_id=sid,
        performed_by=get_jwt_identity(),
        description=f"Service '{service_data.name}' created",
    )

    return jsonify(ServiceResponse(**service_dict).model_dump(by_alias=True)), 201


@services_bp.route("/", methods=["GET"])
@jwt_required()
def list_services():
    db = get_db()
    services = list(db.services.find().sort("name", 1))
    return jsonify([ServiceResponse(**s).model_dump(by_alias=True) for s in services]), 200


@services_bp.route("/<service_id>", methods=["GET"])
@jwt_required()
def get_service(service_id):
    db = get_db()
    service = db.services.find_one({"_id": ObjectId(service_id)})
    if not service:
        return jsonify({"error": "Service not found"}), 404
    return jsonify(ServiceResponse(**service).model_dump(by_alias=True)), 200


@services_bp.route("/<service_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_service(service_id):
    db = get_db()
    data = request.get_json()
    task_ids = data.pop("task_ids", None)
    if task_ids is not None and len(task_ids) < 1:
        return jsonify({"error": "At least one task must be assigned to the service"}), 400
    try:
        update_data = ServiceUpdate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
    if not update_dict and task_ids is None:
        return jsonify({"error": "No fields to update"}), 400

    update_dict["updated_at"] = datetime.now(timezone.utc)

    old = db.services.find_one({"_id": ObjectId(service_id)})
    if not old:
        return jsonify({"error": "Service not found"}), 404

    if update_dict:
        db.services.update_one({"_id": ObjectId(service_id)}, {"$set": update_dict})

    if task_ids is not None:
        _update_task_assignments(service_id, task_ids, get_jwt_identity())

    AuditService.log(
        action="update",
        entity_type="service",
        entity_id=service_id,
        performed_by=get_jwt_identity(),
        changes={"before": {k: str(old.get(k)) for k in update_dict}, "after": {k: str(v) for k, v in update_dict.items()}},
        description=f"Service '{old.get('name')}' updated",
    )

    updated = db.services.find_one({"_id": ObjectId(service_id)})
    return jsonify(ServiceResponse(**updated).model_dump(by_alias=True)), 200


@services_bp.route("/<service_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_service(service_id):
    db = get_db()
    service = db.services.find_one({"_id": ObjectId(service_id)})
    if not service:
        return jsonify({"error": "Service not found"}), 404

    db.services.delete_one({"_id": ObjectId(service_id)})

    AuditService.log(
        action="delete",
        entity_type="service",
        entity_id=service_id,
        performed_by=get_jwt_identity(),
        description=f"Service '{service.get('name')}' deleted",
    )

    return jsonify({"message": "Service deleted"}), 200
