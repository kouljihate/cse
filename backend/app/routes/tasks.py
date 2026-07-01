from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from app.database import get_db
from app.models.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.audit_service import AuditService
from functools import wraps

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@tasks_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_task():
    db = get_db()
    data = request.get_json()
    try:
        task_data = TaskCreate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    task_dict = task_data.model_dump()
    task_dict["created_by"] = ObjectId(get_jwt_identity())
    task_dict["created_at"] = datetime.now(timezone.utc)
    task_dict["updated_at"] = datetime.now(timezone.utc)

    result = db.tasks.insert_one(task_dict)
    task_dict["_id"] = str(result.inserted_id)

    AuditService.log(
        action="create",
        entity_type="task",
        entity_id=str(result.inserted_id),
        performed_by=get_jwt_identity(),
        description=f"Task '{task_data.title}' created",
    )

    return jsonify(TaskResponse(**task_dict).model_dump(by_alias=True)), 201


@tasks_bp.route("/", methods=["GET"])
@jwt_required()
def list_tasks():
    db = get_db()
    query = {}

    status = request.args.get("status")
    if status:
        query["status"] = status

    sort_field = request.args.get("sort", "created_at")
    sort_order = -1 if request.args.get("order", "desc") == "desc" else 1

    tasks = list(db.tasks.find(query).sort(sort_field, sort_order))
    return jsonify([TaskResponse(**t).model_dump(by_alias=True) for t in tasks]), 200


@tasks_bp.route("/<task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id):
    db = get_db()
    task = db.tasks.find_one({"_id": ObjectId(task_id)})
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(TaskResponse(**task).model_dump(by_alias=True)), 200


@tasks_bp.route("/<task_id>", methods=["PUT"])
@jwt_required()
def update_task(task_id):
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    data = request.get_json()

    try:
        update_data = TaskUpdate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
    if not update_dict:
        return jsonify({"error": "No fields to update"}), 400

    update_dict["updated_at"] = datetime.now(timezone.utc)

    old = db.tasks.find_one({"_id": ObjectId(task_id)})
    if not old:
        return jsonify({"error": "Task not found"}), 404

    db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": update_dict})

    AuditService.log(
        action="update",
        entity_type="task",
        entity_id=task_id,
        performed_by=identity,
        changes={"before": {k: str(old.get(k)) for k in update_dict}, "after": {k: str(v) for k, v in update_dict.items()}},
        description=f"Task '{old.get('title')}' updated",
    )

    updated = db.tasks.find_one({"_id": ObjectId(task_id)})
    return jsonify(TaskResponse(**updated).model_dump(by_alias=True)), 200


@tasks_bp.route("/<task_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_task(task_id):
    db = get_db()
    task = db.tasks.find_one({"_id": ObjectId(task_id)})
    if not task:
        return jsonify({"error": "Task not found"}), 404

    db.tasks.delete_one({"_id": ObjectId(task_id)})

    AuditService.log(
        action="delete",
        entity_type="task",
        entity_id=task_id,
        performed_by=get_jwt_identity(),
        description=f"Task '{task.get('title')}' deleted",
    )

    return jsonify({"message": "Task deleted"}), 200
