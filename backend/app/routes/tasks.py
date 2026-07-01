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

    if not db.users.find_one({"_id": ObjectId(task_data.assigned_to), "role": "employee"}):
        return jsonify({"error": "Assigned user must be an employee"}), 400

    if not db.affairs.find_one({"_id": ObjectId(task_data.affair_id)}):
        return jsonify({"error": "Affair not found"}), 404

    task_dict = task_data.model_dump()
    task_dict["assigned_to"] = ObjectId(task_dict["assigned_to"])
    task_dict["affair_id"] = ObjectId(task_dict["affair_id"])
    if task_dict.get("service_id"):
        task_dict["service_id"] = ObjectId(task_dict["service_id"])
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
        description=f"Task '{task_data.title}' created for affair",
    )

    return jsonify(TaskResponse(**task_dict).model_dump(by_alias=True)), 201


@tasks_bp.route("/", methods=["GET"])
@jwt_required()
def list_tasks():
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    query = {}

    if role == "employee":
        query["assigned_to"] = ObjectId(identity)
    elif role == "customer":
        affairs = list(db.affairs.find({"customer_id": ObjectId(identity)}))
        affair_ids = [a["_id"] for a in affairs]
        if affair_ids:
            query["affair_id"] = {"$in": affair_ids}
        else:
            return jsonify([]), 200

    status = request.args.get("status")
    if status:
        query["status"] = status

    priority = request.args.get("priority")
    if priority:
        query["priority"] = priority

    affair_id = request.args.get("affair_id")
    if affair_id and role == "admin":
        query["affair_id"] = ObjectId(affair_id)

    service_id = request.args.get("service_id")
    if service_id and role == "admin":
        query["service_id"] = ObjectId(service_id)

    sort_field = request.args.get("sort", "created_at")
    sort_order = -1 if request.args.get("order", "desc") == "desc" else 1

    pipeline = [
        {"$match": query},
        {"$sort": {sort_field: sort_order}},
        {
            "$lookup": {
                "from": "users",
                "localField": "assigned_to",
                "foreignField": "_id",
                "as": "assigned_user",
            }
        },
        {"$unwind": {"path": "$assigned_user", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "affairs",
                "localField": "affair_id",
                "foreignField": "_id",
                "as": "affair",
            }
        },
        {"$unwind": {"path": "$affair", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "services",
                "localField": "service_id",
                "foreignField": "_id",
                "as": "service",
            }
        },
        {"$unwind": {"path": "$service", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "assigned_to_name": "$assigned_user.full_name",
                "affair_name": "$affair.name",
                "service_name": "$service.name",
            }
        },
        {"$project": {"assigned_user": 0, "affair": 0, "service": 0}},
    ]

    tasks = list(db.tasks.aggregate(pipeline))
    return jsonify([TaskResponse(**t).model_dump(by_alias=True) for t in tasks]), 200


@tasks_bp.route("/<task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id):
    db = get_db()
    pipeline = [
        {"$match": {"_id": ObjectId(task_id)}},
        {
            "$lookup": {
                "from": "users",
                "localField": "assigned_to",
                "foreignField": "_id",
                "as": "assigned_user",
            }
        },
        {"$unwind": {"path": "$assigned_user", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "affairs",
                "localField": "affair_id",
                "foreignField": "_id",
                "as": "affair",
            }
        },
        {"$unwind": {"path": "$affair", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "services",
                "localField": "service_id",
                "foreignField": "_id",
                "as": "service",
            }
        },
        {"$unwind": {"path": "$service", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "assigned_to_name": "$assigned_user.full_name",
                "affair_name": "$affair.name",
                "service_name": "$service.name",
            }
        },
        {"$project": {"assigned_user": 0, "affair": 0, "service": 0}},
    ]
    tasks = list(db.tasks.aggregate(pipeline))
    if not tasks:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(TaskResponse(**tasks[0]).model_dump(by_alias=True)), 200


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

    if "service_id" in update_dict and update_dict["service_id"]:
        update_dict["service_id"] = ObjectId(update_dict["service_id"])

    update_dict["updated_at"] = datetime.now(timezone.utc)

    old = db.tasks.find_one({"_id": ObjectId(task_id)})
    if not old:
        return jsonify({"error": "Task not found"}), 404

    if claims.get("role") != "admin":
        db.tasks.update_one(
            {"_id": ObjectId(task_id), "assigned_to": ObjectId(identity)},
            {"$set": update_dict},
        )
    else:
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
