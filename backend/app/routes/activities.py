from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from app.database import get_db
from app.services.audit_service import AuditService
from app.socketio_server import notify_user, notify_badge_update
from functools import wraps

activities_bp = Blueprint("activities", __name__, url_prefix="/api/activities")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@activities_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_activity():
    db = get_db()
    data = request.get_json()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    assigned_to = data.get("assigned_to", "").strip()
    customer_id = data.get("customer_id", "").strip()
    task_ids = data.get("task_ids", [])

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not assigned_to:
        return jsonify({"error": "Assigned employee is required"}), 400
    if not db.users.find_one({"_id": ObjectId(assigned_to), "role": "employee"}):
        return jsonify({"error": "Assigned user must be an employee"}), 400
    if not customer_id:
        return jsonify({"error": "Customer is required"}), 400
    if not db.users.find_one({"_id": ObjectId(customer_id), "role": "customer"}):
        return jsonify({"error": "Customer not found"}), 400

    admin_id = get_jwt_identity()
    now = datetime.now(timezone.utc)

    activity_dict = {
        "title": title,
        "description": description or None,
        "assigned_to": ObjectId(assigned_to),
        "assigned_by": ObjectId(admin_id),
        "customer_id": ObjectId(customer_id),
        "task_ids": [ObjectId(tid) for tid in task_ids],
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    result = db.activities.insert_one(activity_dict)
    activity_dict["_id"] = str(result.inserted_id)

    notif_id = db.notifications.insert_one({
        "user_id": ObjectId(assigned_to),
        "type": "activity_assigned",
        "title": "New Activity Assigned",
        "message": f"You have been assigned a new activity: {title}",
        "activity_id": result.inserted_id,
        "read": False,
        "created_at": now,
    }).inserted_id

    AuditService.log(
        action="create",
        entity_type="notification",
        entity_id=str(notif_id),
        performed_by=admin_id,
        description=f"Activity assigned notification sent to user {assigned_to}",
    )

    notify_user(assigned_to, {
        "_id": str(notif_id),
        "type": "activity_assigned",
        "title": "New Activity Assigned",
        "message": f"You have been assigned a new activity: {title}",
        "activity_id": str(result.inserted_id),
        "read": False,
        "created_at": now.isoformat(),
    })
    notify_badge_update(assigned_to)

    AuditService.log(
        action="create",
        entity_type="activity",
        entity_id=str(result.inserted_id),
        performed_by=admin_id,
        description=f"Activity '{title}' created for employee",
    )

    activity_dict["assigned_to"] = str(activity_dict["assigned_to"])
    activity_dict["assigned_by"] = str(activity_dict["assigned_by"])
    activity_dict["customer_id"] = str(activity_dict["customer_id"])
    activity_dict["task_ids"] = [str(tid) for tid in activity_dict["task_ids"]]

    tasks_data = list(db.tasks.find({"_id": {"$in": [ObjectId(tid) for tid in task_ids]}}, {"title": 1}))
    activity_dict["task_names"] = [t["title"] for t in tasks_data]

    customer = db.users.find_one({"_id": ObjectId(customer_id)}, {"full_name": 1})
    activity_dict["customer_name"] = customer["full_name"] if customer else None

    return jsonify(activity_dict), 201


@activities_bp.route("/", methods=["GET"])
@jwt_required()
def list_activities():
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    query = {}
    if role == "employee":
        query["assigned_to"] = ObjectId(identity)

    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
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
                "from": "users",
                "localField": "assigned_by",
                "foreignField": "_id",
                "as": "assigned_by_user",
            }
        },
        {"$unwind": {"path": "$assigned_by_user", "preserveNullAndEmptyArrays": True}},
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
            "$lookup": {
                "from": "tasks",
                "localField": "task_ids",
                "foreignField": "_id",
                "as": "tasks",
            }
        },
        {
            "$addFields": {
                "assigned_to_name": "$assigned_user.full_name",
                "assigned_by_name": "$assigned_by_user.full_name",
                "customer_name": "$customer_user.full_name",
                "task_names": {"$map": {"input": "$tasks", "as": "t", "in": "$$t.title"}},
            }
        },
        {"$project": {"assigned_user": 0, "assigned_by_user": 0, "customer_user": 0, "tasks": 0}},
    ]

    activities = list(db.activities.aggregate(pipeline))
    for a in activities:
        for key in ("_id", "assigned_to", "assigned_by", "customer_id"):
            if key in a and isinstance(a[key], ObjectId):
                a[key] = str(a[key])
        if "task_ids" in a and a["task_ids"]:
            a["task_ids"] = [str(t) if isinstance(t, ObjectId) else t for t in a["task_ids"]]
    return jsonify(activities), 200


@activities_bp.route("/<activity_id>", methods=["GET"])
@jwt_required()
def get_activity(activity_id):
    db = get_db()
    pipeline = [
        {"$match": {"_id": ObjectId(activity_id)}},
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
                "from": "users",
                "localField": "assigned_by",
                "foreignField": "_id",
                "as": "assigned_by_user",
            }
        },
        {"$unwind": {"path": "$assigned_by_user", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "tasks",
                "localField": "task_ids",
                "foreignField": "_id",
                "as": "tasks",
            }
        },
        {
            "$addFields": {
                "assigned_to_name": "$assigned_user.full_name",
                "assigned_by_name": "$assigned_by_user.full_name",
                "task_names": {"$map": {"input": "$tasks", "as": "t", "in": "$$t.title"}},
            }
        },
        {"$project": {"assigned_user": 0, "assigned_by_user": 0, "tasks": 0}},
    ]
    activities = list(db.activities.aggregate(pipeline))
    if not activities:
        return jsonify({"error": "Activity not found"}), 404
    a = activities[0]
    for key in ("_id", "assigned_to", "assigned_by"):
        if key in a and isinstance(a[key], ObjectId):
            a[key] = str(a[key])
    if "task_ids" in a and a["task_ids"]:
        a["task_ids"] = [str(t) if isinstance(t, ObjectId) else t for t in a["task_ids"]]
    return jsonify(a), 200


@activities_bp.route("/<activity_id>/status", methods=["PUT"])
@jwt_required()
def update_activity_status(activity_id):
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    data = request.get_json()
    new_status = data.get("status", "").strip()

    if new_status not in ("in_progress", "completed", "cancelled"):
        return jsonify({"error": "Invalid status"}), 400

    activity = db.activities.find_one({"_id": ObjectId(activity_id)})
    if not activity:
        return jsonify({"error": "Activity not found"}), 404

    current = activity.get("status")
    role = claims.get("role")

    if role != "admin" and str(activity["assigned_to"]) != identity:
        return jsonify({"error": "Forbidden"}), 403

    if current == "completed":
        return jsonify({"error": "Activity is already completed"}), 400

    if current == "pending" and new_status != "in_progress" and role != "admin":
        return jsonify({"error": "Must accept before completing"}), 400

    if current == "in_progress" and new_status == "in_progress":
        return jsonify({"error": "Already in progress"}), 400

    now = datetime.now(timezone.utc)
    db.activities.update_one(
        {"_id": ObjectId(activity_id)},
        {"$set": {"status": new_status, "updated_at": now}},
    )

    admin_id = str(activity["assigned_by"])

    if new_status == "in_progress" and current == "pending":
        nid1 = db.notifications.insert_one({
            "user_id": ObjectId(admin_id),
            "type": "activity_accepted",
            "title": "Activity Accepted",
            "message": f"Employee accepted activity '{activity.get('title')}'",
            "activity_id": ObjectId(activity_id),
            "read": False,
            "created_at": now,
        }).inserted_id

        AuditService.log(
            action="create",
            entity_type="notification",
            entity_id=str(nid1),
            performed_by=identity,
            description=f"Activity accepted notification sent to admin {admin_id}",
        )

        notify_user(admin_id, {
            "_id": str(nid1),
            "type": "activity_accepted",
            "title": "Activity Accepted",
            "message": f"Employee accepted activity '{activity.get('title')}'",
            "activity_id": activity_id,
            "read": False,
            "created_at": now.isoformat(),
        })
        notify_badge_update(admin_id)

    if new_status == "completed":
        nid2 = db.notifications.insert_one({
            "user_id": ObjectId(admin_id),
            "type": "activity_completed",
            "title": "Activity Completed",
            "message": f"Activity '{activity.get('title')}' has been completed",
            "activity_id": ObjectId(activity_id),
            "read": False,
            "created_at": now,
        }).inserted_id

        AuditService.log(
            action="create",
            entity_type="notification",
            entity_id=str(nid2),
            performed_by=identity,
            description=f"Activity completed notification sent to admin {admin_id}",
        )

        notify_user(admin_id, {
            "_id": str(nid2),
            "type": "activity_completed",
            "title": "Activity Completed",
            "message": f"Activity '{activity.get('title')}' has been completed",
            "activity_id": activity_id,
            "read": False,
            "created_at": now.isoformat(),
        })
        notify_badge_update(admin_id)

    AuditService.log(
        action="update",
        entity_type="activity",
        entity_id=activity_id,
        performed_by=identity,
        description=f"Activity '{activity.get('title')}' status changed to {new_status}",
    )

    updated = db.activities.find_one({"_id": ObjectId(activity_id)})
    for key in ("_id", "assigned_to", "assigned_by"):
        if key in updated and isinstance(updated[key], ObjectId):
            updated[key] = str(updated[key])
    return jsonify(updated), 200


@activities_bp.route("/notifications", methods=["GET"])
@jwt_required()
def list_notifications():
    db = get_db()
    identity = get_jwt_identity()
    notifications = list(
        db.notifications.find({"user_id": ObjectId(identity)}).sort("created_at", -1).limit(50)
    )
    for n in notifications:
        if "_id" in n and isinstance(n["_id"], ObjectId):
            n["_id"] = str(n["_id"])
        if "user_id" in n and isinstance(n["user_id"], ObjectId):
            n["user_id"] = str(n["user_id"])
        if "activity_id" in n and isinstance(n["activity_id"], ObjectId):
            n["activity_id"] = str(n["activity_id"])
    return jsonify(notifications), 200


@activities_bp.route("/notifications/read", methods=["POST"])
@jwt_required()
def mark_notifications_read():
    db = get_db()
    identity = get_jwt_identity()
    result = db.notifications.update_many(
        {"user_id": ObjectId(identity), "read": False},
        {"$set": {"read": True}},
    )
    if result.modified_count > 0:
        AuditService.log(
            action="update",
            entity_type="notification",
            entity_id="",
            performed_by=identity,
            description=f"{result.modified_count} notifications marked as read",
        )
    return jsonify({"ok": True}), 200


@activities_bp.route("/notifications/unread-count", methods=["GET"])
@jwt_required()
def unread_notification_count():
    db = get_db()
    identity = get_jwt_identity()
    count = db.notifications.count_documents({"user_id": ObjectId(identity), "read": False})
    return jsonify({"count": count}), 200


@activities_bp.route("/notifications/send", methods=["POST"])
@jwt_required()
def send_notification():
    db = get_db()
    identity = get_jwt_identity()
    claims = get_jwt()
    data = request.get_json()
    target_user_id = data.get("user_id", "").strip()
    message = data.get("message", "").strip()
    title = data.get("title", "Notification").strip()

    if not target_user_id or not message:
        return jsonify({"error": "user_id and message are required"}), 400
    if not db.users.find_one({"_id": ObjectId(target_user_id)}):
        return jsonify({"error": "User not found"}), 404

    sender = db.users.find_one({"_id": ObjectId(identity)}, {"full_name": 1})
    sender_name = sender["full_name"] if sender else "Unknown"

    now = datetime.now(timezone.utc)
    nid = db.notifications.insert_one({
        "user_id": ObjectId(target_user_id),
        "type": "manual",
        "title": title,
        "message": f"From {sender_name}: {message}",
        "sender_id": ObjectId(identity),
        "read": False,
        "created_at": now,
    }).inserted_id

    notify_user(target_user_id, {
        "_id": str(nid),
        "type": "manual",
        "title": title,
        "message": f"From {sender_name}: {message}",
        "sender_id": identity,
        "read": False,
        "created_at": now.isoformat(),
    })
    notify_badge_update(target_user_id)

    AuditService.log(
        action="create",
        entity_type="notification",
        entity_id="",
        performed_by=identity,
        description=f"Manual notification sent to user {target_user_id}: {title}",
    )

    return jsonify({"ok": True}), 201
