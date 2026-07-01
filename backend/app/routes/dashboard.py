from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from app.database import get_db

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_task_query = {}
    if role == "employee":
        base_task_query["assigned_to"] = ObjectId(identity)
    elif role == "customer":
        affairs = list(db.affairs.find({"customer_id": ObjectId(identity)}))
        affair_ids = [a["_id"] for a in affairs]
        if affair_ids:
            base_task_query["affair_id"] = {"$in": affair_ids}
        else:
            return jsonify({
                "total_tasks": 0,
                "tasks_by_status": {},
                "tasks_by_priority": {},
                "users_count": 0,
                "recent_activities": [],
                "monthly_tasks": 0,
            }), 200

    total_tasks = db.tasks.count_documents(base_task_query)
    monthly_tasks = db.tasks.count_documents({**base_task_query, "created_at": {"$gte": first_of_month}})

    tasks_by_status = list(db.tasks.aggregate([
        {"$match": base_task_query},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]))

    tasks_by_priority = list(db.tasks.aggregate([
        {"$match": base_task_query},
        {"$group": {"_id": "$priority", "count": {"$sum": 1}}},
    ]))

    users_count = db.users.count_documents({"is_active": True}) if role == "admin" else 0
    customers_count = db.users.count_documents({"role": "customer"}) if role == "admin" else 0
    services_count = db.services.count_documents({}) if role == "admin" else 0

    open_tasks = None
    completed_tasks = None
    if role == "customer":
        open_tasks = db.tasks.count_documents({**base_task_query, "status": {"$in": ["pending", "in_progress"]}})
        completed_tasks = db.tasks.count_documents({**base_task_query, "status": "completed"})

    recent_pipeline = [
        {"$sort": {"created_at": -1}},
        {"$limit": 20},
        {
            "$lookup": {
                "from": "users",
                "localField": "performed_by",
                "foreignField": "_id",
                "as": "performer",
            }
        },
        {"$unwind": {"path": "$performer", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"performed_by_name": "$performer.full_name"}},
        {"$project": {"performer": 0}},
    ]
    recent_activities = list(db.audit_logs.aggregate(recent_pipeline))

    return jsonify({
        "total_tasks": total_tasks,
        "monthly_tasks": monthly_tasks,
        "tasks_by_status": {s["_id"]: s["count"] for s in tasks_by_status},
        "tasks_by_priority": {p["_id"]: p["count"] for p in tasks_by_priority},
        "users_count": users_count,
        "customers_count": customers_count,
        "services_count": services_count,
        "open_tasks": open_tasks,
        "completed_tasks": completed_tasks,
        "recent_activities": [
            {
                "id": str(a["_id"]),
                "action": a["action"],
                "entity_type": a["entity_type"],
                "description": a.get("description", ""),
                "performed_by_name": a.get("performed_by_name", ""),
                "created_at": a["created_at"].isoformat() if isinstance(a["created_at"], datetime) else str(a["created_at"]),
            }
            for a in recent_activities
        ],
    }), 200


@dashboard_bp.route("/assignations", methods=["GET"])
@jwt_required()
def assignations():
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    query = {}
    if role == "employee":
        query["assigned_to"] = ObjectId(identity)

    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$assigned_to", "task_count": {"$sum": 1}}},
        {
            "$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "user",
            }
        },
        {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "employee_name": "$user.full_name",
                "employee_username": "$user.username",
                "task_count": 1,
            }
        },
    ]

    assignations = list(db.tasks.aggregate(pipeline))
    return jsonify(assignations), 200


@dashboard_bp.route("/employee-stats", methods=["GET"])
@jwt_required()
def employee_stats():
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    if role != "employee":
        return jsonify({"error": "Employee access required"}), 403

    pending = db.activities.count_documents({"assigned_to": ObjectId(identity), "status": "pending"})
    in_progress = db.activities.count_documents({"assigned_to": ObjectId(identity), "status": "in_progress"})
    completed = db.activities.count_documents({"assigned_to": ObjectId(identity), "status": "completed"})
    unread = db.notifications.count_documents({"user_id": ObjectId(identity), "read": False})

    recent = list(db.activities.aggregate([
        {"$match": {"assigned_to": ObjectId(identity)}},
        {"$sort": {"created_at": -1}},
        {"$limit": 10},
        {
            "$lookup": {
                "from": "users",
                "localField": "customer_id",
                "foreignField": "_id",
                "as": "customer_user",
            }
        },
        {"$unwind": {"path": "$customer_user", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "customer_name": "$customer_user.full_name",
            }
        },
        {"$project": {"customer_user": 0}},
    ]))
    processed = []
    for a in recent:
        entry = {}
        for k, v in a.items():
            if isinstance(v, ObjectId):
                entry[k] = str(v)
            elif isinstance(v, datetime):
                entry[k] = v.isoformat()
            else:
                entry[k] = v
        processed.append(entry)

    return jsonify({
        "pending_activities": pending,
        "in_progress_activities": in_progress,
        "completed_activities": completed,
        "unread_notifications": unread,
        "recent_activities": processed,
    }), 200
